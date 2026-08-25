"""
ETAPA 7B — O ROBÔ COMPLETO, EM UM COMANDO
==========================================

Este é o arquivo que o GitHub Actions chama todo dia. Ele faz, em ordem:

  0. Reconfere um lote da base contra a API oficial da Caixa
  0B. Roda a auditoria estatística (qui-quadrado) e salva data/analise.json
  1. Busca o resultado do concurso que acabou de sair
  2. Confere os jogos gerados na véspera E publica o post de RESULTADO
  3. Gera os 13 jogos do PRÓXIMO concurso
  4. Gera as imagens (2 estilos, 3 formatos)
  5. Gera as 3 legendas e escolhe uma pelo rodízio A/B
  6. Atualiza os painéis HTML
  7. Roda o checklist de conformidade (trava a publicação se reprovar)
  8. Copia as imagens para a pasta pública (GitHub Pages)

A PUBLICAÇÃO é um comando separado (--somente-publicar), que roda DEPOIS que
as imagens já estão no ar. Instagram e TikTok não recebem o arquivo: eles
buscam a imagem por URL, então ela precisa existir antes.

Se qualquer passo falhar, os anteriores já feitos permanecem. O robô informa
onde parou em vez de desfazer tudo.

Como rodar:
    python -m src.executar              # tudo, publicando
    python -m src.executar --simular    # tudo, sem publicar de verdade
    python -m src.executar --sem-publicar
"""

from __future__ import annotations

import argparse
import json
import traceback
from datetime import datetime
from pathlib import Path

from src import analise, conformidade, dashboard, desempenho, jogos, legendas, painel, pecas, publicar
from src.coleta import PASTA_DADOS, atualizar, carregar_base, reconferir


def publicar_pendentes(simular: bool = False) -> int:
    """
    Fase de PUBLICAÇÃO, separada da geração.

    Por que separada: o Instagram e o TikTok não recebem o arquivo — eles vão
    BUSCAR a imagem numa URL pública. Ou seja, a imagem precisa estar no ar
    ANTES de publicar. Como quem coloca a imagem no ar é o passo de envio para
    o GitHub, a publicação tem que acontecer depois dele, e não junto da geração.
    """
    base = carregar_base()
    if not base:
        print("Base vazia — nada a publicar.")
        return 1

    proximo = base[-1]["concurso"] + 1
    erros = 0

    print("=" * 62)
    print("PUBLICAÇÃO" + (" (SIMULAÇÃO)" if simular else ""))
    print("=" * 62)

    # 1. resultados que já foram montados e ainda não foram ao ar
    for arquivo in sorted(pecas.PASTA_SAIDAS.glob("*/resultado.json")):
        concurso = int(arquivo.parent.name)
        if publicar.ja_publicado(concurso, "resultado"):
            continue
        try:
            publicar.registrar(concurso, publicar.publicar_resultado(concurso, "radar", simular))
        except publicar.PublicacaoError as erro:
            erros += 1
            print(f"  resultado do {concurso} não publicou: {erro}")

    # 2. o jogo do próximo concurso
    if publicar.ja_publicado(proximo, "feed"):
        print(f"\nJogo do concurso {proximo} já havia sido publicado. Nada a fazer.")
    else:
        for rede, funcao in (
            ("Instagram", lambda: publicar.publicar_instagram(proximo, "radar", "feed", simular)),
            ("TikTok", lambda: publicar.publicar_tiktok(proximo, "radar", simular)),
        ):
            try:
                publicar.registrar(proximo, funcao())
            except publicar.PublicacaoError as erro:
                erros += 1
                print(f"  {rede} não publicou: {erro}")

    print("\n" + "=" * 62)
    print(f"Publicação concluída · {erros} falha(s)")
    print("=" * 62)
    return 0 if erros == 0 else 1


def executar(simular: bool = False, publicar_redes: bool = True) -> int:
    inicio = datetime.now()
    print("=" * 62)
    print(f"LOTOFÁCIL BOT — execução de {inicio.strftime('%d/%m/%Y %H:%M')}")
    print("=" * 62)

    erros = 0

    def passo(numero: int, titulo: str, funcao, obrigatorio: bool = True):
        nonlocal erros
        print(f"\n[{numero}] {titulo}")
        try:
            return funcao()
        except Exception as erro:  # noqa: BLE001
            erros += 1
            print(f"    FALHOU: {erro}")
            if not obrigatorio:
                return None
            traceback.print_exc()
            return None

    # 0. reconferência contra a fonte oficial
    def verificar_base():
        r = reconferir(verboso=True)
        if r["divergencias"]:
            print(f"    ATENÇÃO: {len(r['divergencias'])} divergência(s) corrigida(s)")
        return r
    passo(0, "Reconferindo a base na fonte oficial", verificar_base, obrigatorio=False)

    # 0B. auditoria estatística — roda os testes qui-quadrado (dezenas quentes,
    # moldura/miolo/primos/pares) e salva o relatório em data/analise.json.
    # É diagnóstico: nunca bloqueia a publicação, só registra se a base
    # continua se comportando como um sorteio honesto.
    def auditoria_estatistica():
        base_auditoria = carregar_base()
        if not base_auditoria:
            print("    base vazia — pulando")
            return None
        relatorio = analise.analisar(base_auditoria, janela=100)
        destino = Path(PASTA_DADOS) / "analise.json"
        destino.write_text(json.dumps(relatorio, ensure_ascii=False, indent=1), encoding="utf-8")
        for rotulo, t in relatorio["testes_aderencia_grupos"].items():
            marca = "ok" if t["compativel_com_hipergeometrica"] else "DESVIO"
            print(f"    {rotulo:8} p={t['p_valor']:.4f} -> {marca}")
        return relatorio
    passo("0B", "Auditoria estatística (qui-quadrado)", auditoria_estatistica, obrigatorio=False)

    # 1. resultado novo
    # Não é obrigatório: se a Caixa estiver fora do ar, seguimos com a base que
    # já temos em disco em vez de abortar o dia inteiro.
    passo(1, "Buscando resultados novos na Caixa",
          lambda: atualizar(completo=False, verboso=True), obrigatorio=False)

    base = carregar_base()
    if not base:
        print("\nBase vazia — nada a fazer.")
        return 1
    ultimo = base[-1]["concurso"]
    proximo = ultimo + 1
    print(f"    último concurso na base: {ultimo} · próximo: {proximo}")

    # 2. conferência dos jogos da véspera + peça de resultado
    conferidos: list[int] = []

    def conferir():
        novos = desempenho.conferir_pendentes(verboso=True)
        conferidos.extend(r["concurso"] for r in novos)
        return novos
    passo(2, "Conferindo os jogos já gerados", conferir, obrigatorio=False)

    def preparar_resultados():
        for numero in conferidos:
            r = pecas.gerar_resultado(numero)
            legendas.gerar_resultado(numero)
            print(f"    concurso {numero}: {r['acertos']} acertos · peça e legenda prontas")
        if not conferidos:
            print("    nenhum concurso novo para conferir")
    passo(3, "Montando o post de resultado", preparar_resultados, obrigatorio=False)

    # 3. jogos do próximo concurso
    def gerar_jogos():
        r = jogos.gerar_jogos(base, concurso_alvo=proximo)
        jogos.salvar(r)
        c = r["conferencia"]
        print(f"    13 jogos · sobreposição máx {c['max_dezenas_em_comum']} · "
              f"uso {c['uso_minimo']}-{c['uso_maximo']} · regras ok: {c['todos_dentro_das_regras']}")
        return r
    passo(4, f"Gerando os 13 jogos do concurso {proximo}", gerar_jogos)

    # 4. imagens
    def gerar_pecas():
        r = pecas.gerar(proximo)
        total = sum(2 + len(v["carrossel"]) for v in r["estilos"].values())
        print(f"    {total} imagens em {len(r['estilos'])} estilos")
        return r
    passo(5, "Gerando as peças visuais", gerar_pecas)

    # 5. legendas
    def gerar_legendas():
        r = legendas.gerar(proximo)
        v = r["variacoes"][r["estilo_escolhido"]]
        print(f"    estilo do rodízio: {r['estilo_escolhido']} "
              f"({v['caracteres']} caracteres, {v['hashtags']} hashtags)")
        return r
    passo(6, "Gerando as legendas (rodízio A/B)", gerar_legendas)

    # 6. painéis
    def gerar_paineis():
        print(f"    {dashboard.gerar()}")
        print(f"    {painel.gerar()}")
    passo(7, "Atualizando os painéis", gerar_paineis, obrigatorio=False)

    # 6B. TRAVA DE CONFORMIDADE — nada é publicado sem passar por aqui
    liberado = True

    def checar_conformidade():
        nonlocal liberado
        r = conformidade.verificar_concurso(proximo)
        liberado = r["pode_publicar"]
        print(f"    situação: {r['situacao'].upper()}")
        for a in r["reprovacoes"] + r["alertas"]:
            print(f"    [{a['nivel']}] {a['onde']}: {a['detalhe']}")
        return r
    passo(8, "Checklist de conformidade", checar_conformidade, obrigatorio=False)

    if not liberado:
        print("\n    PUBLICAÇÃO BLOQUEADA pelo checklist. Corrija os pontos acima.")
        publicar_redes = False

    # 8 e 9. publicação
    # Copiar para a pasta pública SEMPRE: é isso que coloca as imagens no ar.
    # Sem elas no ar, a publicação da etapa seguinte não tem o que buscar.
    def copiar():
        for numero in conferidos:
            publicar.publicar_no_site(numero, verboso=False)
        publicar.publicar_no_site(proximo)
    passo(9, "Copiando imagens para a pasta pública", copiar, obrigatorio=False)

    print("\n[10] A publicação nas redes é um comando à parte "
          "(--somente-publicar), executado depois que as imagens estiverem no ar.")

    duracao = (datetime.now() - inicio).total_seconds()
    print("\n" + "=" * 62)
    print(f"Concluído em {duracao:.0f}s · {erros} passo(s) com erro")
    print("=" * 62)
    return 0 if erros == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa o robô inteiro")
    parser.add_argument("--simular", action="store_true", help="não publica de verdade")
    parser.add_argument("--sem-publicar", action="store_true", help="pula a etapa de publicação")
    parser.add_argument("--somente-publicar", action="store_true",
                        help="não gera nada; só publica o que já está pronto")
    args = parser.parse_args()

    if args.somente_publicar:
        raise SystemExit(publicar_pendentes(simular=args.simular))

    raise SystemExit(executar(simular=args.simular, publicar_redes=not args.sem_publicar))
