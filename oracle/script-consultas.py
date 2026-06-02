"""
=============================================================================
  benchmark_oracle_final.py — Benchmark Oracle 19c Docker
  Requisitos: pip install oracledb
=============================================================================
"""

import csv
import statistics
import time
import oracledb
import sys

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

DB_CONFIG = {
    "user":     "SeuUser",
    "password": "SuaSenha",
    "dsn":      "AMBIENTE:PORTA/SERVIÇO",
}

EXECUCOES = 7

VOLUMES = {
    "3M":  "LOG_2025_3M",
    "10M": "LOG_2025_10M",
    "50M": "LOG_2025_50M",
}

CSV_FILE = "benchmark_oracle.csv"


CONSULTAS = [
    {
        "id": "Q01",
        "descricao": "DISTINCT com extração de string e agrupamento (Limit 25M)",
        "sql": """
            SELECT
                ID_LOG_TIPO AS log_tipo,
                TO_CHAR(SUBSTR(VALOR_ATUAL, INSTR(VALOR_ATUAL, 'papel de ') + 9)) AS local,
                HORA AS hora,
                IP_COMPUTADOR AS ip_computador
            FROM (
                SELECT ID_LOG_TIPO, VALOR_ATUAL, HORA, IP_COMPUTADOR
                FROM {tabela}
                WHERE ID_LOG_TIPO IN (96, 117)
                  AND DATA >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
                  AND DATA <  TO_DATE('2025-03-01', 'YYYY-MM-DD')
                  AND ROWNUM <= 25000000
            )
            GROUP BY ID_LOG_TIPO,
                     TO_CHAR(SUBSTR(VALOR_ATUAL, INSTR(VALOR_ATUAL, 'papel de ') + 9)),
                     HORA,
                     IP_COMPUTADOR
        """
    },
    {
        "id": "Q02",
        "descricao": "COUNT simples com filtro de data",
        "sql": """
            SELECT COUNT(*)
            FROM {tabela}
            WHERE DATA >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
              AND DATA <  TO_DATE('2025-03-01', 'YYYY-MM-DD')
        """
    },
    {
        "id": "Q03",
        "descricao": "Filtro por ID_USU (Limit 25M)",
        "sql": """
            SELECT ID_LOG, ID_LOG_TIPO, IP_COMPUTADOR, DATA, TABELA, VALOR_ATUAL
            FROM (
                SELECT ID_LOG, ID_LOG_TIPO, IP_COMPUTADOR, DATA, TABELA, VALOR_ATUAL
                FROM {tabela}
                WHERE ID_USU = 1
                  AND DATA >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
                  AND DATA <  TO_DATE('2025-03-01', 'YYYY-MM-DD')
                  AND ROWNUM <= 25000000
            )
        """
    },
    {
        "id": "Q04",
        "descricao": "Filtro por IP_COMPUTADOR (Limit 25M)",
        "sql": """
            SELECT ID_LOG, ID_LOG_TIPO, DATA, TABELA, VALOR_ATUAL
            FROM (
                SELECT ID_LOG, ID_LOG_TIPO, DATA, TABELA, VALOR_ATUAL
                FROM {tabela}
                WHERE IP_COMPUTADOR = 'Servidor'
                  AND DATA >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
                  AND DATA <  TO_DATE('2025-03-01', 'YYYY-MM-DD')
                  AND ROWNUM <= 25000000
            )
        """
    },
    {
        "id": "Q05",
        "descricao": "Filtro composto: data + id_log_tipo + tabela (Limit 25M)",
        "sql": """
            SELECT ID_LOG, ID_LOG_TIPO, IP_COMPUTADOR, DATA, TABELA, VALOR_ATUAL
            FROM (
                SELECT ID_LOG, ID_LOG_TIPO, IP_COMPUTADOR, DATA, TABELA, VALOR_ATUAL
                FROM {tabela}
                WHERE ID_LOG_TIPO IN (96, 117)
                  AND TABELA = 'Arquivo'
                  AND DATA >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
                  AND DATA <  TO_DATE('2025-03-01', 'YYYY-MM-DD')
                  AND ROWNUM <= 25000000
            )
        """
    },
    {
        "id": "Q6",
        "descricao": "Agregacao COUNT por IP_COMPUTADOR",
        "sql": """
            SELECT IP_COMPUTADOR, COUNT(*) AS total
            FROM {tabela}
            WHERE DATA >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
              AND DATA <  TO_DATE('2025-03-01', 'YYYY-MM-DD')
            GROUP BY IP_COMPUTADOR
            ORDER BY total DESC
        """
    },
    {
        "id": "Q07",
        "descricao": "Filtro por nome do tipo de log (Limit 25M)",
        "sql": """
            SELECT *
            FROM (
                SELECT l.*, lt.LOG_TIPO AS LOG_TIPO_DESCRICAO
                FROM (
                    SELECT *
                    FROM {tabela}
                    WHERE DATA >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
                      AND DATA <  TO_DATE('2025-03-01', 'YYYY-MM-DD')
                      AND ROWNUM <= 25000000
                ) l
                JOIN SYSTEM.LOG_TIPO lt ON l.ID_LOG_TIPO = lt.ID_LOG_TIPO
            )
            WHERE LOG_TIPO_DESCRICAO LIKE '%Erro%'
        """
    },
    {
        "id": "Q08",
        "descricao": "Paginacao: ultimos 1000 registros por DATA DESC",
        "sql": """
            SELECT ID_LOG, DATA, HORA, ID_LOG_TIPO, VALOR_ATUAL
            FROM (
                SELECT ID_LOG, DATA, HORA, ID_LOG_TIPO, VALOR_ATUAL
                FROM {tabela}
                WHERE DATA >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
                  AND DATA <  TO_DATE('2025-03-01', 'YYYY-MM-DD')
                ORDER BY DATA DESC
            )
            WHERE ROWNUM <= 1000
        """
    },
    {
        "id": "Q09",
        "descricao": "Busca por substring em VALOR_ATUAL (Limit 25M)",
        "sql": """
            SELECT ID_LOG, DATA, HORA, VALOR_ATUAL
            FROM (
                SELECT ID_LOG, DATA, HORA, VALOR_ATUAL
                FROM {tabela}
                WHERE VALOR_ATUAL LIKE '%papel de%'
                  AND DATA >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
                  AND DATA <  TO_DATE('2025-03-01', 'YYYY-MM-DD')
                  AND ROWNUM <= 25000000
            )
        """
    },
    {
        "id": "Q10",
        "descricao": "Agregacao COUNT por dia (DATA)",
        "sql": """
            SELECT TRUNC(DATA, 'DD') AS DIA, COUNT(*) AS TOTAL
            FROM {tabela}
            WHERE DATA >= TO_DATE('2025-01-01', 'YYYY-MM-DD')
              AND DATA <  TO_DATE('2025-03-01', 'YYYY-MM-DD')
            GROUP BY TRUNC(DATA, 'DD')
            ORDER BY TRUNC(DATA, 'DD') ASC
        """
    },
]

# ============================================================================
# FUNÇÕES
# ============================================================================

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def executar_consulta(conn, sql):
    with conn.cursor() as cursor:
        inicio = time.perf_counter()
        cursor.execute(sql)
        linhas = cursor.fetchall()
        tempo  = time.perf_counter() - inicio
    return tempo, len(linhas)

def benchmark_consulta(conn, consulta, volume, tabela, writer, csvfile, todos_resultados):
    sql     = consulta["sql"].format(tabela=tabela)
    tempos  = []

    for i in range(1, EXECUCOES + 1):
        try:
            tempo, qtd = executar_consulta(conn, sql)
        except Exception as e:
            log(f"  ERRO {consulta['id']} exec {i}: {e}")
            tempo, qtd = 0, 0

        tempos.append(tempo)
        nivel = "RAPIDO" if tempo < 1.0 else "MEDIO" if tempo < 10.0 else "LENTO"
        print(f"     [{nivel}]  Exec {i:02d}: {tempo:.4f}s | {qtd:,} linhas")

        writer.writerow({
            "timestamp":  time.strftime("%Y-%m-%d %H:%M:%S"),
            "banco":      "Oracle19c",
            "volume":     volume,
            "tabela":     tabela,
            "consulta_id":consulta["id"],
            "descricao":  consulta["descricao"],
            "execucao":   i,
            "tempo_s":    round(tempo, 6),
            "linhas":     qtd,
        })

        csvfile.flush()

    media   = round(statistics.mean(tempos), 4)
    minimo  = round(min(tempos), 4)
    maximo  = round(max(tempos), 4)
    mediana = round(statistics.median(tempos), 4)
    desvio  = round(statistics.stdev(tempos) if len(tempos) > 1 else 0, 4)

    print(f"\n     [STATS]  Min: {minimo}s | Max: {maximo}s | Media: {media}s | Mediana: {mediana}s")

    todos_resultados.append({
        "volume":     volume,
        "tabela":     tabela,
        "consulta_id":consulta["id"],
        "descricao":  consulta["descricao"],
        "media_s":    media,
        "min_s":      minimo,
        "max_s":      maximo,
        "mediana_s":  mediana,
        "desvio_s":   desvio,
    })

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("  BENCHMARK ORACLE 19c")
    print(f"  Inicio: {time.strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 70)

    log("Conectando ao Oracle 19c...")
    try:
        conn = oracledb.connect(**DB_CONFIG)
        log("Conexao OK")
    except Exception as e:
        log(f"ERRO: {e}")
        sys.exit(1)

    todos_resultados = []
    inicio_total     = time.perf_counter()

    campos_csv = ["timestamp", "banco", "volume", "tabela", "consulta_id",
                  "descricao", "execucao", "tempo_s", "linhas"]

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=campos_csv)
        writer.writeheader()

        for volume, tabela in VOLUMES.items():
            print(f"\n{'='*70}")
            print(f"  VOLUME: {volume} — Tabela: {tabela}")
            print(f"{'='*70}")

            for consulta in CONSULTAS:
                print(f"\n  [{consulta['id']}] {consulta['descricao']}")
                print("  " + "-" * 60)
                benchmark_consulta(conn, consulta, volume, tabela, writer, csvfile, todos_resultados)

    conn.close()
    elapsed = time.perf_counter() - inicio_total

    print()
    print("=" * 70)
    print("  RESUMO FINAL")
    print("=" * 70)
    print(f"  {'Vol':<6} {'Consulta':<6} {'Media (s)':<12} {'Min (s)':<12} {'Mediana (s)':<14} {'Descricao'}")
    print("  " + "-" * 70)
    for r in todos_resultados:
        print(f"  {r['volume']:<6} {r['consulta_id']:<6} {r['media_s']:<12} {r['min_s']:<12} {r['mediana_s']:<14} {r['descricao'][:40]}")

    print("=" * 70)
    print(f"  CSV salvo: {CSV_FILE}")
    print(f"  Duracao total: {elapsed:.1f}s")
    print("=" * 70)

if __name__ == "__main__":
    main()
