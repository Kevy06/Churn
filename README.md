# Previsão de Churn em Telecomunicações

UNEX – Sistemas de Informação · Mineração de Dados · Bloco 2
Base: [Telco Customer Churn (IBM)](https://github.com/IBM/telco-customer-churn-on-icp4d) – 7.043 clientes.

O `churn.py` lê a base, limpa, cria variáveis, calcula churn por período, treina
3 modelos (Regressão Logística, Árvore de Decisão, Random Forest), gera um score de
risco por cliente e salva tudo na pasta `resultados/`.

## Como rodar

```bash
pip install -r requirements.txt
python churn.py                      # baixa a base automaticamente se não existir
pytest -v                            # roda os testes
```

Opções:

| Opção | Para que serve |
|---|---|
| `--csv caminho.csv` | usar outro CSV (padrão: `data/Telco-Customer-Churn.csv`) |
| `--saida pasta` | pasta de resultados (padrão: `resultados`) |
| `--coluna-data coluna` | usar uma coluna de **data real** para churn por mês/semestre/ano |
| `--data-referencia 2026-06-30` | data usada para **estimar** a adesão (veja aviso abaixo) |
| `--sem-graficos` | não gera PNGs |

## Estrutura do `churn.py`

| Parte | Responsável | Funções principais |
|---|---|---|
| 1 – Leitura e limpeza | | `carregar_dados`, `inspecionar_dados`, `limpar_dados`, `detectar_outliers` |
| 2 – EDA e features | | `churn_por_categoria`, `churn_por_faixa_tenure`, `taxa_churn_por_periodo`, `sugerir_limite_cliente_recente`, `criar_features` |
| 3 – Modelos | | `preparar_xy`, `dividir_treino_teste`, `criar_modelos`, `treinar_e_avaliar`, `gerar_score_risco` |
| 4 – Integração | | `executar_pipeline`, `main`, `test_churn.py`, este README |

## Decisões de limpeza (conforme a documentação)

- `TotalCharges` vazio com `tenure = 0` → vira `0` (cliente novo, ainda não cobrado). Vazio com `tenure > 0` seria removido.
- Categorias **não** são fundidas: `No internet service` ≠ `No`.
- Outliers são apenas **reportados** (IQR), nunca removidos automaticamente.
- `customerID` só serve para checar duplicidade; não entra no modelo.
- O CSV bruto nunca é alterado.

## Features criadas

`gasto_medio_observado`, `qtd_servicos_ativos`, `contrato_mensal`, `cliente_recente`
(limite de tenure escolhido a partir dos dados, por uma árvore de profundidade 1).

## Sem vazamento de dados

Imputação, padronização e one-hot ficam dentro de um `Pipeline` do scikit-learn e são
ajustados **só no treino**. Divisão estratificada com semente fixa (42). O score de risco
usa validação cruzada, então nenhum cliente é pontuado por um modelo que o viu no treino.

## Saídas em `resultados/`

`dados_limpos.csv`, `dados_com_features.csv`, `churn_por_*.csv`, `churn_mensal.csv`,
`churn_semestral.csv`, `churn_anual.csv`, `metricas_modelos.csv`,
`importancia_variaveis_rf.csv`, `score_risco_clientes.csv` (alimenta o dashboard),
`relatorio.json` e gráficos PNG.

## ⚠️ Aviso sobre churn por mês/semestre/ano

A base da IBM **não tem coluna de data**. Sem `--coluna-data`, o script *estima* a data de
adesão (`data_referencia − tenure`) e agrupa por coorte de entrada. Isso mostra o churn por
**safra de clientes**, e não o churn ocorrido em cada mês do calendário. Safras recentes
terão churn alto porque os clientes novos cancelam mais, o que é um efeito do `tenure`, e não uma
tendência no tempo. Se tiver uma planilha com datas reais, use `--coluna-data`.