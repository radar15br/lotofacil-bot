"""
ETAPA 4 — CONFERÊNCIA AUTOMÁTICA E HISTÓRICO DE DESEMPENHO
===========================================================

O QUE ESTE MÓDULO FAZ

Depois que a Etapa 3 gerou os 13 jogos e o concurso aconteceu, este módulo:

1. Pega o resultado real do concurso na base local.
2. Confere quantos acertos cada um dos 13 jogos fez.
3. Calcula o prêmio de cada aposta usando o rateio REAL daquele concurso
   (os valores mudaram ao longo dos anos: 11 acertos pagava R$ 2,00 em 2003
   e paga R$ 7,00 hoje).
4. Guarda tudo em data/desempenho.json — o histórico que vira prova social.
5. Monta frases prontas para a legenda ("nossa média nos últimos 10 foi X").

REGRA DE HONESTIDADE DO MÓDULO

Cada registro é marcado como REAL ou SIMULADO:
  - real     = os jogos foram gerados ANTES do sorteio e ficaram salvos em disco
  - simulado = reconstrução do passado (backtest), útil para calibrar, mas que
               NUNCA pode ser apresentada como resultado obtido de verdade.
O resumo separa os dois. As frases de prova social usam só o que é real,
a menos que você peça explicitamente o contrário.

Como rodar:
    python -m src.desempenho --pendentes        # confere tudo que já tem resultado
    python -m src.desempenho --concurso 3757    # confere um concurso específico
    python -m src.desempenho --resumo 10        # prova social dos últimos 10
    python -m src.desempenho --simular 200      # popula histórico simulado
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.coleta import PASTA_DADOS, carregar_base
from src.jogos import PASTA_JOGOS, QTD_JOGOS, carregar_jogos, gerar_jogos

ARQUIVO_DESEMPENHO = PASTA_DADOS / "desempenho.json"

# Preço da aposta simples de 15 dezenas (Caixa, reajuste de julho/2025)
PRECO_APOSTA = 3.50

# Se um concurso antigo não trouxer o rateio, usamos a tabela vigente
PREMIOS_PADRAO = {11: 7.00, 12: 14.00, 13: 35.00}

FAIXAS_PREMIADAS = (11, 12, 13, 14, 15)


# ---------------------------------------------------------------------------
# CONFERÊNCIA
# ---------------------------------------------------------------------------


def _premio_da_faixa(registro_concurso: dict, acertos: int) -> float:
    """Valor pago por uma aposta com `acertos` naquele concurso específico."""
    if acertos < 11:
        return 0.0
    rateios = registro_concurso.get("rateios") or {}
    valor = rateios.get(str(acertos))
    if valor:
        return float(valor)
    return PREMIOS_PADRAO.get(acertos, 0.0)


def conferir(
    concurso: int,
    base: list[dict] | None = None,
    jogos: dict[str, Any] | None = None,
    simulado: bool = False,
) -> dict[str, Any]:
    """Confere os 13 jogos de um concurso contra o resultado real."""
    base = base or carregar_base()
    resultado_real = next((c for c in base if c["concurso"] == concurso), None)
    if resultado_real is None:
        raise RuntimeError(f"O concurso {concurso} ainda não está na base local.")

    jogos = jogos or carregar_jogos(concurso)
    if jogos is None:
        raise RuntimeError(
            f"Não encontrei os jogos do concurso {concurso}. "
            f"Rode: python -m src.jogos --concurso {concurso}"
        )

    sorteadas = set(resultado_real["dezenas"])
    detalhes = []
    for j in jogos["jogos"]:
        acertos = len(set(j["dezenas"]) & sorteadas)
        detalhes.append({
            "jogo": j["numero"],
            "dezenas": j["dezenas"],
            "acertos": acertos,
            "premio": round(_premio_da_faixa(resultado_real, acertos), 2),
        })

    acertos_lista = [d["acertos"] for d in detalhes]
    premio_total = round(sum(d["premio"] for d in detalhes), 2)
    investido = round(QTD_JOGOS * PRECO_APOSTA, 2)

    return {
        "concurso": concurso,
        "data": resultado_real["data"],
        "simulado": simulado,
        "dezenas_sorteadas": sorted(sorteadas),
        "jogos": detalhes,
        "melhor": max(acertos_lista),
        "pior": min(acertos_lista),
        "media": round(sum(acertos_lista) / len(acertos_lista), 2),
        "faixas": {str(f): sum(1 for a in acertos_lista if a == f) for f in FAIXAS_PREMIADAS},
        "apostas_premiadas": sum(1 for a in acertos_lista if a >= 11),
        "investido": investido,
        "retornado": premio_total,
        "saldo": round(premio_total - investido, 2),
    }


# ---------------------------------------------------------------------------
# HISTÓRICO EM DISCO
# ---------------------------------------------------------------------------


def carregar_historico() -> list[dict[str, Any]]:
    if not ARQUIVO_DESEMPENHO.exists():
        return []
    return json.loads(ARQUIVO_DESEMPENHO.read_text(encoding="utf-8"))


def salvar_historico(registros: list[dict[str, Any]]) -> None:
    unicos = {(r["concurso"], r["simulado"]): r for r in registros}
    ordenados = [unicos[k] for k in sorted(unicos, key=lambda x: (x[1], x[0]))]
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    temporario = ARQUIVO_DESEMPENHO.with_suffix(".tmp")
    temporario.write_text(json.dumps(ordenados, ensure_ascii=False, indent=1), encoding="utf-8")
    temporario.replace(ARQUIVO_DESEMPENHO)


def registrar(conferencia: dict[str, Any]) -> None:
    historico = carregar_historico()
    historico.append(conferencia)
    salvar_historico(historico)


def conferir_pendentes(verboso: bool = True) -> list[dict[str, Any]]:
    """
    Percorre todos os arquivos de jogos gerados e confere os que já têm
    resultado publicado e ainda não foram conferidos.
    """
    base = carregar_base()
    publicados = {c["concurso"] for c in base}
    ja_conferidos = {r["concurso"] for r in carregar_historico() if not r["simulado"]}

    if not PASTA_JOGOS.exists():
        if verboso:
            print("Nenhum jogo gerado ainda.")
        return []

    novos = []
    for arquivo in sorted(PASTA_JOGOS.glob("*.json")):
        numero = int(arquivo.stem)
        if numero in ja_conferidos or numero not in publicados:
            continue
        conferencia = conferir(numero, base=base)
        registrar(conferencia)
        novos.append(conferencia)
        if verboso:
            print(f"Concurso {numero} conferido: melhor {conferencia['melhor']} acertos, "
                  f"{conferencia['apostas_premiadas']} apostas premiadas, "
                  f"saldo {formatar_reais(conferencia['saldo'])}")

    if verboso and not novos:
        print("Nada pendente. Todos os jogos gerados já foram conferidos.")
    return novos


def simular_historico(quantos: int = 200, verboso: bool = True) -> int:
    """
    Preenche o histórico com registros SIMULADOS: para cada concurso passado,
    gera os jogos usando só os dados da véspera e confere. Serve para calibrar
    e para ter base de comparação — nunca para apresentar como desempenho real.
    """
    base = carregar_base()
    historico = [r for r in carregar_historico() if not r["simulado"]]

    for pos in range(len(base) - quantos, len(base)):
        concurso = base[pos]["concurso"]
        jogos = gerar_jogos(base[:pos], concurso_alvo=concurso)
        historico.append(conferir(concurso, base=base, jogos=jogos, simulado=True))
        if verboso and (pos - (len(base) - quantos) + 1) % 50 == 0:
            print(f"  ... {pos - (len(base) - quantos) + 1}/{quantos} concursos simulados")

    salvar_historico(historico)
    return quantos


# ---------------------------------------------------------------------------
# RESUMO / PROVA SOCIAL
# ---------------------------------------------------------------------------


def num(valor: float, casas: int = 2) -> str:
    """Formata número no padrão brasileiro: 9,01 · 1.234,5"""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_reais(valor: float) -> str:
    texto = f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-R$ " if valor < 0 else "R$ ") + texto


def resumo(janela: int = 10, incluir_simulados: bool = False) -> dict[str, Any]:
    """Métricas acumuladas dos últimos `janela` concursos conferidos."""
    historico = [r for r in carregar_historico() if incluir_simulados or not r["simulado"]]
    if not historico:
        return {"vazio": True, "mensagem": "Ainda não há concursos conferidos."}

    historico.sort(key=lambda r: r["concurso"])
    recorte = historico[-janela:]

    todos_acertos = [j["acertos"] for r in recorte for j in r["jogos"]]
    apostas = len(todos_acertos)
    premiadas = sum(1 for a in todos_acertos if a >= 11)
    investido = round(sum(r["investido"] for r in recorte), 2)
    retornado = round(sum(r["retornado"] for r in recorte), 2)

    faixas = {str(f): sum(int(r["faixas"][str(f)]) for r in recorte) for f in FAIXAS_PREMIADAS}
    melhor = max(recorte, key=lambda r: r["melhor"])

    # Sequência atual de concursos com ao menos uma aposta premiada
    sequencia = 0
    for r in reversed(recorte):
        if r["apostas_premiadas"] > 0:
            sequencia += 1
        else:
            break

    return {
        "vazio": False,
        "janela": len(recorte),
        "primeiro_concurso": recorte[0]["concurso"],
        "ultimo_concurso": recorte[-1]["concurso"],
        "contem_simulados": any(r["simulado"] for r in recorte),
        "media_de_acertos": round(sum(todos_acertos) / apostas, 2),
        "media_do_melhor_jogo": round(sum(r["melhor"] for r in recorte) / len(recorte), 2),
        "melhor_resultado": {"acertos": melhor["melhor"], "concurso": melhor["concurso"]},
        "apostas": apostas,
        "apostas_premiadas": premiadas,
        "pct_apostas_premiadas": round(100 * premiadas / apostas, 1),
        "concursos_com_premio": sum(1 for r in recorte if r["apostas_premiadas"] > 0),
        "pct_concursos_com_premio": round(100 * sum(1 for r in recorte if r["apostas_premiadas"] > 0) / len(recorte), 1),
        "sequencia_atual_com_premio": sequencia,
        "faixas": faixas,
        "investido": investido,
        "retornado": retornado,
        "saldo": round(retornado - investido, 2),
        "retorno_pct": round(100 * (retornado - investido) / investido, 1) if investido else 0,
    }


def frases_prova_social(janela: int = 10, incluir_simulados: bool = False) -> list[str]:
    """
    Frases prontas para a legenda. Todas verificáveis no arquivo de histórico.
    Nada aqui promete resultado futuro.
    """
    r = resumo(janela, incluir_simulados)
    if r.get("vazio"):
        return ["Primeira publicação: o histórico de desempenho começa a partir de hoje."]

    marca = " (simulação)" if r["contem_simulados"] else ""
    frases = [
        f"Média de {num(r['media_de_acertos'])} acertos por jogo nos últimos {num(r['janela'], 0)} concursos{marca}.",
        f"Melhor marca: {r['melhor_resultado']['acertos']} acertos no concurso {r['melhor_resultado']['concurso']}.",
        f"{r['concursos_com_premio']} dos últimos {num(r['janela'], 0)} concursos tiveram ao menos uma aposta premiada "
        f"({num(r['pct_concursos_com_premio'], 0)}%).",
        f"{num(r['apostas_premiadas'], 0)} apostas premiadas em {num(r['apostas'], 0)} jogadas "
        f"({num(r['pct_apostas_premiadas'], 1)}%).",
    ]
    if r["sequencia_atual_com_premio"] >= 3:
        frases.append(f"{r['sequencia_atual_com_premio']} concursos seguidos com aposta premiada.")
    frases.append(
        f"Retorno acumulado no período: {formatar_reais(r['retornado'])} sobre "
        f"{formatar_reais(r['investido'])} apostados ({'+' if r['retorno_pct'] >= 0 else ''}{num(r['retorno_pct'], 1)}%)."
    )
    return frases


# ---------------------------------------------------------------------------
# LINHA DE COMANDO
# ---------------------------------------------------------------------------


def imprimir_resumo(r: dict[str, Any]) -> None:
    if r.get("vazio"):
        print(r["mensagem"])
        return
    print("=" * 62)
    print(f"DESEMPENHO — concursos {r['primeiro_concurso']} a {r['ultimo_concurso']} "
          f"({r['janela']} concursos)" + ("  [INCLUI SIMULADOS]" if r["contem_simulados"] else ""))
    print("=" * 62)
    print(f"  média de acertos por jogo      : {r['media_de_acertos']}")
    print(f"  média do melhor jogo do dia    : {r['media_do_melhor_jogo']}")
    print(f"  melhor resultado               : {r['melhor_resultado']['acertos']} acertos "
          f"(concurso {r['melhor_resultado']['concurso']})")
    print(f"  apostas premiadas              : {r['apostas_premiadas']} de {r['apostas']} "
          f"({r['pct_apostas_premiadas']}%)")
    print(f"  concursos com prêmio           : {r['concursos_com_premio']} de {r['janela']} "
          f"({r['pct_concursos_com_premio']}%)")
    print(f"  sequência atual com prêmio     : {r['sequencia_atual_com_premio']} concursos")
    print("  por faixa: " + " | ".join(f"{f}: {v}" for f, v in r["faixas"].items()))
    print(f"\n  investido                      : {formatar_reais(r['investido'])}")
    print(f"  retornado                      : {formatar_reais(r['retornado'])}")
    print(f"  saldo                          : {formatar_reais(r['saldo'])} ({r['retorno_pct']:+.1f}%)")
    print("\n  FRASES PARA A LEGENDA:")
    for f in frases_prova_social(r["janela"], r["contem_simulados"]):
        print(f"   - {f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Conferência e histórico de desempenho")
    parser.add_argument("--concurso", type=int, help="confere um concurso específico")
    parser.add_argument("--pendentes", action="store_true", help="confere tudo que já tem resultado")
    parser.add_argument("--resumo", type=int, nargs="?", const=10, help="resumo dos últimos N concursos")
    parser.add_argument("--simular", type=int, help="popula histórico SIMULADO com N concursos")
    parser.add_argument("--incluir-simulados", action="store_true")
    args = parser.parse_args()

    if args.simular:
        n = simular_historico(args.simular)
        print(f"{n} concursos simulados e gravados em {ARQUIVO_DESEMPENHO}")
        imprimir_resumo(resumo(n, incluir_simulados=True))
    elif args.concurso:
        c = conferir(args.concurso)
        registrar(c)
        print(f"Concurso {c['concurso']} ({c['data']}) — sorteadas: "
              f"{' '.join(f'{d:02d}' for d in c['dezenas_sorteadas'])}\n")
        for j in c["jogos"]:
            premio = f"  {formatar_reais(j['premio'])}" if j["premio"] else ""
            print(f"  jogo {j['jogo']:2d}: {j['acertos']:2d} acertos{premio}")
        print(f"\n  melhor {c['melhor']} | média {c['media']} | "
              f"premiadas {c['apostas_premiadas']} | saldo {formatar_reais(c['saldo'])}")
    elif args.pendentes:
        conferir_pendentes()
        imprimir_resumo(resumo(10, args.incluir_simulados))
    else:
        imprimir_resumo(resumo(args.resumo or 10, args.incluir_simulados))
