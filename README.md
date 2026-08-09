# Lotofácil Bot — Etapa 1: Coleta de dados

Robô em Python que baixa o histórico completo da Lotofácil, guarda localmente
e atualiza sozinho apenas os concursos novos.

## Estrutura do projeto

```
lotofacil-bot/
├── src/
│   ├── coleta.py          <- Etapa 1: API da Caixa (concursos novos)
│   ├── importar_excel.py  <- Etapa 1B: carga do histórico via planilha
│   ├── analise.py         <- Etapa 2: estatística + teste de aleatoriedade
│   ├── dashboard.py       <- Etapa 2B: painel HTML interativo
│   ├── jogos.py           <- Etapa 3: gerador dos 13 jogos + backtest
│   ├── desempenho.py      <- Etapa 4: conferência e prova social
│   ├── pecas.py           <- Etapa 5: imagens para Instagram e TikTok
│   ├── legendas.py        <- Etapa 6: 3 copies + rodízio A/B
│   ├── publicar.py        <- Etapa 7: Instagram Graph API + TikTok
│   ├── conformidade.py    <- Etapa 8: trava de conformidade antes de publicar
│   ├── painel.py          <- Etapa 8: painel da operação
│   └── executar.py        <- roda tudo em um comando (é o que o robô chama)
├── data/
│   └── lotofacil.json     <- criado automaticamente na 1ª execução
├── tests/
│   └── test_coleta.py     <- teste que roda sem internet
├── saidas/                <- imagens e legendas (etapas futuras)
└── requirements.txt
```

## Caminho rápido

Se você só quer que funcione, abra o **`COMECE-AQUI.md`** — são dois cliques.
O passo a passo abaixo é para quem quer entender cada etapa.

## Passo a passo para rodar (do zero)

### 1. Instalar o Python

Baixe em https://www.python.org/downloads/ (versão 3.11 ou superior).
**No Windows, marque a caixinha "Add Python to PATH"** durante a instalação.

Confira no terminal (Prompt de Comando ou PowerShell):

```bash
python --version
```

### 2. Abrir a pasta do projeto no terminal

```bash
cd caminho/para/lotofacil-bot
```

### 3. Criar um ambiente isolado (recomendado)

Um "ambiente virtual" é uma caixinha separada para as bibliotecas deste
projeto, para não bagunçar o Python do sistema.

```bash
python -m venv .venv

# Windows:
.venv\Scripts\activate

# Mac/Linux:
source .venv/bin/activate
```

### 4. Instalar as bibliotecas

```bash
pip install -r requirements.txt
```

### 5. Testar sem internet (opcional, mas recomendado)

```bash
python tests/test_coleta.py
```

Deve terminar com `TODOS OS TESTES PASSARAM`.

### 6. Carregar o histórico

**Opção A — você já tem a planilha Excel (mais rápido, recomendado):**

```bash
python -m src.importar_excel "caminho/para/Lotofacil.xlsx"
```

Leva 2 segundos e já roda uma auditoria completa da base. O módulo detecta
sozinho o formato das dezenas (uma coluna por bola, dezenas numa célula só,
ou matriz 1 a 25).

**Opção B — baixar tudo da API da Caixa:**

```bash
python -m src.coleta --completo
```

Baixa ~3.700 concursos. Leva **20 a 30 minutos** — existe uma pausa proposital
entre os pedidos para não sobrecarregar o servidor da Caixa. Só use esta opção
se não tiver a planilha.

### 7. Do dia a dia em diante

```bash
python -m src.coleta --atualizar
```

Segundos. Baixa só o que saiu depois da última execução.

### 8. Conferir o que está guardado

```bash
python -m src.coleta --status
```

### 9. Análise estatística (Etapa 2)

```bash
python -m src.analise --json    # relatório no terminal + data/analise.json
python -m src.analise --janela 500
python -m src.dashboard         # gera saidas/dashboard.html
```

O painel abre em qualquer navegador, funciona offline e tem filtro de janela
(histórico completo / últimos 1.000 / 500 / 100) e modo claro/escuro.

### 10. Gerar os 13 jogos (Etapa 3)

```bash
python -m src.jogos                 # gera para o próximo concurso
python -m src.jogos --concurso 3757 # gera para um concurso específico
python -m src.jogos --backtest 300  # testa o gerador no passado
python tests/test_jogos.py          # 200 gerações + auditoria
```

Os jogos ficam em `data/jogos/{concurso}.json`. A semente aleatória é o número
do concurso: rodar duas vezes produz exatamente o mesmo resultado, o que torna
a prova social auditável.

### 11. Conferir resultados e acompanhar desempenho (Etapa 4)

```bash
python -m src.desempenho --pendentes   # confere tudo que já tem resultado
python -m src.desempenho --resumo 10   # prova social dos últimos 10 concursos
python -m src.desempenho --simular 200 # popula histórico SIMULADO (calibração)
python tests/test_desempenho.py
```

O histórico fica em `data/desempenho.json`. Cada registro é marcado como
**real** (jogos gerados antes do sorteio) ou **simulado** (backtest). As frases
de prova social usam só o que é real, salvo pedido explícito.

### 12. Gerar as peças visuais (Etapa 5)

Na primeira vez, instale o navegador que gera as imagens:

```bash
playwright install chromium
```

Depois:

```bash
python -m src.pecas                  # próximo concurso, nos 2 estilos
python -m src.pecas --concurso 3757
python -m src.pecas --estilo noite   # ou --estilo dia
```

Saída em `saidas/{concurso}/{estilo}/`:

| Arquivo | Tamanho | Uso |
|---|---|---|
| `feed.png` | 1080x1080 | post quadrado do Instagram |
| `stories.png` | 1080x1920 | Stories do Instagram e TikTok |
| `carrossel/1-capa.png` … `7-cta.png` | 1080x1350 | carrossel de 7 slides |

Para criar um terceiro estilo visual, copie um bloco do dicionário `ESTILOS`
em `src/pecas.py` e troque as cores. Nenhum outro arquivo precisa mudar.

### 13. Legendas com teste A/B (Etapa 6)

```bash
python -m src.legendas               # 3 versões, escolhe 1 pelo rodízio
python -m src.legendas --mostrar     # imprime as 3 inteiras
python -m src.legendas --relatorio   # compara o desempenho dos estilos
```

Depois de publicar, alimente as métricas para o teste A/B valer:

```bash
python -c "from src.legendas import registrar_metricas; \
registrar_metricas(3757, curtidas=140, alcance=3200, salvamentos=22)"
```

### 14. Publicação e automação (Etapa 7)

**Leia o `CONFIGURACAO.md`** — é o passo a passo completo das contas, tokens e
do agendamento. Resumo dos comandos:

```bash
python -m src.publicar --simular     # mostra as chamadas, não envia nada
python -m src.publicar --rede instagram
python -m src.executar --simular     # o robô inteiro, sem publicar
python -m src.executar               # o robô inteiro, publicando
```

### 15. Conformidade e painel da operação (Etapa 8)

```bash
python -m src.conformidade                    # confere o próximo concurso
python -m src.conformidade --texto "frase"    # testa uma frase avulsa
python -m src.painel                          # gera saidas/painel.html
```

O checklist roda automaticamente dentro de `src.executar` e **bloqueia a
publicação** se encontrar promessa de resultado, faltar aviso obrigatório ou
estourar limite de plataforma.

Estratégia de monetização e checklist completo das plataformas: veja
`MONETIZACAO.md`.

### Rotina completa do dia a dia

Um comando só faz tudo:

```bash
python -m src.executar
```

Se preferir passo a passo:

```bash
python -m src.coleta --atualizar     # 1. busca o resultado que saiu
python -m src.desempenho --pendentes # 2. confere os jogos de ontem
python -m src.jogos                  # 3. gera os jogos do próximo concurso
python -m src.pecas                  # 4. gera as imagens do post
python -m src.legendas               # 5. gera as legendas
python -m src.dashboard              # 6. atualiza o painel
python -m src.publicar               # 7. publica nas redes
```

## Se der erro

| Erro | O que fazer |
|---|---|
| `SSLError` / `CERTIFICATE_VERIFY_FAILED` | Rode com `LOTOFACIL_SSL=0` na frente do comando (Windows: `set LOTOFACIL_SSL=0` antes) |
| `Nenhuma fonte respondeu` | A Caixa costuma ficar instável logo após o sorteio. Espere 10 min e rode de novo — o robô tenta a fonte alternativa sozinho |
| Alguns concursos em `falhas` | Rode `--atualizar` de novo; ele tenta apenas os que faltam |

## Formato dos dados salvos

```json
{
  "concurso": 3200,
  "data": "2026-08-07",
  "dezenas": [1, 2, 4, 5, 7, 9, 10, 12, 14, 16, 18, 20, 21, 23, 25],
  "acumulado": false,
  "ganhadores_15": 2,
  "fonte": "caixa"
}
```

Todas as etapas seguintes leem deste mesmo arquivo.

## Aviso

Este projeto faz **análise estatística de dados históricos**, não previsão.
Cada sorteio da Lotofácil é independente e todas as combinações têm a mesma
probabilidade matemática. Jogue com responsabilidade.
