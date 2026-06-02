"""
=============================================================================
  update_valor_novo_detalhes.py
  Cria o campo 'valor_novo_detalhes' extraído do campo 'VALOR_NOVO'
  em paralelo por faixas de _id para máxima performance.

  Requisitos: pip install pymongo --break-system-packages
=============================================================================
"""

from pymongo import MongoClient, UpdateOne
from bson import ObjectId
import re
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO
# ---------------------------------------------------------------------------

MONGO_URI       = "mongodb://SeuUser:SuaSenha@AMBIENTE:PORTA/?authSource=admin"
DATABASE        = "benchmark"
COLLECTIONS     = ["logs_3m", "logs_10m"]
BATCH_SIZE      = 10000   # documentos por lote
N_WORKERS       = 4      # threads paralelas por collection

# ---------------------------------------------------------------------------
# FUNÇÕES
# ---------------------------------------------------------------------------

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def parsear_valor_novo(valor_novo):
    if not valor_novo or not isinstance(valor_novo, str):
        return None

    valor_novo = valor_novo.strip()
    if not (valor_novo.startswith("[") and valor_novo.endswith("]")):
        return None

    try:
        conteudo = valor_novo[1:-1]
        partes   = conteudo.split(";")
        resultado = {}
        for parte in partes:
            if ":" in parte:
                chave, _, valor = parte.partition(":")
                chave = chave.strip()
                valor = valor.strip()
                if chave:
                    resultado[chave] = valor
        return resultado if resultado else None
    except Exception:
        return None

def processar_lote(collection_name, ids, client):
    db  = client[DATABASE]
    col = db[collection_name]

    cursor = col.find(
        {
            "_id": {"$in": ids},
            "VALOR_NOVO": {"$exists": True, "$type": "string"}
        },
        {"_id": 1, "VALOR_NOVO": 1}
    )

    operacoes = []
    for doc in cursor:
        detalhes = parsear_valor_novo(doc.get("VALOR_NOVO"))
        if detalhes is not None:
            operacoes.append(UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"valor_novo_detalhes": detalhes}}
            ))

    if operacoes:
        resultado = col.bulk_write(operacoes, ordered=False)
        return resultado.modified_count
    return 0

def buscar_ids_em_lotes(col, batch_size):
    lote = []
    for doc in col.find(
        {"VALOR_NOVO": {"$exists": True, "$type": "string", "$regex": r"^\[.*\]$"}},
        {"_id": 1}
    ):
        lote.append(doc["_id"])
        if len(lote) >= batch_size:
            yield lote
            lote = []
    if lote:
        yield lote

def atualizar_collection(collection_name):
    client = MongoClient(MONGO_URI)
    db = client[DATABASE]
    col = db[collection_name]

    filtro = {
        "VALOR_NOVO": {
            "$exists": True,
            "$type": "string",
            "$regex": r"^\[.*\]$"
        },
        "valor_novo_detalhes": {"$exists": False}
    }

    total_docs = col.count_documents(filtro)

    log(f"[{collection_name}] {total_docs:,} documentos para processar")

    if total_docs == 0:
        log(f"[{collection_name}] Nada a processar")
        client.close()
        return 0

    inicio = time.perf_counter()
    total_atualizados = 0
    operacoes = []

    cursor = col.find(
        filtro,
        {"_id": 1, "VALOR_NOVO": 1},
        no_cursor_timeout=True,
        batch_size=BATCH_SIZE
    )

    try:
        for doc in cursor:
            detalhes = parsear_valor_novo(doc.get("VALOR_NOVO"))

            if detalhes is not None:
                operacoes.append(
                    UpdateOne(
                        {"_id": doc["_id"]},
                        {"$set": {"valor_novo_detalhes": detalhes}}
                    )
                )

            if len(operacoes) >= BATCH_SIZE:
                resultado = col.bulk_write(operacoes, ordered=False)
                total_atualizados += resultado.modified_count
                operacoes = []

                elapsed = time.perf_counter() - inicio
                velocidade = (
                    total_atualizados / elapsed if elapsed > 0 else 0
                )
                pct = (
                    total_atualizados / total_docs * 100
                    if total_docs > 0 else 0
                )

                print(
                    f"  [{collection_name}] "
                    f"{pct:5.1f}% | "
                    f"{total_atualizados:>12,} atualizados | "
                    f"{velocidade:,.0f} doc/s",
                    end="\r",
                    flush=True
                )

        # Grava o restante
        if operacoes:
            resultado = col.bulk_write(operacoes, ordered=False)
            total_atualizados += resultado.modified_count

    finally:
        cursor.close()
        client.close()

    elapsed = time.perf_counter() - inicio
    print()

    log(
        f"[{collection_name}] Concluído: "
        f"{total_atualizados:,} docs em "
        f"{elapsed:.3f}s "
        f"({total_atualizados / elapsed:,.0f} doc/s)"
    )

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
        client.close()
    except Exception as e:
        log(f"ERRO na conexão: {e}")
        sys.exit(1)

    print()
    resultados = {}

    for collection in COLLECTIONS:
        print("=" * 60)
        inicio   = time.perf_counter()
        elapsed  = atualizar_collection(collection)
        resultados[collection] = elapsed

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
