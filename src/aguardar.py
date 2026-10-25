"""
ESPERA PELO RESULTADO — o que deixa o post sair na hora certa
=============================================================

O agendador do GitHub atrasa (já chegou a ~5h). Em vez de depender do horário
exato, o robô agora começa ANTES do sorteio e fica esperando a Caixa publicar
o resultado. Assim que o resultado aparece, o restante do fluxo roda na hora.

Decisão (escrita em GITHUB_OUTPUT como seguir=true/false):

  - O próximo sorteio já passou e o resultado ainda não está na base
      -> segue na hora (estamos atrasados)
  - O sorteio é hoje e começa em até JANELA_MAX_H horas
      -> espera até o resultado sair (ou até o prazo) e segue
  - O sorteio é hoje mas ainda falta mais que isso, ou não é hoje
      -> não segue; uma execução mais tarde cuida disso

Como rodar:
    python -m src.aguardar
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.coleta import buscar_concurso, carregar_base

FUSO = ZoneInfo("America/Sao_Paulo")
JANELA_MAX_H = 4.5        # quanto o robô aceita esperar ANTES do sorteio
PRAZO_APOS_H = 3.0        # desiste de esperar 3h depois do horário do sorteio
INTERVALO_S = 90          # de quanto em quanto tempo consulta a Caixa
HORA_SORTEIO = {6: 11}    # domingo 11h; demais dias 21h


def _saida(seguir: bool, motivo: str) -> bool:
    print(f"{'SEGUIR' if seguir else 'PARAR'}: {motivo}")
    arquivo = os.getenv("GITHUB_OUTPUT")
    if arquivo:
        with open(arquivo, "a", encoding="utf-8") as f:
            f.write(f"seguir={'true' if seguir else 'false'}\n")
    return seguir


def _resultado_saiu(numero: int) -> bool:
    try:
        return buscar_concurso(numero).get("concurso") == numero
    except Exception as erro:  # noqa: BLE001 — fonte fora do ar = ainda não saiu
        print(f"  consulta falhou: {erro}")
        return False


def decidir(agora: datetime | None = None) -> bool:
    agora = agora or datetime.now(FUSO)
    base = carregar_base()
    if not base:
        return _saida(True, "base vazia")

    ultimo = base[-1]
    alvo = ultimo["concurso"] + 1
    data_txt = ultimo.get("data_proximo")
    if not data_txt:
        return _saida(True, "Caixa não informou a data do próximo sorteio")

    dia = datetime.strptime(data_txt, "%Y-%m-%d").replace(tzinfo=FUSO)
    sorteio = dia.replace(hour=HORA_SORTEIO.get(dia.weekday(), 21))
    prazo = sorteio + timedelta(hours=PRAZO_APOS_H)
    print(f"Próximo: concurso {alvo} em {sorteio:%d/%m/%Y %Hh} · agora {agora:%d/%m %H:%M}")

    # Publicação pendente (ex.: o Instagram falhou na execução anterior):
    # não há o que esperar, roda já para tentar de novo.
    from src.publicar import ja_publicado
    if not ja_publicado(alvo, "feed"):
        return _saida(True, f"jogo do concurso {alvo} ainda não foi publicado")

    if agora > prazo:
        return _saida(True, "sorteio já passou há tempo — rodando direto")
    if sorteio - agora > timedelta(hours=JANELA_MAX_H):
        return _saida(False, "ainda falta muito para o sorteio")

    while datetime.now(FUSO) < prazo:
        if datetime.now(FUSO) >= sorteio and _resultado_saiu(alvo):
            espera = datetime.now(FUSO) - sorteio
            return _saida(True, f"resultado do {alvo} publicado ({espera.seconds // 60} min após o sorteio)")
        time.sleep(INTERVALO_S)

    return _saida(True, "prazo de espera esgotado — rodando com o que houver")


if __name__ == "__main__":
    decidir()
