# Relatório de solução: previsão da temperatura final do banho

## Steelproof, redução do consumo energético no forno-panela

Etapa 3 do Projeto Final. Bootcamp de Data Science, TripleTen.
Autor: Fernando Szekut. Agosto de 2026.

---

## Resumo

A Steelproof quer gastar menos energia elétrica no refino do aço. O consumo se concentra no
forno-panela, onde o banho é reaquecido por arco elétrico até chegar à temperatura de
lingotamento. Hoje essa temperatura é buscada por tentativa e erro: aquece-se, mede-se, e se
faltou, aquece-se de novo. Cada iteração desnecessária é energia desperdiçada e tempo de forno
ocupado.

Construí um modelo que prevê em que temperatura o banho vai terminar, a partir da condição inicial
da corrida e do tratamento que se pretende aplicar. Ele responde a uma pergunta condicional: em
que temperatura a corrida termina se eu aplicar este plano de aquecimento. É isso que permite
comparar planos antes de gastar a energia, em vez de descobrir o resultado depois.

O modelo entrega erro médio absoluto (MAE, do inglês *mean absolute error*) de 5,22 °C em 488
corridas posteriores no tempo, que ele nunca viu. A meta que fixei no plano de trabalho era
6,8 °C, e o piso de referência, o que se acerta chutando sempre a média histórica, é 10,42 °C. O
erro cai pela metade em relação a não ter modelo nenhum, e sete em cada dez corridas ficam dentro
da tolerância.

O desperdício que isso permite cortar fica entre 2,8% e 5,6% da energia de arco por corrida no
cenário que considero realista, o equivalente a deixar de aplicar de 0,13 a 0,26 ciclo de
aquecimento em cada corrida, de um total médio de 4,6. Converter esse valor para reais depende de
uma informação que os dados não trazem, e digo adiante qual é e como obtê-la.

O modelo não serve igualmente para todas as corridas, e essa é a informação mais útil do
trabalho. As corridas em que ele erra muito são reconhecíveis antes de começarem, pelo volume de
tratamento planejado, o que permite entregá-lo com uma regra de uso em vez de aplicá-lo às cegas.

---

# O cenário

## O que a Steelproof quer resolver

Reduzir o consumo de energia elétrica no processamento do aço. Na metalurgia de panela, o aço
líquido chega do forno de fusão, recebe adições de liga e é reaquecido por eletrodos de grafite
até a temperatura correta para o lingotamento. O reaquecimento por arco é o item pesado da conta
de energia dessa etapa.

## Por que isso custa caro hoje

A temperatura de destino é conhecida, porque a faixa de lingotamento é especificação. O que não se
sabe é em que temperatura a corrida vai efetivamente terminar depois do tratamento aplicado. A
incerteza está no resultado, não na meta.

No registro completo da planta, antes de qualquer filtro de qualidade, cada corrida recebe em
média 4,6 ciclos de aquecimento e 4,0 medições de temperatura. O padrão descreve um processo
iterativo: aquece, mede, avalia, repete. Duas fontes de desperdício saem daí.

A primeira é a margem de segurança. Sem saber onde a corrida vai parar, o caminho seguro é aquecer
um pouco a mais. Aço frio no lingotamento causa problema imediato de qualidade, enquanto aço um
pouco quente demais custa apenas energia. A assimetria empurra a operação para o lado caro, e a
margem embutida é proporcional à incerteza sobre o resultado.

A segunda é a iteração. Cada ciclo extra de aquecimento tem custo energético, e cada medição extra
consome um sensor descartável e interrompe o processo. Extrapolando o ritmo observado nos dados,
27 corridas por dia, a planta faz cerca de 9.850 corridas e 40 mil medições de temperatura por
ano.

## Por que vale resolver

Reduzir a incerteza sobre a temperatura final ataca as duas fontes ao mesmo tempo. Permite
encolher a margem de segurança e permite dimensionar o aquecimento de uma vez, em vez de convergir
por tentativas. Não se trata de aquecer menos do que o processo precisa. Trata-se de parar de
pagar pela ignorância sobre onde ele vai terminar.

## O critério de sucesso

No plano de trabalho da Etapa 1 fixei MAE de no máximo 6,8 °C como indicador-chave de desempenho
(KPI, do inglês *key performance indicator*). O número não é arbitrário. Ele precisa ser bem menor
que a dispersão natural do alvo para que a previsão carregue informação. A temperatura final tem
desvio-padrão de apenas 15,9 °C, cerca de metade da dispersão da temperatura de entrada. Prever
dentro de 6,8 °C significa acertar dentro de menos da metade de um desvio-padrão, o que torna o
problema mais difícil do que a escala absoluta em graus sugere.

---

# Desenvolvimento do projeto

## Dados e qualidade iniciais

São sete arquivos, ligados pela coluna `key`, que identifica a corrida:

| Fonte | Conteúdo | Granularidade |
|---|---|---|
| `data_arc` | potência ativa e reativa, início e fim de cada aquecimento | 1 linha por ciclo |
| `data_temp` | medições de temperatura com horário | 1 linha por medição |
| `data_gas` | volume de gás de purga | 1 linha por corrida |
| `data_bulk` e `data_bulk_time` | massa e horário de 15 materiais a granel | 1 linha por corrida |
| `data_wire` e `data_wire_time` | massa e horário de 9 materiais em arame | 1 linha por corrida |

Nenhuma linha duplicada. A contagem de corridas varia entre as fontes, 3.239 no gás, 3.216 na
temperatura, 3.081 no arame, o que significa que o cruzamento gera ausências por falta de
registro. Cada tipo de ausência precisa de tratamento próprio.

Encontrei cinco problemas de qualidade. O primeiro é uma potência reativa fisicamente impossível,
um registro de menos 715,5 contra mediana de 0,42, três ordens de grandeza fora da faixa e com
sinal invertido. Marquei como ausente, e não como zero, porque zero afirmaria que não houve
potência reativa quando o que se sabe é apenas que a leitura não serve.

O segundo são as corridas sem duas medições de temperatura. O alvo é a última temperatura
registrada e o atributo de entrada é a primeira, de modo que corridas com uma única medição não
permitem separar entrada de saída. Sobraram 2.475 das 3.216.

O terceiro é a mudança de protocolo em 06/08/2019. A partir dessa data o registro passa de
múltiplas medições por corrida para uma só. O padrão é compatível com alteração no procedimento de
gravação e não com falha de sensor, porque falha produziria ausência ou valor inválido, não uma
mudança sistemática de formato. Cortei o período posterior.

O quarto são as durações de tratamento fora da faixa operacional, com máximo de 395 minutos contra
mediana de 31. Cortei fora do intervalo de 1 a 100,6 minutos, com lastro no processo: tratamento
muito longo implica troca de calor com o refratário que descaracteriza a corrida.

O quinto são quatro temperaturas iniciais impossíveis, entre 1.191 e 1.227 °C contra mínimo
operacional de 1.519 °C. Não as removi por serem estatisticamente atípicas, e sim porque as duas
leituras da corrida são mutuamente incompatíveis. Elas implicariam elevação de 365 a 408 °C
consumindo de 0,6% a 3,8% da energia que a planta gasta para isso. Não importa qual das duas
leituras está errada, porque o par não pode estar certo.

A limpeza custou 24% das corridas, quase todas pelo segundo item.

## Proteção contra vazamento de informação

A armadilha central deste problema é o vazamento de informação. Se qualquer medição intermediária
de temperatura entrar como atributo, o erro despenca artificialmente e o modelo fica inútil na
prática, porque no momento em que se quer usá-lo essas medições ainda não existem.

Admiti como atributo apenas a primeira medição de cada corrida. O alvo é a última. Os timestamps e
a chave `key` ficaram fora dos atributos, para que o modelo não decore a posição da corrida na
série de produção. Padronizei a escala dentro de um `Pipeline` reajustado a cada dobra da
validação, de modo que nem a média usada na normalização vaze do futuro para o passado.

## Divisão entre treino e teste

Usei corte cronológico de 80/20, com as 1.950 primeiras corridas para treino e as 488 seguintes
para teste. A separação é posicional: ordenei as corridas pelo horário da primeira medição e
cortei na posição 1.950. Nenhuma corrida aparece nos dois conjuntos.

O corte cai dentro do dia 19/07, que por isso tem corridas dos dois lados, 8 no treino e 13 no
teste. A última corrida de treino começa às 8h09 e a primeira de teste às 9h06, de forma que a
ordem temporal é respeitada mesmo dentro do dia da fronteira. O treino cobre de 03/05 a 19/07 e o
teste de 19/07 a 05/08.

Amostragem aleatória seria mais generosa e menos honesta, porque com ordem temporal embaralhar
permite que o modelo aprenda com corridas posteriores às que está avaliando.

Testei antes se havia deriva no alvo ao longo do período, e não há: as médias mensais ficam entre
1.594 e 1.597 °C. O corte cronológico não é necessário por instabilidade dos dados. Ele é
necessário porque simula a condição real de uso, em que só se conhece o passado.

## Colinearidade

As variáveis energéticas medem a mesma coisa por caminhos diferentes, e o diagnóstico pelo fator
de inflação da variância (VIF, do inglês *variance inflation factor*) confirma:

| Atributo | VIF |
|---|---:|
| tempo de arco | 37,9 |
| potência ativa | 29,2 |
| potência reativa | 16,2 |
| energia | 11,9 |

Acima de 10 já é colinearidade grave. Numa regressão comum isso torna os coeficientes instáveis a
ponto de inverter sinal, e o modelo poderia concluir que mais arco esfria o aço. Foi por isso que
usei Ridge no lugar da regressão linear pura, porque a penalização estabiliza os coeficientes sob
colinearidade. Modelos de árvore não sofrem do problema.

## Modelos avaliados

Avaliei quatro famílias, mais o piso de referência, todas com busca de hiperparâmetros em
validação cruzada temporal. O `DummyRegressor` na média serve de piso, ou seja, o que se acerta
sem modelo algum. O Ridge é a referência linear, com a colinearidade sob controle. O Random Forest
captura interações não lineares. O LightGBM aplica boosting regularizado. O CatBoost entrou por
causa da esparsidade das colunas de adição, já que 22 das 34 ficam em zero na maioria das corridas.

---

# Resultados

## Desempenho comparado

Todos os números abaixo estão medidos nas 488 corridas de teste, posteriores no tempo. RMSE é a
raiz do erro quadrático médio e R² o coeficiente de determinação:

| Modelo | MAE treino | MAE teste | RMSE | R² | Redução do erro vs. piso | Atinge meta |
|---|---:|---:|---:|---:|---:|:---:|
| Dummy (média) | 10,19 | 10,42 | 15,56 | −0,02 | | não |
| Ridge | 6,05 | 6,72 | 9,38 | 0,63 | 35,5% | sim |
| Random Forest | 3,14 | 5,63 | 7,47 | 0,77 | 45,9% | sim |
| CatBoost | 4,76 | 5,42 | 7,14 | 0,79 | 48,0% | sim |
| LightGBM | 3,73 | 5,30 | 7,09 | 0,79 | 49,2% | sim |
| LightGBM calibrado | | 5,22 | 7,09 | 0,79 | 49,9% | sim |

Há uma observação metodológica que faz diferença no número relatado. No plano de trabalho eu havia
estimado o piso em 12,8 °C. Medido nos dados limpos, ele é 10,42 °C. Calculei a redução contra o
valor medido. Manter a estimativa do plano teria inflado o resultado relatado de 49,9% para 59,2%
sem que uma única linha do modelo mudasse.

## Seleção do modelo final

Escolhi o LightGBM com calibração de viés. A diferença de MAE para o CatBoost é de 0,12 °C, abaixo
do limiar de 0,3 °C que eu havia fixado no plano como diferença relevante. Quando o erro não
desempata, o critério passa a ser outro, e comparei então a importância dos atributos das duas
famílias. Elas apontam os mesmos atributos, na mesma ordem, o que indica que ambas capturam física
do processo e não idiossincrasia do algoritmo. Fiquei com o LightGBM pelo erro marginalmente
menor, e registro o CatBoost como alternativa equivalente.

A calibração de viés é um ajuste barato e de efeito real. O modelo bruto subestimava a temperatura
em 1,26 °C de forma sistemática. Estimei esse deslocamento nos últimos 10% do treino, uma faixa
separada que não é o teste, e o descontei. O viés cai para 0,25 °C, o MAE de 5,30 para 5,22 °C, e
a fração de corridas dentro da tolerância sobe de 70,5% para 72,1%, sem nenhuma complexidade
adicional no modelo.

## O que o modelo aprendeu

Medi a importância por permutação no conjunto de teste, método que não favorece atributos de alta
cardinalidade como faria a importância interna das árvores:

| Atributo | Importância (°C de MAE) |
|---|---:|
| temperatura inicial | 6,12 |
| potência ativa total | 2,72 |
| massa total de arame | 1,32 |
| energia | 1,15 |
| duração total do arco | 0,76 |
| adições específicas (arame 1, granel 6) | 0,33 e 0,30 |
| intervalo desde a corrida anterior | 0,05 |

A leitura é fisicamente coerente. Onde o banho começa domina, seguido do quanto de energia
elétrica foi aplicada e das adições que consomem calor para se dissolver. Os resíduos não mostram
padrão contra a temperatura inicial, o que indica que não sobrou sinal óbvio na mesa.

Uma hipótese minha não se sustentou. Eu havia proposto o intervalo desde a corrida anterior como
proxy do estado térmico do refratário, supondo que panela recém-usada estaria mais quente e
roubaria menos calor do banho. A importância ficou em 0,05 °C, praticamente zero. Registro o
resultado como ele saiu, porque a hipótese era razoável e os dados não a confirmaram.

## Onde o modelo erra, e por que isso é útil

Dizer que 72% das corridas ficam dentro da tolerância deixa 28% de fora, e errar 7 °C é diferente
de errar 25 °C. Por isso quebrei o erro em faixas:

| Faixa de erro | % das corridas de teste |
|---|---:|
| até 3 °C | 38,5% |
| 3 a 6,8 °C | 33,6% |
| 6,8 a 10 °C | 15,0% |
| 10 a 20 °C | 10,9% |
| acima de 20 °C | 2,0% |

O erro mediano é de 3,97 °C, o percentil 90 fica em 11,13 °C e o máximo em 30,10 °C.

A cauda é o que limita o uso. Cerca de uma corrida em cada oito, 12,9%, erra mais de 10 °C, e
nessas a estimativa não substitui a medição. A pergunta prática é se dá para reconhecer essas
corridas antes de rodá-las, e a resposta é sim:

| | Corridas com erro > 10 °C | Demais | Diferença |
|---|---:|---:|---:|
| temperatura inicial | 1.596,1 °C | 1.586,3 °C | +0,6% |
| energia total | 0,26 | 0,19 | +38,7% |
| duração do arco | 36,8 min | 28,9 min | +27,5% |
| potência ativa somada | 3,70 | 2,98 | +24,3% |

As corridas ruins não se distinguem pela temperatura de entrada, que é praticamente igual à das
demais. Elas se distinguem pelo volume de tratamento, e são as corridas longas e pesadas.

A leitura física é direta. Quanto mais longo o tratamento, mais tempo o banho troca calor com o
refratário, com o ambiente e com as adições, e mais o resultado depende de fatores que não estão
nos dados. O modelo é confiável no regime normal de operação e perde precisão exatamente onde o
processo se afasta dele.

A consequência prática é o motivo de eu ter feito esta análise. O que separa as corridas ruins não
é a temperatura de entrada, que ninguém escolhe, e sim o volume de tratamento, que é decidido
antes de a corrida começar. Um plano que prevê muita energia e arco longo já sinaliza que ali a
estimativa merece confirmação por medição.

Registro o limite dessa leitura. As diferenças acima estão medidas sobre energia e arco
realizados, porque é o que os arquivos trazem. Transpor a regra para o plano supõe que o planejado
se aproxima do executado, o que é razoável para dimensionamento mas não consigo verificar com
estes dados.

---

## Estimativa de impacto no negócio

A coluna `Active power` não tem unidade documentada. Tentei calibrá-la pela física, comparando a
energia registrada com a elevação de temperatura obtida, e a massa implicada não bate com a
capacidade de 100 t informada sob nenhuma hipótese razoável de rendimento. Isso não invalida o
modelo, porque ele aprende a relação entre a grandeza registrada e a temperatura seja qual for a
escala dela, mas invalida qualquer conversão direta para megawatt-hora ou para reais.

Apresento então o impacto em três camadas, da mais firme para a mais dependente de informação
externa: a grandeza física adimensional, que os dados sustentam por inteiro; a tradução para
unidades operacionais que a planta reconhece; e a fórmula pronta para a conversão financeira,
faltando um único parâmetro que só a planta tem.

### Mecanismo da redução

Sem modelo, a incerteza sobre em que temperatura a corrida vai terminar é de 10,42 °C. Com o
modelo, é de 5,22 °C. A margem de segurança térmica pode encolher em até 5,20 °C, e essa é a
grandeza que o projeto entrega.

Converter graus em energia exige saber quanto a planta gasta por grau na margem, e não em média,
porque são coisas diferentes. A energia de uma corrida paga duas contas ao mesmo tempo: elevar a
temperatura do banho e repor o calor que ele perde para o refratário, para o ambiente e para as
adições enquanto é tratado. A segunda parcela não desaparece quando se mira dois graus mais baixo.
Dividir energia total por elevação obtida misturaria as duas contas e superestimaria a economia.

Separei-as regredindo a energia de cada corrida contra a elevação obtida e a duração do
tratamento. A elevação responde por 0,00429 unidades de energia por grau, e a duração por 0,00439
unidades por minuto, com R² de 0,64. É o primeiro coeficiente que interessa aqui, porque é ele que
mede o que se deixa de gastar ao mirar mais baixo:

| Cenário | Margem reduzida | Energia poupada por corrida | % da energia de arco | Ciclos evitados |
|---|---:|---:|---:|---:|
| Conservador, captura 1/4 da margem | 1,30 °C | 0,0056 | 2,8% | 0,13 |
| Central, captura metade | 2,60 °C | 0,0112 | 5,6% | 0,26 |
| Teto, captura a margem inteira | 5,20 °C | 0,0223 | 11,3% | 0,52 |

A hipótese que separa os cenários é quanto da margem de segurança a operação de fato consegue
liberar. O teto supõe que hoje se sobreaquece exatamente o equivalente à incerteza, o que é
agressivo, porque parte da margem existente responde a fatores que o modelo não elimina. Considero
o cenário conservador o piso defensável e o central a expectativa realista.

Duas ressalvas sobre a estimativa do coeficiente. Ela é observacional: a energia aplicada causa a
elevação e a duração é escolhida pelo operador, de modo que o número não é uma medida causal
limpa. E ela não é constante ao longo da faixa, variando por fator de 2,7 entre as corridas que
menos e as que mais aquecem, o que significa que a tabela vale para o regime médio de operação e
perde validade nos extremos.

### Impacto em unidades operacionais

Um ciclo de aquecimento consome em média 0,0428 unidades de energia. Nessa escala, o cenário
conservador equivale a deixar de aplicar 0,13 ciclo por corrida, cerca de 1.280 ciclos por ano no
ritmo de 9.850 corridas anuais. O cenário central equivale a 0,26 ciclo por corrida, cerca de
2.570 ciclos por ano, ou 5,6% de toda a energia de arco da planta.

Há um efeito paralelo que não entra nessa conta e é mais fácil de auditar, que são as medições de
temperatura. A planta faz cerca de 40 mil por ano, cada uma consumindo um sensor descartável e
interrompendo o processo. Um modelo que acerta dentro de 3 °C em 38,5% das corridas e dentro de
6,8 °C em 72% permite reduzir a frequência de medição de confirmação nas corridas do regime
normal, mantendo-a integral nas 13% de cauda que a regra da seção anterior identifica de antemão.

### A conversão financeira

Falta um único número, e ele não está nos dados:

```
Economia anual (R$) = 9.850 corridas × 0,0056 a 0,0112 unidades de energia por corrida
                      × [ R$ por unidade de "Active power" ]
```

Traduzindo: a economia anual fica entre 55 e 110 unidades de energia, na escala em que a coluna
`Active power` é registrada. Assim que a planta informar o que essa coluna mede, e o custo do
megawatt-hora que ela pratica, a conta fecha em reais em uma linha.

Registro isso como pergunta a fazer, não como número a estimar. Chutar um fator de conversão
produziria um valor bonito e indefensável.

### Efeitos não energéticos

Há três efeitos que vale citar sem quantificar, porque quantificá-los exigiria dados que não estão
aqui.

Deixar de aplicar de 0,13 a 0,26 ciclo por corrida libera capacidade do forno-panela. Se o forno
for gargalo da linha, esse efeito pode superar o de energia. Se não for, ele não se materializa.
Depende do arranjo da planta, que eu não conheço.

Reduzir a variabilidade da temperatura de entrega também deve reduzir a incidência de corridas
fora da faixa de lingotamento, e portanto o retrabalho. Não consigo medir isso, porque os dados
não trazem descarte nem qualquer indicador de qualidade.

Menos tempo de arco significa ainda menos consumo de eletrodo de grafite e menos agressão térmica
ao revestimento refratário. O efeito vai na mesma direção da economia de energia, mas não tenho
base nos dados para dimensioná-lo.

---

## O que o modelo não sabe

Entrego esta seção junto com o resultado porque um MAE dentro da meta é fácil de ler como problema
resolvido, e não é o caso.

Começo pelo que é o inverso dos demais: em parte das corridas o modelo sabe demais. As variáveis
de processo agregam a corrida inteira, mas nem sempre a última medição de temperatura é o último
evento. Em 135 corridas, 5,5% do total, há aquecimento ou adição posteriores ao instante do alvo.
Nessas, a energia somada carrega informação que ainda não existia quando a previsão seria feita. O
MAE de 5,22 °C está provavelmente um pouco otimista por causa disso. O caminho correto é fixar o
instante da previsão e agregar apenas o que ocorreu antes dele, e é o primeiro item que eu
refaria.

O modelo não vê a composição química da corrida. Ligas diferentes têm calor específico diferente,
e nada nos sete arquivos identifica qual liga está sendo produzida. Parte do erro residual quase
certamente vem daí, e nenhum ajuste de hiperparâmetro alcança essa informação.

O modelo não vê o estado do refratário, a temperatura ambiente, o desgaste dos eletrodos nem a
panela específica de cada corrida. A única proxy disponível foi testada e não funcionou.

O período coberto é de três meses. Não encontrei deriva dentro dessa janela, mas três meses não
garantem estabilidade ao longo de um ano.

O formato de gravação mudou em 06/08/2019. Se ele continuar como ficou, dados novos chegam com uma
única medição por corrida e não servem nem para treinar nem para validar o modelo.

---

## Conclusões e recomendações

O que está entregue é um modelo que prevê a temperatura final do banho com erro médio de 5,22 °C,
contra 10,42 °C de não ter modelo nenhum. A meta de 6,8 °C foi atingida com folga, 72% das
corridas ficam dentro da tolerância, e a avaliação foi feita em corridas posteriores no tempo que
o modelo nunca viu. Junto com ele vai uma regra que diz onde confiar nele e onde não confiar.

Deixo cinco recomendações, em ordem de retorno sobre esforço.

A primeira é adotar o modelo com regra de uso diferenciada, e não como número único. Nas corridas
do regime normal, com plano de tratamento dentro da faixa usual de energia e arco, a previsão
dimensiona o aquecimento e reduz a medição de confirmação. Nas corridas de tratamento longo e
pesado, que os dados mostram serem cerca de 13% e que são identificáveis pelo plano, o modelo
entra como orientação e a medição continua obrigatória. É a recomendação de maior valor imediato e
não exige nenhum dado novo.

A segunda é informar o que a coluna `Active power` mede. É a única pendência entre a economia
física já demonstrada e a economia em reais. Uma resposta da engenharia da planta resolve, e sem
ela nenhuma estimativa financeira deste projeto se sustenta.

A terceira é restabelecer o registro de múltiplas medições de temperatura por corrida. O protocolo
mudou em 06/08/2019 e, se permanecer assim, o modelo não pode ser retreinado nem revalidado com
dados novos. É decisão da fábrica, não do modelo, e sem ela o projeto tem prazo de validade.

A quarta é refazer o recorte temporal dos atributos antes de tratar 5,22 °C como número final.
Agregaria apenas operações anteriores ao instante da previsão e mediria o resultado em um bloco de
tempo ainda não utilizado, porque este conjunto de teste também serviu para escolher entre as
quatro famílias de modelo, de modo que o número atual tem um grau a menos de independência do que
o ideal.

A quinta é registrar a liga produzida em cada corrida. É a informação ausente com maior potencial
de reduzir o erro residual. Não altera nada no que já foi entregue, mas define o teto de uma
versão futura.

Fecho com uma ressalva. O objetivo que declarei na Etapa 1, dimensionar o aquecimento em vez de
buscá-lo por tentativa e erro, é alcançável com o que está aqui, desde que o modelo seja lido como
comparação entre planos de tratamento e não como previsão passiva de uma corrida parada na
entrada. É essa leitura condicional que transforma uma estimativa de temperatura em decisão de
quanta energia aplicar, e é dela que vem a economia.
