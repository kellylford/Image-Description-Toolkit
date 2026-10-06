// The only file that calls Windows' AI API. Everything it decides about results goes through
// Protocol, which is tested; this is the thin part that can only run on a Copilot+ PC.
using Microsoft.Graphics.Imaging;
using Microsoft.Windows.AI;
using Microsoft.Windows.AI.ContentSafety;
using Microsoft.Windows.AI.Imaging;
using Windows.Graphics.Imaging;
using Windows.Storage.Streams;

namespace IdtWindowsAI;

public sealed class Describer : IDisposable
{
    /// <summary>The longest side a picture is decoded at. The model works on far less; this
    /// keeps a huge photo from costing gigabytes of memory on the way in.</summary>
    private const uint MaxSide = 4096;

    private ImageDescriptionGenerator? _generator;

    public static string ReadyState() => ImageDescriptionGenerator.GetReadyState().ToString();

    /// <summary>Makes the model ready, downloading it the first time if Windows needs to.
    /// Returns null when ready, or the failure code and message.</summary>
    public static async Task<(string Code, string Message)?> PrepareAsync()
    {
        var state = ImageDescriptionGenerator.GetReadyState();
        if (Protocol.ForReadyState(state.ToString()) is { } unavailable) return unavailable;
        if (state == AIFeatureReadyState.Ready) return null;
        var result = await ImageDescriptionGenerator.EnsureReadyAsync();
        if (result.Status == AIFeatureReadyResultState.Success) return null;
        return (Codes.NotReady,
            "Windows couldn't get its image description model ready" +
            (result.ExtendedError is { } e ? $": {e.Message.Trim()} (0x{e.HResult:X8})." : ". It may still be downloading; try again in a few minutes."));
    }

    /// <summary>Describes one picture. Returns the description, or throws
    /// <see cref="ProtocolException"/> with the code to answer with.</summary>
    public async Task<string> DescribeAsync(Protocol.DescribeRequest request)
    {
        if (_generator is null)
        {
            if (await PrepareAsync() is { } notReady) throw new ProtocolException(request.Id, notReady.Code, notReady.Message);
            _generator = await ImageDescriptionGenerator.CreateAsync();
        }

        SoftwareBitmap bitmap;
        try
        {
            using var stream = new InMemoryRandomAccessStream();
            using (var writer = new DataWriter(stream))
            {
                writer.WriteBytes(request.Image);
                await writer.StoreAsync();
                writer.DetachStream();
            }
            stream.Seek(0);
            var decoder = await BitmapDecoder.CreateAsync(stream);
            var scale = Math.Min(1.0, (double)MaxSide / Math.Max(decoder.PixelWidth, decoder.PixelHeight));
            var transform = new BitmapTransform
            {
                ScaledWidth = (uint)Math.Max(1, Math.Round(decoder.PixelWidth * scale)),
                ScaledHeight = (uint)Math.Max(1, Math.Round(decoder.PixelHeight * scale)),
                InterpolationMode = BitmapInterpolationMode.Fant,
            };
            bitmap = await decoder.GetSoftwareBitmapAsync(BitmapPixelFormat.Bgra8, BitmapAlphaMode.Premultiplied,
                transform, ExifOrientationMode.RespectExifOrientation, ColorManagementMode.DoNotColorManage);
        }
        catch (Exception ex) when (ex is not ProtocolException)
        {
            // The decoder's own messages are often empty; say what failed.
            throw new ProtocolException(request.Id, Codes.DecodeFailed,
                $"The picture couldn't be read as {request.Mime}" + (string.IsNullOrWhiteSpace(ex.Message) ? "." : $": {ex.Message.Trim()}"));
        }

        using (bitmap)
        {
            var image = ImageBuffer.CreateForSoftwareBitmap(bitmap);
            var result = await _generator.DescribeAsync(image, KindFor(request.Kind), new ContentFilterOptions());
            var status = result.Status.ToString();
            if (Protocol.CodeForStatus(status) is { } code) throw new ProtocolException(request.Id, code, Protocol.MessageForStatus(status));
            return result.Description;
        }
    }

    private static ImageDescriptionKind KindFor(string kind) => kind switch
    {
        "detailed" => ImageDescriptionKind.DetailedDescription,
        "brief" => ImageDescriptionKind.BriefDescription,
        "diagram" => ImageDescriptionKind.DiagramDescription,
        _ => ImageDescriptionKind.AccessibleDescription,
    };

    public void Dispose() => _generator?.Dispose();
}
