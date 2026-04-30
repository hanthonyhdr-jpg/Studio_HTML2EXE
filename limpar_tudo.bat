@echo off
echo ==========================================
echo   Limpando Ambiente de Desenvolvimento
echo ==========================================
echo.

echo [1/3] Removendo pastas de build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist dist_installer rmdir /s /q dist_installer

echo [2/3] Limpando cache do Python...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"

echo [3/3] Removendo arquivos temporarios...
if exist *.pyc del /q *.pyc
if exist *.spec.bak del /q *.spec.bak

echo.
echo Ambientes limpo com sucesso!
echo.
pause
