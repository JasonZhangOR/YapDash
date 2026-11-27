using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Windows.Forms;
using Microsoft.Win32;

internal static class Setup
{
    private const string Product = "麦来 · YapDash";
    private const string RegistryPath = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\YapDash";
    private static readonly string DirectoryPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "YapDash");
    private static readonly string StartLink = ShortcutPath(Environment.SpecialFolder.Programs);
    private static readonly string DesktopLink = ShortcutPath(Environment.SpecialFolder.DesktopDirectory);

    [STAThread]
    private static int Main(string[] args)
    {
        Application.EnableVisualStyles();
        try
        {
            if (args.Length == 1 && args[0] == "--verify")
            {
                string scratch = Path.Combine(Path.GetTempPath(), "YapDash-" + Guid.NewGuid());
                try { Extract(scratch); }
                finally { if (Directory.Exists(scratch)) Directory.Delete(scratch, true); }
                return 0;
            }
#if UNINSTALL
            Uninstall();
#else
            ShowInstaller();
#endif
            return 0;
        }
        catch (Exception error)
        {
            if (args.Length != 1 || args[0] != "--verify")
                MessageBox.Show(error.Message, Product, MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    private static void Extract(string destination)
    {
        using (var payload = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip"))
        using (var archive = new ZipArchive(payload, ZipArchiveMode.Read))
            archive.ExtractToDirectory(destination);
    }

    private static string ShortcutPath(Environment.SpecialFolder folder)
    {
        return Path.Combine(Environment.GetFolderPath(folder), Product + ".lnk");
    }

    private static void MakeShortcut(string path, string target)
    {
        dynamic shell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));
        dynamic shortcut = shell.CreateShortcut(path);
        shortcut.TargetPath = target;
        shortcut.WorkingDirectory = DirectoryPath;
        shortcut.Save();
    }

    private static void ShowInstaller()
    {
        if (!Environment.Is64BitOperatingSystem || Environment.OSVersion.Version.Build < 20348)
            throw new InvalidOperationException("需要 64 位 Windows 11 或支持应用音频捕获的 Windows（内部版本 20348 或更高）。");
        using (var form = new Form { Text = "安装 " + Product, Width = 520, Height = 260,
            StartPosition = FormStartPosition.CenterScreen, FormBorderStyle = FormBorderStyle.FixedDialog,
            MaximizeBox = false, MinimizeBox = false, AutoScaleMode = AutoScaleMode.Dpi })
        {
            var title = new Label { Text = Product, Left = 24, Top = 22, Width = 440, Height = 24 };
            var status = new Label { Text = "为当前用户安装麦来。安装包已包含程序和语音模型。",
                Left = 24, Top = 58, Width = 445, Height = 36 };
            var desktop = new CheckBox { Text = "创建桌面快捷方式", Checked = true,
                Left = 24, Top = 101, Width = 260 };
            var progress = new ProgressBar { Left = 24, Top = 137, Width = 445, Visible = false,
                Style = ProgressBarStyle.Marquee };
            var install = new Button { Text = "安装", Left = 364, Top = 170, Width = 105 };
            form.Controls.AddRange(new Control[] { title, status, desktop, progress, install });
            form.AcceptButton = install;
            bool busy = false;
            form.FormClosing += (sender, e) => { if (busy) e.Cancel = true; };
            install.Click += async (sender, e) =>
            {
                busy = true;
                install.Enabled = desktop.Enabled = false;
                progress.Visible = true;
                status.Text = "正在解压程序和模型，请稍候…";
                bool createDesktop = desktop.Checked;
                bool complete = false;
                try
                {
                    await System.Threading.Tasks.Task.Run(() => Install(createDesktop));
                    complete = true;
                }
                catch (Exception error) { status.Text = error.Message; }
                finally
                {
                    busy = false;
                    progress.Visible = false;
                    install.Enabled = desktop.Enabled = true;
                }
                if (complete)
                {
                    if (MessageBox.Show(form, "安装完成。现在打开麦来？", Product,
                        MessageBoxButtons.YesNo, MessageBoxIcon.Information) == DialogResult.Yes)
                        Process.Start(Launcher());
                    form.Close();
                }
            };
            Application.Run(form);
        }
    }

    private static string Launcher() { return Path.Combine(DirectoryPath, "麦来.exe"); }

    private static void RequireClosed()
    {
        foreach (var process in Process.GetProcessesByName("pythonw"))
        {
            using (process)
            {
                string executable;
                try { executable = process.MainModule.FileName; }
                catch (System.ComponentModel.Win32Exception) { continue; }
                catch (InvalidOperationException) { continue; }
                if (executable.StartsWith(DirectoryPath + Path.DirectorySeparatorChar,
                    StringComparison.OrdinalIgnoreCase))
                    throw new InvalidOperationException("请从系统托盘退出麦来，再继续。");
            }
        }
    }

    private static void Install(bool desktop)
    {
        RequireClosed();
        string staging = DirectoryPath + ".new-" + Guid.NewGuid();
        string backup = DirectoryPath + ".old-" + Guid.NewGuid();
        bool replaced = false;
        try
        {
            Directory.CreateDirectory(staging);
            Extract(staging);
            if (Directory.Exists(DirectoryPath))
            {
                if (!File.Exists(Path.Combine(DirectoryPath, "YapDash-Uninstall.exe")))
                    throw new IOException("默认安装目录已存在，且无法确认它是麦来的安装目录。");
                Directory.Move(DirectoryPath, backup);
            }
            Directory.Move(staging, DirectoryPath);
            replaced = true;
            MakeShortcut(StartLink, Launcher());
            if (desktop) MakeShortcut(DesktopLink, Launcher());
            using (var key = Registry.CurrentUser.CreateSubKey(RegistryPath))
            {
                key.SetValue("DisplayName", Product);
                key.SetValue("DisplayIcon", Launcher());
                key.SetValue("InstallLocation", DirectoryPath);
                key.SetValue("UninstallString", "\"" + Path.Combine(DirectoryPath, "YapDash-Uninstall.exe") + "\"");
            }
        }
        catch
        {
            if (replaced) Directory.Delete(DirectoryPath, true);
            if (Directory.Exists(backup)) Directory.Move(backup, DirectoryPath);
            throw;
        }
        finally { if (Directory.Exists(staging)) Directory.Delete(staging, true); }
        if (Directory.Exists(backup)) Directory.Delete(backup, true);
    }

    private static void Uninstall()
    {
        if (!String.Equals(Path.GetDirectoryName(Application.ExecutablePath), DirectoryPath,
            StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("请从 Windows「已安装的应用」中卸载麦来。");
        if (MessageBox.Show("卸载麦来？你的词库和设置会保留。", Product, MessageBoxButtons.YesNo,
            MessageBoxIcon.Question) != DialogResult.Yes) return;
        RequireClosed();
        string self = Application.ExecutablePath;
        foreach (string directory in Directory.GetDirectories(DirectoryPath)) Directory.Delete(directory, true);
        foreach (string file in Directory.GetFiles(DirectoryPath))
            if (!String.Equals(file, self, StringComparison.OrdinalIgnoreCase)) File.Delete(file);
        File.Delete(StartLink);
        File.Delete(DesktopLink);
        Registry.CurrentUser.DeleteSubKeyTree(RegistryPath, false);
        var info = new ProcessStartInfo(Path.Combine(Environment.SystemDirectory, "cmd.exe"),
            "/d /c ping -n 3 127.0.0.1 >nul & del /q \"" + self + "\" & rd \"" + DirectoryPath + "\"");
        info.CreateNoWindow = true;
        info.UseShellExecute = false;
        Process.Start(info);
    }
}
