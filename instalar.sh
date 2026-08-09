#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# RADAR 15 — INSTALAÇÃO AUTOMÁTICA (Mac e Linux)
#
# Faz tudo que precisa ser feito no SEU computador:
#   1. cria o ambiente isolado do Python
#   2. instala as bibliotecas
#   3. instala o navegador que gera as imagens
#   4. roda os testes
#   5. roda o robô inteiro em modo simulação
#
# Como usar:  bash instalar.sh
# ---------------------------------------------------------------------------
set -u

cd "$(dirname "$0")"

echo "=============================================================="
echo " RADAR 15 — instalação"
echo "=============================================================="

# --- 1. Python existe? ---
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo
  echo "ERRO: não encontrei o Python neste computador."
  echo "Instale em https://www.python.org/downloads/ e rode este arquivo de novo."
  exit 1
fi
echo
echo "[1/5] Python encontrado: $($PY --version)"

# --- 2. ambiente isolado ---
echo "[2/5] Criando o ambiente isolado (.venv)..."
$PY -m venv .venv >/dev/null 2>&1
# shellcheck disable=SC1091
source .venv/bin/activate

# --- 3. bibliotecas ---
echo "[3/5] Instalando as bibliotecas... (pode levar 1 a 2 minutos)"
python -m pip install --upgrade pip >/dev/null 2>&1
python -m pip install -r requirements.txt >/dev/null 2>&1 || {
  echo "ERRO ao instalar as bibliotecas. Rode manualmente:"
  echo "  source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
}

echo "      Instalando o navegador que gera as imagens... (~150 MB, só uma vez)"
python -m playwright install chromium >/dev/null 2>&1 || {
  echo "AVISO: não consegui instalar o Chromium automaticamente."
  echo "Rode manualmente:  playwright install chromium"
}

# --- 4. testes ---
echo "[4/5] Rodando os testes..."
python tests/test_coleta.py     | tail -1
python tests/test_desempenho.py | tail -1

# --- 5. simulação ---
echo "[5/5] Rodando o robô inteiro em modo simulação..."
echo
python -m src.executar --sem-publicar

echo
echo "=============================================================="
echo " PRONTO."
echo
echo " As imagens estão em:  saidas/<numero-do-concurso>/"
echo " Os painéis estão em:  saidas/dashboard.html e saidas/painel.html"
echo
echo " Próximo passo: bash configurar-github.sh"
echo "=============================================================="
