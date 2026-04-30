; =====================================================
; Hero JUVICKS XML Pallet - Inno Setup Script
; Juvicks Studio - v1.0
; Compile com: Inno Setup Compiler
; =====================================================

; Se nao for passado via linha de comando, usa o padrao
#ifndef MyAppName
  #define MyAppName      "Hero JUVICKS"
#endif
#ifndef MyAppExeName
  #define MyAppExeName   "HeroJUVICKS.exe"
#endif
#ifndef MyAppDataName
  #define MyAppDataName  "HeroJUVICKS"
#endif
#ifndef MyAppFolder
  #define MyAppFolder    "HeroJUVICKS"
#endif

#define MyAppVersion   "1.0"
#define MyAppPublisher "Juvicks Studio"

#ifndef MyAppId
  #define MyAppId "{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}"
#endif

; Caminho onde os arquivos compilados estao (sera passado pelo Builder)
#ifndef SourcePath
  #define SourcePath "dist"
#endif

; Caminho para recursos (icones, imagens)
#ifndef ResourcePath
  #define ResourcePath "assets"
#endif

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

; Instalacao em Arquivos de Programas (requer admin)
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin

; Saida do instalador final
OutputDir=dist_installer
OutputBaseFilename={#MyAppName}_Setup

; Icone do instalador (da janela de setup)
SetupIconFile={#ResourcePath}\favicon.ico

; Compressao maxima
Compression=lzma2/ultra64
SolidCompression=yes
CompressionThreads=auto

; Visual moderno
WizardStyle=modern
WizardSizePercent=120
ShowLanguageDialog=no

; Windows 10+ obrigatorio
MinVersion=10.0

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon";  Description: "Criar atalho na Area de Trabalho";    GroupDescription: "Atalhos:";               Flags: unchecked
Name: "startup";      Description: "Iniciar com o Windows (na bandeja)";  GroupDescription: "Inicializacao:";        Flags: unchecked

[Files]
; Instalamos a pasta completa com todas as dependencias
Source: "{#SourcePath}\{#MyAppFolder}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Menu Iniciar
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; Area de Trabalho (opcional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Iniciar com Windows - abre minimizado (vai direto para bandeja)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Registry]
; Registra o programa no Adicionar/Remover Programas
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1"; \
  ValueType: string; ValueName: "DisplayIcon"; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1"; \
  ValueType: string; ValueName: "Publisher"; ValueData: "{#MyAppPublisher}"; Flags: uninsdeletevalue

[Run]
; Oferecer para iniciar apos instalar
Filename: "{app}\{#MyAppExeName}"; \
  Description: "Iniciar {#MyAppName} agora"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Mata todos os processos do programa antes de desinstalar
Filename: "taskkill"; Parameters: "/F /IM {#MyAppExeName} /T"; \
  Flags: runhidden waituntilterminated; RunOnceId: "KillApp"

[Code]
var
  RemoveData: Boolean;

// Mata o processo se estiver rodando antes de instalar/atualizar
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Exec('taskkill', '/F /IM {#MyAppExeName} /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := True;
end;

// Pergunta ao usuario sobre os dados ao desinstalar
function InitializeUninstall(): Boolean;
var
  Response: Integer;
  ResultCode: Integer;
begin
  // Mata o processo antes de desinstalar
  Exec('taskkill', '/F /IM {#MyAppExeName} /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  Response := MsgBox(
    'Deseja remover as predefinicoes salvas?' + #13#10 +
    '(Pasta: %APPDATA%\{#MyAppDataName})' + #13#10#13#10 +
    'Clique em Sim para apagar tudo, ou Nao para manter os dados.',
    mbConfirmation,
    MB_YESNO
  );

  RemoveData := (Response = IDYES);
  Result := True;
end;

// Executa a limpeza se o usuario autorizou
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if (CurUninstallStep = usPostUninstall) and RemoveData then
  begin
    DelTree(ExpandConstant('{userappdata}\{#MyAppDataName}'), True, True, True);
  end;
end;
