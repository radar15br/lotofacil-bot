"""
POSTS FIXADOS DO PERFIL
=======================

Dois carrosséis para fixar no topo do perfil — é o que a pessoa vê quando
chega pela primeira vez e decide se segue:

  como-funciona  — o que é o Radar 15, como o jogo é montado, o compromisso
                   de conferir sempre, e o aviso legal
  placar         — o placar aberto de TODOS os jogos publicados até hoje,
                   com a média comparada à média matemática (9,00)

Como rodar:
    python -m src.fixados                       # gera os dois
    python -m src.fixados --publicar placar     # gera e publica um deles
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from typing import Any

from src import pecas
from src.desempenho import carregar_historico, formatar_reais

E = pecas.ESTILOS["radar"]
L, A = 1080, 1350
PASTA = pecas.PASTA_SAIDAS / "fixados"
_n = pecas._n
_ic = pecas._icone

# ---------------------------------------------------------------------------
# SISTEMA VISUAL — o mesmo das peças diárias (painéis pretos com borda verde,
# bolas brancas com anel limão, faixa limão no rodapé)
# ---------------------------------------------------------------------------

CSS = f"""
.pad {{ padding:40px 40px 34px; gap:18px; }}
.painel {{ background:#000; border:2px solid {E['borda']}; border-radius:24px; padding:26px 30px; }}
.painel.forte {{ border-color:{E['destaque']}; box-shadow:0 0 36px rgba(163,246,0,.14); }}
.cresce {{ flex:1; min-height:0; display:flex; flex-direction:column; }}
.topo {{ display:flex; justify-content:space-between; align-items:center; padding:18px 26px; }}
.marca {{ display:flex; align-items:center; gap:16px; }}
.wm {{ font-style:italic; font-weight:800; letter-spacing:-.02em; font-size:40px; line-height:1; }}
.wm-sub {{ font-size:14px; letter-spacing:.16em; text-transform:uppercase; color:{E['texto2']}; font-weight:700; margin-top:6px; }}
.sec {{ text-align:right; }}
.sec .rot {{ font-size:17px; letter-spacing:.14em; text-transform:uppercase; color:{E['destaque']}; font-weight:800; }}
.sec .pg {{ font-size:15px; letter-spacing:.12em; color:{E['texto3']}; font-weight:700; margin-top:4px; }}
.faixa {{ background:{E['destaque']}; color:#06120A; border-radius:16px; padding:16px 26px;
  display:flex; justify-content:space-between; align-items:center;
  font-size:21px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }}
.aviso {{ font-size:17px; color:{E['texto3']}; text-align:center; line-height:1.35; }}
.rotulo {{ font-size:17px; letter-spacing:.14em; text-transform:uppercase; color:{E['texto2']}; font-weight:800; }}
.titulo {{ font-size:96px; font-weight:800; line-height:1; letter-spacing:-.03em; }}
.titulo2 {{ font-size:70px; font-weight:800; line-height:1.03; letter-spacing:-.025em; }}
.txt {{ font-size:30px; color:{E['texto2']}; line-height:1.35; }}
.bola {{ width:var(--b,66px); height:var(--b,66px); border-radius:50%; background:#fff; color:#000;
  display:flex; align-items:center; justify-content:center; flex:0 0 auto;
  font-size:calc(var(--b,66px)*.4); font-weight:800; font-variant-numeric:tabular-nums;
  border:2.5px solid #000; box-shadow:0 0 0 2.5px {E['destaque']}; }}
.bola.hit {{ background:{E['destaque']}; box-shadow:0 0 0 2.5px {E['destaque']}, 0 0 18px rgba(163,246,0,.55); }}
.bola.miss {{ background:transparent; color:{E['texto3']}; border:2px solid {E['borda']}; box-shadow:none; }}
.centro {{ margin:0 auto; }}
.bolas {{ display:flex; flex-wrap:wrap; justify-content:center; gap:10px; }}
.kpi-g {{ text-align:center; }}
.kpi-g .v {{ font-size:150px; font-weight:800; line-height:1; letter-spacing:-.04em; font-variant-numeric:tabular-nums; }}
.kpi-g .r {{ font-size:22px; letter-spacing:.1em; text-transform:uppercase; color:{E['texto2']}; font-weight:800; margin-top:10px; line-height:1.3; }}
.chip-tag {{ display:inline-flex; align-items:center; gap:10px; background:{E['destaque']}; color:#06120A;
  font-size:17px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; padding:8px 18px; border-radius:10px; }}
"""


def _pag(corpo: str) -> str:
    return pecas._pagina(E, L, A, corpo).replace("</style>", CSS + "</style>")


def _topo(secao: str, pagina: str) -> str:
    return f"""
<div class="painel topo">
  <div class="marca">{pecas._radar_svg(E['destaque'], 78)}
    <div><div class="wm">RADAR <span class="destaque">15</span></div>
    <div class="wm-sub">Inteligência para <span class="destaque">Lotofácil</span></div></div>
  </div>
  <div class="sec"><div class="rot">{secao}</div><div class="pg">{pagina}</div></div>
</div>"""


def _base(direita: str = "Placar aberto, sempre") -> str:
    return f"""
<div class="aviso">{pecas.AVISO_CURTO}</div>
<div class="faixa"><span>Siga {pecas.PERFIL}</span><span>{direita}</span></div>"""


def _bolas(numeros, classe: dict | None = None, tamanho: int = 66) -> str:
    classe = classe or {}
    return (f'<div class="bolas" style="--b:{tamanho}px">' + "".join(
        f'<div class="bola {classe.get(n, "")}">{n:02d}</div>' for n in numeros) + "</div>")


# ---------------------------------------------------------------------------
# COMO FUNCIONA
# ---------------------------------------------------------------------------


def como_funciona() -> list[tuple[str, str]]:
    total = 5
    ultimo = next(r for r in reversed(carregar_historico()) if not r.get("simulado"))
    ex = pecas.contexto_resultado(ultimo["concurso"])
    acertadas = set(ex["acertadas"])
    marcas = {n: ("hit" if n in acertadas else "miss") for n in ex["publicado"]}

    capa = _pag(f"""
<div class="pad">
  {_topo("Comece por aqui", f"1 / {total}")}
  <div class="painel forte" style="padding:40px 40px 36px">
    <div class="titulo">Como funciona<br>o <span class="destaque">Radar 15</span></div>
    <div class="txt" style="margin-top:22px">Um jogo grátis antes de cada sorteio.<br>O resultado conferido logo depois.</div>
  </div>
  <div class="painel cresce" style="justify-content:space-evenly">
    <div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <span class="chip-tag">1 · Antes do sorteio</span><span class="rotulo">Concurso {ex['concurso']}</span>
      </div>
      {_bolas(ex['publicado'], tamanho=64)}
    </div>
    <div style="display:flex;align-items:center;gap:16px;color:{E['texto3']};font-size:20px;font-weight:700;letter-spacing:.12em">
      <div style="flex:1;height:2px;background:{E['borda']}"></div>SORTEIO DA CAIXA<div style="flex:1;height:2px;background:{E['borda']}"></div>
    </div>
    <div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <span class="chip-tag">2 · Depois do sorteio</span>
        <span style="font-size:34px;font-weight:800"><span class="destaque">{ex['acertos']}</span> acertos</span>
      </div>
      {_bolas(ex['publicado'], marcas, 64)}
    </div>
  </div>
  {_base("Arraste para entender →")}
</div>""")

    passos = [
        ("barras", "Analisa o histórico", "Todos os concursos desde 2003, da base oficial da Caixa."),
        ("balanca", "Monta o jogo", "15 dezenas no equilíbrio mais comum: pares, ímpares, soma e moldura."),
        ("calendario", "Publica antes", "O jogo vai ao ar antes do sorteio. Sem editar depois."),
        ("check", "Confere depois", "Reel com os acertos logo após o sorteio — dê no que der."),
    ]
    cards = "".join(f"""
<div class="painel" style="display:flex;flex-direction:column;gap:16px;padding:30px 28px">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <div style="width:84px;height:84px;border-radius:50%;background:{E['chip_alto_tint']};border:2px solid {E['destaque']};
      display:flex;align-items:center;justify-content:center">{_ic(ic, E['destaque'], 42, 2)}</div>
    <div style="font-size:84px;font-weight:800;color:{E['borda']};line-height:1">{i}</div>
  </div>
  <div style="font-size:46px;font-weight:800;line-height:1.05;letter-spacing:-.015em;margin-top:auto">{t}</div>
  <div style="font-size:30px;color:{E['texto2']};line-height:1.32">{d}</div>
</div>""" for i, (ic, t, d) in enumerate(passos, 1))
    metodo = _pag(f"""
<div class="pad">
  {_topo("O método", f"2 / {total}")}
  <div class="painel"><div class="titulo2">Quatro passos, <span class="destaque">todo dia</span></div></div>
  <div class="cresce" style="display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;gap:18px">{cards}</div>
  {_base()}
</div>""")

    try:
        hist = dados_placar()["linhas"][-10:]
    except RuntimeError:
        hist = []
    mini = "".join(
        f'<div style="text-align:center"><div class="bola centro {"hit" if x["acertos"] >= 11 else ""}" '
        f'style="--b:116px">{x["acertos"]}</div><div style="font-size:19px;color:{E["texto3"]};margin-top:10px;'
        f'font-weight:700">{x["concurso"]}</div></div>' for x in hist)
    compromisso = _pag(f"""
<div class="pad">
  {_topo("Nosso compromisso", f"3 / {total}")}
  <div class="painel forte" style="padding:40px">
    <div class="titulo2">Placar aberto.<br><span class="destaque">Sem esconder dia ruim.</span></div>
    <div class="txt" style="margin-top:20px">Qualquer perfil parece acertar se só mostrar os dias bons. Aqui, todo jogo publicado é conferido em público.</div>
  </div>
  <div class="painel cresce" style="justify-content:center;gap:22px">
    <div class="rotulo" style="text-align:center">Acertos dos últimos {len(hist)} jogos publicados</div>
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:30px 10px">{mini}</div>
  </div>
  <div class="painel" style="padding:22px 28px">
    <div style="font-size:23px;color:{E['texto2']};line-height:1.4">Transparência: a média matemática de acertos de qualquer jogo de
    15 dezenas é <b style="color:#fff">9,00</b>. A análise mostra padrões do histórico — <b style="color:#fff">não aumenta a chance de ganhar</b>.</div>
  </div>
  {_base()}
</div>""")

    def bloco(dia: str, hora: str, nota: str) -> str:
        return f"""
<div class="painel forte" style="display:flex;align-items:center;gap:30px;padding:34px 36px">
  <div style="width:110px;height:110px;border-radius:24px;background:{E['chip_alto_tint']};border:2px solid {E['destaque']};
    display:flex;align-items:center;justify-content:center;flex:0 0 auto">{_ic('calendario', E['destaque'], 58, 1.8)}</div>
  <div style="flex:1"><div class="rotulo">{dia}</div>
    <div style="font-size:30px;color:{E['texto2']};margin-top:10px;line-height:1.3">{nota}</div></div>
  <div style="font-size:120px;font-weight:800;letter-spacing:-.04em;line-height:1" class="destaque">{hora}</div>
</div>"""
    horarios = _pag(f"""
<div class="pad">
  {_topo("Quando sai", f"4 / {total}")}
  <div class="painel"><div class="titulo2">Todo dia de sorteio,<br><span class="destaque">logo depois da Caixa</span></div></div>
  <div class="cresce" style="display:flex;flex-direction:column;justify-content:space-evenly;gap:18px">
    {bloco("Segunda a sexta", "21h", "Sorteio às 21h.<br>Resultado + próximo jogo em seguida.")}
    {bloco("Domingo", "11h", "Sorteio às 11h.<br>Resultado + próximo jogo em seguida.")}
    <div class="painel" style="display:flex;align-items:center;gap:24px;padding:28px 34px">
      {_ic('instagram', E['destaque'], 54, 1.8)}
      <div style="font-size:30px;line-height:1.3"><b>Ative as notificações</b><br>
      <span style="color:{E['texto2']}">Toque no sininho do perfil e receba o jogo assim que sair.</span></div>
    </div>
  </div>
  {_base()}
</div>""")

    acoes = "".join(f"""
<div class="painel" style="display:flex;align-items:center;gap:26px;padding:28px 32px">
  <div style="width:76px;height:76px;border-radius:50%;background:{E['destaque']};display:flex;align-items:center;justify-content:center;flex:0 0 auto">
    {_ic(ic, '#06120A', 38, 2.2)}</div>
  <div style="font-size:40px;font-weight:800">{t}</div>
</div>""" for ic, t in (("instagram", f"Siga <span class='destaque'>{pecas.PERFIL}</span>"),
                       ("salvar", "Salve este post"),
                       ("check", "Mande para quem joga com você")))
    cta = _pag(f"""
<div class="pad">
  {_topo("Faça parte", f"5 / {total}")}
  <div class="painel forte" style="padding:44px 40px;text-align:center">
    <div class="titulo">Receba o jogo<br><span class="destaque">de graça</span></div>
    <div class="txt" style="margin-top:20px">Todo dia de sorteio, antes da Caixa sortear.</div>
  </div>
  <div class="cresce" style="display:flex;flex-direction:column;justify-content:space-evenly;gap:16px">{acoes}</div>
  <div class="painel" style="padding:20px 26px"><div style="font-size:18px;color:{E['texto3']};line-height:1.4">{pecas.AVISO_LONGO}</div></div>
  <div class="faixa"><span>Siga {pecas.PERFIL}</span><span>+18 · Jogue com responsabilidade</span></div>
</div>""")

    return [("1-capa", capa), ("2-metodo", metodo), ("3-placar-aberto", compromisso),
            ("4-horarios", horarios), ("5-siga", cta)]


# ---------------------------------------------------------------------------
# PLACAR
# ---------------------------------------------------------------------------


def dados_placar() -> dict[str, Any]:
    """Acertos do jogo PUBLICADO (o destaque) em cada concurso real conferido."""
    linhas = []
    for r in carregar_historico():
        if r.get("simulado"):
            continue
        try:
            c = pecas.contexto_resultado(r["concurso"])
        except Exception:  # noqa: BLE001 — concurso sem jogo publicado
            continue
        linhas.append({"concurso": c["concurso"], "data": c["data"],
                       "acertos": c["acertos"], "premio": c["premio"]})
    if not linhas:
        raise RuntimeError("Nenhum concurso real conferido ainda.")

    contagem = Counter(x["acertos"] for x in linhas)
    premiados = [x for x in linhas if x["acertos"] >= 11]
    return {
        "linhas": linhas,
        "total": len(linhas),
        "media": sum(x["acertos"] for x in linhas) / len(linhas),
        "melhor": max(x["acertos"] for x in linhas),
        "premiados": len(premiados),
        "premios_total": sum(x["premio"] for x in premiados),
        "distribuicao": dict(sorted(contagem.items())),
        "desde": linhas[0]["data"],
        "ate": linhas[-1]["data"],
    }



def placar() -> list[tuple[str, str]]:
    d = dados_placar()
    pct = d["premiados"] / d["total"] * 100
    total = 4

    capa = _pag(f"""
<div class="pad">
  {_topo("Placar aberto", f"1 / {total}")}
  <div class="painel forte" style="padding:40px">
    <span class="chip-tag">Atualizado em {d['ate']}</span>
    <div class="titulo" style="margin-top:26px">Placar<br><span class="destaque">aberto</span></div>
    <div class="txt" style="margin-top:20px">Todos os <b style="color:#fff">{d['total']} jogos</b> publicados desde {d['desde']},
    conferidos um a um — inclusive os ruins.</div>
  </div>
  <div class="cresce" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px">
    <div class="painel forte kpi-g" style="display:flex;flex-direction:column;justify-content:center">
      <div class="v destaque">{d['premiados']}</div><div class="r">vezes<br>premiado<br>(11+ acertos)</div></div>
    <div class="painel kpi-g" style="display:flex;flex-direction:column;justify-content:center">
      <div class="v">{d['melhor']}</div><div class="r">melhor<br>marca<br>em 15</div></div>
    <div class="painel kpi-g" style="display:flex;flex-direction:column;justify-content:center">
      <div class="v">{_n(d['media'], 1)}</div><div class="r">acertos<br>em média<br>por jogo</div></div>
  </div>
  {_base("Arraste para ver jogo a jogo →")}
</div>""")

    ultimos = d["linhas"][-30:]
    celulas = "".join(
        f'<div style="text-align:center"><div class="bola centro {"hit" if x["acertos"] >= 11 else ""}" '
        f'style="--b:104px">{x["acertos"]}</div><div style="font-size:18px;color:{E["texto3"]};'
        f'margin-top:8px;font-weight:700">{x["concurso"]}</div></div>'
        for x in ultimos)
    jogo_a_jogo = _pag(f"""
<div class="pad">
  {_topo("Jogo a jogo", f"2 / {total}")}
  <div class="painel" style="display:flex;justify-content:space-between;align-items:flex-end;gap:20px">
    <div class="titulo2">Últimos {len(ultimos)} <span class="destaque">jogos</span></div>
    <div style="display:flex;gap:22px;font-size:20px;font-weight:700;color:{E['texto2']};padding-bottom:8px">
      <span style="display:flex;align-items:center;gap:8px"><span class="bola hit" style="--b:24px"></span>Premiado</span>
      <span style="display:flex;align-items:center;gap:8px"><span class="bola" style="--b:24px"></span>Não premiado</span>
    </div>
  </div>
  <div class="painel cresce" style="justify-content:center">
    <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:22px 8px">{celulas}</div>
    <div class="rotulo" style="text-align:center;margin-top:24px">Acertos em 15 · número do concurso embaixo</div>
  </div>
  {_base()}
</div>""")

    maior = max(d["distribuicao"].values())
    barras = "".join(f"""
<div style="display:flex;align-items:center;gap:20px">
  <div class="bola {'hit' if a >= 11 else ''}" style="--b:72px">{a}</div>
  <div style="flex:1;height:56px;background:#0F1A0E;border-radius:12px;overflow:hidden">
    <div style="height:100%;width:{q / maior * 100:.1f}%;border-radius:12px;
      background:{E['destaque'] if a >= 11 else '#3A5530'}"></div></div>
  <div style="width:76px;text-align:right;font-size:40px;font-weight:800;font-variant-numeric:tabular-nums">{q}</div>
</div>""" for a, q in sorted(d["distribuicao"].items(), reverse=True))
    distribuicao = _pag(f"""
<div class="pad">
  {_topo("Distribuição", f"3 / {total}")}
  <div class="painel"><div class="titulo2">Quantas vezes fez<br><span class="destaque">cada pontuação</span></div></div>
  <div class="painel cresce" style="justify-content:space-evenly">{barras}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
    <div class="painel forte kpi-g"><div class="v destaque" style="font-size:84px">{_n(pct, 0)}%</div><div class="r">dos jogos premiados</div></div>
    <div class="painel kpi-g"><div class="v" style="font-size:78px">{formatar_reais(d['premios_total'])}</div><div class="r">em prêmios (1 aposta)</div></div>
  </div>
  {_base()}
</div>""")

    transparencia = _pag(f"""
<div class="pad">
  {_topo("Leia com atenção", f"4 / {total}")}
  <div class="painel forte" style="padding:40px">
    <div class="titulo2">O que este placar<br><span class="destaque">quer dizer</span></div>
  </div>
  <div class="cresce" style="display:grid;grid-template-columns:1fr 1fr;gap:18px">
    <div class="painel kpi-g" style="display:flex;flex-direction:column;justify-content:center">
      <div class="v destaque">{_n(d['media'])}</div><div class="r">média do<br>Radar 15</div></div>
    <div class="painel kpi-g" style="display:flex;flex-direction:column;justify-content:center">
      <div class="v">9,00</div><div class="r">média matemática de<br>qualquer jogo</div></div>
  </div>
  <div class="painel" style="padding:30px">
    <div style="font-size:29px;line-height:1.4;color:{E['texto2']}">O Radar 15 organiza o histórico e mostra tudo em público,
    mas <b style="color:#fff">nenhuma análise aumenta a chance de ganhar</b> — cada sorteio é independente.</div>
  </div>
  <div class="painel" style="padding:20px 26px"><div style="font-size:18px;color:{E['texto3']};line-height:1.4">{pecas.AVISO_LONGO}</div></div>
  <div class="faixa"><span>Siga {pecas.PERFIL}</span><span>+18 · Jogue com responsabilidade</span></div>
</div>""")

    return [("1-capa", capa), ("2-jogo-a-jogo", jogo_a_jogo),
            ("3-distribuicao", distribuicao), ("4-transparencia", transparencia)]


# ---------------------------------------------------------------------------
# GERAÇÃO E PUBLICAÇÃO
# ---------------------------------------------------------------------------

POSTS = {"como-funciona": como_funciona, "placar": placar}

LEGENDAS = {
    "como-funciona": (
        "📌 COMECE POR AQUI\n\n"
        "O Radar 15 publica um jogo grátis da Lotofácil ANTES de cada sorteio "
        "e confere o resultado logo DEPOIS — dê no que der.\n\n"
        "Arraste para ver como o jogo é montado e quando sai.\n\n"
        "Siga @radar15br e ative as notificações para receber o jogo do dia."
    ),
    "placar": (
        "📊 PLACAR ABERTO — todos os jogos que publicamos, conferidos um a um.\n\n"
        "Sem esconder dia ruim: é assim que dá para confiar no que você vê aqui.\n\n"
        "Salve este post e acompanhe o histórico."
    ),
}


def gerar(nome: str) -> list[str]:
    paginas = [(n, html, L, A, PASTA / nome / f"{n}.png") for n, html in POSTS[nome]()]
    pecas.renderizar(paginas)
    return [str(PASTA / nome / f"{n}.jpg") for n, *_ in paginas]


def publicar(nome: str, simular: bool = False) -> dict[str, Any]:
    import shutil
    import time

    from src import publicar as pub
    from src.legendas import AVISO_LEGENDA, _hashtags

    arquivos = gerar(nome)
    destino = pub.PASTA_SITE / "fixados" / nome
    destino.mkdir(parents=True, exist_ok=True)
    for a in arquivos:
        shutil.copy2(a, destino)
    return {"arquivos": arquivos, "legenda": f"{LEGENDAS[nome]}\n\n{AVISO_LEGENDA}\n\n{_hashtags('prova_social')}",
            "urls": [f"{pub.URL_BASE}/fixados/{nome}/{a.rsplit('/', 1)[-1]}" for a in arquivos]}


def postar(nome: str, simular: bool = False) -> str:
    """Publica o carrossel no Instagram (as imagens precisam já estar no site)."""
    import time

    from src import publicar as pub
    from src.legendas import AVISO_LEGENDA, _hashtags

    urls = [f"{pub.URL_BASE}/fixados/{nome}/{n}.jpg" for n, _ in POSTS[nome]()]
    if not simular and not pub.esperar_site(urls[0]):
        raise pub.PublicacaoError("Imagens dos posts fixados ainda não estão no ar.")
    filhos = [pub._ig_post(f"{pub.IG_USER_ID}/media", {"image_url": u, "is_carousel_item": "true"}, simular)["id"]
              for u in urls]
    pai = pub._ig_post(f"{pub.IG_USER_ID}/media", {
        "media_type": "CAROUSEL", "children": ",".join(filhos),
        "caption": f"{LEGENDAS[nome]}\n\n{AVISO_LEGENDA}\n\n{_hashtags('prova_social')}",
    }, simular)["id"]
    if not simular:
        time.sleep(10)
    return pub._ig_post(f"{pub.IG_USER_ID}/media_publish", {"creation_id": pai}, simular)["id"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Posts fixados do perfil")
    parser.add_argument("--etapa", choices=["gerar", "postar"], default="gerar")
    parser.add_argument("--post", choices=[*POSTS, "todos"], default="todos")
    parser.add_argument("--simular", action="store_true")
    args = parser.parse_args()
    nomes = list(POSTS) if args.post == "todos" else [args.post]
    for nome in nomes:
        if args.etapa == "gerar":
            print(json.dumps(publicar(nome), ensure_ascii=False)[:300])
        else:
            print(f"{nome}: publicado -> {postar(nome, args.simular)}")
