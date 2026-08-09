"""
ETAPA 1 — COLETA DE DADOS DA LOTOFÁCIL
=======================================

O que este módulo faz, em português simples:

1. Pergunta para a API da Caixa qual é o concurso mais recente.
2. Olha o arquivo local (data/lotofacil.json) para ver até onde já baixamos.
3. Baixa APENAS os concursos que faltam (coleta incremental).
4. Salva tudo de volta no arquivo local, ordenado por número de concurso.

Se a API oficial da Caixa estiver fora do ar, o módulo tenta automaticamente
uma fonte alternativa (um espelho público da mesma base).

Como rodar no terminal:
    python -m src.coleta --status      # mostra o que já temos guardado
    python -m src.coleta --atualizar   # baixa só o que falta
    python -m src.coleta --completo    # baixa tudo do zero (concurso 1 até o último)
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES GERAIS
# ---------------------------------------------------------------------------

# Pasta raiz do projeto (a pasta que contém "src" e "data")
RAIZ = Path(__file__).resolve().parent.parent
PASTA_DADOS = RAIZ / "data"
ARQUIVO_BASE = PASTA_DADOS / "lotofacil.json"

# Alguns servidores recusam requisições sem um "User-Agent" de navegador.
CABECALHOS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

TIMEOUT = 25          # segundos de paciência por requisição
TENTATIVAS = 3        # quantas vezes tentar de novo quando dá erro
PAUSA_ENTRE_PEDIDOS = 0.35   # segundos — evita "martelar" o servidor da Caixa

# O certificado SSL da Caixa às vezes falha em ambientes antigos.
# Se der erro de SSL, defina a variável de ambiente LOTOFACIL_SSL=0
VERIFICAR_SSL = os.getenv("LOTOFACIL_SSL", "1") != "0"


# ---------------------------------------------------------------------------
# FONTES DE DADOS
# ---------------------------------------------------------------------------
# Cada fonte sabe montar a URL e traduzir a resposta para o NOSSO formato padrão.
# Formato padrão de um concurso:
#   {
#     "concurso": 3200,
#     "data": "2026-08-07",
#     "dezenas": [1, 2, 3, ...],   # 15 números, ordenados
#     "acumulado": False,
#     "ganhadores_15": 2,
#     "fonte": "caixa"
#   }


def _url_caixa(concurso: int | None) -> str:
    base = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
    return base if concurso is None else f"{base}/{concurso}"


def _traduzir_caixa(bruto: dict[str, Any]) -> dict[str, Any]:
    """Converte a resposta oficial da Caixa para o nosso formato padrão."""
    dezenas = sorted(int(d) for d in bruto.get("listaDezenas", []))

    # A Caixa devolve a data como "07/08/2026". Convertemos para "2026-08-07".
    data_bruta = bruto.get("dataApuracao") or ""
    try:
        data = datetime.strptime(data_bruta, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        data = data_bruta

    # Ganhadores de 15 e valor pago em cada faixa (11 a 15 acertos)
    ganhadores_15 = 0
    rateios: dict[str, float] = {}
    for faixa in bruto.get("listaRateioPremio", []) or []:
        descricao = faixa.get("descricaoFaixa", "")
        acertos = descricao.split()[0] if descricao else ""
        if acertos.isdigit():
            rateios[acertos] = float(faixa.get("valorPremio", 0) or 0)
        if descricao.startswith("15"):
            ganhadores_15 = int(faixa.get("numeroDeGanhadores", 0))

    proxima = bruto.get("dataProximoConcurso") or ""
    try:
        proxima = datetime.strptime(proxima, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        proxima = ""

    return {
        "concurso": int(bruto["numero"]),
        "data": data,
        "data_proximo": proxima,
        "dezenas": dezenas,
        "acumulado": bool(bruto.get("acumulado", False)),
        "ganhadores_15": ganhadores_15,
        "rateios": rateios,
        "fonte": "caixa",
    }


def _url_espelho(concurso: int | None) -> str:
    base = "https://loteriascaixa-api.herokuapp.com/api/lotofacil"
    return f"{base}/latest" if concurso is None else f"{base}/{concurso}"


def _traduzir_espelho(bruto: dict[str, Any]) -> dict[str, Any]:
    """Converte a resposta do espelho público para o nosso formato padrão."""
    dezenas = sorted(int(d) for d in bruto.get("dezenas", []))
    data_bruta = bruto.get("data") or ""
    try:
        data = datetime.strptime(data_bruta, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        data = data_bruta

    ganhadores_15 = 0
    rateios: dict[str, float] = {}
    for faixa in bruto.get("premiacoes", []) or []:
        acertos = str(faixa.get("acertos", ""))
        if acertos.isdigit():
            rateios[acertos] = float(faixa.get("premio", 0) or 0)
        if acertos.startswith("15"):
            ganhadores_15 = int(faixa.get("vencedores", 0))

    return {
        "concurso": int(bruto["concurso"]),
        "data": data,
        "dezenas": dezenas,
        "acumulado": bool(bruto.get("acumulou", False)),
        "ganhadores_15": ganhadores_15,
        "rateios": rateios,
        "fonte": "espelho",
    }


FONTES = [
    {"nome": "Caixa (oficial)", "url": _url_caixa, "traduzir": _traduzir_caixa},
    {"nome": "Espelho público", "url": _url_espelho, "traduzir": _traduzir_espelho},
]


# ---------------------------------------------------------------------------
# BUSCA NA INTERNET
# ---------------------------------------------------------------------------


class ColetaError(RuntimeError):
    """Erro quando nenhuma fonte conseguiu entregar o concurso pedido."""


def _pedir_json(url: str) -> dict[str, Any]:
    """Faz o GET com retentativas e espera crescente entre elas."""
    ultimo_erro: Exception | None = None
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resposta = requests.get(
                url, headers=CABECALHOS, timeout=TIMEOUT, verify=VERIFICAR_SSL
            )
            resposta.raise_for_status()
            dados = resposta.json()
            if not dados:
                raise ValueError("resposta vazia")
            return dados
        except Exception as erro:  # noqa: BLE001 - queremos capturar tudo e tentar de novo
            ultimo_erro = erro
            if tentativa < TENTATIVAS:
                time.sleep(1.5 * tentativa)  # 1.5s, depois 3s...
    raise ColetaError(f"Falha ao acessar {url}: {ultimo_erro}")


def buscar_concurso(numero: int | None = None,
                    apenas_oficial: bool = False) -> dict[str, Any]:
    """
    Busca um concurso específico. Se `numero` for None, busca o mais recente.
    Tenta a Caixa primeiro; se falhar, cai para o espelho.

    apenas_oficial=True desliga o espelho — usado na reconferência, onde o
    objetivo é justamente comparar contra a fonte oficial.
    """
    erros = []
    for fonte in (FONTES[:1] if apenas_oficial else FONTES):
        try:
            bruto = _pedir_json(fonte["url"](numero))
            # O espelho às vezes devolve lista em vez de objeto
            if isinstance(bruto, list):
                bruto = bruto[0]
            return fonte["traduzir"](bruto)
        except Exception as erro:  # noqa: BLE001
            erros.append(f"{fonte['nome']}: {erro}")
    alvo = "último concurso" if numero is None else f"concurso {numero}"
    raise ColetaError(f"Nenhuma fonte respondeu para o {alvo}. Detalhes: {' | '.join(erros)}")


# ---------------------------------------------------------------------------
# ARQUIVO LOCAL
# ---------------------------------------------------------------------------


def carregar_base() -> list[dict[str, Any]]:
    """Lê o histórico salvo em disco. Devolve lista vazia se ainda não existe."""
    if not ARQUIVO_BASE.exists():
        return []
    with ARQUIVO_BASE.open("r", encoding="utf-8") as f:
        return json.load(f)


def salvar_base(concursos: list[dict[str, Any]]) -> None:
    """Grava o histórico em disco, ordenado e sem duplicatas."""
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)

    # Remove duplicatas mantendo a última versão de cada concurso
    unicos: dict[int, dict[str, Any]] = {c["concurso"]: c for c in concursos}
    ordenados = [unicos[k] for k in sorted(unicos)]

    # Escreve num arquivo temporário e só então substitui o original.
    # Assim, se faltar energia no meio da escrita, a base antiga não se perde.
    temporario = ARQUIVO_BASE.with_suffix(".tmp")
    with temporario.open("w", encoding="utf-8") as f:
        json.dump(ordenados, f, ensure_ascii=False, indent=1)
    temporario.replace(ARQUIVO_BASE)


def validar_concurso(registro: dict[str, Any]) -> bool:
    """Confere se o registro faz sentido: 15 dezenas únicas, entre 1 e 25."""
    dezenas = registro.get("dezenas", [])
    return (
        len(dezenas) == 15
        and len(set(dezenas)) == 15
        and all(1 <= d <= 25 for d in dezenas)
    )


# ---------------------------------------------------------------------------
# ROTINA PRINCIPAL DE ATUALIZAÇÃO
# ---------------------------------------------------------------------------


def atualizar(completo: bool = False, verboso: bool = True) -> dict[str, Any]:
    """
    Atualiza a base local.
      completo=False -> baixa só os concursos que faltam (uso do dia a dia)
      completo=True  -> baixa tudo desde o concurso 1 (primeira execução)
    """
    base = [] if completo else carregar_base()
    ja_temos = {c["concurso"] for c in base}

    ultimo = buscar_concurso(None)
    numero_ultimo = ultimo["concurso"]
    if verboso:
        print(f"Último concurso publicado: {numero_ultimo} ({ultimo['data']})")

    faltantes = [n for n in range(1, numero_ultimo + 1) if n not in ja_temos]
    if not faltantes:
        if verboso:
            print("Base já está em dia. Nada a baixar.")
        return {"baixados": 0, "total": len(base), "ultimo": numero_ultimo}

    if verboso:
        print(f"Faltam {len(faltantes)} concursos. Baixando...")

    baixados = 0
    falhas: list[int] = []
    for i, numero in enumerate(faltantes, start=1):
        try:
            registro = ultimo if numero == numero_ultimo else buscar_concurso(numero)
            if not validar_concurso(registro):
                falhas.append(numero)
                continue
            base.append(registro)
            baixados += 1
        except ColetaError:
            falhas.append(numero)

        # Salva parcialmente a cada 50 concursos: se cair no meio, não perde tudo
        if baixados and baixados % 50 == 0:
            salvar_base(base)
            if verboso:
                print(f"  ... {i}/{len(faltantes)} processados")

        time.sleep(PAUSA_ENTRE_PEDIDOS)

    salvar_base(base)

    if verboso:
        print(f"Pronto. {baixados} concursos novos gravados em {ARQUIVO_BASE}")
        if falhas:
            print(f"ATENÇÃO: {len(falhas)} concursos falharam: {falhas[:10]}...")

    return {
        "baixados": baixados,
        "total": len(base),
        "ultimo": numero_ultimo,
        "falhas": falhas,
    }


# ---------------------------------------------------------------------------
# RECONFERÊNCIA — garantir que tudo bata com a fonte oficial
# ---------------------------------------------------------------------------

# Quantos concursos são reconferidos por execução. Um número baixo mantém a
# rotina rápida; com 25 por dia, uma base de 3.700 fica toda verificada em
# poucos meses, começando sempre pelos mais recentes.
RECONFERIR_POR_EXECUCAO = 25


def _pendentes_de_verificacao(base: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Quem precisa ser reconferido, em ordem de prioridade:
      1. o que veio do espelho (terceiro, não é a Caixa)
      2. o que veio da planilha, do mais recente para o mais antigo
    O que já veio direto da Caixa não precisa: já é a fonte oficial.
    """
    pendentes = [
        r for r in base
        if r.get("fonte") != "caixa" and not r.get("verificado")
    ]
    prioridade = {"espelho": 0, "excel": 1}
    pendentes.sort(key=lambda r: (prioridade.get(r.get("fonte"), 2), -r["concurso"]))
    return pendentes


def reconferir(limite: int = RECONFERIR_POR_EXECUCAO, verboso: bool = True) -> dict[str, Any]:
    """
    Confere contra a API OFICIAL da Caixa os concursos que entraram por outra
    via (planilha ou espelho). Divergência encontrada é corrigida na hora e
    reportada — nunca corrigida em silêncio.
    """
    base = carregar_base()
    por_numero = {r["concurso"]: r for r in base}
    pendentes = _pendentes_de_verificacao(base)[:limite]

    if not pendentes:
        if verboso:
            print("Toda a base já foi verificada contra a fonte oficial.")
        return {"verificados": 0, "divergencias": [], "restantes": 0, "falhas": 0}

    if verboso:
        print(f"Reconferindo {len(pendentes)} concursos contra a API da Caixa...")

    divergencias: list[dict[str, Any]] = []
    verificados = falhas = seguidas = 0

    for registro in pendentes:
        # Se a Caixa está fora do ar, não adianta insistir: cada tentativa
        # gasta segundos e a rotina do dia não pode ficar presa aqui.
        if seguidas >= 3:
            if verboso:
                print("  API da Caixa não está respondendo — reconferência adiada.")
            break

        numero = registro["concurso"]
        try:
            oficial = buscar_concurso(numero, apenas_oficial=True)
            seguidas = 0
        except ColetaError:
            falhas += 1
            seguidas += 1
            continue

        if not validar_concurso(oficial):
            falhas += 1
            continue

        if oficial["dezenas"] != registro["dezenas"]:
            divergencias.append({
                "concurso": numero,
                "tinhamos": registro["dezenas"],
                "oficial": oficial["dezenas"],
                "fonte_anterior": registro.get("fonte"),
            })
            oficial["verificado"] = True
            por_numero[numero] = oficial       # a Caixa manda
        else:
            registro["verificado"] = True
            registro["fonte"] = "caixa"        # confirmado na origem oficial

        verificados += 1
        time.sleep(PAUSA_ENTRE_PEDIDOS)

    salvar_base(list(por_numero.values()))
    restantes = len(_pendentes_de_verificacao(carregar_base()))

    if verboso:
        print(f"  {verificados} conferidos · {len(divergencias)} divergência(s) · "
              f"{falhas} sem resposta · {restantes} ainda por verificar")
        for d in divergencias:
            print(f"  CORRIGIDO concurso {d['concurso']} (vinha de '{d['fonte_anterior']}')")
            print(f"    tínhamos: {d['tinhamos']}")
            print(f"    oficial : {d['oficial']}")

    return {
        "verificados": verificados,
        "divergencias": divergencias,
        "restantes": restantes,
        "falhas": falhas,
    }


def status() -> None:
    """Mostra um resumo do que já está guardado localmente."""
    base = carregar_base()
    if not base:
        print("Base local vazia. Rode: python -m src.coleta --completo")
        return
    numeros = [c["concurso"] for c in base]
    buracos = sorted(set(range(min(numeros), max(numeros) + 1)) - set(numeros))
    print(f"Arquivo: {ARQUIVO_BASE}")
    print(f"Concursos guardados: {len(base)}")
    print(f"Intervalo: {min(numeros)} a {max(numeros)}")
    print(f"Último sorteio: {base[-1]['data']} -> {base[-1]['dezenas']}")
    print(f"Concursos faltando no meio: {len(buracos)}" + (f" {buracos[:10]}" if buracos else ""))

    from collections import Counter
    fontes = Counter(c.get("fonte", "?") for c in base)
    oficiais = sum(1 for c in base if c.get("fonte") == "caixa")
    print(f"Origem dos dados: " + " · ".join(f"{k}: {v}" for k, v in fontes.items()))
    print(f"Verificados na fonte oficial: {oficiais} de {len(base)} "
          f"({100 * oficiais / len(base):.1f}%)")


# ---------------------------------------------------------------------------
# LINHA DE COMANDO
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Coleta de resultados da Lotofácil")
    parser.add_argument("--completo", action="store_true", help="baixa todo o histórico do zero")
    parser.add_argument("--atualizar", action="store_true", help="baixa só o que falta")
    parser.add_argument("--status", action="store_true", help="mostra o que já está salvo")
    parser.add_argument("--reconferir", type=int, nargs="?", const=RECONFERIR_POR_EXECUCAO,
                        help="reconfere N concursos contra a API oficial da Caixa")
    args = parser.parse_args()

    if args.reconferir:
        reconferir(args.reconferir)
    elif args.status:
        status()
    elif args.completo:
        atualizar(completo=True)
    else:
        atualizar(completo=False)
