import pandas as pd
import sqlite3
import os

# Configuração do Banco de Dados (Lê a variável do Railway ou usa o padrão local)
DB_PATH = os.getenv("DB_PATH", "ativos.db")

# 🔍 AUTO-DETECTAR O ARQUIVO DE DADOS (Não precisa configurar nada!)
# O código vai procurar na pasta por qualquer arquivo que comece com "dados" ou contenha "dados"
arquivo_encontrado = None
extensao_csv = False

# Lista todos os arquivos na raiz do projeto para achar o seu
for arquivo in os.listdir("."):
    nome_minusculo = arquivo.lower()
    # Procura um arquivo que tenha "dados" no nome e termine com .xlsx ou .csv
    if "dados" in nome_minusculo and (nome_minusculo.endswith(".xlsx") or nome_minusculo.endswith(".csv")):
        arquivo_encontrado = arquivo
        if nome_minusculo.endswith(".csv"):
            extensao_csv = True
        break

# Se não achou de forma inteligente, tenta os nomes padrões exatos
if not arquivo_encontrado:
    nomes_padrao = ["Dados.xlsx", "dados.xlsx", "Dados.xlsx - Planilha1.csv", "dados.csv"]
    for nome in nomes_padrao:
        if os.path.exists(nome):
            arquivo_encontrado = nome
            if nome.lower().endswith(".csv"):
                extensao_csv = True
            break

# Se mesmo assim não achar nada, avisa o erro
if not arquivo_encontrado:
    print("❌ Erro crítico: Nenhum arquivo de dados (Excel ou CSV) foi encontrado na raiz do seu projeto!")
    print("👉 Certifique-se de que o arquivo está na mesma pasta que o 'app.py' no seu GitHub.")
    exit(1)

print(f"✅ Arquivo de dados detectado automaticamente: '{arquivo_encontrado}'")

# Definição das colunas e seções da sua planilha original
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

# Realiza a leitura correta dependendo do formato que o arquivo estiver
try:
    if extensao_csv:
        df = pd.read_csv(arquivo_encontrado, header=None)
    else:
        df = pd.read_excel(arquivo_encontrado, header=None)
except Exception as e:
    print(f"❌ Erro ao abrir a planilha com o pandas: {e}")
    exit(1)

print(f"📋 Estrutura da Planilha: {df.shape[1]} colunas, {df.shape[0]} linhas detectadas.")

records = []

# Processamento das seções
for sec in SECTIONS:
    sc = sec["start_col"]
    name = sec["name"]
    sid = sec["serie_id"]
    
    if sc >= df.shape[1]:
        continue
        
    count_sec = 0
    for r in range(2, df.shape[0]):
        try:
            val_ativo = str(df.iloc[r, sc + COL["ativo"]]).strip()
            val_tipo  = str(df.iloc[r, sc + COL["tipo"]]).strip()
        except IndexError:
            # Prevenção caso alguma linha específica tenha menos colunas
            continue
        
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
    print(f"   {name:<35} → {count_sec} registros lidos")

print(f"\n📊 Total extraído da planilha: {len(records)} registros prontos para o banco.")

# Garante que a pasta do volume (/data) exista no Railway antes de criar o banco
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

conn = sqlite3.connect(DB_PATH)

# Criação da tabela caso ela não exista
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

# Verifica se o banco de dados no volume já tem registros salvos
total_atual = conn.execute("SELECT COUNT(*) FROM ativos").fetchone()[0]

if total_atual == 0:
    if len(records) > 0:
        print("🔄 O seu volume está vazio! Populando banco de dados pela primeira vez com o arquivo...")
        conn.executemany("""
            INSERT INTO ativos
                (serie_id, owner_1, owner_2, id_computer, id_carregator,
                 tipo, marca, modelo, local, situacao, mochila, criticidade)
            VALUES
                (:serie_id, :owner_1, :owner_2, :id_computer, :id_carregator,
                 :tipo, :marca, :modelo, :local, :situacao, :mochila, :criticidade)
        """, records)
        conn.commit()
        print("✅ Dados importados com sucesso para dentro do Volume persistentemente!")
    else:
        print("⚠️ Nenhum dado válido foi processado do arquivo de dados.")
else:
    print(f"⚠️ Atenção: O seu volume já possui {total_atual} registros.")
    print("   A importação automática foi pulada para proteger as alterações que você fez online no site!")

conn.close()
