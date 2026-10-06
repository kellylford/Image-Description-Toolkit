// Trial for TheWorkBench#165: describe a picture with Windows' on-device image description model.
// Prints each step, so a failure says where it happened and why.
//   describe-trial <picture> [Accessible|Brief|Detailed|Diagram ...]
using Microsoft.Graphics.Imaging;
using Microsoft.Windows.AI;
using Microsoft.Windows.AI.ContentSafety;
using Microsoft.Windows.AI.Imaging;
using Windows.Graphics.Imaging;
using Windows.Storage;

// Started as DescribeTrial.exe from its folder, it has no package identity, and the API refuses
// anything without one. So it starts itself again through its command, describe-trial, which
// Windows runs as the package, and passes on what that prints.
if (!HasIdentity())
{
    var alias = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
        @"Microsoft\WindowsApps\describe-trial.exe");
    if (!File.Exists(alias))
    {
        Console.WriteLine("The trial isn't installed as a package, and it only works as one. Register it with:");
        Console.WriteLine($"  powershell Add-AppxPackage -Register \"{Path.Combine(AppContext.BaseDirectory, "AppxManifest.xml")}\"");
        return 1;
    }
    var start = new System.Diagnostics.ProcessStartInfo(alias) { UseShellExecute = false };
    foreach (var a in args) start.ArgumentList.Add(a);
    using var again = System.Diagnostics.Process.Start(start)!;
    again.WaitForExit();
    return again.ExitCode;
}

if (args.Length == 0)
{
    Console.WriteLine("Usage: describe-trial <picture> [Accessible|Brief|Detailed|Diagram ...]");
    return 2;
}
var path = Path.GetFullPath(args[0]);
var kinds = args.Length > 1
    ? args.Skip(1).Select(k => Enum.Parse<ImageDescriptionKind>(k + "Description", ignoreCase: true)).ToArray()
    : [ImageDescriptionKind.AccessibleDescription, ImageDescriptionKind.BriefDescription];

try
{
    Console.WriteLine($"Package identity: {Identity()}");
    var state = ImageDescriptionGenerator.GetReadyState();
    Console.WriteLine($"Ready state: {state}");
    if (state == AIFeatureReadyState.NotReady)
    {
        Console.WriteLine("Getting the model ready (the first time, Windows may download it)...");
        var ready = await ImageDescriptionGenerator.EnsureReadyAsync();
        Console.WriteLine($"EnsureReadyAsync: {ready.Status}{(ready.ExtendedError is { } e ? $" ({e.Message}, 0x{e.HResult:X8})" : "")}");
        if (ready.Status != AIFeatureReadyResultState.Success) return 1;
    }
    else if (state != AIFeatureReadyState.Ready)
    {
        Console.WriteLine("The model can't be used on this PC.");
        return 1;
    }

    using var generator = await ImageDescriptionGenerator.CreateAsync();
    var file = await StorageFile.GetFileFromPathAsync(path);
    using var stream = await file.OpenReadAsync();
    var decoder = await BitmapDecoder.CreateAsync(stream);
    using var bitmap = await decoder.GetSoftwareBitmapAsync(BitmapPixelFormat.Bgra8, BitmapAlphaMode.Premultiplied);
    var image = ImageBuffer.CreateForSoftwareBitmap(bitmap);
    Console.WriteLine($"Picture: {path}, {decoder.PixelWidth} by {decoder.PixelHeight}");

    foreach (var kind in kinds)
    {
        var started = DateTime.Now;
        var result = await generator.DescribeAsync(image, kind, new ContentFilterOptions());
        Console.WriteLine();
        Console.WriteLine($"{kind} ({(DateTime.Now - started).TotalSeconds:0.0} s, {result.Status}):");
        Console.WriteLine(result.Description);
    }
    return 0;
}
catch (Exception ex)
{
    Console.WriteLine($"Failed: {ex.GetType().Name} 0x{ex.HResult:X8}: {ex.Message}");
    return 1;
}

static bool HasIdentity()
{
    try { _ = Windows.ApplicationModel.Package.Current.Id; return true; }
    catch (InvalidOperationException) { return false; }
}

static string Identity()
{
    try { return Windows.ApplicationModel.Package.Current.Id.FullName; }
    catch (InvalidOperationException) { return "none (not running as a packaged app)"; }
}
