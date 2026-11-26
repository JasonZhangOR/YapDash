using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

[assembly: System.Reflection.AssemblyProduct("麦来 · YapDash")]
[assembly: System.Reflection.AssemblyTitle("麦来 · YapDash")]

internal static class Launcher
{
    [STAThread]
    private static int Main()
    {
        string folder = AppDomain.CurrentDomain.BaseDirectory;
        string launcher = Path.Combine(folder, "launch.pyw");
        try
        {
            string python = FindPython(folder);
            if (python == null || !File.Exists(launcher))
            {
                throw new InvalidOperationException(
                    "Keep the extracted files together and install Python 3.10–3.12.");
            }

            using (Process.Start(new ProcessStartInfo(python, "\"" + launcher + "\"")
            {
                WorkingDirectory = folder,
                UseShellExecute = false,
                CreateNoWindow = true
            })) { }
            return 0;
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "麦来 · YapDash", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    private static string FindPython(string folder)
    {
        string local = Path.Combine(folder, @".venv\Scripts\pythonw.exe");
        if (File.Exists(local))
        {
            return local;
        }

        string path = Environment.GetEnvironmentVariable("PATH") ?? "";
        foreach (string entry in path.Split(Path.PathSeparator))
        {
            string directory = entry.Trim().Trim('"');
            if (directory.Length == 0)
            {
                continue;
            }
            string candidate = Path.Combine(directory, "pythonw.exe");
            if (File.Exists(candidate))
            {
                return candidate;
            }
        }
        return null;
    }
}
