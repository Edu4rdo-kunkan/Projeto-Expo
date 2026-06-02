import pandas as pd
import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "ativos.db")

arquivo_encontrado = None
extensao_csv = False

for arquivo in os.listdir("."):
    nome_minusculo = arquivo.lower()
    if "dados" in nome_minusculo and (nome_minusculo.endswith(".xlsx") or nome_minusculo.endswith(".csv")):
        arquivo_encontrado = arquivo
        if nome_minusculo.endswith(".csv"):
            extensao_csv = True
        break

if not arquivo_encontrado:
    nomes_padrao = ["Dados.xlsx", "dados.xlsx", "Dados.xlsx - Planilha1.csv", "dados.csv"]
    for nome in nomes_padrao:
        if os.path.exists(nome):
            arquivo_encontrado = nome
            if nome.lower().endswith(".csv"):
                extensao_csv = True
            break

if not arquivo_encontrado:
    print("❌ Erro crítico: Nenhum arquivo de dados (Excel ou CSV) foi encontrado!")
    exit(1)

# PADRONIZADO: Salvando com os IDs exatos que o site (HTML) usa
SECTIONS = [
    {"start_col": 0,  "name": "COMPUTADORES 2°A",           "serie_id": "2A"},
    {"start_col": 14, "name": "COMPUTADORES 3°A",           "serie_id": "3A"},
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

try:
    if extensao_csv:
        df = pd.read_csv(arquivo_encontrado, header=None)
    else:
        df = pd.read_excel(arquivo_encontrado, header=None)
except Exception as e:
    print(f"❌ Erro ao abrir a planilha: {e}")
    exit(1)

records = []

for sec in SECTIONS:
    sc = sec["start_col"]
    name = sec["name"]
    sid = sec["serie_id"]
    
    if sc >= df.shape[1]:
        continue
        
    for r in range(2, df.shape[0]):
        try:
            val_ativo = str(df.iloc[r, sc + COL["ativo"]]).strip()
            val_tipo  = str(df.iloc[r, sc + COL["tipo"]]).strip()
        except IndexError:
            continue
        
        if val_ativo.lower() in SKIP_ATIVO or val_tipo.lower() in SKIP_TIPO:
            continue
            
        u1, u2 = split_users(df.iloc[r, sc + COL["usuarios"]])
        
        rec = {
            "serie_id": str(sid).strip().upper(),
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

# MODIFICAÇÃO AQUI: Limpa o banco antigo para aceitar as atualizações e novos ativos do Excel
conn.execute("DELETE FROM ativos") 

if len(records) > 0:
    conn.executemany("""
        INSERT INTO ativos
            (serie_id, owner_1, owner_2, id_computer, id_carregator,
             tipo, marca, modelo, local, situacao, mochila, criticidade)
        VALUES
            (:serie_id, :owner_1, :owner_2, :id_computer, :id_carregator,
             :tipo, :marca, :modelo, :local, :situacao, :mochila, :criticidade)
    """, records)
    conn.commit()
    print(f"✅ Sucesso! {len(records)} registros atualizados diretamente do Excel.")

conn.close()
