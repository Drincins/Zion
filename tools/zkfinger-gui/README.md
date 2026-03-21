# ZionScan

Desktop app for ZKFinger enrollment and identification.

- GUI can stay in the background.
- Local agent stays running for web login.
- When you click Enroll or Identify, GUI stops the agent, scans, then starts the agent again.
- GUI shows a fingerprint preview during capture.

## Build (no Visual Studio)

```
$framework = "C:\\Windows\\Microsoft.NET\\Framework\\v4.0.30319"
$lib = "C:\\Users\\Admin\\Desktop\\Zion\\ZKFingerSDK_Windows_Standard\\ZKFinger Standard SDK 5.3.0.33\\C#\\lib\\x86\\libzkfpcsharp.dll"
$outDir = "C:\\Users\\Admin\\Desktop\\Zion\\tools\\zkfinger-gui\\bin"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
& "$framework\\csc.exe" /nologo /platform:x86 /target:winexe /out:"$outDir\\ZionScan.exe" `
  /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.Web.Extensions.dll /r:"$lib" `
  "C:\\Users\\Admin\\Desktop\\Zion\\tools\\zkfinger-gui\\Program.cs"
Copy-Item "$lib" "$outDir\\" -Force
```

## Run

```
tools\\zkfinger-gui\\bin\\ZionScan.exe
```

## Fingerprint slots

- Max 3 fingerprints per staff code (slots 1-3).
- Select the slot in the UI before enrollment.
- Re-enrolling the same slot overwrites it.

## Templates storage

Shared for GUI + agent:

```
%LOCALAPPDATA%\\ZKFinger\\templates.json
```

Override with:

```
FINGERPRINT_TEMPLATES_PATH
```

## Server sync (optional)

- URL is read from `FINGERPRINT_SERVER_URL`, `VITE_SERVER_URL`, or `.env`.
- Token can be filled from `FINGERPRINT_SYNC_TOKEN`.
- Dataset can be set via `FINGERPRINT_DATASET` (default: `default`).
- Auto sync runs at 07:00 and after enrollment; no UI fields.
