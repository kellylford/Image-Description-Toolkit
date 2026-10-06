using System.Text.Json.Nodes;
using IdtWindowsAI;
using Xunit;

namespace IdtWindowsAI.Tests;

public class ProtocolTests
{
    private static readonly string Jpeg = Convert.ToBase64String([0xFF, 0xD8, 0xFF, 0xE0]);

    private static string Request(object? kind = null, object? mime = null, object? image = null, object? id = null)
    {
        var o = new JsonObject();
        if (id is not null) o["id"] = JsonValue.Create(id);
        if (kind is not null) o["kind"] = JsonValue.Create(kind);
        o["mime"] = mime is null ? "image/jpeg" : JsonValue.Create(mime);
        o["image"] = image is null ? Jpeg : JsonValue.Create(image);
        return o.ToJsonString();
    }

    private static ProtocolException Refused(string line) => Assert.Throws<ProtocolException>(() => Protocol.ParseRequest(line));

    [Fact]
    public void AValidRequest_IsRead()
    {
        var r = Protocol.ParseRequest(Request("detailed", id: 7));
        Assert.Equal(7, r.Id);
        Assert.Equal("detailed", r.Kind);
        Assert.Equal("image/jpeg", r.Mime);
        Assert.Equal(4, r.Image.Length);
    }

    [Fact]
    public void WithNoKind_TheFirstKindIsUsed_AndItIsAccessible()
    {
        Assert.Equal("accessible", Protocol.Kinds[0]);
        Assert.Equal("accessible", Protocol.ParseRequest(Request()).Kind);
    }

    [Theory]
    [InlineData(" Brief ", "brief")]
    [InlineData("DIAGRAM", "diagram")]
    public void Kinds_IgnoreCaseAndSpaces(string given, string expected) =>
        Assert.Equal(expected, Protocol.ParseRequest(Request(given)).Kind);

    [Fact]
    public void AnUnknownKind_IsABadRequest_ThatKeepsItsIdAndNamesTheKinds()
    {
        var ex = Refused(Request("poetic", id: 3));
        Assert.Equal(Codes.BadRequest, ex.Code);
        Assert.Equal(3, ex.Id);
        Assert.Contains("accessible, detailed, brief, diagram", ex.Message);
    }

    [Theory]
    [InlineData("not json")]
    [InlineData("[1, 2]")]
    [InlineData("42")]
    public void ALineThatIsntAnObject_IsABadRequestWithIdZero(string line)
    {
        var ex = Refused(line);
        Assert.Equal(Codes.BadRequest, ex.Code);
        Assert.Equal(0, ex.Id);
    }

    [Fact]
    public void ANonNumberId_IsTreatedAsZero_NotAnError() =>
        Assert.Equal(0, Protocol.ParseRequest(Request(id: "seven")).Id);

    [Fact]
    public void ImageJpg_IsReadAsJpeg() =>
        Assert.Equal("image/jpeg", Protocol.ParseRequest(Request(mime: "IMAGE/JPG")).Mime);

    [Theory]
    [InlineData("video/mp4")]
    [InlineData("image/heic")]
    [InlineData("")]
    public void AnUnsupportedOrMissingType_IsUnsupportedFormat(string mime) =>
        Assert.Equal(Codes.UnsupportedFormat, Refused(Request(mime: mime)).Code);

    [Fact]
    public void NoPicture_IsABadRequest()
    {
        var line = new JsonObject { ["id"] = 1, ["mime"] = "image/png" }.ToJsonString();
        Assert.Equal(Codes.BadRequest, Refused(line).Code);
    }

    [Theory]
    [InlineData("%%%")]
    [InlineData("")]
    public void BadOrEmptyBase64_IsABadRequest(string image) =>
        Assert.Equal(Codes.BadRequest, Refused(Request(image: image)).Code);

    [Fact]
    public void APictureOverTheLimit_IsRefusedBeforeDecoding()
    {
        var huge = Convert.ToBase64String(new byte[Protocol.MaxImageBytes + 1]);
        Assert.Equal(Codes.UnsupportedFormat, Refused(Request(image: huge)).Code);
    }

    [Theory]
    [InlineData("Complete", null)]
    [InlineData("ImageBlockedByContentModeration", Codes.ContentFiltered)]
    [InlineData("TextInImageBlockedByContentModeration", Codes.ContentFiltered)]
    [InlineData("DescriptionTextBlockedByContentModeration", Codes.ContentFiltered)]
    [InlineData("ImageHasTooMuchText", Codes.TooMuchText)]
    [InlineData("BlockedByPolicy", Codes.BlockedByPolicy)]
    [InlineData("InternalError", Codes.InternalError)]
    [InlineData("InProgress", Codes.InternalError)]
    [InlineData("SomethingNew", Codes.InternalError)]
    public void EachResultStatus_HasItsCode(string status, string? code)
    {
        Assert.Equal(code, Protocol.CodeForStatus(status));
        if (code is not null) Assert.False(string.IsNullOrWhiteSpace(Protocol.MessageForStatus(status)));
    }

    [Theory]
    [InlineData("Ready", null)]
    [InlineData("NotReady", null)]
    [InlineData("NotSupportedOnCurrentSystem", Codes.NotSupported)]
    [InlineData("DisabledByUser", Codes.DisabledByUser)]
    [InlineData("SomethingNew", Codes.NotSupported)]
    public void EachReadyState_IsUsableOrSaysWhyNot(string state, string? code)
    {
        var result = Protocol.ForReadyState(state);
        Assert.Equal(code, result?.Code);
        if (result is { } r) Assert.False(string.IsNullOrWhiteSpace(r.Message));
    }

    [Fact]
    public void ASuccess_HasTheFieldsIdtReads()
    {
        var o = JsonNode.Parse(Protocol.Success(4, "brief", "A tree.", 2.4567))!.AsObject();
        Assert.Equal(4, (int)o["id"]!);
        Assert.True((bool)o["ok"]!);
        Assert.Equal("brief", (string)o["kind"]!);
        Assert.Equal("A tree.", (string)o["text"]!);
        Assert.Equal(2.46, (double)o["seconds"]!);
    }

    [Fact]
    public void AFailure_HasTheFieldsIdtReads_AndApostrophesStayReadable()
    {
        var line = Protocol.Failure(5, Codes.ContentFiltered, "Windows' filter");
        Assert.Contains("Windows' filter", line);
        var o = JsonNode.Parse(line)!.AsObject();
        Assert.Equal(5, (int)o["id"]!);
        Assert.False((bool)o["ok"]!);
        Assert.Equal(Codes.ContentFiltered, (string)o["code"]!);
    }

    [Fact]
    public void Readiness_SaysTheProtocolVersionAndKinds()
    {
        var o = JsonNode.Parse(Protocol.Readiness(true, "Ready"))!.AsObject();
        Assert.Equal(Protocol.Version, (int)o["protocol"]!);
        Assert.True((bool)o["identity"]!);
        Assert.Equal("Ready", (string)o["state"]!);
        Assert.Equal(Protocol.Kinds, o["kinds"]!.AsArray().Select(k => (string)k!).ToArray());
        Assert.Null(o["message"]);
        Assert.Equal("why", (string)JsonNode.Parse(Protocol.Readiness(false, "NoIdentity", "why"))!["message"]!);
    }
}
