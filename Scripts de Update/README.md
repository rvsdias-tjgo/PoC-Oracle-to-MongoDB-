
# Scripts de Atualização e Enriquecimento de Dados no MongoDB

## Objetivo

Após a carga inicial dos dados, alguns campos são processados e incorporados diretamente aos documentos para reduzir a necessidade de consultas adicionais e melhorar o desempenho das operações de benchmark.

Os scripts deste diretório executam tarefas de:

* Desnormalização de dados de referência
* Extração e estruturação de informações textuais
* Atualização em massa de documentos
* Preparação das collections para execução dos benchmarks

---

# Estrutura

```text
Scripts de Update/
├── denormalize_log_tipo.py
└── update_valor_novo_detalhes.py
```

---

# Requisitos

Instalação das dependências:

```bash
pip install pymongo
```

Bibliotecas utilizadas:

```python
from pymongo import MongoClient
from pymongo import UpdateOne
```

---

# Collections Processadas

Os scripts atuam sobre as collections:

```text
logs_3m
logs_10m
```

E utilizam como referência:

```text
logs_tipo
```

---

# Script 1 — Desnormalização do Tipo de Log

## Arquivo

```text
denormalize_log_tipo.py
```

## Objetivo

Incorporar as informações da collection `logs_tipo` diretamente nos documentos de log utilizando o campo:

```text
ID_LOG_TIPO
```

Essa abordagem elimina a necessidade de consultas adicionais para obtenção da descrição do tipo de log.

---

## Estrutura Antes

```json
{
  "ID_LOG": 123,
  "ID_LOG_TIPO": 96
}
```

---

## Estrutura Depois

```json
{
  "ID_LOG": 123,
  "ID_LOG_TIPO": 96,
  "log_tipo_detalhes": {
    "LOG_TIPO": "Erro de Sistema",
    "STATUS": 1
  }
}
```

---

## Processo

### 1. Carregamento da Collection de Referência

Todos os registros da collection:

```text
logs_tipo
```

são carregados em memória e convertidos para um mapa utilizando:

```text
ID_LOG_TIPO
```

como chave de busca.

---

### 2. Localização dos Documentos

São selecionados apenas documentos que ainda não possuem o campo:

```text
log_tipo_detalhes
```

---

### 3. Atualização em Massa

As atualizações são executadas utilizando:

```python
bulk_write()
```

em lotes de:

```text
10.000 documentos
```

---

## Benefícios

* Eliminação de consultas adicionais
* Redução da necessidade de operações equivalentes a JOIN
* Melhor desempenho em filtros por tipo de log
* Melhor desempenho em consultas analíticas

---

# Script 2 — Estruturação do Campo VALOR_NOVO

## Arquivo

```text
update_valor_novo_detalhes.py
```

## Objetivo

Converter informações armazenadas como texto no campo:

```text
VALOR_NOVO
```

em uma estrutura de dados pesquisável.

---

## Estrutura Antes

```text
[campo1:valor1;campo2:valor2;campo3:valor3]
```

---

## Estrutura Depois

```json
{
  "valor_novo_detalhes": {
    "campo1": "valor1",
    "campo2": "valor2",
    "campo3": "valor3"
  }
}
```

---

## Processo

### 1. Seleção dos Documentos

São processados apenas documentos que:

* Possuem o campo `VALOR_NOVO`
* Possuem conteúdo textual válido
* Ainda não possuem o campo `valor_novo_detalhes`

---

### 2. Interpretação do Conteúdo

O script identifica padrões no formato:

```text
[chave:valor;chave:valor]
```

e converte cada par em um atributo estruturado.

---

### 3. Atualização em Massa

As alterações são executadas utilizando:

```python
bulk_write()
```

em lotes de:

```text
10.000 documentos
```

---

## Exemplo

### Entrada

```text
[usuario:123;perfil:Administrador;ativo:Sim]
```

### Resultado

```json
{
  "valor_novo_detalhes": {
    "usuario": "123",
    "perfil": "Administrador",
    "ativo": "Sim"
  }
}
```

---

# Monitoramento

Durante a execução ambos os scripts exibem:

```text
Percentual concluído
Quantidade atualizada
Tempo decorrido
Documentos por segundo
```

Exemplo:

```text
[logs_10m] 84.3% | 8.430.000 atualizados | 52.000 doc/s
```

---

# Estratégia de Performance

Os scripts utilizam:

* Atualização em lote (`bulk_write`)
* Operações não ordenadas (`ordered=False`)
* Cursor em lote (`batch_size`)
* Processamento incremental
* Atualização apenas dos documentos ainda não processados

Essa estratégia reduz consumo de memória e minimiza o impacto sobre o banco durante a preparação dos dados.

---

# Finalidade na PoC

Essas transformações foram realizadas para aproximar o modelo documental das necessidades das consultas de benchmark.

Após a execução dos scripts:

* As informações de tipo de log passam a estar incorporadas ao documento.
* O conteúdo textual de `VALOR_NOVO` passa a estar estruturado em formato chave/valor.
* As consultas utilizadas nos testes podem acessar essas informações diretamente, sem necessidade de processamento adicional durante a execução dos benchmarks.

Essa abordagem permite avaliar o desempenho do MongoDB utilizando um modelo documental otimizado para leitura e análise de dados.
