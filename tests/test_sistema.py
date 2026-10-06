"""
Testes automáticos do back-end do Ativos Escolares.
Rodam contra uma CÓPIA temporária do banco: nunca tocam no ativos.db real.

    python -m unittest discover -s tests -v
"""
import io
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

_TMP = tempfile.mkdtemp(prefix="ativos_test_")
_DB = os.path.join(_TMP, "ativos.db")
if os.path.exists(os.path.join(RAIZ, "ativos.db")):
    shutil.copy(os.path.join(RAIZ, "ativos.db"), _DB)
os.environ["DB_PATH"] = _DB

import app as A  # noqa: E402  (precisa vir depois de definir DB_PATH)

ATIVO = {
    "serie_id": "2A", "tipo": "Notebook", "id_computer": "TESTE-EXPO-01", "marca": "Positivo",
    "modelo": "Teste", "local": "Sala Maker", "situacao": "Em uso", "criticidade": "Nenhuma",
    "owner_1": "Ana", "owner_2": "", "id_carregator": "99", "mochila": "Sim",
}


def cliente_admin():
    c = A.app.test_client()
    c.post("/login", data={"username": "Gabi", "password": "gabi1234"})
    return c


def cliente_visitante():
    c = A.app.test_client()
    c.get("/visitante")
    return c


def sql(q):
    with sqlite3.connect(_DB) as db:
        return db.execute(q).fetchone()[0]


class Autenticacao(unittest.TestCase):
    def test_anonimo_bloqueado(self):
        c = A.app.test_client()
        for rota in ("/api/ativos", "/api/dashboard", "/api/historico", "/exportar"):
            self.assertEqual(c.get(rota).status_code, 401, rota)
        self.assertEqual(c.post("/api/chatbot", json={"message": "oi"}).status_code, 401)
        self.assertEqual(c.get("/").status_code, 302)

    def test_login_mensagens(self):
        c = A.app.test_client()
        self.assertIn("Usuário ou senha incorretos.", c.post("/login", data={"username": "Gabi", "password": "x"}).get_data(as_text=True))
        self.assertIn("Informe usuário e senha.", c.post("/login", data={"username": "", "password": ""}).get_data(as_text=True))

    def test_login_valido_e_logout(self):
        c = cliente_admin()
        self.assertEqual(c.get("/api/me").get_json()["role"], "admin")
        c.get("/logout")
        self.assertEqual(c.get("/api/me").status_code, 401)


class Permissoes(unittest.TestCase):
    def test_visitante_consulta_mas_nao_escreve(self):
        v = cliente_visitante()
        antes = sql("select count(*) from ativos")
        self.assertEqual(v.get("/api/ativos").status_code, 200)
        self.assertEqual(v.get("/api/dashboard").status_code, 200)
        self.assertEqual(v.post("/api/ativos", json=ATIVO).status_code, 403)
        self.assertEqual(v.put("/api/ativos/1", json=ATIVO).status_code, 403)
        self.assertEqual(v.delete("/api/ativos/1").status_code, 403)
        self.assertEqual(v.post("/api/registrar", json=ATIVO).status_code, 403)
        self.assertEqual(v.delete("/api/remover/2A/1").status_code, 403)
        self.assertEqual(v.get("/exportar").status_code, 403)
        self.assertEqual(v.get("/api/admin/info").status_code, 403)
        self.assertEqual(sql("select count(*) from ativos"), antes)

    def test_interface_do_visitante_sem_botoes_de_admin(self):
        html = cliente_visitante().get("/").get_data(as_text=True)
        self.assertNotIn('id="new-btn"', html)
        self.assertNotIn('data-view="admin"', html)


class CrudEHistorico(unittest.TestCase):
    def test_ciclo_completo(self):
        a = cliente_admin()
        r = a.post("/api/ativos", json=ATIVO)
        self.assertEqual(r.status_code, 201)
        nid = r.get_json()["id"]
        self.assertEqual(a.post("/api/ativos", json=ATIVO).status_code, 409)           # duplicado
        r = a.put(f"/api/ativos/{nid}", json={**ATIVO, "local": "Sala 06", "situacao": "Não em uso"})
        self.assertEqual(r.get_json()["alteracoes"], 2)
        hist = a.get(f"/api/historico?ativo_id={nid}").get_json()
        self.assertEqual(hist["total"], 3)                                              # criação + 2 edições
        self.assertTrue(all(h["usuario"] == "Gabi" for h in hist["items"]))
        self.assertEqual(a.delete(f"/api/ativos/{nid}").status_code, 200)
        self.assertEqual(a.delete(f"/api/ativos/{nid}").status_code, 404)
        exc = a.get("/api/historico?operacao=exclusao").get_json()
        self.assertGreaterEqual(exc["total"], 1)                                        # histórico sobrevive à exclusão

    def test_validacoes(self):
        a = cliente_admin()
        self.assertEqual(a.post("/api/ativos", json={**ATIVO, "id_computer": ""}).status_code, 400)
        self.assertEqual(a.post("/api/ativos", json={**ATIVO, "id_computer": "V1", "serie_id": "ZZ"}).status_code, 400)
        self.assertEqual(a.post("/api/ativos", json={**ATIVO, "id_computer": "V2", "situacao": "talvez"}).status_code, 400)
        self.assertEqual(a.post("/api/ativos", json={**ATIVO, "id_computer": "V" * 300}).status_code, 400)
        self.assertEqual(a.post("/api/ativos", data="x", content_type="text/plain").status_code, 415)
        self.assertEqual(a.put("/api/ativos/999999", json=ATIVO).status_code, 404)


class ConsultaEFiltros(unittest.TestCase):
    def test_numeros_batem_com_o_banco(self):
        a = cliente_admin()
        d = a.get("/api/dashboard").get_json()
        self.assertEqual(d["total"], sql("select count(*) from ativos"))
        self.assertEqual(d["em_uso"], sql("select count(*) from ativos where situacao='Em uso'"))
        self.assertEqual(d["criticos"], sql("select count(*) from ativos where criticidade='Sim'"))

    def test_busca_filtros_ordenacao_paginacao(self):
        a = cliente_admin()
        total = sql("select count(*) from ativos")
        self.assertEqual(a.get("/api/ativos?per_page=200").get_json()["total"], total)
        self.assertGreater(a.get("/api/ativos?q=positivo").get_json()["total"], 0)
        self.assertEqual(a.get("/api/ativos?q=zzzzzz").get_json()["total"], 0)
        self.assertEqual(a.get("/api/ativos?tipo=' OR 1=1 --").get_json()["total"], 0)   # injeção SQL inofensiva
        self.assertEqual(a.get("/api/ativos?sort=;drop table ativos&dir=x").status_code, 200)
        p = a.get("/api/ativos?per_page=10&page=999").get_json()
        self.assertEqual(p["page"], p["pages"])


class Chatbot(unittest.TestCase):
    def pergunta(self, texto):
        return cliente_admin().post("/api/chatbot", json={"message": texto}).get_json()["reply"]

    def test_respostas_com_dados_reais(self):
        self.assertIn(f"**{sql('select count(*) from ativos')}**", self.pergunta("Quantos equipamentos existem?"))
        notebooks = sql("select count(*) from ativos where tipo = 'Notebook'")
        self.assertIn(f"**{notebooks}**", self.pergunta("Quantos notebooks existem?"))
        r = self.pergunta("Quantos equipamentos existem no laboratório?")
        self.assertIn("laboratório", r)
        self.assertIn("Sala Maker", r)
        self.assertIn("Novo ativo", self.pergunta("Como cadastrar?"))
        resposta = self.pergunta("qual a capital da França?")
        self.assertTrue("foge do que eu sei" in resposta or "não acesso a internet" in resposta)

    def test_mensagem_vazia(self):
        self.assertEqual(cliente_admin().post("/api/chatbot", json={"message": "  "}).status_code, 400)


class Exportacao(unittest.TestCase):
    def test_excel(self):
        import pandas as pd
        r = cliente_admin().get("/exportar")
        self.assertEqual(r.status_code, 200)
        self.assertIn("relatorio_ativos.xlsx", r.headers["Content-Disposition"])
        df = pd.read_excel(io.BytesIO(r.data))
        self.assertEqual(len(df), sql("select count(*) from ativos"))


class Seguranca(unittest.TestCase):
    def test_cabecalhos_e_qr(self):
        c = cliente_admin()
        r = c.get("/")
        self.assertIn("script-src 'self'", r.headers["Content-Security-Policy"])
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")
        self.assertEqual(c.get("/api/ativos").headers["Cache-Control"], "no-store")
        n = A.app.test_client()
        self.assertIn("/login", n.get("/equipamento/5").headers["Location"])
        n.post("/login", data={"username": "Eduardo", "password": "dudu1234"})
        self.assertIn('data-open="5"', n.get("/equipamento/5").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
