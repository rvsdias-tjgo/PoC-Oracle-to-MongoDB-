from pymongo import MongoClient
import csv, time

# Configurações
MONGO_URI, DATABASE, EXECUCOES, BATCH_SIZE = "mongodb://SeuUser:SuaSenha@AMBIENTE:PORTA/", "benchmark", 7, 10000
COLLECTIONS = {"50M": "logs_50m"}
CSV_FILE = "benchmark_mongodb.csv"

DEFAULTS = {
    "LOG_TIPO": "Download", "ORIGEM": "projudi", "ID_PENDENCIA": "440542455",
    "COMBO_LOG_TIPO": "Download", "COMBO_ORIGEM": "projudi"
}

def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

def get_consultas(col, v):
    return [
        {"id": "Q1", 
         "descricao": "Filtro tipo_log desnormalizado", 
         "pipeline": [{"$match": {"log_tipo_detalhes.LOG_TIPO": v["LOG_TIPO"]}}, {"$limit": 1000000} , {"$project": {"_id": 0, "ID_LOG": 1}}], "col": col
        },
        {"id": "Q2", 
         "descricao": "Filtro Origem desnormalizada", 
         "pipeline": [{"$match": {"valor_novo_detalhes.Origem": v["ORIGEM"]}}, {"$limit": 1000000}, {"$project": {"_id": 0, "ID_LOG": 1}}], "col": col
        },
        {"id": "Q3", 
         "descricao": "Filtro Id_Pendencia desnormalizado", 
         "pipeline": [{"$match": {"valor_novo_detalhes.Id_Pendencia": v["ID_PENDENCIA"]}}, {"$limit": 1000000}, {"$project": {"_id": 0, "ID_LOG": 1}}], "col": col
        },
        {"id": "Q4", 
         "descricao": "Agregação COUNT por tipo", 
         "pipeline": [{"$limit": 1000000},{"$group": {"_id": "$log_tipo_detalhes.LOG_TIPO", "total": {"$sum": 1}}}], "col": col
        },
        {"id": "Q5", 
         "descricao": "Combinado: Tipo + Origem", 
         "pipeline": [{"$match": {"log_tipo_detalhes.LOG_TIPO": v["COMBO_LOG_TIPO"], "valor_novo_detalhes.Origem": v["COMBO_ORIGEM"]}}, {"$limit": 1000000}], "col": col
        }
    ]

def executar(consulta):
    inicio = time.perf_counter()
    cursor = consulta["col"].aggregate(consulta["pipeline"], allowDiskUse=True, batchSize=BATCH_SIZE)
    qtd = sum(1 for _ in cursor)
    return time.perf_counter() - inicio, qtd

def main():
    db = MongoClient(MONGO_URI)[DATABASE]
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp","banco","volume","collection","consulta_id","descricao","execucao","tempo_s","documentos"])
        for label, coll_name in COLLECTIONS.items():
            for q in get_consultas(db[coll_name], DEFAULTS):
                log(f"Rodando {q['id']}")
                for i in range(1, EXECUCOES + 1):
                    t, n = executar(q)
                    writer.writerow([time.strftime('%Y-%m-%d %H:%M:%S'), "MongoDB", label, coll_name, q['id'], q['descricao'], i, f"{t:.6f}", n])
                    f.flush()

if __name__ == "__main__": main()
