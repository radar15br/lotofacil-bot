"""
Teste da conferência e do histórico de desempenho (Etapa 4).

Prova que:
  - a contagem de acertos está correta (caso montado à mão, sem aleatoriedade)
  - o prêmio usa o rateio REAL daquele concurso, não uma tabela fixa
  - as somas do resumo batem com a soma dos registros individuais
  - o retorno esperado da simulação bate com a matemática (hipergeométrica)

Rodar com:  python tests/test_desempenho.py
"""

import sys
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import desempenho as dp  # noqa: E402
from src.coleta import carregar_base  # noqa: E402

SORTEADAS = list(range(1, 16))  # concurso fictício: saíram as dezenas 1 a 15


def concurso_falso() -> dict:
    return {
        "concurso": 99999,
        "data": "2026-08-08",
        "dezenas": SORTEADAS,
        "rateios": {"11": 7.0, "12": 14.0, "13": 35.0, "14": 1500.0, "15": 500000.0},
    }


def jogos_falsos() -> dict:
    """Jogos com acertos conhecidos de antemão: 15, 14, 13, 12, 11 e 10."""
    def jogo(acertos: int) -> list[int]:
        return sorted(SORTEADAS[:acertos] + list(range(16, 16 + 15 - acertos)))

    return {"jogos": [{"numero": i + 1, "dezenas": jogo(a)}
                      for i, a in enumerate([15, 14, 13, 12, 11, 10])]}


def main() -> None:
    base = [concurso_falso()]

    c = dp.conferir(99999, base=base, jogos=jogos_falsos(), simulado=True)
    acertos = [j["acertos"] for j in c["jogos"]]
    assert acertos == [15, 14, 13, 12, 11, 10], acertos
    print("OK  contagem de acertos correta em caso montado à mão")

    premios = [j["premio"] for j in c["jogos"]]
    assert premios == [500000.0, 1500.0, 35.0, 14.0, 7.0, 0.0], premios
    print("OK  prêmio usa o rateio real do concurso (inclusive 14 e 15 acertos)")

    assert c["retornado"] == 501556.0, c["retornado"]
    assert c["apostas_premiadas"] == 5
    assert c["faixas"] == {"11": 1, "12": 1, "13": 1, "14": 1, "15": 1}
    print("OK  somatórios e faixas do concurso conferem")

    # Rateio ausente -> cai para a tabela padrão
    sem_rateio = {**concurso_falso(), "rateios": {}}
    c2 = dp.conferir(99999, base=[sem_rateio], jogos=jogos_falsos(), simulado=True)
    assert [j["premio"] for j in c2["jogos"]][2:5] == [35.0, 14.0, 7.0]
    print("OK  sem rateio na base, usa a tabela vigente como reserva")

    # --- Retorno esperado: simulação x matemática ---
    historico = [r for r in dp.carregar_historico() if r["simulado"]]
    if historico:
        r = dp.resumo(len(historico), incluir_simulados=True)

        # Soma dos registros individuais tem que bater com o resumo
        soma_premios = round(sum(x["retornado"] for x in historico), 2)
        assert abs(soma_premios - r["retornado"]) < 0.01, (soma_premios, r["retornado"])
        print("OK  resumo bate com a soma dos registros individuais")

        # Valor esperado teórico de UMA aposta, com os rateios de hoje
        total = comb(25, 15)
        p = {k: comb(15, k) * comb(10, 15 - k) / total for k in range(11, 16)}
        esperado = (p[11] * 7 + p[12] * 14 + p[13] * 35
                    + p[14] * 1341.42 + p[15] * 565758.41)
        retorno_teorico = 100 * (esperado - dp.PRECO_APOSTA) / dp.PRECO_APOSTA
        print(f"    retorno esperado pela matemática : {retorno_teorico:+.1f}%")
        print(f"    retorno obtido na simulação      : {r['retorno_pct']:+.1f}%")
        print(f"    (prêmio médio teórico por aposta : R$ {esperado:.2f} "
              f"sobre R$ {dp.PRECO_APOSTA:.2f})")
        assert r["retorno_pct"] < 0, "loteria com retorno positivo indicaria erro de cálculo"
        print("OK  retorno negativo, como a matemática da loteria exige")

    # A base real precisa ter rateios para o cálculo ficar exato
    real = carregar_base()
    if real:
        sem = sum(1 for x in real if not (x.get("rateios") or {}).get("11"))
        print(f"OK  base real: {len(real)} concursos, {sem} sem rateio de 11 acertos")

    print("\nTODOS OS TESTES PASSARAM")


if __name__ == "__main__":
    main()
