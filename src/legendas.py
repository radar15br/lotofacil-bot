"""
ETAPA 6 — LEGENDAS COM TESTE A/B
=================================

O QUE ESTE MÓDULO FAZ

Gera 3 versões de legenda para o mesmo post, cada uma com uma "voz" diferente:

  informativo  -> tom de análise, foco no dado. Atrai quem gosta de número.
  chamativo    -> tom direto e emocional, com emoji. Atrai no scroll.
  prova_social -> foco no histórico de desempenho. Atrai quem já acompanha.

Depois escolhe UMA delas por rodízio (o concurso decide, então não tem
viés) e registra qual foi usada em data/ab_testing.json. Com o tempo você
compara curtidas, alcance e cliques por estilo e descobre qual converte.

POR QUE RODÍZIO E NÃO ALEATÓRIO

Rodízio garante que os 3 estilos recebem o mesmo número de publicações em
períodos parecidos — se o estilo A só aparecer em dia de sorteio especial,
a comparação fica contaminada.

LIMITES QUE O MÓDULO RESPEITA

  Instagram: 2.200 caracteres de legenda, no máximo 30 hashtags.
  TikTok:    2.200 caracteres na descrição.
O módulo valida antes de salvar e avisa se estourar.

Como rodar:
    python -m src.legendas                     # gera para o próximo concurso
    python -m src.legendas --concurso 3757
    python -m src.legendas --estilo chamativo  # força um estilo
    python -m src.legendas --relatorio         # desempenho de cada estilo
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src import analise as an
from src.coleta import PASTA_DADOS, RAIZ, carregar_base
from src.desempenho import num, resumo
from src.jogos import carregar_jogos, gerar_jogos

PASTA_SAIDAS = RAIZ / "saidas"
ARQUIVO_AB = PASTA_DADOS / "ab_testing.json"

PERFIL = "@radar15br"

LIMITE_CARACTERES = 2200
LIMITE_HASHTAGS = 30

ESTILOS = ("informativo", "chamativo", "prova_social")

# ---------------------------------------------------------------------------
# HASHTAGS
# ---------------------------------------------------------------------------
# Mistura proposital: tags grandes dão alcance, tags de nicho dão relevância.
# Sem tag de "dinheiro fácil" / "ganhar garantido" — elas atraem moderação.

HASHTAGS_BASE = [
    "#radar15br", "#lotofacil", "#loteria", "#loterias", "#loteriasdacaixa",
    "#lotofacildaindependencia", "#sorteio", "#jogosdaloteria",
]
HASHTAGS_NICHO = [
    "#estatistica", "#analiseestatistica", "#dezenas", "#numerosdasorte",
    "#apostas", "#bolao", "#lotofacilhoje", "#resultadolotofacil",
    "#concurso", "#dicaslotofacil", "#jogoresponsavel",
]
HASHTAGS_POR_ESTILO = {
    "informativo": ["#dados", "#probabilidade", "#matematica"],
    "chamativo": ["#sortegrande", "#fechamento", "#palpites"],
    "prova_social": ["#resultados", "#acertos", "#historico"],
}

AVISO_LEGENDA = (
    "AVISO: jogos montados por análise estatística de resultados históricos. "
    "Não é previsão e não há garantia de resultado — cada sorteio é independente "
    "e todas as combinações têm a mesma probabilidade. Conteúdo sem vínculo com a "
    "Caixa Econômica Federal. Proibido para menores de 18 anos. Jogue com "
    "responsabilidade e apenas o que puder perder."
)

# Onde entra o link de afiliado ou do grupo pago (Etapa 8).
# Deixe vazio enquanto não tiver — o módulo simplesmente omite a linha.
CTA_LINK = ""
CTA_TEXTO = ""


# ---------------------------------------------------------------------------
# MONTAGEM DO CONTEXTO
# ---------------------------------------------------------------------------


def _contexto(concurso_alvo: int | None = None) -> dict[str, Any]:
    base = carregar_base()
    if not base:
        raise RuntimeError("Base vazia. Rode a Etapa 1 antes.")

    alvo = concurso_alvo or base[-1]["concurso"] + 1
    jogos = carregar_jogos(alvo) or gerar_jogos(base, concurso_alvo=alvo)

    freq = an.frequencia(base, 100)
    atr = an.atrasos(base)
    perfil = an.perfil_alvo(base)
    d = resumo(10, incluir_simulados=True)

    quentes = sorted(freq, key=lambda x: -freq[x]["vezes"])[:3]
    atrasadas = sorted(atr, key=lambda x: -atr[x]["atraso_atual"])[:3]

    return {
        "concurso": alvo,
        "total_base": len(base),
        "ultimo": base[-1],
        "jogos": jogos,
        "quentes": quentes,
        "atrasadas": atrasadas,
        "atrasos": atr,
        "perfil": perfil,
        "desempenho": d,
        "data_hoje": datetime.now().strftime("%d/%m/%Y"),
    }


def _linha_jogos(ctx: dict, quantos: int = 13) -> str:
    """Os jogos em texto, um por linha, para quem lê a legenda sem ver a imagem."""
    return "\n".join(
        f"{j['numero']:02d}) " + " ".join(f"{d:02d}" for d in j["dezenas"])
        for j in ctx["jogos"]["jogos"][:quantos]
    )


def _hashtags(estilo: str) -> str:
    tags = HASHTAGS_BASE + HASHTAGS_NICHO + HASHTAGS_POR_ESTILO[estilo]
    return " ".join(tags[:LIMITE_HASHTAGS])


def _bloco_cta() -> str:
    if not CTA_LINK and not CTA_TEXTO:
        return ""
    partes = [p for p in (CTA_TEXTO, CTA_LINK) if p]
    return "\n\n" + "\n".join(partes)


# ---------------------------------------------------------------------------
# OS TRÊS ESTILOS DE COPY
# ---------------------------------------------------------------------------


def copy_informativo(ctx: dict) -> str:
    d = ctx["desempenho"]
    p = ctx["perfil"]
    quentes = ", ".join(f"{x:02d}" for x in ctx["quentes"])
    def _plural(n: int) -> str:
        return f"{n} concurso" if n == 1 else f"{n} concursos"

    atrasadas = ", ".join(
        f"{x:02d} ({_plural(ctx['atrasos'][x]['atraso_atual'])})" for x in ctx["atrasadas"]
    )
    media = num(d.get("media_de_acertos", 0)) if not d.get("vazio") else "—"

    return f"""13 jogos para o concurso {ctx['concurso']} — o que os dados mostram

{PERFIL} · Base analisada: {num(ctx['total_base'], 0)} concursos, de 2003 até hoje.

Padrões que orientaram a montagem:
• Soma das 15 dezenas entre {p['soma_dezenas']['faixa'][0]} e {p['soma_dezenas']['faixa'][1]} — faixa de 8 em cada 10 sorteios
• Entre {p['pares']['faixa'][0]} e {p['pares']['faixa'][1]} números pares
• De {p['repetidas_do_anterior']['faixa'][0]} a {p['repetidas_do_anterior']['faixa'][1]} dezenas repetidas do concurso anterior (média histórica: {num(p['repetidas_do_anterior']['media'])})

Mais sorteadas nos últimos 100 concursos: {quentes}
Mais atrasadas: {atrasadas}

Os jogos:
{_linha_jogos(ctx)}

Transparência que ninguém fala: a média matemática de acertos de qualquer jogo de 15 dezenas é 9,00 — a nossa está em {media}. Os filtros dão aos jogos o formato de um resultado real, mas não aumentam a chance de ganhar. Nenhuma estratégia aumenta.

{AVISO_LEGENDA}{_bloco_cta()}

{_hashtags('informativo')}"""


def copy_chamativo(ctx: dict) -> str:
    d = ctx["desempenho"]
    atrasada = ctx["atrasadas"][0]
    dias = ctx["atrasos"][atrasada]["atraso_atual"]
    melhor = d.get("melhor_resultado", {}).get("acertos", "—")

    plural = "concurso" if dias == 1 else "concursos"

    return f"""🎯 13 JOGOS PRONTOS — CONCURSO {ctx['concurso']}

A dezena {atrasada:02d} está há {dias} {plural} sem aparecer. Isso muda a chance dela no próximo sorteio? Não muda nada. Mas é o tipo de detalhe que quem acompanha de perto gosta de saber. 👀

Montamos 13 jogos seguindo os padrões que mais se repetem em {num(ctx['total_base'], 0)} concursos analisados. Nenhum jogo igual ao outro, todas as 25 dezenas distribuídas.

🔥 Melhor marca até aqui: {melhor} acertos
📊 {num(ctx['total_base'], 0)} concursos na base
🎲 13 jogos, zero repetição

{_linha_jogos(ctx)}

⚠️ Falando sério por um segundo: isso é estatística, não bola de cristal. A chance de 15 acertos é 1 em 3.268.760 por jogo. Não existe estratégia que mude isso — quem promete o contrário está te enganando.

Salva o post 📌 e volta depois do sorteio pra conferir com a gente aqui no {PERFIL}.

{AVISO_LEGENDA}{_bloco_cta()}

{_hashtags('chamativo')}"""


def copy_prova_social(ctx: dict) -> str:
    d = ctx["desempenho"]
    if d.get("vazio"):
        linhas = "Primeira publicação: o histórico de desempenho começa hoje, e fica todo público."
    else:
        marca = " (simulação de calibragem)" if d.get("contem_simulados") else ""
        linhas = "\n".join([
            f"• {num(d['media_de_acertos'])} acertos por jogo, em média{marca}",
            f"• {d['concursos_com_premio']} dos últimos {d['janela']} concursos com ao menos uma aposta premiada ({num(d['pct_concursos_com_premio'], 0)}%)",
            f"• Melhor marca: {d['melhor_resultado']['acertos']} acertos no concurso {d['melhor_resultado']['concurso']}",
            f"• {num(d['apostas_premiadas'], 0)} apostas premiadas em {num(d['apostas'], 0)} jogadas",
        ])

    return f"""O placar aberto — concurso {ctx['concurso']}

Todo mundo mostra o palpite. Quase ninguém mostra o resultado depois. No {PERFIL} é o contrário: os jogos ficam registrados antes do sorteio e o desempenho é publicado, dê no que der.

Como estamos:
{linhas}

Os 13 jogos de hoje:
{_linha_jogos(ctx)}

O número que quase ninguém publica: a média matemática de acertos de qualquer jogo de 15 dezenas é 9,00. Se alguém te mostrar "média de 12 acertos", desconfie — ou está contando errado, ou está escolhendo o que mostrar.

{AVISO_LEGENDA}{_bloco_cta()}

{_hashtags('prova_social')}"""


GERADORES = {
    "informativo": copy_informativo,
    "chamativo": copy_chamativo,
    "prova_social": copy_prova_social,
}


# ---------------------------------------------------------------------------
# VALIDAÇÃO
# ---------------------------------------------------------------------------


def validar(texto: str) -> dict[str, Any]:
    hashtags = [p for p in texto.split() if p.startswith("#")]
    return {
        "caracteres": len(texto),
        "hashtags": len(hashtags),
        "dentro_do_limite": len(texto) <= LIMITE_CARACTERES and len(hashtags) <= LIMITE_HASHTAGS,
        "sobra_de_caracteres": LIMITE_CARACTERES - len(texto),
    }


def _encurtar_se_precisar(texto: str, ctx: dict, estilo: str) -> str:
    """
    Se a legenda estourar 2.200 caracteres, corta a listagem de jogos —
    ela já está na imagem. É o único trecho que dá para reduzir sem perder
    informação essencial nem o aviso legal.
    """
    if len(texto) <= LIMITE_CARACTERES:
        return texto

    completo = _linha_jogos(ctx)
    for quantos in (7, 5, 3, 0):
        reduzido = _linha_jogos(ctx, quantos)
        substituto = (reduzido + "\n(os 13 jogos completos estão nas imagens)") if quantos \
            else "Os 13 jogos completos estão nas imagens."
        tentativa = texto.replace(completo, substituto)
        if len(tentativa) <= LIMITE_CARACTERES:
            return tentativa
    return texto[:LIMITE_CARACTERES]


# ---------------------------------------------------------------------------
# RODÍZIO A/B E REGISTRO
# ---------------------------------------------------------------------------


def escolher_estilo(concurso: int) -> str:
    """Rodízio determinístico: o número do concurso decide, sem viés humano."""
    return ESTILOS[concurso % len(ESTILOS)]


def carregar_ab() -> list[dict[str, Any]]:
    if not ARQUIVO_AB.exists():
        return []
    return json.loads(ARQUIVO_AB.read_text(encoding="utf-8"))


def salvar_ab(registros: list[dict[str, Any]]) -> None:
    unicos = {r["concurso"]: r for r in registros}
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    temporario = ARQUIVO_AB.with_suffix(".tmp")
    temporario.write_text(
        json.dumps([unicos[k] for k in sorted(unicos)], ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    temporario.replace(ARQUIVO_AB)


def registrar_metricas(concurso: int, **metricas: float) -> dict[str, Any]:
    """
    Depois de publicar, alimente aqui os números da plataforma:
        registrar_metricas(3757, curtidas=120, alcance=3400, salvamentos=18)
    É isso que transforma o rodízio em teste A/B de verdade.
    """
    registros = carregar_ab()
    alvo = next((r for r in registros if r["concurso"] == concurso), None)
    if alvo is None:
        raise RuntimeError(f"Concurso {concurso} não tem legenda registrada.")
    alvo.setdefault("metricas", {}).update(metricas)
    salvar_ab(registros)
    return alvo


def relatorio_ab() -> dict[str, Any]:
    """Compara o desempenho médio de cada estilo de legenda."""
    registros = [r for r in carregar_ab() if r.get("metricas")]
    if not registros:
        return {"vazio": True, "mensagem": "Ainda não há métricas registradas."}

    por_estilo: dict[str, dict[str, Any]] = {}
    for r in registros:
        e = por_estilo.setdefault(r["estilo"], {"posts": 0, "soma": {}})
        e["posts"] += 1
        for chave, valor in r["metricas"].items():
            e["soma"][chave] = e["soma"].get(chave, 0) + valor

    for e in por_estilo.values():
        e["media"] = {k: round(v / e["posts"], 1) for k, v in e["soma"].items()}
        e.pop("soma")

    return {"vazio": False, "posts_com_metricas": len(registros), "por_estilo": por_estilo}


# ---------------------------------------------------------------------------
# GERAÇÃO
# ---------------------------------------------------------------------------


def gerar(concurso: int | None = None, estilo_forcado: str | None = None) -> dict[str, Any]:
    ctx = _contexto(concurso)
    alvo = ctx["concurso"]
    escolhido = estilo_forcado or escolher_estilo(alvo)

    variacoes: dict[str, Any] = {}
    for nome, gerador in GERADORES.items():
        texto = _encurtar_se_precisar(gerador(ctx), ctx, nome)
        variacoes[nome] = {"texto": texto, **validar(texto)}

    pasta = PASTA_SAIDAS / str(alvo)
    pasta.mkdir(parents=True, exist_ok=True)

    resultado = {
        "concurso": alvo,
        "estilo_escolhido": escolhido,
        "variacoes": variacoes,
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    (pasta / "legendas.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    # Arquivo de texto puro, para copiar e colar se quiser publicar na mão
    (pasta / f"legenda-{escolhido}.txt").write_text(
        variacoes[escolhido]["texto"], encoding="utf-8"
    )

    # Registra a escolha para o teste A/B
    registros = carregar_ab()
    registros.append({
        "concurso": alvo,
        "estilo": escolhido,
        "caracteres": variacoes[escolhido]["caracteres"],
        "hashtags": variacoes[escolhido]["hashtags"],
        "publicado_em": None,
        "metricas": {},
    })
    salvar_ab(registros)

    resultado["pasta"] = str(pasta)
    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera as legendas do post (teste A/B)")
    parser.add_argument("--concurso", type=int, default=None)
    parser.add_argument("--estilo", choices=ESTILOS, default=None)
    parser.add_argument("--relatorio", action="store_true", help="compara os estilos")
    parser.add_argument("--mostrar", action="store_true", help="imprime as 3 legendas inteiras")
    args = parser.parse_args()

    if args.relatorio:
        r = relatorio_ab()
        if r["vazio"]:
            print(r["mensagem"])
            print("\nRegistre assim, depois de publicar:")
            print("  python -c \"from src.legendas import registrar_metricas; "
                  "registrar_metricas(3757, curtidas=120, alcance=3400, salvamentos=18)\"")
        else:
            print(f"TESTE A/B — {r['posts_com_metricas']} posts com métricas\n")
            for estilo, dados in r["por_estilo"].items():
                print(f"  {estilo:14} ({dados['posts']} posts): " +
                      " | ".join(f"{k} {v}" for k, v in dados["media"].items()))
    else:
        r = gerar(args.concurso, args.estilo)
        print(f"Legendas do concurso {r['concurso']}")
        print(f"Estilo escolhido pelo rodízio: {r['estilo_escolhido'].upper()}\n")
        for nome, v in r["variacoes"].items():
            marca = "  <-- este vai ser publicado" if nome == r["estilo_escolhido"] else ""
            ok = "ok" if v["dentro_do_limite"] else "ESTOUROU O LIMITE"
            print(f"  {nome:14} {v['caracteres']:5d} caracteres, "
                  f"{v['hashtags']:2d} hashtags  [{ok}]{marca}")
            if args.mostrar:
                print("\n" + "-" * 60 + f"\n{v['texto']}\n" + "-" * 60 + "\n")
        print(f"\nSalvo em {r['pasta']}")
