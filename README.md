# PoC de Performance — Oracle Database vs MongoDB

## Objetivo

Esta Prova de Conceito (PoC) tem como objetivo comparar o desempenho do Oracle Database e do MongoDB em cenários reais de consulta sobre grandes volumes de dados de auditoria.

Os testes foram executados utilizando conjuntos de dados equivalentes contendo aproximadamente:

| Volume  | Quantidade de Registros |
| ------- | ----------------------- |
| Pequeno | 3 milhões               |
| Médio   | 10 milhões              |
| Grande  | 50 milhões              |

O foco da avaliação é analisar o comportamento de cada banco de dados em operações utilizadas, como:

* Consultas por filtros simples
* Consultas por filtros compostos
* Busca textual
* Paginação
* Operações de agregação
* Contagens
* Consultas equivalentes a `DISTINCT`
* Agrupamentos temporais

---

## Estrutura do Projeto

```text
benchmark-poc/
│
├── mongodb/
│   ├── benchmark_mongodb.py
│   └── mongodb.md
│
├── oracle/
│   ├── benchmark_oracle.py
│   └── oracle.md
│
├── resultados/
│   ├── mongodb/
│   └── oracle/
│
└── README.md
```

---

## Bancos Avaliados

### Oracle Database

Modelo relacional tradicional utilizando tabelas:

| Volume | Tabela       |
| ------ | ------------ |
| 3M     | LOG_2025_3M  |
| 10M    | LOG_2025_10M |
| 50M    | LOG_2025_50M |

### MongoDB

Modelo documental utilizando collections:

| Volume | Collection |
| ------ | ---------- |
| 3M     | logs_3m    |
| 10M    | logs_10m   |
| 50M    | logs_50m   |

---

## Metodologia

Para garantir uma comparação justa, todas as consultas possuem equivalência funcional entre Oracle e MongoDB.

Cada consulta foi executada diversas vezes e os tempos coletados foram utilizados para cálculo de métricas estatísticas como:

* Média
* Mediana
* Menor tempo
* Maior tempo
* Desvio padrão

---

## Consultas Avaliadas

| ID  | Cenário                                    |
| --- | ------------------------------------------ |
| Q01 | DISTINCT com filtro por tipo de log e data |
| Q02 | COUNT simples                              |
| Q03 | Filtro por usuário                         |
| Q04 | Filtro por IP                              |
| Q05 | Filtro composto                            |
| Q06 | Agregação por IP                           |
| Q07 | Busca por nome do tipo de log              |
| Q08 | Paginação                                  |
| Q09 | Busca textual por substring                |
| Q10 | Agregação temporal por dia                 |

---

## Equivalência das Consultas

| Oracle | MongoDB | Objetivo              |
| ------ | ------- | --------------------- |
| Q01    | Q01     | DISTINCT              |
| Q02    | Q02     | COUNT                 |
| Q03    | Q03     | Filtro por usuário    |
| Q04    | Q04     | Filtro por IP         |
| Q05    | Q05     | Filtro composto       |
| Q06    | Q06     | Agregação por IP      |
| Q07    | Q07     | Busca por tipo de log |
| Q08    | Q08     | Paginação             |
| Q09    | Q09     | Busca textual         |
| Q10    | Q10     | Agregação temporal    |

---

## Tecnologias Utilizadas

### Oracle

* Oracle Database
* Python
* oracledb

Instalação:

```bash
pip install oracledb
```

### MongoDB

* MongoDB
* Python
* PyMongo

Instalação:

```bash
pip install pymongo
```

---

## Execução dos Benchmarks

### MongoDB

```bash
python benchmark_mongodb.py
```

### Oracle

```bash
python benchmark_oracle.py
```

---

## Critérios de Avaliação

Os resultados observam principalmente:

* Tempo de resposta das consultas
* Escalabilidade conforme aumento do volume de dados
* Eficiência dos índices
* Impacto de agregações
* Impacto de buscas textuais
* Consumo de recursos do banco de dados

---

## Limitações

Esta PoC representa um conjunto específico de cargas de trabalho baseadas em registros de auditoria.

Os resultados obtidos não devem ser generalizados para todos os cenários de uso de bancos relacionais ou documentais.

O desempenho observado depende de diversos fatores, incluindo:

* Configuração de hardware
* Memória disponível
* Estratégia de indexação
* Volume de dados
* Modelo de dados adotado
* Configuração do banco de dados

---

## Documentação Detalhada

A descrição completa das consultas pode ser encontrada em:

* `mongodb/mongodb.md`
* `oracle/oracle.md`

---

## Licença

Este projeto foi desenvolvido exclusivamente para fins de avaliação técnica e comparação de desempenho entre Oracle Database e MongoDB.
