@echo off
chcp 65001 >nul
title Radar 15 - Configuracao do GitHub
setlocal enabledelayedexpansion

cd /d "%~dp0"
set NOME_REPO=lotofacil-bot

echo ==============================================================
echo  RADAR 15 - configuracao do GitHub
echo ==============================================================

REM --- 0. ferramentas ---
where gh >nul 2>&1
if errorlevel 1 (
  echo.
  echo Falta o GitHub CLI (programa "gh"^).
  echo Baixe em: https://cli.github.com
  echo Instale, feche esta janela e rode este arquivo de novo.
  echo.
  pause
  exit /b 1
)
where git >nul 2>&1
if errorlevel 1 (
  echo Falta o git. Baixe em https://git-scm.com e rode de novo.
  pause
  exit /b 1
)

REM --- 1. login ---
echo.
echo [1/5] Login no GitHub
gh auth status >nul 2>&1
if errorlevel 1 (
  echo       vai abrir o navegador - autorize e volte para ca
  gh auth login -h github.com -p https -w
  if errorlevel 1 ( pause & exit /b 1 )
) else (
  echo       ja esta logado
)

for /f "delims=" %%u in ('gh api user --jq .login') do set USUARIO=%%u
echo       usuario: !USUARIO!

REM --- 2. arquivos ---
echo.
echo [2/5] Preparando os arquivos
if not exist .git ( git init -q -b main )
git add -A
git -c user.email="bot@local" -c user.name="!USUARIO!" commit -q -m "Radar 15 - primeira versao" 2>nul
echo       arquivos prontos para envio

REM --- 3. criar e enviar ---
echo.
echo [3/5] Criando o repositorio no GitHub e enviando
gh repo view !USUARIO!/%NOME_REPO% >nul 2>&1
if errorlevel 1 (
  gh repo create %NOME_REPO% --public --source=. --remote=origin --push
  if errorlevel 1 ( echo ERRO ao criar o repositorio. & pause & exit /b 1 )
) else (
  echo       o repositorio ja existe - sincronizando antes de enviar
  git remote add origin https://github.com/!USUARIO!/%NOME_REPO%.git 2>nul
  REM O proprio robo grava dados e imagens no repositorio quando roda na nuvem.
  REM Por isso o remoto quase sempre esta a frente: buscamos o que ha la e
  REM mantemos a SUA versao dos arquivos que existem dos dois lados.
  git fetch origin main 2>nul
  git merge -X ours origin/main -m "sincroniza com o que o robo gravou" 2>nul
  git push -u origin main
)
echo       https://github.com/!USUARIO!/%NOME_REPO%

REM --- 4. GitHub Pages ---
echo.
echo [4/5] Ligando o GitHub Pages (pasta docs/^)
gh api -X POST repos/!USUARIO!/%NOME_REPO%/pages -f "source[branch]=main" -f "source[path]=/docs" >nul 2>&1
if errorlevel 1 (
  echo       Pages ja estava ligado, ou precisa ser ligado a mao em Settings ^> Pages
) else (
  echo       Pages ligado
)
set URL_PUBLICA=https://!USUARIO!.github.io/%NOME_REPO%
echo       endereco publico: !URL_PUBLICA!

REM --- 5. credenciais ---
echo.
echo [5/5] Credenciais do robo
echo       Deixe em branco e tecle Enter para preencher depois.
echo.

gh variable set URL_BASE_PUBLICA --body "!URL_PUBLICA!" >nul 2>&1
gh variable set IG_MODO --body "instagram_login" >nul 2>&1
gh variable set TIKTOK_PRIVACIDADE --body "SELF_ONLY" >nul 2>&1
echo       variaveis padrao cadastradas
echo.

set /p IG_ID="      IG_USER_ID (numero da conta do Instagram): "
if not "!IG_ID!"=="" (
  gh secret set IG_USER_ID --body "!IG_ID!" >nul 2>&1
  echo       IG_USER_ID guardado
)

set /p IG_TK="      IG_TOKEN: "
if not "!IG_TK!"=="" (
  gh secret set IG_TOKEN --body "!IG_TK!" >nul 2>&1
  echo       IG_TOKEN guardado
)

set /p TT_TK="      TIKTOK_TOKEN (opcional, Enter para pular): "
if not "!TT_TK!"=="" (
  gh secret set TIKTOK_TOKEN --body "!TT_TK!" >nul 2>&1
  echo       TIKTOK_TOKEN guardado
)

echo.
echo ==============================================================
echo  PRONTO.
echo.
echo  Repositorio : https://github.com/!USUARIO!/%NOME_REPO%
echo  Site        : !URL_PUBLICA!  (leva alguns minutos para publicar^)
echo  Automacao   : https://github.com/!USUARIO!/%NOME_REPO%/actions
echo.
echo  Teste agora sem publicar de verdade:
echo    gh workflow run "Lotofacil Bot" -f simular=true
echo.
echo  Para trocar uma credencial depois:
echo    gh secret set IG_TOKEN
echo ==============================================================
echo.
pause
