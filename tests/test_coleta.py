"""
Teste do módulo de coleta SEM depender da internet.

A ideia: substituímos a função que acessa a rede por uma função falsa
que devolve uma resposta igual à da Caixa. Assim conseguimos provar que
a tradução, a validação e a gravação em disco funcionam.

Rodar com:  python tests/test_coleta.py
"""

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import coleta  # noqa: E402

TOTAL_FALSO = 120  # simulamos 120 concursos


def resposta_falsa_da_caixa(numero: int) -> dict:
    """Monta um JSON no MESMO formato que a Caixa devolve."""
    random.seed(numero)  # sorteio reprodutível, para o teste dar sempre igual
    dezenas = sorted(random.sample(range(1, 26), 15))
    return {
        "numero": numero,
        "dataApuracao": "07/08/2026",
        "listaDezenas": [f"{d:02d}" for d in dezenas],
        "acumulado": False,
        "listaRateioPremio": [
            {"descricaoFaixa": "15 acertos", "numeroDeGanhadores": 3},
            {"descricaoFaixa": "14 acertos", "numeroDeGanhadores": 400},
        ],
    }


def falso_pedir_json(url: str) -> dict:
    """Substitui a chamada de rede. Descobre o concurso pedido pela URL."""
    ultimo_pedaco = url.rstrip("/").split("/")[-1]
    numero = TOTAL_FALSO if not ultimo_pedaco.isdigit() else int(ultimo_pedaco)
    return resposta_falsa_da_caixa(numero)


def main() -> None:
    global TOTAL_FALSO

    # 1) Redireciona a coleta para uma pasta de teste e para a rede falsa
    pasta_teste = Path(__file__).resolve().parent / "_temp"
    pasta_teste.mkdir(exist_ok=True)
    coleta.PASTA_DADOS = pasta_teste
    coleta.ARQUIVO_BASE = pasta_teste / "lotofacil.json"
    coleta.PAUSA_ENTRE_PEDIDOS = 0
    coleta._pedir_json = falso_pedir_json
    if coleta.ARQUIVO_BASE.exists():
        coleta.ARQUIVO_BASE.unlink()

    # 2) Primeira carga: deve baixar os 120 concursos
    r1 = coleta.atualizar(completo=True, verboso=False)
    assert r1["baixados"] == TOTAL_FALSO, r1
    assert r1["total"] == TOTAL_FALSO, r1
    print(f"OK  carga completa: {r1['baixados']} concursos baixados")

    # 3) Segunda execução: não pode baixar nada de novo (coleta incremental)
    r2 = coleta.atualizar(completo=False, verboso=False)
    assert r2["baixados"] == 0, r2
    print("OK  execução incremental não rebaixou nada")

    # 4) Simula um concurso novo saindo: deve baixar exatamente 1
    TOTAL_FALSO += 1
    r3 = coleta.atualizar(completo=False, verboso=False)
    assert r3["baixados"] == 1, r3
    assert r3["total"] == TOTAL_FALSO, r3
    print("OK  concurso novo detectado e baixado sozinho")

    # 5) Conteúdo gravado está correto?
    base = json.loads(coleta.ARQUIVO_BASE.read_text(encoding="utf-8"))
    numeros = [c["concurso"] for c in base]
    assert numeros == sorted(numeros), "base fora de ordem"
    assert len(numeros) == len(set(numeros)), "há concursos duplicados"
    assert all(coleta.validar_concurso(c) for c in base), "registro inválido"
    assert base[0]["data"] == "2026-08-07", base[0]["data"]
    assert base[0]["ganhadores_15"] == 3
    print(f"OK  base gravada: ordenada, sem duplicatas, {len(base)} registros válidos")

    # 6) Validação rejeita jogo errado?
    assert not coleta.validar_concurso({"dezenas": [1, 2, 3]})
    assert not coleta.validar_concurso({"dezenas": [1] * 15})
    assert not coleta.validar_concurso({"dezenas": list(range(11, 26)) + [30]})
    print("OK  validação rejeita registros defeituosos")

    print("\nTODOS OS TESTES PASSARAM")


if __name__ == "__main__":
    main()
