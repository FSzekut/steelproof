# Steelproof

Modelo de regressão para prever a temperatura final do aço no refino secundário em forno-panela e
apoiar decisões de aquecimento com menor consumo de energia.

Projeto final do bootcamp de Data Science da TripleTen, desenvolvido por Fernando Szekut.

## O problema

No forno-panela, a temperatura é ajustada por ciclos sucessivos de aquecimento e medição. O
objetivo do Steelproof é responder a uma pergunta condicional:

> Dado o estado inicial da corrida e o plano de tratamento aplicado, em que temperatura o banho
> tende a terminar?

Essa formulação permite comparar planos de aquecimento antes de gastar energia, em vez de descobrir
o resultado apenas depois da medição final.

## Resultado apresentado

Na avaliação original, o LightGBM calibrado alcançou MAE de 5,22 °C em 488 corridas posteriores no
tempo. O modelo trivial, que sempre prevê a média histórica, alcançou 10,42 °C. A meta definida no
plano de trabalho era 6,8 °C.

A análise da cauda mostrou que 12,9% das corridas tiveram erro superior a 10 °C. Essas corridas
foram associadas a maior volume de tratamento, com mais energia e maior duração de arco, o que levou
à recomendação de usar o modelo com uma regra de confiança e manter confirmação por medição nos
casos mais pesados.

O resultado de 5,22 °C é promissor, mas ainda preliminar como estimativa final. A auditoria interna
identificou pontos a corrigir antes de tratá-lo como avaliação definitiva, principalmente o
alinhamento temporal de algumas variáveis de processo e o uso do mesmo conjunto de teste para
comparar modelos e escolher o candidato final.

## Dados e variáveis

As fontes originais são sete arquivos ligados pela coluna `key`:

- `data_arc`: potência ativa e reativa, início e fim de cada aquecimento;
- `data_temp`: medições de temperatura e horários;
- `data_gas`: purga com gás inerte;
- `data_bulk` e `data_bulk_time`: materiais a granel e seus horários;
- `data_wire` e `data_wire_time`: materiais em arame e seus horários.

O modelo usa a primeira temperatura como condição inicial e a última temperatura válida como alvo.
O tratamento inclui auditoria de qualidade, engenharia de atributos, validação temporal e comparação
entre Ridge, Random Forest, LightGBM e CatBoost.

## Estrutura

```text
README.md
Notebook.ipynb                  # plano e entendimento do problema
Notebook-Etapa2.ipynb           # análise, preparação e modelagem
Relatorio-Etapa3.md             # relatório técnico
Relatorio-Etapa3.html           # versão formatada, autocontida
Relatório de solução_ Steelproof.pdf
build_relatorio.py              # gerador do relatório HTML
requirements.txt
data/                           # local, não versionado — ver abaixo
```

## Dados

**Os sete CSVs não acompanham este repositório.** São material do bootcamp da TripleTen, e o
código é meu mas os dados não. Redistribuí-los exigiria uma autorização que não tenho, então a
opção foi publicar tudo o que descreve o trabalho e nada que pertença a terceiros.

Na prática isso custa pouco a quem lê: os notebooks estão com todas as saídas preservadas, de modo
que a auditoria de qualidade, os tratamentos, as decisões de modelagem e os resultados são
verificáveis célula a célula sem executar nada.

Para executar, coloque os arquivos em:

```text
data/raw/final_steel_en/
```

com os nomes originais — `data_arc_en.csv`, `data_bulk_en.csv`, `data_bulk_time_en.csv`,
`data_gas_en.csv`, `data_temp_en.csv`, `data_wire_en.csv`, `data_wire_time_en.csv`. O notebook
procura nesse caminho primeiro e falha com uma mensagem explícita se não encontrar.

## Sobre o histórico deste repositório

Este repositório não herda o histórico do desenvolvimento, e isso é deliberado.

O trabalho foi desenvolvido em um repositório do bootcamp que continha os dados originais desde o
primeiro commit, junto com o material de outro caso e o notebook com os comentários do avaliador.
Publicar aquele histórico exporia os três. Como um `.gitignore` não alcança arquivos já
versionados, e reescrever o histórico é mais arriscado que recomeçar, optei por um repositório
novo contendo apenas os artefatos publicáveis.

A perda é real: o histórico mostraria a ordem em que as decisões foram tomadas, que é informação
legítima para quem avalia o trabalho. O relatório compensa em parte, porque registra as decisões
com a razão de cada uma, incluindo as que mudaram de ideia no caminho — a taxa marginal corrigida
e o piso de referência remedido estão lá, com o antes e o depois.

## Ambiente

Python com pandas, scikit-learn, LightGBM e CatBoost. As versões efetivamente usadas estão em
`requirements.txt`:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Próximos passos metodológicos

1. Fixar o instante exato em que a previsão estaria disponível.
2. Agregar somente os eventos ocorridos antes desse instante.
3. Separar treino, validação e teste final, usando o último bloco apenas uma vez.
4. Reavaliar o MAE, a cauda de erro e a regra de confiança.
5. Documentar as versões das dependências e o procedimento de execução.

## Relatório

`Relatorio-Etapa3.html` é a versão de leitura: autocontida, com os gráficos embutidos, e abre
direto no navegador. Sintetiza o problema de negócio, a auditoria das fontes, as decisões de
modelagem com os hiperparâmetros de cada uma, os resultados e as limitações. O PDF é a versão
entregue na avaliação e acompanha o repositório.

O relatório **não converte a economia estimada para reais**, e isso é intencional. A unidade da
variável `Active power` não está documentada, e a massa implicada não fecha com a capacidade
informada sob nenhuma hipótese de rendimento. Em vez de arbitrar um fator e produzir um número
apresentável, o relatório entrega a fórmula com o parâmetro em aberto e registra a pergunta a
fazer à planta.

Para regerar o HTML após editar o Markdown:

```bash
python build_relatorio.py
```
