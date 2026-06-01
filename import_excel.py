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

SKIP_TIPO = {"tipo", "type", "", "nan"}
SKIP_ATIVO = {"ativo", "asset", "nan"}

def split_users(text):
    text = str(text).strip()
    if not text or text.lower() == "nan":
        return "", ""
    for sep in ["&", " e ", " E ", ";", ","]:
        if sep in text:
            parts = text.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return text, ""

if not os.path.exists(EXCEL_FILE):
    print(f"❌ Erro crítico: Arquivo '{EXCEL_FILE}' não encontrado no diretório atual.")
    exit(1)

try:
    df = pd.read_excel(EXCEL_FILE, header=None)
except Exception as e:
    print(f"❌ Erro ao abrir a planilha com pandas: {e}")
    exit(1)

print(f"📋 Planilha: {df.shape[1]} colunas, {df.shape[0]} linhas totais")

records = []

for sec in SECTIONS:
    sc = sec["start_col"]
    name = sec["name"]
    sid = sec["serie_id"]
    
    if sc >= df.shape[1]:
        continue
        
    count_sec = 0
    for r in range(2, df.shape[0]):
        val_ativo = str(df.iloc[r, sc + COL["ativo"]]).strip()
        val_tipo  = str(df.iloc[r, sc + COL["tipo"]]).strip()
        
        if val_ativo.lower() in SKIP_ATIVO or val_tipo.lower() in SKIP_TIPO:
            continue
            
        u1, u2 = split_users(df.iloc[r, sc + COL["usuarios"]])
        
        rec = {
            "serie_id": str(sid).strip(),
            "owner_1": u1,
            "owner_2": u2,
            "id_computer": val_ativo,
            "id_carregator": str(df.iloc[r, sc + COL["carregador"]]).strip(),
            "tipo": val_tipo,
            "marca": str(df.iloc[r, sc + COL["marca"]]).strip(),
            "modelo": str(df.iloc[r, sc + COL["modelo"]]).strip(),
            "local": str(df.iloc[r, sc + COL["local"]]).strip(),
            "situacao": str(df.iloc[r, sc + COL["situacao"]]).strip(),
            "mochila": str(df.iloc[r, sc + COL["mochila"]]).strip(),
            "criticidade": str(df.iloc[r, sc + COL["criticidade"]]).strip(),
        }
        records.append(rec)
        count_sec += 1
    print(f"   {name:<35} → {count_sec} registros")

print(f"\n📊 Total processado da planilha: {len(records)} registros")

db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

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

total_atual = conn.execute("SELECT COUNT(*) FROM ativos").fetchone()[0]

if total_atual == 0:
    print("🔄 O volume está vazio. Populando banco de dados pela primeira vez com o Excel...")
    conn.executemany("""
        INSERT INTO ativos
            (serie_id, owner_1, owner_2, id_computer, id_carregator,
             tipo, marca, modelo, local, situacao, mochila, criticidade)
        VALUES
            (:serie_id, :owner_1, :owner_2, :id_computer, :id_carregator,
             :tipo, :marca, :modelo, :local, :situacao, :mochila, :criticidade)
    """, records)
    conn.commit()
    print("✅ Dados da planilha importados com sucesso para dentro do Volume!")
else:
    print(f"⚠️ O volume já possui {total_atual} registros. Importação do Excel ignorada para proteger suas alterações online.")

conn.close()
