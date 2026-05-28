import sqlite3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DB_PATH = "ativos.db"

# ── Banco de dados ─────────────────────────────────────────────────────────

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS ativos (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                serie_id      TEXT    NOT NULL,
                owner_1       TEXT    NOT NULL,
                owner_2       TEXT    NOT NULL,
                id_computer   TEXT    NOT NULL,
                id_carregator TEXT    NOT NULL
            )
        """)

init_db()

# ── Registrar ──────────────────────────────────────────────────────────────

@app.route("/api/registrar", methods=["POST"])
def registrar():
    data  = request.get_json()
    serie = data.get("serie_id", "").strip().replace("º", "")

    if serie not in ("2", "3"):
        return jsonify({"ok": False, "msg": "Ano escolar inválido."}), 400

    with get_db() as db:
        db.execute(
            "INSERT INTO ativos (serie_id, owner_1, owner_2, id_computer, id_carregator) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                serie,
                data.get("owner_1",       "").strip(),
                data.get("owner_2",       "").strip(),
                data.get("id_computer",   "").strip(),
                data.get("id_carregator", "").strip(),
            )
        )

    return jsonify({"ok": True, "msg": "Ativo registrado com sucesso!"})

# ── Visualizar ─────────────────────────────────────────────────────────────

@app.route("/api/visualizar/<ano>")
def visualizar(ano):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM ativos WHERE serie_id = ? ORDER BY id ASC",
            (ano,)
        ).fetchall()

    result = []
    for i, a in enumerate(rows, start=1):
        nb  = f"NB-{int(a['id_computer']):02}"    if a["id_computer"].isdigit()   else "Inválido"
        car = f"CAR-{int(a['id_carregator']):02}"  if a["id_carregator"].isdigit() else "Inválido"
        result.append({
            "num":     i,
            "id":      a["id"],
            "owner_1": a["owner_1"],
            "owner_2": a["owner_2"],
            "nb":      nb,
            "car":     car,
        })

    return jsonify({"ok": True, "ativos": result, "total": len(result)})

# ── Remover ────────────────────────────────────────────────────────────────

@app.route("/api/remover/<ano>/<int:row_id>", methods=["DELETE"])
def remover(ano, row_id):
    with get_db() as db:
        ativo = db.execute(
            "SELECT * FROM ativos WHERE id = ? AND serie_id = ?",
            (row_id, ano)
        ).fetchone()

        if not ativo:
            return jsonify({"ok": False, "msg": "Ativo não encontrado."}), 404

        db.execute("DELETE FROM ativos WHERE id = ?", (row_id,))

    return jsonify({
        "ok":  True,
        "msg": f"Ativo de {ativo['owner_1']} / {ativo['owner_2']} removido."
    })

# ── Página principal ───────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
