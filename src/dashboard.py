"""
ETAPA 2B — DASHBOARD HTML DA ANÁLISE ESTATÍSTICA
=================================================

Gera um arquivo HTML único (sem internet, sem instalar nada) com os gráficos
da análise: frequência, mapa do volante, soma, paridade, repetição e atraso.
Tem filtro de janela (histórico completo / últimos 1000 / 500 / 100 concursos)
e modo claro/escuro.

Como rodar:
    python -m src.dashboard
    python -m src.dashboard --saida saidas/dashboard.html
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from src import analise as an
from src.coleta import carregar_base

JANELAS = [
    ("completo", None, "Histórico completo"),
    ("1000", 1000, "Últimos 1.000"),
    ("500", 500, "Últimos 500"),
    ("100", 100, "Últimos 100"),
]


def _dados_da_janela(base: list[dict], n: int | None) -> dict[str, Any]:
    amostra = base if not n else base[-n:]
    total = len(amostra)

    freq = an.frequencia(base, n)
    par = an.paridade(base, n)
    som = an.soma_dezenas(base, n)
    rep = an.repeticao_concurso_anterior(base, n)
    geo = an.geografia(base, n)
    teste = an.teste_aleatoriedade(base, n)

    # Histograma da soma em faixas de 10
    somas = [sum(c["dezenas"]) for c in amostra]
    faixas = Counter((s // 10) * 10 for s in somas)

    return {
        "total": total,
        "primeiro": amostra[0]["concurso"],
        "ultimo": amostra[-1]["concurso"],
        "data_ultimo": amostra[-1]["data"],
        "frequencia": [
            {"dezena": d, "vezes": freq[d]["vezes"], "pct": freq[d]["pct"],
             "desvio": round(freq[d]["pct"] - 60.0, 2)}
            for d in range(1, 26)
        ],
        "paridade": [
            {"pares": k, "vezes": v, "pct": round(100 * v / total, 1)}
            for k, v in sorted(Counter(
                sum(1 for d in c["dezenas"] if d % 2 == 0) for c in amostra
            ).items())
        ],
        "soma": {
            "media": som["media"], "mediana": som["mediana"],
            "faixa": som["faixa_central_80pct"], "min": som["minimo"], "max": som["maximo"],
            "histograma": [{"faixa": k, "vezes": v} for k, v in sorted(faixas.items())],
        },
        "repeticao": [
            {"qtd": int(k.split()[0]), "vezes": v["vezes"], "pct": v["pct"]}
            for k, v in rep["distribuicao"].items()
        ],
        "repeticao_media": rep["resumo"]["media"],
        "moldura": geo["moldura"]["media_por_sorteio"],
        "miolo": geo["miolo"]["media_por_sorteio"],
        "teste": teste,
    }


def montar_dados(base: list[dict] | None = None) -> dict[str, Any]:
    base = base or carregar_base()
    if not base:
        raise RuntimeError("Base vazia. Rode a Etapa 1 antes.")

    atr = an.atrasos(base)
    perfil = an.perfil_alvo(base)

    return {
        "janelas": {chave: _dados_da_janela(base, n) for chave, n, _ in JANELAS},
        # lista (e não dicionário) para preservar a ordem no navegador
        "rotulos": [{"chave": chave, "rotulo": rotulo} for chave, _, rotulo in JANELAS],
        "atrasos": [
            {"dezena": d, "atual": atr[d]["atraso_atual"],
             "recorde": atr[d]["maior_atraso_historico"]}
            for d in range(1, 26)
        ],
        "perfil": perfil,
        "ultimo_sorteio": base[-1],
    }


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lotofácil — Painel Estatístico</title>
<style>
:root {
  color-scheme: light;
  --surface-0: #f5f5f3;
  --surface-1: #fcfcfb;
  --border:    #e3e2dd;
  --text-primary:   #0b0b0b;
  --text-secondary: #52514e;
  --text-muted:     #8a887f;
  --series-1: #2a78d6;
  --seq-100: #cde2fb; --seq-250: #86b6ef; --seq-400: #3987e5;
  --seq-550: #1c5cab; --seq-700: #0d366b;
  --neutral-mid: #f0efec;
  --pos: #2a78d6;
  --neg: #e34948;
  --grid: #e8e7e2;
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface-0: #121211;
  --surface-1: #1a1a19;
  --border:    #333331;
  --text-primary:   #ffffff;
  --text-secondary: #c3c2b7;
  --text-muted:     #8a887f;
  --series-1: #3987e5;
  --seq-100: #184f95; --seq-250: #256abf; --seq-400: #3987e5;
  --seq-550: #86b6ef; --seq-700: #cde2fb;
  --neutral-mid: #383835;
  --pos: #3987e5;
  --neg: #e66767;
  --grid: #2b2b29;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 24px;
  background: var(--surface-0); color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 14px; line-height: 1.5;
}
.wrap { max-width: 1160px; margin: 0 auto; }
header { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; flex-wrap:wrap; margin-bottom:20px; }
h1 { font-size: 22px; margin: 0 0 4px; letter-spacing: -0.01em; }
.sub { color: var(--text-secondary); font-size: 13px; margin:0; }
.controls { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
button {
  font: inherit; padding: 7px 13px; border-radius: 8px; cursor: pointer;
  border: 1px solid var(--border); background: var(--surface-1); color: var(--text-secondary);
}
button:hover { border-color: var(--text-muted); }
button[aria-pressed="true"] { background: var(--series-1); border-color: var(--series-1); color: #fff; font-weight: 600; }
.cards { display:grid; grid-template-columns: repeat(auto-fit, minmax(168px,1fr)); gap:12px; margin-bottom:18px; }
.card, .panel {
  background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 12px; padding: 16px;
}
.card .rot { font-size: 11.5px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .06em; }
.card .val { font-size: 27px; font-weight: 650; letter-spacing: -0.02em; margin-top: 3px; }
.card .obs { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
.grid2 { display:grid; grid-template-columns: repeat(auto-fit, minmax(430px,1fr)); gap:14px; margin-bottom:14px; }
h2 { font-size: 15.5px; margin: 0 0 3px; letter-spacing: -0.01em; }
.h2sub { font-size: 12.5px; color: var(--text-secondary); margin: 0 0 14px; }
svg { display:block; width:100%; height:auto; overflow: visible; }
.axis text { fill: var(--text-muted); font-size: 10.5px; }
.axis line, .grid line { stroke: var(--grid); stroke-width: 1; }
.reflinha { stroke: var(--text-muted); stroke-width: 1.5; stroke-dasharray: 4 3; }
.vol { display:grid; grid-template-columns: repeat(5, 1fr); gap: 6px; max-width: 340px; margin: 4px auto 10px; }
.bola { aspect-ratio: 1; border-radius: 10px; display:flex; flex-direction:column;
        align-items:center; justify-content:center; font-weight:650; font-size:16px; }
.bola small { font-weight: 450; font-size: 10.5px; opacity: .85; }
.legenda { display:flex; gap:14px; align-items:center; justify-content:center;
           font-size:11.5px; color:var(--text-secondary); flex-wrap:wrap; margin-top:6px; }
.chip { display:inline-flex; align-items:center; gap:6px; }
.sw { width:11px; height:11px; border-radius:3px; display:inline-block; }
.aviso { background: var(--surface-1); border: 1px solid var(--border); border-left: 3px solid var(--seq-400);
         border-radius: 10px; padding: 14px 16px; font-size: 12.8px; color: var(--text-secondary); margin-top: 6px; }
table { width:100%; border-collapse: collapse; font-size: 12.5px; }
th, td { text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--border); }
th:first-child, td:first-child { text-align: left; }
th { color: var(--text-muted); font-weight: 550; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }
.ok  { color: var(--pos); font-weight: 600; }
.alerta { color: var(--neg); font-weight: 600; }
#tip { position: fixed; pointer-events: none; opacity: 0; transition: opacity .1s;
       background: var(--text-primary); color: var(--surface-1); padding: 6px 9px;
       border-radius: 7px; font-size: 12px; white-space: nowrap; z-index: 9; }
details { margin-top: 10px; }
summary { cursor: pointer; font-size: 12.5px; color: var(--text-secondary); }
.rodape { color: var(--text-muted); font-size: 11.5px; text-align:center; margin: 22px 0 4px; }
</style>
</head>
<body>
<div class="wrap">

<header>
  <div>
    <h1>Lotofácil — Painel Estatístico</h1>
    <p class="sub" id="subtitulo"></p>
  </div>
  <div class="controls">
    <span style="font-size:12px;color:var(--text-muted)">Janela:</span>
    <span id="filtros"></span>
    <button id="tema" aria-pressed="false">Modo escuro</button>
  </div>
</header>

<div class="cards" id="cards"></div>

<div class="panel">
  <h2 id="t-freq"></h2>
  <p class="h2sub">Cada dezena deveria sair em 60% dos concursos (15 bolas de 25). As barras mostram quanto cada uma ficou acima ou abaixo disso, em pontos percentuais.</p>
  <div id="c-freq"></div>
</div>

<div class="grid2">
  <div class="panel">
    <h2 id="t-mapa"></h2>
    <p class="h2sub">Desvio de cada dezena em relação aos 60% esperados, na posição real do volante.</p>
    <div id="c-mapa"></div>
    <div class="legenda">
      <span class="chip"><span class="sw" style="background:var(--neg)"></span>abaixo do esperado</span>
      <span class="chip"><span class="sw" style="background:var(--neutral-mid);border:1px solid var(--border)"></span>na média</span>
      <span class="chip"><span class="sw" style="background:var(--pos)"></span>acima do esperado</span>
    </div>
  </div>
  <div class="panel">
    <h2 id="t-atraso"></h2>
    <p class="h2sub">Concursos sem sair até o último resultado. Sempre medido no histórico completo.</p>
    <div id="c-atraso"></div>
  </div>
</div>

<div class="grid2">
  <div class="panel">
    <h2 id="t-soma"></h2>
    <p class="h2sub">Soma das 15 dezenas sorteadas. Mínimo teórico 120, máximo 270.</p>
    <div id="c-soma"></div>
  </div>
  <div class="panel">
    <h2 id="t-par"></h2>
    <p class="h2sub">Quantidade de números pares em cada sorteio.</p>
    <div id="c-par"></div>
  </div>
</div>

<div class="grid2">
  <div class="panel">
    <h2 id="t-rep"></h2>
    <p class="h2sub">Quantas dezenas do concurso anterior reaparecem no concurso seguinte.</p>
    <div id="c-rep"></div>
  </div>
  <div class="panel">
    <h2 id="t-teste"></h2>
    <p class="h2sub">Teste de aderência ao acaso. p-valor acima de 0,05 significa que as diferenças entre dezenas cabem dentro da variação normal.</p>
    <div id="c-teste"></div>
  </div>
</div>

<div class="panel">
  <h2>Perfil-alvo: as regras que o gerador de jogos vai seguir</h2>
  <p class="h2sub">Faixas onde cai a grande maioria dos sorteios reais. Servem para os jogos terem a "cara" de um resultado plausível — não para prever.</p>
  <div id="c-perfil"></div>
</div>

<div class="aviso">
  <strong>Aviso.</strong> Este painel apresenta análise estatística de resultados históricos e
  <strong>não constitui previsão</strong>. Cada sorteio da Lotofácil é independente dos anteriores e todas as
  3.268.760 combinações possíveis de 15 dezenas têm exatamente a mesma probabilidade de serem sorteadas.
  Nenhuma estratégia altera essa probabilidade. Jogue com responsabilidade e apenas o que puder perder.
</div>

<p class="rodape">Gerado automaticamente pelo Lotofácil Bot — Etapa 2</p>
</div>

<div id="tip"></div>

<script>
const DADOS = __DADOS__;
let JANELA = "completo";

const fmt = n => n.toLocaleString("pt-BR");
const fmt1 = n => n.toLocaleString("pt-BR", {minimumFractionDigits:1, maximumFractionDigits:1});
const fmt2 = n => n.toLocaleString("pt-BR", {minimumFractionDigits:2, maximumFractionDigits:2});
const el = id => document.getElementById(id);

/* ---------- tooltip ---------- */
const tip = el("tip");
function ligarTip(no, texto) {
  no.addEventListener("mousemove", e => {
    tip.textContent = texto;
    tip.style.opacity = 1;
    tip.style.left = Math.min(e.clientX + 12, innerWidth - tip.offsetWidth - 8) + "px";
    tip.style.top  = (e.clientY - 34) + "px";
  });
  no.addEventListener("mouseleave", () => tip.style.opacity = 0);
}

/* ---------- helpers de SVG ---------- */
const NS = "http://www.w3.org/2000/svg";
function svg(w, h) {
  const s = document.createElementNS(NS, "svg");
  s.setAttribute("viewBox", `0 0 ${w} ${h}`);
  s.setAttribute("role", "img");
  return s;
}
function no(tag, attrs, pai) {
  const n = document.createElementNS(NS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (pai) pai.appendChild(n);
  return n;
}
/* barra com topo arredondado (4px) ancorada na base */
function barra(pai, x, y, w, h, cor, r = 4) {
  const rr = Math.min(r, w / 2, Math.max(h, 0.01));
  const d = `M${x},${y+h} L${x},${y+rr} Q${x},${y} ${x+rr},${y} L${x+w-rr},${y} Q${x+w},${y} ${x+w},${y+rr} L${x+w},${y+h} Z`;
  return no("path", {d, fill: cor}, pai);
}

/* ---------- 1. frequência: desvio em relação aos 60% esperados ----------
   Barras ancoradas na linha do esperado (60%), não no zero: a pergunta é
   "quanto acima ou abaixo do esperado", então a linha do esperado É a base. */
function grafFrequencia(d) {
  const alvo = el("c-freq"); alvo.innerHTML = "";
  const W = 900, H = 288, ml = 46, mr = 12, mt = 16, mb = 56;
  const s = svg(W, H); alvo.appendChild(s);
  const dados = d.frequencia;
  const lim = Math.max(1, Math.ceil(Math.max(...dados.map(x => Math.abs(x.desvio))) * 1.25));
  const passo = (W - ml - mr) / dados.length;
  const px = i => ml + i * passo;
  const larg = passo - 7;
  const py = v => mt + (H - mt - mb) * (1 - (v + lim) / (2 * lim));
  const base = py(0);

  const g = no("g", {class: "grid"}, s);
  const tick = lim <= 2 ? 0.5 : 1;
  for (let v = -lim; v <= lim + 0.001; v += tick) {
    no("line", {x1: ml, x2: W - mr, y1: py(v), y2: py(v)}, g);
    const t = no("text", {x: ml - 8, y: py(v) + 3.5, "text-anchor": "end"}, s);
    t.setAttribute("class", "axis");
    t.textContent = (v > 0 ? "+" : "") + fmt1(v);
  }
  dados.forEach((x, i) => {
    const acima = x.desvio >= 0;
    const y = acima ? py(x.desvio) : base;
    const h = Math.abs(base - py(x.desvio));
    const b = barra(s, px(i), y, larg, Math.max(h, 1.5), acima ? "var(--pos)" : "var(--neg)");
    if (!acima) b.setAttribute("transform", `rotate(180 ${px(i) + larg / 2} ${base + h / 2})`);
    ligarTip(b, `Dezena ${x.dezena}: saiu ${fmt(x.vezes)} vezes (${fmt2(x.pct)}%) — ${acima ? "+" : ""}${fmt2(x.desvio)} p.p. vs os 60% esperados`);
    const t = no("text", {x: px(i) + larg / 2, y: H - 32, "text-anchor": "middle"}, s);
    t.setAttribute("class", "axis"); t.textContent = x.dezena;
  });
  no("line", {x1: ml, x2: W - mr, y1: base, y2: base, class: "reflinha"}, s);
  const r = no("text", {x: ml, y: H - 8}, s);
  r.setAttribute("class", "axis");
  r.textContent = "linha tracejada = 60%, a frequência esperada pelo acaso · eixo em pontos percentuais";
}

/* ---------- 2. mapa do volante ---------- */
function grafMapa(d) {
  const alvo = el("c-mapa"); alvo.innerHTML = "";
  const div = document.createElement("div"); div.className = "vol"; alvo.appendChild(div);
  const desvios = d.frequencia.map(x => x.desvio);
  const lim = Math.max(...desvios.map(Math.abs)) || 1;
  d.frequencia.forEach(x => {
    const t = x.desvio / lim;                      // -1 .. +1
    const forte = Math.abs(t) > 0.55;
    const cor = t >= 0
      ? `color-mix(in oklab, var(--pos) ${Math.abs(t) * 78 + 8}%, var(--neutral-mid))`
      : `color-mix(in oklab, var(--neg) ${Math.abs(t) * 78 + 8}%, var(--neutral-mid))`;
    const c = document.createElement("div");
    c.className = "bola";
    c.style.background = cor;
    c.style.color = forte ? "#fff" : "var(--text-primary)";
    c.innerHTML = `${x.dezena}<small>${x.desvio >= 0 ? "+" : ""}${fmt1(x.desvio)}</small>`;
    ligarTip(c, `Dezena ${x.dezena}: ${fmt2(x.pct)}% dos concursos (${fmt(x.vezes)} vezes)`);
    div.appendChild(c);
  });
}

/* ---------- 3. atraso ---------- */
function grafAtraso() {
  const alvo = el("c-atraso"); alvo.innerHTML = "";
  const dados = [...DADOS.atrasos].sort((a, b) => b.atual - a.atual).slice(0, 12);
  const W = 440, linha = 24, H = dados.length * linha + 14;
  const s = svg(W, H); alvo.appendChild(s);
  const max = Math.max(...DADOS.atrasos.map(x => x.recorde));
  const ml = 62, esc = v => (W - ml - 60) * (v / max);
  dados.forEach((x, i) => {
    const y = i * linha + 6;
    const r = no("text", {x: ml - 8, y: y + 12, "text-anchor": "end"}, s);
    r.setAttribute("class", "axis"); r.textContent = "dezena " + x.dezena;
    no("rect", {x: ml, y: y + 3, width: Math.max(esc(x.recorde), 2), height: 12, rx: 4,
                fill: "var(--grid)"}, s);
    const b = no("rect", {x: ml, y: y + 3, width: Math.max(esc(x.atual), 2), height: 12, rx: 4,
                fill: "var(--seq-400)"}, s);
    ligarTip(b, `Dezena ${x.dezena}: ${x.atual} concursos sem sair (recorde histórico: ${x.recorde})`);
    const v = no("text", {x: ml + Math.max(esc(x.recorde), 2) + 8, y: y + 13}, s);
    v.setAttribute("class", "axis"); v.textContent = `${x.atual}  (recorde ${x.recorde})`;
  });
}

/* ---------- 4. soma ---------- */
function grafSoma(d) {
  const alvo = el("c-soma"); alvo.innerHTML = "";
  const W = 460, H = 230, ml = 34, mr = 8, mt = 12, mb = 26;
  const s = svg(W, H); alvo.appendChild(s);
  const h = d.soma.histograma, max = Math.max(...h.map(x => x.vezes));
  const larg = (W - ml - mr) / h.length - 3;
  const px = i => ml + i * ((W - ml - mr) / h.length);
  const py = v => mt + (H - mt - mb) * (1 - v / max);
  const [f0, f1] = d.soma.faixa;
  h.forEach((x, i) => {
    const dentro = x.faixa + 9 >= f0 && x.faixa <= f1;
    const b = barra(s, px(i), py(x.vezes), larg, py(0) - py(x.vezes),
                    dentro ? "var(--seq-400)" : "var(--seq-100)");
    ligarTip(b, `Soma ${x.faixa}–${x.faixa + 9}: ${fmt(x.vezes)} sorteios (${fmt1(100 * x.vezes / d.total)}%)`);
    if (i % 2 === 0) {
      const t = no("text", {x: px(i) + larg / 2, y: H - 8, "text-anchor": "middle"}, s);
      t.setAttribute("class", "axis"); t.textContent = x.faixa;
    }
  });
  no("line", {x1: ml, x2: W - mr, y1: py(0), y2: py(0), stroke: "var(--grid)"}, s);
}

/* ---------- 5. paridade / 6. repetição (barras simples) ---------- */
function barrasSimples(idAlvo, dados, rotulo, texto) {
  const alvo = el(idAlvo); alvo.innerHTML = "";
  const W = 460, H = 230, ml = 30, mr = 8, mt = 14, mb = 30;
  const s = svg(W, H); alvo.appendChild(s);
  const max = Math.max(...dados.map(x => x.pct));
  const larg = (W - ml - mr) / dados.length - 8;
  const px = i => ml + i * ((W - ml - mr) / dados.length);
  const py = v => mt + (H - mt - mb) * (1 - v / max);
  dados.forEach((x, i) => {
    const b = barra(s, px(i), py(x.pct), larg, py(0) - py(x.pct),
                    x.pct >= max * 0.55 ? "var(--seq-400)" : "var(--seq-250)");
    ligarTip(b, texto(x));
    const t = no("text", {x: px(i) + larg / 2, y: H - 10, "text-anchor": "middle"}, s);
    t.setAttribute("class", "axis"); t.textContent = rotulo(x);
    if (x.pct >= max * 0.5) {
      const v = no("text", {x: px(i) + larg / 2, y: py(x.pct) - 6, "text-anchor": "middle"}, s);
      v.setAttribute("class", "axis"); v.textContent = fmt1(x.pct) + "%";
    }
  });
  no("line", {x1: ml, x2: W - mr, y1: py(0), y2: py(0), stroke: "var(--grid)"}, s);
}

/* ---------- 7. teste de aleatoriedade ---------- */
function painelTeste(d) {
  const alvo = el("c-teste");
  const t = d.teste;
  const ok = t.compativel_com_acaso;
  alvo.innerHTML = `
    <table>
      <tr><th>Concursos testados</th><td>${fmt(t.concursos_testados)}</td></tr>
      <tr><th>Estatística (24 g.l.)</th><td>${fmt2(t.estatistica)}</td></tr>
      <tr><th>p-valor</th><td class="${ok ? "ok" : "alerta"}">${t.p_valor < 0.001 ? "menor que 0,001" : t.p_valor.toLocaleString("pt-BR", {minimumFractionDigits:4, maximumFractionDigits:4})}</td></tr>
      <tr><th>Conclusão</th><td class="${ok ? "ok" : "alerta"}">${ok ? "compatível com o acaso" : "desvio além do acaso"}</td></tr>
    </table>
    <details><summary>O que isso quer dizer, na prática</summary>
      <p style="font-size:12.5px;color:var(--text-secondary)">${t.leitura}
      Mesmo quando aparece desvio, a diferença é da ordem de 2 pontos percentuais sobre uma base de 60% —
      pequena demais para mudar o resultado esperado de qualquer aposta, e ela não se mantém estável
      ao longo das diferentes épocas do sorteio. As dezenas "quentes" servem como narrativa de conteúdo,
      não como vantagem estatística.</p>
    </details>`;
}

/* ---------- 8. perfil-alvo ---------- */
function painelPerfil() {
  const p = DADOS.perfil;
  el("c-perfil").innerHTML = `
    <table>
      <tr><th>Critério</th><th>Faixa-alvo</th><th>Média histórica</th></tr>
      <tr><td>Soma das 15 dezenas</td><td>${p.soma_dezenas.faixa[0]} a ${p.soma_dezenas.faixa[1]}</td><td>${fmt2(p.soma_dezenas.media)}</td></tr>
      <tr><td>Números pares</td><td>${p.pares.faixa[0]} a ${p.pares.faixa[1]}</td><td>${fmt2(p.pares.media)}</td></tr>
      <tr><td>Números primos</td><td>${p.primos.faixa[0]} a ${p.primos.faixa[1]}</td><td>${fmt2(p.primos.media)}</td></tr>
      <tr><td>Repetidas do concurso anterior</td><td>${p.repetidas_do_anterior.faixa[0]} a ${p.repetidas_do_anterior.faixa[1]}</td><td>${fmt2(p.repetidas_do_anterior.media)}</td></tr>
      <tr><td>Dezenas da moldura (borda do volante)</td><td>8 a 11</td><td>${fmt2(p.moldura.media)}</td></tr>
      <tr><td>Dezenas do miolo (centro do volante)</td><td>4 a 7</td><td>${fmt2(p.miolo.media)}</td></tr>
    </table>`;
}

/* ---------- cartões ---------- */
function cards(d) {
  const u = DADOS.ultimo_sorteio;
  el("cards").innerHTML = [
    ["Concursos analisados", fmt(d.total), `do ${fmt(d.primeiro)} ao ${fmt(d.ultimo)}`],
    ["Soma típica", `${d.soma.faixa[0]}–${d.soma.faixa[1]}`, `média ${fmt2(d.soma.media)} · 80% dos sorteios`],
    ["Repetem do anterior", fmt2(d.repeticao_media), "dezenas, em média"],
    ["Moldura x miolo", `${fmt1(d.moldura)} x ${fmt1(d.miolo)}`, "borda vence sempre (16 vs 9 dezenas)"],
    ["Último resultado", u.concurso, u.dezenas.join(" · ")],
  ].map(([r, v, o]) => `<div class="card"><div class="rot">${r}</div><div class="val">${v}</div><div class="obs">${o}</div></div>`).join("");
}

/* ---------- títulos que entregam a conclusão ---------- */
function titulos(d) {
  const f = [...d.frequencia].sort((a, b) => b.pct - a.pct);
  const par = [...d.paridade].sort((a, b) => b.pct - a.pct)[0];
  const rep = [...d.repeticao].sort((a, b) => b.pct - a.pct)[0];
  const atr = [...DADOS.atrasos].sort((a, b) => b.atual - a.atual)[0];
  const ok = d.teste.compativel_com_acaso;

  el("subtitulo").textContent =
    `${fmt(d.total)} concursos · último: ${fmt(d.ultimo)} em ${d.data_ultimo.split("-").reverse().join("/")}`;
  el("t-freq").textContent =
    `Dezena ${f[0].dezena} lidera com ${fmt2(f[0].pct)}%, contra ${fmt2(f[f.length-1].pct)}% da dezena ${f[f.length-1].dezena} — diferença de ${fmt1(f[0].pct - f[f.length-1].pct)} pontos`;
  el("t-mapa").textContent = "O volante não tem região privilegiada — os desvios se espalham sem padrão";
  el("t-atraso").textContent = `Dezena ${atr.dezena} é a mais atrasada: ${atr.atual} concursos sem sair`;
  el("t-soma").textContent = `8 em cada 10 sorteios somam entre ${d.soma.faixa[0]} e ${d.soma.faixa[1]}`;
  el("t-par").textContent = `${par.pares} pares e ${15 - par.pares} ímpares é a divisão mais comum (${fmt1(par.pct)}% dos sorteios)`;
  el("t-rep").textContent = `${rep.qtd} dezenas se repetem do concurso anterior em ${fmt1(rep.pct)}% das vezes`;
  el("t-teste").textContent = ok
    ? "Nesta janela, as dezenas 'quentes' são efeito do acaso"
    : "Nesta janela há desvio estatístico — mas pequeno demais para virar vantagem";
}

/* ---------- render ---------- */
function render() {
  const d = DADOS.janelas[JANELA];
  titulos(d); cards(d);
  grafFrequencia(d); grafMapa(d); grafAtraso(); grafSoma(d);
  barrasSimples("c-par", d.paridade, x => x.pares,
    x => `${x.pares} pares / ${15 - x.pares} ímpares: ${fmt(x.vezes)} sorteios (${fmt1(x.pct)}%)`);
  barrasSimples("c-rep", d.repeticao, x => x.qtd,
    x => `${x.qtd} dezenas repetidas: ${fmt(x.vezes)} sorteios (${fmt1(x.pct)}%)`);
  painelTeste(d); painelPerfil();
}

/* ---------- filtros e tema ---------- */
el("filtros").innerHTML = DADOS.rotulos
  .map(x => `<button data-j="${x.chave}" aria-pressed="${x.chave === "completo"}">${x.rotulo}</button>`).join(" ");
el("filtros").addEventListener("click", e => {
  const b = e.target.closest("button"); if (!b) return;
  JANELA = b.dataset.j;
  [...el("filtros").querySelectorAll("button")].forEach(x => x.setAttribute("aria-pressed", x === b));
  render();
});
el("tema").addEventListener("click", () => {
  const escuro = document.documentElement.dataset.theme === "dark";
  document.documentElement.dataset.theme = escuro ? "light" : "dark";
  el("tema").textContent = escuro ? "Modo escuro" : "Modo claro";
  el("tema").setAttribute("aria-pressed", !escuro);
  render();
});
if (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches) el("tema").click();
render();
</script>
</body>
</html>
"""


def gerar(saida: str | Path = "saidas/dashboard.html") -> Path:
    dados = montar_dados()
    html = TEMPLATE.replace("__DADOS__", json.dumps(dados, ensure_ascii=False))
    destino = Path(saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    return destino


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera o painel HTML da análise estatística")
    parser.add_argument("--saida", default="saidas/dashboard.html")
    args = parser.parse_args()
    caminho = gerar(args.saida)
    print(f"Painel gerado em {caminho.resolve()}")
