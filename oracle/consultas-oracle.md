# Consultas Oracle

## Objetivo

Este benchmark foi desenvolvido para avaliar o desempenho do Oracle Database em diferentes volumes de dados utilizando tabelas contendo aproximadamente:

| Volume     | Tabela         |
| ---------- | -------------- |
| 3 milhões  | `LOG_2025_3M`  |
| 10 milhões | `LOG_2025_10M` |
| 50 milhões | `LOG_2025_50M` |

As consultas simulam cenários comuns de auditoria e análise de logs, incluindo filtros simples, consultas compostas, agregações, paginação, buscas textuais e operações equivalentes a `DISTINCT`.

O conjunto de consultas foi projetado para ser funcionalmente equivalente ao benchmark executado no MongoDB, permitindo comparações diretas de desempenho entre os dois SGBDs.

---

## Bibliotecas Utilizadas

```python
import csv
import statistics
import time
import oracledb
import sys
```

### Dependências

#### Oracle Database Driver

Driver oficial para conexão Python → Oracle.

Instalação:

```bash
pip install oracledb
```

### Bibliotecas Nativas do Python

| Biblioteca   | Finalidade                       |
| ------------ | -------------------------------- |
| `csv`        | Exportação dos resultados        |
| `statistics` | Cálculo de médias e estatísticas |
| `time`       | Medição de tempo de execução     |
| `sys`        | Controle de execução do script   |

---

## Tabelas Avaliadas

```python
VOLUMES = {
    "3M":  "LOG_2025_3M",
    "10M": "LOG_2025_10M",
    "50M": "LOG_2025_50M",
}
```

---

# Consultas Avaliadas

## Q01 - DISTINCT com filtro por tipo de log e data

### Objetivo

Simular uma consulta equivalente a `SELECT DISTINCT`, retornando registros únicos com extração de texto do campo `VALOR_ATUAL`.

### Operações

* Filtro por intervalo de datas
* Filtro por tipos de log específicos
* Extração da substring após o texto `"papel de"`
* Agrupamento para eliminação de duplicidades

### Consulta

```sql
SELECT
    ID_LOG_TIPO AS log_tipo,
    TO_CHAR(
        SUBSTR(
            VALOR_ATUAL,
            INSTR(VALOR_ATUAL, 'papel de ') + 9
        )
    ) AS local,
    HORA,
    IP_COMPUTADOR
FROM (
    SELECT ID_LOG_TIPO,
           VALOR_ATUAL,
           HORA,
           IP_COMPUTADOR
    FROM {tabela}
    WHERE ID_LOG_TIPO IN (96,117)
      AND DATA >= TO_DATE('2025-01-01','YYYY-MM-DD')
      AND DATA < TO_DATE('2025-03-01','YYYY-MM-DD')
      AND ROWNUM <= 25000000
)
GROUP BY
    ID_LOG_TIPO,
    TO_CHAR(
        SUBSTR(
            VALOR_ATUAL,
            INSTR(VALOR_ATUAL,'papel de ') + 9
        )
    ),
    HORA,
    IP_COMPUTADOR;
```

---

## Q02 - COUNT simples

### Objetivo

Contar a quantidade total de registros dentro de um período.

### Consulta

```sql
SELECT COUNT(*)
FROM {tabela}
WHERE DATA >= TO_DATE('2025-01-01','YYYY-MM-DD')
  AND DATA < TO_DATE('2025-03-01','YYYY-MM-DD');
```

---

## Q03 - Filtro por usuário

### Objetivo

Recuperar registros de um usuário específico.

### Consulta

```sql
SELECT
    ID_LOG,
    ID_LOG_TIPO,
    IP_COMPUTADOR,
    DATA,
    TABELA,
    VALOR_ATUAL
FROM (
    SELECT
        ID_LOG,
        ID_LOG_TIPO,
        IP_COMPUTADOR,
        DATA,
        TABELA,
        VALOR_ATUAL
    FROM {tabela}
    WHERE ID_USU = 1
      AND DATA >= TO_DATE('2025-01-01','YYYY-MM-DD')
      AND DATA < TO_DATE('2025-03-01','YYYY-MM-DD')
      AND ROWNUM <= 25000000
);
```

---

## Q04 - Filtro por IP_COMPUTADOR

### Objetivo

Buscar registros provenientes de um determinado computador ou servidor.

### Consulta

```sql
SELECT
    ID_LOG,
    ID_LOG_TIPO,
    DATA,
    TABELA,
    VALOR_ATUAL
FROM (
    SELECT
        ID_LOG,
        ID_LOG_TIPO,
        DATA,
        TABELA,
        VALOR_ATUAL
    FROM {tabela}
    WHERE IP_COMPUTADOR = 'Servidor'
      AND DATA >= TO_DATE('2025-01-01','YYYY-MM-DD')
      AND DATA < TO_DATE('2025-03-01','YYYY-MM-DD')
      AND ROWNUM <= 25000000
);
```

---

## Q05 - Filtro composto

### Objetivo

Simular uma consulta com múltiplas condições.

### Consulta

```sql
SELECT
    ID_LOG,
    ID_LOG_TIPO,
    IP_COMPUTADOR,
    DATA,
    TABELA,
    VALOR_ATUAL
FROM (
    SELECT
        ID_LOG,
        ID_LOG_TIPO,
        IP_COMPUTADOR,
        DATA,
        TABELA,
        VALOR_ATUAL
    FROM {tabela}
    WHERE ID_LOG_TIPO IN (96,117)
      AND TABELA = 'Arquivo'
      AND DATA >= TO_DATE('2025-01-01','YYYY-MM-DD')
      AND DATA < TO_DATE('2025-03-01','YYYY-MM-DD')
      AND ROWNUM <= 25000000
);
```

---

## Q06 - Agregação por IP

### Objetivo

Identificar os computadores que mais geraram registros.

### Consulta

```sql
SELECT
    IP_COMPUTADOR,
    COUNT(*) AS TOTAL
FROM {tabela}
WHERE DATA >= TO_DATE('2025-01-01','YYYY-MM-DD')
  AND DATA < TO_DATE('2025-03-01','YYYY-MM-DD')
GROUP BY IP_COMPUTADOR
ORDER BY TOTAL DESC;
```

### Resultado

Quantidade de registros agrupados por IP.

---

## Q07 - Busca por nome do tipo de log

### Objetivo

Pesquisar registros contendo determinada descrição de log.

### Operações

* Associação entre LOG e LOG_TIPO
* Busca textual pela descrição do tipo de log
* Equivalente à busca sobre `log_tipo_detalhes.LOG_TIPO` no MongoDB

### Consulta

```sql
SELECT *
FROM (
    SELECT
        l.*,
        lt.LOG_TIPO AS LOG_TIPO_DESCRICAO
    FROM (
        SELECT *
        FROM {tabela}
        WHERE DATA >= TO_DATE('2025-01-01','YYYY-MM-DD')
          AND DATA < TO_DATE('2025-03-01','YYYY-MM-DD')
          AND ROWNUM <= 25000000
    ) l
    JOIN SYSTEM.LOG_TIPO lt
      ON l.ID_LOG_TIPO = lt.ID_LOG_TIPO
)
WHERE LOG_TIPO_DESCRICAO LIKE '%Erro%';
```

### Observação

No MongoDB o campo `LOG_TIPO` encontra-se desnormalizado dentro do documento. No Oracle é necessário realizar `JOIN` com a tabela de referência.

---

## Q08 - Paginação

### Objetivo

Recuperar os 1000 registros mais recentes.

### Consulta

```sql
SELECT
    ID_LOG,
    DATA,
    HORA,
    ID_LOG_TIPO,
    VALOR_ATUAL
FROM (
    SELECT
        ID_LOG,
        DATA,
        HORA,
        ID_LOG_TIPO,
        VALOR_ATUAL
    FROM {tabela}
    WHERE DATA >= TO_DATE('2025-01-01','YYYY-MM-DD')
      AND DATA < TO_DATE('2025-03-01','YYYY-MM-DD')
    ORDER BY DATA DESC
)
WHERE ROWNUM <= 1000;
```

---

## Q09 - Busca textual por substring

### Objetivo

Localizar ocorrências contendo o texto `"papel de"` dentro de `VALOR_ATUAL`.

### Consulta

```sql
SELECT
    ID_LOG,
    DATA,
    HORA,
    VALOR_ATUAL
FROM (
    SELECT
        ID_LOG,
        DATA,
        HORA,
        VALOR_ATUAL
    FROM {tabela}
    WHERE VALOR_ATUAL LIKE '%papel de%'
      AND DATA >= TO_DATE('2025-01-01','YYYY-MM-DD')
      AND DATA < TO_DATE('2025-03-01','YYYY-MM-DD')
      AND ROWNUM <= 25000000
);
```

### Características

* Busca textual parcial
* Tende a realizar varredura extensa da tabela
* Equivalente a um `$regex` no MongoDB

---

## Q10 - Agregação temporal

### Objetivo

Contar a quantidade de registros por dia.

### Consulta

```sql
SELECT
    TRUNC(DATA,'DD') AS DIA,
    COUNT(*) AS TOTAL
FROM {tabela}
WHERE DATA >= TO_DATE('2025-01-01','YYYY-MM-DD')
  AND DATA < TO_DATE('2025-03-01','YYYY-MM-DD')
GROUP BY TRUNC(DATA,'DD')
ORDER BY TRUNC(DATA,'DD');
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

O benchmark permite comparar o comportamento do Oracle Database em diferentes volumes de dados (3M, 10M e 50M de registros), avaliando escalabilidade, eficiência dos índices e impacto de consultas analíticas sobre grandes conjuntos de dados.
