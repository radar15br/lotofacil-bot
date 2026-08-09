@echo off
chcp 65001 >nul
title Radar 15 - Instalacao
setlocal

cd /d "%~dp0"

echo ==============================================================
echo  RADAR 15 - instalacao
echo ==============================================================

REM --- 1. Python existe? ---
where python >nul 2>&1
if errorlevel 1 (
  echo.
  echo ERRO: nao encontrei o Python neste computador.
  echo Instale em https://www.python.org/downloads/
  echo IMPORTANTE: marque a caixa "Add Python to PATH" durante a instalacao.
  echo.
  pause
  exit /b 1
)
echo.
echo [1/5] Python encontrado:
python --version

REM --- 2. ambiente isolado ---
echo [2/5] Criando o ambiente isolado (.venv)...
python -m venv .venv >nul 2>&1
call .venv\Scripts\activate.bat

REM --- 3. bibliotecas ---
echo [3/5] Instalando as bibliotecas... (pode levar 1 a 2 minutos)
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
  echo ERRO ao instalar as bibliotecas.
  echo Rode manualmente: .venv\Scripts\activate  e depois  pip install -r requirements.txt
  pause
  exit /b 1
)

echo       Instalando o navegador que gera as imagens... (~150 MB, so uma vez)
python -m playwright install chromium >nul 2>&1
if errorlevel 1 (
  echo AVISO: nao consegui instalar o Chromium automaticamente.
  echo Rode manualmente: playwright install chromium
)

REM --- 4. testes ---
echo [4/5] Rodando os testes...
python tests\test_coleta.py
python tests\test_desempenho.py

REM --- 5. simulacao ---
echo [5/5] Rodando o robo inteiro em modo simulacao...
echo.
python -m src.executar --sem-publicar

echo.
echo ==============================================================
echo  PRONTO.
echo.
echo  As imagens estao em:  saidas\^<numero-do-concurso^>\
echo  Os paineis estao em:  saidas\dashboard.html e saidas\painel.html
echo.
echo  Proximo passo: clique duas vezes em configurar-github.bat
echo ==============================================================
echo.
pause
