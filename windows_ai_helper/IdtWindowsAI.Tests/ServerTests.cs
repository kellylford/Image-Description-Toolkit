using System.Text.Json.Nodes;
using IdtWindowsAI;
using Xunit;

namespace IdtWindowsAI.Tests;

public class ServerTests
{
    private static readonly string Jpeg = Convert.ToBase64String([0xFF, 0xD8, 0xFF, 0xE0]);

    private static string Req(int id, string kind = "brief") =>
        new JsonObject { ["id"] = id, ["kind"] = kind, ["mime"] = "image/jpeg", ["image"] = Jpeg }.ToJsonString();

    private static async Task<List<JsonObject>> Serve(string input, Func<Protocol.DescribeRequest, Task<string>> describe, Action? onFailure = null)
    {
        var output = new StringWriter();
        await Server.RunAsync(new StringReader(input), output, describe, onFailure);
        var text = output.ToString();
        Assert.DoesNotContain("\r", text); // "\n" only, whatever the platform
        return text.Split('\n', StringSplitOptions.RemoveEmptyEntries).Select(l => JsonNode.Parse(l)!.AsObject()).ToList();
    }

    [Fact]
    public async Task EachRequest_GetsOneAnswer_InOrder_AndBlankLinesGetNone()
    {
        var answers = await Serve($"{Req(1)}\n\n   \n{Req(2, "detailed")}\r\n{Req(3)}",
            r => Task.FromResult($"{r.Kind} {r.Id}"));
        Assert.Equal([1, 2, 3], answers.Select(a => (int)a["id"]!));
        Assert.Equal(["brief 1", "detailed 2", "brief 3"], answers.Select(a => (string)a["text"]!));
        Assert.All(answers, a => Assert.True((bool)a["ok"]!));
    }

    [Fact]
    public async Task AnUnexpectedFailure_KeepsTheRequestsId_IsReported_AndServingCarriesOn()
    {
        var resets = 0;
        var answers = await Serve($"{Req(42)}\n{Req(43)}\n", r =>
            r.Id == 42 ? throw new InvalidOperationException("the NPU went away") : Task.FromResult("fine"),
            () => resets++);
        Assert.Equal(42, (int)answers[0]["id"]!);
        Assert.Equal(Codes.InternalError, (string)answers[0]["code"]!);
        Assert.Contains("the NPU went away", (string)answers[0]["message"]!);
        Assert.Equal(1, resets);
        Assert.Equal("fine", (string)answers[1]["text"]!);
    }

    [Fact]
    public async Task AProtocolFailure_IsAnsweredWithItsCode_AndDoesntReset()
    {
        var resets = 0;
        var answers = await Serve($"{Req(5)}\nnot json\n", r =>
            throw new ProtocolException(r.Id, Codes.ContentFiltered, "declined"), () => resets++);
        Assert.Equal((5, Codes.ContentFiltered), ((int)answers[0]["id"]!, (string)answers[0]["code"]!));
        Assert.Equal((0, Codes.BadRequest), ((int)answers[1]["id"]!, (string)answers[1]["code"]!));
        Assert.Equal(0, resets);
    }

    [Fact]
    public async Task ALineOverTheCap_IsRefusedAsTooLarge_AndTheNextLineStillWorks()
    {
        var huge = new string('x', Protocol.MaxLineChars + 10);
        var answers = await Serve($"{huge}\n{Req(9)}\n", r => Task.FromResult("after"));
        Assert.Equal(Codes.TooLarge, (string)answers[0]["code"]!);
        Assert.Equal("after", (string)answers[1]["text"]!);
    }

    [Fact]
    public async Task TheInputEnding_EndsServing_EvenWithoutAFinalNewline()
    {
        var answers = await Serve(Req(7), r => Task.FromResult("last"));
        Assert.Equal("last", (string)Assert.Single(answers)["text"]!);
        Assert.Empty(await Serve("", r => Task.FromResult("never")));
    }

    [Fact]
    public async Task LineReader_SplitsAcrossItsBuffer_AndStripsCr()
    {
        var long1 = new string('a', 100_000);
        var reader = new LineReader(new StringReader($"{long1}\r\nshort\n"), 200_000);
        Assert.Equal((long1, false), await reader.ReadLineAsync());
        Assert.Equal(("short", false), await reader.ReadLineAsync());
        Assert.Equal(((string?)null, false), await reader.ReadLineAsync());
    }

    [Fact]
    public async Task LineReader_ReportsAnOverlongLine_WithoutKeepingIt_ThenCarriesOn()
    {
        var reader = new LineReader(new StringReader(new string('z', 300_000) + "\nnext\n"), 1000);
        Assert.Equal(((string?)null, true), await reader.ReadLineAsync());
        Assert.Equal(("next", false), await reader.ReadLineAsync());
    }
}
