using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using NAudio.Wave;
using NAudio.CoreAudioApi;

internal static class LoopbackProbe
{
    [MTAThread]
    private static int Main(string[] args)
    {
        if (args.Length != 1)
        {
            Console.Error.WriteLine("Pass an existing, isolated run directory.");
            return 2;
        }

        try
        {
            string directory = Path.GetFullPath(args[0]);
            Record(directory);
            File.WriteAllText(Path.Combine(directory, "wasapi.complete"), "WAV closed successfully");
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine(error);
            return 1;
        }
    }

    private static void Record(string directory)
    {
        string output = Path.Combine(directory, "wasapi.wav");
        string ready = Path.Combine(directory, "wasapi.ready");
        string stop = Path.Combine(directory, "wasapi.stop");
        var format = new WaveFormat(48000, 16, 2);
        using (var finished = new ManualResetEvent(false))
        using (var writer = new WaveFileWriter(output, format))
        using (var recorder = new WasapiLoopbackCapture())
        {
            recorder.WaveFormat = format;
            Exception failure = null;
            recorder.DataAvailable += (sender, eventArgs) =>
                writer.Write(eventArgs.Buffer, 0, eventArgs.BytesRecorded);
            recorder.RecordingStopped += (sender, eventArgs) =>
            {
                failure = eventArgs.Exception;
                finished.Set();
            };

            recorder.StartRecording();
            var startup = Stopwatch.StartNew();
            while (recorder.CaptureState == CaptureState.Starting)
            {
                if (startup.Elapsed > TimeSpan.FromSeconds(20))
                    throw new TimeoutException("WASAPI did not start.");
                Thread.Sleep(25);
            }
            if (recorder.CaptureState != CaptureState.Capturing)
                throw new InvalidOperationException("WASAPI stopped at startup.", failure);

            File.WriteAllText(ready, "WASAPI loopback recording");
            var recording = Stopwatch.StartNew();
            while (!File.Exists(stop) && !finished.WaitOne(100))
            {
                if (recording.Elapsed > TimeSpan.FromMinutes(12))
                    throw new TimeoutException("The guest did not stop the WASAPI probe.");
            }

            bool stoppedEarly = !File.Exists(stop);
            recorder.StopRecording();
            if (!finished.WaitOne(TimeSpan.FromSeconds(15)))
                throw new TimeoutException("WASAPI did not finish writing.");
            if (failure != null || stoppedEarly)
                throw new InvalidOperationException("WASAPI stopped during capture.", failure);
            if (writer.Length == 0)
                throw new InvalidDataException("WASAPI captured no PCM frames.");
        }
    }
}
