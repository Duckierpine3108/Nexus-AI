; -- NEXUS AI v2.0 Enterprise Installer Script for Inno Setup --
; Architected for Windows 10/11 x64 Workstations

#define MyAppName "NEXUS AI"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "NEXUS Core"
#define MyAppExeName "nexus.exe"
#define SourceDistDir "dist\nexus"
#define AppIconFile "config\nexus.ico"

[Setup]
; Unique System GUID for Nexus AI Core
AppId={{8F5B7B12-9A4E-4C21-B21D-7C5D489A1234}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\config\nexus.ico

; Target 64-bit Windows OS exclusively
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Output Directory & Executable Naming
OutputDir=Output
OutputBaseFilename=nexus_ai_setup_v2.0
Compression=lzma2/ultra64
SolidCompression=yes

; Look & Feel
WizardStyle=modern
SetupIconFile={#AppIconFile}
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Active Instance Watchdog: Prevents corrupted DLL overwrites while running
AppMutex=NexusAI_Workstation_Core_Mutex
CloseApplications=force
RestartApplications=no

; Navigation Settings
DisableDirPage=no
DisableProgramGroupPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "Create a Quick Launch shortcut"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 1. PERSISTENT USER DATA: Never overwrite or delete user memory, PRs, or certificates during updates
Source: "{#SourceDistDir}\memory\long_term.json"; DestDir: "{app}\memory"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#SourceDistDir}\config\devices_telemetry.json"; DestDir: "{app}\config"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#SourceDistDir}\config\certs\*"; DestDir: "{app}\config\certs"; Flags: onlyifdoesntexist uninsneveruninstall recursesubdirs createallsubdirs

; 2. CORE SYSTEM BINARIES & ASSETS: Safe to update with ignoreversion
Source: "{#SourceDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*\__pycache__\*,*.pyc,*.lock,*.tmp,memory\long_term.json,config\devices_telemetry.json,config\certs\*"

[Dirs]
; CRITICAL PERMISSIONS: Grant full write/modify rights so Self-Evolution & telemetry can write without UAC blocks
Name: "{app}"; Permissions: users-full
Name: "{app}\actions"; Permissions: users-full
Name: "{app}\memory"; Permissions: users-full
Name: "{app}\config"; Permissions: users-full
Name: "{app}\plugins"; Permissions: users-full
Name: "{app}\dashboard"; Permissions: users-full
Name: "{app}\dashboard\static"; Permissions: users-full

[Icons]
; Start Menu Shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\config\nexus.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop Shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\config\nexus.ico"; Tasks: desktopicon

[Run]
; Launch Nexus AI Core immediately after setup finishes
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up dynamically generated runtime logs, locks, and pycache on uninstall
Type: files; Name: "{app}\config\splash_session.lock"
Type: files; Name: "{app}\config\last_splash.json"
Type: files; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\*\__pycache__"