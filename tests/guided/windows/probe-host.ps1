$ErrorActionPreference = 'Stop'

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class GuidedHostProbe {
    [DllImport("user32.dll", SetLastError = true)]
    static extern IntPtr OpenInputDesktop(uint flags, bool inherit, uint access);
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    static extern bool GetUserObjectInformation(IntPtr handle, int index,
        StringBuilder value, int size, out int needed);
    [DllImport("user32.dll")]
    static extern bool CloseDesktop(IntPtr handle);
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"),
     InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDeviceEnumerator {
        [PreserveSig] int EnumAudioEndpoints(int flow, int mask, out IntPtr devices);
        [PreserveSig] int GetDefaultAudioEndpoint(int flow, int role, out IntPtr endpoint);
    }

    public static string InputDesktop() {
        var desktop = OpenInputDesktop(0, false, 1);
        if (desktop == IntPtr.Zero) return "Win32 error " + Marshal.GetLastWin32Error();
        try {
            var value = new StringBuilder(128);
            int needed;
            if (GetUserObjectInformation(desktop, 2, value, 256, out needed))
                return value.ToString();
            return "Win32 error " + Marshal.GetLastWin32Error();
        } finally { CloseDesktop(desktop); }
    }

    public static string DefaultRenderEndpoint() {
        try {
            var type = Type.GetTypeFromCLSID(new Guid("BCDE0395-E52F-467C-8E3D-C4579291692E"));
            var devices = (IMMDeviceEnumerator)Activator.CreateInstance(type);
            try {
                IntPtr endpoint;
                int result = devices.GetDefaultAudioEndpoint(0, 1, out endpoint);
                if (endpoint != IntPtr.Zero) Marshal.Release(endpoint);
                return result == 0 ? "available" : String.Format("HRESULT 0x{0:X8}", result);
            } finally { Marshal.ReleaseComObject(devices); }
        } catch (COMException error) {
            return String.Format("HRESULT 0x{0:X8}", error.HResult);
        }
    }
}
'@

$desktop = [GuidedHostProbe]::InputDesktop()
$keyboardProbe = 'not attempted without the default input desktop'
if ($desktop -eq 'Default') {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    $form = [System.Windows.Forms.Form]::new()
    $form.Text = 'Guided runner keyboard probe'
    $form.TopMost = $true
    $inputField = [System.Windows.Forms.TextBox]::new()
    $form.Controls.Add($inputField)
    $timer = [System.Windows.Forms.Timer]::new()
    $timer.Interval = 500
    $evidence = @{ Result = 'foreground or keyboard input was not confirmed' }
    $timer.Add_Tick({
        $timer.Stop()
        try {
            if ([GuidedHostProbe]::GetForegroundWindow() -eq $form.Handle -and $inputField.Focused) {
                [System.Windows.Forms.SendKeys]::SendWait('nalprobe')
                if ($inputField.Text -ceq 'nalprobe') {
                    $evidence.Result = 'foreground and keyboard input confirmed'
                }
            }
        } finally {
            $form.Close()
        }
    })
    $form.Add_Shown({
        $form.Activate()
        [void]$inputField.Focus()
        $timer.Start()
    })
    try {
        [void]$form.ShowDialog()
        $keyboardProbe = $evidence.Result
    } finally {
        $timer.Dispose()
        $form.Dispose()
    }
}

[ordered]@{
    os = [Environment]::OSVersion.Version.ToString()
    session = (Get-Process -Id $PID).SessionId
    inputDesktop = $desktop
    foregroundKeyboard = $keyboardProbe
    windowsTerminalCommand = [bool](Get-Command wt.exe -ErrorAction SilentlyContinue)
    renderEndpoint = [GuidedHostProbe]::DefaultRenderEndpoint()
    workspaceFreeGiB = [Math]::Round((Get-Item .).PSDrive.Free / 1GB, 1)
} | ConvertTo-Json
