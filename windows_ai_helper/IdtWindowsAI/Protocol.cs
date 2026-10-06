// The helper's protocol with IDT. Plain C#, no Windows Runtime, so it is unit tested on any
// machine (windows_ai_helper/IdtWindowsAI.Tests), including CI runners with no NPU.
//
// Serve mode reads one JSON request per line on stdin and writes one JSON response per line on
// stdout, in order. Requests:
//   {"id": 7, "kind": "accessible", "mime": "image/jpeg", "image": "<base64>"}
// Responses:
//   {"id": 7, "ok": true,  "kind": "accessible", "text": "...", "seconds": 2.41}
//   {"id": 7, "ok": false, "code": "content_filtered", "message": "..."}
// The codes are the contract; IDT's Python side (idt_core/providers/windows_ai.py) decides what
// each one means for a batch. Bump Version if a field's meaning changes.
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace IdtWindowsAI;

public static class Protocol
{
    public const int Version = 1;

    /// <summary>The description kinds, in IDT's order: the first is the default.</summary>
    public static readonly string[] Kinds = ["accessible", "detailed", "brief", "diagram"];

    /// <summary>What the image decoder is asked to read. IDT converts anything else (HEIC, WebP)
    /// to JPEG before it gets here.</summary>
    public static readonly string[] SupportedMimeTypes = ["image/jpeg", "image/png", "image/bmp", "image/gif", "image/tiff"];

    /// <summary>Larger than any picture IDT sends (it resizes past 3.75 MB), small enough that a
    /// bad request can't exhaust memory.</summary>
    public const int MaxImageBytes = 50 * 1024 * 1024;

    /// <summary>Apostrophes and accents written as themselves, not as escapes: the output is
    /// valid JSON either way, and people read --check's.</summary>
    private static readonly JsonSerializerOptions Readable = new() { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping };

    public sealed record DescribeRequest(int Id, string Kind, string Mime, byte[] Image);

    /// <summary>Reads one request line. Throws <see cref="ProtocolException"/> with the code to
    /// answer with, and the request's id when it could be read.</summary>
    public static DescribeRequest ParseRequest(string line)
    {
        JsonObject request;
        try
        {
            request = JsonNode.Parse(line) as JsonObject ?? throw new JsonException("not an object");
        }
        catch (JsonException ex)
        {
            throw new ProtocolException(0, Codes.BadRequest, $"The request isn't valid JSON: {ex.Message}");
        }

        var id = 0;
        if (request["id"] is JsonValue idValue && idValue.TryGetValue(out int parsedId)) id = parsedId;

        var kind = (request["kind"]?.GetValueKind() == JsonValueKind.String ? request["kind"]!.GetValue<string>() : null)?.Trim().ToLowerInvariant()
            ?? Kinds[0];
        if (!Kinds.Contains(kind))
            throw new ProtocolException(id, Codes.BadRequest, $"There's no description kind '{kind}'. The kinds are {string.Join(", ", Kinds)}.");

        var mime = (request["mime"]?.GetValueKind() == JsonValueKind.String ? request["mime"]!.GetValue<string>() : "")?.Trim().ToLowerInvariant() ?? "";
        if (mime == "image/jpg") mime = "image/jpeg";
        if (!SupportedMimeTypes.Contains(mime))
            throw new ProtocolException(id, Codes.UnsupportedFormat,
                mime.Length == 0 ? "The request didn't say what kind of picture it is." : $"Pictures of type {mime} can't be described.");

        if (request["image"]?.GetValueKind() != JsonValueKind.String)
            throw new ProtocolException(id, Codes.BadRequest, "The request has no picture.");
        byte[] image;
        try
        {
            image = Convert.FromBase64String(request["image"]!.GetValue<string>());
        }
        catch (FormatException)
        {
            throw new ProtocolException(id, Codes.BadRequest, "The picture isn't valid base64.");
        }
        if (image.Length == 0) throw new ProtocolException(id, Codes.BadRequest, "The picture is empty.");
        if (image.Length > MaxImageBytes)
            throw new ProtocolException(id, Codes.UnsupportedFormat, $"The picture is {image.Length / (1024 * 1024)} MB; the limit is {MaxImageBytes / (1024 * 1024)} MB.");

        return new DescribeRequest(id, kind, mime, image);
    }

    public static string Success(int id, string kind, string text, double seconds) =>
        new JsonObject { ["id"] = id, ["ok"] = true, ["kind"] = kind, ["text"] = text, ["seconds"] = Math.Round(seconds, 2) }.ToJsonString(Readable);

    public static string Failure(int id, string code, string message) =>
        new JsonObject { ["id"] = id, ["ok"] = false, ["code"] = code, ["message"] = message }.ToJsonString(Readable);

    /// <summary>The readiness report for --check and --prepare.</summary>
    public static string Readiness(bool identity, string state, string? message = null)
    {
        var o = new JsonObject
        {
            ["protocol"] = Version,
            ["version"] = typeof(Protocol).Assembly.GetName().Version?.ToString(3) ?? "",
            ["identity"] = identity,
            ["state"] = state,
            ["kinds"] = new JsonArray(Kinds.Select(k => (JsonNode)k).ToArray()),
        };
        if (message is not null) o["message"] = message;
        return o.ToJsonString(Readable);
    }

    /// <summary>The code for a finished description's status, by the status's name in
    /// Microsoft.Windows.AI.Imaging.ImageDescriptionResultStatus. Null means it succeeded.</summary>
    public static string? CodeForStatus(string status) => status switch
    {
        "Complete" => null,
        "ImageBlockedByContentModeration" or "TextInImageBlockedByContentModeration"
            or "DescriptionTextBlockedByContentModeration" => Codes.ContentFiltered,
        "ImageHasTooMuchText" => Codes.TooMuchText,
        "BlockedByPolicy" => Codes.BlockedByPolicy,
        _ => Codes.InternalError, // InternalError, and InProgress, which a finished call shouldn't report
    };

    /// <summary>What to tell the user for a status that isn't Complete.</summary>
    public static string MessageForStatus(string status) => status switch
    {
        "ImageBlockedByContentModeration" => "Windows' content filter declined to describe this picture.",
        "TextInImageBlockedByContentModeration" => "Windows' content filter declined the text in this picture.",
        "DescriptionTextBlockedByContentModeration" => "Windows' content filter declined the description it wrote for this picture.",
        "ImageHasTooMuchText" => "This picture has too much text for Windows to describe. Try OCR instead.",
        "BlockedByPolicy" => "A policy on this PC blocks Windows' image description.",
        _ => $"Windows couldn't describe this picture ({status}).",
    };

    /// <summary>The code and message for a model that isn't ready to use, by the state's name in
    /// Microsoft.Windows.AI.AIFeatureReadyState. Null when it is Ready or can be made ready.</summary>
    public static (string Code, string Message)? ForReadyState(string state) => state switch
    {
        "Ready" or "NotReady" => null,
        "NotSupportedOnCurrentSystem" => (Codes.NotSupported,
            "Windows' image description needs a Copilot+ PC, with an NPU, and a recent version of Windows 11."),
        "DisabledByUser" => (Codes.DisabledByUser,
            "Windows' AI features are turned off on this PC. They can be turned on in Settings, Privacy & security."),
        _ => (Codes.NotSupported, $"Windows' image description isn't available on this PC ({state})."),
    };
}

/// <summary>The failure codes. The Python side maps each to what a batch should do.</summary>
public static class Codes
{
    public const string ContentFiltered = "content_filtered";
    public const string TooMuchText = "too_much_text";
    public const string BlockedByPolicy = "blocked_by_policy";
    public const string NotSupported = "not_supported";
    public const string DisabledByUser = "disabled_by_user";
    public const string NotReady = "not_ready";
    public const string NoIdentity = "no_identity";
    public const string InternalError = "internal_error";
    public const string UnsupportedFormat = "unsupported_format";
    public const string DecodeFailed = "decode_failed";
    public const string BadRequest = "bad_request";
}

public sealed class ProtocolException(int id, string code, string message) : Exception(message)
{
    public int Id { get; } = id;
    public string Code { get; } = code;
}
