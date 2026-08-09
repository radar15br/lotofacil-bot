"""
Teste da reconferência contra a fonte oficial (sem internet).

Monta uma base falsa com três origens diferentes e simula a resposta da API
da Caixa. Verifica que:
  - o que veio da planilha e bate com a Caixa é marcado como verificado
  - o que veio do espelho e DIVERGE é corrigido e reportado
  - o que já era "caixa" não é reconferido de novo
  - a prioridade coloca o espelho antes da planilha

Rodar com:  python tests/test_reconferencia.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import coleta  # noqa: E402

# O concurso 102 está ERRADO na nossa base de propósito (veio do espelho)
OFICIAL = {
    100: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    101: [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
    102: [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
    103: [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
}

pedidos: list[int] = []


def falso_pedir_json(url: str) -> dict:
    numero = int(url.rstrip("/").split("/")[-1])
    pedidos.append(numero)
    return {
        "numero": numero,
        "dataApuracao": "07/08/2026",
        "listaDezenas": [f"{d:02d}" for d in OFICIAL[numero]],
        "acumulado": False,
        "listaRateioPremio": [{"descricaoFaixa": "15 acertos", "numeroDeGanhadores": 1,
                               "valorPremio": 500000.0}],
    }


def base_inicial() -> list[dict]:
    return [
        {"concurso": 100, "data": "2026-08-04", "dezenas": OFICIAL[100],
         "rateios": {}, "fonte": "excel"},
        {"concurso": 101, "data": "2026-08-05", "dezenas": OFICIAL[101],
         "rateios": {}, "fonte": "caixa"},                      # já oficial
        {"concurso": 102, "data": "2026-08-06", "dezenas": [1, 2, 3, 4, 5, 6, 7,
         8, 9, 10, 11, 12, 13, 14, 25], "rateios": {}, "fonte": "espelho"},  # ERRADO
        {"concurso": 103, "data": "2026-08-07", "dezenas": OFICIAL[103],
         "rateios": {}, "fonte": "excel"},
    ]


def main() -> None:
    pasta = Path(__file__).resolve().parent / "_temp_rec"
    pasta.mkdir(exist_ok=True)
    coleta.PASTA_DADOS = pasta
    coleta.ARQUIVO_BASE = pasta / "lotofacil.json"
    coleta.PAUSA_ENTRE_PEDIDOS = 0
    coleta._pedir_json = falso_pedir_json
    coleta.salvar_base(base_inicial())

    # --- prioridade: o espelho tem que vir primeiro ---
    ordem = [r["concurso"] for r in coleta._pendentes_de_verificacao(coleta.carregar_base())]
    assert ordem[0] == 102, ordem
    assert 101 not in ordem, "concurso já oficial não deveria entrar na fila"
    print(f"OK  fila de verificação correta: {ordem} (espelho primeiro, oficial fora)")

    # --- reconferência ---
    r = coleta.reconferir(limite=10, verboso=False)
    assert r["verificados"] == 3, r
    assert len(r["divergencias"]) == 1, r
    d = r["divergencias"][0]
    assert d["concurso"] == 102 and d["fonte_anterior"] == "espelho", d
    print("OK  divergência do espelho detectada e reportada")

    # --- correção aplicada ---
    base = {c["concurso"]: c for c in coleta.carregar_base()}
    assert base[102]["dezenas"] == OFICIAL[102], base[102]["dezenas"]
    assert base[102]["fonte"] == "caixa"
    print("OK  dado divergente substituído pelo oficial")

    # --- marcação de verificado ---
    assert base[100]["fonte"] == "caixa" and base[100]["verificado"]
    assert base[103]["fonte"] == "caixa" and base[103]["verificado"]
    print("OK  registros conferidos passam a constar como oficiais")

    # --- não repete trabalho ---
    antes = len(pedidos)
    r2 = coleta.reconferir(limite=10, verboso=False)
    assert r2["verificados"] == 0 and len(pedidos) == antes
    assert r2["restantes"] == 0
    print("OK  segunda execução não refaz o que já foi verificado")

    # --- a base continua íntegra ---
    assert all(coleta.validar_concurso(c) for c in coleta.carregar_base())
    print("OK  base segue válida após a correção")

    print("\nTODOS OS TESTES PASSARAM")


if __name__ == "__main__":
    main()
