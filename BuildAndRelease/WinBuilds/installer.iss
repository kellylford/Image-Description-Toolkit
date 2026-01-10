; Image Description Toolkit - Inno Setup Script
; Version dynamically read from VERSION file
; wxPython Version - Simplified installer that works directly from dist_all directory

#define MyAppName "Image Description Toolkit"
#define VersionFile FileOpen(SourcePath + "\..\VERSION")
#define MyAppVersion Trim(FileRead(VersionFile))
#expr FileClose(VersionFile)
#define MyAppPublisher "Kelly Ford"
#define MyAppURL "https://github.com/kellylford/Image-Description-Toolkit"
#define MyAppExeName "idt.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{8F7A3B2D-5E9C-4A1F-B3D6-7C8E9F0A1B2C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={sd}\idt
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\..\..\LICENSE
OutputDir=..\releases
OutputBaseFilename=ImageDescriptionToolkit_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
SetupIconFile=
ChangesEnvironment=yes
; Preserve user data during updates
DirExistsWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "addtopath"; Description: "Add to PATH (allows running 'idt' from any command prompt)"; GroupDescription: "System Integration:"; Flags: unchecked

[Files]
; Main IDT CLI executable
Source: "dist_all\bin\idt.exe"; DestDir: "{app}"; Flags: ignoreversion

; GUI Applications
Source: "dist_all\bin\Viewer.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist_all\bin\ImageDescriber.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist_all\bin\prompteditor.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist_all\bin\idtconfigure.exe"; DestDir: "{app}"; Flags: ignoreversion

; Configuration files (from scripts directory)
Source: "..\..\..\scripts\*.json"; DestDir: "{app}\scripts"; Flags: ignoreversion recursesubdirs
Source: "..\..\..\scripts\prompts\*"; DestDir: "{app}\scripts\prompts"; Flags: ignoreversion recursesubdirs

; Shared utilities
Source: "..\..\..\shared\*.py"; DestDir: "{app}\shared"; Flags: ignoreversion

; Documentation
Source: "..\..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Image Description Toolkit (CLI)"; Filename: "cmd.exe"; Parameters: "/k cd /d ""{app}"" && echo Image Description Toolkit && echo Type 'idt --help' for usage"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Viewer"; Filename: "{app}\Viewer.exe"; WorkingDir: "{app}"
Name: "{group}\ImageDescriber"; Filename: "{app}\ImageDescriber.exe"; WorkingDir: "{app}"
Name: "{group}\Prompt Editor"; Filename: "{app}\prompteditor.exe"; WorkingDir: "{app}"
Name: "{group}\Configure"; Filename: "{app}\idtconfigure.exe"; WorkingDir: "{app}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Image Description Toolkit (CLI)"; Filename: "cmd.exe"; Parameters: "/k cd /d ""{app}"" && echo Image Description Toolkit v{#MyAppVersion} && echo. && echo Type 'idt --help' for usage && echo."; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autodesktop}\ImageDescriber"; Filename: "{app}\ImageDescriber.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Code]
const
  EnvironmentKey = 'Environment';

var
  OllamaPage: TOutputMsgWizardPage;

procedure EnvAddPath(Path: string);
var
  Paths: string;
begin
  { Retrieve current path (use empty string if entry not exists) }
  if not RegQueryStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', Paths) then
    Paths := '';

  { Skip if already in path }
  if Pos(';' + Uppercase(Path) + ';', ';' + Uppercase(Paths) + ';') > 0 then exit;

  { Add to path }
  if Paths = '' then
    Paths := Path
  else
    Paths := Paths + ';' + Path;

  { Overwrite (or create if missing) path environment variable }
  if RegWriteStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', Paths)
  then begin
    Log(Format('The [%s] added to PATH: [%s]', [Path, Paths]));
  end
  else begin
    Log(Format('Error while adding the [%s] to PATH: [%s]', [Path, Paths]));
  end;
end;

procedure InitializeWizard;
begin
  OllamaPage := CreateOutputMsgPage(wpSelectTasks,
    'Ollama Required', 'AI Model Server Installation',
    'Image Description Toolkit requires Ollama to use local AI models.' + #13#10 + #13#10 +
    'If you don''t have Ollama installed yet:' + #13#10 +
    '1. Visit https://ollama.com' + #13#10 +
    '2. Download and install Ollama' + #13#10 +
    '3. Run: ollama pull moondream' + #13#10 + #13#10 +
    'You can install Ollama now or after installing IDT.');
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Set IDT_CONFIG_DIR environment variable to point to scripts directory
    RegWriteStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'IDT_CONFIG_DIR', ExpandConstant('{app}\scripts'));
    Log('Set IDT_CONFIG_DIR environment variable to: ' + ExpandConstant('{app}\scripts'));
    
    // Add to PATH if selected
    if WizardIsTaskSelected('addtopath') then
      EnvAddPath(ExpandConstant('{app}'));
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Path: string;
  AppDir: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Remove IDT_CONFIG_DIR environment variable
    RegDeleteValue(HKEY_CURRENT_USER, 'Environment', 'IDT_CONFIG_DIR');
    
    // Remove from PATH if it was added
    AppDir := ExpandConstant('{app}');
    if RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path) then
    begin
      if Pos(AppDir, Path) > 0 then
      begin
        StringChangeEx(Path, ';' + AppDir, '', True);
        StringChangeEx(Path, AppDir + ';', '', True);
        StringChangeEx(Path, AppDir, '', True);
        RegWriteStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', Path);
      end;
    end;
    
    // NOTE: User data (workflows, descriptions) is NOT deleted
    // Users must manually remove C:\idt if they want to clean everything
  end;
end;

[Run]
Filename: "cmd.exe"; Parameters: "/k cd /d ""{app}"" && echo Image Description Toolkit v{#MyAppVersion} && echo. && echo Type 'idt --help' for usage && echo."; Description: "{cm:LaunchProgram,Image Description Toolkit (CLI)}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\ImageDescriber.exe"; Description: "{cm:LaunchProgram,ImageDescriber}"; Flags: nowait postinstall skipifsilent unchecked
Filename: "https://ollama.com"; Description: "Open Ollama website to download (if not installed)"; Flags: shellexec postinstall skipifsilent unchecked
Filename: "{app}\docs"; Description: "View Documentation"; Flags: shellexec postinstall skipifsilent unchecked
