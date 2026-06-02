import csv, time, oracledb

DB_CONFIG = {"user": "SeuUser", "password": "SuaSenha", "dsn": "AMBIENTE:PORTA/SERVICO"}
EXECUCOES, ARRAYSIZE = 7, 10000
VOLUMES = {"50M": "LOG_2025_50M"}
CSV_FILE = "benchmark_oracle.csv"
DEFAULTS = {"LOG_TIPO": "Download", "ORIGEM": "projudi", "ID_PENDENCIA": "440542455", "COMBO_LOG_TIPO": "Download", "COMBO_ORIGEM": "projudi"}

def regexp_campo(campo):
    return f"CAST(RTRIM(REGEXP_SUBSTR(DBMS_LOB.SUBSTR(VALOR_NOVO, 1000, 1), '{campo}:([^;]+)', 1, 1, NULL, 1), ']') AS VARCHAR2(1000))"

def get_consultas(tabela, v):
    return [
        {
            "id": "Q11",
            "descricao": f"Filtro por tipo de log (JOIN LOG_TIPO='{v['LOG_TIPO']}' - Limit 1M)",
            "sql": f"""
                SELECT l.ID_LOG, l.DATA, lt.LOG_TIPO, lt.STATUS
                FROM {tabela} l
                JOIN SYSTEM.LOG_TIPO lt ON l.ID_LOG_TIPO = lt.ID_LOG_TIPO
                WHERE lt.LOG_TIPO = '{v['LOG_TIPO']}'
                  AND ROWNUM <= 1000000
            """,
        },
        {
            "id": "Q12",
            "descricao": f"Filtro por Origem no CLOB VALOR_NOVO ('{v['ORIGEM']}' - Limit 1M)",
            "sql": f"""
                SELECT ID_LOG, DATA, {regexp_campo('Origem')} AS ORIGEM, {regexp_campo('Id_Pendencia')} AS ID_PENDENCIA
                FROM {tabela}
                WHERE VALOR_NOVO LIKE '%Origem:{v['ORIGEM']}%'
                  AND ROWNUM <= 1000000
            """,
        },
        {
            "id": "Q13",
            "descricao": f"Filtro por Id_Pendencia no CLOB VALOR_NOVO ('{v['ID_PENDENCIA']}' - Limit 1M)",
            "sql": f"""
                SELECT ID_LOG
                FROM {tabela}
                WHERE VALOR_NOVO LIKE '%Id_Pendencia:{v['ID_PENDENCIA']}%'
                  AND ROWNUM <= 1000000
            """,
        },
        {
            "id": "Q14",
            "descricao": "Agregacao COUNT por tipo de log (JOIN LOG_TIPO - Limit 1M)",
            "sql": f"""
                SELECT lt.LOG_TIPO, COUNT(*) AS total
                FROM {tabela} l
                JOIN SYSTEM.LOG_TIPO lt ON l.ID_LOG_TIPO = lt.ID_LOG_TIPO
                WHERE ROWNUM <= 1000000
                GROUP BY lt.LOG_TIPO
                ORDER BY total DESC
            """,
        },
        {
            "id": "Q15",
            "descricao": f"Combinado: LOG_TIPO='{v['COMBO_LOG_TIPO']}' + Origem='{v['COMBO_ORIGEM']}' (Limit 1M)",
            "sql": f"""
                SELECT l.ID_LOG, l.DATA, lt.LOG_TIPO, {regexp_campo('Origem').replace('VALOR_NOVO', 'l.VALOR_NOVO')} AS ORIGEM
                FROM {tabela} l
                JOIN SYSTEM.LOG_TIPO lt ON l.ID_LOG_TIPO = lt.ID_LOG_TIPO
                WHERE lt.LOG_TIPO = '{v['COMBO_LOG_TIPO']}'
                  AND l.VALOR_NOVO LIKE '%Origem:{v['COMBO_ORIGEM']}%'
                  AND ROWNUM <= 1000000
            """,
        },
    ]

def executar(conn, sql):
    with conn.cursor() as cur:
        cur.arraysize = ARRAYSIZE
        inicio = time.perf_counter()
        cur.execute(sql)
        qtd = 0
        while True:
            lote = cur.fetchmany(ARRAYSIZE)
            if not lote: break
            qtd += len(lote)
        return time.perf_counter() - inicio, qtd

def main():
    conn = oracledb.connect(**DB_CONFIG)
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp","banco","volume","collection","consulta_id","descricao","execucao","tempo_s","documentos"])
        for label, tabela in VOLUMES.items():
            for q in get_consultas(tabela, DEFAULTS):
                print(f"Rodando {q['id']}")
                for i in range(1, EXECUCOES + 1):
                    t, n = executar(conn, q['sql'])
                    writer.writerow([time.strftime('%Y-%m-%d %H:%M:%S'), "Oracle", label, tabela, q['id'], q['descricao'], i, f"{t:.6f}", n])
                    f.flush()
    conn.close()

if __name__ == "__main__": main()
