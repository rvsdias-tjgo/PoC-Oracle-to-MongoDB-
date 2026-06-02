
# Carga de Dados para Oracle e MongoDB

## Objetivo

Os scripts deste diretório têm como finalidade realizar a carga de grandes volumes de dados de auditoria a partir de arquivos CSV para os ambientes Oracle Database e MongoDB utilizados na Prova de Conceito (PoC) de desempenho.

O processo contempla:

* Leitura dos arquivos CSV em lotes (chunks)
* Conversão automática de tipos de dados
* Conversão de datas
* Tratamento de valores nulos
* Inserção em massa
* Diagnóstico prévio dos arquivos
* Validação da carga

---

# Estrutura

```text
load/
├── script-load-mongodb.py
└── script-load-oracle.py
```

---

# Requisitos

## MongoDB

Instalação das dependências:

```bash
pip install pandas pymongo
```

Bibliotecas utilizadas:

```python
import pandas as pd
from pymongo import MongoClient
```

---

## Oracle

Instalação das dependências:

```bash
pip install pandas oracledb
```

Bibliotecas utilizadas:

```python
import pandas as pd
import oracledb
```

---

# Arquivos de Entrada

Os scripts foram projetados para importar arquivos CSV contendo registros de log.

Exemplos:

```text
log_tipo.csv
log_2025_3m.csv
log_2025_10m.csv
```

---

# Conversão de Dados

Durante a importação são realizadas conversões automáticas para garantir consistência dos dados.

## Datas

Os scripts detectam automaticamente formatos compatíveis como:

```text
DD/MM/YYYY
DD/MM/YY
YYYY-MM-DD
```

Exemplos:

```text
01/01/2025
01/01/25
2025-01-01
```

Caso nenhum formato seja identificado, é utilizada inferência automática.

---

## Campos Numéricos

As seguintes colunas são convertidas para valores numéricos:

```text
ID_LOG
ID_LOG_TIPO
ID_USU
CODIGO_TEMP
ID_TABELA
QTD_ERROS_DIA
```

---

## Valores Nulos

Valores vazios, inválidos ou não convertíveis são tratados como:

```text
NULL
```

---

# Processo de Carga — MongoDB

## Execução

```bash
python script-load-mongodb.py
```

## Características

* Leitura em lotes de 5.000 registros
* Conversão automática de tipos
* Inserção utilizando `insert_many()`
* Diagnóstico prévio do CSV
* Verificação de datas após a carga
* Criação automática de índices

## Collections

Exemplo de collections utilizadas:

```text
logs_tipo
logs_3m
logs_10m
```

## Índices Criados

Após a carga são criados automaticamente os índices:

```javascript
ID_LOG_TIPO

DATA

(ID_LOG_TIPO, DATA)
```

Esses índices são utilizados pelas consultas de benchmark.

## Validação Pós-Carga

Ao final da importação é realizada uma contagem dos documentos cujo campo DATA encontra-se entre:

```text
01/01/2025
01/03/2025
```

Também é exibido um resumo contendo:

* Quantidade total de documentos
* Quantidade de documentos com DATA válida
* Percentual de registros válidos

---

# Processo de Carga — Oracle

## Execução

```bash
python script-load-oracle.py
```

## Características

* Leitura em lotes de 15.000 registros
* Conversão automática de tipos
* Inserção em lote utilizando `executemany()`
* Controle de erros por lote
* Diagnóstico prévio do CSV
* Commit automático ao final de cada lote

## Tabelas

Exemplo:

```text
LOG_2025_3M
LOG_2025_10M
```

## Inserção em Massa

Os registros são inseridos utilizando:

```python
cursor.executemany()
```

Essa abordagem reduz o número de operações de rede e melhora o desempenho da carga.

## Tratamento de Erros

Durante a inserção são utilizados:

```python
batcherrors=True
```

Permitindo:

* Continuidade da carga
* Registro de linhas inválidas
* Exibição dos erros encontrados

---

# Monitoramento

Durante a execução ambos os scripts exibem:

```text
Número do lote
Quantidade carregada
Tempo decorrido
Taxa de registros por segundo
```

Exemplo:

```text
Lote 120 | 1.800.000 registros | 45.000 reg/s
```

---

# Considerações

Os scripts foram desenvolvidos para suportar cargas de milhões de registros utilizando processamento em lotes, reduzindo consumo de memória e permitindo a comparação de desempenho entre Oracle Database e MongoDB em condições equivalentes.

O processo de conversão automática de tipos e validação dos dados busca garantir que os conjuntos carregados nos dois ambientes sejam funcionalmente equivalentes para a execução dos benchmarks.
