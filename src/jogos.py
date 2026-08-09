"""
ETAPA 3 — GERAÇÃO DOS 13 JOGOS
===============================

O QUE ESTE MÓDULO FAZ, EM PORTUGUÊS SIMPLES

Ele monta 13 jogos de 15 dezenas seguindo o "perfil-alvo" que a Etapa 2
calculou — as faixas onde caem 80% dos sorteios reais (soma, pares, primos,
repetição do último concurso, moldura/miolo). O resultado são jogos com CARA
de resultado real, não sequências esquisitas tipo 1-2-3-4-5.

TRÊS GARANTIAS QUE O GERADOR DÁ

1. Nenhum jogo se repete. Mais que isso: dois jogos nunca compartilham mais de
   13 das 15 dezenas — se compartilhassem 14, seriam praticamente o mesmo jogo.
2. As 25 dezenas aparecem de forma equilibrada. Como 13 jogos x 15 dezenas =
   195 posições e existem 25 dezenas, cada uma deveria aparecer 7,8 vezes. O
   gerador mantém todas entre 7 e 9 aparições.
3. Mesmo concurso, mesmos jogos. A "semente" aleatória é o número do concurso.
   Rodar duas vezes produz exatamente o mesmo resultado — isso é o que torna a
   prova social auditável: ninguém pode dizer que você escolheu os jogos depois.

O QUE ELE NÃO FAZ

Não aumenta sua chance de ganhar. A chance de 15 acertos em UM jogo é de
1 em 3.268.760. Com 13 jogos, 1 em 251.443. Os filtros mudam o "formato" do
jogo, não a probabilidade — todas as combinações continuam igualmente prováveis.

Como rodar:
    python -m src.jogos                    # gera os jogos do próximo concurso
    python -m src.jogos --concurso 3757    # gera para um concurso específico
    python -m src.jogos --backtest 100     # testa o gerador nos últimos 100 concursos
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from src import analise as an
from src.coleta import PASTA_DADOS, carregar_base

PASTA_JOGOS = PASTA_DADOS / "jogos"

QTD_JOGOS = 13
DEZENAS_POR_JOGO = 15
TOTAL_DEZENAS = 25

# Duas apostas não podem compartilhar mais que isto (14 seria "o mesmo jogo")
MAX_DEZENAS_EM_COMUM = 13

# Quantas vezes cada dezena deve aparecer no conjunto dos 13 jogos
USO_ALVO = QTD_JOGOS * DEZENAS_POR_JOGO / TOTAL_DEZENAS   # 7,8
USO_MIN, USO_MAX = 7, 9


# ---------------------------------------------------------------------------
# REGRAS (vindas do perfil-alvo da Etapa 2)
# ---------------------------------------------------------------------------


def montar_regras(base: list[dict]) -> dict[str, Any]:
    """Traduz o perfil-alvo da Etapa 2 em faixas que um jogo precisa respeitar."""
    p = an.perfil_alvo(base)
    return {
        "soma": tuple(p["soma_dezenas"]["faixa"]),
        "pares": tuple(p["pares"]["faixa"]),
        "primos": tuple(p["primos"]["faixa"]),
        "repetidas": tuple(p["repetidas_do_anterior"]["faixa"]),
        "moldura": (8, 11),
        "miolo": (4, 7),
    }


def medir(jogo: list[int], ultimo: set[int]) -> dict[str, int]:
    """Calcula os indicadores de um jogo."""
    conjunto = set(jogo)
    return {
        "soma": sum(jogo),
        "pares": sum(1 for d in jogo if d % 2 == 0),
        "primos": len(conjunto & set(an.PRIMOS)),
        "repetidas": len(conjunto & ultimo),
        "moldura": len(conjunto & set(an.MOLDURA)),
        "miolo": len(conjunto & set(an.MIOLO)),
    }


def dentro_das_regras(jogo: list[int], ultimo: set[int], regras: dict) -> bool:
    m = medir(jogo, ultimo)
    return all(regras[k][0] <= m[k] <= regras[k][1] for k in regras)


# ---------------------------------------------------------------------------
# SORTEIO PONDERADO
# ---------------------------------------------------------------------------


def _sortear_ponderado(rng: random.Random, pesos: dict[int, float], quantos: int) -> list[int]:
    """
    Sorteia `quantos` números sem repetição, respeitando pesos.
    Método de Efraimidis-Spirakis: cada item recebe a chave rand^(1/peso) e
    ficam os maiores. Peso maior = mais chance de entrar, sem virar certeza.
    """
    chaves = {d: rng.random() ** (1.0 / max(peso, 1e-9)) for d, peso in pesos.items()}
    return sorted(sorted(chaves, key=chaves.get, reverse=True)[:quantos])


def _pesos(uso: dict[int, int], jogos_feitos: int, forca: float = 2.2) -> dict[int, float]:
    """
    Dezenas usadas MENOS do que deveriam ganham peso maior. É isso que mantém
    as 25 dezenas equilibradas ao longo dos 13 jogos.
    """
    esperado = USO_ALVO * (jogos_feitos + 1) / QTD_JOGOS
    return {
        d: max(0.05, 1.0 + forca * (esperado - uso.get(d, 0)) / max(esperado, 1))
        for d in range(1, TOTAL_DEZENAS + 1)
    }


# ---------------------------------------------------------------------------
# GERAÇÃO
# ---------------------------------------------------------------------------


def gerar_jogos(
    base: list[dict] | None = None,
    concurso_alvo: int | None = None,
    quantidade: int = QTD_JOGOS,
    tentativas_max: int = 60000,
) -> dict[str, Any]:
    base = base or carregar_base()
    if not base:
        raise RuntimeError("Base vazia. Rode a Etapa 1 antes.")

    ultimo_registro = base[-1]
    concurso_alvo = concurso_alvo or ultimo_registro["concurso"] + 1
    ultimo = set(ultimo_registro["dezenas"])
    regras = montar_regras(base)

    # Semente = número do concurso. Mesmo concurso -> mesmos jogos, sempre.
    rng = random.Random(concurso_alvo)

    jogos: list[list[int]] = []
    uso: dict[int, int] = {d: 0 for d in range(1, TOTAL_DEZENAS + 1)}
    tentativas = 0

    while len(jogos) < quantidade and tentativas < tentativas_max:
        tentativas += 1
        restantes = quantidade - len(jogos)

        # Dezenas que PRECISAM entrar agora, senão não alcançam o uso mínimo.
        # Ex.: faltam 3 jogos e a dezena 7 só apareceu 4 vezes (mínimo é 7)
        # -> ela tem que entrar nos 3 jogos que sobraram.
        obrigatorias = [
            d for d in range(1, TOTAL_DEZENAS + 1)
            if USO_MIN - uso[d] >= restantes and uso[d] < USO_MAX
        ]
        if len(obrigatorias) > DEZENAS_POR_JOGO:
            raise RuntimeError("Regras de equilíbrio impossíveis de cumprir.")

        # As demais são sorteadas com peso, entre as que ainda cabem
        disponiveis = {
            d: p for d, p in _pesos(uso, len(jogos)).items()
            if d not in obrigatorias and uso[d] < USO_MAX
        }
        faltam = DEZENAS_POR_JOGO - len(obrigatorias)
        if len(disponiveis) < faltam:
            continue

        candidato = sorted(obrigatorias + _sortear_ponderado(rng, disponiveis, faltam))

        if not dentro_das_regras(candidato, ultimo, regras):
            continue
        # Nenhum jogo pode ser quase idêntico a outro já aceito
        if any(len(set(candidato) & set(j)) > MAX_DEZENAS_EM_COMUM for j in jogos):
            continue
        # Nenhuma dezena pode estourar o teto de aparições
        if any(uso[d] + 1 > USO_MAX for d in candidato):
            continue

        jogos.append(candidato)
        for d in candidato:
            uso[d] += 1

    if len(jogos) < quantidade:
        raise RuntimeError(
            f"Só consegui montar {len(jogos)} de {quantidade} jogos em {tentativas} tentativas. "
            "As regras podem estar restritivas demais."
        )

    # O destaque é fixado AGORA e gravado em disco. Se fosse recalculado depois
    # do sorteio, a base já teria mudado e poderia apontar outro jogo — o post
    # de resultado precisa conferir exatamente o jogo que foi publicado.
    destaque = an.escolher_destaque(jogos, base)

    return {
        "destaque": destaque,
        "concurso_alvo": concurso_alvo,
        "gerado_a_partir_do_concurso": ultimo_registro["concurso"],
        "data_base": ultimo_registro["data"],
        "dezenas_do_ultimo_concurso": sorted(ultimo),
        "regras_aplicadas": {k: list(v) for k, v in regras.items()},
        "jogos": [
            {
                "numero": i + 1,
                "dezenas": jogo,
                "indicadores": medir(jogo, ultimo),
            }
            for i, jogo in enumerate(jogos)
        ],
        "uso_das_dezenas": uso,
        "tentativas": tentativas,
        "conferencia": conferir_conjunto(jogos, ultimo, regras),
        "probabilidade": {
            "um_jogo_15_acertos": "1 em 3.268.760",
            "treze_jogos_15_acertos": "1 em 251.443",
            "observacao": (
                "Os filtros estatísticos NÃO alteram esta probabilidade. Todas as "
                "combinações têm a mesma chance; os filtros apenas dão aos jogos o "
                "formato típico de um resultado real."
            ),
        },
    }


def conferir_conjunto(jogos: list[list[int]], ultimo: set[int], regras: dict) -> dict[str, Any]:
    """Auditoria: prova que as 3 garantias do gerador foram cumpridas."""
    uso = {d: sum(1 for j in jogos if d in j) for d in range(1, TOTAL_DEZENAS + 1)}
    sobreposicoes = [
        len(set(a) & set(b))
        for i, a in enumerate(jogos) for b in jogos[i + 1:]
    ]
    return {
        "jogos_gerados": len(jogos),
        "jogos_duplicados": len(jogos) - len({tuple(j) for j in jogos}),
        "max_dezenas_em_comum": max(sobreposicoes) if sobreposicoes else 0,
        "media_dezenas_em_comum": round(sum(sobreposicoes) / len(sobreposicoes), 2) if sobreposicoes else 0,
        "uso_minimo": min(uso.values()),
        "uso_maximo": max(uso.values()),
        "dezenas_nunca_usadas": [d for d, v in uso.items() if v == 0],
        "todos_dentro_das_regras": all(dentro_das_regras(j, ultimo, regras) for j in jogos),
    }


# ---------------------------------------------------------------------------
# ARQUIVO
# ---------------------------------------------------------------------------


def salvar(resultado: dict[str, Any]) -> Path:
    PASTA_JOGOS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_JOGOS / f"{resultado['concurso_alvo']}.json"
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    return destino


def carregar_jogos(concurso: int) -> dict[str, Any] | None:
    arquivo = PASTA_JOGOS / f"{concurso}.json"
    if not arquivo.exists():
        return None
    return json.loads(arquivo.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# BACKTEST — o gerador teria funcionado no passado?
# ---------------------------------------------------------------------------


def backtest(base: list[dict] | None = None, quantos: int = 100) -> dict[str, Any]:
    """
    Simula o passado com honestidade: para cada um dos últimos N concursos,
    gera os jogos usando SOMENTE os dados disponíveis até o concurso anterior
    e confere quantos acertos teria feito. Sem olhar o futuro.
    """
    base = base or carregar_base()
    resultados: list[dict[str, Any]] = []

    for pos in range(len(base) - quantos, len(base)):
        historico = base[:pos]                  # tudo que se sabia na véspera
        real = set(base[pos]["dezenas"])        # o que saiu de fato
        saida = gerar_jogos(historico, concurso_alvo=base[pos]["concurso"])

        acertos = [len(set(j["dezenas"]) & real) for j in saida["jogos"]]
        resultados.append({
            "concurso": base[pos]["concurso"],
            "melhor": max(acertos),
            "media": round(sum(acertos) / len(acertos), 2),
            "premiados_11_ou_mais": sum(1 for a in acertos if a >= 11),
            "faixas": {str(f): sum(1 for a in acertos if a == f) for f in range(11, 16)},
        })

    todos = [r["media"] for r in resultados]
    melhores = [r["melhor"] for r in resultados]
    premiados = sum(r["premiados_11_ou_mais"] for r in resultados)
    total_apostas = len(resultados) * QTD_JOGOS

    faixas_totais = {f: sum(r["faixas"][str(f)] for r in resultados) for f in range(11, 16)}

    return {
        "concursos_testados": len(resultados),
        "apostas_simuladas": total_apostas,
        "media_de_acertos_por_jogo": round(sum(todos) / len(todos), 2),
        "media_do_melhor_jogo": round(sum(melhores) / len(melhores), 2),
        "melhor_resultado_absoluto": max(melhores),
        "apostas_premiadas_11_ou_mais": premiados,
        "pct_apostas_premiadas": round(100 * premiados / total_apostas, 2),
        "faixas": faixas_totais,
        "concursos_com_ao_menos_um_premio": sum(1 for r in resultados if r["premiados_11_ou_mais"] > 0),
        "detalhe": resultados[-10:],
    }


# ---------------------------------------------------------------------------
# LINHA DE COMANDO
# ---------------------------------------------------------------------------


def imprimir(resultado: dict[str, Any]) -> None:
    print("=" * 64)
    print(f"13 JOGOS PARA O CONCURSO {resultado['concurso_alvo']}")
    print(f"gerados a partir do concurso {resultado['gerado_a_partir_do_concurso']} "
          f"({resultado['data_base']})")
    print("=" * 64)
    print(f"último resultado: {' '.join(f'{d:02d}' for d in resultado['dezenas_do_ultimo_concurso'])}\n")

    print("  #   dezenas                                              soma  par  pri  rep")
    for j in resultado["jogos"]:
        i = j["indicadores"]
        dz = " ".join(f"{d:02d}" for d in j["dezenas"])
        print(f" {j['numero']:2d}   {dz}   {i['soma']:3d}   {i['pares']:2d}   {i['primos']:2d}   {i['repetidas']:2d}")

    c = resultado["conferencia"]
    print("\n--- AUDITORIA DO CONJUNTO ---")
    print(f"  jogos duplicados            : {c['jogos_duplicados']}")
    print(f"  máx. dezenas em comum       : {c['max_dezenas_em_comum']} (limite {MAX_DEZENAS_EM_COMUM})")
    print(f"  média de dezenas em comum   : {c['media_dezenas_em_comum']}")
    print(f"  uso das dezenas             : de {c['uso_minimo']} a {c['uso_maximo']} vezes (alvo {USO_ALVO})")
    print(f"  dezenas nunca usadas        : {c['dezenas_nunca_usadas'] or 'nenhuma'}")
    print(f"  todos dentro das regras     : {'sim' if c['todos_dentro_das_regras'] else 'NÃO'}")
    print(f"\nchance de 15 acertos com os 13 jogos: {resultado['probabilidade']['treze_jogos_15_acertos']}")
    print(resultado["probabilidade"]["observacao"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera os 13 jogos da Lotofácil")
    parser.add_argument("--concurso", type=int, default=None, help="concurso alvo")
    parser.add_argument("--backtest", type=int, default=0, help="testa o gerador em N concursos passados")
    args = parser.parse_args()

    if args.backtest:
        r = backtest(quantos=args.backtest)
        print("=" * 64)
        print(f"BACKTEST — {r['concursos_testados']} concursos, {r['apostas_simuladas']} apostas simuladas")
        print("=" * 64)
        print(f"  média de acertos por jogo        : {r['media_de_acertos_por_jogo']}")
        print(f"  média do melhor jogo do dia      : {r['media_do_melhor_jogo']}")
        print(f"  melhor resultado absoluto        : {r['melhor_resultado_absoluto']} acertos")
        print(f"  apostas premiadas (11+)          : {r['apostas_premiadas_11_ou_mais']} "
              f"({r['pct_apostas_premiadas']}% das apostas)")
        print(f"  concursos com ao menos 1 prêmio  : {r['concursos_com_ao_menos_um_premio']} de {r['concursos_testados']}")
        print("  por faixa: " + " | ".join(f"{f} acertos: {v}" for f, v in r["faixas"].items()))
    else:
        resultado = gerar_jogos(concurso_alvo=args.concurso)
        imprimir(resultado)
        caminho = salvar(resultado)
        print(f"\nJogos salvos em {caminho}")
