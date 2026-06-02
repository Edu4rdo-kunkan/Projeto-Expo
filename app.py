from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
import os

app = Flask(__name__, template_folder="templates")

# Caminho apontando diretamente para o volume definitivo do Railway
DB_PATH = os.getenv("DB_PATH", "ativos.db")

# Garante que a pasta do volume exista na nuvem antes de conectar
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
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
    conn.commit()
    conn.close()

init_db()

@app.route("/api/visualizar/<serie>", methods=["GET"])
def visualizar(serie):
    serie_busca = str(serie).strip().upper()
    if serie_busca == "2A":
        serie_busca = "2"
    elif serie_busca == "3A":
        serie_busca = "3"
    
    conn = get_db()
    cursor = conn.execute("SELECT * FROM ativos WHERE CAST(serie_id AS TEXT) = ?", (serie_busca,))
    rows = cursor.fetchall()
    conn.close()

    ativos_list = [dict(row) for row in rows]
    return jsonify(ativos_list)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/registrar", methods=["POST"])
def registrar():
    data = request.json or {}
    campos_obrigatorios = ["serie_id", "owner_1", "id_computer", "id_carregator", "tipo", "marca", "modelo", "local", "situacao", "mochila", "criticidade"]
    
    for field in campos_obrigatorios:
        if not data.get(field, "").strip():
            return jsonify({"ok": False, "msg": f"Campo obrigatório: {field}"})

    conn = get_db()
    conn.execute("""
        INSERT INTO ativos
            (serie_id, owner_1, owner_2, id_computer, id_carregator,
             tipo, marca, modelo, local, situacao, mochila, criticidade)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data["serie_id"].strip(),
        data["owner_1"].strip(),
        data.get("owner_2", "").strip(),
        data["id_computer"].strip(),
        data["id_carregator"].strip(),
        data["tipo"].strip(),
        data["marca"].strip(),
        data["modelo"].strip(),
        data["local"].strip(),
        data["situacao"].strip(),
        data["mochila"].strip(),
        data["criticidade"].strip(),
    ))
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "msg": "Ativo registrado com sucesso!"})

@app.route("/api/remover/<serie>/<int:id>", methods=["DELETE"])
def remover(serie, id):
    serie_busca = str(serie).strip().upper()
    if serie_busca == "2A":
        serie_busca = "2"
    elif serie_busca == "3A":
        serie_busca = "3"
        
    conn = get_db()
    cur = conn.execute(
        "DELETE FROM ativos WHERE id=? AND CAST(serie_id AS TEXT)=?", (id, serie_busca)
    )
    conn.commit()
    conn.close()

    if cur.rowcount == 0:
        return jsonify({"ok": False, "msg": "Ativo não encontrado ou já removido."})

    return jsonify({"ok": True, "msg": "Ativo removido com sucesso!"})

# Rota genérica modificada para não interceptar as rotas da API de forma errada
@app.route("/<path:path>")
def send_static(path):
    # Se o arquivo solicitado existir na pasta raiz, ele envia. Caso contrário, manda 404 de forma limpa.
    if os.path.exists(path) and os.path.isfile(path):
        return send_from_directory(".", path)
    return jsonify({"error": "Not Found"}), 404

if __name__ == "__main__":
    # O Railway exige dinamicamente usar a variável de ambiente PORT
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
