from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
import os

app = Flask(__name__, template_folder="templates")

DB_PATH = os.getenv("DB_PATH", "ativos.db")

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
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM ativos WHERE serie_id=? ORDER BY id",
        (serie,)
    ).fetchall()
    conn.close()

    ativos = []
    for i, r in enumerate(rows, start=1):
        ativos.append({
            "id":          r["id"],
            "num":         i,
            "owner_1":     r["owner_1"],
            "owner_2":     r["owner_2"],
            "tipo":        r["tipo"],
            "marca":       r["marca"],
            "modelo":      r["modelo"],
            "local":       r["local"],
            "nb":          r["id_computer"],
            "car":         r["id_carregator"],
            "situacao":    r["situacao"],
            "mochila":     r["mochila"],
            "criticidade": r["criticidade"],
        })

    return jsonify({"ok": True, "ativos": ativos, "total": len(ativos)})

@app.route("/api/registrar", methods=["POST"])
def registrar():
    data = request.get_json()

    required = ["serie_id", "owner_1", "id_computer",
                "id_carregator", "tipo", "marca", "modelo",
                "local", "situacao", "mochila", "criticidade"]

    for field in required:
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
    conn = get_db()
    cur = conn.execute(
        "DELETE FROM ativos WHERE id=? AND serie_id=?", (id, serie)
    )
    conn.commit()
    conn.close()

    if cur.rowcount == 0:
        return jsonify({"ok": False, "msg": "Ativo não encontrado."})
    return jsonify({"ok": True, "msg": "Ativo removido com sucesso!"})

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
