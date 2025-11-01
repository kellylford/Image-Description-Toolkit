; Image Description Toolkit - Inno Setup Script
; Version dynamically read from VERSION file

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
LicenseFile=..\LICENSE
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
; Main toolkit files (from ImageDescriptionToolkit zip)
Source: "..\releases\ImageDescriptionToolkit_v{#MyAppVersion}.zip"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

; Viewer
Source: "..\releases\viewer_v{#MyAppVersion}.zip"; DestDir: "{tmp}"; Flags: deleteafterinstall

; ImageDescriber
Source: "..\releases\imagedescriber_v{#MyAppVersion}.zip"; DestDir: "{tmp}"; Flags: deleteafterinstall

; Prompt Editor
Source: "..\releases\prompt_editor_v{#MyAppVersion}.zip"; DestDir: "{tmp}"; Flags: deleteafterinstall

; IDTConfigure
Source: "..\releases\idtconfigure_v{#MyAppVersion}.zip"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\Image Description Toolkit (CLI)"; Filename: "cmd.exe"; Parameters: "/k cd /d ""{app}"" && echo Image Description Toolkit v{#MyAppVersion} && echo. && echo Type 'idt --help' for usage && echo."; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\ImageDescriber"; Filename: "{app}\ImageDescriber\imagedescriber.exe"; WorkingDir: "{app}\ImageDescriber"
Name: "{group}\Viewer"; Filename: "{app}\Viewer\viewer.exe"; WorkingDir: "{app}\Viewer"
Name: "{group}\Prompt Editor"; Filename: "{app}\PromptEditor\prompteditor.exe"; WorkingDir: "{app}\PromptEditor"
Name: "{group}\Configure"; Filename: "{app}\IDTConfigure\idtconfigure.exe"; WorkingDir: "{app}\IDTConfigure"
Name: "{group}\Documentation"; Filename: "{app}\docs"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Image Description Toolkit (CLI)"; Filename: "cmd.exe"; Parameters: "/k cd /d ""{app}"" && echo Image Description Toolkit v{#MyAppVersion} && echo. && echo Type 'idt --help' for usage && echo."; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autodesktop}\ImageDescriber"; Filename: "{app}\ImageDescriber\imagedescriber.exe"; WorkingDir: "{app}\ImageDescriber"; Tasks: desktopicon

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
    '3. Run: ollama pull llava' + #13#10 + #13#10 +
    'You can also use cloud-based AI providers (OpenAI, Claude) by setting API keys.');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Extract main toolkit
    Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path ''' + ExpandConstant('{tmp}\ImageDescriptionToolkit_v{#MyAppVersion}.zip') + ''' -DestinationPath ''' + ExpandConstant('{app}') + ''' -Force"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    
    // Extract Viewer
    Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path ''' + ExpandConstant('{tmp}\viewer_v{#MyAppVersion}.zip') + ''' -DestinationPath ''' + ExpandConstant('{app}\Viewer') + ''' -Force"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    
    // Extract ImageDescriber
    Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path ''' + ExpandConstant('{tmp}\imagedescriber_v{#MyAppVersion}.zip') + ''' -DestinationPath ''' + ExpandConstant('{app}\ImageDescriber') + ''' -Force"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    
    // Extract Prompt Editor
    Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path ''' + ExpandConstant('{tmp}\prompt_editor_v{#MyAppVersion}.zip') + ''' -DestinationPath ''' + ExpandConstant('{app}\PromptEditor') + ''' -Force"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    
    // Extract IDTConfigure
    Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path ''' + ExpandConstant('{tmp}\idtconfigure_v{#MyAppVersion}.zip') + ''' -DestinationPath ''' + ExpandConstant('{app}\IDTConfigure') + ''' -Force"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    
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
Filename: "{app}\ImageDescriber\imagedescriber.exe"; Description: "{cm:LaunchProgram,ImageDescriber}"; Flags: nowait postinstall skipifsilent unchecked
Filename: "https://ollama.com"; Description: "Open Ollama website to download (if not installed)"; Flags: shellexec postinstall skipifsilent unchecked
Filename: "{app}\docs"; Description: "View Documentation"; Flags: shellexec postinstall skipifsilent unchecked
