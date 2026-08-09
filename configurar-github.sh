#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# RADAR 15 — SUBIR PARA O GITHUB E LIGAR A AUTOMAÇÃO (Mac e Linux)
#
# Este arquivo faz por você, via linha de comando:
#   1. login no GitHub (abre o navegador uma vez)
#   2. cria o repositório público
#   3. envia todos os arquivos
#   4. liga o GitHub Pages na pasta docs/
#   5. cadastra os segredos e as variáveis do robô
#
# O único momento em que você digita algo é o login e as credenciais das APIs.
#
# Como usar:  bash configurar-github.sh
# ---------------------------------------------------------------------------
set -u

cd "$(dirname "$0")"

NOME_REPO="lotofacil-bot"

echo "=============================================================="
echo " RADAR 15 — configuração do GitHub"
echo "=============================================================="

# --- 0. o GitHub CLI está instalado? ---
if ! command -v gh >/dev/null 2>&1; then
  echo
  echo "Falta o GitHub CLI (programa 'gh'). Instale assim:"
  echo
  echo "  Mac:            brew install gh"
  echo "  Ubuntu/Debian:  sudo apt install gh"
  echo "  Outros:         https://cli.github.com"
  echo
  echo "Depois rode este arquivo de novo."
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "Falta o git. Instale em https://git-scm.com e rode de novo."
  exit 1
fi

# --- 1. login ---
echo
echo "[1/5] Login no GitHub"
if gh auth status >/dev/null 2>&1; then
  echo "      já está logado como: $(gh api user --jq .login)"
else
  echo "      vai abrir o navegador — autorize e volte para cá"
  gh auth login -h github.com -p https -w || exit 1
fi

USUARIO=$(gh api user --jq .login)
echo "      usuário: $USUARIO"

# --- 2. repositório local ---
echo
echo "[2/5] Preparando os arquivos"
if [ ! -d .git ]; then
  git init -q -b main
fi
git add -A
git -c user.email="bot@local" -c user.name="$USUARIO" commit -q -m "Radar 15 — primeira versão" 2>/dev/null || true
echo "      arquivos prontos para envio"

# --- 3. criar e enviar ---
echo
echo "[3/5] Criando o repositório no GitHub e enviando"
if gh repo view "$USUARIO/$NOME_REPO" >/dev/null 2>&1; then
  echo "      o repositório já existe — sincronizando antes de enviar"
  git remote add origin "https://github.com/$USUARIO/$NOME_REPO.git" 2>/dev/null || true
  # O próprio robô grava dados e imagens no repositório quando roda na nuvem.
  # Por isso o remoto quase sempre está à frente: buscamos o que há lá e
  # mantemos a SUA versão dos arquivos que existem dos dois lados.
  git fetch origin main 2>/dev/null || true
  git merge -X ours origin/main -m "sincroniza com o que o robô gravou" 2>/dev/null || true
  git push -u origin main 2>/dev/null || git push origin main
else
  gh repo create "$NOME_REPO" --public --source=. --remote=origin --push || {
    echo "ERRO ao criar o repositório."; exit 1; }
fi
echo "      https://github.com/$USUARIO/$NOME_REPO"

# --- 4. GitHub Pages ---
echo
echo "[4/5] Ligando o GitHub Pages (pasta docs/)"
gh api -X POST "repos/$USUARIO/$NOME_REPO/pages" \
  -f "source[branch]=main" -f "source[path]=/docs" >/dev/null 2>&1 \
  && echo "      Pages ligado" \
  || echo "      Pages já estava ligado (ou precisa ser ligado à mão em Settings > Pages)"

URL_PUBLICA="https://$USUARIO.github.io/$NOME_REPO"
echo "      endereço público: $URL_PUBLICA"

# --- 5. segredos e variáveis ---
echo
echo "[5/5] Credenciais do robô"
echo "      Deixe em branco e tecle Enter para preencher depois."
echo

gh variable set URL_BASE_PUBLICA  --body "$URL_PUBLICA"      >/dev/null 2>&1
gh variable set IG_MODO           --body "instagram_login"   >/dev/null 2>&1
gh variable set TIKTOK_PRIVACIDADE --body "SELF_ONLY"        >/dev/null 2>&1
echo "      variáveis padrão cadastradas"
echo

read -r -p "      IG_USER_ID (número da conta do Instagram): " IG_ID
[ -n "$IG_ID" ] && gh secret set IG_USER_ID --body "$IG_ID" >/dev/null 2>&1 && echo "      IG_USER_ID guardado"

read -r -s -p "      IG_TOKEN (não vai aparecer na tela): " IG_TK; echo
[ -n "$IG_TK" ] && gh secret set IG_TOKEN --body "$IG_TK" >/dev/null 2>&1 && echo "      IG_TOKEN guardado"

read -r -s -p "      TIKTOK_TOKEN (opcional, Enter para pular): " TT_TK; echo
[ -n "$TT_TK" ] && gh secret set TIKTOK_TOKEN --body "$TT_TK" >/dev/null 2>&1 && echo "      TIKTOK_TOKEN guardado"

echo
echo "=============================================================="
echo " PRONTO."
echo
echo " Repositório : https://github.com/$USUARIO/$NOME_REPO"
echo " Site        : $URL_PUBLICA  (leva alguns minutos para publicar)"
echo " Automação   : https://github.com/$USUARIO/$NOME_REPO/actions"
echo
echo " Teste agora sem publicar de verdade:"
echo "   gh workflow run 'Lotofacil Bot' -f simular=true"
echo
echo " Para adicionar ou trocar uma credencial depois:"
echo "   gh secret set IG_TOKEN"
echo "=============================================================="
