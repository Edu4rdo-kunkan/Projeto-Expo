"""
import_excel.py
Lê a planilha Dados.xlsx e importa os dados para o banco SQLite (ativos.db).

Seções reconhecidas:
  COMPUTADORES 2°A   → serie_id = "2"
  COMPUTADORES 3°A   → serie_id = "3"

Colunas usadas da planilha:
  Ativo      → id_computer  (número do notebook)
  Tipo       → tipo
  Marca      → marca
  Modelo     → modelo
  Local      → local
  Usuários   → owner_1 / owner_2  (dividido no separador & ou /)
  Situação   → situacao
  Criticidade→ criticidade
  Mochila    → mochila
  Carregador → id_carregator
"""

import pandas as pd
import sqlite3
import os
import re

EXCEL_FILE = os.getenv("EXCEL_FILE", "Dados.xlsx")
DB_PATH    = os.getenv("DB_PATH",    "ativos.db")

# ── 1. Ler planilha ───────────────────────────────────────────────────────
df = pd.read_excel(EXCEL_FILE)
df.columns = df.columns.str.strip()
df = df.where(pd.notna(df), "")          # NaN → string vazia

# ── 2. Detectar seções (linhas onde Tipo está vazio e Ativo tem texto) ────
SECTION_MAP = {
    "COMPUTADORES 2": "2",
    "COMPUTADORES 3": "3",
}

def get_serie(header: str) -> str | None:
    h = str(header).upper().strip()
    for key, val in SECTION_MAP.items():
        if key in h:
            return val
    return None

# ── 3. Percorrer linhas e agrupar por série ───────────────────────────────
def split_users(text: str):
    """Divide 'João & Maria' em ('João', 'Maria'), ou ('João', '') se só um."""
    text = str(text).strip()
    for sep in [" & ", " / ", "&", "/"]:
        if sep in text:
            parts = text.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return text, ""

records = []
current_serie = None

for _, row in df.iterrows():
    tipo_val = str(row.get("Tipo", "")).strip()
    ativo_val = str(row.get("Ativo", "")).strip()

    # Linha de cabeçalho de seção?
    if not tipo_val and ativo_val:
        s = get_serie(ativo_val)
        if s:
            current_serie = s
        continue

    # Linha de dados sem série definida → pular
    if not current_serie:
        continue

    # Pular linhas completamente vazias
    if not ativo_val and not tipo_val:
        continue

    owner_1, owner_2 = split_users(row.get("Usuários", ""))

    records.append({
        "serie_id":      current_serie,
        "owner_1":       owner_1,
        "owner_2":       owner_2,
        "id_computer":   ativo_val,
        "id_carregator": str(row.get("Carregador", "")).strip(),
        "tipo":          tipo_val,
        "marca":         str(row.get("Marca",     "")).strip(),
        "modelo":        str(row.get("Modelo",    "")).strip(),
        "local":         str(row.get("Local",     "")).strip(),
        "situacao":      str(row.get("Situação",  "")).strip(),
        "mochila":       str(row.get("Mochila",   "")).strip(),
        "criticidade":   str(row.get("Criticidade","")).strip(),
    })

print(f"📊 {len(records)} registros encontrados na planilha.")

# ── 4. Salvar no SQLite ───────────────────────────────────────────────────
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

# Limpar dados antigos (reimportação limpa)
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
