# Consultas MongoDB

## Objetivo

Este benchmark foi desenvolvido para avaliar o desempenho do MongoDB em diferentes volumes de dados utilizando coleções contendo aproximadamente:

| Volume     | Collection |
| ---------- | ---------- |
| 3 milhões  | `logs_3m`  |
| 10 milhões | `logs_10m` |
| 50 milhões | `logs_50m` |

As consultas simulam cenários comuns de auditoria e análise de logs, incluindo filtros simples, consultas compostas, agregações, paginação, buscas textuais e operações equivalentes a `DISTINCT`.

---

## Bibliotecas Utilizadas

```python
from pymongo import MongoClient
from datetime import datetime
import csv
import statistics
import time
import sys
```

### Dependências

#### PyMongo

Driver oficial para comunicação com MongoDB.

Instalação:

```bash
pip install pymongo
```

### Bibliotecas Nativas do Python

| Biblioteca   | Finalidade                        |
| ------------ | --------------------------------- |
| `datetime`   | Manipulação de datas              |
| `csv`        | Exportação de resultados          |
| `statistics` | Cálculo de médias e estatísticas  |
| `time`       | Medição de tempo de execução      |
| `sys`        | Controle de argumentos e execução |

---

## Coleções Avaliadas

```python
COLLECTIONS = {
    "3M":  "logs_3m",
    "10M": "logs_10m",
    "50M": "logs_50m",
}
```

---

## Parâmetros Utilizados

### Intervalo Principal

```python
DATA_INICIO = datetime(2025, 1, 1, 0, 0, 0)
DATA_FIM    = datetime(2025, 3, 1, 0, 0, 0)
```

### Intervalo de 6 Meses

```python
DATA_FIM_6M = datetime(2025, 6, 1, 0, 0, 0)
```

### Tipos de Log Utilizados

```python
IDS_LOG_TIPO = [96, 117]
```

---

# Consultas Avaliadas

## Q01 - DISTINCT com filtro por tipo de log e data (limitado a 25M documentos)

### Objetivo

Simular uma consulta equivalente a `SELECT DISTINCT`, retornando registros únicos com extração de texto do campo `VALOR_ATUAL`. Limitada a 25 milhões de documentos para controle de consumo de memória.

### Operações

* Filtro por tipos de log específicos e intervalo de datas
* Limitação a 25 milhões de documentos antes do agrupamento
* Agrupamento para remoção de duplicidades
* Extração da substring após o texto `"papel de"` via `$addFields` + `$let`
* Projeção dos campos relevantes

### Pipeline

```javascript
[
  {
    $match: {
      ID_LOG_TIPO: { $in: [96, 117] },
      DATA: {
        $gte: DATA_INICIO,
        $lt: DATA_FIM
      }
    }
  },
  {
    $limit: 25000000
  },
  {
    $group: {
      _id: {
        log_tipo:      "$log_tipo_detalhes.LOG_TIPO",
        valor_atual:   "$VALOR_ATUAL",
        hora:          "$HORA",
        ip_computador: "$IP_COMPUTADOR"
      }
    }
  },
  {
    $addFields: {
      local_extraido: {
        $let: {
          vars: { idx: { $indexOfCP: ["$_id.valor_atual", "papel de "] } },
          in: {
            $cond: {
              if:   { $gte: ["$$idx", 0] },
              then: { $substrCP: [
                "$_id.valor_atual",
                { $add: ["$$idx", 9] },
                { $strLenCP: "$_id.valor_atual" }
              ]},
              else: null
            }
          }
        }
      }
    }
  },
  {
    $project: {
      _id:           0,
      log_tipo:      "$_id.log_tipo",
      local:         "$local_extraido",
      hora:          "$_id.hora",
      ip_computador: "$_id.ip_computador"
    }
  }
]
```

---

## Q02 - COUNT simples (limitado a 25M documentos)

### Objetivo

Contar a quantidade total de documentos dentro de um período.

### Consulta

```javascript
{
  DATA: {
    $gte: DATA_INICIO,
    $lt: DATA_FIM
  }
}
```

### Operação

```python
count_documents()
```

---

## Q03 - Filtro por usuário (limitado a 25M documentos)

### Objetivo

Recuperar registros de um usuário específico com uso explícito de índice e limite de documentos retornados.

### Filtro

```javascript
{
  ID_USU: 1,
  DATA: {
    $gte: DATA_INICIO,
    $lt: DATA_FIM
  }
}
```

### Parâmetros

```python
limit=25_000_000
hint="ID_USU_1_DATA_1"
allow_disk_use=False
```

### Índice utilizado

```javascript
ID_USU_1_DATA_1
```

---

## Q04 - Filtro por IP_COMPUTADOR (limitado a 25M documentos)

### Objetivo

Buscar registros provenientes de um determinado computador ou servidor, com uso explícito de índice e limite de documentos retornados.

### Filtro

```javascript
{
  IP_COMPUTADOR: "Servidor",
  DATA: {
    $gte: DATA_INICIO,
    $lt: DATA_FIM
  }
}
```

### Parâmetros

```python
limit=25_000_000
hint="IP_COMPUTADOR_1_DATA_1"
allow_disk_use=False
```

### Índice utilizado

```javascript
IP_COMPUTADOR_1_DATA_1
```

---

## Q05 - Filtro composto (limitado a 25M documentos)

### Objetivo

Simular uma consulta com múltiplas condições, com uso explícito de índice e limite de documentos retornados.

### Filtro

```javascript
{
  ID_LOG_TIPO: {
    $in: [96, 117]
  },
  TABELA: "Arquivo",
  DATA: {
    $gte: DATA_INICIO,
    $lt: DATA_FIM
  }
}
```

### Parâmetros

```python
limit=25_000_000
hint="ID_LOG_TIPO_1_DATA_1"
allow_disk_use=False
```

### Índice utilizado

```javascript
ID_LOG_TIPO_1_DATA_1
```

---

## Q06 - Agregação por IP

### Objetivo

Identificar os computadores que mais geraram registros, com uso explícito de índice composto e permissão de escrita em disco.

### Pipeline

```javascript
[
  {
    $match: {
      DATA: {
        $gte: DATA_INICIO,
        $lt: DATA_FIM
      }
    }
  },
  {
    $group: {
      _id: "$IP_COMPUTADOR",
      total: {
        $sum: 1
      }
    }
  },
  {
    $sort: {
      total: -1
    }
  }
]
```

### Parâmetros

```python
hint="DATA_1_IP_COMPUTADOR_1"
allowDiskUse=True
```

### Resultado

Quantidade de registros agrupados por IP.

---

## Q07 - Busca por nome do tipo de log com âncora de início

### Objetivo

Pesquisar registros cujo tipo de log começa com determinada descrição, com uso explícito de índice.

### Filtro

```javascript
{
  "log_tipo_detalhes.LOG_TIPO": {
    $regex: "^Erro"
  },
  DATA: {
    $gte: DATA_INICIO,
    $lt: DATA_FIM
  }
}
```

### Parâmetros

```python
hint="log_tipo_detalhes.LOG_TIPO_1"
allow_disk_use=False
```

### Observação

Consulta baseada em expressão regular com âncora `^` no início da string, permitindo uso de índice pelo MongoDB. Diferente de uma busca com `.*Erro`, que forçaria varredura completa da coleção.

---

## Q08 - Paginação

### Objetivo

Recuperar os 1000 registros mais recentes com uso explícito de índice.

### Pipeline

```javascript
[
  {
    $match: {
      DATA: {
        $gte: DATA_INICIO,
        $lt: DATA_FIM
      }
    }
  },
  {
    $sort: {
      DATA: -1
    }
  },
  {
    $limit: 1000
  }
]
```

### Parâmetros

```python
hint="DATA_1"
allow_disk_use=False
```

### Índice utilizado

```javascript
{ DATA: 1 }
```

---

## Q09 - Busca por substring em VALOR_ATUAL (limitado a 25M documentos)

### Objetivo

Localizar ocorrências contendo o texto `"papel de"` dentro de `VALOR_ATUAL`, com uso explícito de índice e limite de documentos retornados.

### Filtro

```javascript
{
  DATA: {
    $gte: DATA_INICIO,
    $lt: DATA_FIM
  },
  VALOR_ATUAL: {
    $regex: "papel de"
  }
}
```

### Parâmetros

```python
limit=25_000_000
hint="DATA_1"
allow_disk_use=False
```

### Características

* Busca textual parcial
* Tende a realizar varredura extensa da coleção mesmo com índice em `DATA`
* Equivalente a um `LIKE '%texto%'` em bancos relacionais

---

## Q10 - Agregação temporal

### Objetivo

Contar a quantidade de registros por dia.

### Pipeline

```javascript
[
  {
    $match: {
      DATA: {
        $gte: DATA_INICIO,
        $lt: DATA_FIM
      }
    }
  },
  {
    $group: {
      _id: {
        $dateToString: {
          format: "%Y-%m-%d",
          date: "$DATA"
        }
      },
      total: {
        $sum: 1
      }
    }
  },
  {
    $sort: {
      _id: 1
    }
  }
]
```

# Considerações

As consultas foram projetadas para representar cenários reais, contemplando:

* Filtros simples
* Filtros compostos
* Operações equivalentes a `DISTINCT`
* Paginação
* Busca textual
* Agregações estatísticas
* Agregações temporais

O benchmark permite comparar o comportamento do MongoDB em diferentes volumes de dados (3M, 10M e 50M de documentos), avaliando escalabilidade, eficiência dos índices e impacto de consultas analíticas sobre grandes conjuntos de registros.
