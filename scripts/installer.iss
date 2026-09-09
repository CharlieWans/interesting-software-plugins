;============================================================
; 吃豆人删除 — Inno Setup 安装脚本
; 作用: 把 build.bat 打出的 dist\吃豆人删除 制作成安装程序
;
; 使用前提:
;   1) 已用 scripts\build.bat 完成打包 (生成 dist\吃豆人删除)
;   2) 已安装 Inno Setup 6 或以上 (https://jrsoftware.org/isinfo.php)
; 使用:
;   右键本文件 → Compile (或 ISCC installer.iss)
;   输出: scripts\Output\吃豆人删除安装程序.exe
;============================================================

#define MyAppName "吃豆人删除"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "CharlieWans"
#define MyAppExeName "PacManDelete.exe"
#define MyAppAssocName "PacManDelete"

[Setup]
AppId={{7F2E8C1A-4B6D-4C9E-9A5F-D3E8B0A1C2D4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=吃豆人删除安装程序
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\吃豆人删除\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs
Source: "..\assets\icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即体验 {#MyAppName}"; Flags: nowait postinstall skipifsilent

;------------------------------------------------------------
; 安装时写入右键菜单 (文件/文件夹)
; 卸载时移除右键菜单
;------------------------------------------------------------
[Registry]
Root: HKCU; Subkey: "Software\Classes\*\shell\PacManDelete"; ValueType: string; ValueName: ""; ValueData: "吃豆人删除"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\*\shell\PacManDelete"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\assets\icon.ico"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\*\shell\PacManDelete\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey

Root: HKCU; Subkey: "Software\Classes\Directory\shell\PacManDelete"; ValueType: string; ValueName: ""; ValueData: "吃豆人删除"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Directory\shell\PacManDelete"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\assets\icon.ico"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Directory\shell\PacManDelete\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey
