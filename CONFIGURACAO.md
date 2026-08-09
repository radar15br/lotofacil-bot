# Configuração do zero — do repositório à publicação automática

Guia completo. Siga na ordem. O que dá para fazer hoje está marcado com ⏱️;
o que depende de aprovação de terceiros está marcado com ⏳.

---

## Parte 1 — Colocar o robô no GitHub ⏱️ (20 minutos)

### 1.1 Criar a conta e o repositório

1. Crie uma conta em https://github.com (grátis)
2. Clique em **New repository**
3. Nome: `lotofacil-bot`
4. Marque **Public** — repositório público dá minutos de execução ilimitados
   e libera o GitHub Pages de graça. Não há segredo no código: as senhas ficam
   guardadas separadamente, no cofre do GitHub.
5. **Create repository**

### 1.2 Enviar os arquivos

Pelo site, o caminho mais simples para quem está começando:

1. Na página do repositório, clique em **uploading an existing file**
2. Arraste **todas** as pastas do projeto (`src`, `data`, `tests`, `.github`,
   `requirements.txt`, `README.md`, `CONFIGURACAO.md`)
3. Escreva "primeira versão" e clique em **Commit changes**

> A pasta `.github` às vezes fica invisível no seu computador. No Windows,
> ative "Itens ocultos" na aba Exibir do Explorador de Arquivos.

### 1.3 Ligar o GitHub Pages

É aqui que as imagens ganham um endereço público — **sem isso nenhuma das duas
APIs consegue publicar**, porque as duas buscam a imagem por URL.

1. No repositório: **Settings** → **Pages**
2. Em *Source*, escolha **Deploy from a branch**
3. Branch: `main` · Pasta: `/docs`
4. **Save**

Em alguns minutos seu endereço fica assim:

```
https://SEU-USUARIO.github.io/lotofacil-bot
```

Guarde esse endereço. Ele é o `URL_BASE_PUBLICA`.

---

## Parte 2 — Instagram ⏱️ (25 minutos)

> **Boa notícia:** desde julho de 2024 a Meta oferece a *API do Instagram com
> Login do Instagram*, que **não exige página do Facebook**. É o caminho que o
> robô usa por padrão. A única coisa que ele não cobre é anúncio e marcação de
> produto — que você não vai usar.
>
> Se algum dia precisar do caminho antigo (via página do Facebook), basta
> definir a variável `IG_MODO=pagina_facebook`. O código suporta os dois.

### 2.1 Conta profissional ✅

Você já fez. Só confirme que está como **Empresa** (e não Criador): o botão
**Painel profissional** deve aparecer abaixo da sua bio.

### 2.2 Criar o app no Meta for Developers

1. Acesse https://developers.facebook.com e faça login
2. **Meus apps** → **Criar app**
3. Em *casos de uso*, escolha a opção relacionada ao **Instagram**
   (algo como "Outro" → tipo **Empresa**, ou o caso de uso do Instagram, se
   oferecido)
4. Nome do app: `Radar 15 Bot`
5. No app criado, adicione o produto **Instagram** → **Configurar**
6. Escolha a configuração **API do Instagram com login do Instagram**
   (*Instagram API setup with Instagram login*)

### 2.3 Conectar a sua conta

Ainda no painel do produto Instagram:

1. Procure a seção de **contas do Instagram** / *Generate access tokens*
2. Clique em **Adicionar conta** e faça login com o **@radar15br**
3. Autorize as permissões pedidas

### 2.4 Permissões necessárias

| Permissão | Para quê |
|---|---|
| `instagram_business_basic` | ler dados da conta |
| `instagram_business_content_publish` | **publicar o post** |

Com o app em **modo de desenvolvimento** essas permissões já funcionam para a
sua própria conta — que é o seu caso. Revisão do app só é exigida para publicar
em contas de terceiros.

### 2.5 Pegar o `IG_USER_ID` e o `IG_TOKEN`

No mesmo painel, ao lado da conta conectada, clique em **Gerar token**.

- O que aparecer como **ID da conta** é o seu `IG_USER_ID` (um número longo,
  não é o @arroba)
- O texto comprido é o seu `IG_TOKEN`. **Copie agora** — ele não é mostrado de novo

### 2.6 A validade do token — e como não ser pego de surpresa

Esse token dura **60 dias**. Ele pode ser renovado por mais 60 a qualquer
momento, e o robô já traz o comando pronto:

```bash
python -m src.publicar --renovar-token
```

Ele imprime o token novo e a validade. Copie e atualize o segredo `IG_TOKEN`
no GitHub.

**Coloque um lembrete mensal no celular.** Se o token expirar, o robô continua
gerando tudo — só a publicação para, e o log do GitHub Actions mostra
`Invalid OAuth access token`.

---

## Parte 3 — TikTok ⏳ (30 minutos + espera de aprovação)

### 3.1 Conta de desenvolvedor

1. Acesse https://developers.tiktok.com e entre com a conta do TikTok
2. **Manage apps** → **Connect an app**
3. Nome: `Lotofacil Bot` · descreva o uso: publicação automática de conteúdo
   informativo próprio

### 3.2 Adicionar o produto e o escopo

1. No app, adicione **Content Posting API**
2. Solicite o escopo **`video.publish`** (é ele que libera post de foto também)

### 3.3 Verificar o domínio

O TikTok só busca imagens de **domínio verificado**. Como as suas imagens ficam
no GitHub Pages:

1. No painel do app → **URL properties** → adicione
   `https://SEU-USUARIO.github.io/lotofacil-bot/`
2. O TikTok fornece um arquivo de verificação — coloque-o na pasta `docs/` do
   repositório e faça o commit
3. Volte ao painel e clique em **Verify**

### 3.4 A limitação que você precisa saber agora ⏳

Enquanto o app **não passar pela auditoria** do TikTok, todo post publicado pela
API entra como **privado** (`SELF_ONLY`) — vai para a sua conta, mas ninguém vê.

Isso é regra da plataforma, não limitação do código. O robô já vem configurado
para respeitar isso. Depois da aprovação, mude a variável
`TIKTOK_PRIVACIDADE` para `PUBLIC_TO_EVERYONE` e pronto.

A auditoria é solicitada no painel do app. O prazo varia — comece cedo.

**Enquanto espera:** o Instagram publica normalmente. O robô continua gerando
as imagens do TikTok, e você publica na mão pelo app se quiser.

---

## Parte 4 — Cadastrar as credenciais no GitHub ⏱️ (5 minutos)

No repositório: **Settings** → **Secrets and variables** → **Actions**

### Aba "Secrets" (informação sensível, fica criptografada)

| Nome | Valor |
|---|---|
| `IG_USER_ID` | o número do passo 2.5 |
| `IG_TOKEN` | o token do passo 2.5 |
| `TIKTOK_TOKEN` | o token do TikTok |

### Aba "Variables" (não é sensível)

| Nome | Valor |
|---|---|
| `URL_BASE_PUBLICA` | `https://SEU-USUARIO.github.io/lotofacil-bot` |
| `TIKTOK_PRIVACIDADE` | `SELF_ONLY` (troque depois da auditoria) |
| `IG_MODO` | `instagram_login` (só mude se for usar página do Facebook) |

---

## Parte 5 — Testar antes de soltar ⏱️

### 5.1 No seu computador, sem publicar nada

```bash
python -m src.executar --simular
```

Isso roda tudo — coleta, jogos, imagens, legendas — e **mostra** as chamadas de
API que seriam feitas, sem enviar. Se terminar com "0 passo(s) com erro", está
pronto.

### 5.2 No GitHub, ainda sem publicar

1. Aba **Actions** → **Lotofacil Bot** → **Run workflow**
2. Marque a caixa **Rodar sem publicar de verdade**
3. **Run workflow**

Acompanhe o log. No fim, baixe o artefato `pecas-do-dia` para ver as imagens
que o robô gerou na nuvem.

### 5.3 Publicação de verdade

Repita o 5.2 **sem** marcar a caixa. Confira o post no Instagram.

### 5.4 Deixar rodando sozinho

Nada a fazer — o agendamento já está no arquivo
`.github/workflows/lotofacil.yml`:

```
cron: "30 0 * * 2-6"    # seg a sex, 21h30 de Brasília
cron: "30 15 * * 0"     # domingo, 12h30 de Brasília
```

Desde **19/07/2026** a Caixa mudou o calendário: os sorteios de sábado passaram
para **domingo às 11h**. De segunda a sexta continuam às 20h. Por isso são dois
agendamentos — cada um roda cerca de uma hora e meia depois da apuração.

O GitHub trabalha em UTC e Brasília é UTC-3, por isso os horários aparecem
deslocados.

Para mudar o horário, altere só esse número: o primeiro campo é o minuto, o
segundo é a hora **em UTC**. O último campo são os dias da semana, numerados
de 0 a 6, sendo **0 = domingo**. O dia 7 não existe — usar `2-7` faz o GitHub
rejeitar o arquivo inteiro.

---

## Custo mensal real

| Item | Custo |
|---|---|
| GitHub Actions (repositório público) | R$ 0 — ilimitado |
| GitHub Pages | R$ 0 |
| API da Caixa | R$ 0 |
| Instagram Graph API | R$ 0 |
| TikTok Content Posting API | R$ 0 |
| **Total de infraestrutura** | **R$ 0/mês** |

O único custo real é o das apostas, se você optar por jogá-las: R$ 45,50 por
concurso (13 × R$ 3,50), cerca de R$ 1.183/mês nos 26 concursos mensais.
**Jogar não é necessário para o conteúdo funcionar** — o robô publica a análise
independentemente disso.

---

## Quando algo der errado

| Sintoma | Causa provável | Solução |
|---|---|---|
| `The image_url is not accessible` | GitHub Pages ainda não publicou | Espere 5 min e rode de novo. Teste abrindo a URL da imagem no navegador |
| `Media type not supported` | está mandando PNG | O robô já gera `.jpg` — confira se `URL_BASE_PUBLICA` está correta |
| `(#10) Application does not have permission` | falta permissão no app | Revise o passo 2.4 |
| `Invalid OAuth access token` | token expirou (60 dias) | Rode `python -m src.publicar --renovar-token` e atualize o segredo |
| Post do TikTok não aparece para ninguém | app ainda não auditado | Esperado. Veja o passo 3.4 |
| `url ownership unverified` (TikTok) | domínio não verificado | Refaça o passo 3.3 |
| Workflow não roda no horário | GitHub atrasa cron em horário de pico | Normal, pode atrasar alguns minutos. Se passar de 1h, rode manualmente |
| Repositório ficou pesado | as imagens acumulam | Rode `git rm -r --cached saidas/` e adicione `saidas/` ao `.gitignore` |

---

## Ordem sugerida de execução

1. **Hoje:** Partes 1, 2 e 4 → Instagram publicando automaticamente (sem página do Facebook)
2. **Hoje também:** Parte 3 até o 3.3 → solicite a auditoria do TikTok
3. **Enquanto espera:** acompanhe o teste A/B das legendas
   (`python -m src.legendas --relatorio`)
4. **Depois da aprovação:** troque `TIKTOK_PRIVACIDADE` para
   `PUBLIC_TO_EVERYONE`

---

## Aviso

Este robô publica conteúdo de análise estatística. Ele **não** promete
resultado, **não** vende palpite garantido e **não** tem vínculo com a Caixa
Econômica Federal. Manter esse posicionamento não é só ética — é o que reduz o
risco de restrição das contas nas duas plataformas.
