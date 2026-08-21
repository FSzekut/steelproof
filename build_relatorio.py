"""Gera o HTML do Relatório da Etapa 3 a partir do Markdown, com gráficos embutidos.

Uso:  python build_relatorio.py
Saída: Relatorio-Etapa3.html  (autocontido; abrir no navegador e imprimir como PDF)

Os números plotados são os medidos no Notebook-Etapa2.ipynb, transcritos aqui para que
o relatório não dependa de reexecutar o treinamento.
"""

import base64
import io
import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import markdown
from PIL import Image

def num(v, casas=1):
    """Formata número com arredondamento meio-para-cima e vírgula decimal.

    O `%.1f` do Python arredonda meio-para-par e ainda sofre com a representação
    binária: 38.65 sai como "38,6", enquanto a tabela do Markdown diz 38,7. Duas
    versões do mesmo número na mesma página. Aqui o critério é o da tabela.
    """
    q = Decimal(1).scaleb(-casas)
    return str(Decimal(str(v)).quantize(q, rounding=ROUND_HALF_UP)).replace(".", ",")


AQUI = Path(__file__).parent
# Duas paletas, espelhando as variáveis do CSS. O relatório tem tema escuro
# desde sempre, mas os gráficos eram só claros: no escuro cada um virava uma
# placa acesa no meio do texto. Agora cada gráfico sai nas duas versões e o
# CSS escolhe, porque o tema pode vir do sistema ou do botão.
PALETA_CLARA = {
    "tinta": "#1c2833", "azul": "#2c5f8a", "azul_claro": "#7fa8c7",
    "verde": "#3d7a5a", "cinza": "#9aa5ad", "vermelho": "#b04a3a",
    "ambar": "#d9a441", "grade": "#eef1f3", "borda": "#cfd6db", "fundo": "#fffdfb",
}
PALETA_ESCURA = {
    "tinta": "#dfe4e8", "azul": "#84b4dc", "azul_claro": "#5c86a6",
    "verde": "#5f9e7d", "cinza": "#6b7280", "vermelho": "#c4553f",
    "ambar": "#c99a3e", "grade": "#242c36", "borda": "#39434f", "fundo": "#0e1319",
}

TINTA = AZUL = AZUL_CLARO = VERDE = CINZA = VERMELHO = AMBAR = GRADE = FUNDO = ""


def usar_paleta(p):
    """Aplica uma paleta aos globais e ao rcParams do matplotlib."""
    global TINTA, AZUL, AZUL_CLARO, VERDE, CINZA, VERMELHO, AMBAR, GRADE, FUNDO
    TINTA, AZUL, AZUL_CLARO = p["tinta"], p["azul"], p["azul_claro"]
    VERDE, CINZA, VERMELHO = p["verde"], p["cinza"], p["vermelho"]
    AMBAR, GRADE, FUNDO = p["ambar"], p["grade"], p["fundo"]
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9.5,
        "axes.edgecolor": p["borda"],
        # Sem estas duas a área do gráfico continua branca no tema escuro, e os
        # rótulos claros ficam ilegíveis em cima dela.
        "axes.facecolor": p["fundo"],
        "figure.facecolor": p["fundo"],
        "axes.labelcolor": p["tinta"],
        "text.color": p["tinta"],
        "xtick.color": p["tinta"],
        "ytick.color": p["tinta"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 160,
    })


usar_paleta(PALETA_CLARA)


def _png(fig):
    """Renderiza a figura em WebP, no fundo da paleta corrente.

    WebP em vez de PNG: um gráfico de barras com texto cai para cerca de um
    terço do tamanho sem diferença visível, e como agora cada um sai duas
    vezes (claro e escuro) o documento fica menor do que era com uma só.
    """
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=FUNDO)
    plt.close(fig)
    buf.seek(0)
    saida = io.BytesIO()
    Image.open(buf).convert("RGB").save(saida, format="WEBP", quality=90, method=6)
    return base64.b64encode(saida.getvalue()).decode()


def figura(gerador, legenda, alt):
    """Monta a figura com as duas versões do gráfico, claro e escuro."""
    usar_paleta(PALETA_CLARA)
    claro = gerador()
    usar_paleta(PALETA_ESCURA)
    escuro = gerador()
    usar_paleta(PALETA_CLARA)
    return (
        f'<figure><img class="claro" src="data:image/webp;base64,{claro}" alt="{alt}">'
        f'<img class="escuro" src="data:image/webp;base64,{escuro}" alt="{alt}">'
        f"<figcaption>{legenda}</figcaption></figure>"
    )


def grafico_modelos():
    """Comparação de MAE contra o piso e a meta."""
    nomes = ["Dummy\n(média)", "Ridge", "Random\nForest", "CatBoost", "LightGBM", "LightGBM\ncalibrado"]
    mae = [10.42, 6.72, 5.63, 5.42, 5.30, 5.22]
    cores = [CINZA, AZUL_CLARO, AZUL_CLARO, AZUL_CLARO, AZUL_CLARO, VERDE]

    fig, ax = plt.subplots(figsize=(7.0, 3.1))
    barras = ax.bar(nomes, mae, color=cores, width=0.62, zorder=3)
    ax.axhline(6.8, color=VERMELHO, ls="--", lw=1.2, zorder=4)
    ax.text(5.48, 6.98, "meta: 6,8 °C", color=VERMELHO, fontsize=8.5, ha="right")

    for b, v in zip(barras, mae):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.22, num(v, 2),
                ha="center", fontsize=8.8, color=TINTA)

    ax.set_ylabel("MAE no teste (°C)")
    ax.set_ylim(0, 12.2)
    ax.grid(axis="y", color=GRADE, zorder=0)
    ax.set_title("Erro médio absoluto por modelo, em 488 corridas posteriores no tempo",
                 fontsize=10, pad=10, loc="left")
    return _png(fig)


def grafico_faixas():
    """Distribuição do erro em faixas operacionais."""
    faixas = ["até 3 °C", "3 a 6,8 °C", "6,8 a 10 °C", "10 a 20 °C", "acima de 20 °C"]
    pct = [38.5, 33.6, 15.0, 10.9, 2.0]
    cores = [VERDE, VERDE, AMBAR, VERMELHO, VERMELHO]

    fig, ax = plt.subplots(figsize=(7.0, 2.6))
    esq = 0
    for p, c, f in zip(pct, cores, faixas):
        ax.barh([0], [p], left=esq, color=c, height=0.5, zorder=3)
        if p > 4:
            ax.text(esq + p / 2, 0, num(p) + "%", ha="center", va="center",
                    color="white", fontsize=9, fontweight="bold")
        esq += p

    ax.axvline(72.1, color=TINTA, lw=1.3, ls="--", zorder=5)
    ax.text(72.1, 0.42, "72,1% dentro da tolerância de ±6,8 °C", fontsize=8.5, ha="center", color=TINTA)

    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in
               [VERDE, AMBAR, VERMELHO]]
    ax.legend(handles, ["dentro da tolerância", "erro moderado (6,8 a 10 °C)",
                        "cauda, exige medição (>10 °C)"],
              loc="lower center", bbox_to_anchor=(0.5, -0.62), ncol=3, frameon=False, fontsize=8.3)

    ax.set_xlim(0, 100)
    ax.set_ylim(-0.4, 0.62)
    ax.set_yticks([])
    ax.set_xlabel("% das corridas de teste")
    ax.spines["left"].set_visible(False)
    ax.set_title("Onde o erro cai, por faixa de erro absoluto", fontsize=10, pad=18, loc="left")
    return _png(fig)


def grafico_cauda():
    """Perfil das corridas com erro alto contra as demais."""
    itens = ["Temperatura\ninicial", "Potência ativa\nsomada", "Duração\ndo arco", "Energia\ntotal"]
    dif = [0.62, 24.34, 27.48, 38.65]
    cores = [CINZA] + [VERMELHO] * 3

    fig, ax = plt.subplots(figsize=(7.0, 2.9))
    barras = ax.barh(itens, dif, color=cores, height=0.55, zorder=3)
    for b, v in zip(barras, dif):
        ax.text(v + 0.9, b.get_y() + b.get_height() / 2, "+" + num(v) + "%",
                va="center", fontsize=9, color=TINTA)

    ax.set_xlim(0, 46)
    ax.set_xlabel("diferença das corridas com erro > 10 °C em relação às demais")
    ax.grid(axis="x", color=GRADE, zorder=0)
    ax.invert_yaxis()
    ax.set_title("As corridas ruins se distinguem pelo tratamento, não pela entrada",
                 fontsize=10, pad=10, loc="left")
    return _png(fig)


def grafico_impacto():
    """Cenários de economia de energia, pela taxa marginal (0,00429 unidades por °C)."""
    cenarios = ["Conservador\n(1/4 da margem)", "Central\n(1/2 da margem)", "Teto\n(margem inteira)"]
    pct = [2.8, 5.6, 11.3]
    ciclos = [0.13, 0.26, 0.52]
    cores = [VERDE, AZUL, AZUL_CLARO]

    fig, ax = plt.subplots(figsize=(7.0, 2.9))
    barras = ax.bar(cenarios, pct, color=cores, width=0.5, zorder=3)
    for b, p, c in zip(barras, pct, ciclos):
        ax.text(b.get_x() + b.get_width() / 2, p + 0.28,
                num(p) + "%", ha="center", fontsize=10,
                fontweight="bold", color=TINTA)
        ax.text(b.get_x() + b.get_width() / 2, p / 2,
                num(c, 2) + " ciclo\nevitado/corrida", ha="center", va="center",
                fontsize=8.3, color="white")

    ax.set_ylabel("% da energia de arco poupada")
    ax.set_ylim(0, 13.5)
    ax.grid(axis="y", color=GRADE, zorder=0)
    ax.set_title("Redução do desperdício por cenário de captura da margem de segurança",
                 fontsize=10, pad=10, loc="left")
    return _png(fig)


# Onde cada gráfico entra: (âncora no HTML gerado, imagem, legenda)
# Cada entrada: âncora, gerador, legenda e texto alternativo. O alt descreve os
# números do gráfico; a legenda diz o que eles querem dizer. O alt vinha vazio,
# e quem usa leitor de tela recebia só a legenda.
GRAFICOS = [
    ("<h2>Seleção do modelo final</h2>", grafico_modelos,
     "O erro cai de 10,42 °C sem modelo para 5,22 °C com o LightGBM calibrado, abaixo da meta de 6,8 °C.",
     "Gráfico de barras do erro médio por modelo: 10,42 °C sem modelo, 6,72 no Ridge, 5,63 na Random "
     "Forest, 5,42 no CatBoost e 5,22 no LightGBM calibrado, com a meta de 6,8 °C marcada."),
    ("<h2>Onde o modelo erra", grafico_faixas,
     "Sete em cada dez corridas ficam dentro da tolerância; a cauda acima de 10 °C responde por 12,9%.",
     "Barra empilhada com a distribuição do erro: 38,5% até 3 °C, 33,6% de 3 a 6,8 °C, 15,0% de 6,8 a "
     "10 °C, 10,9% de 10 a 20 °C e 2,0% acima de 20 °C."),
    ("<h2>Estimativa de impacto no negócio</h2>", grafico_cauda,
     "A temperatura de entrada quase não distingue as corridas ruins; o volume de tratamento sim, e ele é decidido antes da corrida.",
     "Gráfico de barras comparando as corridas com erro acima de 10 °C com as demais: energia total 38,7% "
     "maior, duração do arco 27,5%, potência ativa 24,3% e temperatura inicial apenas 0,6%."),
    ("<h2>O que o modelo não sabe</h2>", grafico_impacto,
     "Cenários de economia conforme quanto da margem de segurança a operação consiga liberar.",
     "Três cenários de economia: conservador com 2,8% e 0,13 ciclo evitado por corrida, central com 5,6% "
     "e 0,26, e teto com 11,3% e 0,52."),
]

# O CSS tem dois destinos e eles pedem coisas opostas. Na tela, o que cansa é
# linha longa: a pesquisa de tipografia converge em 50-75 caracteres por linha,
# e a largura antiga (190mm, herdada do A4) entregava perto de 100. Então a base
# é escrita para leitura em tela — coluna estreita, corpo maior, alinhamento à
# esquerda — e o @media print no fim devolve tudo ao formato de papel.
CSS = """
@page { size: A4; margin: 17mm 16mm 16mm 16mm; }

:root {
  color-scheme: light dark;
  --tinta:#1c2833; --azul:#2c5f8a; --borda:#dfe5ea; --suave:#f5f8fa;
  --fundo:#fffdfb; --fraca:#5b6b78; --realce:#fff8e6;
  /* ~66 caracteres por linha no corpo; figuras e tabelas usam a coluna larga */
  --medida: 35rem;
  --larga: 54rem;
  --serif: "Charter","Georgia","DejaVu Serif",serif;
  --sans: "Segoe UI","Helvetica Neue",Arial,sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --tinta:#dfe4e8; --azul:#84b4dc; --borda:#28303a; --suave:#161c23;
    --fundo:#0e1319; --fraca:#93a2ae; --realce:#1d2430;
  }
}
:root[data-theme="dark"] {
  --tinta:#dfe4e8; --azul:#84b4dc; --borda:#28303a; --suave:#161c23;
  --fundo:#0e1319; --fraca:#93a2ae; --realce:#1d2430;
}
:root[data-theme="light"] {
  --tinta:#1c2833; --azul:#2c5f8a; --borda:#dfe5ea; --suave:#f5f8fa;
  --fundo:#fffdfb; --fraca:#5b6b78; --realce:#fff8e6;
}

* { box-sizing: border-box; }

body {
  background: var(--fundo); color: var(--tinta);
  font-family: var(--serif);
  font-size: clamp(1.04rem, 0.99rem + 0.28vw, 1.17rem);
  line-height: 1.72;
  margin: 0; padding: 0 0 6rem;
  -webkit-font-smoothing: antialiased;
  /* Coluna central estreita para o texto; as laterais recebem figuras e tabelas. */
  display: grid;
  grid-template-columns: 1fr min(var(--medida), 100% - 2.6rem) 1fr;
}
body > * { grid-column: 2; }

/* ---------- barra fixa: progresso, modo de leitura, tema ---------- */
.barra {
  grid-column: 1 / -1; position: sticky; top: 0; z-index: 20;
  display: flex; align-items: center; gap: .75rem;
  padding: .55rem max(1.3rem, calc((100% - var(--larga)) / 2));
  background: color-mix(in srgb, var(--fundo) 88%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--borda);
  font-family: var(--sans); font-size: .8rem;
}
.progresso {
  position: absolute; left: 0; bottom: -1px; height: 2px;
  background: var(--azul); width: 0;
}
.barra .quem { color: var(--fraca); margin-right: auto;
               overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.modos { display: inline-flex; border: 1px solid var(--borda); border-radius: 999px; overflow: hidden; }
.modos button {
  font: inherit; padding: .3rem .8rem; border: 0; cursor: pointer;
  background: transparent; color: var(--fraca);
}
.modos button[aria-pressed="true"] { background: var(--azul); color: #fff; }
.tema {
  font: inherit; cursor: pointer; background: transparent; color: var(--fraca);
  border: 1px solid var(--borda); border-radius: 999px;
  width: 2rem; height: 2rem; flex: none;
  display: grid; place-items: center;
}
/* Sem JavaScript os controles não funcionariam; então não aparecem, e o
   documento fica sendo o relatório completo — que é o comportamento correto. */
.sem-js .barra { display: none; }
/* Sem JS o corpo já vem em .modo-resumo, mas não há botão para sair dele.
   Então sem script o leitor recebe o relatório inteiro, que é o documento. */
.sem-js .exec { display: none; }
.sem-js .capa, .sem-js .sumario, .sem-js .bloco, .sem-js .parte { display: block; }
.modos button:focus-visible, .tema:focus-visible,
a:focus-visible { outline: 2px solid var(--azul); outline-offset: 2px; }

/* ---------- capa ---------- */
.capa { padding: 3.2rem 0 1.4rem; border-bottom: 2.5px solid var(--azul); margin-bottom: 1.6rem; }
.capa h1 {
  font-family: var(--sans); font-size: clamp(1.7rem, 1.2rem + 2vw, 2.5rem);
  line-height: 1.15; letter-spacing: -.02em; margin: 0 0 .5rem; color: var(--tinta);
}
.capa .sub { font-family: var(--sans); font-size: 1.05rem; font-weight: 500;
             color: var(--fraca); margin: 0 0 1.1rem; text-align: left; }
.meta { font-family: var(--sans); font-size: .88rem; color: var(--fraca); text-align: left; }
.meta a { color: var(--azul); }

/* ---------- sumário ---------- */
.sumario {
  font-family: var(--sans); font-size: .92rem;
  background: var(--suave); border: 1px solid var(--borda); border-radius: 10px;
  padding: 1.1rem 1.3rem; margin: 0 0 2.4rem;
}
.sumario h2 {
  font-size: .78rem; text-transform: uppercase; letter-spacing: .09em;
  color: var(--fraca); margin: 0 0 .7rem; border: 0; padding: 0;
}
.sumario ol { list-style: none; margin: 0; padding: 0; }
.sumario > ol > li { margin-bottom: .55rem; }
.sumario > ol > li > a { font-weight: 600; }
.sumario ol ol { margin: .3rem 0 0 .9rem; }
.sumario ol ol li { margin-bottom: .2rem; }
.sumario ol ol a { color: var(--fraca); font-size: .88rem; }
.sumario a { color: var(--tinta); text-decoration: none; }
.sumario a:hover { color: var(--azul); text-decoration: underline; }

/* ---------- texto ---------- */
h1, h2, h3 { font-family: var(--sans); line-height: 1.25; }
.parte > h1 {
  font-size: clamp(1.35rem, 1.1rem + 1vw, 1.7rem); margin: 3.2rem 0 .3rem;
  letter-spacing: -.015em; color: var(--azul);
}
h2 { font-size: 1.22rem; margin: 2.4rem 0 .7rem; padding-bottom: .3rem;
     border-bottom: 1.6px solid var(--azul); }
h3 { font-size: 1.04rem; margin: 1.7rem 0 .4rem; color: var(--azul); }
p { margin: 0 0 1.05rem; text-align: left; hyphens: none; }
strong { font-weight: 700; }
a { color: var(--azul); }
hr { border: 0; border-top: 1px solid var(--borda); margin: 2.4rem 0; }
ul, ol { margin: 0 0 1.1rem; padding-left: 1.35rem; }
li { margin-bottom: .38rem; }

/* ---------- elementos largos: escapam da coluna de texto ---------- */
figure, table, pre { grid-column: 1 / -1; justify-self: center; }
/* Figura e código preenchem a faixa; a tabela toma a largura do próprio conteúdo,
   e é o margin auto abaixo que a centraliza em relação ao texto. */
figure, pre { width: 100%; }
figure { margin: 1.8rem 0 2rem; max-width: var(--larga); text-align: center; }
figure img { width: 100%; max-width: 100%; border-radius: 6px; }
/* O tema vem do sistema ou do botão, que escreve data-theme na raiz. A media
   query sozinha não enxerga o botão, então as duas condições ficam escritas. */
figure img.escuro { display: none; }
@media (prefers-color-scheme: dark) {
  html:not([data-theme="light"]) figure img.claro { display: none; }
  html:not([data-theme="light"]) figure img.escuro { display: block; }
}
html[data-theme="dark"] figure img.claro { display: none; }
html[data-theme="dark"] figure img.escuro { display: block; }
html[data-theme="light"] figure img.claro { display: block; }
html[data-theme="light"] figure img.escuro { display: none; }
figcaption {
  font-family: var(--sans); font-size: .85rem; color: var(--fraca);
  margin-top: .6rem; text-align: left; border-left: 2.5px solid var(--azul);
  padding-left: .6rem; line-height: 1.5;
  max-width: var(--medida); margin-left: auto; margin-right: auto;
}
table {
  border-collapse: collapse; margin: 1.4rem auto 1.8rem; max-width: var(--larga);
  width: auto; font-family: var(--sans); font-size: .88rem;
}
th { background: var(--azul); color: #fff; text-align: left; padding: .5rem .65rem; font-weight: 600; }
td { padding: .45rem .65rem; border-bottom: 1px solid var(--borda); vertical-align: top; }
tbody tr:nth-child(even) { background: var(--suave); }
th:not(:first-child), td:not(:first-child) { text-align: right; }
th:first-child, td:first-child { text-align: left; }
code, pre { font-family: "Cascadia Mono","Consolas",ui-monospace,monospace; }
code { background: var(--suave); padding: 1px 4px; border-radius: 3px; font-size: .88em; }
pre { background: var(--suave); border-left: 3px solid var(--azul); padding: .8rem 1rem;
      overflow-x: auto; max-width: var(--larga); font-size: .84rem; margin: 1.2rem auto; }
pre code { background: none; padding: 0; }

/* ---------- modo de leitura ----------
   Três profundidades. "Uma página" não é um filtro sobre as seções do
   relatório: nenhuma delas é curta o bastante (a menor tem 406 palavras).
   É um resumo escrito para o cargo, e some inteiro nos outros dois modos. */
.bloco[data-tec="1"], .parte[data-tec="1"] { display: block; }
body.modo-rapida .bloco[data-tec="1"], body.modo-rapida .parte[data-tec="1"] { display: none; }
body.modo-rapida .sumario [data-tec="1"] { display: none; }
.aviso-modo {
  display: none; font-family: var(--sans); font-size: .9rem;
  background: var(--realce); border: 1px solid var(--borda); border-left: 3px solid var(--azul);
  border-radius: 6px; padding: .8rem 1rem; margin: 1.6rem 0; color: var(--fraca);
}
body.modo-rapida .aviso-modo { display: block; }

/* ---------- resumo executivo: o modo de uma página ---------- */
.exec { display: none; grid-column: 1 / -1; }
body.modo-resumo .exec { display: block; }
body.modo-resumo .capa,
body.modo-resumo .sumario,
body.modo-resumo .bloco,
body.modo-resumo .parte,
body.modo-resumo .aviso-modo { display: none; }

/* O resumo controla a própria largura, sem depender da grade do relatório. */
.exec-dentro { max-width: 54rem; margin: 0 auto; padding: 2.4rem 1.3rem 0; }
.exec h1 { font-size: clamp(1.9rem, 1.3rem + 2.4vw, 2.8rem); margin: 0 0 .2rem;
           letter-spacing: -.02em; line-height: 1.1; }
.exec .linha-fina { font-family: var(--sans); font-size: clamp(1.02rem, .95rem + .4vw, 1.2rem);
                    color: var(--fraca); margin: 0 0 2rem; }
.exec h2 { font-size: 1.1rem; margin: 2.6rem 0 .6rem; border: 0; padding: 0;
           font-family: var(--sans); letter-spacing: .01em; }
.exec p { margin: 0 0 1rem; }
.exec figure { margin: 1.4rem 0 1.8rem; max-width: 100%; }

.numeros {
  display: grid; gap: .7rem; margin: 0 0 1rem;
  grid-template-columns: repeat(auto-fit, minmax(8.5rem, 1fr));
}
.numero { background: var(--suave); border: 1px solid var(--borda);
          border-radius: 8px; padding: .85rem 1rem; }
.numero b { display: block; font-family: var(--sans); font-size: 1.45rem;
            font-variant-numeric: tabular-nums; letter-spacing: -.02em;
            line-height: 1.15; color: var(--tinta); }
.numero span { display: block; font-family: var(--sans); font-size: .78rem;
               color: var(--fraca); margin-top: .2rem; line-height: 1.4; }

/* A ressalva que o relatório faz sobre a conversão financeira, dita cedo. */
.limite {
  background: var(--realce); border: 1px solid var(--borda);
  border-left: 3px solid var(--azul); border-radius: 6px;
  padding: 1rem 1.2rem; margin: 2rem 0; font-family: var(--sans); font-size: .92rem;
  color: var(--fraca);
}
.limite b { display: block; margin-bottom: .35rem; color: var(--tinta); }

.exec .fundo { margin: 2.4rem 0 1rem; }
.ir-fundo {
  font-family: var(--sans); font-size: .92rem; background: none; color: var(--azul);
  border: 1px solid var(--azul); border-radius: 6px; padding: .55rem 1.15rem; cursor: pointer;
}
.ir-fundo:hover { background: var(--realce); }
.aviso-modo button {
  font: inherit; color: var(--azul); background: none; border: 0;
  padding: 0; cursor: pointer; text-decoration: underline;
}

/* ---------- impressão: volta a ser um documento A4 ---------- */
@media print {
  :root { --tinta:#1c2833; --azul:#2c5f8a; --borda:#dfe5ea; --suave:#f5f8fa;
          --fundo:#fff; --fraca:#5b6b78; }
  body {
    display: block; max-width: 190mm; margin: 0 auto; padding: 0;
    font-size: 10.2pt; line-height: 1.62; background: #fff;
  }
  p { text-align: justify; hyphens: auto; margin: 0 0 9pt; }
  .barra, .sumario, .aviso-modo, .exec { display: none !important; }
  /* No papel nada é escondido: o PDF é sempre o relatório completo, esteja a
     tela no modo que estiver. Sem a segunda regra, imprimir a partir do modo
     de uma página rende quatro páginas quase vazias e nenhum gráfico. */
  .bloco[data-tec="1"], .parte[data-tec="1"] { display: block !important; }
  body.modo-resumo .capa,
  body.modo-resumo .bloco,
  body.modo-resumo .parte { display: block !important; }
  .capa { padding: 0 0 12pt; margin-bottom: 6pt; }
  .capa h1 { font-size: 20pt; }
  .capa .sub { font-size: 12.5pt; margin-bottom: 14pt; }
  .parte > h1 { font-size: 17pt; margin: 0 0 4pt; letter-spacing: -0.2pt;
                page-break-before: always; page-break-after: avoid; }
  h2 { font-size: 14pt; margin: 26pt 0 9pt; padding-bottom: 4pt; page-break-after: avoid; }
  h3 { font-size: 11.4pt; margin: 17pt 0 6pt; page-break-after: avoid; }
  figure, pre { display: block; max-width: 100%; page-break-inside: avoid; }
  /* No papel a tabela segue sendo tabela: display:block a esticaria à margem toda
     e o margin auto perderia o efeito. */
  table { display: table; width: auto; max-width: 100%; page-break-inside: avoid; }
  figure { margin: 14pt 0 18pt; }
  figure img { max-width: 165mm; border-radius: 0; }
  figure img.claro { display: block !important; }
  figure img.escuro { display: none !important; }
  figcaption { font-size: 8.6pt; margin-top: 5pt; padding-left: 7pt; line-height: 1.45; }
  table { font-size: 9.1pt; margin: 11pt auto 14pt; }
  th { padding: 5.5pt 7pt; } td { padding: 5pt 7pt; }
  pre { font-size: 9pt; padding: 9pt 11pt; }
  a { color: inherit; text-decoration: none; }
}
"""

# O que o modo "leitura rápida" esconde. São as seções de método: quem quer
# saber se o resultado é confiável lê; quem quer saber o que o projeto entrega
# não precisa passar por elas para chegar às conclusões.
#
# Só entram títulos de nível 2 — a segmentação trabalha em h1 e h2, então um h3
# listado aqui seria ignorado em silêncio. "Estimativa de impacto no negócio"
# fica de fora de propósito: é a seção que mais interessa a quem lê rápido.
def resumo_executivo():
    """O modo de uma página, escrito para quem tem trinta segundos.

    Não sai do Markdown de propósito: nenhuma seção do relatório é curta o
    bastante para servir de resumo (a menor tem 406 palavras), e o que este
    leitor precisa é dos números e da ressalva, nessa ordem. Todos os valores
    daqui aparecem no relatório; nada é calculado neste arquivo.
    """
    return (
        '<section class="exec" aria-label="Resumo em uma página"><div class="exec-dentro">'
        "<h1>Steelproof</h1>"
        '<p class="linha-fina">Prever a temperatura do aço antes de gastar a energia.</p>'
        '<div class="numeros">'
        '<div class="numero"><b>5,22 °C</b><span>erro médio do modelo</span></div>'
        '<div class="numero"><b>6,8 °C</b><span>a meta do plano</span></div>'
        '<div class="numero"><b>12,9%</b><span>das corridas erram mais de 10 °C</span></div>'
        '<div class="numero"><b>2,8 a 5,6%</b><span>da energia de arco por corrida</span></div>'
        "</div>"
        "<h2>O problema</h2>"
        "<p>No forno-panela a temperatura final sai por tentativa: aquece, mede, ainda está "
        "frio, aquece de novo. Cada corrida leva em média 4,6 ciclos de aquecimento e 4,0 "
        "medições de temperatura, e a planta faz cerca de 9.850 corridas e 40 mil medições "
        "por ano. Cada medição gasta um sensor descartável e interrompe o processo.</p>"
        "<h2>O resultado</h2>"
        "<p>O modelo prevê a temperatura final com erro médio de 5,22 °C em 488 corridas "
        "posteriores no tempo, que ele nunca viu. Chutando sempre a média histórica o erro "
        "é 10,42 °C, e a meta fixada no plano de trabalho era 6,8 °C.</p>"
        "<h2>Onde o modelo não deve ser usado</h2>"
        + figura(
            grafico_cauda,
            "As corridas ruins se distinguem pelo tratamento, não pela entrada.",
            "Gráfico de barras comparando as corridas com erro acima de 10 °C com as demais: "
            "energia total 38,7% maior, duração do arco 27,5%, potência ativa 24,3% e "
            "temperatura inicial apenas 0,6%.",
        ) +
        "<p>Uma corrida em cada oito erra mais de 10 °C, e nessas a previsão não substitui a "
        "medição. O que separa essas corridas não é a temperatura de entrada e sim o volume "
        "de tratamento, que é decidido antes de a corrida começar. Dá para saber de antemão "
        "em qual corrida não confiar, e isso é mais útil que o erro médio.</p>"
        "<h2>O que isso vale</h2>"
        "<p>Encolher a margem de segurança térmica poupa entre 2,8% e 5,6% da energia de arco "
        "por corrida, o equivalente a deixar de aplicar de 0,13 a 0,26 ciclo de aquecimento, "
        "de um total médio de 4,6.</p>"
        '<div class="limite"><b>O relatório não converte isso em reais.</b> '
        "A unidade de <code>Active power</code> não está documentada nos dados, e a massa "
        "implicada não fecha com a capacidade informada. O que está entregue é a fórmula com "
        "o parâmetro em aberto e a pergunta a fazer para a planta.</div>"
        '<p class="fundo"><button type="button" class="ir-fundo">Ler o relatório</button></p>'
        "</div></section>"
    )


TECNICAS = {
    "Dados e qualidade iniciais",
    "Proteção contra vazamento de informação",
    "Divisão entre treino e teste",
    "Colinearidade",
    "Modelos avaliados",
    "Hiperparâmetros",
    "Desempenho comparado",
}

JS = """
(function () {
  var raiz = document.documentElement, corpo = document.body;
  raiz.classList.remove('sem-js');

  // --- modo de leitura: ?leitura=resumo|rapida|completa abre direto naquele ---
  // Quem chega sem escolher cai no resumo de uma página: é o modo que responde
  // "o que é isto" em trinta segundos. Os outros dois ficam a um clique.
  var MODOS = ['resumo', 'rapida', 'completa'];
  var botoes = {};
  MODOS.forEach(function (m) { botoes[m] = document.getElementById('m-' + m); });

  function aplicar(modo, guardar) {
    if (MODOS.indexOf(modo) < 0) { modo = 'resumo'; }
    MODOS.forEach(function (m) {
      corpo.classList.toggle('modo-' + m, m === modo);
      if (botoes[m]) { botoes[m].setAttribute('aria-pressed', String(m === modo)); }
    });
    if (guardar) { try { localStorage.setItem('leitura', modo); } catch (e) {} }
  }

  var params = new URLSearchParams(location.search);
  var inicial = params.get('leitura');
  if (MODOS.indexOf(inicial) < 0) {
    try { inicial = localStorage.getItem('leitura'); } catch (e) { inicial = null; }
  }
  aplicar(inicial, false);

  MODOS.forEach(function (m) {
    if (botoes[m]) { botoes[m].addEventListener('click', function () { aplicar(m, true); }); }
  });
  Array.prototype.forEach.call(document.querySelectorAll('.ver-tudo'), function (b) {
    b.addEventListener('click', function () { aplicar('completa', true); window.scrollTo(0, 0); });
  });
  Array.prototype.forEach.call(document.querySelectorAll('.ir-fundo'), function (b) {
    b.addEventListener('click', function () { aplicar('rapida', true); window.scrollTo(0, 0); });
  });

  // --- tema: segue o sistema até o leitor escolher ---
  // Ícones em SVG, não em glifo: ☾ e ☀ faltam em muitas fontes de sistema e
  // aparecem como caixa vazia — foi o que aconteceu no primeiro teste.
  var btnTema = document.getElementById('tema');
  var SOL = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"'
    + ' stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/>'
    + '<path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5.2 5.2l1.4 1.4M17.4 17.4l1.4 1.4'
    + 'M5.2 18.8l1.4-1.4M17.4 6.6l1.4-1.4"/></svg>';
  var LUA = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"'
    + ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    + '<path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.7 6.7 0 0 0 10.5 10.5z"/></svg>';

  function pintar(t) {
    if (t) { raiz.setAttribute('data-theme', t); } else { raiz.removeAttribute('data-theme'); }
    var escuro = t ? t === 'dark'
      : window.matchMedia('(prefers-color-scheme: dark)').matches;
    btnTema.innerHTML = escuro ? SOL : LUA;
    btnTema.setAttribute('aria-label', escuro ? 'Usar tema claro' : 'Usar tema escuro');
  }
  var salvo = null;
  try { salvo = localStorage.getItem('tema'); } catch (e) {}
  pintar(salvo);
  btnTema.addEventListener('click', function () {
    var atual = raiz.getAttribute('data-theme');
    var escuro = atual ? atual === 'dark'
      : window.matchMedia('(prefers-color-scheme: dark)').matches;
    var novo = escuro ? 'light' : 'dark';
    pintar(novo);
    try { localStorage.setItem('tema', novo); } catch (e) {}
  });

  // --- progresso e seção corrente ---
  var barra = document.querySelector('.progresso');
  var quem = document.querySelector('.quem');
  var titulos = [].slice.call(document.querySelectorAll('.parte > h1, .bloco > h2'));

  function aoRolar() {
    var alcance = document.documentElement.scrollHeight - window.innerHeight;
    barra.style.width = (alcance > 0 ? (window.scrollY / alcance) * 100 : 0) + '%';
    var atual = '';
    for (var i = 0; i < titulos.length; i++) {
      var el = titulos[i];
      if (el.offsetParent === null) continue;      // oculto no modo rápido
      if (el.getBoundingClientRect().top > 90) break;
      atual = el.textContent;
    }
    quem.textContent = atual;
  }
  var agendado = false;
  window.addEventListener('scroll', function () {
    if (agendado) return;
    agendado = true;
    requestAnimationFrame(function () { aoRolar(); agendado = false; });
  }, { passive: true });
  window.addEventListener('resize', aoRolar, { passive: true });
  aoRolar();
})();
"""


def _texto(html_fragmento):
    """Título sem as marcações que o markdown deixou dentro dele."""
    return re.sub(r"<[^>]+>", "", html_fragmento).strip()


def _ancora(titulo):
    base = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-") or "secao"


def segmentar(corpo):
    """Quebra o HTML plano em partes (h1) e blocos (h2), marcando os técnicos.

    O markdown devolve uma sequência sem hierarquia. Para esconder as seções de
    método no modo rápido — e para montar o sumário — cada trecho precisa virar
    um elemento próprio com identidade.
    """
    partes, soltos, atual = [], [], None
    for pedaco in re.split(r"(?=<h[12]>)", corpo):
        if not pedaco.strip():
            continue
        cab1 = re.match(r"<h1>(.*?)</h1>", pedaco, re.S)
        cab2 = re.match(r"<h2>(.*?)</h2>", pedaco, re.S)
        if cab1:
            titulo = _texto(cab1.group(1))
            atual = {"titulo": titulo, "id": _ancora(titulo), "abertura": pedaco, "blocos": []}
            partes.append(atual)
        elif cab2:
            titulo = _texto(cab2.group(1))
            bloco = {"titulo": titulo, "id": _ancora(titulo),
                     "tec": titulo in TECNICAS, "html": pedaco}
            (atual["blocos"] if atual else soltos).append(bloco)
        elif atual:
            atual["abertura"] += pedaco
        else:
            soltos.append({"titulo": "", "id": "", "tec": False, "html": pedaco})

    # Uma parte cujos blocos são todos de método some inteira no modo rápido —
    # senão sobraria o título de uma seção sem nenhum conteúdo embaixo.
    for parte in partes:
        com_titulo = [b for b in parte["blocos"] if b["titulo"]]
        parte["tec"] = bool(com_titulo) and all(b["tec"] for b in com_titulo)
    return soltos, partes


def montar_sumario(soltos, partes):
    linhas = ['<nav class="sumario" aria-label="Sumário"><h2>Neste relatório</h2><ol>']
    for bloco in soltos:
        if bloco["titulo"]:
            linhas.append(f'<li data-tec="{int(bloco["tec"])}">'
                          f'<a href="#{bloco["id"]}">{bloco["titulo"]}</a></li>')
    for parte in partes:
        linhas.append(f'<li data-tec="{int(parte["tec"])}">'
                      f'<a href="#{parte["id"]}">{parte["titulo"]}</a>')
        filhos = [b for b in parte["blocos"] if b["titulo"]]
        if filhos:
            linhas.append("<ol>")
            for bloco in filhos:
                linhas.append(f'<li data-tec="{int(bloco["tec"])}">'
                              f'<a href="#{bloco["id"]}">{bloco["titulo"]}</a></li>')
            linhas.append("</ol>")
        linhas.append("</li>")
    linhas.append("</ol></nav>")
    return "".join(linhas)


def _bloco_html(bloco):
    if not bloco["titulo"]:
        return bloco["html"]
    return (f'<section class="bloco" id="{bloco["id"]}" data-tec="{int(bloco["tec"])}">'
            f'{bloco["html"]}</section>')


def main():
    md_texto = (AQUI / "Relatorio-Etapa3.md").read_text(encoding="utf-8")
    corpo = markdown.markdown(md_texto, extensions=["tables", "fenced_code", "sane_lists"])

    # Insere cada gráfico logo DEPOIS do título da seção correspondente.
    #
    # Antes ele era inserido antes do título, o que o deixava no fim da seção
    # anterior. Isso quebrava a leitura rápida: o gráfico da comparação de
    # modelos caía dentro de "Desempenho comparado", que é uma seção de método
    # e fica oculta — sumindo justamente o gráfico com o número central do
    # trabalho, para o leitor que menos vai atrás dele.
    for ancora, gerador, legenda, alt in GRAFICOS:
        pos = corpo.find(ancora)
        if pos == -1:
            print(f"  aviso: ancora nao encontrada -> {ancora[:40]}")
            continue
        fim = corpo.find("</h2>", pos)
        if fim == -1:
            print(f"  aviso: titulo sem fechamento -> {ancora[:40]}")
            continue
        fim += len("</h2>")
        corpo = corpo[:fim] + "\n" + figura(gerador, legenda, alt) + "\n" + corpo[fim:]

    # A capa é tudo até a primeira régua: título, subtítulo e a linha de autoria.
    capa_bruta, _, resto = corpo.partition("<hr />")
    titulo = _texto(re.search(r"<h1>(.*?)</h1>", capa_bruta, re.S).group(1))
    subtitulo = _texto(re.search(r"<h2>(.*?)</h2>", capa_bruta, re.S).group(1))
    autoria = _texto(re.search(r"<p>(.*?)</p>", capa_bruta, re.S).group(1))
    capa = (
        '<header class="capa">'
        f"<h1>{titulo}</h1>"
        f'<p class="sub">{subtitulo}</p>'
        f'<p class="meta">{autoria}<br>'
        'Código, notebooks e o Markdown que gera este documento: '
        '<a href="https://github.com/FSzekut/steelproof">github.com/FSzekut/steelproof</a>'
        "</p></header>"
    )

    soltos, partes = segmentar(resto)
    conteudo = "".join(_bloco_html(b) for b in soltos)
    for parte in partes:
        conteudo += (f'<section class="parte" id="{parte["id"]}" data-tec="{int(parte["tec"])}">'
                     f'{parte["abertura"]}'
                     f'{"".join(_bloco_html(b) for b in parte["blocos"])}'
                     "</section>")

    # Conta seções, não elementos: uma parte oculta leva os blocos dela junto,
    # e é o número de seções que o leitor deixa de ver que interessa no aviso.
    escondidas = sum(1 for b in soltos if b["tec"]) + sum(
        1 for p in partes for b in p["blocos"] if b["tec"]
    )
    aviso = (
        '<p class="aviso-modo">Você está na <strong>leitura rápida</strong>: '
        f"{escondidas} seções de método estão ocultas, entre elas como os dados foram "
        "tratados e como os hiperparâmetros foram escolhidos. Os números e as conclusões "
        "são os mesmos. "
        '<button type="button" class="ver-tudo">Ver o relatório completo</button></p>'
    )
    barra = (
        '<div class="barra">'
        '<span class="progresso"></span>'
        '<span class="quem"></span>'
        '<span class="modos" role="group" aria-label="Modo de leitura">'
        '<button type="button" id="m-resumo" aria-pressed="true">Uma página</button>'
        '<button type="button" id="m-rapida" aria-pressed="false">Leitura rápida</button>'
        '<button type="button" id="m-completa" aria-pressed="false">Completo</button>'
        "</span>"
        '<button type="button" class="tema" id="tema" aria-label="Alternar tema"></button>'
        "</div>"
    )

    html = (
        '<!doctype html><html lang="pt-BR" class="sem-js"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Relatório de solução: Steelproof</title>"
        '<meta name="description" content="Previsão da temperatura final do banho no '
        'forno-panela: erro médio de 5,22 °C, contra 10,42 °C sem modelo.">'
        f'<style>{CSS}</style></head><body class="modo-resumo">'
        f"{barra}{resumo_executivo()}{capa}{montar_sumario(soltos, partes)}{aviso}{conteudo}"
        f"<script>{JS}</script></body></html>"
    )
    saida = AQUI / "Relatorio-Etapa3.html"
    saida.write_text(html, encoding="utf-8")
    print(f"gerado: {saida}  ({len(html)/1024:.0f} KB)")
    print(f"  {len(partes)} partes, {sum(len(p['blocos']) for p in partes) + len(soltos)} blocos, "
          f"{escondidas} ocultos na leitura rápida")


if __name__ == "__main__":
    main()
