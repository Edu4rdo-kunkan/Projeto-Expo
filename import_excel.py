"""
import_excel.py
Lê a planilha Dados.xlsx (tabelas lado a lado) e importa para o banco SQLite (ativos.db).

Estrutura da planilha (colunas base → nome da seção → serie_id):
  Col 0  : COMPUTADORES 2°A  → serie_id = "2"
  Col 14 : COMPUTADORES 3°A  → serie_id = "3"
  Col 28 : SETUPS             → serie_id = "SETUPS"
  Col 42 : COMPUTADORES DOS CARRINHOS → serie_id = "CARRINHOS"
  Col 56 : TABLETS            → serie_id = "TABLETS"
  Col 70 : TELEVISÃO          → serie_id = "TELEVISAO"

Row 0: nome da seção (exceto col 0, onde fica "Ativo" como cabeçalho da 1ª tabela)
Row 1: cabeçalhos das colunas de cada tabela (exceto col 0, onde fica o nome da seção "COMPUTADORES 2°A")
Row 2+: dados
"""

import pandas as pd
import sqlite3
import os

EXCEL_FILE = os.getenv("EXCEL_FILE", "Dados.xlsx")
DB_PATH    = os.getenv("DB_PATH",    "ativos.db")

# Definição das seções: (col_inicio, nome_secao, serie_id)
# Colunas padrão por seção (Ativo, Tipo, Marca, Modelo, Local, Usuários, Situação, Criticidade, Mochila/Carrinho, Carregador)
SECTIONS = [
    {"start_col": 0,  "name": "COMPUTADORES 2°A",        "serie_id": "2"},
    {"start_col": 14, "name": "COMPUTADORES 3°A",        "serie_id": "3"},
    {"start_col": 28, "name": "SETUPS",                  "serie_id": "SETUPS"},
    {"start_col": 42, "name": "COMPUTADORES DOS CARRINHOS", "serie_id": "CARRINHOS"},
    {"start_col": 56, "name": "TABLETS",                 "serie_id": "TABLETS"},
    {"start_col": 70, "name": "TELEVISAO",               "serie_id": "TELEVISAO"},
]

# Mapeamento de colunas relativas dentro de cada bloco de 13 colunas
# índice 0 = Ativo, 1 = Tipo, 2 = Marca, 3 = Modelo, 4 = Local,
# 5 = Usuários, 6 = Situação, 7 = Possui defeito?, 8 = Criticidade,
# 9 = Mochila/Carrinho, 10 = Carregador, 11 = Data, 12 = Observações
COL = {
    "ativo":       0,
    "tipo":        1,
    "marca":       2,
    "modelo":      3,
    "local":       4,
    "usuarios":    5,
    "situacao":    6,
    "defeito":     7,
    "criticidade": 8,
    "mochila":     9,
    "carregador":  10,
}

def split_users(text):
    text = str(text).strip() if pd.notna(text) else ""
    for sep in [" & ", " / ", "&", "/"]:
        if sep in text:
            parts = text.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return text, ""

def cell(row, base, offset):
    val = row.iloc[base + offset]
    return str(val).strip() if pd.notna(val) else ""

# ── 1. Ler planilha sem cabeçalho ───────────────────────────────────────
df = pd.read_excel(EXCEL_FILE, header=None)

# Dados começam na linha 2 (índice 2), linhas 0 e 1 são cabeçalhos
data_rows = df.iloc[2:].reset_index(drop=True)

records = []

for sec in SECTIONS:
    base = sec["start_col"]
    serie_id = sec["serie_id"]

    for _, row in data_rows.iterrows():
        ativo_val = cell(row, base, COL["ativo"])
        tipo_val  = cell(row, base, COL["tipo"])

        # Pular linhas vazias
        if not ativo_val and not tipo_val:
            continue

        owner_1, owner_2 = split_users(row.iloc[base + COL["usuarios"]])

        records.append({
            "serie_id":      serie_id,
            "owner_1":       owner_1,
            "owner_2":       owner_2,
            "id_computer":   ativo_val,
            "id_carregator": cell(row, base, COL["carregador"]),
            "tipo":          tipo_val,
            "marca":         cell(row, base, COL["marca"]),
            "modelo":        cell(row, base, COL["modelo"]),
            "local":         cell(row, base, COL["local"]),
            "situacao":      cell(row, base, COL["situacao"]),
            "mochila":       cell(row, base, COL["mochila"]),
            "criticidade":   cell(row, base, COL["criticidade"]),
        })

print(f"📊 {len(records)} registros encontrados na planilha.")
for sec in SECTIONS:
    count = sum(1 for r in records if r["serie_id"] == sec["serie_id"])
    print(f"   {sec['name']:35s} → {count} registros")

# ── 2. Salvar no SQLite ───────────────────────────────────────────────────
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
