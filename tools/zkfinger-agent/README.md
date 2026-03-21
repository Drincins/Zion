# ZKFinger local agent

Local HTTP agent that talks to the ZKFinger SDK over USB and returns staff_code
to the web UI. Templates are stored locally on the workstation.

## Build

1) Install the ZKFinger SDK and confirm the demo works.
2) Open `tools/zkfinger-agent/ZkFingerAgent.csproj` in Visual Studio.
3) Build x86 (Release).

If the SDK is in a different folder, update the HintPath in
`tools/zkfinger-agent/ZkFingerAgent.csproj` to point to `libzkfpcsharp.dll`.

## Run

```
tools\zkfinger-agent\bin\ZkFingerAgent.exe
```

Default URL: `http://127.0.0.1:47123/`

If you need a custom URL/port:

```
ZkFingerAgent.exe http://127.0.0.1:47123/
```

## API

- GET `/status`
- POST `/identify`
- POST `/enroll` with JSON `{ staff_code: "00001", slot: 1 }`
- POST `/shutdown`

## Fingerprint slots

- Max 3 fingerprints per staff code (slots 1-3).
- If `slot` is omitted or 0, the agent uses the first free slot.

## Templates storage

```
%LOCALAPPDATA%\ZKFinger\templates.json
```

Override with `FINGERPRINT_TEMPLATES_PATH`.

## Notes

- If HttpListener returns access denied, run the agent once as admin or
  reserve the URL with `netsh http add urlacl`.
- The web UI can read the agent URL from `VITE_FINGER_AGENT_URL`.
