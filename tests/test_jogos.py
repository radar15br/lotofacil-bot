"""
Teste do gerador de jogos (Etapa 3).

Prova as garantias prometidas, em 200 gerações seguidas:
  - sempre monta os 13 jogos
  - nenhum jogo duplicado
  - nenhum par de jogos com mais de 13 dezenas em comum
  - cada dezena aparece de 7 a 9 vezes no conjunto
  - todos os jogos respeitam o perfil-alvo
  - mesma semente -> mesmo resultado (auditável)

Rodar com:  python tests/test_jogos.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.coleta import carregar_base  # noqa: E402
from src.jogos import (  # noqa: E402
    MAX_DEZENAS_EM_COMUM, QTD_JOGOS, USO_MAX, USO_MIN, gerar_jogos,
)

QUANTAS = 200


def main() -> None:
    base = carregar_base()
    if not base:
        print("Base vazia — rode a Etapa 1 antes."); return

    falhas = []
    for i in range(QUANTAS):
        # Usa um recorte diferente da base a cada volta, simulando dias diferentes
        historico = base[: len(base) - i]
        r = gerar_jogos(historico)
        c = r["conferencia"]

        if c["jogos_gerados"] != QTD_JOGOS:
            falhas.append((i, "quantidade", c["jogos_gerados"]))
        if c["jogos_duplicados"] != 0:
            falhas.append((i, "duplicados", c["jogos_duplicados"]))
        if c["max_dezenas_em_comum"] > MAX_DEZENAS_EM_COMUM:
            falhas.append((i, "sobreposicao", c["max_dezenas_em_comum"]))
        if not (USO_MIN <= c["uso_minimo"] and c["uso_maximo"] <= USO_MAX):
            falhas.append((i, "equilibrio", (c["uso_minimo"], c["uso_maximo"])))
        if not c["todos_dentro_das_regras"]:
            falhas.append((i, "regras", False))

    print(f"OK  {QUANTAS} gerações completas" if not falhas else f"FALHAS: {falhas[:5]}")
    assert not falhas

    # Reprodutibilidade: mesma entrada, mesmo resultado
    a = gerar_jogos(base, concurso_alvo=9999)
    b = gerar_jogos(base, concurso_alvo=9999)
    assert [j["dezenas"] for j in a["jogos"]] == [j["dezenas"] for j in b["jogos"]]
    print("OK  mesma semente produz exatamente os mesmos 13 jogos")

    # Concursos diferentes têm que dar jogos diferentes
    c = gerar_jogos(base, concurso_alvo=10000)
    assert [j["dezenas"] for j in a["jogos"]] != [j["dezenas"] for j in c["jogos"]]
    print("OK  concursos diferentes produzem jogos diferentes")

    print("\nTODOS OS TESTES PASSARAM")


if __name__ == "__main__":
    main()
