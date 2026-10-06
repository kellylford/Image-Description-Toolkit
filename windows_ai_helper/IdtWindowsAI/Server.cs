// The --serve loop: one request per line in, one answer per line out, in order, until the input
// ends. Plain C#, given the describing as a function, so it is tested without the model.
using System.Text;

namespace IdtWindowsAI;

public static class Server
{
    /// <summary>
    /// Serves until <paramref name="input"/> ends. Every request line gets exactly one answer,
    /// carrying its id whenever the id could be read; blank lines get none. An exception from
    /// <paramref name="describe"/> other than <see cref="ProtocolException"/> is answered as
    /// internal_error and reported to <paramref name="onUnexpectedFailure"/>, which can reset
    /// whatever failed, and serving carries on.
    /// </summary>
    public static async Task RunAsync(TextReader input, TextWriter output,
        Func<Protocol.DescribeRequest, Task<string>> describe, Action? onUnexpectedFailure = null)
    {
        var reader = new LineReader(input, Protocol.MaxLineChars);
        while (true)
        {
            var (line, tooLong) = await reader.ReadLineAsync();
            if (line is null && !tooLong) return; // the input ended
            string response;
            if (tooLong)
            {
                response = Protocol.Failure(0, Codes.TooLarge,
                    $"The request is too large; a picture can be at most {Protocol.MaxImageBytes / (1024 * 1024)} MB.");
            }
            else if (line!.Trim().Length == 0)
            {
                continue;
            }
            else
            {
                var started = DateTime.UtcNow;
                var id = 0;
                try
                {
                    var request = Protocol.ParseRequest(line);
                    id = request.Id;
                    var text = await describe(request);
                    response = Protocol.Success(id, request.Kind, text, (DateTime.UtcNow - started).TotalSeconds);
                }
                catch (ProtocolException ex)
                {
                    response = Protocol.Failure(ex.Id, ex.Code, ex.Message);
                }
                catch (Exception ex)
                {
                    onUnexpectedFailure?.Invoke();
                    response = Protocol.Failure(id, Codes.InternalError, $"{ex.GetType().Name} 0x{ex.HResult:X8}: {ex.Message.Trim()}");
                }
            }
            // "\n" whatever the platform: the reader on the other end splits on it.
            await output.WriteAsync(response + "\n");
            await output.FlushAsync();
        }
    }
}

/// <summary>Reads lines with a length cap: a longer line is skipped as it arrives rather than
/// built up in memory, and reported as too long.</summary>
public sealed class LineReader(TextReader input, int maxChars)
{
    private readonly char[] _buffer = new char[64 * 1024];
    private int _start;
    private int _end;

    /// <summary>The next line without its line ending, or (null, false) at the end of the input,
    /// or (null, true) for a line over the cap.</summary>
    public async Task<(string? Line, bool TooLong)> ReadLineAsync()
    {
        var line = new StringBuilder();
        var tooLong = false;
        var any = false;
        while (true)
        {
            if (_start == _end)
            {
                _start = 0;
                _end = await input.ReadAsync(_buffer, 0, _buffer.Length);
                if (_end == 0)
                    return any ? (tooLong ? (null, true) : (TrimCr(line), false)) : (null, false);
            }
            any = true;
            var newline = Array.IndexOf(_buffer, '\n', _start, _end - _start);
            var stop = newline < 0 ? _end : newline;
            if (!tooLong)
            {
                if (line.Length + (stop - _start) > maxChars)
                {
                    tooLong = true;
                    line.Clear();
                }
                else
                {
                    line.Append(_buffer, _start, stop - _start);
                }
            }
            if (newline < 0)
            {
                _start = _end;
                continue;
            }
            _start = newline + 1;
            return tooLong ? (null, true) : (TrimCr(line), false);
        }
    }

    private static string TrimCr(StringBuilder line)
    {
        if (line.Length > 0 && line[^1] == '\r') line.Length--;
        return line.ToString();
    }
}
