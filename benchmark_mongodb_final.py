
from pymongo import MongoClient
from datetime import datetime
import csv
import statistics
import time
import sys


MONGO_URI  = "mongodb://admin:senha123@localhost:27017/"
DATABASE   = "benchmark"
EXECUCOES  = 7

COLLECTIONS = {
    # "3M":  "logs_3m",
    "10M": "logs_50m",
}


DATA_INICIO   = datetime(2025, 1, 1, 0, 0, 0)
DATA_FIM      = datetime(2025, 3, 1, 0, 0, 0)   
DATA_FIM_6M   = datetime(2025, 6, 1, 0, 0, 0)   
IDS_LOG_TIPO  = [96, 117]

CSV_FILE = "benchmark_mongodb_final2.csv"

def get_consultas(db, collection):
    col = db[collection]
    return [

        # Q01 — DISTINCT com log_tipo_detalhes, filtro id_log_tipo e data
        {
            "id":       "Q01",
            "descricao":"DISTINCT com log_tipo_detalhes, filtro id_log_tipo e data (Limitado a 25M)",
            "executar": lambda: list(col.aggregate([
                { "$limit": 25_000_000 },
                {"$match": {
                    "ID_LOG_TIPO": {"$in": IDS_LOG_TIPO},
                    "DATA": {"$gte": DATA_INICIO, "$lt": DATA_FIM}
                }},
                {"$project": {
                    "_id": 0,
                    "ID_LOG_TIPO": 1, "VALOR_ATUAL": 1,
                    "HORA": 1, "IP_COMPUTADOR": 1,
                    "log_tipo_detalhes": 1
                }},
                {"$addFields": {
                    "log_tipo_nome": "$log_tipo_detalhes.LOG_TIPO",
                    "local_extraido": {"$let": {
                        "vars": {"idx": {"$indexOfCP": ["$VALOR_ATUAL", "papel de "]}},
                        "in": {"$cond": {
                            "if":   {"$gte": ["$$idx", 0]},
                            "then": {"$substrCP": [
                                "$VALOR_ATUAL",
                                {"$add": ["$$idx", 9]},
                                {"$strLenCP": "$VALOR_ATUAL"}
                            ]},
                            "else": None
                        }}
                    }}
                }},
                {"$group": {"_id": {
                    "log_tipo":     "$log_tipo_nome",
                    "local":        "$local_extraido",
                    "hora":         "$HORA",
                    "ip_computador":"$IP_COMPUTADOR"
                }}},
                {"$project": {"_id": 0,
                    "log_tipo":      "$_id.log_tipo",
                    "local":         "$_id.local",
                    "hora":          "$_id.hora",
                    "ip_computador": "$_id.ip_computador"
                }}
            ], allowDiskUse=True))
        },

        # Q02 — COUNT simples com filtro de data
       {
            "id":       "Q02",
            "descricao":"COUNT simples com filtro de data (Limitado a 25M)",
            "executar": lambda: list(col.aggregate([
                {"$limit": 25_000_000},
                {"$match": {"DATA": {"$gte": DATA_INICIO, "$lt": DATA_FIM}}},
                {"$count": "total"}
            ]))
        },

        # Q03 — SELECT com range de data de 6 meses (até junho — igual ao Oracle)
        {
            "id":       "Q03",
            "descricao":"SELECT com range de data de 6 meses (jan a jun) (Limitado a 25M)",
            "executar": lambda: list(col.aggregate([
                {"$limit": 25_000_000},
                {"$match": {"DATA": {"$gte": DATA_INICIO, "$lt": DATA_FIM_6M}}},
                {"$project": {"_id": 0, "ID_LOG": 1, "ID_LOG_TIPO": 1,
                             "IP_COMPUTADOR": 1, "DATA": 1, "TABELA": 1}}
            ], allowDiskUse=True))
        },


        # Q04 — Filtro por ID_USU
        {
            "id":       "Q04",
            "descricao":"Filtro por ID_USU (Limitado a 25M)",
            "executar": lambda: list(col.aggregate([
                {"$limit": 25_000_000},
                {"$match": {
                    "ID_USU": 1,
                    "DATA": {"$gte": DATA_INICIO, "$lt": DATA_FIM}
                }},
                {"$project": {"_id": 0, "ID_LOG": 1, "ID_LOG_TIPO": 1,
                             "IP_COMPUTADOR": 1, "DATA": 1, "TABELA": 1, "VALOR_ATUAL": 1}}
            ], allowDiskUse=True))
        },

        # Q05 — Filtro por IP_COMPUTADOR
        {
            "id":       "Q05",
            "descricao":"Filtro por IP_COMPUTADOR (Limitado a 25M)",
            "executar": lambda: list(col.aggregate([
                {"$limit": 25_000_000},
                {"$match": {
                    "IP_COMPUTADOR": "Servidor",
                    "DATA": {"$gte": DATA_INICIO, "$lt": DATA_FIM}
                }},
                {"$project": {"_id": 0, "ID_LOG": 1, "ID_LOG_TIPO": 1,
                             "DATA": 1, "TABELA": 1, "VALOR_ATUAL": 1}}
            ], allowDiskUse=True))
        },

        # Q06 — Filtro por TABELA
        {
            "id":       "Q06",
            "descricao":"Filtro por campo TABELA (Limitado a 25M)",
            "executar": lambda: list(col.aggregate([
                {"$limit": 25_000_000},
                {"$match": {
                    "TABELA": "Arquivo",
                    "DATA": {"$gte": DATA_INICIO, "$lt": DATA_FIM}
                }},
                {"$project": {
                    "_id": 0, "ID_LOG": 1, "ID_LOG_TIPO": 1,
                    "IP_COMPUTADOR": 1, "DATA": 1, "VALOR_ATUAL": 1
                }}
            ], allowDiskUse=True))
        },

        # Q07 — Busca por nome do tipo de log (desnormalizado)
        {
            "id":       "Q07",
            "descricao":"Filtro por nome do tipo de log (log_tipo_detalhes) (Limitado a 25M)",
            "executar": lambda: list(col.aggregate([
                {"$limit": 25_000_000},
                {"$match": {
                    "log_tipo_detalhes.LOG_TIPO": {"$regex": "Erro"},
                    "DATA": {"$gte": DATA_INICIO, "$lt": DATA_FIM}
                }},
                {"$project": {
                    "_id": 0, "ID_LOG": 1, "IP_COMPUTADOR": 1,
                    "DATA": 1, "TABELA": 1, "log_tipo_detalhes.LOG_TIPO": 1
                }}
            ], allowDiskUse=True))
        },

        # Q08 — Busca por Id_Arquivo em valor_novo_detalhes
        {
            "id":       "Q07",
            "descricao":"Filtro por nome do tipo de log (log_tipo_detalhes) (Limitado a 25M)",
            "executar": lambda: list(col.aggregate([
                {"$limit": 25_000_000},
                {"$match": {
                    "log_tipo_detalhes.LOG_TIPO": {"$regex": "Erro"},
                    "DATA": {"$gte": DATA_INICIO, "$lt": DATA_FIM}
                }},
                {"$project": {
                    "_id": 0, "ID_LOG": 1, "IP_COMPUTADOR": 1,
                    "DATA": 1, "TABELA": 1, "log_tipo_detalhes.LOG_TIPO": 1
                }}
            ], allowDiskUse=True))
        },

        # Q09 — Filtro composto: data + id_log_tipo + tabela
        {
            "id":       "Q07",
            "descricao":"Filtro por nome do tipo de log (log_tipo_detalhes) (Limitado a 25M)",
            "executar": lambda: list(col.aggregate([
                {"$limit": 25_000_000},
                {"$match": {
                    "log_tipo_detalhes.LOG_TIPO": {"$regex": "Erro"},
                    "DATA": {"$gte": DATA_INICIO, "$lt": DATA_FIM}
                }},
                {"$project": {
                    "_id": 0, "ID_LOG": 1, "IP_COMPUTADOR": 1,
                    "DATA": 1, "TABELA": 1, "log_tipo_detalhes.LOG_TIPO": 1
                }}
            ], allowDiskUse=True))
        },

        # Q10 — Agregação: COUNT por IP_COMPUTADOR
        {
            "id":       "Q10",
            "descricao":"Agregacao COUNT por IP_COMPUTADOR (Limitado a 25M)",
            "executar": lambda: list(col.aggregate([
                {"$limit": 25_000_000},
                {"$match": {"DATA": {"$gte": DATA_INICIO, "$lt": DATA_FIM}}},
                {"$group": {"_id": "$IP_COMPUTADOR", "total": {"$sum": 1}}},
                {"$sort": {"total": -1}},
            ], allowDiskUse=True))
        },
    ]

# ============================================================================
# FUNÇÕES
# ============================================================================

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def benchmark_consulta(consulta, volume, collection, writer, todos_resultados):
    tempos = []

    for i in range(1, EXECUCOES + 1):
        try:
            t0     = time.perf_counter()
            result = consulta["executar"]()
            tempo  = time.perf_counter() - t0
            qtd    = len(result)
        except Exception as e:
            log(f"  ERRO {consulta['id']} exec {i}: {e}")
            tempo, qtd = 0, 0

        tempos.append(tempo)
        nivel = "RAPIDO" if tempo < 1.0 else "MEDIO" if tempo < 5.0 else "LENTO"
        print(f"     [{nivel}]  Exec {i:02d}: {tempo:.4f}s | {qtd:,} docs")

        writer.writerow({
            "timestamp":   time.strftime("%Y-%m-%d %H:%M:%S"),
            "banco":       "MongoDB",
            "volume":      volume,
            "collection":  collection,
            "consulta_id": consulta["id"],
            "descricao":   consulta["descricao"],
            "execucao":    i,
            "tempo_s":     round(tempo, 6),
            "documentos":  qtd,
        })

    media   = round(statistics.mean(tempos), 4)
    minimo  = round(min(tempos), 4)
    maximo  = round(max(tempos), 4)
    mediana = round(statistics.median(tempos), 4)
    desvio  = round(statistics.stdev(tempos) if len(tempos) > 1 else 0, 4)

    print(f"\n     [STATS]  Min: {minimo}s | Max: {maximo}s | Media: {media}s | Mediana: {mediana}s")

    todos_resultados.append({
        "volume":      volume,
        "collection":  collection,
        "consulta_id": consulta["id"],
        "descricao":   consulta["descricao"],
        "media_s":     media,
        "min_s":       minimo,
        "max_s":       maximo,
        "mediana_s":   mediana,
        "desvio_s":    desvio,
    })

def main():
    print("=" * 70)
    print("  BENCHMARK MONGODB — 10 Consultas x 7 Execucoes")
    print(f"  Inicio: {time.strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 70)

    log("Conectando ao MongoDB...")
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info()
        log("Conexao OK")
    except Exception as e:
        log(f"ERRO: {e}")
        sys.exit(1)

    db               = client[DATABASE]
    todos_resultados = []
    inicio_total     = time.perf_counter()

    campos_csv = ["timestamp", "banco", "volume", "collection", "consulta_id",
                  "descricao", "execucao", "tempo_s", "documentos"]

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=campos_csv)
        writer.writeheader()

        for volume, collection in COLLECTIONS.items():
            print(f"\n{'='*70}")
            print(f"  VOLUME: {volume} — Collection: {collection}")
            print(f"{'='*70}")

            consultas = get_consultas(db, collection)

            for consulta in consultas:
                print(f"\n  [{consulta['id']}] {consulta['descricao']}")
                print("  " + "-" * 60)
                benchmark_consulta(consulta, volume, collection, writer, todos_resultados)

    client.close()
    elapsed = time.perf_counter() - inicio_total

    print()
    print("=" * 70)
    print("  RESUMO FINAL")
    print("=" * 70)
    print(f"  {'Vol':<6} {'Q':<6} {'Media (s)':<12} {'Min (s)':<12} {'Mediana (s)':<14} {'Descricao'}")
    print("  " + "-" * 70)
    for r in todos_resultados:
        print(f"  {r['volume']:<6} {r['consulta_id']:<6} {r['media_s']:<12} {r['min_s']:<12} {r['mediana_s']:<14} {r['descricao'][:40]}")

    print("=" * 70)
    print(f"  CSV salvo: {CSV_FILE}")
    print(f"  Duracao total: {elapsed:.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()