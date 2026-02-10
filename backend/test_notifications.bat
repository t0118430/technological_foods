@echo off
REM Script para testar notificações com dados reais
REM Verifica se você receberá alertas em todos os cenários

echo ========================================
echo 📱 TESTE DE NOTIFICACOES - DADOS REAIS
echo ========================================
echo.

cd /d "%~dp0"

REM Verificar se .env existe
if not exist ".env" (
    echo ❌ ERRO: Arquivo .env nao encontrado!
    echo.
    echo Copie o .env.example:
    echo   copy .env.example .env
    echo.
    echo E configure o NTFY_TOPIC para receber notificacoes reais.
    pause
    exit /b 1
)

REM Carregar variáveis do .env (simplificado)
for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
    if "%%a"=="NTFY_TOPIC" set NTFY_TOPIC=%%b
)

echo 🔍 Verificando configuracao...
echo.

if "%NTFY_TOPIC%"=="" (
    echo ⚠️ NTFY_TOPIC nao configurado
    echo.
    echo MODO DE TESTE: Apenas validacao de logica
    echo   - Regras serao avaliadas
    echo   - Alertas serao processados
    echo   - Notificacoes NAO serao enviadas
    echo.
    echo Para receber notificacoes REAIS:
    echo   1. Edite .env
    echo   2. Configure: NTFY_TOPIC=agritech-test
    echo   3. Execute novamente
    echo.
) else (
    echo ✅ NTFY_TOPIC configurado: %NTFY_TOPIC%
    echo.
    echo 📱 MODO COMPLETO: Notificacoes REAIS serao enviadas!
    echo.
    echo IMPORTANTE:
    echo   1. Instale o app ntfy no celular
    echo   2. Inscreva-se no topico: %NTFY_TOPIC%
    echo   3. Aguarde notificacoes durante o teste
    echo.
    pause
)

echo.
echo ========================================
echo 🧪 INICIANDO TESTES
echo ========================================
echo.

REM Executar testes
cd api
python -m pytest test_integration_notifications.py -v -s --tb=short

echo.
echo ========================================
echo 📊 RESULTADO DOS TESTES
echo ========================================
echo.

if %errorlevel% equ 0 (
    echo ✅ SUCESSO: Todos os testes passaram!
    echo.
    echo Verificado:
    echo   ✅ Regras detectam problemas nos sensores
    echo   ✅ Alertas sao gerados corretamente
    echo   ✅ Escalacao funciona apos tempo de espera
    echo   ✅ Cooldown previne spam
    echo   ✅ Tiers respeitam limites de features
    if not "%NTFY_TOPIC%"=="" (
        echo   ✅ Notificacoes enviadas via ntfy
        echo.
        echo 📱 VERIFIQUE SEU CELULAR!
        echo    Voce deve ter recebido notificacoes de teste.
    )
) else (
    echo ❌ FALHA: Alguns testes falharam
    echo.
    echo Verifique os erros acima e:
    echo   1. Confirme que backend/api/*.py existem
    echo   2. Verifique configuracao do .env
    echo   3. Execute: pip install -r requirements.txt
)

echo.
pause
