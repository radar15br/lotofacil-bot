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


def _pag(corpo: str) -> str:
    extra = f"""
<style>
.marca {{ display:flex; align-items:center; gap:18px; }}
.marca .nome {{ font-size:46px; font-weight:800; font-style:italic; letter-spacing:-.02em; }}
.passo {{ display:flex; gap:26px; align-items:flex-start; }}
.passo .num {{
  flex:0 0 74px; height:74px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  background:{E['chip_alto_tint']}; border:2px solid {E['destaque']}; color:{E['destaque']};
  font-size:36px; font-weight:800;
}}
.passo h3 {{ font-size:40px; }}
.passo p {{ font-size:29px; color:{E['texto2']}; line-height:1.38; margin-top:8px; }}
.grade-res {{ display:grid; grid-template-columns:repeat(6,1fr); gap:16px; }}
.res {{
  border-radius:18px; padding:24px 6px 18px; text-align:center;
  background:{E['superficie']}; border:1px solid {E['borda']};
}}
.res .a {{ font-size:62px; font-weight:800; line-height:1; font-variant-numeric:tabular-nums; }}
.res .c {{ font-size:20px; color:{E['texto3']}; margin-top:6px; font-variant-numeric:tabular-nums; }}
.res.premio {{ background:{E['chip_alto_tint']}; border:2px solid {E['destaque']}; }}
.res.premio .a {{ color:{E['destaque']}; }}
.barra {{ display:flex; align-items:center; gap:18px; }}
.barra .r {{ width:150px; font-size:28px; font-weight:700; text-align:right; color:{E['texto2']}; }}
.barra .t {{ flex:1; height:60px; background:#0F1A0E; border-radius:10px; overflow:hidden; }}
.barra .f {{ height:100%; background:{E['texto3']}; border-radius:10px; }}
.barra .f.p {{ background:{E['destaque']}; }}
.barra .q {{ width:90px; font-size:28px; font-weight:800; font-variant-numeric:tabular-nums; }}
</style>"""
    return pecas._pagina(E, L, A, corpo).replace("</head>", extra + "</head>")


def _marca(tamanho: int = 92) -> str:
    return (f'<div class="marca">{pecas._radar_svg(E["destaque"], tamanho)}'
            f'<div class="nome">RADAR <span class="destaque">15</span></div></div>')


def _radar_fundo() -> str:
    """Radar grande e apagado no canto — dá profundidade às capas."""
    return (f'<div style="position:absolute;right:-170px;top:250px;opacity:.22;pointer-events:none">'
            f'{pecas._radar_svg(E["destaque"], 640)}</div>')


def _rodape() -> str:
    return (f'<div class="rodape assina"><span>{pecas.AVISO_CURTO}</span>'
            f'<span class="perfil">{pecas.PERFIL}</span></div>')


# ---------------------------------------------------------------------------
# COMO FUNCIONA
# ---------------------------------------------------------------------------


def como_funciona() -> list[tuple[str, str]]:
    capa = _pag(f"""
<div class="pad" style="position:relative">
  {_radar_fundo()}
  {_marca()}
  <div class="corpo" style="justify-content:center;position:relative">
    <div>
      <div class="tag"><span class="ponto"></span>Comece por aqui</div>
      <h1 style="margin-top:34px;font-size:104px">Como funciona<br>o <span class="destaque">Radar 15</span></h1>
      <p class="sub" style="margin-top:30px;font-size:36px">
        Um jogo grátis da Lotofácil antes de cada sorteio.<br>
        O resultado conferido logo depois.
      </p>
      <p class="mini" style="margin-top:44px;font-size:27px">Arraste para entender &rarr;</p>
    </div>
  </div>
  {_rodape()}
</div>""")

    passos = [
        ("1", "Analisamos o histórico",
         "Todos os concursos da Lotofácil desde 2003, direto da base oficial da Caixa."),
        ("2", "Montamos o jogo do dia",
         "15 dezenas com o equilíbrio mais comum nos sorteios: pares e ímpares, soma, moldura e miolo."),
        ("3", "Publicamos ANTES do sorteio",
         "O jogo sai no perfil antes da Caixa sortear. Sem editar depois."),
        ("4", "Conferimos DEPOIS, sempre",
         "Logo após o sorteio sai o Reel com quantos acertos o jogo fez — dê no que der."),
    ]
    itens = "".join(
        f'<div class="passo"><div class="num">{n}</div><div><h3>{t}</h3><p>{d}</p></div></div>'
        for n, t, d in passos
    )
    metodo = _pag(f"""
<div class="pad">
  <h2>Quatro passos,<br><span class="destaque">todo dia</span></h2>
  <div class="corpo" style="margin-top:40px;justify-content:space-evenly">{itens}</div>
  {_rodape()}
</div>""")

    placar = _pag(f"""
<div class="pad">
  <div class="corpo" style="justify-content:center">
    <div>
      <div class="tag"><span class="ponto"></span>Nosso compromisso</div>
      <h2 style="margin-top:30px;font-size:76px">Placar aberto.<br><span class="destaque">Sem esconder dia ruim.</span></h2>
      <div class="cartao" style="margin-top:40px">
        <p class="sub" style="font-size:32px">
          Qualquer perfil parece acertar se só mostrar os dias bons.
          Aqui todo jogo publicado é conferido em público — e o histórico
          completo fica no post fixado <b class="destaque">Placar</b>.
        </p>
      </div>
      <div class="cartao" style="margin-top:20px">
        <p class="mini" style="font-size:26px">
          Transparência: a média matemática de acertos de qualquer jogo de 15 dezenas
          é <b>9,00</b>. A análise mostra padrões do histórico —
          <b>não aumenta a chance de ganhar</b>.
        </p>
      </div>
    </div>
  </div>
  {_rodape()}
</div>""")

    horarios = _pag(f"""
<div class="pad">
  <h2>Quando <span class="destaque">sai</span></h2>
  <div class="corpo" style="margin-top:40px;justify-content:space-evenly">
    <div class="cartao">
      <h3 class="destaque" style="font-size:40px">Segunda a sexta</h3>
      <p class="sub" style="margin-top:12px">Sorteio às 21h · resultado + próximo jogo logo depois</p>
    </div>
    <div class="cartao">
      <h3 class="destaque" style="font-size:40px">Domingo</h3>
      <p class="sub" style="margin-top:12px">Sorteio às 11h · resultado + próximo jogo logo depois</p>
    </div>
    <div class="cartao">
      <h3 style="font-size:40px">Ative as notificações</h3>
      <p class="sub" style="margin-top:12px">Toque no sininho do perfil para receber o jogo assim que ele sair.</p>
    </div>
  </div>
  {_rodape()}
</div>""")

    cta = _pag(f"""
<div class="pad">
  <div class="corpo" style="justify-content:center;align-items:center;text-align:center">
    <div>
      {_marca(120).replace('class="marca"', 'class="marca" style="justify-content:center"')}
      <h1 style="margin-top:44px;font-size:84px">Siga e receba<br><span class="destaque">o jogo de graça</span></h1>
      <div class="cartao" style="margin-top:44px">
        <h3 class="destaque" style="font-size:52px">{pecas.PERFIL}</h3>
        <h3 style="margin-top:10px">Siga &middot; Salve &middot; Compartilhe</h3>
      </div>
      <div class="cartao" style="margin-top:22px">
        <p class="mini" style="font-size:24px">{pecas.AVISO_LONGO}</p>
      </div>
    </div>
  </div>
</div>""")

    return [("1-capa", capa), ("2-metodo", metodo), ("3-placar-aberto", placar),
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

    capa = _pag(f"""
<div class="pad" style="position:relative">
  {_radar_fundo()}
  {_marca()}
  <div class="corpo" style="justify-content:center;position:relative">
    <div>
      <div class="tag"><span class="ponto"></span>Atualizado em {d['ate']}</div>
      <h1 style="margin-top:30px;font-size:100px">Placar<br><span class="destaque">aberto</span></h1>
      <p class="sub" style="margin-top:22px;font-size:34px">
        Todos os {d['total']} jogos publicados desde {d['desde']},<br>conferidos um a um.
      </p>
      <div class="cartao" style="margin-top:40px">
        <div class="kpis">
          <div class="kpi"><div class="v destaque">{d['premiados']}</div><div class="r">vezes com 11+<br>acertos (premiado)</div></div>
          <div class="kpi"><div class="v">{d['melhor']}</div><div class="r">melhor marca<br>em 15</div></div>
          <div class="kpi"><div class="v">{_n(d['media'])}</div><div class="r">acertos<br>em média</div></div>
        </div>
      </div>
      <p class="mini" style="margin-top:36px;font-size:27px">Arraste para ver jogo a jogo &rarr;</p>
    </div>
  </div>
  {_rodape()}
</div>""")

    ultimos = d["linhas"][-30:]
    celulas = "".join(
        f'<div class="res{" premio" if x["acertos"] >= 11 else ""}">'
        f'<div class="a">{x["acertos"]}</div><div class="c">{x["concurso"]}</div></div>'
        for x in ultimos
    )
    jogo_a_jogo = _pag(f"""
<div class="pad">
  <h2>Jogo a jogo</h2>
  <p class="mini" style="margin-top:10px;font-size:25px">
    Acertos dos últimos {len(ultimos)} jogos publicados · número do concurso embaixo ·
    <span class="destaque">em destaque, premiados (11+)</span>
  </p>
  <div class="corpo" style="margin-top:34px;justify-content:center">
    <div class="grade-res">{celulas}</div>
  </div>
  {_rodape()}
</div>""")

    maior = max(d["distribuicao"].values())
    barras = "".join(
        f'<div class="barra"><div class="r">{a} acertos</div><div class="t">'
        f'<div class="f{" p" if a >= 11 else ""}" style="width:{q / maior * 100:.1f}%"></div></div>'
        f'<div class="q">{q}</div></div>'
        for a, q in sorted(d["distribuicao"].items(), reverse=True)
    )
    distribuicao = _pag(f"""
<div class="pad">
  <h2>Como os acertos<br><span class="destaque">se distribuem</span></h2>
  <div class="corpo" style="margin-top:40px">
    <div style="display:flex;flex-direction:column;gap:28px">{barras}</div>
    <div class="cartao">
      <div class="kpis">
        <div class="kpi"><div class="v destaque">{_n(pct, 0)}%</div><div class="r">dos jogos<br>premiados</div></div>
        <div class="kpi"><div class="v">{formatar_reais(d['premios_total'])}</div><div class="r">em prêmios<br>somados (1 aposta)</div></div>
      </div>
    </div>
  </div>
  {_rodape()}
</div>""")

    transparencia = _pag(f"""
<div class="pad">
  <div class="corpo" style="justify-content:center">
    <div>
      <div class="tag"><span class="ponto"></span>Leia com atenção</div>
      <h2 style="margin-top:28px">O que este placar<br><span class="destaque2">quer dizer</span></h2>
      <div class="cartao" style="margin-top:34px">
        <p class="sub" style="font-size:30px">
          Nossa média é <b>{_n(d['media'])}</b> acertos. A média matemática de
          <b>qualquer</b> jogo de 15 dezenas é <b>9,00</b>. Ou seja: o Radar 15 organiza
          o histórico e mostra tudo em público, mas <b>nenhuma análise aumenta a chance
          de ganhar</b> — cada sorteio é independente.
        </p>
      </div>
      <div class="cartao" style="margin-top:20px">
        <p class="mini" style="font-size:25px">{pecas.AVISO_LONGO}</p>
      </div>
    </div>
  </div>
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
