; Image Description Toolkit - Inno Setup Script
; Version dynamically read from VERSION file
; wxPython Version - Simplified installer that works directly from dist_all directory

#define MyAppName "Image Description Toolkit"
#define VersionFile FileOpen(SourcePath + "\\..\\..\\VERSION")
#define MyAppVersion Trim(FileRead(VersionFile))
#expr FileClose(VersionFile)
#define MyAppPublisher "Kelly Ford"
#define MyAppURL "https://github.com/kellylford/Image-Description-Toolkit"
#define MyAppExeName "idt.exe"
#define LicensePath SourcePath + "\\..\\..\\LICENSE"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Double braces are required in Inno Setup to escape the GUID braces
AppId={{8F7A3B2D-5E9C-4A1F-B3D6-7C8E9F0A1B2C}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={sd}\idt
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile={#LicensePath}
OutputDir=dist_all
OutputBaseFilename=ImageDescriptionToolkit_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
ChangesEnvironment=yes
; Preserve user data during updates
DirExistsWarning=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Code]
const
  EnvironmentKey = 'Environment';

var
  OllamaPage: TOutputMsgWizardPage;
  WingetAvailable: Boolean;

function IsWingetAvailable: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c winget --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
  if Result then
    Log('Winget availability check: True')
  else
    Log('Winget availability check: False');
end;

function ShouldShowOllamaInstallTask: Boolean;
begin
  Result := IsWingetAvailable();
end;

function ShouldShowOllamaWebsiteLink: Boolean;
begin
  Result := not IsWingetAvailable();
end;

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
var
  OllamaMessage: string;
begin
  // Check if winget is available on this system
  WingetAvailable := IsWingetAvailable();
  
  // Customize message based on winget availability
  if WingetAvailable then
  begin
    OllamaMessage := 'Image Description Toolkit requires Ollama to use local AI models.' + #13#10 + #13#10 +
      'You can install Ollama automatically using the checkbox on the next page,' + #13#10 +
      'or install it manually later:' + #13#10 +
      '1. Visit https://ollama.com' + #13#10 +
      '2. Download and install Ollama' + #13#10 +
      '3. Run: ollama pull moondream';
  end
  else
  begin
    OllamaMessage := 'Image Description Toolkit requires Ollama to use local AI models.' + #13#10 + #13#10 +
      'If you don''t have Ollama installed yet:' + #13#10 +
      '1. Visit https://ollama.com' + #13#10 +
      '2. Download and install Ollama' + #13#10 +
      '3. Run: ollama pull moondream' + #13#10 + #13#10 +
      'You can install Ollama now or after installing IDT.';
  end;
  
  OllamaPage := CreateOutputMsgPage(wpSelectTasks,
    'Ollama Required', 'AI Model Server Installation',
    OllamaMessage);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Set IDT_CONFIG_DIR environment variable to point to scripts directory
    RegWriteStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'IDT_CONFIG_DIR', ExpandConstant('{app}\scripts'));
    Log('Set IDT_CONFIG_DIR environment variable to: ' + ExpandConstant('{app}\scripts'));
    
    // Add to PATH if selected
    if WizardIsTaskSelected('addtopath') then
      EnvAddPath(ExpandConstant('{app}'));
    
    // Install Ollama via winget if selected
    if WizardIsTaskSelected('installollama') then
    begin
      Log('Installing Ollama via winget...');
      if Exec('cmd.exe', '/c winget install Ollama.Ollama --silent --accept-package-agreements --accept-source-agreements', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
      begin
        if ResultCode = 0 then
          Log('Ollama installed successfully')
        else
          Log('Ollama installation returned code: ' + IntToStr(ResultCode));
      end
      else
      begin
        Log('Failed to execute winget command');
        MsgBox('Failed to install Ollama automatically. Please install manually from ollama.com', mbError, MB_OK);
      end;
    end;
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

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "addtopath"; Description: "Add to PATH (allows running 'idt' from any command prompt)"; GroupDescription: "System Integration:"; Flags: unchecked
Name: "installollama"; Description: "Install Ollama (local AI models) via winget"; GroupDescription: "Dependencies:"; Flags: unchecked; Check: ShouldShowOllamaInstallTask

[Files]
; Main I DT CLI executable
Source: "dist_all\bin\idt.exe"; DestDir: "{app}"; Flags: ignoreversion

; GUI Applications
; Note: Viewer is now integrated into ImageDescriber as "Viewer Mode" tab
Source: "dist_all\bin\ImageDescriber.exe"; DestDir: "{app}"; Flags: ignoreversion
; Note: PromptEditor and Configure are now integrated into ImageDescriber (Tools menu)

; Configuration files (from scripts directory)
Source: "..\..\scripts\*.json"; DestDir: "{app}\scripts"; Flags: ignoreversion recursesubdirs
; Note: scripts\prompts folder is no longer present; omit to avoid build failure

; Shared utilities
Source: "..\..\shared\*.py"; DestDir: "{app}\shared"; Flags: ignoreversion

; Documentation
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Image Description Toolkit (CLI)"; Filename: "cmd.exe"; Parameters: "/k cd /d ""{app}"" && echo Image Description Toolkit && echo Type 'idt --help' for usage"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\ImageDescriber"; Filename: "{app}\ImageDescriber.exe"; WorkingDir: "{app}"; Comment: "Batch image processing (Viewer Mode tab + Tools menu includes Prompt Editor and Configure)"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Image Description Toolkit (CLI)"; Filename: "cmd.exe"; Parameters: "/k cd /d ""{app}"" && echo Image Description Toolkit v{#MyAppVersion} && echo. && echo Type 'idt --help' for usage && echo."; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autodesktop}\ImageDescriber"; Filename: "{app}\ImageDescriber.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "cmd.exe"; Parameters: "/k cd /d ""{app}"" && echo Image Description Toolkit v{#MyAppVersion} && echo. && echo Type 'idt --help' for usage && echo."; Description: "{cm:LaunchProgram,Image Description Toolkit (CLI)}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\ImageDescriber.exe"; Description: "{cm:LaunchProgram,ImageDescriber}"; Flags: nowait postinstall skipifsilent unchecked
Filename: "https://ollama.com"; Description: "Open Ollama website to download (if not installed)"; Flags: shellexec postinstall skipifsilent unchecked; Check: ShouldShowOllamaWebsiteLink
Filename: "{app}\docs"; Description: "View Documentation"; Flags: shellexec postinstall skipifsilent unchecked