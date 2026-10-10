; Image Description Toolkit - Inno Setup Script
; Version dynamically read from VERSION file
; wxPython Version - Simplified installer that works directly from dist_all directory

#define MyAppName "Image Description Toolkit"
#define VersionFile FileOpen(SourcePath + "\\..\\..\\VERSION")
#define MyAppVersion Trim(FileRead(VersionFile))
#expr FileClose(VersionFile)
#define MyFileVersion StringChange(MyAppVersion, " ", "_")
#define MyAppPublisher "Kelly Ford"
#define MyAppURL "https://github.com/TheIdeaPlace/Image-Description-Toolkit"
#define MyAppExeName "idt.exe"
#define LicensePath SourcePath + "\\..\\..\\LICENSE"
; Windows AI's helper packages, built and signed by the Windows build workflow
; (windows_ai_helper\build_helper.ps1 -Pack). A local build without them makes an
; installer without Windows AI, rather than failing.
#define WindowsAIDir SourcePath + "\\..\\..\\windows_ai_helper\\dist"
#if FileExists(WindowsAIDir + "\\IdtWindowsAI_x64.msix") && FileExists(WindowsAIDir + "\\IdtWindowsAI_arm64.msix")
  #define WithWindowsAI
#endif

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
OutputBaseFilename=ImageDescriptionToolkitSetup_{#MyFileVersion}
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
; In-app updates (Help > Check for Updates) run this installer over a live
; install. ImageDescriber closes itself first, but an idt.exe console may still
; be open, so let Setup close what is holding the executables rather than
; failing on a locked file. No auto-restart: the user relaunches when ready.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Code]
const
  EnvironmentKey = 'Environment';

var
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

{ Windows AI: Windows' own on-device image description, on a Copilot+ PC with Windows 11
  24H2 or later. Offered where Windows is new enough; whether this PC is a Copilot+ PC is
  for IDT to say when it is used, since only Windows' own API can tell. }
function CanSetUpWindowsAI: Boolean;
#ifdef WithWindowsAI
var
  Version: TWindowsVersion;
begin
  GetWindowsVersionEx(Version);
  Result := Version.Build >= 26100;
#else
begin
  Result := False;
#endif
end;

{ By full path: a bare name is looked for in the current folder first. }
function PowerShellExe: String;
begin
  Result := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
end;

function WindowsAIArch: String;
begin
  if IsArm64 then
    Result := 'arm64'
  else
    Result := 'x64';
end;

{ Packages are installed per user, so this runs as the person who started Setup, not as
  the administrator it elevated to. The script does nothing on a PC without an NPU, and adds
  the Windows App Runtime first if the PC doesn't have it. Failing here never fails Setup:
  IDT works without Windows AI. }
procedure SetUpWindowsAI;
var
  ResultCode: Integer;
  Dir, Params, LogFile, Caption: String;
  Done: Boolean;
begin
  Dir := ExpandConstant('{app}\windows_ai');
  LogFile := ExpandConstant('{%TEMP}\idt_windows_ai_setup.log');
  Params := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + Dir + '\install_windows_ai.ps1"' +
            ' -Package "' + Dir + '\IdtWindowsAI_' + WindowsAIArch + '.msix" -Arch ' + WindowsAIArch +
            ' -Log "' + LogFile + '"';
  Caption := WizardForm.StatusLabel.Caption;
  WizardForm.StatusLabel.Caption := 'Setting up Windows AI. This can take a few minutes.';
  Log('Setting up Windows AI: ' + PowerShellExe + ' ' + Params);
  try
    Done := ExecAsOriginalUser(PowerShellExe, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
  except
    Done := False;
    Log('Windows AI setup could not start: ' + GetExceptionMessage);
  end;
  WizardForm.StatusLabel.Caption := Caption;
  if Done then
    Log('Windows AI set up')
  else
  begin
    Log('Windows AI setup failed, code ' + IntToStr(ResultCode));
    if not WizardSilent then
      MsgBox('Windows AI couldn''t be set up. The rest of IDT works without it.' + #13#10#13#10 +
             'What happened is in ' + LogFile, mbInformation, MB_OK);
  end;
end;

procedure InitializeWizard;
begin
  // Check if winget is available on this system
  WingetAvailable := IsWingetAvailable();
  
  // Note: Ollama information page removed - checkbox description is sufficient
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

    if WizardIsTaskSelected('windowsai') then
      SetUpWindowsAI;
    
    // Install Ollama via winget if selected
    if WizardIsTaskSelected('installollama') then
    begin
      Log('Installing Ollama via winget...');
      if Exec('cmd.exe', '/c winget install Ollama.Ollama --silent --accept-package-agreements --accept-source-agreements', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
      begin
        if ResultCode = 0 then
        begin
          Log('Ollama installed successfully');
          
          // Pull default model after successful Ollama installation.
          // DEFAULT MODEL: to change this, update scripts/image_describer_config.json "default_model"
          // and change the two references to "minicpm-v4.6" below to match.
          Log('Pulling minicpm-v4.6 model...');
          if Exec('cmd.exe', '/c ollama pull minicpm-v4.6', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
          begin
            if ResultCode = 0 then
              Log('minicpm-v4.6 model pulled successfully')
            else
              Log('minicpm-v4.6 model pull returned code: ' + IntToStr(ResultCode));
          end
          else
          begin
            Log('Failed to execute ollama pull command');
            MsgBox('Ollama installed but failed to pull minicpm-v4.6 model. You can pull it manually by running: ollama pull minicpm-v4.6', mbInformation, MB_OK);
          end;
        end
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
  ResultCode: Integer;
begin
  // Before the files go: the script that removes the helper package is one of them. It
  // removes it for every user, as whoever installed it may not be the administrator now.
  if (CurUninstallStep = usUninstall) and
     FileExists(ExpandConstant('{app}\windows_ai\install_windows_ai.ps1')) then
  begin
    Exec(PowerShellExe, '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' +
         ExpandConstant('{app}\windows_ai\install_windows_ai.ps1') + '" -Remove',
         '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Log('Removing the Windows AI helper returned ' + IntToStr(ResultCode));
  end;

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
Name: "installollama"; Description: "Install Ollama and minicpm-v4.6 model via winget"; GroupDescription: "Dependencies:"; Flags: unchecked; Check: ShouldShowOllamaInstallTask
Name: "windowsai"; Description: "Set up Windows AI, for descriptions on this PC if it is a Copilot+ PC"; GroupDescription: "Dependencies:"; Check: CanSetUpWindowsAI

[Files]
; Main I DT CLI executable
Source: "dist_all\bin\idt.exe"; DestDir: "{app}"; Flags: ignoreversion

; GUI Applications
; Note: Viewer is now integrated into ImageDescriber as "Viewer Mode" tab
Source: "dist_all\bin\ImageDescriber.exe"; DestDir: "{app}"; Flags: ignoreversion
; Note: PromptEditor and Configure are now integrated into ImageDescriber (Tools menu)
; Standalone accessible chat client. Ships in the same installer so one update
; covers every app, per the update checker's single-feed design.
Source: "dist_all\bin\IDTChat.exe"; DestDir: "{app}"; Flags: ignoreversion

#ifdef WithWindowsAI
; Windows AI's helper, for this PC's architecture only, and the script that installs it.
Source: "..\..\windows_ai_helper\dist\IdtWindowsAI_x64.msix"; DestDir: "{app}\windows_ai"; Flags: ignoreversion; Check: not IsArm64
Source: "..\..\windows_ai_helper\dist\IdtWindowsAI_arm64.msix"; DestDir: "{app}\windows_ai"; Flags: ignoreversion; Check: IsArm64
Source: "..\..\windows_ai_helper\install_windows_ai.ps1"; DestDir: "{app}\windows_ai"; Flags: ignoreversion
#endif

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
Name: "{group}\IDT Chat"; Filename: "{app}\IDTChat.exe"; WorkingDir: "{app}"; Comment: "Accessible chat client for Ollama, Claude and OpenAI"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Image Description Toolkit (CLI)"; Filename: "cmd.exe"; Parameters: "/k cd /d ""{app}"" && echo Image Description Toolkit v{#MyAppVersion} && echo. && echo Type 'idt --help' for usage && echo."; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autodesktop}\ImageDescriber"; Filename: "{app}\ImageDescriber.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autodesktop}\IDT Chat"; Filename: "{app}\IDTChat.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "cmd.exe"; Parameters: "/k cd /d ""{app}"" && echo Image Description Toolkit v{#MyAppVersion} && echo. && echo Type 'idt --help' for usage && echo."; Description: "{cm:LaunchProgram,Image Description Toolkit (CLI)}"; Flags: nowait postinstall skipifsilent unchecked
Filename: "{app}\ImageDescriber.exe"; Description: "{cm:LaunchProgram,ImageDescriber}"; Flags: nowait postinstall skipifsilent
Filename: "https://ollama.com"; Description: "Open Ollama website to download (if not installed)"; Flags: shellexec postinstall skipifsilent unchecked; Check: ShouldShowOllamaWebsiteLink
Filename: "https://theideaplace.github.io/Image-Description-Toolkit/user-guide.html"; Description: "View Documentation"; Flags: shellexec postinstall skipifsilent unchecked