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

## Estrutura prevista para publicação

```text
README.md
Notebook.ipynb                  # plano e entendimento do problema
Notebook-Etapa2.ipynb           # análise, preparação e modelagem
Relatorio-Etapa3.md             # relatório técnico
Relatorio-Etapa3.html           # versão formatada do relatório
Relatório de solução_ Steelproof.pdf
build_relatorio.py              # gerador do relatório HTML
data/                            # local, não versionado
```

O notebook revisado com comentários do avaliador é material interno e não deve ser publicado.
Backups, checkpoints, arquivos `Zone.Identifier`, `.DS_Store` e o ZIP original também devem ficar
fora do repositório público.

## Dados

Os sete CSVs vieram do material do bootcamp. Eles devem permanecer fora do repositório público até
que os termos de uso da TripleTen confirmem que sua redistribuição é permitida.

Para uma publicação segura, o notebook deve apontar para uma pasta local como:

```text
data/raw/final_steel_en/
```

O repositório público pode documentar os nomes e o esquema dos arquivos sem incluir os dados
originais. Se necessário, uma versão futura pode fornecer dados sintéticos para demonstrar a
execução.

## Ambiente

O projeto foi desenvolvido em Python com pandas, scikit-learn, LightGBM e CatBoost. As versões
exatas devem ser registradas em `requirements.txt` antes da publicação para tornar a execução
reproduzível.

## Próximos passos metodológicos

1. Fixar o instante exato em que a previsão estaria disponível.
2. Agregar somente os eventos ocorridos antes desse instante.
3. Separar treino, validação e teste final, usando o último bloco apenas uma vez.
4. Reavaliar o MAE, a cauda de erro e a regra de confiança.
5. Documentar as versões das dependências e o procedimento de execução.

## Relatório

O PDF e o relatório HTML sintetizam o problema de negócio, a auditoria das fontes, as decisões de
modelagem, os resultados e as limitações. O relatório não converte a economia estimada para reais
porque a unidade da variável `Active power` não está documentada nos dados.

## Segurança e publicação

Antes do primeiro push, verificar se o repositório não contém dados originais, notebook de revisão,
backups, arquivos temporários, caminhos pessoais, credenciais ou artefatos de sistema. O PDF público
deve ser a versão final de entrega, sem comentários internos do avaliador.
