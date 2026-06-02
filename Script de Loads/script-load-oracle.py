"""
=============================================================================
  load_oracle.py — Carga dos CSVs no Oracle via Python
  Requisitos: pip install pandas oracledb
=============================================================================
"""

import pandas as pd
import oracledb
import time
import sys

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO
# ---------------------------------------------------------------------------

HOST     = "AMBIENTE"
PORT     = 'PORTA'
SERVICE  = "SERVICO"
USER     = "SeuUser"
PASSWORD = "SuaSenha"

CARGAS = [
    {
        "arquivo": r"C:\Users\user\Desktop\base-3m\log_2025_3m.csv",
        "tabela":  "LOG_2025_3M",
        "truncar": False,
    },
     {
        "arquivo": r"C:\Users\user\Desktop\base-10m\log_2025_10m.csv",
        "tabela":  "LOG_2025_10M",
        "truncar": False,
    },
]

CHUNK_SIZE = 15_000
ENCODING   = "utf-8"
SEPARADOR  = ","

FORMATOS_DATA = [
    "%d/%m/%Y",   
    "%d/%m/%y",   
    "%Y-%m-%d",  
]

COLUNAS_DATA = ["DATA", "HORA"]
COLUNAS_NUM  = ["ID_LOG", "ID_LOG_TIPO", "ID_USU", "CODIGO_TEMP", "ID_TABELA", "QTD_ERROS_DIA"]

_formato_detectado_data = None
_formato_detectado_hora = None

# ---------------------------------------------------------------------------
# FUNÇÕES
# ---------------------------------------------------------------------------

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def detectar_formato(valores_amostra: list, nome_col: str) -> str | None:
    """Retorna o primeiro formato que parseia >= 90% da amostra."""
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


def preparar_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
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
    return chunk


def diagnosticar_csv(arquivo: str) -> None:
    log("=== DIAGNÓSTICO DO CSV ===")
    try:
        amostra = pd.read_csv(
            arquivo, sep=SEPARADOR, encoding=ENCODING,
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


def inserir_chunk(cursor, tabela: str, chunk: pd.DataFrame):
    colunas = list(chunk.columns)
    placeholders = ", ".join(f":{i+1}" for i in range(len(colunas)))
    sql = f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({placeholders})"

    dados = [
        tuple(None if (isinstance(v, float) and v != v) else v for v in row)
        for row in chunk.itertuples(index=False, name=None)
    ]

    cursor.executemany(sql, dados, batcherrors=True)

    erros = cursor.getbatcherrors()
    if erros:
        for erro in erros[:5]:
            print(f"\n  [AVISO] Linha {erro.offset}: {erro.message}")
        if len(erros) > 5:
            print(f"\n  ... e mais {len(erros) - 5} erros omitidos")


def carregar(carga: dict, conn) -> int:
    global _formato_detectado_data, _formato_detectado_hora
    _formato_detectado_data = None
    _formato_detectado_hora = None

    arquivo = carga["arquivo"]
    tabela  = carga["tabela"].upper()
    truncar = carga["truncar"]

    log(f"Iniciando carga: {tabela}")
    log(f"Arquivo: {arquivo}")
    diagnosticar_csv(arquivo)

    cursor = conn.cursor()
    cursor.prefetchrows = 0

    if truncar:
        cursor.execute(f"TRUNCATE TABLE {tabela}")
        conn.commit()
        log(f"Tabela {tabela} truncada.")

    total         = 0
    chunk_n       = 0
    n_datas_nulas = 0
    inicio        = time.perf_counter()

    for chunk in pd.read_csv(
        arquivo, sep=SEPARADOR, encoding=ENCODING,
        chunksize=CHUNK_SIZE, dtype=str, on_bad_lines="skip",
    ):
        chunk_n += 1
        chunk = preparar_chunk(chunk)

        if "DATA" in chunk.columns:
            n_datas_nulas += chunk["DATA"].isna().sum()

        inserir_chunk(cursor, tabela, chunk)
        conn.commit()

        total  += len(chunk)
        elapsed = time.perf_counter() - inicio
        print(f"  Lote {chunk_n:4d} | {total:>12,} registros | {total/elapsed:>10,.0f} reg/s", end="\r")

    cursor.close()
    elapsed = time.perf_counter() - inicio
    print()
    log(f"Concluído: {total:,} registros em {elapsed:.1f}s  ({total/elapsed:,.0f} reg/s médio)")

    if n_datas_nulas > 0:
        pct = n_datas_nulas / max(total, 1) * 100
        log(f"  AVISO: {n_datas_nulas:,} registros com DATA nula ({pct:.1f}%) — verifique o CSV.")

    return total


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    log("Conectando ao Oracle...")
    try:
        conn = oracledb.connect(user=USER, password=PASSWORD, dsn=f"{HOST}:{PORT}/{SERVICE}")
        with conn.cursor() as c:
            c.execute("SELECT 1 FROM DUAL")
        log("Conexão OK.")
    except Exception as e:
        log(f"ERRO na conexão: {e}")
        sys.exit(1)

    total_geral  = 0
    inicio_geral = time.perf_counter()

    for carga in CARGAS:
        print()
        print("=" * 65)
        try:
            total = carregar(carga, conn)
            total_geral += total
        except Exception as e:
            log(f"ERRO na carga de {carga['tabela']}: {e}")

    conn.close()

    elapsed_geral = time.perf_counter() - inicio_geral
    print()
    print("=" * 65)
    log(f"CARGA COMPLETA: {total_geral:,} registros em {elapsed_geral:.1f}s")
    print("=" * 65)


if __name__ == "__main__":
    main()
