; -- NEXUS AI Installer Script for Inno Setup --

#define MyAppName "NEXUS AI"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "NEXUS Core"
#define MyAppExeName "nexus.exe"
#define SourceDistDir "C:\Old PC Data\NEXUS Setup\dist\nexus"
#define AppIconFile "C:\Old PC Data\NEXUS Setup\config\nexus.ico"

[Setup]
; Basic Application Info
AppId={{8F5B7B12-9A4E-4C21-B21D-7C5D489A1234}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}

; Output configuration
OutputDir=C:\Old PC Data\NEXUS Setup\Output
OutputBaseFilename=nexus_ai_setup
Compression=lzma2/ultra64
SolidCompression=yes

; Look & Feel
WizardStyle=modern
SetupIconFile={#AppIconFile}
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Prevents pathing bugs
DisableDirPage=no
DisableProgramGroupPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a Quick Launch shortcut"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy the ENTIRE folder structure exactly as-is
Source: "{#SourceDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; CRITICAL: Grant full write permissions to users so memory/config files can be updated dynamically
Name: "{app}"; Permissions: users-full
Name: "{app}\memory"; Permissions: users-full
Name: "{app}\config"; Permissions: users-full

[Icons]
; Start Menu Shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\config\nexus.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop Shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\config\nexus.ico"; Tasks: desktopicon

[Run]
; Option to launch Nexus AI right after installation finishes
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent