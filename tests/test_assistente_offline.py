"""
Testes do assistente offline (assistente.py).
Usam uma cópia temporária do banco; os números esperados vêm de consultas SQL diretas.

    python -m unittest discover -s tests -v
"""
import os
import random
import shutil
import sqlite3
import string
import sys
import tempfile
import time
import unittest
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

_TMP = tempfile.mkdtemp(prefix="ativos_offline_")
_DB = os.path.join(_TMP, "ativos.db")
if os.path.exists(os.path.join(RAIZ, "ativos.db")):
    shutil.copy(os.path.join(RAIZ, "ativos.db"), _DB)
os.environ.setdefault("DB_PATH", _DB)

import app as A  # noqa: E402

_DB = A.DB_PATH   # o app é importado uma única vez; usa o banco dele
import assistente as S  # noqa: E402
import assistente_conteudo as C  # noqa: E402

AGORA = datetime(2026, 10, 4, 14, 32)


def sql(q, *args):
    with sqlite3.connect(_DB) as db:
        return db.execute(q, args).fetchone()[0]


def semear_historico():
    with sqlite3.connect(_DB) as db:
        db.execute("DELETE FROM historico")
        db.executemany(
            "INSERT INTO historico(ativo_id,id_computer,serie_id,tipo,usuario,operacao,campo,valor_anterior,valor_novo,criado_em) VALUES (?,?,?,?,?,?,?,?,?,?)",
            [(4, "7", "2A", "Notebook", "Gabi", "edicao", "Local", "Armário Maker", "Sala 06", "2026-10-03 09:22:11"),
             (21, "TESTE-1", "2A", "Notebook", "Eduardo", "exclusao", "", "Notebook Positivo · Sala Maker", "", "2026-10-04 11:15:03")])


def base():
    conn = A.get_db()
    try:
        return A._base_assistente(conn)
    finally:
        conn.close()


class Dialogo:
    """Conversa com contexto, como o navegador faz."""
    def __init__(self, perfil="admin", usuario="Gabi", semente=1):
        self.ctx, self.perfil, self.usuario = None, perfil, usuario
        self.rnd = random.Random(semente)
        self.base = base()

    def diz(self, msg):
        r = S.responder(msg, self.base, self.ctx, self.usuario, self.perfil, AGORA, self.rnd)
        self.ctx = r["contexto"]
        self.ultima = r
        return r["reply"]


class Dados(unittest.TestCase):
    def test_contagens_batem_com_o_banco(self):
        d = Dialogo()
        total = sql("select count(*) from ativos")
        self.assertIn(f"**{total}**", d.diz("Quantos equipamentos existem?"))
        self.assertIn(f"**{sql('select count(*) from ativos where tipo=?', 'Notebook')}**", d.diz("quantos notebooks?"))
        self.assertIn(f"**{sql('select count(*) from ativos where tipo=?', 'Tablet')}**", d.diz("quantos tablets existem"))
        self.assertIn(f"**{sql('select count(*) from ativos where tipo=?', 'Televisão')}**", d.diz("quantas televisões?"))
        self.assertIn(f"**{sql('select count(*) from ativos where tipo=? and situacao=?', 'Notebook', 'Em uso')}**",
                      d.diz("Quantos notebooks estão em uso?"))
        self.assertIn(f"**{sql('select count(*) from ativos where local=?', 'Sala Maker')}**",
                      d.diz("quantos equipamentos na sala maker?"))
        self.assertIn(f"**{sql('select count(*) from ativos where marca=?', 'LG')}**", d.diz("quantos equipamentos da marca LG?"))
        self.assertIn(f"**{sql('select count(*) from ativos where serie_id=?', '2A')}**", d.diz("quantos equipamentos na 2a?"))

    def test_zero_resultados_com_alternativa(self):
        d = Dialogo()
        r = d.diz("tem tablet na sala 06?")
        self.assertIn("Não encontrei", r)
        self.assertIn("Mas há", r)
        self.assertIn("todos", d.diz("quantos estão fora de uso?"))
        self.assertIn("Nenhum equipamento está marcado como crítico", d.diz("quantos são críticos?"))

    def test_local_inexistente(self):
        r = Dialogo().diz("Quantos equipamentos existem no laboratório?")
        self.assertIn("laboratório", r)
        self.assertIn("Sala Maker", r)

    def test_seguimento_herda_filtros(self):
        d = Dialogo()
        d.diz("Quantos equipamentos existem na sala maker?")
        esperado = sql("select count(*) from ativos where local='Sala Maker' and tipo='Notebook'")
        self.assertIn(f"**{esperado}**", d.diz("e notebooks?"))
        esperado = sql("select count(*) from ativos where local='Sala Maker' and tipo='Notebook' and situacao='Em uso'")
        self.assertIn(f"**{esperado}**", d.diz("e em uso?"))

    def test_equipamentos_explicito_nao_herda(self):
        d = Dialogo()
        d.diz("quantos tablets?")
        self.assertIn(f"**{sql('select count(*) from ativos')}**", d.diz("quantos equipamentos existem?"))

    def test_lista_paginada_sem_repetir(self):
        d = Dialogo()
        d.diz("liste os notebooks")
        ids1 = [i["id"] for i in d.ultima["items"]]
        self.assertEqual(len(ids1), 8)
        d.diz("mostra mais")
        ids2 = [i["id"] for i in d.ultima["items"]]
        self.assertFalse(set(ids1) & set(ids2))
        vistos = set(ids1) | set(ids2)
        for _ in range(10):
            d.diz("mostra mais")
            vistos |= {i["id"] for i in d.ultima["items"]}
            if "mais" not in d.ultima["reply"].lower() or "…e mais" not in d.ultima["reply"]:
                break
        self.assertEqual(len(vistos), sql("select count(*) from ativos where tipo='Notebook'"))

    def test_mostra_mais_sem_lista(self):
        self.assertIn("Não tenho mais itens", Dialogo().diz("mostra mais"))

    def test_oferta_sim_e_nao(self):
        d = Dialogo()
        d.diz("quantos notebooks?")
        self.assertIn("Notebook", d.diz("sim"))
        self.assertTrue(d.ultima["items"])
        d2 = Dialogo()
        d2.diz("quantos notebooks?")
        self.assertIn(d2.diz("não"), ["Tudo bem! Se mudar de ideia, é só falar.", "Sem problema. Estou por aqui se precisar."])

    def test_quais_sao_usa_o_contexto(self):
        d = Dialogo()
        d.diz("e tablets?")
        d.diz("quais são?")
        self.assertTrue(all("Tablet" in i["label"] or "TABLETS" in i["label"] for i in d.ultima["items"]))

    def test_ranking_comparacao_distribuicao_porcentagem(self):
        d = Dialogo()
        top_local = sql("select local from ativos group by local order by count(*) desc limit 1")
        self.assertIn(top_local, d.diz("qual local tem mais equipamentos?"))
        self.assertIn("Notebook", d.diz("qual tipo é mais comum?"))
        self.assertIn("A marca", d.diz("qual marca tem mais?"))
        self.assertIn("Notebook", d.diz("tem mais notebook ou tablet?"))
        r = d.diz("quantos por local?")
        self.assertIn("Distribuição por local", r)
        pc = round(sql("select count(*) from ativos where tipo='Notebook'") * 100 / sql("select count(*) from ativos"), 1)
        self.assertIn(str(pc).replace(".", ","), d.diz("qual a porcentagem de notebooks?"))
        self.assertIn("Sala Maker", d.diz("onde estão os tablets?"))

    def test_catalogos(self):
        d = Dialogo()
        self.assertIn("Sala Maker", d.diz("quais locais existem?"))
        self.assertIn("Positivo", d.diz("quais marcas existem?"))
        self.assertIn(f"**{len(base().locais)}**", d.diz("quantos locais temos?"))
        self.assertIn("Notebook", d.diz("quais tipos existem?"))

    def test_resumo(self):
        r = Dialogo().diz("me dá um resumo")
        self.assertIn(f"**{sql('select count(*) from ativos')}**", r)
        self.assertIn("Tipo mais comum", r)


class Equipamentos(unittest.TestCase):
    def test_detalhe_por_id_e_atributos(self):
        d = Dialogo()
        a = d.base.ativos[0]
        unico = next(x for x in d.base.ativos if len(d.base.por_id[S.squash(S.norm(x["id_computer"]))]) == 1)
        r = d.diz(f"equipamento {unico['id_computer']}")
        self.assertIn(unico["local"], r)
        self.assertIn(unico["local"], d.diz("onde está?"))
        r = d.diz("e quem usa?")
        donos = [x for x in (unico["owner_1"], unico["owner_2"]) if x]
        self.assertTrue(all(n in r for n in donos))
        self.assertIn(unico["situacao"], d.diz("qual a situação?"))

    def test_id_repetido_pergunta_e_depois_responde_o_que_foi_pedido(self):
        d = Dialogo()
        r = d.diz("onde está o 7?")
        self.assertIn("Qual deles", r)
        self.assertIn("Antes", d.diz("e quem usa?"))
        r = d.diz("o da 2a")
        eq = next(x for x in d.base.ativos if x["id_computer"] == "7" and x["serie_id"] == "2A")
        donos = [x for x in (eq["owner_1"], eq["owner_2"]) if x]
        self.assertTrue(all(n in r for n in donos))        # responde a última pergunta feita ("quem usa")

    def test_carregador_com_tipo_antes_do_numero(self):
        d = Dialogo()
        eq = next(x for x in d.base.ativos if x["tipo"] == "Notebook" and x["serie_id"] == "2A" and x["id_carregator"])
        r = d.diz(f"qual o carregador do notebook {eq['id_computer']} da 2a?")
        self.assertIn(eq["id_carregator"], r)

    def test_ids_com_barra(self):
        d = Dialogo()
        eq = next(x for x in d.base.ativos if x["id_computer"].startswith("N/-"))
        self.assertIn(eq["local"], d.diz(f"onde está o {eq['id_computer']}?"))

    def test_pessoas(self):
        d = Dialogo()
        dono = next(x for x in d.base.donos if len(x.split()) == 1 and x not in ("Professores",) and x.isalpha())
        r = d.diz(f"o que o {dono} usa?")
        self.assertIn(dono, r)
        self.assertTrue(d.ultima["items"])
        self.assertIn("Professores", d.diz("equipamentos dos professores"))


class Sistema(unittest.TestCase):
    def test_topicos_de_ajuda(self):
        d = Dialogo()
        casos = {
            "Como cadastrar?": "Novo ativo", "como exporto o excel?": "Exportar Excel", "o que é CRUD?": "Criar (cadastrar)",
            "o que significa crítico?": "criticidade", "como funciona o histórico?": "Histórico",
            "esqueci minha senha": "ADMIN_USERS", "não consigo editar": "visitante", "como imprimir o qr code": "QR Code",
            "como uso o filtro?": "Filtros", "como mudo para o tema escuro?": "lua", "dá pra desfazer uma exclusão?": "não pode ser desfeita",
            "como faço pra baixar a tabela": "Exportar Excel", "como usar o sistema": "Painel", "como funciona o backup?": "cópia",
        }
        for pergunta, esperado in casos.items():
            self.assertIn(esperado, d.diz(pergunta).replace("**", ""), pergunta)

    def test_ajuda_traz_atalho_e_aviso_de_visitante(self):
        d = Dialogo(perfil="visitor", usuario=None)
        r = d.diz("Como cadastrar?")
        self.assertIn("visitante", r)
        self.assertTrue(d.ultima["links"])
        r = Dialogo(perfil="visitor", usuario=None)
        r.diz("como exportar?")
        self.assertFalse([l for l in r.ultima["links"] if l.get("view") == "admin"])   # visitante não é levado à Administração

    def test_glossario(self):
        d = Dialogo()
        self.assertIn("cópia de segurança", d.diz("o que é backup?"))
        self.assertIn("computador portátil", d.diz("o que é um notebook?"))
        self.assertIn("Wi-Fi", d.diz("o que é wifi?"))

    def test_link_para_inventario_com_filtro(self):
        d = Dialogo()
        d.diz("liste os tablets")
        links = [l for l in d.ultima["links"] if "filtro" in l]
        self.assertEqual(links[0]["filtro"].get("tipo"), "Tablet")

    def test_historico(self):
        semear_historico()
        d = Dialogo()
        self.assertIn("TESTE-1", d.diz("quem alterou por último?"))
        self.assertIn("Gabi", d.diz("o que mudou?"))
        self.assertIn("03/10/2026", d.diz("alterações de 03/10/2026"))
        self.assertIn("Não encontrei", d.diz("alterações de 01/10"))

    def test_historico_vazio(self):
        with sqlite3.connect(_DB) as db:
            db.execute("DELETE FROM historico")
        self.assertIn("vazio", Dialogo().diz("o que mudou?"))


class Conversa(unittest.TestCase):
    def variantes(self, nome):
        padrao = next(p for n, p, r in C.SOCIAL if n == nome)
        resp = next(r for n, p, r in C.SOCIAL if n == nome)
        return [x.format(escola=A.ESCOLA_NOME) for x in resp]

    def dentro(self, resposta, nome):
        # aceita a variante com ou sem o nome da pessoa inserido
        limpas = [v.replace("!", "").replace(".", "") for v in self.variantes(nome)]
        simples = resposta.replace("!", "").replace(",", "").replace(".", "")
        return any(all(parte in simples for parte in v.replace(",", "").split()[:3]) for v in limpas)

    def test_papo_basico(self):
        d = Dialogo(usuario="Gabi")
        self.assertTrue(self.dentro(d.diz("obrigado!"), "agradecimento"))
        self.assertTrue(self.dentro(d.diz("tchau"), "despedida"))
        self.assertTrue(self.dentro(d.diz("tudo bem?"), "como_vai"))
        self.assertTrue(self.dentro(d.diz("quem é você?"), "quem_e_voce"))
        self.assertTrue(self.dentro(d.diz("vc eh um robo?"), "quem_e_voce"))
        self.assertTrue(self.dentro(d.diz("kkkk"), "risada"))
        self.assertTrue(self.dentro(d.diz("você gosta de música?"), "gostos"))
        self.assertIn("conhecimentos gerais", d.diz("qual a capital da França?"))
        self.assertIn("Contar e listar", d.diz("o que você sabe fazer?").replace("**", ""))

    def test_saudacao_usa_hora_e_nome(self):
        r = Dialogo(usuario="Gabi").diz("oi")
        self.assertIn("Boa tarde", r)
        self.assertIn("Gabi", r)
        self.assertIn("Bom dia", Dialogo().diz("bom dia"))

    def test_nome_lembrado(self):
        d = Dialogo(perfil="visitor", usuario=None)
        self.assertIn("Carla", d.diz("meu nome é Carla"))
        self.assertIn("Carla", d.diz("oi"))
        self.assertIn("Carla", d.diz("quem sou eu?"))

    def test_perfil(self):
        self.assertIn("administrador", Dialogo().diz("qual meu perfil?"))
        self.assertIn("visitante", Dialogo(perfil="visitor", usuario=None).diz("posso editar?"))
        self.assertIn("Gabi", Dialogo().diz("quem são os administradores?"))
        self.assertIn("só para os próprios", Dialogo(perfil="visitor", usuario=None).diz("quem são os administradores?"))

    def test_hora_e_data(self):
        d = Dialogo()
        self.assertIn("14:32", d.diz("que horas são?"))
        self.assertIn("domingo, 4 de outubro de 2026", d.diz("que dia é hoje?"))

    def test_contas(self):
        d = Dialogo()
        self.assertIn("**4**", d.diz("quanto é 2+2?"))
        self.assertIn("**30**", d.diz("15% de 200"))
        self.assertIn("**9**", d.diz("raiz de 81"))
        self.assertIn("**5**", d.diz("20 dividido por 4"))
        self.assertIn("**14**", d.diz("quanto é (3+4)*2"))
        self.assertIn("zero", d.diz("quanto é 10 dividido por 0"))
        self.assertNotIn("**", d.diz("alterações de 03/10/2026"))        # data não vira conta

    def test_diversao(self):
        d = Dialogo()
        r = d.diz("me conta uma piada")
        self.assertTrue(any(p in r for p in C.PIADAS))
        self.assertNotEqual(d.diz("outra"), r)
        r = d.diz("me conta uma curiosidade")
        self.assertTrue(any(c in r for c in C.CURIOSIDADES))
        r = d.diz("me dá uma dica")
        self.assertTrue(any(c in r for c in C.DICAS))

    def test_cansado_oferece_ânimo(self):
        d = Dialogo()
        d.diz("estou cansado")
        r = d.diz("sim")
        self.assertTrue(any(m in r for m in C.MOTIVACAO))

    def test_repetir(self):
        d = Dialogo()
        d.diz("quantos tablets?")
        self.assertIn("repetindo", d.diz("repete"))

    def test_erros_de_digitacao(self):
        d = Dialogo()
        n = sql("select count(*) from ativos where tipo='Notebook'")
        self.assertIn(f"**{n}**", d.diz("quantos notbooks tem?"))
        self.assertIn(f"**{sql('select count(*) from ativos where tipo=?', 'Tablet')}**", d.diz("qntos tablets existem"))
        self.assertIn("Histórico", d.diz("histrico"))
        self.assertIn("Sala Maker", d.diz("qual o loca com mais equipamentos"))
        self.assertIn(f"**{sql('select count(*) from ativos where tipo=? and situacao=?', 'Notebook', 'Em uso')}**",
                      d.diz("qntos notebokks estao em uzo"))

    def test_conversa_longa(self):
        d = Dialogo()
        falas = ["bom dia", "tudo bem?", "preciso saber quantos notebooks tem na sala maker", "e os tablets?", "e na sala 06?",
                 "valeu", "agora me conta uma curiosidade", "outra", "obrigado, era só isso", "tchau"]
        respostas = [d.diz(f) for f in falas]
        self.assertTrue(all(r.strip() for r in respostas))
        self.assertIn(f"**{sql('select count(*) from ativos where local=? and tipo=?', 'Sala Maker', 'Notebook')}**", respostas[2])


class Robustez(unittest.TestCase):
    def test_contexto_malicioso(self):
        b = base()
        ruins = ["texto", 123, ["a"], {"f": "x"}, {"f": {"tipos": "x", "serie": "ZZ", "situacao": "?", "locais": [1, {}]}},
                 {"oferta": {"acao": "apagar_tudo"}}, {"lista": {"offset": -5}}, {"lista": {"offset": 10 ** 12}},
                 {"ultimo_id": "x"}, {"cand": "x"}, {"nome": "<script>alert(1)</script>"}, {"ultima": 5}, {"fun": {"tipo": "x"}}, None]
        for c in ruins:
            r = S.responder("e em uso?", b, c, "Gabi", "admin", AGORA, random.Random(1))
            self.assertTrue(r["reply"])
        self.assertNotIn("nome", S.limpar_contexto({"nome": "<script>alert(1)</script>"}))

    def test_texto_aleatorio_nunca_quebra(self):
        b, rnd = base(), random.Random(7)
        alfabeto = string.ascii_letters + string.digits + " áéíóúãõç?!.,;:/\\-+*()%<>'\"\n\t"
        for _ in range(400):
            txt = "".join(rnd.choice(alfabeto) for _ in range(rnd.randint(0, 120)))
            r = S.responder(txt, b, None, "Gabi", "admin", AGORA, random.Random(1))
            self.assertIsInstance(r["reply"], str)
            self.assertIn("contexto", r)

    def test_frases_estranhas(self):
        d = Dialogo()
        for f in ["", "   ", "???", "a", "1234567890", "<script>alert(1)</script>", "DROP TABLE ativos;", "x" * 5000,
                  "quantos " * 200, "🙂🙂", "\u0000\u0001"]:
            self.assertTrue(d.diz(f).strip())
        self.assertEqual(sql("select count(*) from ativos"), len(base().ativos))

    def test_resposta_e_texto_puro(self):
        r = Dialogo().diz("<b>oi</b>")
        self.assertIsInstance(r, str)

    def test_velocidade(self):
        d = Dialogo()
        t0 = time.time()
        for _ in range(50):
            d.diz("quantos notebooks estão em uso na sala maker?")
        self.assertLess((time.time() - t0) / 50, 0.1)      # menos de 100 ms por resposta


if __name__ == "__main__":
    unittest.main(verbosity=2)
