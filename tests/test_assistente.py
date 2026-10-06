"""
Testes do assistente: modo offline (regras) e conversa livre (API simulada).
A API é simulada por um servidor local, então não precisam de internet nem de chave.

    python -m unittest discover -s tests -v
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

_TMP = tempfile.mkdtemp(prefix="ativos_assist_")
_DB = os.path.join(_TMP, "ativos.db")
if os.path.exists(os.path.join(RAIZ, "ativos.db")):
    shutil.copy(os.path.join(RAIZ, "ativos.db"), _DB)
os.environ["DB_PATH"] = _DB

import app as A  # noqa: E402

PEDIDOS = []      # o que o servidor simulado recebeu
MODO = {"valor": "ok"}


class ApiSimulada(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8"))
        PEDIDOS.append({"corpo": corpo, "chave": self.headers.get("x-api-key")})
        if MODO["valor"] == "erro":
            self.send_response(500)
            self.end_headers()
            return
        ultima = corpo["messages"][-1]["content"]
        if isinstance(ultima, list) and ultima and ultima[0].get("type") == "tool_result":
            dados = json.loads(ultima[0]["content"])
            total = dados.get("total_encontrado", dados.get("total"))
            resp = {"stop_reason": "end_turn", "content": [{"type": "text", "text": f"Encontrei **{total}** equipamentos."}]}
        else:
            texto = ultima if isinstance(ultima, str) else ""
            if "notebooks" in texto:
                bloco = {"type": "tool_use", "id": "t1", "name": "buscar_equipamentos",
                         "input": {"tipo": "notebook", "limite": 3}}
            else:
                bloco = {"type": "tool_use", "id": "t1", "name": "resumo_inventario", "input": {}}
            resp = {"stop_reason": "tool_use", "content": [bloco]}
        dados = json.dumps(resp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)


def sql(q):
    with sqlite3.connect(_DB) as db:
        return db.execute(q).fetchone()[0]


def admin():
    c = A.app.test_client()
    c.post("/login", data={"username": "Gabi", "password": "gabi1234"})
    return c


def perguntar(c, msg, **extra):
    return c.post("/api/chatbot", json={"message": msg, **extra}).get_json()


class Offline(unittest.TestCase):
    def setUp(self):
        os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_conversa_basica(self):
        c = admin()
        r = perguntar(c, "Obrigado!")["reply"]
        self.assertTrue(any(x in r for x in ("De nada", "Por nada", "Disponha", "Imagina")))
        self.assertIn("assistente", perguntar(c, "Quem é você?")["reply"])
        r = perguntar(c, "Tudo bem?")["reply"]
        self.assertTrue(any(x in r for x in ("Tudo ótimo", "Tudo certo", "Estou muito bem")))
        r = perguntar(c, "tchau")["reply"]
        self.assertTrue(any(x in r for x in ("Até", "Tchau")))
        self.assertTrue(perguntar(c, "ok")["reply"])

    def test_conversa_basica_nao_atrapalha_perguntas(self):
        r = perguntar(admin(), "Obrigado, quantos notebooks existem?")["reply"]
        n = sql("select count(*) from ativos where tipo='Notebook'")
        self.assertIn(f"**{n}**", r)

    def test_pergunta_de_seguimento(self):
        c = admin()
        r1 = perguntar(c, "Quantos equipamentos existem na sala maker?")
        r2 = perguntar(c, "e notebooks?", contexto=r1["contexto"])
        esperado = sql("select count(*) from ativos where local='Sala Maker' and tipo='Notebook'")
        self.assertIn(f"**{esperado}**", r2["reply"])
        r3 = perguntar(c, "e em uso?", contexto=r2["contexto"])
        esperado = sql("select count(*) from ativos where local='Sala Maker' and tipo='Notebook' and situacao='Em uso'")
        self.assertIn(f"**{esperado}**", r3["reply"])

    def test_contexto_malformado_nao_quebra(self):
        c = admin()
        for ctx in ("texto", 123, ["a"], {"tipo": 5, "locais": "x", "serie": "ZZ", "situacao": "?"}, None):
            self.assertTrue(perguntar(c, "e em uso?", contexto=ctx)["ok"])

    def test_modo_indicado(self):
        self.assertEqual(perguntar(admin(), "oi")["modo"], "regras")


class ConversaLivre(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), ApiSimulada)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}/v1/messages"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        PEDIDOS.clear()
        MODO["valor"] = "ok"
        os.environ["ANTHROPIC_API_KEY"] = "chave-de-teste"
        os.environ["ANTHROPIC_API_URL"] = self.url
        os.environ.pop("CHATBOT_ENVIAR_NOMES", None)
        A._USO_IA.clear()

    def tearDown(self):
        for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_API_URL", "CHATBOT_ENVIAR_NOMES", "CHATBOT_MODELO"):
            os.environ.pop(k, None)

    def test_fluxo_com_ferramenta(self):
        r = perguntar(admin(), "Quantos notebooks a escola tem?")
        n = sql("select count(*) from ativos where tipo='Notebook'")
        self.assertEqual(r["modo"], "ia")
        self.assertIn(f"**{n}**", r["reply"])                      # número veio do banco, via ferramenta
        self.assertEqual(len(PEDIDOS), 2)                          # pergunta + devolução do resultado
        self.assertEqual(PEDIDOS[0]["chave"], "chave-de-teste")
        corpo = PEDIDOS[0]["corpo"]
        self.assertEqual(corpo["model"], A.IA_MODELO_PADRAO)
        self.assertIn("Escola Estadual Antônio Branco Rodrigues Junior", corpo["system"])
        self.assertEqual({t["name"] for t in corpo["tools"]}, {"resumo_inventario", "buscar_equipamentos", "historico_recente"})

    def test_nomes_de_responsaveis_nao_sao_enviados(self):
        conn = A.get_db()
        try:
            os.environ["CHATBOT_ENVIAR_NOMES"] = "1"
            com_nomes = A._ferramenta_ia("buscar_equipamentos", {"tipo": "notebook", "limite": 3}, conn)["equipamentos"]
            os.environ.pop("CHATBOT_ENVIAR_NOMES")
        finally:
            conn.close()
        nomes = [n for e in com_nomes for n in e["responsaveis"]]
        self.assertTrue(nomes)
        perguntar(admin(), "Quantos notebooks?")
        enviado = json.dumps(PEDIDOS[1]["corpo"], ensure_ascii=False)
        self.assertTrue(all(n not in enviado for n in nomes))              # padrão: nenhum nome sai
        os.environ["CHATBOT_ENVIAR_NOMES"] = "1"
        PEDIDOS.clear()
        perguntar(admin(), "Quantos notebooks?")
        enviado = json.dumps(PEDIDOS[1]["corpo"], ensure_ascii=False)
        self.assertTrue(all(n in enviado for n in nomes))

    def test_historico_limpo_e_modelo_configuravel(self):
        os.environ["CHATBOT_MODELO"] = "modelo-x"
        hist = [{"role": "assistant", "content": "fala solta"}, {"role": "user", "content": "oi"},
                {"role": "user", "content": "tudo bem?"}, {"role": "invalido", "content": "x"}, "lixo", {"role": "assistant", "content": ""}]
        perguntar(admin(), "Resuma tudo", history=hist)
        corpo = PEDIDOS[0]["corpo"]
        self.assertEqual(corpo["model"], "modelo-x")
        msgs = corpo["messages"]
        self.assertEqual(msgs[0]["role"], "user")                  # nunca começa por "assistant"
        self.assertTrue(all(a["role"] != b["role"] for a, b in zip(msgs, msgs[1:])))   # papéis alternados

    def test_erro_da_api_volta_para_o_modo_offline(self):
        MODO["valor"] = "erro"
        r = perguntar(admin(), "Quantos equipamentos existem?")
        self.assertEqual(r["modo"], "regras")
        self.assertIn(f"**{sql('select count(*) from ativos')}**", r["reply"])

    def test_api_fora_do_ar_volta_para_o_modo_offline(self):
        os.environ["ANTHROPIC_API_URL"] = "http://127.0.0.1:9/v1/messages"
        r = perguntar(admin(), "Quantos equipamentos existem?")
        self.assertEqual(r["modo"], "regras")

    def test_limite_de_uso(self):
        antigo = A._IA_MAX_MENSAGENS
        A._IA_MAX_MENSAGENS = 2
        try:
            modos = [perguntar(admin(), "Resuma tudo")["modo"] for _ in range(4)]
        finally:
            A._IA_MAX_MENSAGENS = antigo
        self.assertEqual(modos, ["ia", "ia", "regras", "regras"])

    def test_visitante_usa_e_anonimo_nao(self):
        v = A.app.test_client()
        v.get("/visitante")
        self.assertEqual(perguntar(v, "Resuma tudo")["modo"], "ia")
        self.assertIn("visitante", PEDIDOS[0]["corpo"]["system"])
        anon = A.app.test_client()
        self.assertEqual(anon.post("/api/chatbot", json={"message": "oi"}).status_code, 401)

    def test_ferramentas_so_leem(self):
        antes = sql("select count(*) from ativos")
        conn = A.get_db()
        try:
            r = A._ferramenta_ia("buscar_equipamentos", {"tipo": "TABLET", "local": "sala maker", "limite": 500}, conn)
            self.assertLessEqual(r["exibidos"], 25)
            self.assertEqual(A._ferramenta_ia("apagar_tudo", {}, conn), {"erro": "Ferramenta desconhecida."})
        finally:
            conn.close()
        self.assertEqual(sql("select count(*) from ativos"), antes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
