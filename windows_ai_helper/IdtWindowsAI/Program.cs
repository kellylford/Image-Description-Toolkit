// IDT's Windows AI helper: describes pictures with Windows' on-device model on a Copilot+ PC.
//
//   idt-windows-ai --check                 readiness, as one JSON line
//   idt-windows-ai --prepare               make the model ready (may download it), as one JSON line
//   idt-windows-ai --serve                 JSON lines on stdin and stdout, for IDT (see Protocol.cs)
//   idt-windows-ai --describe <picture> [kind ...]   describe one picture, for people
//   idt-windows-ai --version
//
// Windows only lets a packaged app use the model, so this must run with its package's identity:
// started as idt-windows-ai (the command its package adds), not as IdtWindowsAI.exe from its
// folder. Started without identity, it starts itself again through that command.
using IdtWindowsAI;

const string Alias = "idt-windows-ai.exe";

Console.OutputEncoding = new System.Text.UTF8Encoding(false);
Console.InputEncoding = new System.Text.UTF8Encoding(false);
var mode = args.FirstOrDefault()?.ToLowerInvariant() ?? "--help";

if (mode is "--version")
{
    Console.WriteLine(typeof(Protocol).Assembly.GetName().Version?.ToString(3));
    return 0;
}
if (mode is "--help" or "-h" or "/?")
{
    Console.WriteLine("Usage: idt-windows-ai --check | --prepare | --serve | --describe <picture> [kind ...] | --version");
    Console.WriteLine($"Kinds: {string.Join(", ", Protocol.Kinds)}");
    return 0;
}

if (!HasIdentity())
{
    var alias = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Microsoft", "WindowsApps", Alias);
    if (!File.Exists(alias))
    {
        var message = "The Windows AI helper isn't installed as a package, and Windows only lets a package use its model.";
        if (mode is "--check" or "--prepare") Console.WriteLine(Protocol.Readiness(false, "NoIdentity", message));
        else Console.Error.WriteLine(message);
        return 1;
    }
    // The child inherits this console's stdin and stdout, so --serve works through the restart too.
    var start = new System.Diagnostics.ProcessStartInfo(alias) { UseShellExecute = false };
    foreach (var a in args) start.ArgumentList.Add(a);
    using var again = System.Diagnostics.Process.Start(start)!;
    again.WaitForExit();
    return again.ExitCode;
}

switch (mode)
{
    case "--check":
        Console.WriteLine(Protocol.Readiness(true, Describer.ReadyState()));
        return 0;

    case "--prepare":
    {
        var failure = await Describer.PrepareAsync();
        Console.WriteLine(Protocol.Readiness(true, Describer.ReadyState(), failure?.Message));
        return failure is null ? 0 : 1;
    }

    case "--serve":
        return await ServeAsync();

    case "--describe":
        return await DescribeForPeopleAsync(args.Skip(1).ToArray());

    default:
        Console.Error.WriteLine($"Unknown option {args[0]}. Try --help.");
        return 2;
}

// One request per line until stdin closes, which is also how the helper ends when IDT exits or
// is killed: nothing is left running.
static async Task<int> ServeAsync()
{
    using var describer = new Describer();
    string? line;
    while ((line = Console.ReadLine()) is not null)
    {
        if (line.Trim().Length == 0) continue;
        var started = DateTime.UtcNow;
        string response;
        try
        {
            var request = Protocol.ParseRequest(line);
            var text = await describer.DescribeAsync(request);
            response = Protocol.Success(request.Id, request.Kind, text, (DateTime.UtcNow - started).TotalSeconds);
        }
        catch (ProtocolException ex)
        {
            response = Protocol.Failure(ex.Id, ex.Code, ex.Message);
        }
        catch (Exception ex)
        {
            response = Protocol.Failure(0, Codes.InternalError, $"{ex.GetType().Name} 0x{ex.HResult:X8}: {ex.Message.Trim()}");
        }
        Console.WriteLine(response);
        Console.Out.Flush();
    }
    return 0;
}

static async Task<int> DescribeForPeopleAsync(string[] rest)
{
    if (rest.Length == 0)
    {
        Console.Error.WriteLine("Usage: idt-windows-ai --describe <picture> [kind ...]");
        return 2;
    }
    var path = Path.GetFullPath(rest[0]);
    var kinds = rest.Length > 1 ? rest.Skip(1).Select(k => k.ToLowerInvariant()).ToArray() : [Protocol.Kinds[0]];
    var mime = Path.GetExtension(path).ToLowerInvariant() switch
    {
        ".jpg" or ".jpeg" => "image/jpeg", ".png" => "image/png", ".bmp" => "image/bmp",
        ".gif" => "image/gif", ".tif" or ".tiff" => "image/tiff", var other => $"unknown ({other})",
    };
    byte[] image;
    try { image = await File.ReadAllBytesAsync(path); }
    catch (Exception ex) { Console.Error.WriteLine($"Can't read {path}: {ex.Message}"); return 1; }

    using var describer = new Describer();
    var status = 0;
    foreach (var kind in kinds)
    {
        var started = DateTime.UtcNow;
        try
        {
            var request = Protocol.ParseRequest(
                new System.Text.Json.Nodes.JsonObject { ["kind"] = kind, ["mime"] = mime, ["image"] = Convert.ToBase64String(image) }.ToJsonString());
            var text = await describer.DescribeAsync(request);
            Console.WriteLine($"{char.ToUpperInvariant(kind[0])}{kind[1..]} ({(DateTime.UtcNow - started).TotalSeconds:0.0} s):");
            Console.WriteLine(text);
        }
        catch (ProtocolException ex)
        {
            Console.WriteLine($"{kind}: {ex.Message}");
            status = 1;
        }
        Console.WriteLine();
    }
    return status;
}

static bool HasIdentity()
{
    try { _ = Windows.ApplicationModel.Package.Current.Id; return true; }
    catch (InvalidOperationException) { return false; }
}
