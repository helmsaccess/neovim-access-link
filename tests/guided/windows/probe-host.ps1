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

[ordered]@{
    os = [Environment]::OSVersion.Version.ToString()
    session = (Get-Process -Id $PID).SessionId
    inputDesktop = [GuidedHostProbe]::InputDesktop()
    renderEndpoint = [GuidedHostProbe]::DefaultRenderEndpoint()
    workspaceFreeGiB = [Math]::Round((Get-Item .).PSDrive.Free / 1GB, 1)
} | ConvertTo-Json
