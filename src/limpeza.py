"""
LIMPEZA DE POSTS DUPLICADOS
===========================

Até 24/10/2026 o registro de publicações não era salvo, e as execuções de
reserva publicavam o mesmo post várias vezes. Este módulo encontra os
repetidos (mesma legenda) e mantém só o MAIS ANTIGO de cada grupo.

    python -m src.limpeza            # só lista, não apaga nada
    python -m src.limpeza --apagar   # apaga os repetidos
"""

from __future__ import annotations

import argparse
from collections import defaultdict

import requests

from src.publicar import IG_HOST, IG_TOKEN, IG_USER_ID, IG_VERSAO_API, TIMEOUT

API = f"https://{IG_HOST}/{IG_VERSAO_API}"


def listar_midias(limite: int = 500) -> list[dict]:
    url = f"{API}/{IG_USER_ID}/media"
    params = {"fields": "id,caption,timestamp,media_type,permalink", "limit": 100,
              "access_token": IG_TOKEN}
    midias: list[dict] = []
    while url and len(midias) < limite:
        dados = requests.get(url, params=params, timeout=TIMEOUT).json()
        if "error" in dados:
            raise RuntimeError(dados["error"].get("message"))
        midias += dados.get("data", [])
        url, params = dados.get("paging", {}).get("next"), None
    return midias


def duplicados(midias: list[dict]) -> list[tuple[dict, list[dict]]]:
    grupos: dict[str, list[dict]] = defaultdict(list)
    for m in midias:
        chave = " ".join((m.get("caption") or "").split())
        if chave:
            grupos[chave].append(m)
    saida = []
    for itens in grupos.values():
        if len(itens) > 1:
            itens.sort(key=lambda m: m["timestamp"])
            saida.append((itens[0], itens[1:]))
    return sorted(saida, key=lambda g: g[0]["timestamp"])


def apagar(media_id: str) -> tuple[bool, str]:
    r = requests.delete(f"{API}/{media_id}", params={"access_token": IG_TOKEN}, timeout=TIMEOUT)
    try:
        dados = r.json()
    except ValueError:
        dados = {"texto": r.text}
    ok = r.status_code < 400 and "error" not in dados
    return ok, "" if ok else str(dados.get("error", dados).get("message", dados)
                                 if isinstance(dados.get("error"), dict) else dados)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apagar", action="store_true")
    args = parser.parse_args()

    midias = listar_midias()
    grupos = duplicados(midias)
    extras = sum(len(r) for _, r in grupos)
    print(f"{len(midias)} posts no perfil · {len(grupos)} grupos repetidos · {extras} cópias a remover")
    for manter, repetidos in grupos:
        titulo = (manter.get("caption") or "").split("\n")[0][:60]
        print(f"\nMANTER {manter['timestamp'][:16]}  {titulo}")
        for m in repetidos:
            print(f"  cópia {m['timestamp'][:16]}  {m['permalink']}")

    if args.apagar:
        print("\nApagando...")
        ok = falhas = 0
        for _, repetidos in grupos:
            for m in repetidos:
                sucesso, erro = apagar(m["id"])
                if sucesso:
                    ok += 1
                else:
                    falhas += 1
                    print(f"  NÃO apagou {m['id']}: {erro}")
                    if falhas >= 2 and ok == 0:
                        raise SystemExit("::error::A API do Instagram não permite apagar posts com este token.")
        print(f"\nApagados: {ok} · falhas: {falhas}")
