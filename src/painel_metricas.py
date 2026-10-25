"""Template HTML do painel de métricas (docs/metricas.html)."""

TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Radar 15 · Métricas</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{
  --bg:#050805; --sup:#0A110A; --sup2:#0F1A0E; --borda:#1F3D14;
  --txt:#F2F7EC; --txt2:#B9C9AC; --txt3:#7D8F72;
  --lima:#A3F600; --lima-suave:rgba(163,246,0,.14);
  --ok:#6FE36B; --alerta:#FFB547; --ruim:#FF6B5E;
}
*{box-sizing:border-box;margin:0;padding:0}
html{background:var(--bg)}
body{min-height:100vh;background:radial-gradient(120% 70% at 10% 0%,#10200A 0%,var(--bg) 55%) fixed;
  color:var(--txt);font:15px/1.45 Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:28px 16px 60px}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:22px}
.marca{font-size:28px;font-weight:800;font-style:italic;letter-spacing:-.02em}
.marca b{color:var(--lima)}
.sub{color:var(--txt3);font-size:13px}
.filtros{display:flex;gap:8px;flex-wrap:wrap}
.filtros button{background:var(--sup);border:1px solid var(--borda);color:var(--txt2);
  font:600 13px Inter,sans-serif;padding:8px 14px;border-radius:999px;cursor:pointer}
.filtros button.ativo{background:var(--lima);color:#06120A;border-color:var(--lima)}
.resumo{background:var(--sup);border:1px solid var(--borda);border-left:4px solid var(--lima);
  border-radius:16px;padding:18px 20px;margin-bottom:18px}
.resumo h2{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--lima);margin-bottom:8px}
.resumo li{margin:4px 0 4px 18px;color:var(--txt)}
.alerta{background:rgba(255,181,71,.08);border:1px solid rgba(255,181,71,.4);color:#FFD9A0;
  border-radius:12px;padding:12px 16px;margin-bottom:18px;font-size:14px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:18px}
.kpi{background:var(--sup);border:1px solid var(--borda);border-radius:16px;padding:16px 18px}
.kpi .r{font-size:12px;color:var(--txt3);text-transform:uppercase;letter-spacing:.06em;font-weight:600}
.kpi .v{font-size:30px;font-weight:800;letter-spacing:-.02em;margin-top:6px;font-variant-numeric:tabular-nums}
.kpi .d{font-size:13px;margin-top:2px;color:var(--txt2)}
.up{color:var(--ok)} .down{color:var(--ruim)}
.grade{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:18px}
@media(max-width:820px){.grade{grid-template-columns:1fr}}
.card{background:var(--sup);border:1px solid var(--borda);border-radius:16px;padding:18px 18px 14px}
.card h3{font-size:16px;font-weight:700;margin-bottom:2px}
.card .nota{font-size:12px;color:var(--txt3);margin-bottom:12px}
.chart{position:relative;height:240px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{text-align:left;color:var(--txt3);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.05em;
  padding:8px 10px;border-bottom:1px solid var(--borda);cursor:pointer;white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid #13240F;font-variant-numeric:tabular-nums}
td.n,th.n{text-align:right}
tr:hover td{background:var(--sup2)}
a{color:var(--lima);text-decoration:none}
.pill{display:inline-block;font-size:11.5px;font-weight:700;padding:2px 9px;border-radius:999px;
  background:var(--lima-suave);color:var(--lima)}
.pill.img{background:#1A2418;color:var(--txt2)}
.tabela{overflow-x:auto}
footer{color:var(--txt3);font-size:12px;margin-top:20px}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <div class="marca">RADAR <b>15</b> · Métricas</div>
      <div class="sub" id="atualizado"></div>
    </div>
    <div class="filtros" id="periodo">
      <button data-d="7">7 dias</button><button data-d="30" class="ativo">30 dias</button><button data-d="90">90 dias</button>
    </div>
  </header>

  <div id="avisos"></div>
  <section class="resumo"><h2>Resumo executivo</h2><ul id="conclusoes"></ul></section>
  <section class="kpis" id="kpis"></section>

  <section class="grade">
    <div class="card"><h3 id="t-seg">Seguidores</h3><div class="nota">Total de seguidores por dia</div>
      <div class="chart"><canvas id="g-seg"></canvas></div></div>
    <div class="card"><h3 id="t-fmt">Alcance por formato</h3><div class="nota">Alcance médio por post no período</div>
      <div class="chart"><canvas id="g-fmt"></canvas></div></div>
  </section>
  <section class="grade">
    <div class="card"><h3 id="t-eng">Salvamentos e compartilhamentos</h3><div class="nota">Média por post, por formato</div>
      <div class="chart"><canvas id="g-eng"></canvas></div></div>
    <div class="card"><h3 id="t-ab">Teste A/B de legendas</h3><div class="nota">Alcance médio por estilo de legenda (posts do jogo do dia)</div>
      <div class="chart"><canvas id="g-ab"></canvas></div></div>
  </section>

  <section class="card">
    <h3>Posts do período</h3><div class="nota">Clique no título da coluna para ordenar</div>
    <div class="tabela"><table id="tabela"><thead><tr>
      <th data-k="data">Data</th><th data-k="tipo">Formato</th><th data-k="conteudo">Conteúdo</th>
      <th class="n" data-k="reach">Alcance</th><th class="n" data-k="views">Visualiz.</th>
      <th class="n" data-k="curtidas">Curtidas</th><th class="n" data-k="comentarios">Coment.</th>
      <th class="n" data-k="saved">Salvos</th><th class="n" data-k="shares">Compart.</th><th>Link</th>
    </tr></thead><tbody></tbody></table></div>
  </section>
  <footer>Dados da API oficial do Instagram, atualizados uma vez por dia pelo robô.</footer>
</div>

<script>
const D = __DADOS__;
const nf = new Intl.NumberFormat('pt-BR');
const pf = v => (v>0?'+':'') + v.toLocaleString('pt-BR',{maximumFractionDigits:1}) + '%';
const dt = s => new Date(s).toLocaleDateString('pt-BR',{day:'2-digit',month:'2-digit'});
const media = (xs,k) => xs.length ? xs.reduce((a,p)=>a+(p[k]||0),0)/xs.length : 0;
let dias = 30, ordem = {k:'data', asc:false}, graficos = {};

if (typeof Chart !== 'undefined') {
  Chart.defaults.color = '#B9C9AC';
  Chart.defaults.font.family = 'Inter, sans-serif';
  Chart.defaults.borderColor = 'rgba(31,61,20,.6)';
}
const tip = {backgroundColor:'#0F1A0E',borderColor:'#1F3D14',borderWidth:1,padding:10,titleColor:'#F2F7EC',bodyColor:'#B9C9AC'};

document.getElementById('atualizado').textContent = '@' + (D.conta||'radar15br') + ' · atualizado em ' + D.atualizado;
if (D.avisos && D.avisos.length) document.getElementById('avisos').innerHTML =
  '<div class="alerta">⚠️ Métricas de alcance indisponíveis: o token do Instagram não tem a permissão de insights. Seguidores, curtidas e comentários continuam sendo registrados.</div>';

function noPeriodo(){
  const lim = Date.now() - dias*864e5;
  return D.posts.filter(p => new Date(p.data).getTime() >= lim);
}
function seguidoresPeriodo(){
  const lim = new Date(Date.now() - dias*864e5).toISOString().slice(0,10);
  return D.seguidores.filter(s => s.data >= lim);
}
function porGrupo(posts, campo){
  const g = {};
  posts.forEach(p => { const c = p[campo]; if(!c) return; (g[c] = g[c] || []).push(p); });
  return g;
}

function render(){
  const posts = noPeriodo(), seg = seguidoresPeriodo();
  const atual = D.seguidores.at(-1)?.seguidores || 0;
  const inicio = seg[0]?.seguidores ?? atual;
  const ganho = atual - inicio;
  const fmt = porGrupo(posts,'tipo');
  const reels = fmt['Reel']||[], outros = posts.filter(p=>p.tipo!=='Reel');
  const alcReel = media(reels,'reach'), alcOutros = media(outros,'reach');

  // KPIs
  const kp = [
    ['Seguidores', nf.format(atual), (ganho>=0?'<span class="up">▲ ':'<span class="down">▼ ')+nf.format(Math.abs(ganho))+'</span> em '+dias+' dias'],
    ['Posts no período', nf.format(posts.length), (reels.length)+' Reels · '+outros.length+' imagens/carrosséis'],
    ['Alcance médio', nf.format(Math.round(media(posts,'reach'))), 'por post'],
    ['Salvamentos', nf.format(posts.reduce((a,p)=>a+(p.saved||0),0)), 'total no período'],
    ['Compartilhamentos', nf.format(posts.reduce((a,p)=>a+(p.shares||0),0)), 'total no período'],
  ];
  document.getElementById('kpis').innerHTML = kp.map(k=>`<div class="kpi"><div class="r">${k[0]}</div><div class="v">${k[1]}</div><div class="d">${k[2]}</div></div>`).join('');

  // Conclusões
  const c = [];
  c.push(ganho>0 ? `Perfil ganhou <b>${nf.format(ganho)}</b> seguidores em ${dias} dias.` :
         ganho<0 ? `<span class="down">⚠️ Perfil perdeu ${nf.format(-ganho)} seguidores em ${dias} dias.</span>` :
         `Número de seguidores estável em ${dias} dias (histórico começou a ser registrado em ${D.seguidores[0].data.split('-').reverse().join('/')}).`);
  if (reels.length && outros.length && alcOutros>0)
    c.push(`Reels alcançam <b>${(alcReel/alcOutros).toLocaleString('pt-BR',{maximumFractionDigits:1})}x</b> mais que imagens (${nf.format(Math.round(alcReel))} × ${nf.format(Math.round(alcOutros))} por post).`);
  else if (!reels.length) c.push('Ainda sem Reels no período — o primeiro comparativo aparece após alguns dias de publicação.');
  const melhor = [...posts].sort((a,b)=>(b.reach||0)-(a.reach||0))[0];
  if (melhor && melhor.reach) c.push(`Melhor post: <a href="${melhor.link}" target="_blank">${melhor.tipo} de ${dt(melhor.data)}</a>, com ${nf.format(melhor.reach)} de alcance.`);
  const ab = Object.entries(porGrupo(posts.filter(p=>p.conteudo==='Jogo do dia'),'estilo_legenda'))
    .map(([k,v])=>[k,media(v,'reach'),v.length]).filter(x=>x[2]>=2).sort((a,b)=>b[1]-a[1]);
  if (ab.length>=2) c.push(`Legenda <b>${ab[0][0].replace('_',' ')}</b> lidera o teste A/B (${nf.format(Math.round(ab[0][1]))} de alcance médio).`);
  document.getElementById('conclusoes').innerHTML = c.map(x=>`<li>${x}</li>`).join('');

  // Títulos com conclusão
  document.getElementById('t-seg').textContent = ganho>0 ? `Seguidores crescem ${nf.format(ganho)} em ${dias} dias` : ganho<0 ? `Seguidores caem ${nf.format(-ganho)} em ${dias} dias` : 'Seguidores estáveis no período';
  document.getElementById('t-fmt').textContent = (reels.length && alcOutros>0) ? `Reels alcançam ${(alcReel/alcOutros).toLocaleString('pt-BR',{maximumFractionDigits:1})}x mais que imagens` : 'Alcance médio por formato';
  document.getElementById('t-ab').textContent = ab.length>=2 ? `Legenda "${ab[0][0].replace('_',' ')}" tem o maior alcance` : 'Teste A/B de legendas (dados acumulando)';

  // Gráficos (se a biblioteca não carregar, o resto do painel continua funcionando)
  if (typeof Chart === 'undefined') return renderTabela(posts);
  Object.values(graficos).forEach(g=>g.destroy());
  graficos.seg = new Chart(document.getElementById('g-seg'), {type:'line',
    data:{labels:seg.map(s=>s.data.slice(8,10)+'/'+s.data.slice(5,7)),
      datasets:[{data:seg.map(s=>s.seguidores),borderColor:'#A3F600',backgroundColor:'rgba(163,246,0,.10)',fill:true,borderWidth:2,pointRadius:seg.length<15?4:0,pointHoverRadius:5,tension:.25}]},
    options:{maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{...tip,callbacks:{label:x=>nf.format(x.parsed.y)+' seguidores'}}},
      scales:{x:{grid:{display:false}},y:{grid:{color:'rgba(31,61,20,.45)'},ticks:{callback:v=>nf.format(v),precision:0}}}}});

  const barras = (id, rotulos, valores, sufixo) => new Chart(document.getElementById(id), {type:'bar',
    data:{labels:rotulos,datasets:[{data:valores,backgroundColor:'#A3F600',hoverBackgroundColor:'#C4FF4D',borderRadius:4,maxBarThickness:46}]},
    options:{maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{...tip,callbacks:{label:x=>nf.format(Math.round(x.parsed.y))+sufixo}}},
      scales:{x:{grid:{display:false}},y:{grid:{color:'rgba(31,61,20,.45)'},ticks:{callback:v=>nf.format(v)}}}}});
  const f = Object.entries(fmt);
  graficos.fmt = barras('g-fmt', f.map(x=>x[0]+' ('+x[1].length+')'), f.map(x=>media(x[1],'reach')), ' de alcance médio');

  graficos.eng = new Chart(document.getElementById('g-eng'), {type:'bar',
    data:{labels:f.map(x=>x[0]),datasets:[
      {label:'Salvamentos',data:f.map(x=>media(x[1],'saved')),backgroundColor:'#6BA800',borderRadius:4,maxBarThickness:34},
      {label:'Compartilhamentos',data:f.map(x=>media(x[1],'shares')),backgroundColor:'#3E8BFF',borderRadius:4,maxBarThickness:34}]},
    options:{maintainAspectRatio:false,plugins:{legend:{position:'top',align:'start',labels:{boxWidth:10,boxHeight:10,useBorderRadius:true,borderRadius:2}},
      tooltip:{...tip,callbacks:{label:x=>x.dataset.label+': '+x.parsed.y.toLocaleString('pt-BR',{maximumFractionDigits:1})}}},
      scales:{x:{grid:{display:false}},y:{grid:{color:'rgba(31,61,20,.45)'}}}}});

  graficos.ab = barras('g-ab', ab.map(x=>x[0].replace('_',' ')+' ('+x[2]+')'), ab.map(x=>x[1]), ' de alcance médio');

  renderTabela(posts);
}

function renderTabela(posts){
  const linhas = [...posts].sort((a,b)=>{const va=a[ordem.k]??0, vb=b[ordem.k]??0; return (va>vb?1:va<vb?-1:0)*(ordem.asc?1:-1);});
  const v = x => x==null ? '—' : nf.format(x);
  document.querySelector('#tabela tbody').innerHTML = linhas.map(p=>`<tr>
    <td>${dt(p.data)}</td><td><span class="pill ${p.tipo==='Reel'?'':'img'}">${p.tipo}</span></td><td>${p.conteudo}</td>
    <td class="n">${v(p.reach)}</td><td class="n">${v(p.views)}</td><td class="n">${v(p.curtidas)}</td><td class="n">${v(p.comentarios)}</td>
    <td class="n">${v(p.saved)}</td><td class="n">${v(p.shares)}</td><td><a href="${p.link}" target="_blank">abrir ↗</a></td></tr>`).join('');
}

document.querySelectorAll('#periodo button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#periodo button').forEach(x=>x.classList.remove('ativo'));
  b.classList.add('ativo'); dias = +b.dataset.d; render();
});
document.querySelectorAll('#tabela th[data-k]').forEach(th=>th.onclick=()=>{
  ordem = {k:th.dataset.k, asc: ordem.k===th.dataset.k ? !ordem.asc : false}; render();
});
render();
</script>
</body>
</html>
"""
