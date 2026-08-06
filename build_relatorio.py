"""Gera o HTML do Relatório da Etapa 3 a partir do Markdown, com gráficos embutidos.

Uso:  python build_relatorio.py
Saída: Relatorio-Etapa3.html  (autocontido; abrir no navegador e imprimir como PDF)

Os números plotados são os medidos no Notebook-Etapa2.ipynb, transcritos aqui para que
o relatório não dependa de reexecutar o treinamento.
"""

import base64
import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import markdown

AQUI = Path(__file__).parent
TINTA = "#1c2833"
AZUL = "#2c5f8a"
AZUL_CLARO = "#7fa8c7"
VERDE = "#3d7a5a"
CINZA = "#9aa5ad"
VERMELHO = "#b04a3a"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9.5,
    "axes.edgecolor": "#cfd6db",
    "axes.labelcolor": TINTA,
    "text.color": TINTA,
    "xtick.color": TINTA,
    "ytick.color": TINTA,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 160,
})


def _png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


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
        ax.text(b.get_x() + b.get_width() / 2, v + 0.22, f"{v:.2f}".replace(".", ","),
                ha="center", fontsize=8.8, color=TINTA)

    ax.set_ylabel("MAE no teste (°C)")
    ax.set_ylim(0, 12.2)
    ax.grid(axis="y", color="#eef1f3", zorder=0)
    ax.set_title("Erro médio absoluto por modelo, em 488 corridas posteriores no tempo",
                 fontsize=10, pad=10, loc="left")
    return _png(fig)


def grafico_faixas():
    """Distribuição do erro em faixas operacionais."""
    faixas = ["até 3 °C", "3 a 6,8 °C", "6,8 a 10 °C", "10 a 20 °C", "acima de 20 °C"]
    pct = [38.5, 33.6, 15.0, 10.9, 2.0]
    cores = [VERDE, VERDE, "#d9a441", VERMELHO, VERMELHO]

    fig, ax = plt.subplots(figsize=(7.0, 2.6))
    esq = 0
    for p, c, f in zip(pct, cores, faixas):
        ax.barh([0], [p], left=esq, color=c, height=0.5, zorder=3)
        if p > 4:
            ax.text(esq + p / 2, 0, f"{p:.1f}%".replace(".", ","), ha="center", va="center",
                    color="white", fontsize=9, fontweight="bold")
        esq += p

    ax.axvline(72.1, color=TINTA, lw=1.3, ls="--", zorder=5)
    ax.text(72.1, 0.42, "72,1% dentro da tolerância de ±6,8 °C", fontsize=8.5, ha="center", color=TINTA)

    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in
               [VERDE, "#d9a441", VERMELHO]]
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
        ax.text(v + 0.9, b.get_y() + b.get_height() / 2, f"+{v:.1f}%".replace(".", ","),
                va="center", fontsize=9, color=TINTA)

    ax.set_xlim(0, 46)
    ax.set_xlabel("diferença das corridas com erro > 10 °C em relação às demais")
    ax.grid(axis="x", color="#eef1f3", zorder=0)
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
                f"{p:.1f}%".replace(".", ","), ha="center", fontsize=10,
                fontweight="bold", color=TINTA)
        ax.text(b.get_x() + b.get_width() / 2, p / 2,
                f"{c:.2f} ciclo\nevitado/corrida".replace(".", ","), ha="center", va="center",
                fontsize=8.3, color="white")

    ax.set_ylabel("% da energia de arco poupada")
    ax.set_ylim(0, 13.5)
    ax.grid(axis="y", color="#eef1f3", zorder=0)
    ax.set_title("Redução do desperdício por cenário de captura da margem de segurança",
                 fontsize=10, pad=10, loc="left")
    return _png(fig)


# Onde cada gráfico entra: (âncora no HTML gerado, imagem, legenda)
GRAFICOS = [
    ("<h2>Seleção do modelo final</h2>", grafico_modelos,
     "O erro cai de 10,42 °C sem modelo para 5,22 °C com o LightGBM calibrado, abaixo da meta de 6,8 °C."),
    ("<h2>Onde o modelo erra", grafico_faixas,
     "Sete em cada dez corridas ficam dentro da tolerância; a cauda acima de 10 °C responde por 12,9%."),
    ("<h2>Estimativa de impacto no negócio</h2>", grafico_cauda,
     "A temperatura de entrada quase não distingue as corridas ruins; o volume de tratamento sim, e ele é decidido antes da corrida."),
    ("<h2>O que o modelo não sabe</h2>", grafico_impacto,
     "Cenários de economia conforme quanto da margem de segurança a operação consiga liberar."),
]

CSS = """
@page { size: A4; margin: 17mm 16mm 16mm 16mm; }
:root { --tinta:#1c2833; --azul:#2c5f8a; --borda:#dfe5ea; --suave:#f5f8fa; }
* { box-sizing: border-box; }
body {
  font-family: "Charter","Georgia","DejaVu Serif",serif;
  color: var(--tinta); line-height: 1.62; font-size: 10.6pt;
  max-width: 190mm; margin: 0 auto; padding: 12mm 4mm;
  -webkit-font-smoothing: antialiased;
}
h1, h2, h3 { font-family: "Segoe UI","Helvetica Neue",Arial,sans-serif; line-height: 1.25; }
/* Os h1 de seção (o cenário, o que fiz, o que saiu) abrem página nova; o primeiro é a capa. */
h1 { font-size: 17pt; margin: 0 0 4pt; letter-spacing: -0.2pt;
     color: var(--azul); page-break-before: always; page-break-after: avoid; }
body > h1:first-of-type { font-size: 20pt; color: var(--tinta); page-break-before: auto; }
/* Só o h2 logo após o h1 da capa é subtítulo; os demais mantêm o estilo de seção. */
body > h1:first-of-type + h2 { font-size: 12.5pt; font-weight: 500; color: #5b6b78;
          border: 0; margin: 0 0 14pt; padding: 0; page-break-after: avoid; }
h2 { font-size: 14pt; margin: 26pt 0 9pt; padding-bottom: 4pt;
     border-bottom: 1.6px solid var(--azul); page-break-after: avoid; }
h3 { font-size: 11.4pt; margin: 17pt 0 6pt; color: var(--azul); page-break-after: avoid; }
p { margin: 0 0 9pt; text-align: justify; hyphens: auto; }
strong { font-weight: 700; }
hr { border: 0; border-top: 1px solid var(--borda); margin: 22pt 0; }
table { border-collapse: collapse; width: 100%; margin: 11pt 0 14pt;
        font-family: "Segoe UI",Arial,sans-serif; font-size: 9.1pt; page-break-inside: avoid; }
th { background: var(--azul); color: #fff; text-align: left; padding: 5.5pt 7pt; font-weight: 600; }
td { padding: 5pt 7pt; border-bottom: 1px solid var(--borda); vertical-align: top; }
tbody tr:nth-child(even) { background: var(--suave); }
th:not(:first-child), td:not(:first-child) { text-align: right; }
th:first-child, td:first-child { text-align: left; }
ul, ol { margin: 0 0 10pt; padding-left: 18pt; }
li { margin-bottom: 4pt; }
code, pre { font-family: "Cascadia Mono","Consolas",monospace; font-size: 9pt; }
code { background: var(--suave); padding: 1px 4px; border-radius: 3px; }
pre { background: var(--suave); border-left: 3px solid var(--azul); padding: 9pt 11pt;
      overflow-x: auto; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
figure { margin: 14pt 0 18pt; page-break-inside: avoid; text-align: center; }
figure img { width: 100%; max-width: 165mm; }
figcaption { font-family: "Segoe UI",Arial,sans-serif; font-size: 8.6pt; color: #5b6b78;
             margin-top: 5pt; text-align: left; border-left: 2.5px solid var(--azul);
             padding-left: 7pt; line-height: 1.45; }
.capa { border-bottom: 2.5px solid var(--azul); padding-bottom: 12pt; margin-bottom: 6pt; }
.meta { font-family: "Segoe UI",Arial,sans-serif; font-size: 9.2pt; color: #5b6b78; }
@media print {
  body { padding: 0; font-size: 10.2pt; }
  h2 { page-break-after: avoid; }
  a { color: inherit; text-decoration: none; }
}
"""


def main():
    md_texto = (AQUI / "Relatorio-Etapa3.md").read_text(encoding="utf-8")
    corpo = markdown.markdown(md_texto, extensions=["tables", "fenced_code", "sane_lists"])

    # Insere cada gráfico logo antes da seção correspondente.
    for ancora, gerador, legenda in GRAFICOS:
        pos = corpo.find(ancora)
        if pos == -1:
            print(f"  aviso: ancora nao encontrada -> {ancora[:40]}")
            continue
        fig_html = (f'<figure><img src="data:image/png;base64,{gerador()}" alt="">'
                    f"<figcaption>{legenda}</figcaption></figure>\n")
        corpo = corpo[:pos] + fig_html + corpo[pos:]

    html = (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        "<title>Relatório de solução: Steelproof</title>"
        f"<style>{CSS}</style></head><body>{corpo}</body></html>"
    )
    saida = AQUI / "Relatorio-Etapa3.html"
    saida.write_text(html, encoding="utf-8")
    print(f"gerado: {saida}  ({len(html)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
