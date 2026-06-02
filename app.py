from flask import Flask, request, jsonify, render_template, send_from_directory
import sqlite3
import os

app = Flask(__name__, template_folder="templates")
DB_PATH = os.getenv("DB_PATH", "ativos.db")

db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/api/visualizar/<serie>", methods=["GET"])
def visualizar(serie):
    # Sem gambiarra de conversão: busca o termo exato enviado pelo HTML
    serie_busca = str(serie).strip().upper()
    
    conn = get_db()
    ativos = conn.execute(
        "SELECT * FROM ativos WHERE UPPER(CAST(serie_id AS TEXT)) = ?", (serie_busca,)
    ).fetchall()
    conn.close()

    return jsonify([dict(ix) for ix in ativos])

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
        data["serie_id"].strip().upper(),
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
        
    conn = get_db()
    cur = conn.execute(
        "DELETE FROM ativos WHERE id=? AND UPPER(CAST(serie_id AS TEXT))=?", (id, serie_busca)
    )
    conn.commit()
    conn.close()

    if cur.rowcount == 0:
        return jsonify({"ok": False, "msg": "Ativo não encontrado."})

    return jsonify({"ok": True, "msg": "Ativo removido com sucesso!"})

@app.route("/<path:path>")
def send_static(path):
    if os.path.exists(path) and os.path.isfile(path):
        return send_from_directory(".", path)
    return jsonify({"error": "Not Found"}), 404

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
