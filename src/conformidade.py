"""
ETAPA 8A — CHECKLIST DE CONFORMIDADE (TRAVA ANTES DE PUBLICAR)
===============================================================

POR QUE ISTO EXISTE

Conteúdo de loteria vive numa zona sensível. Uma frase mal colocada pode
custar o perfil — e no Brasil, desde 17/07/2026, existem regras federais duras
para publicidade de apostas de quota fixa (as "bets"), incluindo proibição
explícita de divulgar histórico de premiações e de usar autoridade técnica para
recomendar apostas.

Loteria da Caixa NÃO é aposta de quota fixa, então essas regras não se aplicam
diretamente ao conteúdo em si. MAS elas se aplicam de cheio no momento em que
você colocar um link de afiliado de bet na legenda. Este módulo separa os dois
casos e trava a publicação quando algo está fora.

O QUE ELE VERIFICA

  Obrigatórios : aviso de não-previsão, +18, jogo responsável, ausência de
                 vínculo com a Caixa
  Proibidos    : promessa de ganho, "renda extra", "investimento", "garantido",
                 "vai sair", superlativos de método infalível
  Limites      : caracteres e hashtags dentro do que as plataformas aceitam
  Afiliados    : se houver link de bet, exige os avisos do Ministério da Fazenda

RESULTADO

  aprovado     -> pode publicar
  alerta       -> publica, mas revise
  reprovado    -> o robô NÃO publica

Como rodar:
    python -m src.conformidade                 # confere o próximo concurso
    python -m src.conformidade --concurso 3757
    python -m src.conformidade --texto "qualquer frase para testar"
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from src.coleta import RAIZ, carregar_base

PASTA_SAIDAS = RAIZ / "saidas"

LIMITE_CARACTERES = 2200
LIMITE_HASHTAGS = 30
MAX_ITENS_CARROSSEL = 10


# ---------------------------------------------------------------------------
# REGRAS
# ---------------------------------------------------------------------------

# Termos que NÃO podem aparecer. A busca ignora acento e maiúscula.
# Cada item é (expressão regular, gravidade, por quê).
PROIBIDOS: list[tuple[str, str, str]] = [
    (r"ganho garantid", "reprovado", "promessa de resultado"),
    (r"lucro cert", "reprovado", "promessa de resultado"),
    (r"resultado garantid", "reprovado", "promessa de resultado"),
    (r"\bgarantimos\b", "reprovado", "promessa de resultado"),
    (r"metodo infalivel", "reprovado", "promessa de resultado"),
    (r"\b100% de acerto", "reprovado", "promessa de resultado"),
    (r"dinheiro facil", "reprovado", "sugere ganho fácil"),
    (r"fique rico", "reprovado", "sugere enriquecimento"),
    (r"enriquec", "reprovado", "sugere enriquecimento"),
    (r"renda extra", "reprovado", "apresenta aposta como fonte de renda"),
    (r"fonte de renda", "reprovado", "apresenta aposta como fonte de renda"),
    (r"\binvestimento\b", "reprovado", "apresenta aposta como investimento"),
    (r"\binvista\b", "reprovado", "apresenta aposta como investimento"),
    (r"vai sair", "reprovado", "afirma previsão de resultado"),
    (r"numeros certos", "reprovado", "afirma previsão de resultado"),
    (r"palpite certeir", "reprovado", "afirma previsão de resultado"),
    (r"ultima chance", "alerta", "cria urgência artificial"),
    (r"corre que acaba", "alerta", "cria urgência artificial"),
    (r"so hoje", "alerta", "cria urgência artificial"),
    (r"\bmilionari", "alerta", "associa aposta a sucesso financeiro"),
    (r"mude de vida", "alerta", "associa aposta a sucesso pessoal"),
]

# Trechos que TÊM que aparecer, cada um com uma forma de detectar.
OBRIGATORIOS: list[tuple[str, str, str]] = [
    (r"nao e previsao|nao se trata de previsao", "reprovado",
     "aviso de que não é previsão"),
    (r"\+18|maiores de 18|proibido para menores", "reprovado",
     "restrição de idade"),
    (r"responsabilidade|jogue com responsa", "reprovado",
     "lembrete de jogo responsável"),
    (r"sem vinculo|nao possui vinculo|nao tem vinculo", "alerta",
     "declaração de ausência de vínculo com a Caixa"),
    (r"mesma probabilidade|igual probabilidade|probabilidade", "alerta",
     "explicação de que as combinações são equiprováveis"),
]

# Domínios de casas de aposta. Se aparecer um destes, entram as regras
# federais de publicidade de bets (Portarias de julho/2026).
PADRAO_BET = re.compile(r"\b[\w-]+\.bet\.br\b|\bbet365|\bbetano|\bblaze|\bstake\b", re.I)

# Avisos exigidos pelo Ministério da Fazenda quando há publicidade de bet
AVISOS_FAZENDA = [
    "apostar pode causar dependencia",
    "apostar faz voce perder dinheiro",
    "aposta nao e investimento",
]


def _normalizar(texto: str) -> str:
    """Tira acento e deixa minúsculo, para a busca não depender de grafia."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower()


# ---------------------------------------------------------------------------
# VERIFICAÇÃO DE UM TEXTO
# ---------------------------------------------------------------------------


def verificar_texto(texto: str, rotulo: str = "legenda") -> list[dict[str, Any]]:
    achados: list[dict[str, Any]] = []
    plano = _normalizar(texto)

    # Os avisos oficiais do Ministério da Fazenda contêm, por exigência legal,
    # palavras que estão na nossa lista de proibidos ("aposta não é
    # investimento"). Retiramos esses trechos antes de procurar irregularidade,
    # senão o texto obrigatório reprovaria a si mesmo.
    plano_sem_avisos = plano
    for aviso in AVISOS_FAZENDA:
        plano_sem_avisos = plano_sem_avisos.replace(aviso, " ")

    for padrao, gravidade, motivo in PROIBIDOS:
        encontrado = re.search(padrao, plano_sem_avisos)
        if encontrado:
            achados.append({
                "onde": rotulo, "nivel": gravidade, "tipo": "termo proibido",
                "detalhe": f"'{encontrado.group()}' — {motivo}",
            })

    for padrao, gravidade, oquee in OBRIGATORIOS:
        if not re.search(padrao, plano):
            achados.append({
                "onde": rotulo, "nivel": gravidade, "tipo": "falta obrigatório",
                "detalhe": f"não encontrei {oquee}",
            })

    if len(texto) > LIMITE_CARACTERES:
        achados.append({
            "onde": rotulo, "nivel": "reprovado", "tipo": "limite",
            "detalhe": f"{len(texto)} caracteres (máximo {LIMITE_CARACTERES})",
        })

    hashtags = [p for p in texto.split() if p.startswith("#")]
    if len(hashtags) > LIMITE_HASHTAGS:
        achados.append({
            "onde": rotulo, "nivel": "reprovado", "tipo": "limite",
            "detalhe": f"{len(hashtags)} hashtags (máximo {LIMITE_HASHTAGS})",
        })

    # Regras federais de publicidade de bets — só valem se houver link de bet
    if PADRAO_BET.search(texto):
        achados.append({
            "onde": rotulo, "nivel": "alerta", "tipo": "publicidade de bet",
            "detalhe": "há link/menção de casa de apostas: aplicam-se as regras "
                       "federais de publicidade de bets (vigentes desde 17/07/2026)",
        })
        for aviso in AVISOS_FAZENDA:
            if aviso not in plano:
                achados.append({
                    "onde": rotulo, "nivel": "reprovado", "tipo": "publicidade de bet",
                    "detalhe": f"falta o aviso obrigatório: '{aviso}'",
                })
                break
        if not re.search(r"publi|patrocinad|parceria paga|#ad\b", plano):
            achados.append({
                "onde": rotulo, "nivel": "reprovado", "tipo": "publicidade de bet",
                "detalhe": "publicidade paga sem identificação (#publi / #ad)",
            })

    return achados


# ---------------------------------------------------------------------------
# VERIFICAÇÃO DO PACOTE INTEIRO DO CONCURSO
# ---------------------------------------------------------------------------


def verificar_concurso(concurso: int) -> dict[str, Any]:
    achados: list[dict[str, Any]] = []
    pasta = PASTA_SAIDAS / str(concurso)

    # 1. legendas (as três, não só a escolhida)
    arquivo = pasta / "legendas.json"
    if not arquivo.exists():
        achados.append({"onde": "legendas", "nivel": "reprovado", "tipo": "faltando",
                        "detalhe": "legendas.json não encontrado"})
    else:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        for nome, v in dados["variacoes"].items():
            achados += verificar_texto(v["texto"], f"legenda/{nome}")

    # 2. peças
    indice = pasta / "pecas.json"
    if not indice.exists():
        achados.append({"onde": "peças", "nivel": "reprovado", "tipo": "faltando",
                        "detalhe": "pecas.json não encontrado"})
    else:
        dados = json.loads(indice.read_text(encoding="utf-8"))
        for estilo, arquivos in dados["estilos"].items():
            slides = arquivos["carrossel"]
            if len(slides) > MAX_ITENS_CARROSSEL:
                achados.append({
                    "onde": f"peças/{estilo}", "nivel": "reprovado", "tipo": "limite",
                    "detalhe": f"{len(slides)} slides (Instagram aceita {MAX_ITENS_CARROSSEL})",
                })
            faltando = [c for c in slides + [arquivos["feed"], arquivos["stories"]]
                        if not Path(c).exists()]
            if faltando:
                achados.append({
                    "onde": f"peças/{estilo}", "nivel": "reprovado", "tipo": "faltando",
                    "detalhe": f"{len(faltando)} imagem(ns) não gerada(s)",
                })
            # o slide de aviso legal precisa existir
            if not any("aviso" in c for c in slides):
                achados.append({
                    "onde": f"peças/{estilo}", "nivel": "reprovado", "tipo": "falta obrigatório",
                    "detalhe": "carrossel sem o slide de aviso legal",
                })

    # 3. os jogos precisam bater com a auditoria da Etapa 3
    from src.jogos import carregar_jogos
    jogos = carregar_jogos(concurso)
    if jogos is None:
        achados.append({"onde": "jogos", "nivel": "reprovado", "tipo": "faltando",
                        "detalhe": f"jogos do concurso {concurso} não gerados"})
    else:
        c = jogos["conferencia"]
        if c["jogos_duplicados"]:
            achados.append({"onde": "jogos", "nivel": "reprovado", "tipo": "qualidade",
                            "detalhe": f"{c['jogos_duplicados']} jogo(s) duplicado(s)"})
        if not c["todos_dentro_das_regras"]:
            achados.append({"onde": "jogos", "nivel": "alerta", "tipo": "qualidade",
                            "detalhe": "algum jogo ficou fora do perfil-alvo"})

    reprovacoes = [a for a in achados if a["nivel"] == "reprovado"]
    alertas = [a for a in achados if a["nivel"] == "alerta"]

    return {
        "concurso": concurso,
        "situacao": "reprovado" if reprovacoes else ("alerta" if alertas else "aprovado"),
        "pode_publicar": not reprovacoes,
        "reprovacoes": reprovacoes,
        "alertas": alertas,
        "total_verificacoes": len(PROIBIDOS) + len(OBRIGATORIOS) + 4,
    }


def imprimir(r: dict[str, Any]) -> None:
    simbolo = {"aprovado": "APROVADO", "alerta": "APROVADO COM ALERTAS", "reprovado": "REPROVADO"}
    print("=" * 62)
    print(f"CONFORMIDADE — concurso {r['concurso']}: {simbolo[r['situacao']]}")
    print("=" * 62)

    if r["reprovacoes"]:
        print(f"\n  BLOQUEIOS ({len(r['reprovacoes'])}) — o robô não vai publicar:")
        for a in r["reprovacoes"]:
            print(f"    [{a['onde']}] {a['tipo']}: {a['detalhe']}")
    if r["alertas"]:
        print(f"\n  ALERTAS ({len(r['alertas'])}) — publica, mas vale revisar:")
        for a in r["alertas"]:
            print(f"    [{a['onde']}] {a['tipo']}: {a['detalhe']}")
    if not r["reprovacoes"] and not r["alertas"]:
        print("\n  Nada a corrigir. Conteúdo liberado para publicação.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Checklist de conformidade antes de publicar")
    parser.add_argument("--concurso", type=int, default=None)
    parser.add_argument("--texto", default=None, help="testa uma frase avulsa")
    args = parser.parse_args()

    if args.texto:
        achados = verificar_texto(args.texto, "texto avulso")
        if not achados:
            print("Nada a apontar nesse texto.")
        for a in achados:
            print(f"  [{a['nivel']}] {a['tipo']}: {a['detalhe']}")
    else:
        base = carregar_base()
        concurso = args.concurso or (base[-1]["concurso"] + 1 if base else 0)
        imprimir(verificar_concurso(concurso))
