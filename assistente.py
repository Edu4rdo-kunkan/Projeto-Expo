"""Motor do assistente offline do Ativos Escolares.

Recebe a mensagem, os dados (equipamentos e histórico) e o contexto da conversa
(o que foi perguntado antes) e devolve a resposta. Não usa internet.

Fluxo: normaliza o texto, corrige erros comuns de digitação, reconhece as
"entidades" (tipo, local, categoria, responsável, ID...) e passa por uma
sequência de tratadores; o primeiro que souber responder ganha.
"""
import ast
import difflib
import math
import operator
import random
import re
import unicodedata
from datetime import datetime

from assistente_conteudo import (
    AJUDA, CAPACIDADES, CURIOSIDADES, DICAS, GLOSSARIO, MOTIVACAO, PIADAS, SOCIAL,
)

PAGINA = 8
SERIES_ORDEM = ["2A", "3A", "SETUPS", "CARRINHOS", "TABLETS", "TELEVISAO"]
SERIES_CURTO = {"2A": "2A", "3A": "3A", "SETUPS": "Setups", "CARRINHOS": "Carrinhos",
                "TABLETS": "Tablets", "TELEVISAO": "Televisão"}
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]
OPERACOES = {"criacao": "cadastrou", "edicao": "alterou", "exclusao": "excluiu"}

# Perguntas
QTD = r"\b(quantos|quantas|quantidade|total|numero de|qtd|qtde|contar|conta quantos|qntos|qtos)\b"
LISTA = r"\b(quais|liste|listar|lista|mostre|mostra|mostrar|exiba|ver todos|veja|relacione|me diga quais|diga quais|quero ver|me mostre)\b"
EXISTE = r"\b(tem algum|tem alguma|existe algum|existe alguma|existem|ha algum|ha alguma|ha equipamento|tem equipamento|possui algum|possui alguma|ainda tem|sobrou|existe)\b"
MAIS = r"\b(mais|maior|maioria|principal|predominante|lider|topo)\b"
MENOS = r"\b(menos|menor|minoria|raro|pouco|poucos)\b"
PCT = r"(porcent|percentual|\bpct\b|%)"
DISTR = r"\b(por (local|locais|tipo|tipos|marca|marcas|modelo|categoria|serie|turma|situacao|ano|sala|salas|responsavel)|em cada|cada (local|tipo|marca|categoria|sala)|distribuicao|distribuidos|separados por|agrupados por|divididos por|de cada)\b"
RESUMO = r"\b(resumo|resuma|panorama|visao geral|situacao geral|como estamos|como esta (o )?(inventario|tudo|geral)|como estao (os )?(equipamentos|ativos)|me atualiza|me atualize|status geral|balanco|relatorio rapido|retrato)\b"
MARCADOR_AJUDA = r"\b(como|onde|o que e|o que sao|o que significa|para que serve|pra que serve|qual a funcao|me explica|explique|explica|ensina|ensine|passo a passo|tutorial|ajuda com|duvida|nao consigo|nao funciona|nao esta funcionando|deu erro)\b"
SIM = r"(sim|pode|claro|quero|manda|isso|por favor|pf|aham|uhum|ok|beleza|bora|vai|com certeza|pode ser|positivo|show|quero sim|pode sim|manda ver|sim por favor|sim quero|pode mandar|liste|lista|mostra|mostre)"
NAO = r"(nao|nao obrigado|nao precisa|deixa|deixa pra la|agora nao|depois|por enquanto nao|nope|nao quero|nem precisa)"
MAIS_ITENS = r"(mostra mais|mostre mais|mais|continua|continue|proximos|proxima|proxima pagina|mais itens|tem mais|e os outros|os outros|ver mais|me mostra mais|o resto|e o resto|segue)"

# Palavras que podem aparecer depois de "no/na/em" sem ser o nome de um local
IGNORAR_LOCAL = {
    "uso", "geral", "total", "todos", "todas", "cada", "sistema", "banco", "estoque", "inventario", "escola",
    "fim", "momento", "dados", "cadastro", "cadastrado", "cadastrados", "cadastradas", "uma", "um", "salas",
    "sala", "locais", "local", "painel", "planilha", "excel", "historico", "mochila", "mochilas", "carregador",
    "ordem", "alguma", "algum", "outra", "outro", "hoje", "ontem", "semana", "mes", "ano", "dia", "meio",
    "vez", "caso", "base", "site", "tela", "pagina", "lista", "tabela", "celular", "computador", "qual",
    "quais", "boa", "bom", "que", "como", "primeiro", "segundo", "ultimo", "resumo", "conjunto", "momentos",
    "equipamentos", "equipamento", "ativos", "itens", "aparelhos", "computadores", "maquinas", "pessoas", "alunos",
    "professores", "turmas", "ordem", "estado", "situacao", "cadastro", "inventario",
}
FIRST_TOKEN_IGNORADO = {"todos", "todas", "alunos", "outros", "nenhum", "professor", "aluno"}

# Domínio: palavras que o corretor de digitação conhece (já sem acento)
VOCAB_ALVO = [
    "quantos", "quantas", "quantidade", "equipamentos", "equipamento", "notebooks", "notebook", "tablets", "tablet",
    "televisoes", "televisao", "setups", "carrinhos", "criticos", "critico", "situacao", "historico", "estatisticas",
    "estatistica", "responsavel", "responsaveis", "mochila", "carregador", "porcentagem", "percentual", "locais",
    "marcas", "modelos", "categoria", "categorias", "armario", "computadores", "computador", "obrigado", "obrigada",
    "parabens", "inventario", "administrador", "visitante", "planilha", "resumo", "panorama", "alteracoes",
    "alteracao", "ultimas", "informacoes", "informacao", "sistema", "relatorio", "distribuicao", "curiosidade",
    "dashboard", "painel", "backup", "senha", "administradores", "visitantes", "usuarios", "carregadores", "mochilas",
    "planilhas", "senhas", "responsavel", "informacoes", "equipamentos", "relatorios", "etiquetas", "estatisticas",
]
PALAVRAS_VAZIAS = {"de", "do", "da", "dos", "das", "a", "o", "os", "as", "para", "pra", "um", "uma", "no", "na", "em", "e", "se"}
STOP_CORRECAO = {"quanto", "quando", "quanta", "qualquer", "quarto", "outros", "outras"}


def norm(txt):
    t = unicodedata.normalize("NFD", str(txt or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9\-/%? ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


ABREVIACOES = {
    "uzo": "uso", "uzando": "usando", "kantos": "quantos", "quantus": "quantos", "qntos": "quantos", "qtos": "quantos",
    "qntas": "quantas", "qtas": "quantas", "qts": "quantos", "oq": "o que", "pq": "porque", "vc": "voce", "vcs": "voces",
    "tbm": "tambem", "tb": "tambem", "blz": "beleza", "obg": "obrigado", "vlw": "valeu", "pfv": "por favor",
    "naum": "nao", "eh": "e", "tds": "todos", "mto": "muito", "msm": "mesmo", "hj": "hoje", "loca": "local",
    "mostar": "mostrar", "mostrr": "mostrar", "listr": "listar", "equip": "equipamentos", "equips": "equipamentos",
    "notebok": "notebook", "tabelt": "tablet", "criticos": "criticos", "dnv": "de novo", "agr": "agora",
}


def squash(t):
    """Tira zeros à esquerda ("sala 06" vira "sala 6") para comparar números."""
    return re.sub(r"(?<![a-z0-9])0+(\d)", r"\1", t)


def chave_natural(texto):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", norm(texto))]


def palavra(termo):
    return rf"(?<![a-z0-9]){re.escape(termo)}(?![a-z0-9])"


def plural_tipo(tipo, n):
    s = tipo.lower()
    if n == 1:
        return s
    if s.endswith("ão"):
        return s[:-2] + "ões"
    return s if s.endswith("s") else s + "s"


def em_local(local):
    prim = norm(local).split()[0] if norm(local) else ""
    prep = {"sala": "na", "salas": "nas", "armario": "no", "laboratorio": "no", "biblioteca": "na",
            "quadra": "na", "patio": "no", "auditorio": "no", "secretaria": "na", "diretoria": "na"}.get(prim, "em")
    return f"{prep} {local}"


def num_br(x):
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    if isinstance(x, float):
        return f"{x:.6f}".rstrip("0").rstrip(".").replace(".", ",")
    return str(x)


def pct(n, total):
    if not total:
        return "0%"
    return num_br(round(n * 100 / total, 1)) + "%"


SINONIMOS_TIPO = {
    "notebook": ["notebook", "notebooks", "note", "notes", "laptop", "laptops", "portatil", "portateis"],
    "tablet": ["tablet", "tablets", "tabletes"],
    "setup": ["setup", "setups", "set up"],
    "televisao": ["televisao", "televisoes", "tv", "tvs", "televisor", "televisores"],
}


class Base:
    """Dados que o assistente consulta (montados pelo servidor a cada pergunta)."""

    def __init__(self, ativos, historico=None, hist_total=0, hist_hoje=0, escola="", sigla="", admins=None):
        self.ativos = ativos
        self.admins = list(admins or [])
        self.hist = historico or []
        self.hist_total, self.hist_hoje = hist_total, hist_hoje
        self.escola = escola or "escola"
        self.sigla = sigla or self.escola
        self.tipos = sorted({a["tipo"] for a in ativos if a["tipo"]}, key=norm)
        self.locais = sorted({a["local"] for a in ativos if a["local"]}, key=norm)
        self.marcas = sorted({a["marca"] for a in ativos if a["marca"]}, key=norm)
        self.modelos = sorted({a["modelo"] for a in ativos if a["modelo"]}, key=norm)
        donos = set()
        for a in ativos:
            for o in (a["owner_1"], a["owner_2"]):
                if o:
                    donos.add(o)
        self.donos = sorted(donos, key=norm)
        self.por_id = {}
        for a in ativos:
            self.por_id.setdefault(squash(norm(a["id_computer"])), []).append(a)
        self.sin_tipo = {t: SINONIMOS_TIPO.get(norm(t)) or [norm(t), norm(t) + "s", norm(t) + "es"] for t in self.tipos}
        generico = {"sala", "salas", "local", "area", "de", "do", "da", "dos", "das"}
        self.tok_local = {}
        for loc in self.locais:
            for w in norm(loc).split():
                if len(w) >= 4 and w not in generico and not w.isdigit():
                    self.tok_local.setdefault(w, set()).add(loc)
        self.conhecidas = set()
        for lista in (self.tipos, self.locais, self.marcas, self.modelos, self.donos):
            for x in lista:
                self.conhecidas.update(norm(x).split())
        for sins in self.sin_tipo.values():
            self.conhecidas.update(sins)
        self.alvo_correcao = sorted(set(VOCAB_ALVO) | {w for w in self.conhecidas if len(w) >= 5})

    def corrigir(self, t):
        """Corrige erros comuns de digitação em palavras do domínio (notbook -> notebook)."""
        saida = []
        for w in t.split():
            if w in ABREVIACOES:
                saida.append(ABREVIACOES[w])
                continue
            if (len(w) < 6 or w in self.conhecidas or w in VOCAB_ALVO or w in STOP_CORRECAO
                    or not w.isalpha()):
                saida.append(w)
                continue
            perto = [x for x in difflib.get_close_matches(w, self.alvo_correcao, n=3, cutoff=0.86) if x[0] == w[0]]
            saida.append(perto[0] if perto else w)
        return " ".join(saida)


def aplica(a, F):
    if F.get("tipos") and a["tipo"] not in F["tipos"]:
        return False
    if F.get("locais") and a["local"] not in F["locais"]:
        return False
    if F.get("serie") and a["serie_id"] != F["serie"]:
        return False
    if F.get("situacao") and a["situacao"] != F["situacao"]:
        return False
    if F.get("critico") and a["criticidade"] != "Sim":
        return False
    if F.get("mochila") and a["mochila"] != F["mochila"]:
        return False
    if F.get("marcas") and a["marca"] not in F["marcas"]:
        return False
    if F.get("modelos") and a["modelo"] not in F["modelos"]:
        return False
    if F.get("pessoas") and not ({a["owner_1"], a["owner_2"]} & set(F["pessoas"])):
        return False
    return True


CHAVES_FILTRO = ("tipos", "locais", "serie", "situacao", "critico", "mochila", "marcas", "modelos", "pessoas")


FEMININOS = {"televisão", "televisao"}


def descrever(F, n):
    tipos = F.get("tipos") or []
    nome = " e ".join(plural_tipo(t, n) for t in tipos) if tipos else ("equipamento" if n == 1 else "equipamentos")
    partes = [nome]
    if F.get("critico"):
        fem = len(tipos) == 1 and tipos[0].lower() in FEMININOS
        partes.append(("crítica" if fem else "crítico") if n == 1 else ("críticas" if fem else "críticos"))
    if F.get("situacao") == "Em uso":
        partes.append("em uso")
    elif F.get("situacao") == "Não em uso":
        partes.append("fora de uso")
    if F.get("mochila") == "Sim":
        partes.append("com mochila")
    elif F.get("mochila") == "Não":
        partes.append("sem mochila")
    if F.get("marcas"):
        partes.append("da marca " + " ou ".join(F["marcas"]))
    if F.get("modelos"):
        partes.append("do modelo " + " ou ".join(F["modelos"]))
    if F.get("pessoas"):
        partes.append("de " + " ou ".join(F["pessoas"]))
    if F.get("locais"):
        partes.append(" ou ".join(em_local(x) for x in F["locais"]))
    if F.get("serie"):
        partes.append("na categoria " + SERIES_CURTO.get(F["serie"], F["serie"]))
    return " ".join(partes)


def filtro_para_link(F):
    """Traduz os filtros para os do Inventário. Devolve None se não der para representar."""
    saida = {}
    if len(F.get("tipos") or []) > 1 or len(F.get("locais") or []) > 1:
        return None
    textos = [x for x in (F.get("marcas") or []) + (F.get("modelos") or []) + (F.get("pessoas") or [])]
    if len(textos) > 1:
        return None
    if F.get("tipos"):
        saida["tipo"] = F["tipos"][0]
    if F.get("locais"):
        saida["local"] = F["locais"][0]
    if F.get("serie"):
        saida["serie"] = F["serie"]
    if F.get("situacao"):
        saida["situacao"] = F["situacao"]
    if F.get("critico"):
        saida["criticidade"] = "Sim"
    if F.get("mochila"):
        saida["mochila"] = F["mochila"]
    if textos:
        saida["q"] = textos[0]
    return saida


def item_chip(a):
    return {"id": a["id"], "label": f"{a['id_computer']} · {a['serie_id']}"}


def linha(a, curto=False):
    if curto:   # todos os itens da lista são do mesmo modelo: não repete tipo, marca e modelo
        return (f"• **{a['id_computer']}** ({SERIES_CURTO.get(a['serie_id'], a['serie_id'])})"
                f" · {a['local'] or 'sem local'} · {a['situacao']}")
    return (f"• **{a['id_computer']}** ({a['serie_id']}): {a['tipo']} {a['marca']} {a['modelo']}".rstrip()
            + f" · {a['local'] or 'sem local'} · {a['situacao']}")


# Contas -----------------------------------------------------------------------

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Mod: operator.mod}


def _avaliar(no):
    if isinstance(no, ast.Expression):
        return _avaliar(no.body)
    if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
        return no.value
    if isinstance(no, ast.BinOp) and type(no.op) in _OPS:
        return _OPS[type(no.op)](_avaliar(no.left), _avaliar(no.right))
    if isinstance(no, ast.UnaryOp) and isinstance(no.op, (ast.UAdd, ast.USub)):
        v = _avaliar(no.operand)
        return v if isinstance(no.op, ast.UAdd) else -v
    raise ValueError("expressão não permitida")


def calcular(texto, pediu=False):
    """Devolve (resultado, descrição) para contas simples escritas no texto, ou None."""
    s = texto.lower().replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:de|do|da)\s*(\d+(?:\.\d+)?)", s)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return a * b / 100, f"{num_br(a)}% de {num_br(b)}"
    m = re.search(r"raiz\s*(?:quadrada)?\s*(?:de)?\s*(\d+(?:\.\d+)?)", s)
    if m:
        v = float(m.group(1))
        return math.sqrt(v), f"raiz quadrada de {num_br(v)}"
    s = re.sub(r"(?<=\d)\s*[x×]\s*(?=\d)", "*", s)
    s = s.replace("÷", "/").replace("dividido por", "/").replace("vezes", "*").replace("multiplicado por", "*")
    s = re.sub(r"(?<=\d)\s+mais\s+(?=\d)", " + ", s)
    s = re.sub(r"(?<=\d)\s+menos\s+(?=\d)", " - ", s)
    achados = re.findall(r"[\d\s.+\-*/()]{3,}", s)
    for trecho in sorted(achados, key=len, reverse=True):
        trecho = trecho.strip()
        if not re.search(r"\d\s*[+\-*/]\s*[\d(]", trecho) or len(trecho) > 40:
            continue
        try:
            valor = _avaliar(ast.parse(trecho, mode="eval"))
        except ZeroDivisionError:
            return "div0", trecho
        except (SyntaxError, ValueError):
            continue
        compacto = re.sub(r"\s+", "", s)
        if not pediu and len(re.sub(r"\s+", "", trecho)) < 0.5 * len(compacto):
            continue
        return valor, trecho.replace("*", " × ").replace("/", " ÷ ").replace("  ", " ")
    return None


# Contexto ------------------------------------------------------------------------

def _lista_str(v, n=5, tam=60):
    return [x for x in v[:n] if isinstance(x, str) and 0 < len(x) <= tam] if isinstance(v, list) else []


def _limpar_filtro(f):
    if not isinstance(f, dict):
        return {}
    out = {}
    for k in ("tipos", "locais", "marcas", "modelos", "pessoas"):
        v = _lista_str(f.get(k))
        if v:
            out[k] = v
    if f.get("serie") in SERIES_ORDEM:
        out["serie"] = f["serie"]
    if f.get("situacao") in ("Em uso", "Não em uso"):
        out["situacao"] = f["situacao"]
    if f.get("critico") is True:
        out["critico"] = True
    if f.get("mochila") in ("Sim", "Não"):
        out["mochila"] = f["mochila"]
    return out


def limpar_contexto(c):
    """Aceita do navegador apenas o que o assistente guarda, nos formatos esperados."""
    if not isinstance(c, dict):
        return {}
    out = {}
    f = _limpar_filtro(c.get("f"))
    if f:
        out["f"] = f
    if isinstance(c.get("nome"), str) and re.fullmatch(r"[A-Za-zÀ-ÿ' ]{1,30}", c["nome"].strip() or "-"):
        out["nome"] = c["nome"].strip()
    if isinstance(c.get("ultima"), str):
        out["ultima"] = c["ultima"][:400]
    if c.get("cand_attr") in ("tudo", "onde", "quem", "carregador", "mochila", "situacao", "critico", "modelo", "categoria"):
        out["cand_attr"] = c["cand_attr"]
    if isinstance(c.get("ultimo_id"), int) and not isinstance(c["ultimo_id"], bool):
        out["ultimo_id"] = c["ultimo_id"]
    if isinstance(c.get("cand"), list):
        out["cand"] = [x for x in c["cand"][:12] if isinstance(x, int) and not isinstance(x, bool)]
    of = c.get("oferta")
    if isinstance(of, dict) and of.get("acao") in ("listar", "motivar", "piada", "resumo"):
        out["oferta"] = {"acao": of["acao"], "f": _limpar_filtro(of.get("f"))}
    li = c.get("lista")
    if isinstance(li, dict) and isinstance(li.get("offset"), int) and 0 <= li["offset"] < 100000:
        out["lista"] = {"f": _limpar_filtro(li.get("f")), "offset": li["offset"]}
    if c.get("saudou") is True:
        out["saudou"] = True
    fun = c.get("fun")
    if isinstance(fun, dict) and fun.get("tipo") in ("piada", "curiosidade", "motivacao", "dica") and isinstance(fun.get("i"), int):
        out["fun"] = {"tipo": fun["tipo"], "i": fun["i"]}
    return out


# Conversa ----------------------------------------------------------------------

class Conversa:
    def __init__(self, base, msg, contexto, usuario, perfil, agora, rnd):
        self.base = base
        self.original = (msg or "").strip()
        self.tq = norm(self.original)                     # mantém "?"
        self.t = self.base.corrigir(self.tq.replace("?", " ").strip())
        self.t = re.sub(r"\s+", " ", self.t)
        self.tcq = re.sub(r"\s*\?\s*", "?", self.base.corrigir(self.tq.replace("?", " ? ")))
        self.ts = squash(self.t)
        self.palavras = len(self.t.split())
        self.ctx = contexto or {}
        self.out = dict(self.ctx)
        self.usuario = usuario
        self.perfil = perfil
        self.agora = agora or datetime.now()
        self.rnd = rnd or random
        self.E = self.entidades()
        self.dados_forte = bool(re.search(QTD, self.t) or re.search(LISTA, self.t) or re.search(EXISTE, self.t)
                                or re.search(PCT, self.t) or re.search(DISTR, self.t))
        self.seguimento = self.detectar_seguimento()
        self.topico = self.melhor_topico()

    # ---- utilidades -------------------------------------------------------
    def escolher(self, lista):
        return self.rnd.choice(lista)

    def quem(self):
        if self.ctx.get("nome"):
            return self.ctx["nome"]
        if self.perfil == "admin" and self.usuario:
            return self.usuario
        return None

    def R(self, texto, items=None, links=None, sug=None):
        return {"reply": texto, "items": items or [], "links": links or [], "suggestions": sug}

    def sugestoes_padrao(self):
        return ["Faça um resumo dos equipamentos", "Quantos notebooks estão em uso?",
                "Qual local tem mais equipamentos?", "Como cadastrar?", "Me conta uma curiosidade"]

    def nome_vocativo(self):
        n = self.quem()
        return f", {n}" if n else ""

    # ---- entidades ----------------------------------------------------------
    def entidades(self):
        b, t, ts = self.base, self.t, self.ts
        E = {k: [] if k in ("tipos", "locais", "marcas", "modelos", "pessoas") else None for k in CHAVES_FILTRO}
        E["critico"] = False
        achados = []
        for tipo in b.tipos:
            for sin in b.sin_tipo[tipo]:
                m = re.search(palavra(sin), t)
                if m:
                    achados.append((m.start(), tipo))
                    break
        E["tipos"] = [x for _, x in sorted(achados)]
        E["generico_pc"] = False
        if not E["tipos"] and re.search(r"\b(computador|computadores|pc|pcs|maquina|maquinas)\b", t):
            E["tipos"] = [x for x in ("Notebook", "Setup") if x in b.tipos]
            E["generico_pc"] = bool(E["tipos"])
        for loc in b.locais:
            nl = squash(norm(loc))
            alternativas = {nl, nl.replace("salas", "sala"), nl.replace("sala de", "salas de")}
            if any(re.search(palavra(a), ts) for a in alternativas):
                E["locais"].append(loc)
        if not E["locais"]:
            for w in t.split():
                for loc in b.tok_local.get(w, ()):
                    if loc not in E["locais"]:
                        E["locais"].append(loc)
        if re.search(r"(?<![a-z0-9])(2 ?a|2o ano|2 ano|segundo ano|segunda serie)(?![a-z0-9])", t):
            E["serie"] = "2A"
        elif re.search(r"(?<![a-z0-9])(3 ?a|3o ano|3 ano|terceiro ano|terceira serie)(?![a-z0-9])", t):
            E["serie"] = "3A"
        elif re.search(r"\bcarrinhos?\b", t):
            E["serie"] = "CARRINHOS"
        if re.search(r"(nao em uso|fora de uso|sem uso|parad[oa]s?\b|ocios[oa]s?|disponiv|livres?\b|guardad[oa]s?|nao usad|desativad|nao utilizad|sobrando)", t):
            E["situacao"] = "Não em uso"
        elif re.search(r"(em uso|usando|sendo usad|sendo utilizad|em utilizacao|ocupad[oa]s?|funcionando)", t):
            E["situacao"] = "Em uso"
        E["critico"] = bool(re.search(r"\bcritic", t))
        if re.search(r"\b(com mochila|tem mochila|possui mochila|tem bolsa)\b", t):
            E["mochila"] = "Sim"
        elif re.search(r"\b(sem mochila|nao tem mochila|nao possui mochila|sem bolsa)\b", t):
            E["mochila"] = "Não"
        for marca in b.marcas:
            if re.search(palavra(norm(marca)), t):
                E["marcas"].append(marca)
        for modelo in b.modelos:
            nm = norm(modelo)
            tokens = [w for w in nm.split() if len(w) >= 4 and re.search(r"\d", w)]
            if (len(nm) >= 6 and re.search(palavra(nm), t)) or any(re.search(palavra(w), t) for w in tokens):
                E["modelos"].append(modelo)
        # pessoas: nome completo ou primeiro nome
        for dono in b.donos:
            nd = norm(dono)
            if len(nd.split()) >= 2 and re.search(palavra(nd), t):
                E["pessoas"].append(dono)
        if not E["pessoas"]:
            for w in set(t.split()):
                if len(w) >= 3 and w not in FIRST_TOKEN_IGNORADO and w not in b.tok_local:
                    for dono in b.donos:
                        pt = norm(dono).split()
                        if pt and pt[0] == w and dono not in E["pessoas"]:
                            E["pessoas"].append(dono)
        return E

    def so_entidades(self):
        E = self.E
        return any(E[k] for k in CHAVES_FILTRO)

    def detectar_seguimento(self):
        t = self.t
        if re.match(r"^(e|entao|agora|mas|so|apenas|somente|tambem)\b", t):
            return True
        if re.search(r"\b(desses|dessas|deles|delas|neles|nelas|nesses|nessas|destes|deste|desse|dai)\b", t):
            return True
        if (self.ctx.get("f") and not self.so_entidades() and self.palavras <= 5
                and not re.search(r"\b(equipamentos|ativos|itens|aparelhos)\b", t)
                and (re.search(LISTA, t) or re.search(QTD, t))):
            return True
        return (self.palavras <= 3 and self.so_entidades() and not self.dados_forte
                and not re.search(r"\b(equipamentos|ativos|itens|aparelhos)\b", t))

    def melhor_topico(self):
        melhor, pontos = None, 0
        tokens = set(self.t.split())
        for item in AJUDA:
            for chave in item["chaves"]:
                if re.search(palavra(chave), self.t):
                    p = len(chave.split()) * 10 + len(chave)
                elif len(chave.split()) >= 2:
                    # todas as palavras da expressão aparecem na pergunta, mesmo separadas
                    uteis = [w for w in chave.split() if w not in PALAVRAS_VAZIAS]
                    p = (len(uteis) * 5 + len(chave) // 2) if len(uteis) >= 2 and all(w in tokens for w in uteis) else 0
                else:
                    p = 0
                if p > pontos:
                    melhor, pontos = item, p
        return melhor

    # ---- tratadores ---------------------------------------------------------
    def responder(self):
        for h in (self.h_pendente, self.h_nome, self.h_saudacao, self.h_social, self.h_tempo, self.h_calculo,
                  self.h_diversao, self.h_historico, self.h_equipamento, self.h_ajuda_marcada, self.h_catalogo,
                  self.h_pessoa, self.h_dados, self.h_ajuda_livre):
            r = h()
            if r:
                return r
        return self.fallback()

    # Respostas a ofertas e continuações ("sim", "mostra mais")
    def h_pendente(self):
        t, ctx = self.t, self.ctx
        if ctx.get("cand") and (self.E["serie"] or self.E["tipos"]):
            escolhidos = [a for a in self.base.ativos if a["id"] in ctx["cand"]
                          and (not self.E["serie"] or a["serie_id"] == self.E["serie"])
                          and (not self.E["tipos"] or a["tipo"] in self.E["tipos"])]
            if len(escolhidos) == 1:
                return self.detalhe(escolhidos[0], ctx.get("cand_attr") or "tudo")
        if re.fullmatch(MAIS_ITENS, t) and not ctx.get("lista") and not ctx.get("fun"):
            return self.R("Não tenho mais itens para mostrar agora. Quer fazer outra consulta?")
        if ctx.get("lista") and re.fullmatch(MAIS_ITENS, t):
            F, off = ctx["lista"].get("f") or {}, ctx["lista"].get("offset", 0)
            return self.listar(F, off)
        if ctx.get("oferta"):
            of = ctx["oferta"]
            if re.fullmatch(SIM, t):
                self.out.pop("oferta", None)
                if of["acao"] == "listar":
                    return self.listar(of.get("f") or {}, 0)
                if of["acao"] == "motivar":
                    return self.fun("motivacao")
                if of["acao"] == "piada":
                    return self.fun("piada")
                if of["acao"] == "resumo":
                    return self.resumo()
            if re.fullmatch(NAO, t):
                self.out.pop("oferta", None)
                return self.R(self.escolher(["Tudo bem! Se mudar de ideia, é só falar.", "Sem problema. Estou por aqui se precisar."]))
        if ctx.get("fun") and re.fullmatch(r"(outra|outro|mais uma|mais um|outra piada|outro fato|de novo|quero outra|quero outro|mais|manda outra|manda outro)", t):
            return self.fun(ctx["fun"]["tipo"])
        return None

    def h_nome(self):
        t = self.t
        m = re.search(r"\b(?:meu nome e|me chamo|pode me chamar de|me chama de|eu sou o|eu sou a|sou o|sou a)\s+([a-z]{2,20})\b", t)
        if m and not self.dados_forte:
            nome = self.nome_original(m.group(1))
            if nome and nome.lower() not in {"o", "a", "um", "uma", "admin", "administrador", "visitante"}:
                self.out["nome"] = nome
                return self.R(self.escolher([f"Prazer, {nome}! Vou lembrar do seu nome durante esta conversa. Em que posso ajudar?",
                                             f"Muito prazer, {nome}! Pode contar comigo."]))
        if re.search(r"\b(qual (e )?(o )?meu nome|como (eu )?me chamo|quem sou eu|sabe meu nome|lembra do meu nome)\b", t):
            if self.ctx.get("nome"):
                return self.R(f"Você me disse que se chama {self.ctx['nome']}.")
            if self.perfil == "admin" and self.usuario:
                return self.R(f"Você está logado como **{self.usuario}**, administrador. Se preferir outro nome na conversa, diga: \"meu nome é...\".")
            if self.perfil != "admin":
                return self.R("Você está como **visitante**. Ainda não sei o seu nome; se quiser, diga: \"meu nome é...\".")
            return self.R("Ainda não sei o seu nome. Se quiser, diga: \"meu nome é...\".")
        if re.search(r"\b(quem (sao|e) (os |o )?(administradores|admins|admin)|quais (sao )?(os )?administradores|quantos administradores|lista de administradores)\b", t):
            if self.perfil != "admin":
                return self.R("A lista de administradores é visível só para os próprios administradores.")
            if not self.base.admins:
                return self.R("Não tenho a lista de administradores agora.")
            return self.R(f"Os administradores são **{len(self.base.admins)}**: " + ", ".join(self.base.admins) + ".")
        if re.search(r"\b(qual (e )?(o )?meu perfil|sou admin|sou administrador|que perfil eu tenho|posso editar|tenho permissao|minhas permissoes|sou visitante)\b", t):
            if self.perfil == "admin":
                return self.R("Você está como **administrador**: pode cadastrar, editar, excluir, exportar e ver o histórico.")
            return self.R("Você está como **visitante**: pode consultar tudo, mas não cadastrar, editar, excluir ou exportar. Para isso, é preciso entrar com uma conta de administrador.")
        return None

    def nome_original(self, token):
        for w in re.findall(r"[A-Za-zÀ-ÿ']+", self.original):
            if norm(w) == token:
                return w.capitalize()
        return token.capitalize()

    def h_saudacao(self):
        t = self.t
        if self.palavras > 6 or self.dados_forte:
            return None
        if not re.match(r"^(oi+|ola+|opa|eae|e ai|fala|salve|hey|hello|oie|bom dia|boa tarde|boa noite|ola tudo bem|oi tudo bem|iai|oiee+)\b", t):
            return None
        voc = self.nome_vocativo()
        hora = self.agora.hour
        periodo = "Bom dia" if hora < 12 else ("Boa tarde" if hora < 18 else "Boa noite")
        m = re.search(r"\b(bom dia|boa tarde|boa noite)\b", t)
        saud = m.group(1).capitalize() if m else periodo
        if re.search(r"tudo bem|como vai|como esta", t):
            texto = f"{saud}{voc}! Tudo ótimo por aqui, obrigado por perguntar. Em que posso ajudar?"
        elif self.ctx.get("saudou"):
            texto = self.escolher([f"Oi de novo{voc}! No que posso ajudar?", f"Olá{voc}! Pode falar."])
        else:
            texto = self.escolher([
                f"{saud}{voc}! Sou o assistente do Ativos Escolares. Como posso ajudar?",
                f"{saud}{voc}! Pode perguntar sobre os equipamentos ou sobre o sistema.",
                f"{saud}{voc}! O que você precisa hoje?",
            ])
        self.out["saudou"] = True
        return self.R(texto, sug=self.sugestoes_padrao())

    def h_social(self):
        if self.dados_forte:
            return None
        for nome, padrao, respostas in SOCIAL:
            if nome in ("sim_solto", "nao_solto") and self.ctx.get("oferta"):
                continue
            if not re.search(padrao, self.tcq):
                continue
            if nome == "repetir":
                if self.ctx.get("ultima"):
                    return self.R("Claro, repetindo: " + self.ctx["ultima"])
                return self.R("Ainda não falei nada para repetir. Pode perguntar!")
            if nome == "capacidades":
                return self.R(CAPACIDADES, sug=self.sugestoes_padrao())
            if nome == "nao_entendi" and self.ctx.get("ultima"):
                return self.R("Desculpe, vou tentar explicar de outro jeito. A última coisa que eu disse foi: "
                              + self.ctx["ultima"] + "\nQual parte ficou confusa?")
            if nome in ("estou_mal",):
                self.out["oferta"] = {"acao": "motivar", "f": {}}
            if nome == "risada":
                self.out["oferta"] = {"acao": "piada", "f": {}}
            texto = self.escolher(respostas).format(escola=self.base.escola)
            if nome == "agradecimento":
                n = self.quem()
                if n and self.rnd.random() < 0.4:
                    texto = texto.replace("!", f", {n}!", 1) if "!" in texto else texto
            return self.R(texto, sug=self.sugestoes_padrao() if nome in ("despedida",) else None)
        return None

    def h_tempo(self):
        t, ag = self.t, self.agora
        pede_hora = re.search(r"\b(que horas|horas sao|hora e agora|que hora|horario atual|hora atual|me diz as horas|tem horas)\b", t)
        pede_data = re.search(r"\b(que dia (e )?hoje|data de hoje|dia de hoje|qual (e )?a data|que data|em que dia estamos|hoje e que dia|dia da semana|que dia da semana|que mes|em que mes|que ano|em que ano|qual (e )?o ano|qual (e )?o mes)\b", t)
        if not (pede_hora or pede_data):
            return None
        data = f"{DIAS[ag.weekday()]}, {ag.day} de {MESES[ag.month - 1]} de {ag.year}"
        hora = f"{ag.hour:02d}:{ag.minute:02d}"
        if pede_hora and pede_data:
            return self.R(f"Hoje é {data}, e agora são {hora}.")
        if pede_hora:
            return self.R(f"Agora são {hora}.")
        return self.R(f"Hoje é {data}.")

    def h_calculo(self):
        orig = self.original
        if not re.search(r"\d", orig):
            return None
        pede = re.search(r"\b(quanto e|quanto da|quanto fica|calcula|calcule|calcular|conta de|resultado de|resolve|resolva|soma|subtrai|multiplica|divide)\b", self.t)
        tem_equip = self.so_entidades() or re.search(r"\b(equipamento|ativo|id|numero)\b", self.t)
        if tem_equip and not pede:
            return None
        r = calcular(orig, bool(pede))
        if not r:
            return None
        valor, expr = r
        if valor == "div0":
            return self.R("Não dá para dividir por zero. Tente outra conta!")
        if isinstance(valor, float) and (math.isinf(valor) or math.isnan(valor)):
            return None
        return self.R(f"{expr.strip()} = **{num_br(round(valor, 6) if isinstance(valor, float) else valor)}**")

    def fun(self, tipo):
        fontes = {"piada": PIADAS, "curiosidade": CURIOSIDADES, "motivacao": MOTIVACAO, "dica": DICAS}
        lista = fontes[tipo]
        ult = (self.ctx.get("fun") or {}).get("i", -1) if (self.ctx.get("fun") or {}).get("tipo") == tipo else -1
        idx = self.rnd.randrange(len(lista))
        if len(lista) > 1 and idx == ult:
            idx = (idx + 1) % len(lista)
        self.out["fun"] = {"tipo": tipo, "i": idx}
        extra = {"piada": "\n\nQuer outra?", "curiosidade": "\n\nQuer mais uma curiosidade?", "motivacao": "", "dica": ""}[tipo]
        return self.R(lista[idx] + extra)

    def h_diversao(self):
        t = self.t
        if self.dados_forte and not re.search(r"\b(piada|curiosidade)\b", t):
            return None
        if re.search(r"\b(piada|piadas|me faz rir|faz rir|me faca rir|algo engracado|conta uma graca|humor|brincadeira)\b", t):
            return self.fun("piada")
        if re.search(r"\b(curiosidade|curiosidades|fato curioso|voce sabia|sabia que|me conta algo|conta alguma coisa|algo interessante|me surpreenda|me conta uma novidade|fato interessante)\b", t):
            return self.fun("curiosidade")
        if re.search(r"\b(me motiva|motivacao|frase de animo|me inspira|inspiracao|palavras de incentivo|me incentiva|frase motivacional|me da forca)\b", t):
            return self.fun("motivacao")
        if re.search(r"\b(dica|dicas|conselho|conselhos|boas praticas)\b", t):
            return self.fun("dica")
        return None

    # Histórico
    def h_historico(self):
        t = self.t
        if not re.search(r"((alteracoes|mudancas|historico|edicoes) (de|em|do dia|no dia) \d{1,2}/\d{1,2}|ultim[ao]s? (alteracao|alteracoes|mudanca|mudancas|modificacao|modificacoes|edicao|edicoes)|o que mudou|o que foi (alterado|mudado|editado)|quem (alterou|mexeu|editou|cadastrou|excluiu|apagou|mudou|modificou)|historico recente|alteracoes (de )?hoje|houve (alteracao|mudanca)|mudancas recentes|quantas alteracoes|quantas mudancas|ultima vez que|movimentacao|o que aconteceu)", t):
            return None
        b = self.base
        data = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", self.original)
        if data:
            dia, mes, ano = int(data.group(1)), int(data.group(2)), data.group(3)
            ano = int(ano) + 2000 if ano and len(ano) == 2 else (int(ano) if ano else self.agora.year)
            alvo = f"{ano:04d}-{mes:02d}-{dia:02d}"
            do_dia = [h for h in b.hist if h["criado_em"].startswith(alvo)]
            rotulo = f"{dia:02d}/{mes:02d}/{ano}"
            if not do_dia:
                return self.R(f"Não encontrei alterações registradas em {rotulo} entre as mais recentes.",
                              links=[{"label": "Abrir Histórico", "view": "historico"}])
            return self.R(f"Em {rotulo} foram **{len(do_dia)}** alterações recentes:\n" + "\n".join("• " + self.frase_hist(h) for h in do_dia[:6]),
                          links=[{"label": "Abrir Histórico", "view": "historico"}])
        if re.search(r"\b(quantas (alteracoes|mudancas|edicoes|modificacoes))\b", t):
            if re.search(r"\bhoje\b", t):
                return self.R(f"Hoje foram registradas **{b.hist_hoje}** alterações no histórico.")
            return self.R(f"O histórico tem **{b.hist_total}** registros ao todo, sendo **{b.hist_hoje}** de hoje.")
        if not b.hist:
            return self.R("O histórico ainda está vazio: nenhuma alteração foi registrada. Cadastros, edições e exclusões feitas pelo sistema aparecerão lá.",
                          links=[{"label": "Abrir Histórico", "view": "historico"}])
        if re.search(r"\bhoje\b", t) and not b.hist_hoje:
            return self.R("Hoje ainda não houve nenhuma alteração.", links=[{"label": "Abrir Histórico", "view": "historico"}])
        so_ultima = re.search(r"(ultim[ao] (alteracao|mudanca|modificacao|edicao)|ultima vez|quem (alterou|mexeu|editou|mudou|modificou) (por )?ultimo)", t)
        if so_ultima:
            texto = "A última alteração foi: " + self.frase_hist(b.hist[0])
        else:
            texto = "As alterações mais recentes:\n" + "\n".join("• " + self.frase_hist(h) for h in b.hist[:5])
        return self.R(texto, links=[{"label": "Abrir Histórico", "view": "historico"}])

    def frase_hist(self, h):
        quando = h["criado_em"]
        data = f"{quando[8:10]}/{quando[5:7]}/{quando[0:4]} às {quando[11:16]}"
        nome = f"{h.get('tipo') or 'equipamento'} {h['id_computer']}".strip()
        op = OPERACOES.get(h["operacao"], "alterou")
        if h["operacao"] == "edicao":
            antes, depois = h.get("valor_anterior") or "vazio", h.get("valor_novo") or "vazio"
            return f"**{h['usuario']}** {op} {str(h.get('campo') or 'dados').lower()} de {nome} ({antes} → {depois}) em {data}"
        return f"**{h['usuario']}** {op} {nome} em {data}"

    # Equipamento específico
    def ids_na_mensagem(self):
        gatilhos = {"equipamento", "ativo", "id", "numero", "computador", "notebook", "note", "tablet", "tv", "televisao",
                    "setup", "patrimonio", "plaqueta", "etiqueta", "carrinho", "o", "a", "do", "da", "no", "na",
                    "dele", "dela", "de", "n"}
        toks = self.ts.split()
        achados = []
        for i, tok in enumerate(toks):
            if tok in gatilhos:
                j = i + 1
                if j < len(toks) and toks[j] in ("n", "no", "de", "numero", "id"):
                    j += 1
                if j < len(toks) and toks[j] in self.base.por_id and toks[j] not in achados:
                    achados.append(toks[j])
        for tok in toks:
            if tok in self.base.por_id and tok not in achados and re.search(r"[a-z]", tok) and tok not in ("2a", "3a"):
                achados.append(tok)
        return achados

    def atributo(self):
        t = self.t
        if re.search(r"\b(onde|local|em que sala|qual sala|fica|esta guardad|localizacao|em qual sala|que sala)\b", t):
            return "onde"
        if re.search(r"\b(quem usa|quem utiliza|quem e o responsavel|quem e o dono|responsavel|responsaveis|dono|quem esta com|quem tem|quem fica com|usuario)\b", t):
            return "quem"
        if re.search(r"\b(carregador|fonte|cabo)\b", t):
            return "carregador"
        if re.search(r"\b(mochila|bolsa)\b", t):
            return "mochila"
        if re.search(r"\b(situacao|status|esta em uso|em uso|disponivel|funcionando|esta sendo usado)\b", t):
            return "situacao"
        if re.search(r"\b(critic)", t):
            return "critico"
        if re.search(r"\b(marca|modelo|que equipamento e|que aparelho e|qual a marca|qual o modelo|fabricante)\b", t):
            return "modelo"
        if re.search(r"\b(categoria|serie|turma|grupo)\b", t):
            return "categoria"
        return None

    def h_equipamento(self):
        ids = self.ids_na_mensagem()
        attr = self.atributo()
        eq = []
        if ids:
            for tok in ids:
                eq.extend(self.base.por_id[tok])
            if self.E["serie"]:
                eq = [a for a in eq if a["serie_id"] == self.E["serie"]] or eq
            if self.E["tipos"]:
                eq = [a for a in eq if a["tipo"] in self.E["tipos"]] or eq
            vistos = set()
            eq = [a for a in eq if not (a["id"] in vistos or vistos.add(a["id"]))]
        elif (attr and self.ctx.get("ultimo_id") and self.palavras <= 7 and not self.so_entidades()
              and not self.dados_forte and not (self.topico and self.topico["id"] not in ("mochila", "carregador", "situacao", "critico", "categorias"))):
            eq = [a for a in self.base.ativos if a["id"] == self.ctx["ultimo_id"]]
        if not eq and attr and self.ctx.get("cand") and self.palavras <= 7 and not self.so_entidades():
            pend = [a for a in self.base.ativos if a["id"] in self.ctx["cand"]]
            if pend:
                self.out["cand"] = self.ctx["cand"]
                self.out["cand_attr"] = attr
                return self.R("Antes, preciso saber qual equipamento você quer. Diga a categoria (por exemplo, \"o da 2A\"):\n"
                              + "\n".join(linha(a) for a in pend[:8]), items=[item_chip(a) for a in pend[:8]])
        if not eq:
            return None
        if self.dados_forte and not attr and re.search(QTD, self.t):
            return None
        if len(eq) > 1:
            self.out["cand"] = [a["id"] for a in eq][:12]
            self.out["cand_attr"] = attr or "tudo"
            texto = (f"Encontrei **{len(eq)}** equipamentos com o ID **{eq[0]['id_computer']}**. Qual deles você quer? "
                     "Pode dizer a categoria (por exemplo, \"o da 2A\").\n" + "\n".join(linha(a) for a in eq[:8]))
            return self.R(texto, items=[item_chip(a) for a in eq[:8]])
        return self.detalhe(eq[0], attr or "tudo")

    def detalhe(self, a, attr):
        self.out["ultimo_id"] = a["id"]
        nome = f"{a['tipo'].lower()} **{a['id_computer']}** ({SERIES_CURTO.get(a['serie_id'], a['serie_id'])})".strip()
        donos = [x for x in (a["owner_1"], a["owner_2"]) if x]
        chip = [item_chip(a)]
        if attr == "onde":
            texto = f"O {nome} está em **{a['local']}**." if a["local"] else f"O {nome} não tem local cadastrado."
        elif attr == "quem":
            texto = (f"O {nome} está com **{' e '.join(donos)}**." if donos
                     else f"O {nome} não tem responsáveis cadastrados.")
        elif attr == "carregador":
            texto = (f"O carregador do {nome} está cadastrado como **{a['id_carregator']}**." if a["id_carregator"]
                     else f"O {nome} não tem informação de carregador.")
        elif attr == "mochila":
            texto = (f"Mochila do {nome}: **{a['mochila']}**." if a["mochila"] else f"O {nome} não tem informação de mochila.")
        elif attr == "situacao":
            texto = f"O {nome} está **{a['situacao']}**." if a["situacao"] else f"O {nome} não tem situação cadastrada."
        elif attr == "critico":
            texto = (f"O {nome} é um equipamento **crítico**." if a["criticidade"] == "Sim"
                     else f"O {nome} não está marcado como crítico (criticidade: {a['criticidade'] or 'não informada'}).")
        elif attr == "modelo":
            texto = f"O {nome} é um **{a['marca']} {a['modelo']}**.".replace("  ", " ")
        elif attr == "categoria":
            texto = f"O {nome} é da categoria **{a['serie_rotulo'] if 'serie_rotulo' in a else a['serie_id']}**."
        else:
            partes = [f"Equipamento **{a['id_computer']}** ({a.get('serie_rotulo', a['serie_id'])}): {a['tipo']} {a['marca']} {a['modelo']}.".replace("  ", " "),
                      f"• Local: {a['local'] or 'não informado'}",
                      f"• Situação: {a['situacao'] or 'não informada'}",
                      f"• Responsáveis: {' e '.join(donos) if donos else 'não informados'}",
                      f"• Mochila: {a['mochila'] or 'não informada'} · Carregador: {a['id_carregator'] or 'não informado'}",
                      f"• Criticidade: {a['criticidade'] or 'não informada'}"]
            texto = "\n".join(partes)
        return self.R(texto, items=chip, sug=["E quem usa?", "Onde está?", "Mostre outro equipamento", "Faça um resumo dos equipamentos"])

    # Pessoas
    def h_pessoa(self):
        E = self.E
        if not E["pessoas"]:
            return None
        gatilho = re.search(r"\b(do|da|de|dos|das|com|para|pro|pra|usa|usam|usando|responsavel|responsaveis|dono|equipamentos|equipamento|tem|que)\b", self.t)
        if not (self.palavras <= 4 or gatilho):
            return None
        if re.search(QTD, self.t) or re.search(PCT, self.t) or re.search(DISTR, self.t) or re.search(MAIS, self.t):
            return None
        F = {"pessoas": E["pessoas"]}
        for k in ("tipos", "serie", "locais", "situacao"):
            if E[k]:
                F[k] = E[k]
        achados = [a for a in self.base.ativos if aplica(a, F)]
        nomes = E["pessoas"]
        if not achados:
            return self.R(f"Não encontrei equipamentos em nome de **{' ou '.join(nomes[:3])}**.")
        self.out["f"] = F
        plural = "s" if len(achados) != 1 else ""
        if len(nomes) == 1:
            titulo = f"**{nomes[0]}** aparece como responsável por **{len(achados)}** equipamento{plural}:"
        else:
            titulo = (f"Encontrei **{len(nomes)}** responsáveis com esse nome ({', '.join(nomes[:4])}"
                      f"{'…' if len(nomes) > 4 else ''}). Juntos, aparecem em **{len(achados)}** equipamento{plural}:")
        return self.listar(F, 0, titulo=titulo)

    # Catálogo (listas de locais, tipos, marcas...)
    def h_catalogo(self):
        t, b = self.t, self.base
        if re.search(r"\b(mais|menos|maior|menor)\b", t):
            return None
        quer_qtd = re.search(r"\b(quantos|quantas)\b", t)
        quer_lista = re.search(r"\b(quais|que|liste|lista|mostre|mostra|existem|temos|tem)\b", t)
        if not (quer_qtd or quer_lista):
            return None

        def lista(titulo, itens, contar):
            return self.R(titulo + "\n" + "\n".join(f"• {x}: **{contar(x)}**" for x in itens))

        if re.search(r"\b(locais|ambientes|lugares)\b|\b(quais|que|quantas)\s+salas\b", t):
            if quer_qtd:
                return self.R(f"Há **{len(b.locais)}** locais cadastrados: {', '.join(b.locais)}.")
            return lista("Os locais cadastrados são:", b.locais, lambda x: sum(1 for a in b.ativos if a["local"] == x))
        if re.search(r"\b(tipos|tipo de equipamento|tipos de equipamento)\b", t) and not self.so_entidades():
            if quer_qtd:
                return self.R(f"Há **{len(b.tipos)}** tipos: {', '.join(b.tipos)}.")
            return lista("Os tipos de equipamento são:", b.tipos, lambda x: sum(1 for a in b.ativos if a["tipo"] == x))
        if re.search(r"\b(marcas|fabricantes)\b", t):
            if quer_qtd:
                return self.R(f"Há **{len(b.marcas)}** marcas: {', '.join(b.marcas)}.")
            return lista("As marcas cadastradas são:", b.marcas, lambda x: sum(1 for a in b.ativos if a["marca"] == x))
        if re.search(r"\bmodelos\b", t):
            if quer_qtd or len(b.modelos) > 20:
                return self.R(f"Há **{len(b.modelos)}** modelos diferentes cadastrados. Peça por marca ou tipo para eu detalhar.")
            return lista("Os modelos cadastrados são:", b.modelos, lambda x: sum(1 for a in b.ativos if a["modelo"] == x))
        if re.search(r"\bcategorias\b", t):
            if quer_qtd:
                return self.R(f"Há **{len(SERIES_ORDEM)}** categorias: 2A, 3A, Setups, Carrinhos, Tablets e Televisão.")
            return lista("As categorias são:", [SERIES_CURTO[x] for x in SERIES_ORDEM],
                         lambda x: sum(1 for a in b.ativos if SERIES_CURTO.get(a["serie_id"]) == x))
        if re.search(r"\b(responsaveis|pessoas|usuarios)\b", t) and quer_qtd:
            return self.R(f"Há **{len(b.donos)}** responsáveis diferentes cadastrados (pessoas e grupos).")
        return None

    # Ajuda e glossário
    def h_ajuda_marcada(self):
        t = self.t
        if not re.search(MARCADOR_AJUDA, t):
            return None
        gl = self.glossario(t)
        if gl and re.search(r"\b(o que e|o que sao|o que significa|significado|define|definicao|explica o que e|qual o significado)\b", t):
            return self.R(gl)
        if self.topico:
            return self.responder_topico(self.topico)
        return None

    def h_ajuda_livre(self):
        if self.topico and not self.dados_forte:
            return self.responder_topico(self.topico)
        gl = self.glossario(self.t)
        if gl and self.palavras <= 4:
            return self.R(gl)
        return None

    def glossario(self, t):
        melhor, tam = None, 0
        for chaves, texto in GLOSSARIO:
            for c in chaves:
                if re.search(palavra(c), t) and len(c) > tam:
                    melhor, tam = texto, len(c)
        return melhor

    def responder_topico(self, item):
        texto = item["resposta"]
        if item.get("somente_admin") and self.perfil != "admin":
            texto += "\n\nComo você está como **visitante**, só consegue consultar; esta ação é dos administradores."
        links = []
        if item.get("ir"):
            tela, rotulo = item["ir"]
            if tela != "admin" or self.perfil == "admin":
                links.append({"label": rotulo, "view": tela})
        self.out["topico"] = item["id"]
        return self.R(texto, links=links, sug=self.sugestoes_padrao())

    # Dados
    def filtros(self):
        E = self.E
        explicit = {k for k in CHAVES_FILTRO if E.get(k)}
        F = {k: E[k] for k in CHAVES_FILTRO if E.get(k)}
        if self.seguimento and self.ctx.get("f"):
            for k, v in self.ctx["f"].items():
                if k not in explicit and v:
                    F[k] = v
        return F

    def contar(self, F):
        return [a for a in self.base.ativos if aplica(a, F)]

    def alternativas(self, F):
        """Quando não há resultado, mostra o que existe sem um dos filtros."""
        if len(F) < 2:
            return " Quer tentar outro filtro?"
        sugestoes = []
        for chave in ("situacao", "critico", "mochila", "marcas", "modelos", "pessoas", "locais", "tipos", "serie"):
            if chave in F:
                G = {k: v for k, v in F.items() if k != chave}
                m = len(self.contar(G))
                if m > 0:
                    sugestoes.append(f"{m} {descrever(G, m)}")
            if len(sugestoes) == 2:
                break
        if not sugestoes:
            return ""
        return " Mas há " + " e ".join(sugestoes) + "."

    def listar(self, F, offset=0, titulo=None):
        achados = sorted(self.contar(F), key=lambda a: (SERIES_ORDEM.index(a["serie_id"]) if a["serie_id"] in SERIES_ORDEM else 99,
                                                        chave_natural(a["id_computer"])))
        if not achados:
            return self.R(f"Não encontrei {descrever(F, 0)}." + self.alternativas(F))
        pagina = achados[offset:offset + PAGINA]
        topo = titulo or f"Encontrei **{len(achados)}** {descrever(F, len(achados))}:"
        iguais = len({(a["tipo"], a["marca"], a["modelo"]) for a in achados}) == 1
        if iguais and len(pagina) > 1:
            topo = topo.rstrip(":") + f" (todos {achados[0]['tipo']} {achados[0]['marca']} {achados[0]['modelo']}):".replace("  ", " ")
        texto = topo + "\n" + "\n".join(linha(a, iguais) for a in pagina)
        links = []
        fim = offset + len(pagina)
        if fim < len(achados):
            texto += f"\n…e mais {len(achados) - fim}. Diga **mostra mais** para continuar."
            self.out["lista"] = {"f": F, "offset": fim}
        else:
            self.out.pop("lista", None)
        fl = filtro_para_link(F)
        if fl is not None and len(achados) > 1:
            links.append({"label": "Ver no Inventário", "filtro": fl})
        self.out["f"] = F
        return self.R(texto, items=[item_chip(a) for a in pagina], links=links)

    def agrupar(self, F, campo):
        cont = {}
        for a in self.contar(F):
            chave = a[campo] if campo != "serie_id" else SERIES_CURTO.get(a["serie_id"], a["serie_id"])
            cont[chave or "Não informado"] = cont.get(chave or "Não informado", 0) + 1
        return sorted(cont.items(), key=lambda kv: (-kv[1], norm(kv[0])))

    def campo_da_pergunta(self):
        t = self.t
        if re.search(r"\b(local|locais|sala|salas|ambiente|ambientes|onde)\b", t):
            return "local", "local"
        if re.search(r"\b(marca|marcas|fabricante|fabricantes)\b", t):
            return "marca", "marca"
        if re.search(r"\b(modelo|modelos)\b", t):
            return "modelo", "modelo"
        if re.search(r"\b(categoria|categorias|serie|turma|ano|grupo|grupos)\b", t):
            return "serie_id", "categoria"
        if re.search(r"\b(tipo|tipos|aparelho|aparelhos)\b", t):
            return "tipo", "tipo"
        if re.search(r"\b(situacao)\b", t):
            return "situacao", "situação"
        return None, None

    def resumo(self):
        b = self.base
        total = len(b.ativos)
        if not total:
            return self.R("Ainda não há equipamentos cadastrados.")
        em_uso = sum(1 for a in b.ativos if a["situacao"] == "Em uso")
        crit = sum(1 for a in b.ativos if a["criticidade"] == "Sim")
        tipos = self.agrupar({}, "tipo")
        locais = self.agrupar({}, "local")
        partes = [f"Hoje o inventário tem **{total}** equipamentos: **{em_uso}** em uso, **{total - em_uso}** fora de uso e **{crit}** críticos.",
                  f"• Tipo mais comum: **{tipos[0][0]}** ({tipos[0][1]})" if tipos else "",
                  f"• Local com mais equipamentos: **{locais[0][0]}** ({locais[0][1]})" if locais else ""]
        if b.hist:
            partes.append("• Última alteração: " + self.frase_hist(b.hist[0]).replace("**", ""))
        return self.R("\n".join(p for p in partes if p), links=[{"label": "Abrir Painel", "view": "dashboard"}],
                      sug=["Quantos notebooks estão em uso?", "Quantos equipamentos por local?", "Quais equipamentos são críticos?"])

    def h_dados(self):
        t, E, b = self.t, self.E, self.base
        F = self.filtros()
        tem = bool(F)
        if re.search(RESUMO, t) and not tem:
            return self.resumo()
        mais, menos = re.search(MAIS, t), re.search(MENOS, t)
        rank = (mais or menos) and (tem or re.search(r"\b(comum|frequente|equipamentos|ativos|itens|local|locais|tipo|tipos|marca|marcas|modelo|categoria|sala|salas|numero)\b", t))

        # Comparação entre duas coisas ("tem mais notebook ou tablet?")
        if re.search(r"\b(ou|versus|vs|comparar|compare|comparado|contra|diferenca entre)\b", t) and (len(E["tipos"]) >= 2 or len(E["locais"]) >= 2 or len(E["marcas"]) >= 2):
            chave = "tipos" if len(E["tipos"]) >= 2 else ("locais" if len(E["locais"]) >= 2 else "marcas")
            base_F = {k: v for k, v in F.items() if k != chave}
            valores = E[chave][:2]
            conts = []
            for v in valores:
                G = dict(base_F)
                G[chave] = [v]
                conts.append(len(self.contar(G)))
            (a, ca), (c, cc) = (valores[0], conts[0]), (valores[1], conts[1])
            if ca == cc:
                texto = f"Empate: **{a}** e **{c}** têm **{ca}** cada."
            else:
                maior, menor = ((a, ca), (c, cc)) if ca > cc else ((c, cc), (a, ca))
                texto = f"**{maior[0]}** tem mais: **{maior[1]}** contra **{menor[1]}** de {menor[0]}."
            return self.R(texto)

        # Ranking ("qual local tem mais equipamentos?")
        if rank and not re.search(PCT, t):
            campo, rotulo = self.campo_da_pergunta()
            if campo is None:
                campo, rotulo = "tipo", "tipo"
                if E["locais"] and not E["tipos"]:
                    campo, rotulo = "marca", "marca"
            G = dict(F)
            if campo == "tipo":
                G.pop("tipos", None)
            elif campo == "local":
                G.pop("locais", None)
            elif campo == "marca":
                G.pop("marcas", None)
            elif campo == "modelo":
                G.pop("modelos", None)
            elif campo == "serie_id":
                G.pop("serie", None)
            grupos = self.agrupar(G, campo)
            if not grupos:
                return self.R("Não encontrei equipamentos com esses critérios.")
            alvo = grupos[-1] if (menos and not mais) else grupos[0]
            empatados = [g for g in grupos if g[1] == alvo[1]]
            total_f = sum(c for _, c in grupos)
            desc = descrever(G, 2)
            sufixo = "mais" if not (menos and not mais) else "menos"
            fem = campo in ("marca", "serie_id", "situacao")
            art, prep = ("A", "na") if fem else ("O", "no")
            if len(empatados) > 1 and len(empatados) < len(grupos):
                texto = f"Há empate {prep} {rotulo} com {sufixo} {desc}: {', '.join('**' + g[0] + '**' for g in empatados)}, com **{alvo[1]}** cada."
            else:
                texto = f"{art} {rotulo} com {sufixo} {desc} é **{alvo[0]}**, com **{alvo[1]}** de {total_f} ({pct(alvo[1], total_f)})."
            restantes = [g for g in grupos if g not in empatados][:2] if sufixo == "mais" else list(reversed([g for g in grupos if g not in empatados]))[:2]
            if restantes:
                texto += " Em seguida: " + ", ".join(f"{g[0]} ({g[1]})" for g in restantes) + "."
            self.out["f"] = F
            return self.R(texto)

        # "Onde estão os notebooks?" -> distribuição por local
        if re.search(r"\bonde (esta|estao|ficam|fica|tem|existem)\b", t) and tem and not E["locais"]:
            grupos = self.agrupar(F, "local")
            if grupos:
                total = sum(c for _, c in grupos)
                self.out["f"] = F
                return self.R(f"Os {descrever(F, 2)} estão assim:\n" + "\n".join(f"• {k}: **{v}** ({pct(v, total)})" for k, v in grupos))

        # Percentual
        if re.search(PCT, t):
            if not tem:
                grupos = self.agrupar({}, "situacao")
                total = len(b.ativos)
                return self.R("Por situação:\n" + "\n".join(f"• {k}: **{pct(v, total)}** ({v})" for k, v in grupos))
            n = len(self.contar(F))
            total = len(b.ativos)
            self.out["f"] = F
            return self.R(f"São **{n}** de **{total}** equipamentos, ou **{pct(n, total)}** do total ({descrever(F, n)}).")

        # Distribuição ("por local", "em cada categoria")
        if re.search(DISTR, t):
            campo, rotulo = self.campo_da_pergunta()
            campo = campo or "tipo"
            rotulo = rotulo or "tipo"
            G = {k: v for k, v in F.items() if not (campo == "tipo" and k == "tipos") and not (campo == "local" and k == "locais")
                 and not (campo == "marca" and k == "marcas") and not (campo == "serie_id" and k == "serie")}
            grupos = self.agrupar(G, campo)
            if not grupos:
                return self.R("Não encontrei equipamentos com esses critérios.")
            total = sum(c for _, c in grupos)
            tit = f"Distribuição por {rotulo}" + (f" ({descrever(G, 2)})" if G else "") + ":"
            self.out["f"] = G
            return self.R(tit + "\n" + "\n".join(f"• {k}: **{v}** ({pct(v, total)})" for k, v in grupos))

        # Local citado que não existe
        if not (E["locais"] or E["tipos"] or E["serie"] or E["marcas"] or E["modelos"] or E["pessoas"]) and self.dados_forte:
            m = re.search(r"\b(?:no|na|nos|nas|em)\s+(?:o\s+|a\s+)?([a-z0-9\-]{4,})", t)
            if m and m.group(1) not in IGNORAR_LOCAL and not E["situacao"] and not E["critico"] and not E["mochila"]:
                digitado = next((w for w in re.findall(r"[\wÀ-ÿ\-]+", self.original) if norm(w) == m.group(1)), m.group(1))
                return self.R(f"Não encontrei \"{digitado}\" entre os locais cadastrados. Os locais são: {', '.join(b.locais) or 'nenhum'}.")

        # Existência ("tem algum tablet na Sala 06?")
        if re.search(EXISTE, t) and (tem or True) and not re.search(QTD, t):
            achados = self.contar(F)
            self.out["f"] = F
            if not achados:
                return self.R(f"Não, não há {descrever(F, 2)}." + self.alternativas(F))
            n = len(achados)
            texto = (f"Sim, há **{n}** {descrever(F, n)}." if n > 1 else f"Sim, há **1** {descrever(F, 1)}.")
            if n <= 6:
                return self.R(texto + "\n" + "\n".join(linha(a) for a in achados), items=[item_chip(a) for a in achados])
            self.out["oferta"] = {"acao": "listar", "f": F}
            return self.R(texto + " Quer que eu liste?")

        # Lista
        if re.search(LISTA, t) and (tem or self.palavras <= 8):
            return self.listar(F, 0)

        # Contagem
        if re.search(QTD, t) or (tem and not (self.topico and self.topico["id"] not in ("situacao", "critico", "categorias", "mochila", "carregador", "detalhes", "painel"))):
            achados = self.contar(F)
            n = len(achados)
            self.out["f"] = F
            if n == 0:
                total = len(b.ativos)
                if set(F) == {"situacao"} and total:
                    outro = "em uso" if F["situacao"] == "Não em uso" else "fora de uso"
                    return self.R(f"Nenhum equipamento está {'fora de uso' if F['situacao'] == 'Não em uso' else 'em uso'}: todos os **{total}** estão {outro}.")
                if set(F) == {"critico"}:
                    return self.R("Nenhum equipamento está marcado como crítico.")
                return self.R(self.escolher([f"Não encontrei {descrever(F, 0)}.", f"Nenhum resultado para {descrever(F, 0)}."]) + self.alternativas(F))
            if n == 1:
                texto = self.escolher([f"Existe **1** {descrever(F, 1)}.", f"Encontrei **1** {descrever(F, 1)}.", f"É apenas **1** {descrever(F, 1)}."])
            elif not tem:
                em_uso = sum(1 for a in achados if a["situacao"] == "Em uso")
                texto = f"Existem **{n}** equipamentos cadastrados: **{em_uso}** em uso e **{n - em_uso}** fora de uso."
            else:
                texto = self.escolher([f"Existem **{n}** {descrever(F, n)}.", f"São **{n}** {descrever(F, n)}.", f"Encontrei **{n}** {descrever(F, n)}."])
            sug = ["Quais são?", "E em uso?", "Mostre por local", "Faça um resumo dos equipamentos"]
            if 1 < n <= 80 and tem:
                self.out["oferta"] = {"acao": "listar", "f": F}
                texto += " " + self.escolher(["Quer que eu liste?", "Quer ver quais são?"])
            return self.R(texto, sug=sug)
        if re.search(RESUMO, t):
            return self.resumo()
        return None

    # Quando nada serviu
    def fallback(self):
        t = self.t
        if self.so_entidades():
            return self.R("Posso contar, listar ou comparar isso. Por exemplo: \"quantos são?\" ou \"quais são?\".", sug=["Quantos são?", "Quais são?"])
        if re.search(r"\?", self.tq) or self.palavras >= 3:
            texto = self.escolher([
                "Não tenho certeza do que você quis dizer. Posso contar e listar equipamentos, dizer onde está cada um, mostrar o que mudou, explicar o sistema e até contar uma piada. Tente algo como: \"quantos notebooks estão em uso?\".",
                "Ainda não sei responder isso. Funciono offline e conheço o sistema e os equipamentos da escola. Quer tentar de outro jeito, por exemplo: \"onde está o equipamento 7?\"",
                "Hmm, essa eu não peguei. Você pode reformular? Se preferir, escolha uma das sugestões abaixo.",
            ])
        else:
            texto = self.escolher(["Pode explicar melhor? Não entendi.", "Não entendi muito bem. Do que você precisa?"])
        return self.R(texto, sug=self.sugestoes_padrao())

    def finalizar(self, r):
        self.out["ultima"] = re.sub(r"\*\*", "", r["reply"]).replace("\n", " ")[:400]
        r["contexto"] = self.out
        r["suggestions"] = r["suggestions"] or self.sugestoes_padrao()
        return r


def responder(msg, base, contexto=None, usuario=None, perfil="visitor", agora=None, rnd=None):
    """Ponto de entrada. Devolve {reply, items, links, suggestions, contexto}."""
    ctx = limpar_contexto(contexto)
    conv = Conversa(base, msg, ctx, usuario, perfil, agora, rnd)
    if not conv.original:
        r = conv.R("Digite uma pergunta sobre o sistema ou sobre os equipamentos.")
        return conv.finalizar(r)
    # Ofertas, listas em andamento e escolhas pendentes valem só para a mensagem seguinte.
    for k in ("oferta", "lista", "cand", "cand_attr", "fun"):
        conv.out.pop(k, None)
    r = conv.responder()
    return conv.finalizar(r)
