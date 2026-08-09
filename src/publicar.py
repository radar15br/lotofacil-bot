"""
ETAPA 7 — PUBLICAÇÃO AUTOMÁTICA (INSTAGRAM + TIKTOK)
=====================================================

O PONTO QUE MUDA TUDO

As duas APIs NÃO aceitam upload de arquivo direto para foto. Elas exigem que a
imagem já esteja numa URL pública, e vão buscá-la. Ou seja, antes de publicar o
robô precisa hospedar as imagens em algum lugar acessível pela internet.

Solução usada aqui: GitHub Pages. O mesmo repositório que roda o robô publica a
pasta `docs/` como site estático, de graça. As imagens ficam em URLs do tipo:

    https://SEU-USUARIO.github.io/lotofacil-bot/3757/dia/feed.jpg

Isso resolve os dois lados de uma vez:
  - Instagram exige JPEG em URL pública  -> ok
  - TikTok exige domínio VERIFICADO      -> github.io permite verificar

REGRAS DAS PLATAFORMAS QUE O CÓDIGO RESPEITA

  Instagram: carrossel de no máximo 10 itens; 100 publicações por API a cada
             24h; container criado e só depois publicado (2 chamadas).
  TikTok:    apps ainda não auditados só conseguem postar como PRIVADO
             (SELF_ONLY). Máximo 6 requisições por minuto por token.

MODO SIMULAÇÃO

Sem credenciais, tudo roda em modo simulação: o robô monta as chamadas exatas
que faria e mostra na tela, sem enviar nada. Serve para testar o fluxo inteiro
antes de ter os tokens aprovados.

Como rodar:
    python -m src.publicar --simular              # não envia nada, só mostra
    python -m src.publicar --rede instagram
    python -m src.publicar --rede tiktok
    python -m src.publicar --formato carrossel    # ou feed / stories
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

from src.coleta import PASTA_DADOS, RAIZ

PASTA_SAIDAS = RAIZ / "saidas"
PASTA_SITE = RAIZ / "docs"          # o que o GitHub Pages publica
ARQUIVO_PUBLICACOES = PASTA_DADOS / "publicacoes.json"

# ---------------------------------------------------------------------------
# CREDENCIAIS (todas vêm de variáveis de ambiente / segredos do GitHub)
# ---------------------------------------------------------------------------

IG_USER_ID = os.getenv("IG_USER_ID", "")
IG_TOKEN = os.getenv("IG_TOKEN", "")
IG_VERSAO_API = os.getenv("IG_VERSAO_API", "v23.0")

# A Meta oferece DOIS caminhos para publicar no Instagram:
#
#   "instagram_login"  (padrão, mais simples)
#       API do Instagram com Login do Instagram. NÃO exige página do Facebook.
#       Host: graph.instagram.com
#
#   "pagina_facebook"  (o caminho antigo)
#       Graph API através de uma página do Facebook vinculada.
#       Host: graph.facebook.com. Necessário se você também for usar anúncios
#       ou marcação de produtos, que o caminho novo não cobre.
IG_MODO = os.getenv("IG_MODO", "instagram_login")
IG_HOST = ("graph.instagram.com" if IG_MODO == "instagram_login"
           else "graph.facebook.com")

TIKTOK_TOKEN = os.getenv("TIKTOK_TOKEN", "")
# Enquanto o app não passar pela auditoria do TikTok, o post SÓ pode ser privado
TIKTOK_PRIVACIDADE = os.getenv("TIKTOK_PRIVACIDADE", "SELF_ONLY")

# Base pública onde as imagens ficam hospedadas (GitHub Pages)
URL_BASE = os.getenv("URL_BASE_PUBLICA", "").rstrip("/")

TIMEOUT = 60
MAX_ITENS_CARROSSEL = 10


class PublicacaoError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# PREPARAÇÃO DOS ARQUIVOS PARA A WEB
# ---------------------------------------------------------------------------


def publicar_no_site(concurso: int, verboso: bool = True) -> list[str]:
    """
    Copia as imagens .jpg do concurso para a pasta docs/, que o GitHub Pages
    serve. Devolve a lista de URLs públicas correspondentes.
    """
    import shutil

    origem = PASTA_SAIDAS / str(concurso)
    if not origem.exists():
        raise PublicacaoError(f"Não encontrei as peças do concurso {concurso}. Rode src.pecas antes.")

    destino = PASTA_SITE / str(concurso)
    urls: list[str] = []

    for arquivo in sorted(origem.rglob("*.jpg")):
        relativo = arquivo.relative_to(origem)
        alvo = destino / relativo
        alvo.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(arquivo, alvo)
        if URL_BASE:
            urls.append(f"{URL_BASE}/{concurso}/{relativo.as_posix()}")

    # Página simples para o GitHub Pages não ficar vazio
    indice = PASTA_SITE / "index.html"
    if not indice.exists():
        PASTA_SITE.mkdir(parents=True, exist_ok=True)
        indice.write_text(
            "<!DOCTYPE html><meta charset='utf-8'><title>Lotofácil Bot</title>"
            "<p>Imagens geradas automaticamente. Análise estatística de dados "
            "históricos, não é previsão. +18.</p>",
            encoding="utf-8",
        )

    _limpar_antigos(verboso)

    if verboso:
        print(f"{len(urls) or '?'} imagens copiadas para {destino}")
        if not URL_BASE:
            print("AVISO: variável URL_BASE_PUBLICA não definida — sem URLs públicas.")
    return urls


# Quantos concursos ficam guardados no site público. Cada concurso ocupa ~5 MB;
# 30 concursos são cerca de 5 semanas de conteúdo e ~150 MB de repositório.
CONCURSOS_NO_SITE = int(os.getenv("CONCURSOS_NO_SITE", "30"))


def _limpar_antigos(verboso: bool = True) -> int:
    """
    Apaga do site os concursos mais antigos. Sem isso o repositório cresce
    ~5 MB por dia e fica pesado em poucos meses.
    """
    import shutil

    if not PASTA_SITE.exists():
        return 0
    pastas = sorted(
        (p for p in PASTA_SITE.iterdir() if p.is_dir() and p.name.isdigit()),
        key=lambda p: int(p.name),
    )
    excedente = pastas[:-CONCURSOS_NO_SITE] if len(pastas) > CONCURSOS_NO_SITE else []
    for pasta in excedente:
        shutil.rmtree(pasta)
    if excedente and verboso:
        print(f"{len(excedente)} concurso(s) antigo(s) removido(s) do site "
              f"(mantendo os últimos {CONCURSOS_NO_SITE})")
    return len(excedente)


def urls_do_concurso(concurso: int, estilo: str) -> dict[str, Any]:
    """Monta as URLs públicas a partir do índice gerado pela Etapa 5."""
    indice = PASTA_SAIDAS / str(concurso) / "pecas.json"
    if not indice.exists():
        raise PublicacaoError(f"Índice não encontrado: {indice}")
    dados = json.loads(indice.read_text(encoding="utf-8"))
    arquivos = dados["estilos"][estilo]

    def url(caminho: str) -> str:
        relativo = Path(caminho).relative_to(PASTA_SAIDAS / str(concurso))
        return f"{URL_BASE}/{concurso}/{relativo.as_posix()}"

    return {
        "feed": url(arquivos["feed"]),
        "stories": url(arquivos["stories"]),
        # "vip_13_jogos" fica de fora de propósito: é material do grupo pago
        "carrossel": [url(c) for c in arquivos["carrossel"]][:MAX_ITENS_CARROSSEL],
    }


def legenda_do_concurso(concurso: int) -> tuple[str, str]:
    """Devolve (texto, estilo) da legenda escolhida pelo rodízio A/B."""
    arquivo = PASTA_SAIDAS / str(concurso) / "legendas.json"
    if not arquivo.exists():
        raise PublicacaoError(f"Legendas não encontradas: {arquivo}")
    dados = json.loads(arquivo.read_text(encoding="utf-8"))
    estilo = dados["estilo_escolhido"]
    return dados["variacoes"][estilo]["texto"], estilo


# ---------------------------------------------------------------------------
# INSTAGRAM
# ---------------------------------------------------------------------------


def _ig_post(caminho: str, dados: dict, simular: bool) -> dict:
    url = f"https://{IG_HOST}/{IG_VERSAO_API}/{caminho}"
    if simular:
        print(f"  [SIMULADO] POST {url}")
        for chave, valor in dados.items():
            if chave != "access_token":
                print(f"             {chave} = {str(valor)[:110]}")
        return {"id": f"simulado_{int(time.time() * 1000) % 100000}"}

    resposta = requests.post(url, data={**dados, "access_token": IG_TOKEN}, timeout=TIMEOUT)
    corpo = resposta.json()
    if resposta.status_code >= 400 or "error" in corpo:
        raise PublicacaoError(f"Instagram recusou: {corpo}")
    return corpo


def publicar_instagram(concurso: int, estilo: str = "dia", formato: str = "carrossel",
                       simular: bool = False) -> dict[str, Any]:
    """
    Fluxo oficial do Instagram, em duas etapas:
      1. cria um "container" para cada imagem
      2. publica o container (ou o container-pai, no caso de carrossel)
    """
    if not simular and (not IG_USER_ID or not IG_TOKEN):
        raise PublicacaoError("Faltam IG_USER_ID e IG_TOKEN. Use --simular para testar sem eles.")
    if not URL_BASE:
        raise PublicacaoError("Defina URL_BASE_PUBLICA — o Instagram busca a imagem por URL.")

    urls = urls_do_concurso(concurso, estilo)
    legenda, estilo_legenda = legenda_do_concurso(concurso)

    print(f"Instagram · concurso {concurso} · visual {estilo} · copy {estilo_legenda}")
    print(f"  modo: {IG_MODO} ({IG_HOST})")

    if formato == "carrossel":
        imagens = urls["carrossel"]
        print(f"  carrossel com {len(imagens)} slides (limite da plataforma: {MAX_ITENS_CARROSSEL})")

        filhos = []
        for i, imagem in enumerate(imagens, start=1):
            r = _ig_post(f"{IG_USER_ID}/media",
                         {"image_url": imagem, "is_carousel_item": "true"}, simular)
            filhos.append(r["id"])
            print(f"  slide {i}/{len(imagens)} -> container {r['id']}")
            time.sleep(0.4)

        pai = _ig_post(f"{IG_USER_ID}/media", {
            "media_type": "CAROUSEL",
            "children": ",".join(filhos),
            "caption": legenda,
        }, simular)
        container = pai["id"]
    else:
        imagem = urls["feed"] if formato == "feed" else urls["stories"]
        dados = {"image_url": imagem, "caption": legenda}
        if formato == "stories":
            dados = {"image_url": imagem, "media_type": "STORIES"}
        container = _ig_post(f"{IG_USER_ID}/media", dados, simular)["id"]

    # O Instagram precisa de alguns segundos para processar o container
    if not simular:
        time.sleep(8)

    publicado = _ig_post(f"{IG_USER_ID}/media_publish", {"creation_id": container}, simular)
    print(f"  PUBLICADO -> id {publicado['id']}")

    return {"rede": "instagram", "formato": formato, "estilo": estilo,
            "estilo_legenda": estilo_legenda, "id": publicado["id"], "simulado": simular}


def publicar_resultado(concurso: int, estilo: str = "radar", simular: bool = False) -> dict[str, Any]:
    """Publica no Instagram a peça única de RESULTADO (imagem simples)."""
    if not simular and (not IG_USER_ID or not IG_TOKEN):
        raise PublicacaoError("Faltam IG_USER_ID e IG_TOKEN.")
    if not URL_BASE:
        raise PublicacaoError("Defina URL_BASE_PUBLICA.")

    indice = PASTA_SAIDAS / str(concurso) / "resultado.json"
    if not indice.exists():
        raise PublicacaoError(f"Peça de resultado do concurso {concurso} não foi gerada.")
    dados = json.loads(indice.read_text(encoding="utf-8"))

    caminho = Path(dados["estilos"][estilo])
    relativo = caminho.relative_to(PASTA_SAIDAS / str(concurso))
    imagem = f"{URL_BASE}/{concurso}/{relativo.as_posix()}"

    legenda_arquivo = PASTA_SAIDAS / str(concurso) / "legenda-resultado.txt"
    if not legenda_arquivo.exists():
        raise PublicacaoError("Legenda do resultado não foi gerada.")
    legenda = legenda_arquivo.read_text(encoding="utf-8")

    print(f"Instagram · RESULTADO do concurso {concurso} · {dados['acertos']} acertos")
    container = _ig_post(f"{IG_USER_ID}/media",
                         {"image_url": imagem, "caption": legenda}, simular)["id"]
    if not simular:
        time.sleep(8)
    publicado = _ig_post(f"{IG_USER_ID}/media_publish", {"creation_id": container}, simular)
    print(f"  PUBLICADO -> id {publicado['id']}")

    return {"rede": "instagram", "formato": "resultado", "estilo": estilo,
            "acertos": dados["acertos"], "id": publicado["id"], "simulado": simular}


# ---------------------------------------------------------------------------
# TIKTOK
# ---------------------------------------------------------------------------


def publicar_tiktok(concurso: int, estilo: str = "noite", simular: bool = False) -> dict[str, Any]:
    """
    Post de FOTO no TikTok (endpoint /v2/post/publish/content/init/).
    Enquanto o app não passar pela auditoria, o TikTok força visualização
    privada — o post entra na conta, mas só você vê.
    """
    if not simular and not TIKTOK_TOKEN:
        raise PublicacaoError("Falta TIKTOK_TOKEN. Use --simular para testar sem ele.")
    if not URL_BASE:
        raise PublicacaoError("Defina URL_BASE_PUBLICA — o TikTok busca a imagem por URL.")

    urls = urls_do_concurso(concurso, estilo)
    legenda, estilo_legenda = legenda_do_concurso(concurso)

    corpo = {
        "post_info": {
            "title": f"13 jogos da Lotofácil — concurso {concurso}",
            "description": legenda[:4000],
            "privacy_level": TIKTOK_PRIVACIDADE,
            "disable_comment": False,
            "auto_add_music": True,
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "photo_cover_index": 0,
            "photo_images": urls["carrossel"],
        },
        "post_mode": "DIRECT_POST",
        "media_type": "PHOTO",
    }

    print(f"TikTok · concurso {concurso} · visual {estilo} · copy {estilo_legenda}")
    print(f"  {len(urls['carrossel'])} fotos · privacidade {TIKTOK_PRIVACIDADE}")

    if simular:
        print("  [SIMULADO] POST https://open.tiktokapis.com/v2/post/publish/content/init/")
        print("  " + json.dumps(corpo, ensure_ascii=False)[:400] + " ...")
        return {"rede": "tiktok", "publish_id": "simulado", "estilo": estilo,
                "estilo_legenda": estilo_legenda, "simulado": True}

    resposta = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/content/init/",
        headers={"Authorization": f"Bearer {TIKTOK_TOKEN}",
                 "Content-Type": "application/json; charset=UTF-8"},
        json=corpo, timeout=TIMEOUT,
    )
    dados = resposta.json()
    if dados.get("error", {}).get("code") not in ("ok", None):
        raise PublicacaoError(f"TikTok recusou: {dados}")

    publish_id = dados.get("data", {}).get("publish_id", "")
    print(f"  PUBLICADO -> publish_id {publish_id}")
    return {"rede": "tiktok", "publish_id": publish_id, "estilo": estilo,
            "estilo_legenda": estilo_legenda, "simulado": False}


# ---------------------------------------------------------------------------
# RENOVAÇÃO DO TOKEN DO INSTAGRAM
# ---------------------------------------------------------------------------


def renovar_token_instagram(token: str | None = None) -> dict[str, Any]:
    """
    O token do caminho "Login do Instagram" dura 60 dias e pode ser renovado
    por mais 60 a qualquer momento depois das primeiras 24 horas. Rode isto
    uma vez por mês e atualize o segredo IG_TOKEN no GitHub.
    """
    token = token or IG_TOKEN
    if not token:
        raise PublicacaoError("Sem IG_TOKEN para renovar.")

    resposta = requests.get(
        f"https://graph.instagram.com/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": token},
        timeout=TIMEOUT,
    )
    dados = resposta.json()
    if "access_token" not in dados:
        raise PublicacaoError(f"Não consegui renovar: {dados}")

    dias = int(dados.get("expires_in", 0)) // 86400
    return {"token": dados["access_token"], "dias_de_validade": dias}


# ---------------------------------------------------------------------------
# REGISTRO
# ---------------------------------------------------------------------------


def registrar(concurso: int, resultado: dict[str, Any]) -> None:
    registros = []
    if ARQUIVO_PUBLICACOES.exists():
        registros = json.loads(ARQUIVO_PUBLICACOES.read_text(encoding="utf-8"))
    registros.append({
        "concurso": concurso,
        "quando": datetime.now().strftime("%Y-%m-%d %H:%M"),
        **resultado,
    })
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    ARQUIVO_PUBLICACOES.write_text(
        json.dumps(registros, ensure_ascii=False, indent=1), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# LINHA DE COMANDO
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from src.coleta import carregar_base

    parser = argparse.ArgumentParser(description="Publica o post no Instagram e/ou TikTok")
    parser.add_argument("--concurso", type=int, default=None)
    parser.add_argument("--rede", choices=["instagram", "tiktok", "ambas"], default="ambas")
    parser.add_argument("--formato", choices=["carrossel", "feed", "stories"], default="carrossel")
    parser.add_argument("--estilo", default="dia")
    parser.add_argument("--simular", action="store_true", help="não envia nada, só mostra")
    parser.add_argument("--renovar-token", action="store_true",
                        help="renova o token do Instagram por mais 60 dias")
    args = parser.parse_args()

    if args.renovar_token:
        r = renovar_token_instagram()
        print(f"Token renovado. Validade: {r['dias_de_validade']} dias.")
        print("Atualize o segredo IG_TOKEN no GitHub com o valor abaixo:\n")
        print(r["token"])
        raise SystemExit(0)

    base = carregar_base()
    concurso = args.concurso or (base[-1]["concurso"] + 1 if base else 0)

    publicar_no_site(concurso)
    print()

    if args.rede in ("instagram", "ambas"):
        try:
            r = publicar_instagram(concurso, args.estilo, args.formato, args.simular)
            registrar(concurso, r)
        except PublicacaoError as erro:
            print(f"  ERRO no Instagram: {erro}")
        print()

    if args.rede in ("tiktok", "ambas"):
        try:
            r = publicar_tiktok(concurso, "noite", args.simular)
            registrar(concurso, r)
        except PublicacaoError as erro:
            print(f"  ERRO no TikTok: {erro}")
