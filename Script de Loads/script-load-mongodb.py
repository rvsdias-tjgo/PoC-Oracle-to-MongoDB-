"""
=============================================================================
  load_mongodb.py — Carga dos CSVs no MongoDB
  Requisitos: pip install pandas pymongo
=============================================================================
"""

import pandas as pd
from pymongo import MongoClient
import time
import sys

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO
# ---------------------------------------------------------------------------

MONGO_URI = "mongodb://SeuUser:SuaSenha@AMBIENTE:PORTA/"
DATABASE  = "benchmark"

CARGAS = [
    {
        "arquivo":    r"C:\Users\user\Desktop\base-log-tipo\log_tipo.csv",
        "collection": "logs_tipo",
        "limpar":     False,
    },
    {
        "arquivo":    r"C:\Users\user\Desktop\base-3m\log_2025_3m.csv",
        "collection": "logs_3m",
        "limpar":     False,
    },
    {
        "arquivo":    r"C:\Users\user\Desktop\base-10m\log_2025_10m.csv",
        "collection": "logs_10m",
        "limpar":     False,
    },
]

CHUNK_SIZE = 5_000
ENCODING   = "latin1"

FORMATOS_DATA = [
    "%d/%m/%Y",   # 01/01/2025  ← padrão Oracle SQL Developer
    "%d/%m/%y",   # 01/01/25
    "%Y-%m-%d",   # 2025-01-01
]

COLUNAS_NUM = ["ID_LOG", "ID_LOG_TIPO", "ID_USU", "CODIGO_TEMP", "ID_TABELA", "QTD_ERROS_DIA"]

_formato_detectado_data = None
_formato_detectado_hora = None

# ---------------------------------------------------------------------------
# FUNÇÕES
# ---------------------------------------------------------------------------

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def detectar_formato(valores_amostra: list, nome_col: str) -> str | None:
    for fmt in FORMATOS_DATA:
        try:
            parsed = pd.to_datetime(valores_amostra, format=fmt, errors="coerce")
            if parsed.notna().mean() >= 0.9:
                log(f"  Formato detectado para {nome_col}: '{fmt}'")
                return fmt
        except Exception:
            continue
    log(f"  AVISO: formato não detectado para {nome_col}. Usando inferência (dayfirst=True).")
    return None


def converter_data(series: pd.Series, fmt: str | None) -> pd.Series:

    if fmt:
        return pd.to_datetime(series, format=fmt, errors="coerce")
    return pd.to_datetime(series, dayfirst=True, errors="coerce")


def detectar_formatos_do_chunk(chunk: pd.DataFrame) -> None:
    global _formato_detectado_data, _formato_detectado_hora

    if _formato_detectado_data is None and "DATA" in chunk.columns:
        _formato_detectado_data = detectar_formato(
            chunk["DATA"].dropna().head(20).tolist(), "DATA"
        )
    if _formato_detectado_hora is None and "HORA" in chunk.columns:
        _formato_detectado_hora = detectar_formato(
            chunk["HORA"].dropna().head(20).tolist(), "HORA"
        )


def converter_chunk(chunk: pd.DataFrame) -> list[dict]:
    detectar_formatos_do_chunk(chunk)

    if "DATA" in chunk.columns:
        chunk["DATA"] = converter_data(chunk["DATA"], _formato_detectado_data)
    if "HORA" in chunk.columns:
        chunk["HORA"] = converter_data(chunk["HORA"], _formato_detectado_hora)

    for col in COLUNAS_NUM:
        if col in chunk.columns:
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce")

    chunk = chunk.replace("nan", None)
    chunk = chunk.where(pd.notnull(chunk), None)

    registros = []
    for _, row in chunk.iterrows():
        doc = {}
        for k, v in row.items():
            if isinstance(v, float) and pd.isna(v):
                doc[k] = None
            elif hasattr(v, "to_pydatetime"):
                doc[k] = v.to_pydatetime() if pd.notna(v) else None
            else:
                doc[k] = v
        registros.append(doc)
    return registros


def diagnosticar_csv(arquivo: str) -> None:
    log("=== DIAGNÓSTICO DO CSV ===")
    try:
        amostra = pd.read_csv(
            arquivo, sep=",", encoding=ENCODING,
            nrows=10, dtype=str, on_bad_lines="skip",
        )
        for col in ["DATA", "HORA"]:
            if col in amostra.columns:
                log(f"  {col} (bruto): {amostra[col].dropna().head(5).tolist()}")
            else:
                log(f"  {col}: coluna não encontrada")
    except Exception as e:
        log(f"  ERRO no diagnóstico: {e}")
    log("==========================")


def carregar(carga: dict, db) -> int:
    global _formato_detectado_data, _formato_detectado_hora
    _formato_detectado_data = None
    _formato_detectado_hora = None

    arquivo    = carga["arquivo"]
    collection = carga["collection"]
    limpar     = carga["limpar"]

    log(f"Iniciando carga: {collection}")
    log(f"Arquivo: {arquivo}")
    diagnosticar_csv(arquivo)

    col = db[collection]
    if limpar:
        col.drop()
        log(f"Collection {collection} limpa")

    total         = 0
    chunk_n       = 0
    n_datas_nulas = 0
    inicio        = time.perf_counter()

    for chunk in pd.read_csv(
        arquivo, sep=",", encoding=ENCODING,
        chunksize=CHUNK_SIZE, dtype=str, on_bad_lines="skip",
    ):
        chunk_n += 1
        registros = converter_chunk(chunk)

        if "DATA" in chunk.columns:
            n_datas_nulas += chunk["DATA"].isna().sum()

        if registros:
            col.insert_many(registros, ordered=False)

        total  += len(registros)
        elapsed = time.perf_counter() - inicio
        print(f"  Lote {chunk_n:4d} | {total:>10,} registros | {total/elapsed:,.0f} reg/s", end="\r")

    elapsed = time.perf_counter() - inicio
    print()
    log(f"Concluído: {total:,} registros em {elapsed:.1f}s ({total/elapsed:,.0f} reg/s)")

    if n_datas_nulas > 0:
        pct = n_datas_nulas / max(total, 1) * 100
        log(f"  AVISO: {n_datas_nulas:,} registros com DATA nula ({pct:.1f}%) — verifique o CSV.")

    # Verificação pós-carga: conta documentos no período do benchmark
    from datetime import datetime
    c_periodo = col.count_documents({
        "DATA": {
            "$gte": datetime(2025, 1, 1, 0, 0, 0),
            "$lt":  datetime(2025, 3, 1, 0, 0, 0),
        }
    })
    log(f"  Docs com DATA entre 01/01/2025 e 01/03/2025: {c_periodo:,}")

    log(f"Criando índices em {collection}...")
    col.create_index("ID_LOG_TIPO")
    col.create_index("DATA")
    col.create_index([("ID_LOG_TIPO", 1), ("DATA", 1)])
    log("Índices criados")

    return total


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    log("Conectando ao MongoDB...")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        log("Conexão OK")
    except Exception as e:
        log(f"ERRO na conexão: {e}")
        sys.exit(1)

    db           = client[DATABASE]
    total_geral  = 0
    inicio_geral = time.perf_counter()

    for carga in CARGAS:
        print()
        print("=" * 60)
        total = carregar(carga, db)
        total_geral += total

    elapsed_geral = time.perf_counter() - inicio_geral
    print()
    print("=" * 60)
    log(f"CARGA COMPLETA: {total_geral:,} registros em {elapsed_geral:.1f}s")

    print()
    print("=" * 60)
    print("  RESUMO:")
    for carga in CARGAS:
        c      = db[carga["collection"]]
        total  = c.count_documents({})
        c_data = c.count_documents({"DATA": {"$ne": None}})
        pct    = c_data / max(total, 1) * 100
        print(f"  {carga['collection']:<15} {total:>12,} docs  |  DATA válida: {c_data:>12,} ({pct:.1f}%)")
    print("=" * 60)

    client.close()


if __name__ == "__main__":
    main()
