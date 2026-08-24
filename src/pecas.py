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

# Se você tiver o logotipo em arquivo, coloque em assets/logo.png (fundo
# transparente). Existindo o arquivo, ele substitui o logotipo desenhado em
# CSS e a peça fica idêntica à sua arte. Sem o arquivo, o robô desenha sozinho.
PASTA_ASSETS = RAIZ / "assets"
ARQUIVO_LOGO = PASTA_ASSETS / "logo.png"


def _logo_html(e: dict, altura: int = 150) -> str:
    """Logotipo do perfil: usa o arquivo próprio, se houver."""
    if not ARQUIVO_LOGO.exists():
        return ""
    import base64
    dados = base64.b64encode(ARQUIVO_LOGO.read_bytes()).decode()
    return (f'<img src="data:image/png;base64,{dados}" alt="Radar 15" '
            f'style="height:{altura}px; width:auto; display:block">')


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

ESTILOS["radar"] = {
    "nome": "Radar",
    "fundo": "radial-gradient(130% 100% at 12% 0%, #10200A 0%, #050805 55%)",
    "superficie": "#0A110A",
    "borda": "#1F3D14",
    "texto": "#FFFFFF",
    "texto2": "#B9C9AC",
    "texto3": "#6E7F63",
    "destaque": "#A3F600",
    "destaque2": "#6FE36B",
    "chip_fundo": "#FFFFFF",
    "chip_borda": "#A3F600",
    "chip_texto": "#06120A",
    "chip_alto_fundo": "linear-gradient(135deg,#A3F600,#6FE36B)",
    "chip_alto_texto": "#06120A",
    "chip_alto_tint": "rgba(163,246,0,.16)",
    "sombra": "0 0 42px rgba(163,246,0,.18)",
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


DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo"]


# Horário do sorteio por dia da semana (0=segunda ... 6=domingo).
# Desde 19/07/2026 a Caixa passou os sorteios de sábado para domingo, às 11h.
HORARIOS = {0: "21h", 1: "21h", 2: "21h", 3: "21h", 4: "21h", 5: "21h", 6: "11h"}


def dias_de_sorteio(base: list[dict], amostra: int = 20) -> set[int]:
    """
    Descobre em QUAIS DIAS DA SEMANA a Lotofácil está sorteando, lendo as datas
    reais dos últimos concursos. Assim, se a Caixa mudar o calendário de novo,
    o robô se ajusta sozinho — foi o que aconteceu em julho/2026, quando os
    sorteios de sábado passaram para domingo.
    """
    from collections import Counter

    contagem: Counter = Counter()
    for registro in base[-amostra:]:
        try:
            contagem[datetime.strptime(registro["data"], "%Y-%m-%d").weekday()] += 1
        except (ValueError, KeyError):
            continue

    # Exige ao menos 2 ocorrências: uma aparição isolada costuma ser
    # antecipação de feriado, não mudança de calendário.
    dias = {dia for dia, vezes in contagem.items() if vezes >= 2}
    return dias or {0, 1, 2, 3, 4, 6}


def _data_do_sorteio(ultimo: dict, base: list[dict] | None = None) -> dict[str, str]:
    """
    Data do próximo sorteio. Prioridade:
      1. o que a própria Caixa informa na API
      2. o próximo dia que bate com o calendário observado nos últimos concursos
    """
    from datetime import timedelta

    def montar(d: datetime, estimada: bool) -> dict[str, str]:
        return {
            "iso": d.strftime("%Y-%m-%d"),
            "br": d.strftime("%d/%m/%Y"),
            "dia": DIAS[d.weekday()],
            "hora": HORARIOS.get(d.weekday(), "21h"),
            "estimada": estimada,
        }

    informada = ultimo.get("data_proximo")
    if informada:
        try:
            return montar(datetime.strptime(informada, "%Y-%m-%d"), False)
        except ValueError:
            pass

    try:
        d = datetime.strptime(ultimo["data"], "%Y-%m-%d")
    except (ValueError, KeyError):
        return {"iso": "", "br": "", "dia": "", "hora": "", "estimada": True}

    validos = dias_de_sorteio(base or [ultimo])
    for _ in range(1, 8):
        d += timedelta(days=1)
        if d.weekday() in validos:
            return montar(d, True)
    return montar(d, True)


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
    # Preferimos o destaque gravado no arquivo do concurso — é ele que foi
    # publicado. Só recalculamos para jogos gerados antes desta versão.
    destaque = jogos.get("destaque") or an.escolher_destaque(
        [j["dezenas"] for j in jogos["jogos"]], base)

    return {
        "destaque": destaque,
        "data_sorteio": _data_do_sorteio(base[-1], base),
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





# Ícones desenhados em SVG — sem depender de fonte de ícone instalada
ICONES = {
    "radar": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/>'
             '<path d="M12 12 L20 6"/>',
    "balanca": '<path d="M12 4v16M6 20h12M5 8h14M5 8l-3 6h6zM19 8l-3 6h6z"/>',
    "pizza": '<path d="M12 3a9 9 0 1 0 9 9h-9z"/><path d="M12 3v9h9A9 9 0 0 0 12 3z"/>',
    "barras": '<path d="M5 20V11M10 20V5M15 20V14M20 20V8"/>',
    "escudo": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "soma": '<path d="M17 4H7l5 8-5 8h10"/>',
    "alvo": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>',
    "calendario": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-5"/>',
    "salvar": '<path d="M6 3h12v18l-6-4-6 4z"/>',
    "instagram": '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1"/>',
}


def _icone(nome: str, cor: str, tamanho: int = 26, traco: float = 1.8) -> str:
    return (f'<svg width="{tamanho}" height="{tamanho}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{cor}" stroke-width="{traco}" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{ICONES[nome]}</svg>')

# ---------- PEÇA DESTAQUE (1 jogo) — 1080 x 1080 ----------


def _radar_svg(cor: str, tamanho: int = 150) -> str:
    """Símbolo do radar: anéis, grade radial, feixe girando e ecos brilhando."""
    aneis = "".join(
        f'<circle cx="50" cy="50" r="{r}" fill="none" stroke="{cor}" '
        f'stroke-opacity="{op}" stroke-width="1.1"/>'
        for r, op in ((46, .55), (36, .34), (25, .26), (14, .2))
    )
    grade = "".join(
        f'<line x1="50" y1="50" x2="{50 + 46 * __import__("math").cos(__import__("math").radians(a))}" '
        f'y2="{50 + 46 * __import__("math").sin(__import__("math").radians(a))}" '
        f'stroke="{cor}" stroke-opacity=".16" stroke-width=".9"/>'
        for a in range(0, 360, 30)
    )
    ecos = "".join(
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="{cor}" fill-opacity="{op}"/>'
        for x, y, r, op in ((70, 33, 2.9, 1), (33, 62, 2.3, .7), (63, 70, 2, .5), (38, 34, 1.8, .45))
    )
    return f"""
<svg width="{tamanho}" height="{tamanho}" viewBox="0 0 100 100" aria-hidden="true"
     style="filter:drop-shadow(0 0 9px {cor}66)">
  <defs>
    <radialGradient id="fundo-radar">
      <stop offset="0%" stop-color="{cor}" stop-opacity=".16"/>
      <stop offset="100%" stop-color="{cor}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="feixe" x1="50%" y1="50%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{cor}" stop-opacity=".9"/>
      <stop offset="100%" stop-color="{cor}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="46" fill="url(#fundo-radar)"/>
  {aneis}
  {grade}
  <path d="M50,50 L96,50 A46,46 0 0,0 79,14 Z" fill="url(#feixe)"/>
  <line x1="50" y1="50" x2="79" y2="14" stroke="{cor}" stroke-width="2.6" stroke-linecap="round"/>
  <circle cx="50" cy="50" r="3.6" fill="{cor}"/>
  {ecos}
</svg>"""


def _barra_nota(nota: int, e: dict, segmentos: int = 20) -> str:
    cheios = round(segmentos * nota / 100)
    return '<div class="barra">' + "".join(
        f'<span class="seg{" on" if i < cheios else ""}"></span>' for i in range(segmentos)
    ) + "</div>"


def _linha_stat(rotulo: str, valor: str, e: dict, icone: str = "check") -> str:
    return f"""
<div class="stat">
  <div class="ico">{_icone(icone, e['destaque'], 30)}</div>
  <div>
    <div class="stat-rot">{rotulo}</div>
    <div class="stat-val">{valor}</div>
  </div>
</div>"""


def html_destaque(ctx: dict, e: dict) -> str:
    d = ctx["destaque"]
    data = ctx["data_sorteio"]
    det = d["detalhes"]
    L = A = 1080

    dezenas = "".join(f'<div class="bola">{n:02d}</div>' for n in d["dezenas"])

    marca_feed = _logo_html(e, 168) or (
        _radar_svg(e["destaque"], 152)
        + '<div class="wordmark"><div class="radar">RADAR</div>'
          '<div class="quinze">15<span class="riscos"><i></i><i></i><i></i></span></div></div>'
    )

    estilo_extra = f"""
.pad {{ padding:24px 26px 20px; gap:11px; }}
.topo {{ display:grid; grid-template-columns:1.38fr 1fr; gap:11px; }}
.meio {{ display:grid; grid-template-columns:1.22fr 1fr; gap:11px; flex:1; min-height:0; }}
.painel {{
  background:#000; border:2px solid {e['borda']};
  border-radius:20px; padding:15px 18px; display:flex; flex-direction:column; min-height:0;
}}

/* ---- logotipo ---- */
.marca {{ display:flex; flex-direction:column; align-items:center; justify-content:center; gap:4px; }}
.marca-topo {{ display:flex; align-items:center; gap:14px; }}
.wordmark {{
  font-style:italic; font-weight:800; line-height:.86; letter-spacing:-.035em;
  transform:skewX(-6deg); text-align:left;
}}
.wordmark .radar {{
  font-size:74px; color:#fff;
  text-shadow:0 3px 0 #9aa39a, 0 5px 0 #4d554d, 0 7px 14px rgba(0,0,0,.85);
}}
.wordmark .quinze {{
  font-size:74px; color:{e['destaque']}; display:flex; align-items:center; gap:10px;
  text-shadow:0 3px 0 #4f7a00, 0 6px 16px {e['destaque']}55;
}}
.riscos {{ display:flex; flex-direction:column; gap:5px; margin-bottom:6px; }}
.riscos i {{
  display:block; height:6px; border-radius:3px; background:{e['destaque']};
  transform:skewX(-18deg);
}}
.riscos i:nth-child(1) {{ width:52px; opacity:1; }}
.riscos i:nth-child(2) {{ width:40px; opacity:.72; }}
.riscos i:nth-child(3) {{ width:28px; opacity:.45; }}
.marca-sub {{
  font-size:19px; letter-spacing:.17em; color:#fff; text-transform:uppercase;
  font-weight:800; margin-top:6px;
}}
.marca-sub em {{ font-style:normal; color:{e['destaque']}; }}
.metodo {{
  margin-top:9px; border:2px solid {e['destaque']}; border-radius:10px;
  padding:5px 18px; font-size:18px; letter-spacing:.1em; color:#fff;
  text-transform:uppercase; font-weight:800;
}}
.metodo b {{ color:{e['destaque']}; }}

/* ---- títulos de seção com linhas laterais ---- */
.tit {{
  display:flex; align-items:center; gap:12px; justify-content:center;
  font-size:20px; letter-spacing:.09em; text-transform:uppercase;
  color:#fff; font-weight:800; white-space:nowrap;
}}
.tit em {{ font-style:normal; color:{e['destaque']}; }}
.tit::before, .tit::after {{
  content:""; height:2px; background:{e['borda']}; flex:1; border-radius:2px;
}}

/* ---- painel do concurso ---- */
.rot {{ font-size:20px; letter-spacing:.14em; text-transform:uppercase; color:#fff; font-weight:800; text-align:center; }}
.concurso-num {{
  font-size:82px; font-weight:800; line-height:1; color:{e['destaque']};
  text-align:center; letter-spacing:-.02em; text-shadow:0 0 26px {e['destaque']}44;
}}
.pilula {{
  background:{e['destaque']}; color:#06120A; border-radius:11px; padding:7px 0;
  text-align:center; margin-top:8px; font-size:23px; font-weight:800; letter-spacing:.08em;
  box-shadow:0 0 22px {e['destaque']}44;
}}
.data {{ display:flex; align-items:center; gap:12px; margin-top:12px; justify-content:center; }}
.data .dia {{ font-size:16px; color:#fff; text-transform:uppercase; letter-spacing:.13em; font-weight:800; }}
.data .dia b {{ color:{e['destaque']}; display:block; font-size:20px; margin-top:1px; }}
.data .num {{ font-size:30px; font-weight:800; line-height:1.15; }}
.data .hora {{ font-size:17px; color:#fff; font-weight:800; letter-spacing:.1em; }}

/* ---- dezenas ---- */
.grade {{ display:grid; grid-template-columns:repeat(5,1fr); gap:12px; flex:1; align-content:space-evenly; margin-top:10px; }}
.bola {{
  aspect-ratio:1; border-radius:50%; background:#fff; color:#000;
  display:flex; align-items:center; justify-content:center;
  font-size:38px; font-weight:800; font-variant-numeric:tabular-nums;
  border:3px solid #000; box-shadow:0 0 0 3px {e['destaque']}, 0 0 20px {e['destaque']}55;
}}
.faixa-metodo {{
  display:flex; align-items:center; gap:13px; margin-top:11px;
  border:2px solid {e['borda']}; border-radius:13px; padding:10px 15px;
}}
.faixa-metodo div {{ font-size:16px; letter-spacing:.05em; text-transform:uppercase; color:#fff; font-weight:800; line-height:1.4; }}
.faixa-metodo em {{ font-style:normal; color:{e['destaque']}; }}

/* ---- o que analisamos ---- */
.stats {{ display:flex; flex-direction:column; justify-content:space-evenly; flex:1; margin-top:4px; }}
.stat {{ display:flex; gap:12px; align-items:center; padding:7px 0; border-bottom:1px solid {e['borda']}; }}
.stat:last-child {{ border-bottom:none; }}
.ico {{ flex:0 0 32px; }}
.stat-rot {{ font-size:15px; letter-spacing:.06em; text-transform:uppercase; color:#fff; font-weight:800; }}
.stat-val {{ font-size:17px; font-weight:700; margin-top:2px; color:{e['texto2']}; }}
.stat-val em {{ font-style:normal; color:{e['destaque']}; font-weight:800; }}

/* ---- rodapés ---- */
.cta {{ display:grid; grid-template-columns:1fr 1fr; gap:11px; }}
.cta .painel {{ padding:13px 18px; flex-direction:row; align-items:center; gap:14px; }}
.cta-tit {{ font-size:25px; font-weight:800; letter-spacing:-.01em; }}
.cta-sub {{ font-size:15px; color:#fff; margin-top:2px; line-height:1.28; text-transform:uppercase; font-weight:700; letter-spacing:.02em; }}
.cta-sub em {{ font-style:normal; color:{e['destaque']}; }}
.aviso-final {{
  border:2px solid {e['borda']}; border-radius:13px; padding:9px 16px;
  font-size:15.5px; color:#fff; text-align:center; line-height:1.35;
  text-transform:uppercase; font-weight:700; letter-spacing:.02em;
  display:flex; align-items:center; justify-content:center; gap:10px;
}}
.aviso-final em {{ font-style:normal; color:{e['destaque']}; font-weight:800; }}
.rodape2 {{ display:grid; grid-template-columns:1fr 1fr; gap:11px; }}
.rodape2 .painel {{ padding:10px 15px; flex-direction:row; align-items:center; gap:11px; }}
.rod-rot {{ font-size:14px; letter-spacing:.08em; text-transform:uppercase; color:{e['destaque']}; font-weight:800; }}
.rod-val {{ font-size:13.5px; color:#fff; line-height:1.35; margin-top:1px; }}
"""

    corpo = f"""
<style>{estilo_extra}</style>
<div class="pad">

  <div class="topo">
    <div class="painel marca">
      <div class="marca-topo">{marca_feed}</div>
      <div class="marca-sub">Inteligência para <em>Lotofácil</em></div>
      <div class="metodo">Método <b>LI-15</b></div>
    </div>

    <div class="painel">
      <div class="rot">Concurso</div>
      <div class="concurso-num">{ctx['concurso']}</div>
      <div class="pilula">&#10052; JOGO GRÁTIS &#10052;</div>
      <div class="data">
        {_icone('calendario', e['destaque'], 34)}
        <div>
          <div class="dia">Sorteio<b>{data['dia']}</b></div>
          <div class="num">{data['br']}</div>
          <div class="hora">às {data['hora']}</div>
        </div>
      </div>
    </div>
  </div>

  <div class="meio">
    <div class="painel">
      <div class="tit">15 dezenas <em>selecionadas</em></div>
      <div class="grade">{dezenas}</div>
      <div class="faixa-metodo">
        {_icone('alvo', e['destaque'], 32)}
        <div>Análise baseada no método <em>LI-15</em><br>
             <span style="font-weight:700; letter-spacing:.03em">estatísticas e distribuição das dezenas</span></div>
      </div>
    </div>

    <div class="painel">
      <div class="tit">O que <em>analisamos</em></div>
      <div class="stats">
      {_linha_stat("Equilíbrio ímpar/par", f"<em>{d['impares']} ímpares</em> / {d['pares']} pares", e, "balanca")}
      {_linha_stat("Distribuição por faixas", " • ".join(str(x) for x in d['faixas']), e, "pizza")}
      {_linha_stat("Frequências analisadas", "quentes • mornas • frias", e, "barras")}
      {_linha_stat("Soma", f"<em>{det['soma']['valor']}</em>", e, "soma")}
      {_linha_stat("Análise estatística LI-15", "critérios de recorrência<br>e distribuição histórica", e, "escudo")}
      </div>
    </div>
  </div>

  <div class="cta">
    <div class="painel">
      {_icone('salvar', e['destaque'], 36)}
      <div>
        <div class="cta-tit">SALVE ESTE POST</div>
        <div class="cta-sub">para conferir o resultado <em>depois do sorteio</em></div>
      </div>
    </div>
    <div class="painel">
      {_icone('instagram', e['destaque'], 36)}
      <div>
        <div class="cta-tit">SIGA {PERFIL.upper()}</div>
        <div class="cta-sub">jogos e resultados <em>todo dia de sorteio</em></div>
      </div>
    </div>
  </div>

  <div class="aviso-final">
    {_icone('alvo', e['destaque'], 22)}
    <span>Sugestão estatística. Não existe garantia de premiação. <em>Jogue com responsabilidade.</em> +18</span>
  </div>

  <div class="rodape2">
    <div class="painel">
      {_icone('check', e['destaque'], 28)}
      <div>
        <div class="rod-rot">Fonte oficial</div>
        <div class="rod-val">Caixa Econômica Federal · consulte loterias.caixa.gov.br<br>Perfil sem vínculo com a Caixa.</div>
      </div>
    </div>
    <div class="painel">
      {_icone('calendario', e['destaque'], 28)}
      <div>
        <div class="rod-rot">Confirmação oficial</div>
        <div class="rod-val">Concurso {ctx['concurso']} · {data['br']} ({data['dia']}) · {data['hora']}<br>Horário conforme o site da Caixa.</div>
      </div>
    </div>
  </div>
</div>"""
    return _pagina(e, L, A, corpo)


# ---------- STORIES 1080 x 1920 ----------


def html_stories(ctx: dict, e: dict) -> str:
    """Versão vertical da peça destaque, para Stories e TikTok."""
    d = ctx["destaque"]
    data = ctx["data_sorteio"]
    det = d["detalhes"]

    dezenas = "".join(f'<div class="bola">{n:02d}</div>' for n in d["dezenas"])

    marca_stories = _logo_html(e, 190) or (
        _radar_svg(e["destaque"], 150)
        + '<div class="wordmark"><div class="radar">RADAR</div>'
          '<div class="quinze">15</div></div>'
    )

    estilo_extra = f"""
.pad {{ padding:150px 46px 96px; gap:20px; }}
.painel {{
  background:#000; border:2px solid {e['borda']}; border-radius:24px;
  padding:22px 24px; display:flex; flex-direction:column;
}}
.marca {{ align-items:center; gap:8px; }}
.marca-topo {{ display:flex; align-items:center; gap:18px; }}
.wordmark {{ font-style:italic; font-weight:800; line-height:.86; letter-spacing:-.035em; transform:skewX(-6deg); }}
.wordmark .radar {{ font-size:86px; color:#fff; text-shadow:0 3px 0 #9aa39a, 0 5px 0 #4d554d; }}
.wordmark .quinze {{ font-size:86px; color:{e['destaque']}; text-shadow:0 3px 0 #4f7a00; }}
.marca-sub {{ font-size:22px; letter-spacing:.16em; color:#fff; text-transform:uppercase; font-weight:800; margin-top:10px; }}
.marca-sub em {{ font-style:normal; color:{e['destaque']}; }}
.faixa-concurso {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
.rot {{ font-size:21px; letter-spacing:.14em; text-transform:uppercase; color:#fff; font-weight:800; text-align:center; }}
.concurso-num {{ font-size:96px; font-weight:800; line-height:1; color:{e['destaque']}; text-align:center; }}
.pilula {{ background:{e['destaque']}; color:#06120A; border-radius:12px; padding:9px 0; text-align:center;
           margin-top:10px; font-size:26px; font-weight:800; letter-spacing:.08em; }}
.data-box {{ text-align:center; justify-content:center; }}
.data-box .dia {{ font-size:24px; color:{e['destaque']}; text-transform:uppercase; letter-spacing:.12em; font-weight:800; }}
.data-box .num {{ font-size:44px; font-weight:800; margin-top:6px; }}
.data-box .hora {{ font-size:24px; font-weight:800; margin-top:4px; }}
.tit {{ display:flex; align-items:center; gap:14px; justify-content:center;
        font-size:24px; letter-spacing:.09em; text-transform:uppercase; color:#fff; font-weight:800; white-space:nowrap; }}
.tit em {{ font-style:normal; color:{e['destaque']}; }}
.tit::before, .tit::after {{ content:""; height:2px; background:{e['borda']}; flex:1; border-radius:2px; }}
.grade {{ display:grid; grid-template-columns:repeat(5,1fr); gap:16px; margin-top:20px; }}
.bola {{
  aspect-ratio:1; border-radius:50%; background:#fff; color:#000;
  display:flex; align-items:center; justify-content:center;
  font-size:52px; font-weight:800; font-variant-numeric:tabular-nums;
  border:3px solid #000; box-shadow:0 0 0 4px {e['destaque']}, 0 0 26px {e['destaque']}55;
}}
.stats {{ display:flex; flex-direction:column; gap:4px; margin-top:8px; }}
.stat {{ display:flex; gap:14px; align-items:center; padding:10px 0; border-bottom:1px solid {e['borda']}; }}
.stat:last-child {{ border-bottom:none; }}
.ico {{ flex:0 0 34px; }}
.stat-rot {{ font-size:17px; letter-spacing:.06em; text-transform:uppercase; color:#fff; font-weight:800; }}
.stat-val {{ font-size:21px; font-weight:700; margin-top:2px; color:{e['texto2']}; }}
.stat-val em {{ font-style:normal; color:{e['destaque']}; font-weight:800; }}
.cta-s {{ display:flex; align-items:center; gap:16px; }}
.cta-tit {{ font-size:30px; font-weight:800; }}
.cta-sub {{ font-size:19px; color:#fff; text-transform:uppercase; font-weight:700; margin-top:3px; }}
.cta-sub em {{ font-style:normal; color:{e['destaque']}; }}
.aviso-final {{
  border:2px solid {e['borda']}; border-radius:14px; padding:14px 18px; margin-top:auto;
  font-size:17px; color:#fff; text-align:center; line-height:1.35;
  text-transform:uppercase; font-weight:700;
}}
.aviso-final em {{ font-style:normal; color:{e['destaque']}; font-weight:800; }}
"""

    corpo = f"""
<style>{estilo_extra}</style>
<div class="pad">
  <div class="painel marca">
    <div class="marca-topo">{marca_stories}</div>
    <div class="marca-sub">Inteligência para <em>Lotofácil</em></div>
  </div>

  <div class="faixa-concurso">
    <div class="painel">
      <div class="rot">Concurso</div>
      <div class="concurso-num">{ctx['concurso']}</div>
      <div class="pilula">JOGO GRÁTIS</div>
    </div>
    <div class="painel data-box">
      <div class="dia">Sorteio {data['dia']}</div>
      <div class="num">{data['br']}</div>
      <div class="hora">às {data['hora']}</div>
    </div>
  </div>

  <div class="painel">
    <div class="tit">15 dezenas <em>selecionadas</em></div>
    <div class="grade">{dezenas}</div>
  </div>

  <div class="painel">
    <div class="tit">O que <em>analisamos</em></div>
    <div class="stats">
      {_linha_stat("Nota do Radar", f"<em>{d['nota']}</em> / 100 de aderência", e, "radar")}
      {_linha_stat("Equilíbrio ímpar/par", f"<em>{d['impares']} ímpares</em> · {d['pares']} pares", e, "balanca")}
      {_linha_stat("Soma das dezenas", f"<em>{det['soma']['valor']}</em> · típico {ctx['perfil']['soma_dezenas']['faixa'][0]}–{ctx['perfil']['soma_dezenas']['faixa'][1]}", e, "barras")}
      {_linha_stat("Cobertura histórica", f"<em>{_n(len(ctx['base']), 0)}</em> concursos", e, "escudo")}
    </div>
  </div>

  <div class="painel cta-s">
    {_icone('instagram', e['destaque'], 44)}
    <div>
      <div class="cta-tit">SIGA {PERFIL.upper()}</div>
      <div class="cta-sub">resultado publicado <em>depois do sorteio</em></div>
    </div>
  </div>

  <div class="aviso-final">
    Sugestão estatística. Não existe garantia de premiação.<br>
    <em>Jogue com responsabilidade.</em> +18
  </div>
</div>"""
    return _pagina(e, 1080, 1920, corpo)


# ---------- CARROSSEL 1080 x 1350 ----------


def html_carrossel(ctx: dict, e: dict) -> list[tuple[str, str]]:
    dest = ctx["destaque"]
    d = ctx["desempenho"]
    perfil = ctx["perfil"]
    atrasos = an.atrasos(ctx["base"])
    data = ctx["data_sorteio"]
    L, A = 1080, 1350

    def pag(corpo: str) -> str:
        return _pagina(e, L, A, corpo)

    def rodape() -> str:
        return (f'<div class="rodape assina"><span>{AVISO_CURTO}</span>'
                f'<span class="perfil">{PERFIL}</span></div>')

    # 1. capa
    capa = pag(f"""
<div class="pad">
  <div class="corpo" style="justify-content:center">
    <div>
      <div class="tag"><span class="ponto"></span>{PERFIL} · Concurso {ctx['concurso']}</div>
      <h1 style="margin-top:32px; font-size:100px">Jogo grátis<br><span class="destaque">da Lotofácil</span></h1>
      <p class="sub" style="margin-top:24px; font-size:32px">
        Sorteio {data['dia']}, {data['br']} às {data['hora']}<br>
        {_n(len(ctx['base']), 0)} concursos analisados
      </p>
      <div class="cartao" style="margin-top:40px">
        <div class="kpis">
          <div class="kpi"><div class="v destaque">{dest['nota']}</div><div class="r">nota do radar</div></div>
          <div class="kpi"><div class="v">{_n(d.get('media_de_acertos', 0))}</div><div class="r">acertos por jogo</div></div>
          <div class="kpi"><div class="v">{d.get('melhor_resultado', {}).get('acertos', '-')}</div><div class="r">melhor marca</div></div>
        </div>
      </div>
      <p class="mini" style="margin-top:36px; font-size:26px">Arraste para ver o jogo &rarr;</p>
    </div>
  </div>
  {rodape()}
</div>""")

    # 2. jogo do dia
    jogo_do_dia = pag(f"""
<div class="pad">
  <h2>O jogo <span class="destaque">de hoje</span></h2>
  <p class="mini" style="margin-top:10px">
    Nota {dest['nota']}/100 de aderência · {dest['impares']} ímpares e {dest['pares']} pares ·
    soma {dest['detalhes']['soma']['valor']}
  </p>
  <div class="corpo" style="margin-top:30px; justify-content:center">
    <div style="display:flex; flex-direction:column; gap:18px; align-items:center">
      {_chips(dest['dezenas'][:5], set(dest['dezenas']), 148, 18)}
      {_chips(dest['dezenas'][5:10], set(dest['dezenas']), 148, 18)}
      {_chips(dest['dezenas'][10:], set(dest['dezenas']), 148, 18)}
    </div>
  </div>
  {rodape()}
</div>""")

    # 3. estatísticas
    par_rotulo, _ = ctx["paridade_top"]
    pares = int(par_rotulo.split()[0])
    atrasadas_txt = " · ".join(
        f"<b>{dz}</b> ({atrasos[dz]['atraso_atual']})" for dz in ctx["atrasadas"][:3]
    )
    estat = pag(f"""
<div class="pad">
  <h2>O que os números<br><span class="destaque">mostram</span></h2>
  <div class="corpo" style="margin-top:32px">
    <div class="cartao">
      <h3>Mais sorteadas nos últimos 100</h3>
      <div style="margin-top:20px">{_chips(ctx['quentes'], set(ctx['quentes']), 92, 14)}</div>
    </div>
    <div class="cartao">
      <h3>Mais atrasadas</h3>
      <div style="margin-top:20px">{_chips(ctx['atrasadas'], set(), 92, 14)}</div>
      <p class="mini" style="margin-top:16px">Entre parênteses, concursos sem sair: {atrasadas_txt}</p>
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
  {rodape()}
</div>""")

    # 4. desempenho
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
  <div class="corpo" style="margin-top:34px">
    <div style="display:flex; flex-direction:column; gap:24px">{frases}</div>
    <div class="cartao">
      <p class="mini" style="font-size:25px">
        Transparência: a média matemática de acertos de qualquer jogo de 15 dezenas é
        <b>9,00</b>. A Nota do Radar mede semelhança com o padrão histórico —
        <b>não aumenta a chance de ganhar</b>. Nenhuma estratégia aumenta.
      </p>
    </div>
  </div>
  {rodape()}
</div>""")

    # 5. aviso legal
    aviso = pag(f"""
<div class="pad">
  <div class="corpo" style="justify-content:center">
    <div>
      <div class="tag"><span class="ponto"></span>Leia antes de jogar</div>
      <h2 style="margin-top:28px">Sem promessa.<br><span class="destaque2">Só estatística.</span></h2>
      <div class="cartao" style="margin-top:34px">
        <p class="sub" style="font-size:29px">{AVISO_LONGO}</p>
      </div>
      <div class="cartao" style="margin-top:20px">
        <div class="kpis">
          <div class="kpi"><div class="v" style="font-size:42px">1 em 3.268.760</div>
            <div class="r">chance de 15 acertos<br>em um jogo</div></div>
          <div class="kpi"><div class="v" style="font-size:42px">R$ 3,50</div>
            <div class="r">custo de uma<br>aposta simples</div></div>
        </div>
      </div>
    </div>
  </div>
</div>""")

    # 6. CTA
    cta = pag(f"""
<div class="pad">
  <div class="corpo" style="justify-content:center; align-items:center; text-align:center">
    <div>
      <h1 style="font-size:88px">Salve este post<br><span class="destaque">e volte depois</span></h1>
      <p class="sub" style="margin-top:26px; font-size:33px">
        Publicamos o resultado deste jogo<br>logo após o sorteio, dê no que der.
      </p>
      <div class="cartao" style="margin-top:40px">
        <h3 class="destaque" style="font-size:50px">{PERFIL}</h3>
        <h3 style="margin-top:10px">Siga &middot; Salve &middot; Compartilhe</h3>
      </div>
    </div>
  </div>
  <div class="rodape" style="text-align:center">{AVISO_CURTO}</div>
</div>""")

    return [
        ("1-capa", capa),
        ("2-jogo-do-dia", jogo_do_dia),
        ("3-estatisticas", estat),
        ("4-desempenho", desempenho),
        ("5-aviso-legal", aviso),
        ("6-cta", cta),
    ]


# ---------- PEÇA DE RESULTADO — 1080 x 1080 ----------


def contexto_resultado(concurso: int) -> dict[str, Any]:
    """
    Junta o que a peça de resultado precisa: o sorteio real, o jogo que foi
    publicado antes dele e quantos acertos fez.
    """
    from src.desempenho import carregar_historico, formatar_reais, resumo

    base = carregar_base()
    sorteio = next((c for c in base if c["concurso"] == concurso), None)
    if sorteio is None:
        raise RuntimeError(f"O concurso {concurso} ainda não está na base.")

    jogos = carregar_jogos(concurso)
    if jogos is None:
        raise RuntimeError(f"Não encontrei os jogos publicados do concurso {concurso}.")

    publicado = (jogos.get("destaque")
                 or an.escolher_destaque([j["dezenas"] for j in jogos["jogos"]], base))

    sorteadas = set(sorteio["dezenas"])
    acertadas = sorted(set(publicado["dezenas"]) & sorteadas)
    acertos = len(acertadas)

    premio = float((sorteio.get("rateios") or {}).get(str(acertos), 0) or 0)

    # Desempenho do conjunto dos 13 (material do grupo VIP)
    registro = next(
        (r for r in carregar_historico() if r["concurso"] == concurso and not r["simulado"]),
        None,
    )

    d = resumo(10, incluir_simulados=True)

    return {
        "concurso": concurso,
        "base": base,
        "data": _data_br(sorteio["data"]),
        "sorteadas": sorted(sorteadas),
        "publicado": publicado["dezenas"],
        "acertadas": acertadas,
        "acertos": acertos,
        "premio": premio,
        "premio_texto": formatar_reais(premio) if premio else "",
        "nota": publicado.get("nota"),
        "conjunto": registro,
        "desempenho": d,
        "ganhadores_15": sorteio.get("ganhadores_15", 0),
    }


def html_resultado(ctx: dict, e: dict) -> str:
    L = A = 1080
    acertos = ctx["acertos"]
    acertadas = set(ctx["acertadas"])
    proximo = ctx["concurso"] + 1

    sorteadas = "".join(f'<div class="bola">{n:02d}</div>' for n in ctx["sorteadas"])
    jogo = "".join(f'<div class="bola-plana">{n:02d}</div>' for n in ctx["publicado"])
    comparativo = "".join(
        (f'<div class="bola-comp hit">{n:02d}{_icone("check", e["chip_alto_texto"], 14, 2.4)}</div>'
         if n in acertadas else f'<div class="bola-comp miss">{n:02d}</div>')
        for n in ctx["publicado"]
    )

    marca_feed = _logo_html(e, 96) or _radar_svg(e["destaque"], 92)

    estilo_extra = f"""
.pad {{ padding:30px 34px 26px; gap:14px; }}
.painel {{
  background:#000; border:2px solid {e['borda']};
  border-radius:20px; padding:16px 20px; display:flex; flex-direction:column; min-height:0;
}}
.topo {{ display:flex; justify-content:space-between; align-items:center; gap:14px; }}
.marca-linha {{ display:flex; align-items:center; gap:14px; }}
.marca-linha .wordmark {{ display:flex; align-items:baseline; gap:9px; font-style:italic; font-weight:800; letter-spacing:-.02em; transform:skewX(-6deg); }}
.marca-linha .wordmark .radar {{ font-size:34px; color:#fff; }}
.marca-linha .wordmark .quinze {{ font-size:34px; color:{e['destaque']}; }}
.marca-linha .marca-sub {{ font-size:14px; letter-spacing:.15em; text-transform:uppercase; color:{e['texto2']}; font-weight:700; margin-top:2px; }}
.badge-ok {{ display:flex; align-items:center; gap:12px; text-align:right; }}
.badge-txt .tit-ok {{ font-size:24px; font-weight:800; color:{e['destaque']}; letter-spacing:-.01em; }}
.badge-txt .sub-ok {{ font-size:14px; letter-spacing:.1em; text-transform:uppercase; color:{e['texto2']}; font-weight:700; margin-top:2px; }}
.info-row {{ display:flex; justify-content:space-around; padding:14px 6px; }}
.info-item {{ text-align:center; flex:1; }}
.info-item + .info-item {{ border-left:1.5px solid {e['borda']}; }}
.info-rot {{ font-size:13.5px; letter-spacing:.12em; text-transform:uppercase; color:{e['texto2']}; font-weight:700; }}
.info-val {{ font-size:26px; font-weight:800; margin-top:4px; }}
.info-val.dest {{ color:{e['destaque']}; }}
.faixa-banner {{
  align-self:center; background:{e['destaque']}; color:{e['chip_alto_texto']};
  padding:6px 24px; border-radius:8px; font-size:15px; font-weight:800;
  letter-spacing:.1em; text-transform:uppercase; margin-bottom:10px;
}}
.grade {{ display:flex; flex-wrap:wrap; justify-content:center; gap:8px; }}
.bola {{
  width:68px; height:68px; flex:0 0 auto; border-radius:50%; background:#fff; color:#000;
  display:flex; align-items:center; justify-content:center;
  font-size:26px; font-weight:800; font-variant-numeric:tabular-nums;
  border:2.5px solid #000; box-shadow:0 0 0 2.5px {e['destaque']};
}}
.duo {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
.tit {{ font-size:15px; letter-spacing:.12em; text-transform:uppercase; color:{e['texto2']}; font-weight:800; text-align:center; margin-bottom:8px; }}
.grade-mini {{ display:flex; flex-wrap:wrap; justify-content:center; gap:7px; }}
.bola-plana {{
  width:48px; height:48px; flex:0 0 auto; border-radius:50%; border:2px solid {e['borda']}; color:{e['texto2']};
  display:flex; align-items:center; justify-content:center;
  font-size:18px; font-weight:800; font-variant-numeric:tabular-nums;
}}
.bola-comp {{
  width:48px; height:48px; flex:0 0 auto; border-radius:50%; position:relative;
  display:flex; align-items:center; justify-content:center;
  font-size:18px; font-weight:800; font-variant-numeric:tabular-nums;
}}
.bola-comp.hit {{ background:{e['destaque']}; color:{e['chip_alto_texto']}; box-shadow:0 0 14px {e['destaque']}66; }}
.bola-comp.hit svg {{ position:absolute; bottom:-3px; right:-3px; background:#000; border-radius:50%; padding:1px; }}
.bola-comp.miss {{ border:2px solid {e['borda']}; color:{e['texto3']}; }}
.trofeu {{
  display:grid; grid-template-columns:1fr auto 1.15fr; align-items:center; gap:16px;
  border:2px solid {e['destaque']}; padding:14px 22px;
}}
.ac-rot {{ font-size:16px; letter-spacing:.1em; text-transform:uppercase; color:{e['destaque']}; font-weight:800; }}
.ac-num {{ font-size:66px; font-weight:800; line-height:1; margin-top:2px; }}
.ac-de {{ font-size:16px; letter-spacing:.1em; text-transform:uppercase; color:{e['texto2']}; font-weight:700; margin-top:2px; }}
.emoji-trofeu {{ font-size:74px; line-height:1; }}
.conf-rot {{ font-size:14px; letter-spacing:.1em; text-transform:uppercase; color:{e['texto2']}; font-weight:700; }}
.conf-num {{ font-size:34px; font-weight:800; color:{e['destaque']}; margin-top:2px; }}
.conf-banner {{
  margin-top:8px; background:{e['destaque']}; color:{e['chip_alto_texto']};
  border-radius:8px; padding:6px 16px; font-size:14px; font-weight:800;
  letter-spacing:.08em; text-transform:uppercase; text-align:center;
}}
.rodape-final {{ display:flex; justify-content:space-between; align-items:center; gap:14px; }}
.rf-txt {{ font-size:14px; color:{e['texto2']}; line-height:1.4; }}
.rf-txt b {{ color:#fff; }}
.rf-num {{ text-align:right; }}
.rf-rot {{ font-size:13px; letter-spacing:.1em; text-transform:uppercase; color:{e['texto2']}; font-weight:700; }}
.rf-val {{ font-size:30px; font-weight:800; color:{e['destaque']}; }}
.barra-ig {{
  background:{e['destaque']}; color:{e['chip_alto_texto']}; border-radius:16px;
  padding:12px 22px; display:flex; justify-content:space-between; align-items:center;
  font-size:14.5px; font-weight:800; letter-spacing:.06em; text-transform:uppercase;
}}
"""

    corpo = f"""
<style>{estilo_extra}</style>
<div class="pad">

  <div class="painel">
    <div class="topo">
      <div class="marca-linha">
        {marca_feed}
        <div>
          <div class="wordmark"><div class="radar" style="font-size:34px">RADAR</div>
            <div class="quinze" style="font-size:34px">15</div></div>
          <div class="marca-sub" style="margin-top:2px">Análises · Padrões · Resultados</div>
        </div>
      </div>
      <div class="badge-ok">
        <div class="badge-txt">
          <div class="tit-ok">Resultado conferido</div>
          <div class="sub-ok">Comparativo oficial</div>
        </div>
        {_icone('check', e['destaque'], 38)}
      </div>
    </div>
    <div class="info-row">
      <div class="info-item">
        <div class="info-rot">Concurso</div>
        <div class="info-val dest">{ctx['concurso']}</div>
      </div>
      <div class="info-item">
        <div class="info-rot">Data do sorteio</div>
        <div class="info-val">{ctx['data']}</div>
      </div>
      <div class="info-item">
        <div class="info-rot">Resultado oficial</div>
        <div class="info-val">Caixa</div>
      </div>
    </div>
  </div>

  <div class="painel">
    <div class="faixa-banner">Dezenas sorteadas</div>
    <div class="grade">{sorteadas}</div>
  </div>

  <div class="duo">
    <div class="painel">
      <div class="tit">Jogo do Radar 15</div>
      <div class="grade-mini">{jogo}</div>
    </div>
    <div class="painel">
      <div class="tit">Comparativo</div>
      <div class="grade-mini">{comparativo}</div>
    </div>
  </div>

  <div class="painel trofeu">
    <div>
      <div class="ac-rot">Acertos</div>
      <div class="ac-num">{acertos}</div>
      <div class="ac-de">de 15</div>
    </div>
    <div class="emoji-trofeu">🏆</div>
    <div>
      <div class="conf-rot">Conferência oficial</div>
      <div class="conf-num">{acertos} acertos</div>
      <div class="conf-banner">Resultado conferido</div>
    </div>
  </div>

  <div class="painel">
    <div class="rodape-final">
      <div class="rf-txt"><b>Analisamos padrões. Entregamos resultados.</b><br>Radar 15 · mais que um jogo, uma estratégia!</div>
      <div class="rf-num">
        <div class="rf-rot">Próximo concurso</div>
        <div class="rf-val">{proximo}</div>
      </div>
    </div>
  </div>

  <div class="barra-ig">
    <span>Siga {PERFIL} no Instagram</span>
    <span>Compartilhe e boa sorte!</span>
  </div>
</div>"""
    return _pagina(e, L, A, corpo)


def gerar_resultado(concurso: int, estilos: list[str] | None = None) -> dict[str, Any]:
    """Gera a peça de resultado de um concurso já sorteado."""
    ctx = contexto_resultado(concurso)
    estilos = estilos or list(ESTILOS)
    paginas, indice = [], {"concurso": concurso, "acertos": ctx["acertos"], "estilos": {}}

    for chave in estilos:
        pasta = PASTA_SAIDAS / str(concurso) / chave / "resultado"
        destino = pasta / "resultado.png"
        paginas.append(("resultado", html_resultado(ctx, ESTILOS[chave]), 1080, 1080, destino))
        indice["estilos"][chave] = str(destino.with_suffix(".jpg"))

    renderizar(paginas)
    arquivo = PASTA_SAIDAS / str(concurso) / "resultado.json"
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps(indice, ensure_ascii=False, indent=1), encoding="utf-8")
    return indice


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

        # Limpa a pasta antes de gerar. Sem isso, slides de uma versão antiga
        # ficariam para trás e poderiam acabar publicados junto com os novos.
        if pasta.exists():
            import shutil
            shutil.rmtree(pasta)
        arquivos = {"carrossel": []}

        paginas.append(("feed", html_destaque(ctx, e), 1080, 1080, pasta / "feed.png"))
        # Os 13 jogos NÃO entram no índice público: são o material do grupo VIP
        paginas.append(("13jogos", html_feed(ctx, e), 1080, 1080,
                        pasta / "vip" / "13-jogos.png"))
        arquivos["feed"] = str(pasta / "feed.jpg")
        arquivos["vip_13_jogos"] = str(pasta / "vip" / "13-jogos.jpg")

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
    parser.add_argument("--resultado", type=int, default=None,
                        help="gera a peça de RESULTADO de um concurso já sorteado")
    args = parser.parse_args()

    if args.resultado:
        r = gerar_resultado(args.resultado)
        print(f"Peça de resultado do concurso {r['concurso']} "
              f"({r['acertos']} acertos) gerada em {len(r['estilos'])} estilos:")
        for estilo, caminho in r["estilos"].items():
            print(f"  {estilo}: {caminho}")
        raise SystemExit(0)

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
