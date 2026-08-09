# Monetização e conformidade — @radar15br

> Documento de estratégia. Os números de mercado são **premissas de cenário**,
> não garantias — confirme as comissões reais no site de cada programa antes de
> decidir.

---

## 1. O que mudou na lei em julho de 2026

Desde **17/07/2026** valem regras federais mais duras para publicidade de
apostas de quota fixa (as "bets"). O que elas proíbem:

- apresentar aposta como investimento ou fonte de renda
- sugerir ganho fácil ou enriquecimento
- criar urgência para apostar
- **divulgar histórico de premiações**
- associar aposta a sucesso pessoal ou financeiro
- direcionar conteúdo a menores

E o que exigem: um dos três avisos do Ministério da Fazenda ocupando **no
mínimo 10% do anúncio** — "Apostar pode causar dependência", "Apostar faz você
perder dinheiro", "Aposta não é investimento".

Há ainda uma regra que atinge diretamente perfis como o seu:
**comentaristas, especialistas e analistas não podem usar autoridade técnica
para recomendar apostas específicas.**

### O que isso significa na prática para o @radar15br

| Situação | As regras de bets se aplicam? |
|---|---|
| Conteúdo sobre Lotofácil, sem link de afiliado | **Não.** Loteria da Caixa não é aposta de quota fixa |
| Conteúdo com link de afiliado de **bolão/lotérica online** | **Não** diretamente, mas siga o mesmo padrão por segurança |
| Conteúdo com link de afiliado de **casa de apostas (bet)** | **Sim, integralmente.** Você vira agente da cadeia de veiculação |

A trava automática do robô (`src/conformidade.py`) já implementa essa
separação: se detectar link de bet na legenda, exige os avisos obrigatórios e a
identificação de publicidade — e bloqueia a publicação se faltar.

---

## 2. As três rotas de monetização, comparadas

### Rota A — Afiliado de bolão / lotérica online

Plataformas que intermediam apostas oficiais da Caixa (bolões online). O
público que já te segue é exatamente o público delas.

**Prós**

- Aderência total ao conteúdo — quem vê 13 jogos quer jogar
- Não cai nas regras de publicidade de bets
- Receita começa cedo, com audiência pequena
- Sem obrigação de entregar nada além do conteúdo que você já faz

**Contras**

- Comissão por conversão, não recorrente — receita oscila
- Você depende da reputação da plataforma; se ela falhar, sobra para você
- Exige verificar se a plataforma é intermediária legítima da Caixa

**Cuidado obrigatório:** confira se a plataforma tem credenciamento e histórico.
Bolão online é área com muita empresa improvisada. Uma denúncia de golpe respinga
no perfil que indicou.

### Rota B — Grupo pago (Telegram ou WhatsApp)

Assinatura mensal com conteúdo exclusivo: jogos extras, análises mais fundas,
conferência antecipada, relatório mensal.

**Prós**

- Receita **recorrente e previsível** — o que muda o jogo de verdade
- Você controla preço, produto e comunicação
- Não depende de política de terceiros
- Margem alta: o custo marginal de mais um assinante é zero

**Contras**

- Precisa de audiência antes — não converte no primeiro mês
- Cria obrigação de entrega diária; falhar gera cancelamento e reclamação
- **Risco de Código de Defesa do Consumidor** se a comunicação sugerir
  resultado. Você vende *análise*, nunca *palpite premiado*

### Rota C — Afiliado de casa de apostas (bet)

**Recomendação: não faça, pelo menos por enquanto.**

Paga mais por conversão, mas te coloca dentro do escopo integral das regras de
julho/2026 — inclusive a proibição de divulgar histórico de premiações, que é
justamente o seu diferencial de conteúdo. Você teria que escolher entre a
prova social e a receita de afiliado. Não compensa.

---

## 3. Modelo de cenário — quanto cada rota rende

Premissas conservadoras, para você ajustar com os seus números reais:

- 3% dos seguidores veem cada post e clicam no link da bio
- Conversão de clique para cliente: 5% (afiliado) · 2% (assinatura)
- Comissão de afiliado: R$ 30 por novo cliente (**confirme a real**)
- Assinatura: R$ 24,90/mês
- Cancelamento mensal da assinatura: 10%

| Seguidores | Rota A — afiliado | Rota B — assinatura (regime) | Rota A+B |
|---|---|---|---|
| 1.000 | ~R$ 45/mês | ~R$ 150/mês | ~R$ 195 |
| 5.000 | ~R$ 225/mês | ~R$ 750/mês | ~R$ 975 |
| 10.000 | ~R$ 450/mês | ~R$ 1.500/mês | ~R$ 1.950 |
| 25.000 | ~R$ 1.125/mês | ~R$ 3.700/mês | ~R$ 4.825 |

> "Regime" da assinatura significa o patamar em que entradas e cancelamentos se
> equilibram — leva de 4 a 6 meses para chegar lá.

**Leitura:** o afiliado paga as contas antes; a assinatura constrói o negócio.
Comece pela Rota A e prepare a Rota B para o terceiro mês.

---

## 4. Onde colocar os links

O Instagram não permite link clicável na legenda. As opções reais:

| Lugar | Como usar |
|---|---|
| **Link na bio** | um só link, para uma página que reúne tudo |
| **Stories** | link clicável direto (o robô já gera a peça de Stories) |
| **Comentário fixado** | texto do link + "link na bio" |
| **CTA do carrossel** | slide 7 já existe para isso |

No código, os campos ficam prontos em `src/legendas.py`:

```python
CTA_LINK = "https://sua-pagina.com"
CTA_TEXTO = "Jogue com o nosso parceiro (link na bio)"
```

Preencha e a linha aparece automaticamente nas três legendas. Deixe vazio e
ela some.

---

## 5. Checklist de conformidade — as duas plataformas

### Instagram / Meta

- [ ] Conta profissional do tipo **Empresa**
- [ ] Categoria **não** ligada a jogos de azar (use "Blog pessoal" ou
      "Site de notícias e mídia")
- [ ] Toda peça com **+18** e aviso de jogo responsável
- [ ] Nenhuma promessa de resultado em imagem, legenda ou bio
- [ ] Parceria paga marcada com a ferramenta de **conteúdo de marca** ou `#publi`
- [ ] Sem uso de logo ou identidade visual da Caixa
- [ ] Bio declara: análise estatística, sem vínculo com a Caixa

### TikTok

- [ ] Conta com data de nascimento correta (+18)
- [ ] Loteria é tratada como "jogo que não é de cassino" — permitido com
      restrição, sujeito a lei local
- [ ] Post pela API entra como **privado** até o app passar pela auditoria
- [ ] Sem conteúdo que sugira ganho fácil
- [ ] Publicidade identificada no próprio vídeo/foto, não só na descrição

### Brasil (legislação)

- [ ] Sem link de bet enquanto não houver estrutura para cumprir as regras de
      julho/2026
- [ ] Se houver: os três avisos do Ministério da Fazenda, em 10% da peça
- [ ] Nunca apresentar aposta como renda ou investimento
- [ ] Nunca recomendar aposta específica invocando autoridade técnica

### Rodando sozinho

O `src/conformidade.py` verifica 26 pontos automaticamente antes de cada
publicação e **bloqueia o post** se algo estiver fora. Para testar uma frase:

```bash
python -m src.conformidade --texto "sua frase aqui"
```

---

## 6. O que eu faria nos primeiros 90 dias

**Mês 1 — construir prova social real**
Publique todo dia. Nada de monetização. O objetivo é acumular concursos com
jogos registrados *antes* do sorteio, que é o que sustenta o discurso depois.
Meta: 26 posts, 1.000 seguidores.

**Mês 2 — testar o afiliado**
Escolha uma plataforma de bolão, coloque o link na bio, meça. Use o relatório
A/B (`python -m src.legendas --relatorio`) para descobrir qual estilo de legenda
converte. Meta: primeira comissão.

**Mês 3 — abrir a assinatura**
Só depois de ter audiência engajada. Preço de entrada baixo, entrega diária
garantida pelo robô. Meta: 50 assinantes.

**O que não fazer em nenhum momento:** prometer resultado, esconder que é
estatística, ou publicar histórico de premiação junto de link de bet.

---

## Aviso

Este documento não é aconselhamento jurídico. As regras de publicidade de
apostas no Brasil estão em evolução — confirme a redação vigente antes de
fechar qualquer contrato de afiliado, e considere consultar um advogado se a
operação crescer.
