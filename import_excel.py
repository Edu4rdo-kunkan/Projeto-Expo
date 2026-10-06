import pandas as pd
import sqlite3
import os
import re
import unicodedata

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

# ─────────────────────────────────────────────────────────────────────────
# LEITURA DA PLANILHA
#
# A planilha real NÃO tem as 6 categorias lado a lado em colunas separadas.
# Ela é uma única tabela (mesmas colunas) onde as categorias ficam
# EMPILHADAS uma embaixo da outra, cada bloco começando com uma linha de
# título (ex: "SETUPS", "TABLETS") seguida de uma linha de cabeçalho
# ("Ativo", "Tipo", "Marca", ...) e depois as linhas de dados daquele bloco.
#
# Por isso identificamos a categoria de cada linha pelo TÍTULO do bloco
# (varrendo de cima para baixo), em vez de por uma coluna fixa.
# ─────────────────────────────────────────────────────────────────────────

COL = {
    "ativo": 0, "tipo": 1, "marca": 2, "modelo": 3,
    "local": 4, "usuarios": 5, "situacao": 6,
    "criticidade": 8, "mochila": 9, "carregador": 10,
}

SKIP_TIPO = {"tipo", "type", "", "nan"}
SKIP_ATIVO = {"ativo", "asset", "nan"}


def normalizar(texto):
    """minúsculas, sem acento e sem símbolos, só letras/números/espaço."""
    texto = str(texto).strip().lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    texto = re.sub(r"[^a-z0-9 ]", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


# Título do bloco (já normalizado) -> serie_id usado no banco de dados.
TITULOS_SERIE = {
    "computadores 2a": "2A",
    "computadores 3a": "3A",
    "setups": "SETUPS",
    "computadores dos carrinhos": "CARRINHOS",
    "carrinhos": "CARRINHOS",
    "tablets": "TABLETS",
    "televisao": "TELEVISAO",
}

# Se a célula "Tipo" vier vazia mas a linha claramente pertence a um bloco
# conhecido (ex: TVs cadastradas sem preencher a coluna Tipo), preenchemos
# com o tipo padrão daquele bloco em vez de descartar o ativo.
TIPO_PADRAO_POR_SERIE = {
    "2A": "Notebook",
    "3A": "Notebook",
    "SETUPS": "Setup",
    "CARRINHOS": "Notebook",
    "TABLETS": "Tablet",
    "TELEVISAO": "Televisão",
}


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
serie_atual = None
contagem_por_serie = {}
contador_ids_vistos = {}  # (serie, id_computer_original) -> quantas vezes já apareceu

for r in range(df.shape[0]):
    try:
        val_col0 = df.iloc[r, COL["ativo"]]
    except IndexError:
        continue

    titulo_normalizado = normalizar(val_col0)

    # Linha de título de um novo bloco/categoria?
    if titulo_normalizado in TITULOS_SERIE:
        serie_atual = TITULOS_SERIE[titulo_normalizado]
        continue

    # Linha de cabeçalho ("Ativo", "Tipo", "Marca", ...)? Ignora sem mudar a série.
    if str(val_col0).strip().lower() == "ativo":
        continue

    # Ainda não entramos em nenhum bloco conhecido (linhas antes do 1º título).
    if serie_atual is None:
        continue

    try:
        val_ativo = str(df.iloc[r, COL["ativo"]]).strip()
        val_tipo = str(df.iloc[r, COL["tipo"]]).strip()
    except IndexError:
        continue

    if val_ativo.lower() in SKIP_ATIVO:
        continue

    if val_tipo.lower() in SKIP_TIPO:
        # Tenta preencher com o tipo padrão do bloco em vez de perder o ativo.
        val_tipo = TIPO_PADRAO_POR_SERIE.get(serie_atual, "")
        if not val_tipo:
            continue

    u1, u2 = split_users(df.iloc[r, COL["usuarios"]])

    # Algumas categorias (Setups, Televisão) usam "N/" ou "*" repetido em
    # TODAS as linhas como "Ativo" (não têm um número de patrimônio real).
    # Sem isso, a 2ª linha em diante "atualizaria" a 1ª por engano, pois o
    # sistema identifica um ativo já existente pela dupla (id_computer, serie).
    # Aqui, a 1ª ocorrência mantém o texto original; da 2ª em diante,
    # acrescentamos um sufixo estável (-2, -3, ...) para diferenciar.
    chave_dup = (serie_atual, val_ativo)
    vezes_visto = contador_ids_vistos.get(chave_dup, 0)
    contador_ids_vistos[chave_dup] = vezes_visto + 1
    id_computer_final = val_ativo if vezes_visto == 0 else f"{val_ativo}-{vezes_visto + 1}"

    rec = {
        "serie_id": str(serie_atual).strip().upper(),
        "owner_1": u1,
        "owner_2": u2,
        "id_computer": id_computer_final,
        "id_carregator": str(df.iloc[r, COL["carregador"]]).strip(),
        "tipo": val_tipo,
        "marca": str(df.iloc[r, COL["marca"]]).strip(),
        "modelo": str(df.iloc[r, COL["modelo"]]).strip(),
        "local": str(df.iloc[r, COL["local"]]).strip(),
        "situacao": str(df.iloc[r, COL["situacao"]]).strip(),
        "mochila": str(df.iloc[r, COL["mochila"]]).strip(),
        "criticidade": str(df.iloc[r, COL["criticidade"]]).strip(),
    }
    records.append(rec)
    contagem_por_serie[rec["serie_id"]] = contagem_por_serie.get(rec["serie_id"], 0) + 1

if not records:
    print("⚠️  Nenhum ativo foi reconhecido na planilha. Verifique se os títulos dos blocos "
          "(ex: 'SETUPS', 'TABLETS') continuam com a mesma grafia esperada.")

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

# ATUALIZAÇÃO INTELIGENTE (Não apaga mais a tabela inteira!)
inseridos = 0
atualizados = 0

for rec in records:
    # Verifica se esse ID de computador já existe nessa mesma categoria/turma
    existe = conn.execute(
        "SELECT id FROM ativos WHERE id_computer = ? AND serie_id = ?", 
        (rec["id_computer"], rec["serie_id"])
    ).fetchone()
    
    if existe:
        # Se já existe, atualiza os dados dele vindo do Excel
        conn.execute("""
            UPDATE ativos SET
                owner_1 = ?, owner_2 = ?, id_carregator = ?, tipo = ?, 
                marca = ?, modelo = ?, local = ?, situacao = ?, mochila = ?, criticidade = ?
            WHERE id_computer = ? AND serie_id = ?
        """, (
            rec["owner_1"], rec["owner_2"], rec["id_carregator"], rec["tipo"],
            rec["marca"], rec["modelo"], rec["local"], rec["situacao"], rec["mochila"], rec["criticidade"],
            rec["id_computer"], rec["serie_id"]
        ))
        atualizados += 1
    else:
        # Se não existe, insere como novo
        conn.execute("""
            INSERT INTO ativos
                (serie_id, owner_1, owner_2, id_computer, id_carregator,
                 tipo, marca, modelo, local, situacao, mochila, criticidade)
            VALUES
                (:serie_id, :owner_1, :owner_2, :id_computer, :id_carregator,
                 :tipo, :marca, :modelo, :local, :situacao, :mochila, :criticidade)
        """, rec)
        inseridos += 1

conn.commit()
print(f"✅ Processamento concluído: {inseridos} novos adicionados | {atualizados} atualizados. Cadastros feitos pelo site foram preservados!")
print("   Ativos encontrados por categoria:", contagem_por_serie)
conn.close()
