@echo off
setlocal enabledelayedexpansion
echo ==========================================
echo   Compilando Hero Builder Studio EXE
echo ==========================================
echo.

:: 1. Limpeza previa
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: 2. Seleção de Ícone para o Studio
echo [INFO] Escolha o icone para o seu Gerador...
set "ICON_SOURCE=..\ICONE"
set "ICON_COUNT=0"
for %%f in ("%ICON_SOURCE%\*.ico") do (
    set /a ICON_COUNT+=1
    set "ICON_!ICON_COUNT!=%%~nxf"
    echo   [!ICON_COUNT!] %%~nxf
)

if %ICON_COUNT% EQU 0 (
    echo [AVISO] Nenhum icone encontrado. Usando padrao.
    set "BUILDER_ICON=assets\favicon.ico"
) else if %ICON_COUNT% EQU 1 (
    echo [INFO] Usando icone: %ICON_1%
    set "BUILDER_ICON=%ICON_SOURCE%\%ICON_1%"
) else (
    set /p ICON_CHOICE="Escolha o numero do icone para o GERADOR: "
    if defined ICON_!ICON_CHOICE! (
        set "SELECTED_ICON=!ICON_%ICON_CHOICE%!"
        set "BUILDER_ICON=%ICON_SOURCE%\!SELECTED_ICON!"
    ) else (
        set "BUILDER_ICON=assets\favicon.ico"
    )
)
echo.

:: 3. Gerando o Executavel do Gerador
echo [INFO] Iniciando PyInstaller para o Studio...
setlocal enabledelayedexpansion
pyinstaller --noconfirm builder_studio.spec

echo.
if exist "dist\BuilderStudio_HTML2EXE.exe" (
    echo [SUCESSO] Gerador convertido com exito!
    echo O arquivo esta em: dist\BuilderStudio_HTML2EXE.exe
) else (
    echo [ERRO] Falha ao gerar o executavel do Studio.
)

echo.
pause
