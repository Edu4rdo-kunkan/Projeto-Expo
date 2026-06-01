import pandas as pd
import sqlite3
import os

EXCEL_FILE = os.getenv("EXCEL_FILE", "Dados.xlsx")
DB_PATH    = os.getenv("DB_PATH",    "ativos.db")

SECTIONS = [
    {"start_col": 0,  "name": "COMPUTADORES 2°A",           "serie_id": "2"},
    {"start_col": 14, "name": "COMPUTADORES 3°A",           "serie_id": "3"},
    {"start_col": 28, "name": "SETUPS",                     "serie_id": "SETUPS"},
    {"start_col": 42, "name": "COMPUTADORES DOS CARRINHOS", "serie_id": "CARRINHOS"},
    {"start_col": 56, "name": "TABLETS",                    "serie_id": "TABLETS"},
    {"start_col": 70, "name": "TELEVISAO",                  "serie_id": "TELEVISAO"},
]

COL = {
    "ativo": 0, "tipo": 1, "marca": 2, "modelo": 3,
    "local": 4, "usuarios": 5, "situacao": 6,
    "criticidade": 8, "mochila": 9, "carregador": 10,
}

def split_users(text):
    text = str(text).strip() if pd.notna(text) else ""
    for sep in [" & ", " / ", "&", "/"]:
        if sep in text:
            parts = text.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return text, ""

def safe_cell(row, base, offset, total_cols):
    idx = base + offset
    if idx >= total_cols:
        return ""
    val = row.iloc[idx]
    return str(val).strip() if pd.notna(val) else ""

df = pd.read_excel(EXCEL_FILE, header=None)
data_rows = df.iloc[2:].reset_index(drop=True)
total_cols = len(df.columns)

print(f"📋 Planilha tem {total_cols} colunas e {len(data_rows)} linhas de dados.")

records = []

for sec in SECTIONS:
    base = sec["start_col"]
    if base >= total_cols:
        print(f"⚠️  Seção '{sec['name']}' ignorada (col {base} não existe)")
        continue

    for _, row in data_rows.iterrows():
        ativo_val = safe_cell(row, base, COL["ativo"], total_cols)
        tipo_val  = safe_cell(row, base, COL["tipo"],  total_cols)

        if not ativo_val and not tipo_val:
            continue

        owner_1, owner_2 = split_users(
            row.iloc[base + COL["usuarios"]] if base + COL["usuarios"] < total_cols else ""
        )

        records.append({
            "serie_id":      sec["serie_id"],
            "owner_1":       owner_1,
            "owner_2":       owner_2,
            "id_computer":   ativo_val,
            "id_carregator": safe_cell(row, base, COL["carregador"], total_cols),
            "tipo":          tipo_val,
            "marca":         safe_cell(row, base, COL["marca"],      total_cols),
            "modelo":        safe_cell(row, base, COL["modelo"],     total_cols),
            "local":         safe_cell(row, base, COL["local"],      total_cols),
            "situacao":      safe_cell(row, base, COL["situacao"],   total_cols),
            "mochila":       safe_cell(row, base, COL["mochila"],    total_cols),
            "criticidade":   safe_cell(row, base, COL["criticidade"],total_cols),
        })

print(f"📊 {len(records)} registros encontrados na planilha.")
for sec in SECTIONS:
    count = sum(1 for r in records if r["serie_id"] == sec["serie_id"])
    if count:
        print(f"   {sec['name']:35s} → {count} registros")

conn = sqlite3.connect(DB_PATH)
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
conn.execute("DELETE FROM ativos")
conn.executemany("""
    INSERT INTO ativos
        (serie_id, owner_1, owner_2, id_computer, id_carregator,
         tipo, marca, modelo, local, situacao, mochila, criticidade)
    VALUES
        (:serie_id, :owner_1, :owner_2, :id_computer, :id_carregator,
         :tipo, :marca, :modelo, :local, :situacao, :mochila, :criticidade)
""", records)
conn.commit()
total = conn.execute("SELECT COUNT(*) FROM ativos").fetchone()[0]
print(f"✅ {total} registros importados para '{DB_PATH}' com sucesso!")
conn.close()
