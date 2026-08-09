"""
ETAPA 2 — ANÁLISE ESTATÍSTICA DA LOTOFÁCIL
===========================================

AVISO QUE VALE PARA TODO O PROJETO:
Isto é leitura de dados históricos, NÃO previsão. Cada sorteio da Lotofácil é
independente dos anteriores e todas as 3.268.760 combinações possíveis de 15
dezenas têm exatamente a mesma probabilidade. O que a estatística mostra é o
COMPORTAMENTO TÍPICO dos sorteios passados — e é isso que usamos para montar
jogos com "cara" de resultado real, não para adivinhar o próximo.

O que este módulo calcula:

  1. FREQUÊNCIA  — quantas vezes cada dezena saiu (histórico e janelas recentes)
  2. ATRASO      — há quantos concursos cada dezena não aparece
  3. PARIDADE    — quantos pares e ímpares costumam sair juntos
  4. SOMA        — a faixa em que cai a soma das 15 dezenas
  5. REPETIÇÃO   — quantas dezenas se repetem do concurso anterior
  6. GEOGRAFIA   — linhas, colunas, quadrantes e moldura x miolo do volante
  7. PRIMOS      — quantidade de números primos por sorteio
  8. PERFIL-ALVO — resumo dos padrões que a Etapa 3 usará para gerar os jogos

Como rodar:
    python -m src.analise                # relatório completo no terminal
    python -m src.analise --janela 100   # foca nos últimos 100 concursos
    python -m src.analise --json         # salva data/analise.json
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any

from src.coleta import PASTA_DADOS, carregar_base

# ---------------------------------------------------------------------------
# MAPA DO VOLANTE (5 linhas x 5 colunas)
# ---------------------------------------------------------------------------
#    1  2  3  4  5
#    6  7  8  9 10
#   11 12 13 14 15
#   16 17 18 19 20
#   21 22 23 24 25

LINHAS = {f"L{i+1}": list(range(i * 5 + 1, i * 5 + 6)) for i in range(5)}
COLUNAS = {f"C{j+1}": [j + 1 + 5 * i for i in range(5)] for j in range(5)}

QUADRANTES = {
    "Q1 (sup. esq.)": [1, 2, 6, 7],
    "Q2 (sup. dir.)": [4, 5, 9, 10],
    "Q3 (inf. esq.)": [16, 17, 21, 22],
    "Q4 (inf. dir.)": [19, 20, 24, 25],
    "Centro (cruz)": [3, 8, 13, 18, 23, 11, 12, 14, 15],
}

# Moldura = borda do volante (16 dezenas). Miolo = os 9 do meio.
MOLDURA = [1, 2, 3, 4, 5, 6, 10, 11, 15, 16, 20, 21, 22, 23, 24, 25]
MIOLO = [7, 8, 9, 12, 13, 14, 17, 18, 19]

PRIMOS = [2, 3, 5, 7, 11, 13, 17, 19, 23]

TOTAL_DEZENAS = 25
DEZENAS_POR_JOGO = 15


# ---------------------------------------------------------------------------
# AJUDANTES
# ---------------------------------------------------------------------------


def _janela(base: list[dict], n: int | None) -> list[dict]:
    """Recorta os últimos n concursos. n=None significa histórico inteiro."""
    return base if not n else base[-n:]


def _pct(parte: float, total: float) -> float:
    return round(100 * parte / total, 2) if total else 0.0


def _distribuicao(valores: list[int]) -> dict[str, Any]:
    """Resumo estatístico de uma lista de números (soma, pares, repetição...)."""
    if not valores:
        return {}
    ordenados = sorted(valores)
    n = len(ordenados)

    def percentil(p: float) -> int:
        return ordenados[min(n - 1, int(p / 100 * n))]

    contagem = Counter(valores)
    return {
        "media": round(statistics.mean(valores), 2),
        "mediana": statistics.median(valores),
        "desvio_padrao": round(statistics.pstdev(valores), 2),
        "minimo": ordenados[0],
        "maximo": ordenados[-1],
        "p10": percentil(10),
        "p25": percentil(25),
        "p75": percentil(75),
        "p90": percentil(90),
        "mais_comuns": contagem.most_common(6),
    }


# ---------------------------------------------------------------------------
# 1. FREQUÊNCIA
# ---------------------------------------------------------------------------


def frequencia(base: list[dict], n: int | None = None) -> dict[int, dict[str, Any]]:
    """Quantas vezes cada dezena saiu e em que % dos concursos."""
    amostra = _janela(base, n)
    total = len(amostra)
    contagem = Counter(d for c in amostra for d in c["dezenas"])
    # Esperado: cada dezena sai em 15/25 = 60% dos concursos
    esperado = total * DEZENAS_POR_JOGO / TOTAL_DEZENAS
    return {
        dezena: {
            "vezes": contagem.get(dezena, 0),
            "pct": _pct(contagem.get(dezena, 0), total),
            # Desvio vs. o esperado pela probabilidade pura (em %)
            "desvio_vs_esperado": round(
                100 * (contagem.get(dezena, 0) - esperado) / esperado, 2
            ) if esperado else 0.0,
        }
        for dezena in range(1, TOTAL_DEZENAS + 1)
    }


# ---------------------------------------------------------------------------
# 2. ATRASO
# ---------------------------------------------------------------------------


def atrasos(base: list[dict]) -> dict[int, dict[str, Any]]:
    """
    Atraso atual = há quantos concursos a dezena não sai (0 = saiu no último).
    Também calcula o maior atraso já registrado e o atraso médio.
    """
    resultado: dict[int, dict[str, Any]] = {}
    total = len(base)

    for dezena in range(1, TOTAL_DEZENAS + 1):
        indices = [i for i, c in enumerate(base) if dezena in c["dezenas"]]
        atual = total - 1 - indices[-1] if indices else total

        # Intervalos entre aparições consecutivas
        intervalos = [b - a - 1 for a, b in zip(indices, indices[1:])]
        resultado[dezena] = {
            "atraso_atual": atual,
            "maior_atraso_historico": max(intervalos + [atual]) if intervalos else atual,
            "atraso_medio": round(statistics.mean(intervalos), 2) if intervalos else 0.0,
        }
    return resultado


# ---------------------------------------------------------------------------
# 3 a 7. PADRÕES POR SORTEIO
# ---------------------------------------------------------------------------


def paridade(base: list[dict], n: int | None = None) -> dict[str, Any]:
    """Quantos números PARES saem por sorteio (o resto são ímpares)."""
    amostra = _janela(base, n)
    pares = [sum(1 for d in c["dezenas"] if d % 2 == 0) for c in amostra]
    dist = Counter(pares)
    total = len(amostra)
    return {
        "resumo": _distribuicao(pares),
        "distribuicao": {
            f"{k} pares / {DEZENAS_POR_JOGO - k} ímpares": {
                "vezes": v, "pct": _pct(v, total)
            }
            for k, v in sorted(dist.items())
        },
    }


def soma_dezenas(base: list[dict], n: int | None = None) -> dict[str, Any]:
    """Soma das 15 dezenas sorteadas. Mínimo teórico 120, máximo 270."""
    amostra = _janela(base, n)
    somas = [sum(c["dezenas"]) for c in amostra]
    resumo = _distribuicao(somas)
    total = len(amostra)
    dentro = sum(1 for s in somas if resumo["p10"] <= s <= resumo["p90"])
    resumo["faixa_central_80pct"] = [resumo["p10"], resumo["p90"]]
    resumo["pct_dentro_da_faixa"] = _pct(dentro, total)
    return resumo


def repeticao_concurso_anterior(base: list[dict], n: int | None = None) -> dict[str, Any]:
    """Quantas dezenas do concurso anterior se repetem no concurso seguinte."""
    amostra = _janela(base, n + 1 if n else None)
    repeticoes = [
        len(set(atual["dezenas"]) & set(anterior["dezenas"]))
        for anterior, atual in zip(amostra, amostra[1:])
    ]
    dist = Counter(repeticoes)
    total = len(repeticoes)
    return {
        "resumo": _distribuicao(repeticoes),
        "distribuicao": {
            f"{k} repetidas": {"vezes": v, "pct": _pct(v, total)}
            for k, v in sorted(dist.items())
        },
    }


def _contar_grupo(base: list[dict], grupo: list[int], n: int | None = None) -> dict[str, Any]:
    amostra = _janela(base, n)
    conjunto = set(grupo)
    quantidades = [len(conjunto & set(c["dezenas"])) for c in amostra]
    return {
        "tamanho_do_grupo": len(grupo),
        "media_por_sorteio": round(statistics.mean(quantidades), 2),
        "minimo": min(quantidades),
        "maximo": max(quantidades),
        "faixa_mais_comum": Counter(quantidades).most_common(3),
    }


def geografia(base: list[dict], n: int | None = None) -> dict[str, Any]:
    """Como as dezenas se espalham pelo volante."""
    return {
        "linhas": {nome: _contar_grupo(base, nums, n) for nome, nums in LINHAS.items()},
        "colunas": {nome: _contar_grupo(base, nums, n) for nome, nums in COLUNAS.items()},
        "quadrantes": {nome: _contar_grupo(base, nums, n) for nome, nums in QUADRANTES.items()},
        "moldura": _contar_grupo(base, MOLDURA, n),
        "miolo": _contar_grupo(base, MIOLO, n),
    }


def primos(base: list[dict], n: int | None = None) -> dict[str, Any]:
    amostra = _janela(base, n)
    quantidades = [sum(1 for d in c["dezenas"] if d in PRIMOS) for c in amostra]
    dist = Counter(quantidades)
    total = len(amostra)
    return {
        "resumo": _distribuicao(quantidades),
        "distribuicao": {
            f"{k} primos": {"vezes": v, "pct": _pct(v, total)}
            for k, v in sorted(dist.items())
        },
    }


# ---------------------------------------------------------------------------
# 7B. TESTE DE ALEATORIEDADE — "as dezenas quentes existem de verdade?"
# ---------------------------------------------------------------------------


def _qui2_p_valor(x: float, gl: int = 24) -> float:
    """
    Probabilidade de um sorteio 100% justo produzir um desvio tão grande quanto
    o observado. Fórmula exata para graus de liberdade pares — evita instalar
    a biblioteca scipy só para isto.
    """
    import math

    k = gl // 2
    termo = 1.0
    soma = 1.0
    for i in range(1, k):
        termo *= (x / 2) / i
        soma += termo
    return math.exp(-x / 2) * soma


def teste_aleatoriedade(base: list[dict], n: int | None = None) -> dict[str, Any]:
    """
    Compara a frequência observada com o que um sorteio perfeitamente justo
    produziria. Se o p-valor for alto (> 0,05), as diferenças entre dezenas
    "quentes" e "frias" são compatíveis com puro acaso.

    Detalhe técnico: como cada sorteio tira 15 bolas de 25 (sem reposição), a
    variância correta de cada componente é n * 0,25 — e não n * p, como na
    fórmula de qui-quadrado de manual. Usar a fórmula errada subestima o desvio.
    """
    amostra = _janela(base, n)
    total = len(amostra)
    contagem = Counter(d for c in amostra for d in c["dezenas"])
    esperado = total * DEZENAS_POR_JOGO / TOTAL_DEZENAS

    soma_quadrados = sum((contagem[d] - esperado) ** 2 for d in range(1, TOTAL_DEZENAS + 1))
    estatistica = soma_quadrados / (total * 0.25)
    p_valor = _qui2_p_valor(estatistica)

    return {
        "concursos_testados": total,
        "estatistica": round(estatistica, 2),
        "graus_de_liberdade": 24,
        "p_valor": round(p_valor, 5),
        "compativel_com_acaso": p_valor > 0.05,
        "leitura": (
            "As diferenças de frequência entre as dezenas são compatíveis com o acaso."
            if p_valor > 0.05
            else "Há desvio estatístico além do esperado pelo acaso nesta janela — "
                 "mas o tamanho do efeito é pequeno e não se sustenta em todas as épocas."
        ),
    }


# ---------------------------------------------------------------------------
# 8. PERFIL-ALVO — a "receita" que a Etapa 3 vai seguir
# ---------------------------------------------------------------------------


def perfil_alvo(base: list[dict], janela_recente: int = 100) -> dict[str, Any]:
    """
    Traduz a estatística em REGRAS PRÁTICAS para o gerador de jogos.
    Cada regra é a faixa onde cai a grande maioria dos sorteios reais.
    """
    par = paridade(base)["resumo"]
    som = soma_dezenas(base)
    rep = repeticao_concurso_anterior(base)["resumo"]
    pri = primos(base)["resumo"]
    mol = _contar_grupo(base, MOLDURA)
    mio = _contar_grupo(base, MIOLO)

    def faixa(resumo: dict) -> list[int]:
        return [resumo["p10"], resumo["p90"]]

    return {
        "soma_dezenas": {"faixa": som["faixa_central_80pct"], "media": som["media"]},
        "pares": {"faixa": faixa(par), "media": par["media"]},
        "primos": {"faixa": faixa(pri), "media": pri["media"]},
        "repetidas_do_anterior": {"faixa": faixa(rep), "media": rep["media"]},
        "moldura": {"media": mol["media_por_sorteio"], "faixa_comum": mol["faixa_mais_comum"]},
        "miolo": {"media": mio["media_por_sorteio"], "faixa_comum": mio["faixa_mais_comum"]},
        "linhas_min_max": {
            nome: [dados["minimo"], dados["maximo"]]
            for nome, dados in geografia(base)["linhas"].items()
        },
        "janela_recente_usada": janela_recente,
    }


# ---------------------------------------------------------------------------
# RELATÓRIO EXECUTIVO
# ---------------------------------------------------------------------------


def analisar(base: list[dict] | None = None, janela: int = 100) -> dict[str, Any]:
    base = base or carregar_base()
    if not base:
        raise RuntimeError("Base vazia. Rode a Etapa 1 antes (coleta ou importar_excel).")

    return {
        "meta": {
            "concursos_analisados": len(base),
            "primeiro": base[0]["concurso"],
            "ultimo": base[-1]["concurso"],
            "data_ultimo": base[-1]["data"],
            "janela_recente": janela,
        },
        "frequencia_historica": frequencia(base),
        "frequencia_recente": frequencia(base, janela),
        "atrasos": atrasos(base),
        "paridade": paridade(base),
        "soma": soma_dezenas(base),
        "repeticao": repeticao_concurso_anterior(base),
        "geografia": geografia(base),
        "primos": primos(base),
        "teste_aleatoriedade": {
            "historico_completo": teste_aleatoriedade(base),
            "ultimos_1000": teste_aleatoriedade(base, 1000),
            "ultimos_500": teste_aleatoriedade(base, 500),
        },
        "perfil_alvo": perfil_alvo(base, janela),
        "aviso": (
            "Análise estatística de dados históricos. Não é previsão. Cada sorteio "
            "é independente e todas as combinações têm a mesma probabilidade."
        ),
    }


def imprimir_relatorio(a: dict[str, Any]) -> None:
    m = a["meta"]
    print("=" * 66)
    print(f"ANÁLISE ESTATÍSTICA DA LOTOFÁCIL — concursos {m['primeiro']} a {m['ultimo']}")
    print(f"{m['concursos_analisados']} sorteios | último em {m['data_ultimo']}")
    print("=" * 66)

    # --- Frequência ---
    hist = a["frequencia_historica"]
    rec = a["frequencia_recente"]
    ranking = sorted(hist.items(), key=lambda x: -x[1]["vezes"])
    print(f"\n[1] FREQUÊNCIA — esperado por probabilidade pura: 60,00%")
    print("     Mais sorteadas                 Menos sorteadas")
    for i in range(5):
        d1, v1 = ranking[i]
        d2, v2 = ranking[-(i + 1)]
        print(f"  {i+1}º  dezena {d1:2d}: {v1['vezes']:5d}x ({v1['pct']:.2f}%)"
              f"      dezena {d2:2d}: {v2['vezes']:5d}x ({v2['pct']:.2f}%)")

    print(f"\n     Últimos {m['janela_recente']} concursos — quem esquentou/esfriou:")
    variacao = sorted(
        ((d, rec[d]["pct"] - hist[d]["pct"]) for d in rec), key=lambda x: -x[1]
    )
    quentes = ", ".join(f"{d} ({v:+.1f}p.p.)" for d, v in variacao[:4])
    frias = ", ".join(f"{d} ({v:+.1f}p.p.)" for d, v in variacao[-4:])
    print(f"       subiu : {quentes}")
    print(f"       caiu  : {frias}")

    # --- Atrasos ---
    print("\n[2] ATRASO ATUAL (concursos sem sair)")
    atr = sorted(a["atrasos"].items(), key=lambda x: -x[1]["atraso_atual"])
    for d, v in atr[:6]:
        print(f"  dezena {d:2d}: {v['atraso_atual']:2d} concursos"
              f"  (recorde histórico: {v['maior_atraso_historico']})")

    # --- Paridade ---
    print("\n[3] PARIDADE (pares em 15 dezenas)")
    top = sorted(a["paridade"]["distribuicao"].items(), key=lambda x: -x[1]["vezes"])[:4]
    for nome, v in top:
        print(f"  {nome:26} {v['vezes']:5d}x  ({v['pct']:.1f}%)")

    # --- Soma ---
    s = a["soma"]
    print("\n[4] SOMA DAS 15 DEZENAS (mínimo teórico 120, máximo 270)")
    print(f"  média {s['media']} | mediana {s['mediana']} | desvio {s['desvio_padrao']}")
    print(f"  faixa central (80% dos sorteios): {s['faixa_central_80pct'][0]} a {s['faixa_central_80pct'][1]}")
    print(f"  extremos já vistos: {s['minimo']} e {s['maximo']}")

    # --- Repetição ---
    print("\n[5] REPETIÇÃO DO CONCURSO ANTERIOR")
    r = a["repeticao"]["resumo"]
    top_r = sorted(a["repeticao"]["distribuicao"].items(), key=lambda x: -x[1]["vezes"])[:4]
    print(f"  média de {r['media']} dezenas repetidas por sorteio")
    for nome, v in top_r:
        print(f"  {nome:26} {v['vezes']:5d}x  ({v['pct']:.1f}%)")

    # --- Geografia ---
    g = a["geografia"]
    print("\n[6] GEOGRAFIA DO VOLANTE")
    print(f"  moldura (16 dezenas da borda): média {g['moldura']['media_por_sorteio']} por sorteio")
    print(f"  miolo   ( 9 dezenas do meio ): média {g['miolo']['media_por_sorteio']} por sorteio")
    print("  por linha do volante:")
    for nome, v in g["linhas"].items():
        print(f"    {nome} ({LINHAS[nome][0]:2d}-{LINHAS[nome][-1]:2d}): média {v['media_por_sorteio']} "
              f"| varia de {v['minimo']} a {v['maximo']}")

    # --- Primos ---
    p = a["primos"]["resumo"]
    print(f"\n[7] PRIMOS (há 9 primos entre 1 e 25)")
    print(f"  média {p['media']} por sorteio | mais comum: "
          + ", ".join(f"{k} primos ({v}x)" for k, v in p["mais_comuns"][:3]))

    # --- Teste de aleatoriedade ---
    print("\n[8] AS DEZENAS 'QUENTES' EXISTEM DE VERDADE?")
    for rotulo, t in a["teste_aleatoriedade"].items():
        marca = "compatível com acaso" if t["compativel_com_acaso"] else "desvio além do acaso"
        print(f"  {rotulo:20} n={t['concursos_testados']:5d}  "
              f"estatística={t['estatistica']:6.2f}  p={t['p_valor']:.4f}  -> {marca}")

    # --- Perfil-alvo ---
    pa = a["perfil_alvo"]
    print("\n" + "=" * 66)
    print("PERFIL-ALVO — regras que a Etapa 3 vai aplicar aos 13 jogos")
    print("=" * 66)
    print(f"  soma das dezenas entre {pa['soma_dezenas']['faixa'][0]} e {pa['soma_dezenas']['faixa'][1]}")
    print(f"  pares entre {pa['pares']['faixa'][0]} e {pa['pares']['faixa'][1]}")
    print(f"  primos entre {pa['primos']['faixa'][0]} e {pa['primos']['faixa'][1]}")
    print(f"  repetidas do último concurso entre {pa['repetidas_do_anterior']['faixa'][0]} e {pa['repetidas_do_anterior']['faixa'][1]}")
    print(f"  dezenas da moldura por volta de {pa['moldura']['media']}")
    print(f"\n{a['aviso']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Análise estatística da Lotofácil")
    parser.add_argument("--janela", type=int, default=100, help="tamanho da janela recente")
    parser.add_argument("--json", action="store_true", help="salva data/analise.json")
    args = parser.parse_args()

    resultado = analisar(janela=args.janela)
    imprimir_relatorio(resultado)

    if args.json:
        destino = Path(PASTA_DADOS) / "analise.json"
        destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nAnálise salva em {destino}")


# ---------------------------------------------------------------------------
# 9. NOTA DO RADAR — o quanto um jogo se parece com um sorteio típico
# ---------------------------------------------------------------------------

def _frequencia_relativa(valores: list[int], x: float) -> tuple[float, float]:
    """
    O quanto este valor é COMUM na história, comparado ao valor mais comum
    de todos. Devolve (pontuação 0-100, percentil 0-100).

    Por que não usar percentil puro: a soma 189 e a soma 195 são igualmente
    corriqueiras, mas o percentil puniria a 189 por não ser exatamente a
    mediana. Aqui o que conta é a frequência com que aquele valor aparece.
    """
    if not valores:
        return 50.0, 50.0

    # Janela de suavização proporcional à dispersão do critério
    desvio = statistics.pstdev(valores) or 1
    janela = max(0, round(desvio / 3))

    def quantos(centro: float) -> int:
        return sum(1 for v in valores if abs(v - centro) <= janela)

    pico = max(quantos(c) for c in set(valores))
    pontos = 100 * quantos(x) / pico if pico else 0

    menores = sum(1 for v in valores if v < x)
    iguais = sum(1 for v in valores if v == x)
    percentil = 100 * (menores + iguais / 2) / len(valores)
    return round(pontos, 1), round(percentil, 1)


def maior_sequencia(dezenas: list[int]) -> int:
    """Maior sequência de números consecutivos dentro do jogo (ex.: 7-8-9 = 3)."""
    ordenado = sorted(dezenas)
    maior = atual = 1
    for anterior, seguinte in zip(ordenado, ordenado[1:]):
        atual = atual + 1 if seguinte == anterior + 1 else 1
        maior = max(maior, atual)
    return maior


def nota_do_radar(jogo: list[int], base: list[dict]) -> dict[str, Any]:
    """
    Mede o quanto o jogo se PARECE com um resultado real, de 0 a 100.

    Para cada critério, mede o quanto aquele valor é COMUM nos sorteios reais.
    Valor tão frequente quanto o mais frequente de todos = 100 pontos.
    Valor que quase nunca aparece = perto de 0.

    ATENÇÃO — o que esta nota NÃO é:
    Ela não mede chance de prêmio. Um jogo com nota 100 e outro com nota 40
    têm exatamente a mesma probabilidade de serem sorteados. A nota mede
    semelhança com o padrão histórico, nada além disso.
    """
    ultimo = set(base[-1]["dezenas"]) if base else set()
    conjunto = set(jogo)

    # Valor do jogo e a série histórica correspondente, para cada critério
    criterios = {
        "soma": (
            sum(jogo),
            [sum(c["dezenas"]) for c in base],
        ),
        "pares": (
            sum(1 for d in jogo if d % 2 == 0),
            [sum(1 for d in c["dezenas"] if d % 2 == 0) for c in base],
        ),
        "primos": (
            len(conjunto & set(PRIMOS)),
            [len(set(c["dezenas"]) & set(PRIMOS)) for c in base],
        ),
        "repetidas": (
            len(conjunto & ultimo),
            [len(set(b["dezenas"]) & set(a["dezenas"])) for a, b in zip(base, base[1:])],
        ),
        "moldura": (
            len(conjunto & set(MOLDURA)),
            [len(set(c["dezenas"]) & set(MOLDURA)) for c in base],
        ),
        "miolo": (
            len(conjunto & set(MIOLO)),
            [len(set(c["dezenas"]) & set(MIOLO)) for c in base],
        ),
        # Sem este critério, um jogo absurdo como 01,02,...,15 passaria batido:
        # todos os outros indicadores dele ficam dentro do normal.
        "sequencia": (
            maior_sequencia(jogo),
            [maior_sequencia(c["dezenas"]) for c in base],
        ),
    }

    detalhes: dict[str, Any] = {}
    for nome, (valor, serie) in criterios.items():
        pontos, percentil = _frequencia_relativa(serie, valor)
        detalhes[nome] = {
            "valor": valor,
            "percentil": percentil,
            "pontos": pontos,
            "media_historica": round(statistics.mean(serie), 2),
        }

    nota = round(sum(d["pontos"] for d in detalhes.values()) / len(detalhes))

    # Distribuição por faixas de dezenas (1-6, 7-12, 13-18, 19-25)
    faixas = [
        len([d for d in jogo if 1 <= d <= 6]),
        len([d for d in jogo if 7 <= d <= 12]),
        len([d for d in jogo if 13 <= d <= 18]),
        len([d for d in jogo if 19 <= d <= 25]),
    ]

    return {
        "nota": nota,
        "detalhes": detalhes,
        "faixas": faixas,
        "pares": detalhes["pares"]["valor"],
        "impares": 15 - detalhes["pares"]["valor"],
        "aviso": (
            "A nota mede semelhança com o padrão histórico dos sorteios. "
            "NÃO mede chance de prêmio — todos os jogos têm a mesma probabilidade."
        ),
    }


def escolher_destaque(jogos: list[list[int]], base: list[dict]) -> dict[str, Any]:
    """Entre os 13 jogos, devolve o de maior aderência ao padrão histórico."""
    avaliados = [{"dezenas": j, **nota_do_radar(j, base)} for j in jogos]
    avaliados.sort(key=lambda x: -x["nota"])
    return avaliados[0]
