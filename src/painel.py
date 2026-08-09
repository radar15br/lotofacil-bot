"""
ETAPA 8B — PAINEL DE ACOMPANHAMENTO
====================================

Enquanto o painel da Etapa 2 mostra a ESTATÍSTICA DA LOTOFÁCIL, este mostra o
DESEMPENHO DA SUA OPERAÇÃO: como os jogos vêm se saindo, quanto custou, quanto
voltou, qual estilo de legenda engaja mais e o que já foi publicado.

É este arquivo que você abre para decidir o que mudar na estratégia.

Como rodar:
    python -m src.painel
    python -m src.painel --saida saidas/painel.html
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.coleta import RAIZ
from src.desempenho import (
    ARQUIVO_DESEMPENHO, PRECO_APOSTA, carregar_historico, resumo,
)
from src.jogos import QTD_JOGOS
from src.legendas import ARQUIVO_AB, carregar_ab, relatorio_ab
from src.publicar import ARQUIVO_PUBLICACOES

CONCURSOS_NO_GRAFICO = 60


def montar_dados() -> dict[str, Any]:
    historico = sorted(carregar_historico(), key=lambda r: r["concurso"])
    reais = [r for r in historico if not r["simulado"]]
    tem_reais = len(reais) >= 1
    fonte = reais if tem_reais else historico

    recorte = fonte[-CONCURSOS_NO_GRAFICO:]

    todos_acertos = [j["acertos"] for r in fonte for j in r["jogos"]]
    distribuicao = Counter(todos_acertos)

    publicacoes = []
    if ARQUIVO_PUBLICACOES.exists():
        publicacoes = json.loads(ARQUIVO_PUBLICACOES.read_text(encoding="utf-8"))

    return {
        "tem_dados": bool(fonte),
        "usando_simulacao": not tem_reais,
        "resumo_10": resumo(10, incluir_simulados=not tem_reais),
        "resumo_total": resumo(len(fonte) or 1, incluir_simulados=not tem_reais),
        "serie": [
            {
                "concurso": r["concurso"],
                "data": r["data"],
                "melhor": r["melhor"],
                "media": r["media"],
                "premiadas": r["apostas_premiadas"],
                "saldo": r["saldo"],
            }
            for r in recorte
        ],
        "distribuicao": [
            {"acertos": k, "vezes": distribuicao.get(k, 0),
             "pct": round(100 * distribuicao.get(k, 0) / max(len(todos_acertos), 1), 2)}
            for k in range(min(distribuicao or [9]), max(distribuicao or [9]) + 1)
        ],
        "ab": relatorio_ab(),
        "ab_registros": carregar_ab(),
        "publicacoes": publicacoes[-20:],
        "custos": {
            "preco_aposta": PRECO_APOSTA,
            "jogos_por_concurso": QTD_JOGOS,
            "por_concurso": round(PRECO_APOSTA * QTD_JOGOS, 2),
            "por_mes": round(PRECO_APOSTA * QTD_JOGOS * 26, 2),
            "infraestrutura_mes": 0.0,
        },
        "arquivos": {
            "desempenho": str(ARQUIVO_DESEMPENHO),
            "ab": str(ARQUIVO_AB),
        },
    }


TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Radar 15 — Painel da Operação</title>
<style>
:root {
  color-scheme: light;
  --surface-0:#f5f5f3; --surface-1:#fcfcfb; --border:#e3e2dd;
  --text-primary:#0b0b0b; --text-secondary:#52514e; --text-muted:#8a887f;
  --s1:#2a78d6; --s2:#eb6834; --grid:#e8e7e2;
  --pos:#1baf7a; --neg:#e34948;
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface-0:#121211; --surface-1:#1a1a19; --border:#333331;
  --text-primary:#fff; --text-secondary:#c3c2b7; --text-muted:#8a887f;
  --s1:#3987e5; --s2:#d95926; --grid:#2b2b29;
  --pos:#199e70; --neg:#e66767;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--surface-0);color:var(--text-primary);padding:24px;
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  font-size:14px;line-height:1.5}
.wrap{max-width:1120px;margin:0 auto}
header{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:18px}
h1{font-size:22px;letter-spacing:-.01em;margin-bottom:4px}
.sub{color:var(--text-secondary);font-size:13px}
button{font:inherit;padding:7px 13px;border-radius:8px;cursor:pointer;
  border:1px solid var(--border);background:var(--surface-1);color:var(--text-secondary)}
.aviso-sim{background:color-mix(in oklab,var(--s2) 12%,var(--surface-1));
  border:1px solid color-mix(in oklab,var(--s2) 35%,var(--border));
  border-left:3px solid var(--s2);border-radius:10px;padding:12px 16px;
  font-size:13px;margin-bottom:16px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:16px}
.card,.panel{background:var(--surface-1);border:1px solid var(--border);border-radius:12px;padding:16px}
.card .rot{font-size:11.5px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em}
.card .val{font-size:27px;font-weight:650;letter-spacing:-.02em;margin-top:3px}
.card .obs{font-size:12px;color:var(--text-secondary);margin-top:2px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(430px,1fr));gap:14px;margin-bottom:14px}
h2{font-size:15.5px;margin-bottom:3px;letter-spacing:-.01em}
.h2sub{font-size:12.5px;color:var(--text-secondary);margin-bottom:14px}
svg{display:block;width:100%;height:auto;overflow:visible}
.axis text{fill:var(--text-muted);font-size:10.5px}
.grid line{stroke:var(--grid);stroke-width:1}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{text-align:right;padding:7px 8px;border-bottom:1px solid var(--border)}
th:first-child,td:first-child{text-align:left}
th{color:var(--text-muted);font-weight:550;font-size:11px;text-transform:uppercase;letter-spacing:.05em}
.pos{color:var(--pos);font-weight:600}
.neg{color:var(--neg);font-weight:600}
.legenda{display:flex;gap:16px;font-size:12px;color:var(--text-secondary);margin-top:10px}
.chip{display:inline-flex;align-items:center;gap:7px}
.sw{width:14px;height:3px;border-radius:2px;display:inline-block}
#tip{position:fixed;pointer-events:none;opacity:0;transition:opacity .1s;
  background:var(--text-primary);color:var(--surface-1);padding:6px 9px;border-radius:7px;
  font-size:12px;white-space:nowrap;z-index:9}
.vazio{color:var(--text-muted);font-size:13px;padding:8px 0}
.rodape{color:var(--text-muted);font-size:11.5px;text-align:center;margin:22px 0 4px}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div>
    <h1>Radar 15 — Painel da Operação</h1>
    <p class="sub" id="subtitulo"></p>
  </div>
  <button id="tema">Modo escuro</button>
</header>

<div id="aviso-simulacao"></div>
<div class="cards" id="cards"></div>

<div class="panel">
  <h2 id="t-serie"></h2>
  <p class="h2sub">Cada ponto é um concurso. A linha do melhor jogo é o que vira manchete; a da média é o que mede o conjunto.</p>
  <div id="c-serie"></div>
  <div class="legenda">
    <span class="chip"><span class="sw" style="background:var(--s1)"></span>melhor jogo do dia</span>
    <span class="chip"><span class="sw" style="background:var(--s2)"></span>média dos 13 jogos</span>
    <span class="chip"><span class="sw" style="background:var(--grid);height:2px"></span>9,00 = média matemática</span>
  </div>
</div>

<div class="grid2">
  <div class="panel">
    <h2 id="t-dist"></h2>
    <p class="h2sub">Quantas apostas terminaram com cada número de acertos. A faixa premiada começa em 11.</p>
    <div id="c-dist"></div>
  </div>
  <div class="panel">
    <h2>Quanto custa e quanto volta</h2>
    <p class="h2sub">Números reais do período acompanhado, com o rateio de cada concurso.</p>
    <div id="c-custos"></div>
  </div>
</div>

<div class="grid2">
  <div class="panel">
    <h2 id="t-ab"></h2>
    <p class="h2sub">Rodízio entre 3 estilos de legenda. Alimente as métricas depois de cada post para a comparação valer.</p>
    <div id="c-ab"></div>
  </div>
  <div class="panel">
    <h2>Últimos concursos conferidos</h2>
    <p class="h2sub">Detalhe por concurso, do mais recente para o mais antigo.</p>
    <div id="c-tabela" style="max-height:330px;overflow:auto"></div>
  </div>
</div>

<p class="rodape">Gerado automaticamente pelo Lotofácil Bot · análise estatística, não é previsão · +18</p>
</div>
<div id="tip"></div>

<script>
const D = __DADOS__;
const el = i => document.getElementById(i);
const fmt = (n,c=0) => n.toLocaleString("pt-BR",{minimumFractionDigits:c,maximumFractionDigits:c});
const reais = n => (n<0?"-R$ ":"R$ ") + Math.abs(n).toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2});
const NS="http://www.w3.org/2000/svg";
const tip=el("tip");
function ligarTip(no,texto){
  no.addEventListener("mousemove",e=>{tip.textContent=texto;tip.style.opacity=1;
    tip.style.left=Math.min(e.clientX+12,innerWidth-tip.offsetWidth-8)+"px";tip.style.top=(e.clientY-34)+"px";});
  no.addEventListener("mouseleave",()=>tip.style.opacity=0);
}
function svg(w,h){const s=document.createElementNS(NS,"svg");s.setAttribute("viewBox",`0 0 ${w} ${h}`);return s;}
function no(t,a,p){const n=document.createElementNS(NS,t);for(const k in a)n.setAttribute(k,a[k]);if(p)p.appendChild(n);return n;}
function barra(p,x,y,w,h,cor,r=4){
  const rr=Math.min(r,w/2,Math.max(h,.01));
  return no("path",{d:`M${x},${y+h} L${x},${y+rr} Q${x},${y} ${x+rr},${y} L${x+w-rr},${y} Q${x+w},${y} ${x+w},${y+rr} L${x+w},${y+h} Z`,fill:cor},p);
}

/* ---------- cartões ---------- */
function cards(){
  const r=D.resumo_total, r10=D.resumo_10;
  if(r.vazio){el("cards").innerHTML='<div class="card"><div class="rot">Sem dados</div><div class="val">—</div><div class="obs">Nenhum concurso conferido ainda</div></div>';return;}
  const saldo=r.saldo;
  el("cards").innerHTML=[
    ["Concursos acompanhados",fmt(r.janela),`do ${r.primeiro_concurso} ao ${r.ultimo_concurso}`],
    ["Média de acertos",fmt(r.media_de_acertos,2),`média matemática: 9,00`],
    ["Melhor marca",r.melhor_resultado.acertos,`concurso ${r.melhor_resultado.concurso}`],
    ["Apostas premiadas",fmt(r.pct_apostas_premiadas,1)+"%",`${fmt(r.apostas_premiadas)} de ${fmt(r.apostas)} jogadas`],
    ["Saldo do período",reais(saldo),`${fmt(r.retorno_pct,1)}% sobre o apostado`],
    ["Últimos 10",fmt(r10.media_de_acertos,2),`${fmt(r10.pct_concursos_com_premio,0)}% com prêmio`],
  ].map(([a,b,c])=>`<div class="card"><div class="rot">${a}</div><div class="val">${b}</div><div class="obs">${c}</div></div>`).join("");
}

/* ---------- série temporal ---------- */
function serie(){
  const alvo=el("c-serie");alvo.innerHTML="";
  if(!D.serie.length){alvo.innerHTML='<p class="vazio">Ainda sem concursos conferidos.</p>';return;}
  const W=900,H=280,ml=36,mr=12,mt=16,mb=30;
  const s=svg(W,H);alvo.appendChild(s);
  const dados=D.serie;
  const lo=Math.min(6,...dados.map(x=>x.media))-1, hi=Math.max(...dados.map(x=>x.melhor))+1;
  const px=i=>ml+(W-ml-mr)*(dados.length<2?.5:i/(dados.length-1));
  const py=v=>mt+(H-mt-mb)*(1-(v-lo)/(hi-lo));

  const g=no("g",{class:"grid"},s);
  for(let v=Math.ceil(lo);v<=hi;v++){
    if(v%2)continue;
    no("line",{x1:ml,x2:W-mr,y1:py(v),y2:py(v)},g);
    const t=no("text",{x:ml-7,y:py(v)+3.5,"text-anchor":"end"},s);t.setAttribute("class","axis");t.textContent=v;
  }
  /* referência: 9,00 = média matemática */
  no("line",{x1:ml,x2:W-mr,y1:py(9),y2:py(9),stroke:"var(--text-muted)","stroke-width":1.5,"stroke-dasharray":"4 3"},s);

  for(const [campo,cor] of [["melhor","var(--s1)"],["media","var(--s2)"]]){
    const d=dados.map((x,i)=>`${i?"L":"M"}${px(i)},${py(x[campo])}`).join(" ");
    no("path",{d,fill:"none",stroke:cor,"stroke-width":2,"stroke-linejoin":"round"},s);
  }
  dados.forEach((x,i)=>{
    const alvoInvisivel=no("rect",{x:px(i)-6,y:mt,width:12,height:H-mt-mb,fill:"transparent"},s);
    ligarTip(alvoInvisivel,`Concurso ${x.concurso} (${x.data.split("-").reverse().join("/")}): melhor ${x.melhor}, média ${fmt(x.media,2)}, ${x.premiadas} premiada(s)`);
    if(x.melhor>=13)no("circle",{cx:px(i),cy:py(x.melhor),r:4.5,fill:"var(--s1)",stroke:"var(--surface-1)","stroke-width":2},s);
  });
  [0,Math.floor(dados.length/2),dados.length-1].forEach(i=>{
    const t=no("text",{x:px(i),y:H-8,"text-anchor":i===0?"start":(i===dados.length-1?"end":"middle")},s);
    t.setAttribute("class","axis");t.textContent=dados[i].concurso;
  });
}

/* ---------- distribuição ---------- */
function distribuicao(){
  const alvo=el("c-dist");alvo.innerHTML="";
  const dados=D.distribuicao;
  if(!dados.length){alvo.innerHTML='<p class="vazio">Sem dados.</p>';return;}
  const W=460,H=230,ml=30,mr=8,mt=16,mb=28;
  const s=svg(W,H);alvo.appendChild(s);
  const max=Math.max(...dados.map(x=>x.pct));
  const larg=(W-ml-mr)/dados.length-7;
  const px=i=>ml+i*((W-ml-mr)/dados.length);
  const py=v=>mt+(H-mt-mb)*(1-v/max);
  dados.forEach((x,i)=>{
    const premiada=x.acertos>=11;
    const b=barra(s,px(i),py(x.pct),larg,py(0)-py(x.pct),premiada?"var(--s1)":"var(--grid)");
    ligarTip(b,`${x.acertos} acertos: ${fmt(x.vezes)} apostas (${fmt(x.pct,2)}%)`);
    const t=no("text",{x:px(i)+larg/2,y:H-9,"text-anchor":"middle"},s);t.setAttribute("class","axis");t.textContent=x.acertos;
  });
  no("line",{x1:ml,x2:W-mr,y1:py(0),y2:py(0),stroke:"var(--grid)"},s);
}

/* ---------- custos ---------- */
function custos(){
  const c=D.custos,r=D.resumo_total;
  const linhas=[
    ["Preço da aposta simples",reais(c.preco_aposta),""],
    ["Custo por concurso",reais(c.por_concurso),`${c.jogos_por_concurso} jogos`],
    ["Custo mensal estimado",reais(c.por_mes),"26 concursos/mês"],
    ["Infraestrutura do robô",reais(c.infraestrutura_mes),"Actions + Pages + APIs"],
  ];
  if(!r.vazio){
    linhas.push(["Apostado no período",reais(r.investido),`${fmt(r.janela)} concursos`]);
    linhas.push(["Retornado em prêmios",reais(r.retornado),""]);
  }
  let html=`<table><tr><th>Item</th><th>Valor</th><th>Observação</th></tr>`+
    linhas.map(([a,b,o])=>`<tr><td>${a}</td><td>${b}</td><td style="color:var(--text-muted)">${o}</td></tr>`).join("");
  if(!r.vazio){
    const cls=r.saldo>=0?"pos":"neg";
    html+=`<tr><td><b>Saldo</b></td><td class="${cls}">${reais(r.saldo)}</td><td class="${cls}">${fmt(r.retorno_pct,1)}%</td></tr>`;
  }
  html+="</table>";
  html+=`<p class="h2sub" style="margin-top:14px">O valor esperado matemático de uma aposta de ${reais(c.preco_aposta)} é R$ 1,13 em prêmios (-67,6%). Jogar não é necessário para o conteúdo funcionar.</p>`;
  el("c-custos").innerHTML=html;
}

/* ---------- teste A/B ---------- */
function ab(){
  const r=D.ab;
  const usados={};D.ab_registros.forEach(x=>usados[x.estilo]=(usados[x.estilo]||0)+1);
  const rodizio=Object.entries(usados).map(([k,v])=>`${k} ${v}`).join(" · ")||"nenhum post ainda";
  if(r.vazio){
    el("t-ab").textContent="Teste A/B ainda sem métricas";
    el("c-ab").innerHTML=`<p class="vazio">Posts publicados por estilo: ${rodizio}.</p>
      <p class="vazio">Depois de publicar, registre os números:<br>
      <code style="font-size:11.5px">registrar_metricas(3757, curtidas=140, alcance=3200, salvamentos=22)</code></p>`;
    return;
  }
  const estilos=Object.entries(r.por_estilo);
  const chaves=[...new Set(estilos.flatMap(([,d])=>Object.keys(d.media)))];
  const lider=estilos.slice().sort((a,b)=>(b[1].media[chaves[0]]||0)-(a[1].media[chaves[0]]||0))[0];
  el("t-ab").textContent=`Estilo "${lider[0]}" lidera em ${chaves[0]}`;
  el("c-ab").innerHTML=`<table><tr><th>Estilo</th><th>Posts</th>${chaves.map(k=>`<th>${k}</th>`).join("")}</tr>`+
    estilos.map(([nome,d])=>`<tr><td>${nome}</td><td>${d.posts}</td>${chaves.map(k=>`<td>${fmt(d.media[k]||0,1)}</td>`).join("")}</tr>`).join("")+
    `</table><p class="h2sub" style="margin-top:12px">Rodízio até aqui: ${rodizio}.</p>`;
}

/* ---------- tabela ---------- */
function tabela(){
  const dados=[...D.serie].reverse();
  if(!dados.length){el("c-tabela").innerHTML='<p class="vazio">Sem concursos conferidos.</p>';return;}
  el("c-tabela").innerHTML=`<table><tr><th>Concurso</th><th>Data</th><th>Melhor</th><th>Média</th><th>Premiadas</th><th>Saldo</th></tr>`+
    dados.map(x=>`<tr><td>${x.concurso}</td><td>${x.data.split("-").reverse().join("/")}</td>
      <td>${x.melhor}</td><td>${fmt(x.media,2)}</td><td>${x.premiadas}</td>
      <td class="${x.saldo>=0?"pos":"neg"}">${reais(x.saldo)}</td></tr>`).join("")+`</table>`;
}

/* ---------- títulos ---------- */
function titulos(){
  const r=D.resumo_total;
  el("subtitulo").textContent=r.vazio?"Nenhum concurso conferido ainda":
    `${fmt(r.janela)} concursos acompanhados · ${fmt(r.apostas)} apostas registradas`;
  if(D.usando_simulacao){
    el("aviso-simulacao").innerHTML=`<div class="aviso-sim"><b>Atenção:</b> este painel ainda mostra dados de
      <b>simulação de calibragem</b> — jogos reconstruídos do passado, não apostas registradas antes do sorteio.
      Assim que o robô rodar por concursos reais, o painel passa a usar só eles automaticamente.</div>`;
  }
  if(!r.vazio){
    el("t-serie").textContent=`Média de ${fmt(r.media_de_acertos,2)} acertos por jogo, contra 9,00 esperados pela matemática`;
    const p=D.distribuicao.filter(x=>x.acertos>=11).reduce((a,b)=>a+b.pct,0);
    el("t-dist").textContent=`${fmt(p,1)}% das apostas terminaram na faixa premiada`;
  } else {
    el("t-serie").textContent="Desempenho por concurso";
    el("t-dist").textContent="Distribuição de acertos";
  }
}

function render(){titulos();cards();serie();distribuicao();custos();ab();tabela();}
el("tema").addEventListener("click",()=>{
  const escuro=document.documentElement.dataset.theme==="dark";
  document.documentElement.dataset.theme=escuro?"light":"dark";
  el("tema").textContent=escuro?"Modo escuro":"Modo claro";render();
});
if(window.matchMedia&&matchMedia("(prefers-color-scheme: dark)").matches)el("tema").click();
render();
</script>
</body>
</html>
"""


def gerar(saida: str | Path = "saidas/painel.html") -> Path:
    dados = montar_dados()
    destino = Path(saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        TEMPLATE.replace("__DADOS__", json.dumps(dados, ensure_ascii=False)),
        encoding="utf-8",
    )
    return destino


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Painel de acompanhamento da operação")
    parser.add_argument("--saida", default="saidas/painel.html")
    args = parser.parse_args()
    print(f"Painel gerado em {gerar(args.saida).resolve()}")
