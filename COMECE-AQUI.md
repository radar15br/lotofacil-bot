# Comece aqui — Radar 15

Dois arquivos fazem quase tudo sozinhos. Você só precisa clicar.

## Windows

1. Clique duas vezes em **`instalar.bat`**
   Instala tudo, roda os testes e gera as primeiras imagens. Leva ~3 minutos.
2. Clique duas vezes em **`configurar-github.bat`**
   Cria o repositório, envia os arquivos, liga o site e guarda as credenciais.

## Mac / Linux

Abra o Terminal na pasta do projeto e rode:

```bash
bash instalar.sh
bash configurar-github.sh
```

---

## O que cada um precisa que já esteja instalado

| Arquivo | Precisa de |
|---|---|
| `instalar.bat` / `.sh` | **Python** — https://www.python.org/downloads/ (no Windows, marque *Add Python to PATH*) |
| `configurar-github.bat` / `.sh` | **Git** — https://git-scm.com · **GitHub CLI** — https://cli.github.com |

Se algum estiver faltando, o próprio script avisa e diz onde baixar.

## O que os scripts NÃO conseguem fazer por você

Três coisas exigem login e aceite de termos em seu nome:

1. **Criar a conta do GitHub** (uma vez, em https://github.com)
2. **Criar o app no Meta for Developers** e pegar `IG_USER_ID` + `IG_TOKEN`
   → Parte 2 do `CONFIGURACAO.md`, ~25 minutos
3. **Criar o app no TikTok for Developers** e pedir a auditoria
   → Parte 3 do `CONFIGURACAO.md`

O `configurar-github.sh` pergunta as credenciais no fim e guarda tudo
criptografado no GitHub. Se você ainda não as tiver, é só teclar Enter e rodar
o script de novo depois.

## Ordem recomendada

```
1. instalar.bat            → o robô funciona no seu computador
2. configurar-github.bat   → o robô vai para a nuvem (pode pular as credenciais)
3. CONFIGURACAO.md Parte 2 → pegar IG_USER_ID e IG_TOKEN
4. configurar-github.bat   → rode de novo só para guardar as credenciais
5. CONFIGURACAO.md Parte 3 → TikTok (a auditoria demora, comece cedo)
```

Depois disso o robô roda sozinho, de segunda a sábado, às 21h30.
