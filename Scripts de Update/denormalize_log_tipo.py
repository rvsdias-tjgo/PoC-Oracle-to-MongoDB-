"""
=============================================================================
  denormalize_log_tipo.py
  Desnormaliza as collections de log incorporando os dados do log_tipo
  diretamente no documento, usando ID_LOG_TIPO como chave de join.

  Antes:
    { "ID_LOG_TIPO": 96, ... }

  Depois:
    { "ID_LOG_TIPO": 96, "log_tipo_detalhes": { "log_tipo": "...", "status": 1, ... }, ... }

  Requisitos: pip install pymongo --break-system-packages
=============================================================================
"""

from pymongo import MongoClient, UpdateOne
import time
import sys

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO
# ---------------------------------------------------------------------------

MONGO_URI = "mongodb://SeuUser:SuaSenha@AMBIENTE:PORTA/benchmark?authSource=admin"
DATABASE    = "benchmark"
COLLECTIONS = ["logs_3m", "logs_10m"]
BATCH_SIZE  = 10000

# ---------------------------------------------------------------------------
# FUNÇÕES
# ---------------------------------------------------------------------------

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def carregar_log_tipo(db):
    """Carrega todos os documentos do log_tipo em memória como mapa."""
    mapa = {}
    for doc in db["logs_tipo"].find({}, {"_id": 0}):
        id_tipo = doc.get("ID_LOG_TIPO")
        if id_tipo is not None:
            # Remove o id_log_tipo do embed para não duplicar
            detalhes = {k: v for k, v in doc.items() if k != "ID_LOG_TIPO"}
            mapa[int(id_tipo)] = detalhes
    log(f"log_tipo carregado: {len(mapa):,} tipos")
    return mapa

def desnormalizar_collection(collection_name, log_tipo_map, db):
    col = db[collection_name]

    filtro = {"log_tipo_detalhes": {"$exists": False}}

    total_docs = col.count_documents(filtro)
    log(f"[{collection_name}] {total_docs:,} documentos para desnormalizar")

    if total_docs == 0:
        log(f"[{collection_name}] Nada a processar")
        return 0

    inicio            = time.perf_counter()
    total_atualizados = 0
    total_sem_match   = 0
    operacoes         = []

    cursor = col.find(filtro, {"_id": 1, "ID_LOG_TIPO": 1}, no_cursor_timeout=True, batch_size=BATCH_SIZE)

    try:
        for doc in cursor:
            id_log_tipo = doc.get("ID_LOG_TIPO")
            detalhes    = log_tipo_map.get(int(id_log_tipo)) if id_log_tipo is not None else None

            if detalhes is not None:
                operacoes.append(UpdateOne(
                    {"_id": doc["_id"]},
                    {"$set": {"log_tipo_detalhes": detalhes}}
                ))
            else:
                total_sem_match += 1

            if len(operacoes) >= BATCH_SIZE:
                resultado          = col.bulk_write(operacoes, ordered=False)
                total_atualizados += resultado.modified_count
                operacoes          = []

                elapsed    = time.perf_counter() - inicio
                velocidade = total_atualizados / elapsed if elapsed > 0 else 0
                pct        = total_atualizados / total_docs * 100 if total_docs > 0 else 0
                print(
                    f"  [{collection_name}] {pct:5.1f}% | "
                    f"{total_atualizados:>12,} atualizados | "
                    f"{velocidade:,.0f} doc/s",
                    end="\r", flush=True
                )

        # Gravar restante
        if operacoes:
            resultado          = col.bulk_write(operacoes, ordered=False)
            total_atualizados += resultado.modified_count

    finally:
        cursor.close()

    elapsed = time.perf_counter() - inicio
    print()
    log(f"[{collection_name}] Concluído: {total_atualizados:,} docs em {elapsed:.3f}s ({total_atualizados/elapsed:,.0f} doc/s)")

    if total_sem_match > 0:
        log(f"[{collection_name}] {total_sem_match:,} documentos sem match no log_tipo")

    return elapsed

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
    log_tipo_map = carregar_log_tipo(db)

    if not log_tipo_map:
        log("ERRO — log_tipo vazio ou não encontrado")
        client.close()
        sys.exit(1)

    print()
    resultados = {}

    for collection in COLLECTIONS:
        print("=" * 60)
        elapsed            = desnormalizar_collection(collection, log_tipo_map, db)
        resultados[collection] = elapsed

    client.close()

    print()
    print("=" * 60)
    print("  RESUMO FINAL:")
    print("=" * 60)
    for col, elapsed in resultados.items():
        if isinstance(elapsed, float):
            print(f"  {col:<15} {elapsed:.3f}s")
        else:
            print(f"  {col:<15} sem documentos")
    print("=" * 60)

if __name__ == "__main__":
    main()
