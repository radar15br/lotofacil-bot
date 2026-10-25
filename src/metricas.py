"""
MÉTRICAS DO INSTAGRAM — o que de fato traz alcance e seguidor
==============================================================

Uma vez por dia o robô:
  1. lê o número de seguidores da conta (guarda o histórico diário)
  2. lê as métricas de cada post recente: alcance, visualizações,
     curtidas, comentários, salvamentos, compartilhamentos
  3. cruza cada post com o registro de publicações (formato, Reel x imagem,
     estilo da legenda do rodízio A/B)
  4. salva tudo em data/metricas.json e gera o painel docs/metricas.html

Requer as permissões instagram_business_basic e
instagram_business_manage_insights no token. Sem a de insights, o robô ainda
registra seguidores, curtidas e comentários, e avisa o que faltou.

Como rodar:
    python -m src.metricas
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

from src.coleta import PASTA_DADOS
from src.publicar import (ARQUIVO_PUBLICACOES, IG_HOST, IG_TOKEN, IG_USER_ID,
                          IG_VERSAO_API, PASTA_SITE, TIMEOUT)

ARQUIVO = PASTA_DADOS / "metricas.json"
FUSO = ZoneInfo("America/Sao_Paulo")
POSTS_LIDOS = 60

# A API muda os nomes de tempos em tempos; tenta do conjunto mais completo
# para o mais simples até um ser aceito.
CONJUNTOS = [
    "reach,views,saved,shares,total_interactions",
    "reach,saved,shares,total_interactions",
    "reach,saved",
]


class MetricasError(RuntimeError):
    pass


def _get(caminho: str, **params: Any) -> dict:
    resposta = requests.get(f"https://{IG_HOST}/{IG_VERSAO_API}/{caminho}",
                            params={**params, "access_token": IG_TOKEN}, timeout=TIMEOUT)
    dados = resposta.json()
    if "error" in dados:
        raise MetricasError(dados["error"].get("message", str(dados)))
    return dados


def _insights(media_id: str) -> tuple[dict[str, int], str | None]:
    ultimo_erro = None
    for metricas in CONJUNTOS:
        try:
            dados = _get(f"{media_id}/insights", metric=metricas)
            return ({m["name"]: int((m.get("values") or [{}])[0].get("value", 0) or 0)
                     for m in dados.get("data", [])}, None)
        except MetricasError as erro:
            ultimo_erro = str(erro)
    return {}, ultimo_erro


def coletar() -> dict[str, Any]:
    if not IG_USER_ID or not IG_TOKEN:
        raise MetricasError("Faltam IG_USER_ID e IG_TOKEN.")

    conta = _get(IG_USER_ID, fields="username,followers_count,media_count")
    midias = _get(f"{IG_USER_ID}/media", limit=POSTS_LIDOS,
                  fields="id,caption,media_type,media_product_type,timestamp,"
                         "permalink,like_count,comments_count").get("data", [])

    registro = {}
    if ARQUIVO_PUBLICACOES.exists():
        for r in json.loads(ARQUIVO_PUBLICACOES.read_text(encoding="utf-8")):
            if r.get("id") and not r.get("simulado"):
                registro[str(r["id"])] = r

    posts, avisos = [], set()
    for m in midias:
        valores, erro = _insights(m["id"])
        if erro:
            avisos.add(erro)
        origem = registro.get(m["id"], {})
        legenda = (m.get("caption") or "").strip()
        posts.append({
            "id": m["id"],
            "data": m["timestamp"],
            "link": m.get("permalink"),
            "tipo": "Reel" if m.get("media_product_type") == "REELS" else
                    ("Carrossel" if m.get("media_type") == "CAROUSEL_ALBUM" else "Imagem"),
            "conteudo": "Resultado" if legenda.upper().startswith(("RESULTADO", "✅")) else "Jogo do dia",
            "titulo": legenda.split("\n")[0][:90],
            "concurso": origem.get("concurso"),
            "estilo_legenda": origem.get("estilo_legenda"),
            "curtidas": m.get("like_count", 0),
            "comentarios": m.get("comments_count", 0),
            **valores,
        })

    historico = json.loads(ARQUIVO.read_text(encoding="utf-8")) if ARQUIVO.exists() else {}
    seguidores = historico.get("seguidores", [])
    hoje = datetime.now(FUSO).strftime("%Y-%m-%d")
    seguidores = [s for s in seguidores if s["data"] != hoje]
    seguidores.append({"data": hoje, "seguidores": conta.get("followers_count", 0)})

    resultado = {
        "atualizado": datetime.now(FUSO).strftime("%d/%m/%Y %H:%M"),
        "conta": conta.get("username"),
        "posts_total": conta.get("media_count"),
        "seguidores": seguidores[-400:],
        "posts": posts,
        "avisos": sorted(avisos),
    }
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    ARQUIVO.write_text(json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")
    return resultado


def gerar_painel(dados: dict[str, Any] | None = None) -> str:
    from src.painel_metricas import TEMPLATE

    dados = dados or json.loads(ARQUIVO.read_text(encoding="utf-8"))
    destino = PASTA_SITE / "metricas.html"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(TEMPLATE.replace("__DADOS__", json.dumps(dados, ensure_ascii=False)),
                       encoding="utf-8")
    return str(destino)


if __name__ == "__main__":
    d = coletar()
    print(f"@{d['conta']} · {d['seguidores'][-1]['seguidores']} seguidores · {len(d['posts'])} posts lidos")
    for aviso in d["avisos"]:
        print(f"::warning::Métricas incompletas: {aviso}")
    print(gerar_painel(d))
