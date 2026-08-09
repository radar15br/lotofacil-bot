"""
ETAPA 5 — GERAÇÃO DAS PEÇAS VISUAIS
====================================

COMO FUNCIONA, EM PORTUGUÊS SIMPLES

Em vez de desenhar as imagens pixel a pixel (que é trabalhoso e feio de
ajustar), o robô monta uma página HTML invisível para cada peça e tira uma
"foto" dela com um navegador. É a mesma técnica que sites usam para gerar
imagem de compartilhamento. Vantagem: mudar o visual é mexer em CSS, não em
código de desenho.

O QUE ELE GERA (em 2 estilos visuais diferentes)

  feed.png       1080 x 1080   -> post quadrado do Instagram
  stories.png    1080 x 1920   -> Stories do Instagram e TikTok
  carrossel/     1080 x 1350   -> 7 slides: capa, jogos (2), estatísticas,
                                  desempenho, aviso legal e CTA

CONFORMIDADE JÁ EMBUTIDA

  - Nenhuma peça usa logo, nome ou identidade visual da Caixa/Lotofácil de
    forma que sugira vínculo oficial.
  - Toda peça carrega o aviso de que é análise estatística, não previsão.
  - Toda peça carrega "+18" e o lembrete de jogo responsável.

Como rodar:
    python -m src.pecas                        # próximo concurso, os 2 estilos
    python -m src.pecas --concurso 3757
    python -m src.pecas --estilo noite
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src import analise as an
from src.coleta import RAIZ, carregar_base
from src.desempenho import frases_prova_social, resumo
from src.jogos import carregar_jogos, gerar_jogos

PASTA_SAIDAS = RAIZ / "saidas"

# ---------------------------------------------------------------------------
# ESTILOS VISUAIS
# ---------------------------------------------------------------------------
# Cada estilo é só um conjunto de cores e efeitos. Para criar um terceiro
# estilo, copie um bloco destes e troque os valores.

ESTILOS: dict[str, dict[str, str]] = {
    "noite": {
        "nome": "Noite",
        "fundo": "radial-gradient(120% 90% at 15% 0%, #1B2444 0%, #0B0E1A 60%)",
        "superficie": "rgba(255,255,255,.055)",
        "borda": "rgba(255,255,255,.10)",
        "texto": "#FFFFFF",
        "texto2": "#A9B2C8",
        "texto3": "#6E7891",
        "destaque": "#5EEAD4",
        "destaque2": "#A78BFA",
        "chip_fundo": "rgba(255,255,255,.07)",
        "chip_borda": "rgba(255,255,255,.11)",
        "chip_texto": "#EEF2FF",
        "chip_alto_fundo": "linear-gradient(135deg,#5EEAD4,#38BDF8)",
        "chip_alto_texto": "#06202B",
        "chip_alto_tint": "rgba(94,234,212,.13)",
        "sombra": "0 18px 44px rgba(0,0,0,.45)",
    },
    "dia": {
        "nome": "Dia",
        "fundo": "radial-gradient(110% 85% at 85% 0%, #FFE9D6 0%, #F7F5F0 55%)",
        "superficie": "#FFFFFF",
        "borda": "rgba(16,20,24,.09)",
        "texto": "#101418",
        "texto2": "#5A6270",
        "texto3": "#8A8F9C",
        "destaque": "#2A78D6",
        "destaque2": "#EB6834",
        "chip_fundo": "#FFFFFF",
        "chip_borda": "rgba(16,20,24,.10)",
        "chip_texto": "#101418",
        "chip_alto_fundo": "linear-gradient(135deg,#2A78D6,#4C9BF0)",
        "chip_alto_texto": "#FFFFFF",
        "chip_alto_tint": "rgba(42,120,214,.10)",
        "sombra": "0 14px 34px rgba(16,20,24,.10)",
    },
}

FONTE = '"Carlito","Liberation Sans","Segoe UI","DejaVu Sans",system-ui,sans-serif'

# Identidade do perfil. Troque aqui e muda em todas as peças de uma vez.
PERFIL = "@radar15br"
PERFIL_NOME = "Radar 15"

AVISO_CURTO = "Análise estatística de dados históricos. Não é previsão. +18. Jogue com responsabilidade."
AVISO_LONGO = (
    "Este conteúdo apresenta jogos montados a partir de análise estatística de resultados "
    "históricos da Lotofácil. <b>Não é previsão e não garante resultado.</b> Cada sorteio é "
    "independente dos anteriores e todas as 3.268.760 combinações possíveis de 15 dezenas têm "
    "exatamente a mesma probabilidade. Este perfil não possui vínculo com a Caixa Econômica "
    "Federal. Proibido para menores de 18 anos. Jogue apenas o que puder perder."
)


# ---------------------------------------------------------------------------
# PEÇAS DE HTML REUTILIZÁVEIS
# ---------------------------------------------------------------------------


def _css(e: dict[str, str], largura: int, altura: int) -> str:
    return f"""
* {{ margin:0; padding:0; box-sizing:border-box; }}
html,body {{ width:{largura}px; height:{altura}px; }}
body {{
  font-family:{FONTE};
  background:{e['fundo']};
  color:{e['texto']};
  -webkit-font-smoothing:antialiased;
  display:flex; flex-direction:column;
  overflow:hidden;
}}
.pad {{ padding:64px 60px; display:flex; flex-direction:column; height:100%; }}
.tag {{
  display:inline-flex; align-items:center; gap:10px; align-self:flex-start;
  background:{e['superficie']}; border:1px solid {e['borda']};
  border-radius:999px; padding:12px 22px;
  font-size:26px; font-weight:700; letter-spacing:.06em; text-transform:uppercase;
  color:{e['texto2']};
}}
.ponto {{ width:12px; height:12px; border-radius:50%; background:{e['destaque']}; }}
h1 {{ font-size:88px; line-height:1.02; font-weight:800; letter-spacing:-.03em; }}
h2 {{ font-size:58px; line-height:1.08; font-weight:800; letter-spacing:-.02em; }}
h3 {{ font-size:36px; font-weight:750; letter-spacing:-.01em; }}
.sub {{ font-size:30px; color:{e['texto2']}; line-height:1.35; }}
.mini {{ font-size:23px; color:{e['texto3']}; line-height:1.4; }}
.destaque {{ color:{e['destaque']}; }}
.destaque2 {{ color:{e['destaque2']}; }}
.cartao {{
  background:{e['superficie']}; border:1px solid {e['borda']};
  border-radius:28px; padding:30px 32px; box-shadow:{e['sombra']};
}}
.lista-jogos {{ display:flex; flex-direction:column; flex:1; justify-content:space-between; }}
.linha-jogo {{ display:flex; align-items:center; gap:12px; }}
.cartao-linha {{
  background:{e['superficie']}; border:1px solid {e['borda']};
  border-radius:22px; padding:14px 20px;
}}
.num-jogo {{
  width:38px; font-size:21px; font-weight:700; color:{e['texto3']};
  text-align:right; flex:0 0 38px; font-variant-numeric:tabular-nums;
}}
.dezenas {{ display:flex; }}
.chip {{
  display:flex; align-items:center; justify-content:center;
  background:{e['chip_fundo']}; border:1.5px solid {e['chip_borda']};
  color:{e['chip_texto']}; font-weight:750;
  font-variant-numeric:tabular-nums; flex:0 0 auto;
}}
/* dezena que repetiu do concurso anterior: contorno de destaque, sem virar bloco
   colorido — com 9 repetições em média, preencher tudo polui a peça */
.chip.alto {{
  border-color:{e['destaque']}; color:{e['destaque']};
  background:{e['chip_alto_tint']};
}}
.corpo {{ flex:1; display:flex; flex-direction:column; justify-content:space-between; min-height:0; }}
.rodape {{
  margin-top:auto; padding-top:26px; border-top:1px solid {e['borda']};
  font-size:20px; color:{e['texto3']}; line-height:1.4;
}}
.assina {{
  display:flex; justify-content:space-between; align-items:baseline; gap:20px;
}}
.perfil {{ font-weight:750; color:{e['destaque']}; white-space:nowrap; }}
.kpis {{ display:flex; gap:18px; }}
.kpi {{ flex:1; }}
.kpi .v {{ font-size:56px; font-weight:800; letter-spacing:-.02em; }}
.kpi .r {{ font-size:22px; color:{e['texto2']}; margin-top:4px; line-height:1.25; }}
"""


def _chips(dezenas: list[int], destacar: set[int] | None = None, lado: int = 56,
           gap: int = 6) -> str:
    """Chips de tamanho fixo em pixels — evita que a peça estoure a altura."""
    destacar = destacar or set()
    fonte = round(lado * 0.44)
    raio = round(lado * 0.26)
    return (f'<div class="dezenas" style="gap:{gap}px">' + "".join(
        f'<div class="chip{" alto" if d in destacar else ""}" '
        f'style="width:{lado}px;height:{lado}px;font-size:{fonte}px;border-radius:{raio}px">'
        f'{d:02d}</div>'
        for d in dezenas
    ) + "</div>")


def _linhas_de_jogos(jogos: list[dict], destacar: set[int], lado: int, inicio: int = 1,
                     gap_linha: int = 6, gap_chip: int = 6, cartao: bool = False) -> str:
    classe = "linha-jogo cartao-linha" if cartao else "linha-jogo"
    return (f'<div class="lista-jogos" style="gap:{gap_linha}px">' + "".join(
        f'<div class="{classe}"><div class="num-jogo">{inicio + i:02d}</div>'
        f'{_chips(j["dezenas"], destacar, lado, gap_chip)}</div>'
        for i, j in enumerate(jogos)
    ) + "</div>")


def _pagina(e: dict, largura: int, altura: int, corpo: str) -> str:
    return (f'<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">'
            f"<style>{_css(e, largura, altura)}</style></head><body>{corpo}</body></html>")


def _n(valor: float, casas: int = 2) -> str:
    """Número no padrão brasileiro: 9,03 · 3.756"""
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _data_br(iso: str) -> str:
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return iso


# ---------------------------------------------------------------------------
# CONTEÚDO DAS PEÇAS
# ---------------------------------------------------------------------------


def _contexto(concurso_alvo: int | None = None) -> dict[str, Any]:
    """Reúne tudo que as peças precisam: jogos, estatística e prova social."""
    base = carregar_base()
    if not base:
        raise RuntimeError("Base vazia. Rode a Etapa 1 antes.")

    alvo = concurso_alvo or base[-1]["concurso"] + 1
    jogos = carregar_jogos(alvo) or gerar_jogos(base, concurso_alvo=alvo)

    freq = an.frequencia(base, 100)
    atr = an.atrasos(base)
    perfil = an.perfil_alvo(base)

    quentes = sorted(freq, key=lambda d: -freq[d]["vezes"])[:5]
    atrasadas = sorted(atr, key=lambda d: -atr[d]["atraso_atual"])[:5]

    r = resumo(10, incluir_simulados=True)
    return {
        "concurso": alvo,
        "base": base,
        "ultimo": base[-1],
        "jogos": jogos,
        "quentes": quentes,
        "atrasadas": atrasadas,
        "perfil": perfil,
        "paridade_top": max(
            an.paridade(base)["distribuicao"].items(), key=lambda x: x[1]["vezes"]
        ),
        "desempenho": r,
        "frases": frases_prova_social(10, incluir_simulados=True),
    }


def _cabecalho(ctx: dict, e: dict) -> str:
    return f"""
<div class="tag"><span class="ponto"></span>Concurso {ctx['concurso']}</div>
<h1 style="margin-top:26px">13 jogos<br><span class="destaque">da Lotofácil</span></h1>
<p class="sub" style="margin-top:18px">
  Montados por análise estatística de {_n(len(ctx['base']), 0)} concursos
</p>"""


def _legenda_destaque(ctx: dict) -> str:
    return (f'Contorno colorido = dezena que repetiu do concurso '
            f'{ctx["ultimo"]["concurso"]}')


# ---------- FEED 1080 x 1080 ----------


def html_feed(ctx: dict, e: dict) -> str:
    ultimo = set(ctx["ultimo"]["dezenas"])
    d = ctx["desempenho"]
    corpo = f"""
<div class="pad" style="padding:34px 44px 30px">
  <div style="display:flex; justify-content:space-between; align-items:center">
    <div>
      <div class="tag" style="font-size:23px; padding:9px 18px">
        <span class="ponto"></span>Concurso {ctx['concurso']}
      </div>
      <h2 style="margin-top:14px; font-size:60px">13 jogos <span class="destaque">gerados</span></h2>
    </div>
    <div style="text-align:right">
      <div style="font-size:50px; font-weight:800; letter-spacing:-.02em">{_n(d.get('media_de_acertos', 0))}</div>
      <div class="mini" style="font-size:20px">média de acertos<br>nos últimos {d.get('janela', 10)}</div>
    </div>
  </div>

  <div class="corpo" style="margin-top:22px">
    {_linhas_de_jogos(ctx['jogos']['jogos'], ultimo, 54, gap_linha=7, gap_chip=6)}
  </div>

  <div class="rodape assina" style="font-size:19px; padding-top:16px">
    <span>Contorno = repetiu do concurso {ctx['ultimo']['concurso']} · Não é previsão. +18. Jogue com responsabilidade.</span>
    <span class="perfil">{PERFIL}</span>
  </div>
</div>"""
    return _pagina(e, 1080, 1080, corpo)


# ---------- STORIES 1080 x 1920 ----------


def html_stories(ctx: dict, e: dict) -> str:
    ultimo = set(ctx["ultimo"]["dezenas"])
    d = ctx["desempenho"]
    corpo = f"""
<div class="pad" style="padding:170px 60px 100px">
  {_cabecalho(ctx, e)}

  <div class="corpo" style="margin-top:44px">
    {_linhas_de_jogos(ctx['jogos']['jogos'], ultimo, 55, gap_linha=16, gap_chip=6)}

    <div class="cartao" style="margin-top:40px">
      <div class="kpis">
        <div class="kpi"><div class="v destaque">{_n(d.get('media_de_acertos', 0))}</div>
          <div class="r">acertos por jogo<br>nos últimos {d.get('janela', 10)}</div></div>
        <div class="kpi"><div class="v">{d.get('melhor_resultado', {}).get('acertos', '-')}</div>
          <div class="r">melhor marca<br>registrada</div></div>
        <div class="kpi"><div class="v">{_n(d.get('pct_concursos_com_premio', 0), 0)}%</div>
          <div class="r">dos concursos<br>com prêmio</div></div>
      </div>
    </div>
  </div>

  <div class="rodape assina">
    <span>{_legenda_destaque(ctx)}<br>{AVISO_CURTO}</span>
    <span class="perfil">{PERFIL}</span>
  </div>
</div>"""
    return _pagina(e, 1080, 1920, corpo)


# ---------- CARROSSEL 1080 x 1350 ----------


def html_carrossel(ctx: dict, e: dict) -> list[tuple[str, str]]:
    ultimo = set(ctx["ultimo"]["dezenas"])
    jogos = ctx["jogos"]["jogos"]
    d = ctx["desempenho"]
    perfil = ctx["perfil"]
    atrasos = an.atrasos(ctx["base"])
    L, A = 1080, 1350

    def pag(corpo: str) -> str:
        return _pagina(e, L, A, corpo)

    # 1. capa
    capa = pag(f"""
<div class="pad">
  <div class="corpo" style="justify-content:center">
    <div>
      <div class="tag"><span class="ponto"></span>{PERFIL} · Concurso {ctx['concurso']}</div>
      <h1 style="margin-top:32px; font-size:106px">13 jogos<br><span class="destaque">da Lotofácil</span></h1>
      <p class="sub" style="margin-top:26px; font-size:34px">
        Montados a partir de {_n(len(ctx['base']), 0)} concursos analisados,<br>de 2003 até hoje.
      </p>
      <div class="cartao" style="margin-top:44px">
        <div class="kpis">
          <div class="kpi"><div class="v destaque">{_n(d.get('media_de_acertos', 0))}</div><div class="r">acertos por jogo</div></div>
          <div class="kpi"><div class="v">{d.get('melhor_resultado', {}).get('acertos', '-')}</div><div class="r">melhor marca</div></div>
          <div class="kpi"><div class="v">{_n(d.get('pct_concursos_com_premio', 0), 0)}%</div><div class="r">concursos com prêmio</div></div>
        </div>
      </div>
      <p class="mini" style="margin-top:40px; font-size:26px">Arraste para ver os jogos &rarr;</p>
    </div>
  </div>
  <div class="rodape assina"><span>{AVISO_CURTO}</span><span class="perfil">{PERFIL}</span></div>
</div>""")

    # 2 e 3. jogos
    def slide_jogos(pedaco: list[dict], inicio: int, titulo: str) -> str:
        return pag(f"""
<div class="pad">
  <h2>{titulo}</h2>
  <p class="mini" style="margin-top:10px">{_legenda_destaque(ctx)} — em média 9 dezenas se repetem.</p>
  <div class="corpo" style="margin-top:32px">
    {_linhas_de_jogos(pedaco, ultimo, 52, inicio, gap_linha=18, gap_chip=6, cartao=True)}
  </div>
  <div class="rodape assina"><span>{AVISO_CURTO}</span><span class="perfil">{PERFIL}</span></div>
</div>""")

    jogos1 = slide_jogos(jogos[:7], 1, "Jogos 1 a 7")
    jogos2 = slide_jogos(jogos[7:], 8, "Jogos 8 a 13")

    # 4. estatísticas
    par_rotulo, _ = ctx["paridade_top"]
    pares = int(par_rotulo.split()[0])
    atrasadas_txt = " · ".join(
        f"<b>{dz}</b> ({atrasos[dz]['atraso_atual']})" for dz in ctx["atrasadas"][:3]
    )
    estat = pag(f"""
<div class="pad">
  <h2>O que os números<br><span class="destaque">mostram</span></h2>
  <div class="corpo" style="margin-top:34px">
    <div class="cartao">
      <h3>Mais sorteadas nos últimos 100</h3>
      <div style="margin-top:22px">{_chips(ctx['quentes'], set(ctx['quentes']), 92, 14)}</div>
    </div>
    <div class="cartao">
      <h3>Mais atrasadas</h3>
      <div style="margin-top:22px">{_chips(ctx['atrasadas'], set(), 92, 14)}</div>
      <p class="mini" style="margin-top:18px">Entre parênteses, concursos sem sair: {atrasadas_txt}</p>
    </div>
    <div class="cartao">
      <div class="kpis">
        <div class="kpi"><div class="v">{perfil['soma_dezenas']['faixa'][0]}&ndash;{perfil['soma_dezenas']['faixa'][1]}</div>
          <div class="r">soma das 15 dezenas<br>em 8 de cada 10 sorteios</div></div>
        <div class="kpi"><div class="v">{pares}/{15 - pares}</div>
          <div class="r">pares e ímpares<br>é a divisão mais comum</div></div>
      </div>
    </div>
  </div>
  <div class="rodape assina"><span>{AVISO_CURTO}</span><span class="perfil">{PERFIL}</span></div>
</div>""")

    # 5. desempenho
    frases = "".join(
        f'<div style="display:flex; gap:18px; align-items:flex-start">'
        f'<div style="width:13px;height:13px;border-radius:50%;background:{e["destaque"]};'
        f'margin-top:15px;flex:0 0 13px"></div>'
        f'<div class="sub" style="font-size:33px">{f}</div></div>'
        for f in ctx["frases"][:4]
    )
    desempenho = pag(f"""
<div class="pad">
  <h2>Como os jogos vêm<br><span class="destaque">performando</span></h2>
  <div class="corpo" style="margin-top:36px">
    <div style="display:flex; flex-direction:column; gap:26px">{frases}</div>
    <div class="cartao">
      <p class="mini" style="font-size:25px">
        Transparência: a média matemática de acertos de qualquer jogo de 15 dezenas é
        <b>9,00</b>. Nossos filtros deixam os jogos com formato de resultado real —
        <b>não aumentam a chance de ganhar</b>. Nenhuma estratégia aumenta.
      </p>
    </div>
  </div>
  <div class="rodape assina"><span>{AVISO_CURTO}</span><span class="perfil">{PERFIL}</span></div>
</div>""")

    # 6. aviso legal
    aviso = pag(f"""
<div class="pad">
  <div class="corpo" style="justify-content:center">
    <div>
      <div class="tag"><span class="ponto"></span>Leia antes de jogar</div>
      <h2 style="margin-top:30px">Sem promessa.<br><span class="destaque2">Só estatística.</span></h2>
      <div class="cartao" style="margin-top:36px">
        <p class="sub" style="font-size:29px">{AVISO_LONGO}</p>
      </div>
      <div class="cartao" style="margin-top:22px">
        <div class="kpis">
          <div class="kpi"><div class="v" style="font-size:42px">1 em 3.268.760</div>
            <div class="r">chance de 15 acertos<br>em um jogo</div></div>
          <div class="kpi"><div class="v" style="font-size:42px">1 em 251.443</div>
            <div class="r">chance com os<br>13 jogos juntos</div></div>
        </div>
      </div>
    </div>
  </div>
</div>""")

    # 7. CTA
    cta = pag(f"""
<div class="pad">
  <div class="corpo" style="justify-content:center; align-items:center; text-align:center">
    <div>
      <h1 style="font-size:92px">Salve este post<br><span class="destaque">e confira depois</span></h1>
      <p class="sub" style="margin-top:28px; font-size:34px">
        Toda segunda a sábado, logo após a apuração:<br>13 jogos novos e o resultado dos anteriores.
      </p>
      <div class="cartao" style="margin-top:44px">
        <h3 class="destaque" style="font-size:52px">{PERFIL}</h3>
        <h3 style="margin-top:10px">Siga &middot; Salve &middot; Compartilhe</h3>
        <p class="mini" style="margin-top:14px; font-size:26px">
          Comente qual dezena você nunca deixa de fora.
        </p>
      </div>
    </div>
  </div>
  <div class="rodape" style="text-align:center">{AVISO_CURTO}</div>
</div>""")

    return [
        ("1-capa", capa),
        ("2-jogos-1-7", jogos1),
        ("3-jogos-8-13", jogos2),
        ("4-estatisticas", estat),
        ("5-desempenho", desempenho),
        ("6-aviso-legal", aviso),
        ("7-cta", cta),
    ]


# ---------------------------------------------------------------------------
# RENDERIZAÇÃO (HTML -> PNG)
# ---------------------------------------------------------------------------


def renderizar(paginas: list[tuple[str, str, int, int, Path]]) -> list[Path]:
    """Abre um navegador só uma vez e fotografa todas as páginas."""
    from playwright.sync_api import sync_playwright

    geradas: list[Path] = []
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        for _nome, html, largura, altura, destino in paginas:
            pagina = navegador.new_page(viewport={"width": largura, "height": altura})
            pagina.set_content(html, wait_until="load")
            destino.parent.mkdir(parents=True, exist_ok=True)
            pagina.screenshot(path=str(destino))
            # O Instagram só aceita JPEG quando a imagem vem por URL pública,
            # então salvamos as duas versões: PNG (qualidade) e JPG (publicação).
            pagina.screenshot(path=str(destino.with_suffix(".jpg")),
                              type="jpeg", quality=92)
            pagina.close()
            geradas.append(destino)
        navegador.close()
    return geradas


def gerar(concurso: int | None = None, estilos: list[str] | None = None) -> dict[str, Any]:
    ctx = _contexto(concurso)
    estilos = estilos or list(ESTILOS)
    alvo = ctx["concurso"]

    paginas: list[tuple[str, str, int, int, Path]] = []
    indice: dict[str, Any] = {"concurso": alvo, "estilos": {}}

    for chave in estilos:
        e = ESTILOS[chave]
        pasta = PASTA_SAIDAS / str(alvo) / chave
        arquivos = {"carrossel": []}

        paginas.append(("feed", html_feed(ctx, e), 1080, 1080, pasta / "feed.png"))
        arquivos["feed"] = str(pasta / "feed.jpg")

        paginas.append(("stories", html_stories(ctx, e), 1080, 1920, pasta / "stories.png"))
        arquivos["stories"] = str(pasta / "stories.jpg")

        for nome, html in html_carrossel(ctx, e):
            destino = pasta / "carrossel" / f"{nome}.png"
            paginas.append((nome, html, 1080, 1350, destino))
            arquivos["carrossel"].append(str(destino.with_suffix(".jpg")))

        indice["estilos"][chave] = arquivos

    renderizar(paginas)

    destino_indice = PASTA_SAIDAS / str(alvo) / "pecas.json"
    destino_indice.write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    indice["arquivo_indice"] = str(destino_indice)
    return indice


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera as peças visuais do post")
    parser.add_argument("--concurso", type=int, default=None)
    parser.add_argument("--estilo", choices=list(ESTILOS) + ["ambos"], default="ambos")
    args = parser.parse_args()

    estilos = list(ESTILOS) if args.estilo == "ambos" else [args.estilo]
    r = gerar(args.concurso, estilos)

    total = sum(2 + len(v["carrossel"]) for v in r["estilos"].values())
    print(f"{total} imagens geradas para o concurso {r['concurso']}:")
    for estilo, arquivos in r["estilos"].items():
        print(f"  [{ESTILOS[estilo]['nome']}]")
        print(f"    feed     : {arquivos['feed']}")
        print(f"    stories  : {arquivos['stories']}")
        print(f"    carrossel: {len(arquivos['carrossel'])} slides")
    print(f"\nÍndice: {r['arquivo_indice']}")
