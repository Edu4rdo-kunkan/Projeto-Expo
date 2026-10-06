from flask import (
    Flask, request, jsonify, render_template, redirect, url_for, session, send_file,
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from io import BytesIO
from datetime import datetime, timedelta, timezone
import re
import time
import unicodedata
import sqlite3
import os
import secrets
import gzip
import json
import urllib.request
import urllib.error

import assistente

app = Flask(__name__, template_folder="templates", static_folder="static")

# Configuração
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ESCOLA_NOME = os.getenv("ESCOLA_NOME", "Escola Estadual Antônio Branco Rodrigues Junior")
ESCOLA_SIGLA = os.getenv("ESCOLA_SIGLA", "E.E. Antônio Branco Rodrigues Junior")
DB_PATH = os.getenv("DB_PATH", "ativos.db")


def _carregar_secret_key():
    """Usa SECRET_KEY, se existir; senão guarda uma chave em .secret_key.

    Assim todos os processos do servidor usam a mesma chave e o login
    não cai a cada reinício.
    """
    env = os.getenv("SECRET_KEY")
    if env:
        return env
    pasta = os.path.dirname(os.path.abspath(DB_PATH)) or BASE_DIR
    caminho = os.path.join(pasta, ".secret_key")
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            valor = f.read().strip()
            if valor:
                return valor
    except OSError:
        pass
    nova = secrets.token_hex(32)
    try:
        fd = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(nova)
    except FileExistsError:
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return f.read().strip() or nova
        except OSError:
            pass
    except OSError:
        pass  # sistema de arquivos somente leitura: usa a chave só em memória
    return nova


app.secret_key = _carregar_secret_key()

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    JSON_AS_ASCII=False,
)

# Contas de administrador. Para trocar senhas sem editar o código, defina a
# variável de ambiente ADMIN_USERS no formato  "usuario:senha;outro:senha2".
# Sem a variável, valem as contas que já existiam no projeto.
_PADRAO = {"Gabi": "gabi1234", "Eduardo": "dudu1234", "Saymon": "saysay1234"}


def _carregar_usuarios():
    pares = {}
    for item in os.getenv("ADMIN_USERS", "").split(";"):
        if ":" in item:
            u, s = item.split(":", 1)
            if u.strip() and s:
                pares[u.strip()] = s
    return {u: generate_password_hash(s) for u, s in (pares or _PADRAO).items()}


USERS = _carregar_usuarios()

SERIES_ORDEM = ["2A", "3A", "SETUPS", "CARRINHOS", "TABLETS", "TELEVISAO"]
SERIES_VALIDAS = set(SERIES_ORDEM)
SERIES_ROTULO = {
    "2A": "2º Ano (2A)", "3A": "3º Ano (3A)", "SETUPS": "Setups",
    "CARRINHOS": "Carrinhos", "TABLETS": "Tablets", "TELEVISAO": "Televisão",
}
SITUACOES = {"Em uso", "Não em uso"}
CRITICIDADES = {"Nenhuma", "Sim", "Não"}
MOCHILAS = {"Sim", "Não", "N/A", ""}

CAMPOS_ATIVO = [
    "serie_id", "owner_1", "owner_2", "id_computer", "id_carregator",
    "tipo", "marca", "modelo", "local", "situacao", "mochila", "criticidade",
]
# Identidade e status do equipamento são obrigatórios. Responsáveis, carregador
# e mochila são opcionais (TVs e setups, por exemplo, não têm todos esses dados).
CAMPOS_OBRIGATORIOS = [
    "serie_id", "id_computer", "tipo", "marca", "modelo", "local",
    "situacao", "criticidade",
]
CAMPOS_ROTULO = {
    "serie_id": "Categoria", "owner_1": "Responsável 1", "owner_2": "Responsável 2",
    "id_computer": "ID do equipamento", "id_carregator": "Carregador",
    "tipo": "Tipo", "marca": "Marca", "modelo": "Modelo", "local": "Local",
    "situacao": "Situação", "mochila": "Mochila", "criticidade": "Criticidade",
}
ORDENACAO_VALIDA = {
    "id_computer", "serie_id", "tipo", "marca", "modelo", "local",
    "situacao", "owner_1", "criticidade", "mochila",
}


# Banco de dados
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cria o que faltar sem tocar nos dados existentes."""
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ativos (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                serie_id      TEXT    NOT NULL,
                owner_1       TEXT    NOT NULL DEFAULT '',
                owner_2       TEXT    NOT NULL DEFAULT '',
                id_computer   TEXT    NOT NULL DEFAULT '',
                id_carregator TEXT    NOT NULL DEFAULT '',
                tipo          TEXT    NOT NULL DEFAULT '',
                marca         TEXT    NOT NULL DEFAULT '',
                modelo        TEXT    NOT NULL DEFAULT '',
                local         TEXT    NOT NULL DEFAULT '',
                situacao      TEXT    NOT NULL DEFAULT '',
                mochila       TEXT    NOT NULL DEFAULT '',
                criticidade   TEXT    NOT NULL DEFAULT ''
            )
        """)
        # Histórico NÃO usa chave estrangeira de propósito: o registro da
        # exclusão de um equipamento precisa sobreviver a ele.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historico (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                ativo_id       INTEGER NOT NULL,
                id_computer    TEXT    NOT NULL DEFAULT '',
                serie_id       TEXT    NOT NULL DEFAULT '',
                tipo           TEXT    NOT NULL DEFAULT '',
                usuario        TEXT    NOT NULL DEFAULT '',
                operacao       TEXT    NOT NULL,
                campo          TEXT    NOT NULL DEFAULT '',
                valor_anterior TEXT    NOT NULL DEFAULT '',
                valor_novo     TEXT    NOT NULL DEFAULT '',
                criado_em      TEXT    NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hist_ativo ON historico(ativo_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hist_data ON historico(criado_em)")
        conn.commit()
    finally:
        conn.close()


init_db()


def clean(value):
    """Normaliza qualquer valor vindo do JSON (inclusive None) para string."""
    if value is None:
        return ""
    return str(value).strip()


def saida(valor):
    """Valores 'nan' (resíduo da importação do Excel) viram vazio só na exibição."""
    v = "" if valor is None else str(valor).strip()
    return "" if v.lower() == "nan" else v


def ativo_dict(row):
    d = dict(row)
    for k in CAMPOS_ATIVO:
        d[k] = saida(d.get(k))
    d["serie_rotulo"] = SERIES_ROTULO.get(d["serie_id"], d["serie_id"])
    return d


def norm(texto):
    """minúsculas, sem acentos, só letras/números/hífen/barra/espaço."""
    t = unicodedata.normalize("NFD", str(texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9\-/ ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def chave_natural(texto):
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", norm(texto))]


def agora():
    # Horário de Brasília (UTC-3), sem depender de tzdata instalado.
    return datetime.now(timezone(timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M:%S")


# Autenticação / autorização
def is_api_request():
    return request.path.startswith("/api/") or request.path == "/exportar"


def _nao_autenticado():
    if is_api_request():
        return jsonify({"ok": False, "msg": "Sua sessão expirou. Faça login novamente."}), 401
    if request.path.startswith("/equipamento/"):
        session["next"] = request.path
    return redirect(url_for("login_page"))


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("authenticated"):
            return _nao_autenticado()
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("authenticated"):
            return _nao_autenticado()
        if session.get("role") != "admin":
            return jsonify({
                "ok": False,
                "msg": "Você não possui permissão para realizar esta operação.",
            }), 403
        if request.method in ("POST", "PUT", "PATCH") and not request.is_json:
            return jsonify({"ok": False, "msg": "Requisição inválida."}), 415
        return f(*args, **kwargs)
    return wrapper


def usuario_atual():
    return session.get("username") or "visitante"


# Limite de tentativas de login (guardado em memória, por processo).
_TENTATIVAS = {}
_MAX_TENTATIVAS = 8
_JANELA_S = 300


def _bloqueado(chave):
    agora_t = time.time()
    recentes = [t for t in _TENTATIVAS.get(chave, []) if agora_t - t < _JANELA_S]
    _TENTATIVAS[chave] = recentes
    return len(recentes) >= _MAX_TENTATIVAS


def _registrar_falha(chave):
    _TENTATIVAS.setdefault(chave, []).append(time.time())


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if session.get("authenticated"):
        return redirect(url_for("index"))

    erro = None
    aviso = None
    if request.method == "GET" and request.args.get("expirada"):
        aviso = "Sua sessão expirou. Faça login novamente."
    if request.method == "GET" and request.args.get("saiu"):
        aviso = "Você saiu do sistema."

    if request.method == "POST":
        usuario_digitado = clean(request.form.get("username"))
        senha_digitada = request.form.get("password") or ""

        if not usuario_digitado or not senha_digitada:
            erro = "Informe usuário e senha."
        else:
            chave_rl = (request.remote_addr, usuario_digitado.lower())
            if _bloqueado(chave_rl):
                erro = "Muitas tentativas. Aguarde alguns minutos e tente novamente."
            else:
                chave_usuario = next(
                    (u for u in USERS if u.lower() == usuario_digitado.lower()), None
                )
                # Mesma mensagem para usuário inexistente e senha errada.
                if chave_usuario and check_password_hash(USERS[chave_usuario], senha_digitada):
                    proximo = session.get("next")
                    session.clear()
                    session.permanent = True
                    session["authenticated"] = True
                    session["role"] = "admin"
                    session["username"] = chave_usuario
                    _TENTATIVAS.pop(chave_rl, None)
                    return redirect(proximo or url_for("index"))
                _registrar_falha(chave_rl)
                erro = "Usuário ou senha incorretos."

    return render_template("login.html", erro=erro, aviso=aviso)


@app.route("/visitante")
def entrar_visitante():
    proximo = session.get("next")
    session.clear()
    session.permanent = True
    session["authenticated"] = True
    session["role"] = "visitor"
    session["username"] = None
    return redirect(proximo or url_for("index"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page", saiu=1))


# Páginas
@app.route("/")
@login_required
def index():
    return render_template(
        "index.html", role=session.get("role"), username=session.get("username"),
        abrir_id=None,
    )


@app.route("/equipamento/<int:ativo_id>")
@login_required
def pagina_equipamento(ativo_id):
    """Destino do QR Code: abre o sistema já com os detalhes do equipamento."""
    return render_template(
        "index.html", role=session.get("role"), username=session.get("username"),
        abrir_id=ativo_id,
    )


@app.context_processor
def _contexto():
    arquivos = ("css/app.css", "js/app.js", "js/charts.js", "js/qr.js", "js/theme.js", "js/login.js")
    try:
        v = int(max(os.path.getmtime(os.path.join(BASE_DIR, "static", a)) for a in arquivos))
    except OSError:
        v = 1
    return {"asset_v": v, "escola_nome": ESCOLA_NOME, "escola_sigla": ESCOLA_SIGLA,
            "assistente_ia": ia_ativa()}


_TIPOS_COMPRIMIVEIS = ("text/", "application/json", "application/javascript", "image/svg+xml")
_CACHE_GZIP = {}


@app.after_request
def _cabecalhos(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    )
    if request.path.startswith("/api/") or request.path == "/exportar":
        resp.headers["Cache-Control"] = "no-store"
    elif request.path.startswith("/static/"):
        # O endereço leva ?v=<versão>, que muda a cada atualização dos arquivos.
        if request.args.get("v"):
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            resp.headers["Cache-Control"] = "no-cache"
    return _comprimir(resp)


def _comprimir(resp):
    """Compacta texto (HTML, CSS, JS, JSON) quando o navegador aceita gzip."""
    try:
        if (resp.status_code != 200 or "Content-Encoding" in resp.headers
                or "gzip" not in request.headers.get("Accept-Encoding", "")
                or not resp.mimetype.startswith(_TIPOS_COMPRIMIVEIS)):
            return resp
        chave = None
        if request.path.startswith("/static/"):
            chave = (request.path, resp.headers.get("ETag"))
            if chave in _CACHE_GZIP:
                dados = _CACHE_GZIP[chave]
                resp.direct_passthrough = False
                resp.set_data(dados)
                resp.headers["Content-Encoding"] = "gzip"
                resp.headers["Vary"] = "Accept-Encoding"
                return resp
        resp.direct_passthrough = False
        bruto = resp.get_data()
        if len(bruto) < 1024:
            return resp
        dados = gzip.compress(bruto, compresslevel=6)
        if chave:
            _CACHE_GZIP[chave] = dados
        resp.set_data(dados)
        resp.headers["Content-Encoding"] = "gzip"
        resp.headers["Vary"] = "Accept-Encoding"
    except Exception:
        pass  # em caso de qualquer problema, entrega sem compactar
    return resp


@app.route("/favicon.ico")
def favicon():
    return ("", 204)


# Histórico (auditoria)
def _hist(conn, ativo, operacao, campo="", anterior="", novo=""):
    conn.execute(
        """INSERT INTO historico
           (ativo_id, id_computer, serie_id, tipo, usuario, operacao, campo,
            valor_anterior, valor_novo, criado_em)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (ativo["id"], saida(ativo["id_computer"]), ativo["serie_id"], saida(ativo["tipo"]),
         usuario_atual(), operacao, campo, anterior, novo, agora()),
    )


def _resumo(d):
    partes = [saida(d.get("tipo")), saida(d.get("marca")), saida(d.get("modelo"))]
    return f"{' '.join(p for p in partes if p)} · {saida(d.get('local'))}".strip(" ·")


# Validação
def _ler_e_validar(data):
    valores = {c: clean(data.get(c)) for c in CAMPOS_ATIVO}
    valores["serie_id"] = valores["serie_id"].upper()

    for c in CAMPOS_OBRIGATORIOS:
        if not valores[c]:
            return None, f"Preencha o campo obrigatório: {CAMPOS_ROTULO[c]}."
    for c, v in valores.items():
        if len(v) > 120:
            return None, f"O campo {CAMPOS_ROTULO[c]} é muito longo (máximo 120 caracteres)."
    if valores["serie_id"] not in SERIES_VALIDAS:
        return None, "Categoria inválida."
    if valores["situacao"] not in SITUACOES:
        return None, "Situação inválida."
    if valores["criticidade"] not in CRITICIDADES:
        return None, "Criticidade inválida."
    if valores["mochila"] not in MOCHILAS:
        return None, "Valor de mochila inválido."
    return valores, None


def _duplicado(conn, valores, ignorar_id=None):
    row = conn.execute(
        "SELECT id FROM ativos WHERE id_computer = ? AND UPPER(serie_id) = ? AND id != ?",
        (valores["id_computer"], valores["serie_id"], ignorar_id or -1),
    ).fetchone()
    return row is not None


# Consultas (administrador e visitante)
@app.route("/api/me", methods=["GET"])
@login_required
def api_me():
    return jsonify({
        "ok": True, "role": session.get("role"), "username": session.get("username"),
    })


@app.route("/api/opcoes", methods=["GET"])
@login_required
def api_opcoes():
    conn = get_db()
    try:
        def distintos(campo):
            rows = conn.execute(
                f"SELECT DISTINCT TRIM({campo}) AS v FROM ativos ORDER BY v"
            ).fetchall()
            return sorted({saida(r["v"]) for r in rows if saida(r["v"])}, key=norm)
        return jsonify({
            "ok": True,
            "series": [{"id": s, "rotulo": SERIES_ROTULO[s]} for s in SERIES_ORDEM],
            "tipos": distintos("tipo"),
            "marcas": distintos("marca"),
            "modelos": distintos("modelo"),
            "locais": distintos("local"),
        })
    finally:
        conn.close()


def _filtrar_ativos(conn, args):
    sql, params = "SELECT * FROM ativos WHERE 1=1", []
    serie = clean(args.get("serie")).upper()
    if serie:
        sql += " AND UPPER(serie_id) = ?"
        params.append(serie)
    for campo in ("tipo", "marca", "local", "situacao", "criticidade"):
        valor = clean(args.get(campo))
        if valor:
            sql += f" AND TRIM({campo}) = ?"
            params.append(valor)
    mochila = clean(args.get("mochila"))
    if mochila:
        sql += " AND TRIM(mochila) = ?"
        params.append(mochila)
    rows = [ativo_dict(r) for r in conn.execute(sql, params).fetchall()]

    q = norm(args.get("q"))
    if q:
        # "em uso" / "não em uso" na busca valem como filtro de situação,
        # não como palavras soltas espalhadas por outros campos.
        situacao_q = None
        if "nao em uso" in q:
            situacao_q, q = "Não em uso", q.replace("nao em uso", " ")
        elif "em uso" in q:
            situacao_q, q = "Em uso", q.replace("em uso", " ")
        if situacao_q:
            rows = [a for a in rows if a["situacao"] == situacao_q]
        termos = q.split()
        def casa(a):
            palheiro = norm(" ".join([
                a["id_computer"], a["id_carregator"], a["owner_1"], a["owner_2"],
                a["tipo"], a["marca"], a["modelo"], a["local"], a["situacao"],
                a["mochila"], a["criticidade"], a["serie_id"], a["serie_rotulo"],
                "critico" if a["criticidade"] == "Sim" else "",
            ]))
            return all(t in palheiro for t in termos)
        rows = [a for a in rows if casa(a)]
    return rows


@app.route("/api/ativos", methods=["GET"])
@login_required
def api_listar_ativos():
    conn = get_db()
    try:
        rows = _filtrar_ativos(conn, request.args)
        total_geral = conn.execute("SELECT COUNT(*) AS c FROM ativos").fetchone()["c"]
    finally:
        conn.close()

    ordem = clean(request.args.get("sort"))
    desc = clean(request.args.get("dir")).lower() == "desc"
    if ordem in ORDENACAO_VALIDA:
        rows.sort(key=lambda a: chave_natural(a[ordem]), reverse=desc)
    else:
        rows.sort(key=lambda a: (
            SERIES_ORDEM.index(a["serie_id"]) if a["serie_id"] in SERIES_ORDEM else 99, a["id"],
        ))

    try:
        por_pagina = min(max(int(request.args.get("per_page", 15)), 1), 200)
        pagina = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        por_pagina, pagina = 15, 1
    total = len(rows)
    paginas = max(1, -(-total // por_pagina))
    pagina = min(pagina, paginas)
    inicio = (pagina - 1) * por_pagina
    return jsonify({
        "ok": True, "total": total, "total_geral": total_geral,
        "page": pagina, "pages": paginas, "per_page": por_pagina,
        "items": rows[inicio:inicio + por_pagina],
    })


@app.route("/api/ativos/<int:ativo_id>", methods=["GET"])
@login_required
def api_detalhe_ativo(ativo_id):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM ativos WHERE id = ?", (ativo_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        return jsonify({"ok": False, "msg": "Equipamento não encontrado."}), 404
    return jsonify({"ok": True, "item": ativo_dict(row)})


@app.route("/api/visualizar/<serie>", methods=["GET"])
@login_required
def visualizar(serie):
    """Rota original, mantida por compatibilidade (agora o visitante vê tudo)."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM ativos WHERE UPPER(serie_id) = ? ORDER BY id",
            (clean(serie).upper(),),
        ).fetchall()
        return jsonify([ativo_dict(r) for r in rows])
    finally:
        conn.close()


@app.route("/api/historico", methods=["GET"])
@login_required
def api_historico():
    ativo_id = request.args.get("ativo_id", type=int)
    operacao = clean(request.args.get("operacao"))
    pagina = max(request.args.get("page", 1, type=int) or 1, 1)
    por_pagina = min(max(request.args.get("per_page", 30, type=int) or 30, 1), 100)

    where, params = "WHERE 1=1", []
    if ativo_id:
        where += " AND ativo_id = ?"
        params.append(ativo_id)
    if operacao in ("criacao", "edicao", "exclusao"):
        where += " AND operacao = ?"
        params.append(operacao)

    conn = get_db()
    try:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM historico {where}", params).fetchone()["c"]
        rows = conn.execute(
            f"""SELECT h.*, (SELECT 1 FROM ativos a WHERE a.id = h.ativo_id) AS existe
                FROM historico h {where.replace('ativo_id', 'h.ativo_id').replace('operacao', 'h.operacao')}
                ORDER BY h.id DESC LIMIT ? OFFSET ?""",
            params + [por_pagina, (pagina - 1) * por_pagina],
        ).fetchall()
        itens = []
        for r in rows:
            d = dict(r)
            d["existe"] = bool(d["existe"])
            itens.append(d)
        return jsonify({
            "ok": True, "total": total, "page": pagina,
            "pages": max(1, -(-total // por_pagina)), "items": itens,
        })
    finally:
        conn.close()


# Estatísticas / dashboard (administrador e visitante)
def calcular_estatisticas(conn):
    def contar(where="1=1", params=()):
        return conn.execute(f"SELECT COUNT(*) AS c FROM ativos WHERE {where}", params).fetchone()["c"]

    def agrupar(campo):
        # `campo` é sempre uma constante do código, nunca vem do usuário.
        rows = conn.execute(f"""
            SELECT COALESCE(NULLIF(TRIM({campo}), ''), 'Não informado') AS chave, COUNT(*) AS total
            FROM ativos GROUP BY chave ORDER BY total DESC, chave
        """).fetchall()
        return [{"chave": saida(r["chave"]) or "Não informado", "total": r["total"]} for r in rows]

    total = contar()
    em_uso = contar("situacao = 'Em uso'")
    nao_em_uso = contar("situacao = 'Não em uso'")
    criticos = contar("criticidade = 'Sim'")
    por_serie_raw = {r["chave"]: r["total"] for r in agrupar("serie_id")}
    por_serie = [
        {"chave": SERIES_ROTULO[s], "id": s, "total": por_serie_raw.get(s, 0)} for s in SERIES_ORDEM
    ]

    def pct(n):
        return round(n * 100 / total, 1) if total else 0

    por_tipo, por_local = agrupar("tipo"), agrupar("local")
    recentes = conn.execute(
        "SELECT * FROM historico ORDER BY id DESC LIMIT 6"
    ).fetchall()
    return {
        "ok": True,
        "total": total, "em_uso": em_uso, "nao_em_uso": nao_em_uso, "criticos": criticos,
        "pct_em_uso": pct(em_uso), "pct_nao_em_uso": pct(nao_em_uso), "pct_criticos": pct(criticos),
        "por_situacao": agrupar("situacao"), "por_tipo": por_tipo, "por_local": por_local,
        "por_criticidade": agrupar("criticidade"), "por_serie": por_serie,
        "top_tipos": por_tipo[:3], "top_locais": por_local[:3],
        "criticos_por_tipo": [
            {"chave": saida(r["chave"]), "total": r["total"]} for r in conn.execute(
                "SELECT TRIM(tipo) AS chave, COUNT(*) AS total FROM ativos "
                "WHERE criticidade = 'Sim' GROUP BY chave ORDER BY total DESC"
            ).fetchall()
        ],
        "recentes": [dict(r) for r in recentes],
    }


@app.route("/api/dashboard", methods=["GET"])
@login_required
def dashboard():
    conn = get_db()
    try:
        return jsonify(calcular_estatisticas(conn))
    finally:
        conn.close()


@app.route("/api/estatisticas", methods=["GET"])
@login_required
def estatisticas():
    return dashboard()


# Alterações (somente administrador)
def _criar(data):
    valores, erro = _ler_e_validar(data)
    if erro:
        return jsonify({"ok": False, "msg": erro}), 400
    conn = get_db()
    try:
        if _duplicado(conn, valores):
            return jsonify({
                "ok": False,
                "msg": f"Já existe o equipamento {valores['id_computer']} em {SERIES_ROTULO[valores['serie_id']]}.",
            }), 409
        cur = conn.execute(
            f"INSERT INTO ativos ({', '.join(CAMPOS_ATIVO)}) "
            f"VALUES ({', '.join(':' + c for c in CAMPOS_ATIVO)})", valores,
        )
        novo_id = cur.lastrowid
        _hist(conn, {"id": novo_id, **valores}, "criacao", "", "", _resumo(valores))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"ok": True, "msg": "Equipamento cadastrado com sucesso.", "id": novo_id}), 201


def _atualizar(ativo_id, data):
    valores, erro = _ler_e_validar(data)
    if erro:
        return jsonify({"ok": False, "msg": erro}), 400
    conn = get_db()
    try:
        atual = conn.execute("SELECT * FROM ativos WHERE id = ?", (ativo_id,)).fetchone()
        if not atual:
            return jsonify({"ok": False, "msg": "Equipamento não encontrado."}), 404
        if _duplicado(conn, valores, ignorar_id=ativo_id):
            return jsonify({
                "ok": False,
                "msg": f"Já existe o equipamento {valores['id_computer']} em {SERIES_ROTULO[valores['serie_id']]}.",
            }), 409

        antigo = dict(atual)
        conn.execute(
            f"UPDATE ativos SET {', '.join(f'{c} = :{c}' for c in CAMPOS_ATIVO)} WHERE id = :id",
            {**valores, "id": ativo_id},
        )
        mudancas = 0
        for c in CAMPOS_ATIVO:
            antes, depois = saida(antigo[c]), valores[c]
            if antes != depois:
                _hist(conn, {"id": ativo_id, **valores}, "edicao", CAMPOS_ROTULO[c], antes, depois)
                mudancas += 1
        conn.commit()
    finally:
        conn.close()
    msg = "Equipamento atualizado com sucesso." if mudancas else "Nenhuma alteração foi feita."
    return jsonify({"ok": True, "msg": msg, "alteracoes": mudancas})


def _excluir(ativo_id, serie=None):
    conn = get_db()
    try:
        sql, params = "SELECT * FROM ativos WHERE id = ?", [ativo_id]
        if serie:
            sql += " AND UPPER(serie_id) = ?"
            params.append(clean(serie).upper())
        atual = conn.execute(sql, params).fetchone()
        if not atual:
            return jsonify({"ok": False, "msg": "Equipamento não encontrado."}), 404
        d = ativo_dict(atual)
        _hist(conn, atual, "exclusao", "", _resumo(d), "")
        conn.execute("DELETE FROM ativos WHERE id = ?", (ativo_id,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"ok": True, "msg": "Equipamento excluído."})


@app.route("/api/ativos", methods=["POST"])
@admin_required
def api_criar():
    return _criar(request.get_json(silent=True) or {})


@app.route("/api/ativos/<int:ativo_id>", methods=["PUT"])
@admin_required
def api_atualizar(ativo_id):
    return _atualizar(ativo_id, request.get_json(silent=True) or {})


@app.route("/api/ativos/<int:ativo_id>", methods=["DELETE"])
@admin_required
def api_excluir(ativo_id):
    return _excluir(ativo_id)


# Rotas originais (mantidas para compatibilidade)
@app.route("/api/registrar", methods=["POST"])
@admin_required
def registrar():
    return _criar(request.get_json(silent=True) or {})


@app.route("/api/editar/<int:ativo_id>", methods=["PUT"])
@admin_required
def editar(ativo_id):
    return _atualizar(ativo_id, request.get_json(silent=True) or {})


@app.route("/api/remover/<serie>/<int:ativo_id>", methods=["DELETE"])
@admin_required
def remover(serie, ativo_id):
    return _excluir(ativo_id, serie)


@app.route("/api/admin/info", methods=["GET"])
@admin_required
def admin_info():
    conn = get_db()
    try:
        return jsonify({
            "ok": True,
            "escola": ESCOLA_NOME,
            "assistente_ia": ia_ativa(),
            "usuarios": sorted(USERS.keys(), key=str.lower),
            "total_ativos": conn.execute("SELECT COUNT(*) AS c FROM ativos").fetchone()["c"],
            "total_historico": conn.execute("SELECT COUNT(*) AS c FROM historico").fetchone()["c"],
            "tamanho_banco_kb": round(os.path.getsize(DB_PATH) / 1024, 1) if os.path.exists(DB_PATH) else 0,
            "senhas_por_ambiente": bool(os.getenv("ADMIN_USERS")),
        })
    finally:
        conn.close()


# Exportação para Excel (somente administrador)
@app.route("/exportar", methods=["GET"])
@admin_required
def exportar():
    import pandas as pd
    from openpyxl.worksheet.properties import PageSetupProperties

    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM ativos").fetchall()
    finally:
        conn.close()
    registros = [ativo_dict(r) for r in rows]
    registros.sort(key=lambda a: (
        SERIES_ORDEM.index(a["serie_id"]) if a["serie_id"] in SERIES_ORDEM else 99, a["id"],
    ))

    cabecalhos = {
        "id": "Código", "serie_id": "Categoria", "id_computer": "ID do equipamento",
        "tipo": "Tipo", "marca": "Marca", "modelo": "Modelo", "local": "Local",
        "owner_1": "Responsável 1", "owner_2": "Responsável 2",
        "id_carregator": "Carregador", "situacao": "Situação",
        "mochila": "Mochila", "criticidade": "Criticidade",
    }
    df = pd.DataFrame(registros, columns=list(cabecalhos.keys())).rename(columns=cabecalhos)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Ativos")
        ws = writer.sheets["Ativos"]
        ws.freeze_panes = "A2"
        ws.print_title_rows = "1:1"
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        ws.oddHeader.center.text = ESCOLA_NOME
        ws.oddHeader.center.size = 11
        ws.oddFooter.center.text = "Página &P de &N"
        writer.book.properties.title = "Relatório de ativos - " + ESCOLA_NOME
        writer.book.properties.creator = ESCOLA_SIGLA
        if len(df):
            ws.auto_filter.ref = ws.dimensions
        for col in ws.columns:
            maior = max((len(str(c.value)) for c in col if c.value is not None), default=8)
            ws.column_dimensions[col[0].column_letter].width = min(max(maior + 3, 10), 40)
    buffer.seek(0)

    return send_file(
        buffer, as_attachment=True, download_name="relatorio_ativos.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# Assistente (regras + consultas ao banco, sem internet)
# O motor fica em assistente.py; aqui só preparamos os dados e o contexto.
def _base_assistente(conn):
    ativos = [ativo_dict(r) for r in conn.execute("SELECT * FROM ativos")]
    historico = [dict(r) for r in conn.execute("SELECT * FROM historico ORDER BY id DESC LIMIT 30")]
    total = conn.execute("SELECT COUNT(*) FROM historico").fetchone()[0]
    hoje = conn.execute("SELECT COUNT(*) FROM historico WHERE substr(criado_em, 1, 10) = ?", (agora()[:10],)).fetchone()[0]
    return assistente.Base(ativos, historico, total, hoje, ESCOLA_NOME, ESCOLA_SIGLA, sorted(USERS.keys(), key=str.lower))


def responder_chatbot(msg, conn, contexto=None, usuario=None, perfil=None):
    """Resposta por regras (funciona sem internet). Devolve também o contexto da conversa."""
    agora_brt = datetime.now(timezone(timedelta(hours=-3))).replace(tzinfo=None)
    return assistente.responder(msg, _base_assistente(conn), contexto, usuario, perfil or "visitor", agora_brt)


# Conversa livre (opcional): usa a API do Claude quando existe ANTHROPIC_API_KEY.
# O modelo só enxerga o inventário por ferramentas de leitura e nunca altera dados.
IA_MODELO_PADRAO = "claude-haiku-4-5-20251001"
IA_URL_PADRAO = "https://api.anthropic.com/v1/messages"
_USO_IA = {}
_IA_MAX_MENSAGENS = 40
_IA_JANELA_S = 600


def ia_ativa():
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def _enviar_nomes():
    return os.getenv("CHATBOT_ENVIAR_NOMES", "0") == "1"


def _dentro_do_limite(chave):
    agora_t = time.time()
    usos = [t for t in _USO_IA.get(chave, []) if agora_t - t < _IA_JANELA_S]
    if len(usos) >= _IA_MAX_MENSAGENS:
        _USO_IA[chave] = usos
        return False
    usos.append(agora_t)
    _USO_IA[chave] = usos
    return True


FERRAMENTAS_IA = [
    {"name": "resumo_inventario",
     "description": "Totais atuais do inventário: total, em uso, não em uso, críticos e contagens por tipo, local e categoria.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "buscar_equipamentos",
     "description": "Lista equipamentos que atendem aos filtros e informa o total encontrado. Use para contar ou listar.",
     "input_schema": {"type": "object", "properties": {
         "tipo": {"type": "string", "description": "Ex.: Notebook, Tablet, Setup, Televisão"},
         "local": {"type": "string", "description": "Nome do local, como aparece no resumo"},
         "categoria": {"type": "string", "enum": SERIES_ORDEM},
         "situacao": {"type": "string", "enum": ["Em uso", "Não em uso"]},
         "criticidade": {"type": "string", "enum": ["Sim", "Não", "Nenhuma"]},
         "texto": {"type": "string", "description": "Busca livre (ID, marca, modelo...)"},
         "limite": {"type": "integer", "description": "Quantos itens listar (padrão 10, máximo 25)"}}}},
    {"name": "historico_recente",
     "description": "Últimas alterações registradas no sistema (cadastros, edições e exclusões).",
     "input_schema": {"type": "object", "properties": {"limite": {"type": "integer"}}}},
]


def _canonico(valor, lista):
    alvo = norm(valor)
    return next((x for x in lista if norm(x) == alvo), None)


def _ferramenta_ia(nome, args, conn):
    if nome == "resumo_inventario":
        e = calcular_estatisticas(conn)
        return {k: e[k] for k in ("total", "em_uso", "nao_em_uso", "criticos", "por_tipo", "por_local", "por_serie")}
    if nome == "buscar_equipamentos":
        distintos = lambda campo: [r[0] for r in conn.execute(f"SELECT DISTINCT TRIM({campo}) FROM ativos") if r[0]]
        filtro = {}
        if args.get("tipo"):
            filtro["tipo"] = _canonico(args["tipo"], distintos("tipo")) or args["tipo"]
        if args.get("local"):
            filtro["local"] = _canonico(args["local"], distintos("local")) or args["local"]
        if args.get("categoria"):
            filtro["serie"] = str(args["categoria"]).upper()
        for k in ("situacao", "criticidade"):
            if args.get(k):
                filtro[k] = args[k]
        if args.get("texto"):
            filtro["q"] = str(args["texto"])[:80]
        itens = _filtrar_ativos(conn, filtro)
        itens.sort(key=lambda a: (SERIES_ORDEM.index(a["serie_id"]) if a["serie_id"] in SERIES_ORDEM else 99,
                                  chave_natural(a["id_computer"])))
        try:
            limite = min(max(int(args.get("limite") or 10), 1), 25)
        except (TypeError, ValueError):
            limite = 10
        saida_itens = []
        for a in itens[:limite]:
            d = {"id": a["id_computer"], "categoria": a["serie_id"], "tipo": a["tipo"], "marca": a["marca"],
                 "modelo": a["modelo"], "local": a["local"], "situacao": a["situacao"],
                 "criticidade": a["criticidade"], "mochila": a["mochila"]}
            if _enviar_nomes():
                d["responsaveis"] = [x for x in (a["owner_1"], a["owner_2"]) if x]
            saida_itens.append(d)
        return {"total_encontrado": len(itens), "exibidos": len(saida_itens), "equipamentos": saida_itens}
    if nome == "historico_recente":
        try:
            limite = min(max(int(args.get("limite") or 8), 1), 15)
        except (TypeError, ValueError):
            limite = 8
        linhas = conn.execute("SELECT * FROM historico ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
        return {"alteracoes": [{"operacao": r["operacao"], "equipamento": f"{r['tipo']} {r['id_computer']}".strip(),
                                "campo": r["campo"], "de": r["valor_anterior"], "para": r["valor_novo"],
                                "usuario": r["usuario"], "quando": r["criado_em"]} for r in linhas]}
    return {"erro": "Ferramenta desconhecida."}


def _prompt_sistema(perfil):
    return (
        f"Você é o assistente do sistema Ativos Escolares da {ESCOLA_NOME}. Ajuda a equipe e os professores a "
        "entender o sistema e a consultar o inventário de equipamentos (notebooks, tablets, setups e televisões).\n"
        "Converse de forma natural, simpática e objetiva, em português do Brasil. Respostas curtas, em parágrafos "
        "curtos, sem títulos nem tabelas; pode usar **negrito** e listas com •.\n"
        "Regras:\n"
        "1. Para qualquer número, quantidade, lista ou dado de equipamento, use as ferramentas. Nunca invente nem "
        "estime. Se não encontrar, diga que não encontrou.\n"
        "2. Você apenas consulta. Não altera dados. Se pedirem para cadastrar, editar ou excluir, explique como fazer "
        "no sistema (somente administradores fazem isso).\n"
        "3. Não peça nem revele dados pessoais de alunos.\n"
        "4. Pode conversar normalmente sobre outros assuntos, de forma breve, e retomar o tema do sistema quando fizer sentido.\n"
        f"5. O usuário atual é {'administrador' if perfil == 'admin' else 'visitante (somente consulta)'}.\n"
        "Telas do sistema: Painel, Inventário (busca e filtros), Detalhes do equipamento (abas Detalhes, QR Code e "
        "Histórico), Estatísticas, Histórico e Administração (exportar Excel, só administrador)."
    )


def _historico_para_api(historico, mensagem):
    msgs = []
    for h in (historico or [])[-8:]:
        if not isinstance(h, dict):
            continue
        papel, texto = h.get("role"), clean(h.get("content"))[:600]
        if papel not in ("user", "assistant") or not texto:
            continue
        if msgs and msgs[-1]["role"] == papel:
            msgs[-1]["content"] += "\n" + texto
        else:
            msgs.append({"role": papel, "content": texto})
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    if msgs and msgs[-1]["role"] == "user":
        msgs[-1]["content"] += "\n" + mensagem
    else:
        msgs.append({"role": "user", "content": mensagem})
    return msgs


def _chamar_api(payload):
    req = urllib.request.Request(
        os.getenv("ANTHROPIC_API_URL", IA_URL_PADRAO),
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json", "x-api-key": os.getenv("ANTHROPIC_API_KEY", ""),
                 "anthropic-version": "2023-06-01"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def responder_ia(mensagem, historico, conn, perfil):
    msgs = _historico_para_api(historico, mensagem)
    for _ in range(5):
        resp = _chamar_api({
            "model": os.getenv("CHATBOT_MODELO", IA_MODELO_PADRAO), "max_tokens": 700,
            "system": _prompt_sistema(perfil), "tools": FERRAMENTAS_IA, "messages": msgs,
        })
        blocos = resp.get("content") or []
        if resp.get("stop_reason") == "tool_use":
            msgs.append({"role": "assistant", "content": blocos})
            resultados = []
            for b in blocos:
                if b.get("type") != "tool_use":
                    continue
                try:
                    saida_f = _ferramenta_ia(b.get("name"), b.get("input") or {}, conn)
                except Exception:
                    saida_f = {"erro": "Não foi possível consultar agora."}
                resultados.append({"type": "tool_result", "tool_use_id": b.get("id"),
                                   "content": json.dumps(saida_f, ensure_ascii=False)})
            msgs.append({"role": "user", "content": resultados})
            continue
        texto = "".join(b.get("text", "") for b in blocos if b.get("type") == "text").strip()
        if texto:
            return texto
        break
    raise RuntimeError("A API não devolveu resposta.")


@app.route("/api/chatbot", methods=["POST"])
@login_required
def api_chatbot():
    data = request.get_json(silent=True) or {}
    mensagem = clean(data.get("message"))[:300]
    if not mensagem:
        return jsonify({"ok": False, "msg": "Digite uma mensagem."}), 400
    historico = data.get("history") if isinstance(data.get("history"), list) else []
    contexto = assistente.limpar_contexto(data.get("contexto"))
    conn = get_db()
    try:
        resposta = None
        if ia_ativa() and _dentro_do_limite((request.remote_addr, session.get("username"))):
            try:
                texto = responder_ia(mensagem, historico, conn, session.get("role"))
                resposta = {"reply": texto, "modo": "ia", "contexto": contexto, "suggestions": [
                    "Faça um resumo dos equipamentos", "Quais locais têm mais equipamentos?",
                    "Tem algum equipamento crítico?", "Como cadastro um equipamento?"]}
            except Exception as e:
                app.logger.warning("Assistente: conversa livre indisponível (%s). Usando o modo offline.", type(e).__name__)
        if resposta is None:
            resposta = responder_chatbot(mensagem, conn, contexto, session.get("username"), session.get("role"))
            resposta["modo"] = "regras"
    finally:
        conn.close()
    return jsonify({"ok": True, **resposta})


# Tratamento de erros
@app.errorhandler(404)
def not_found(_e):
    if is_api_request():
        return jsonify({"ok": False, "msg": "Rota não encontrada."}), 404
    if request.path.startswith("/static/"):
        return "Arquivo não encontrado.", 404
    if session.get("authenticated"):
        return redirect(url_for("index"))
    return redirect(url_for("login_page"))


@app.errorhandler(405)
def metodo_nao_permitido(_e):
    return jsonify({"ok": False, "msg": "Método não permitido."}), 405


@app.errorhandler(500)
def server_error(_e):
    if is_api_request():
        return jsonify({"ok": False, "msg": "Erro interno no servidor. Tente novamente."}), 500
    return render_template("login.html", erro="Ocorreu um erro inesperado. Tente novamente.", aviso=None), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
