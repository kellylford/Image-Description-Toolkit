// The only file that calls Windows' AI API. What it decides about results goes through Protocol,
// which is tested; this is the thin part that can only run on a Copilot+ PC.
using System.Runtime.InteropServices.WindowsRuntime;
using Microsoft.Graphics.Imaging;
using Microsoft.Windows.AI;
using Microsoft.Windows.AI.ContentSafety;
using Microsoft.Windows.AI.Imaging;
using Windows.Graphics.Imaging;
using Windows.Storage.Streams;

namespace IdtWindowsAI;

public sealed class Describer : IDisposable
{
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
    /// <see cref="ProtocolException"/> with the code to answer with. Anything else it throws is
    /// unexpected; the caller should then <see cref="Reset"/>.</summary>
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
            await stream.WriteAsync(request.Image.AsBuffer());
            stream.Seek(0);
            var decoder = await BitmapDecoder.CreateAsync(stream);
            var (width, height) = Protocol.ScaledSize(decoder.PixelWidth, decoder.PixelHeight);
            var transform = new BitmapTransform
            {
                ScaledWidth = width,
                ScaledHeight = height,
                InterpolationMode = BitmapInterpolationMode.Fant,
            };
            bitmap = await decoder.GetSoftwareBitmapAsync(BitmapPixelFormat.Bgra8, BitmapAlphaMode.Premultiplied,
                transform, ExifOrientationMode.RespectExifOrientation, ColorManagementMode.DoNotColorManage);
        }
        catch (Exception ex)
        {
            // The decoder's own messages are often empty; say what failed.
            throw new ProtocolException(request.Id, Codes.DecodeFailed,
                $"The picture couldn't be read as {request.Mime}" + (string.IsNullOrWhiteSpace(ex.Message) ? "." : $": {ex.Message.Trim()}"));
        }

        using (bitmap)
        using (var image = ImageBuffer.CreateForSoftwareBitmap(bitmap))
        {
            var kind = Enum.Parse<ImageDescriptionKind>(Protocol.ApiKindName(request.Kind));
            var result = await _generator.DescribeAsync(image, kind, new ContentFilterOptions());
            var status = result.Status.ToString();
            if (Protocol.CodeForStatus(status) is { } code) throw new ProtocolException(request.Id, code, Protocol.MessageForStatus(status));
            return result.Description;
        }
    }

    /// <summary>Drops the model after an unexpected failure, so the next request starts it
    /// afresh rather than reusing one that may be broken (the NPU reset, say).</summary>
    public void Reset()
    {
        try { _generator?.Dispose(); } catch { /* it may already be gone */ }
        _generator = null;
    }

    public void Dispose() => Reset();
}
