@echo off
setlocal enabledelayedexpansion
echo ==========================================
echo   Hero JUVICKS - Build System v1.4
echo ==========================================
echo.

:: 0. Nome Personalizado
set /p APP_NAME="Digite o nome do sistema de saida (ou Enter para padrao): "
if "%APP_NAME%"=="" set APP_NAME=HeroJUVICKS
echo.

:: 0.1 Seleção Inteligente de Ícone
echo [INFO] Verificando pasta de ícones...
set "ICON_SOURCE=..\ICONE"
set "ICON_COUNT=0"
for %%f in ("%ICON_SOURCE%\*.ico") do (
    set /a ICON_COUNT+=1
    set "ICON_!ICON_COUNT!=%%~nxf"
    echo   [!ICON_COUNT!] %%~nxf
)

if %ICON_COUNT% EQU 0 (
    echo [AVISO] Nenhum icone .ico encontrado em %ICON_SOURCE%. Usando padrao da pasta assets.
) else if %ICON_COUNT% EQU 1 (
    echo [INFO] Usando unico icone encontrado: %ICON_1%
    copy /y "%ICON_SOURCE%\%ICON_1%" "assets\favicon.ico" >nul
) else (
    set /p ICON_CHOICE="Escolha o numero do icone desejado: "
    if defined ICON_!ICON_CHOICE! (
        set "SELECTED_ICON=!ICON_%ICON_CHOICE%!"
        echo [INFO] Selecionado: !SELECTED_ICON!
        copy /y "%ICON_SOURCE%\!SELECTED_ICON!" "assets\favicon.ico" >nul
    ) else (
        echo [AVISO] Escolha invalida. Usando icone atual da pasta assets.
    )
)

echo.
echo [INFO] Nome definido como: %APP_NAME%
echo.

:: 1. Fecha processos antigos
echo [1/5] Fechando processos antigos...
taskkill /F /IM %APP_NAME%.exe /T 2>nul
taskkill /F /IM HeroJUVICKS.exe /T 2>nul

:: 2. Limpeza
echo [2/5] Limpando pastas...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist dist_installer rmdir /s /q dist_installer

:: 3. Dependencias
echo [3/5] Verificando bibliotecas...
pip install PyQt5 PyQtWebEngine pystray Pillow psutil --quiet

:: 4. Compilacao do EXE
echo [4/5] Gerando executavel...
pyinstaller --noconfirm HeroJUVICKS.spec

:: 5. Geracao do Instalador (Inno Setup)
echo [5/5] Gerando instalador final...

:: Tenta encontrar o ISCC em varios caminhos comuns
set "ISCC="

:: Tenta pelo comando WHERE (se estiver no PATH)
for /f "delims=" %%i in ('where iscc.exe 2^>nul') do set "ISCC=%%i"

:: Se nao achou, tenta caminhos padrao
if "!ISCC!"=="" (
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
    if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
    if exist "C:\Program Files\Inno Setup 5\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 5\ISCC.exe"
)

if not "!ISCC!"=="" (
    echo Usando compilador: "!ISCC!"
    "!ISCC!" /dMyAppName="%APP_NAME%" /dMyAppExeName="%APP_NAME%.exe" /dMyAppDataName="%APP_NAME%" /dMyAppFolder="%APP_NAME%" /dMyAppId="{{HeroJUVICKS-%APP_NAME%}" "installer.iss"
    if exist "dist_installer" (
        echo.
        echo [SUCESSO] Instalador criado com exito!
    ) else (
        echo [ERRO] O Inno Setup rodou, mas nao criou a pasta dist_installer.
    )
) else (
    echo.
    echo [ERRO] Inno Setup NAO ENCONTRADO! 
    echo Por favor, instale o Inno Setup 6 ou adicione-o ao PATH do Windows.
    echo Baixe em: https://jrsoftware.org/isdl.php
)

echo.
pause
