#define MyAppName "AndreNotas"
#define MyAppVersion "1.0.2"
#define MyAppExeName "AndreNotas.exe"
[Setup]
AppId={{9B2D89CB-C86F-4D7D-A5C6-6A2CDA4D9C50}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=André Henrique G. Lécio
AppPublisherURL=https://andrelecio.net.br
DefaultDirName={localappdata}\Programs\AndreNotas
DefaultGroupName=AndreNotas
OutputDir=instalador
OutputBaseFilename=AndreNotas_Setup_v1.0.2
SetupIconFile=andrenote.ico
UninstallDisplayIcon={app}\AndreNotas.exe
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
ChangesAssociations=yes
ArchitecturesAllowed=x64compatible
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked
Name: "txtassoc"; Description: "Registrar AndreNotas como aplicativo para arquivos TXT (a escolha padrao pode exigir confirmacao do Windows)"; GroupDescription: "Arquivos de texto:"; Flags: checkedonce
[Files]
Source: "dist\AndreNotas.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "andrenote.ico"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\AndreNotas"; Filename: "{app}\AndreNotas.exe"
Name: "{autodesktop}\AndreNotas"; Filename: "{app}\AndreNotas.exe"; Tasks: desktopicon
[Registry]
; Registra formato TXT e icone AndreNotas via ProgID (sem substituir silenciosamente o padrao do usuario).
Root: HKCU; Subkey: "Software\Classes\AndreNotas.Txt"; ValueType: string; ValueName: ""; ValueData: "Documento de texto AndreNotas"; Flags: uninsdeletekey; Tasks: txtassoc
Root: HKCU; Subkey: "Software\Classes\AndreNotas.Txt\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\andrenote.ico,0"; Tasks: txtassoc
Root: HKCU; Subkey: "Software\Classes\AndreNotas.Txt\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\AndreNotas.exe"" ""%1"""; Tasks: txtassoc
Root: HKCU; Subkey: "Software\Classes\.txt\OpenWithProgids"; ValueType: none; ValueName: "AndreNotas.Txt"; Flags: uninsdeletevalue; Tasks: txtassoc
Root: HKCU; Subkey: "Software\Classes\Applications\AndreNotas.exe\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\AndreNotas.exe"" ""%1"""; Flags: uninsdeletekey; Tasks: txtassoc
Root: HKCU; Subkey: "Software\Classes\Applications\AndreNotas.exe\SupportedTypes"; ValueType: string; ValueName: ".txt"; ValueData: ""; Tasks: txtassoc
[Run]
Filename: "{app}\AndreNotas.exe"; Description: "Executar AndreNotas"; Flags: nowait postinstall skipifsilent
