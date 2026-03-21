using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;
using libzkfpcsharp;

namespace ZkFingerAgent
{
    internal static class Program
    {
        private const string DefaultUrl = "http://127.0.0.1:47123/";

        private static int Main(string[] args)
        {
            string url = args.Length > 0 ? args[0] : DefaultUrl;
            string dataPath = ResolveTemplatesPath();
            TryMigrateTemplates(ResolveLegacyTemplatesPath(), dataPath);

            var store = new TemplateStore(dataPath);
            using (var device = new FingerDevice(store))
            {
                if (!device.Initialize())
                {
                    Console.WriteLine("Device init failed: " + device.LastError);
                    return 1;
                }

                using (var server = new HttpServer(device, url))
                {
                    Console.WriteLine("ZKFinger agent listening on " + url);
                    Console.WriteLine("Press Ctrl+C to stop.");

                    Console.CancelKeyPress += (sender, e) =>
                    {
                        e.Cancel = true;
                        server.Stop();
                    };

                    server.Start();
                }
            }

            return 0;
        }

        private static string ResolveLegacyTemplatesPath()
        {
            return Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "data", "templates.json");
        }

        private static string ResolveTemplatesPath()
        {
            string overridePath = Environment.GetEnvironmentVariable("FINGERPRINT_TEMPLATES_PATH");
            if (!string.IsNullOrEmpty(overridePath))
            {
                return overridePath.Trim();
            }

            string baseDir = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (!string.IsNullOrEmpty(baseDir))
            {
                return Path.Combine(baseDir, "ZKFinger", "templates.json");
            }

            return Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "data", "templates.json");
        }

        private static void TryMigrateTemplates(string legacyPath, string targetPath)
        {
            if (string.IsNullOrEmpty(legacyPath) || string.IsNullOrEmpty(targetPath))
            {
                return;
            }

            if (File.Exists(targetPath) || !File.Exists(legacyPath))
            {
                return;
            }

            string dir = Path.GetDirectoryName(targetPath);
            if (!string.IsNullOrEmpty(dir))
            {
                Directory.CreateDirectory(dir);
            }

            File.Copy(legacyPath, targetPath, true);
        }
    }

    internal sealed class HttpServer : IDisposable
    {
        private readonly HttpListener _listener;
        private readonly FingerDevice _device;
        private readonly JavaScriptSerializer _json;
        private bool _running;
        private const string IndexHtml = @"<!doctype html>
<html>
<head>
  <meta charset=""utf-8"">
  <title>ZKFinger Agent</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 32px; color: #222; }
    .card { max-width: 520px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 24px; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
    h1 { font-size: 20px; margin: 0 0 8px; }
    .status { font-size: 14px; color: #444; margin-bottom: 16px; }
    label { display: block; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; color: #555; }
    input, select { width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid #ccc; font-size: 16px; box-sizing: border-box; }
    .actions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
    button { border: none; padding: 10px 14px; border-radius: 8px; cursor: pointer; font-size: 14px; }
    .primary { background: #2f6bff; color: #fff; }
    .secondary { background: #f0f2f7; color: #222; }
    pre { background: #111; color: #b6f7c1; padding: 12px; border-radius: 8px; height: 180px; overflow: auto; font-size: 12px; margin-top: 16px; }
  </style>
</head>
<body>
  <div class=""card"">
    <h1>ZKFinger Agent</h1>
    <div id=""status"" class=""status"">Loading status...</div>
    <label for=""staffCode"">Staff code</label>
    <input id=""staffCode"" placeholder=""e.g. 00001"" />
    <label for=""slot"">Fingerprint slot</label>
    <select id=""slot"">
      <option value=""auto"">Auto</option>
      <option value=""1"">1</option>
      <option value=""2"">2</option>
      <option value=""3"">3</option>
    </select>
    <div class=""actions"">
      <button id=""enroll"" class=""primary"">Enroll (3 scans)</button>
      <button id=""identify"" class=""secondary"">Identify</button>
      <button id=""refresh"" class=""secondary"">Refresh status</button>
    </div>
    <pre id=""log"">Ready.</pre>
  </div>
  <script>
    const logEl = document.getElementById('log');
    const statusEl = document.getElementById('status');
    const staffInput = document.getElementById('staffCode');

    function log(msg) {
      const ts = new Date().toISOString().slice(11, 19);
      logEl.textContent = `[${ts}] ${msg}\\n` + logEl.textContent;
    }

    function setStatus(data) {
      if (!data || !data.ok) {
        statusEl.textContent = 'Status: error';
        return;
      }
      statusEl.textContent = `Status: ready=${data.device_ready}, templates=${data.templates}`;
    }

    async function fetchStatus() {
      try {
        const resp = await fetch('/status');
        const data = await resp.json();
        setStatus(data);
      } catch (err) {
        statusEl.textContent = 'Status: connection error';
      }
    }

    async function post(path, body) {
      const resp = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
      });
      return resp.json();
    }

    document.getElementById('enroll').addEventListener('click', async () => {
      const staffCode = (staffInput.value || '').trim();
      if (!staffCode) {
        log('Staff code is required.');
        return;
      }
      const slotValue = document.getElementById('slot').value;
      const payload = { staff_code: staffCode };
      if (slotValue !== 'auto') {
        payload.slot = Number(slotValue);
      }
      log('Enrollment started. Scan the same finger 3 times.');
      const result = await post('/enroll', payload);
      log(JSON.stringify(result));
      fetchStatus();
    });

    document.getElementById('identify').addEventListener('click', async () => {
      log('Identify started. Place a finger on the scanner.');
      const result = await post('/identify');
      log(JSON.stringify(result));
      if (result && result.staff_code) {
        staffInput.value = result.staff_code;
      }
    });

    document.getElementById('refresh').addEventListener('click', fetchStatus);
    fetchStatus();
  </script>
</body>
</html>";

        public HttpServer(FingerDevice device, string urlPrefix)
        {
            _device = device;
            _listener = new HttpListener();
            _listener.Prefixes.Add(urlPrefix);
            _json = new JavaScriptSerializer { MaxJsonLength = int.MaxValue };
        }

        public void Start()
        {
            _listener.Start();
            _running = true;
            while (_running)
            {
                HttpListenerContext context;
                try
                {
                    context = _listener.GetContext();
                }
                catch (HttpListenerException)
                {
                    break;
                }
                catch (ObjectDisposedException)
                {
                    break;
                }

                HandleRequest(context);
            }
        }

        public void Stop()
        {
            _running = false;
            if (_listener.IsListening)
            {
                _listener.Stop();
            }
        }

        private void HandleRequest(HttpListenerContext context)
        {
            var request = context.Request;
            var response = context.Response;

            if (string.Equals(request.HttpMethod, "OPTIONS", StringComparison.OrdinalIgnoreCase))
            {
                ApplyCors(response);
                response.StatusCode = 204;
                response.Close();
                return;
            }

            string path = string.Empty;
            if (request.Url != null)
            {
                string rawPath = request.Url.AbsolutePath;
                if (!string.IsNullOrEmpty(rawPath))
                {
                    path = rawPath.TrimEnd('/').ToLowerInvariant();
                }
            }
            try
            {
                if ((path == string.Empty || path == "/") && request.HttpMethod == "GET")
                {
                    WriteHtml(response, IndexHtml);
                    return;
                }

                if (path == "/status" && request.HttpMethod == "GET")
                {
                    WriteJson(response, 200, _device.GetStatus());
                    return;
                }

                if (path == "/identify" && request.HttpMethod == "POST")
                {
                    WriteJson(response, 200, _device.Identify());
                    return;
                }

                if (path == "/enroll" && request.HttpMethod == "POST")
                {
                    var payload = ReadJson<EnrollRequest>(request);
                    string staffCode = null;
                    int slot = 0;
                    if (payload != null)
                    {
                        staffCode = payload.staff_code;
                        slot = payload.slot ?? 0;
                    }
                    WriteJson(response, 200, _device.Enroll(staffCode, slot));
                    return;
                }

                if (path == "/shutdown" && request.HttpMethod == "POST")
                {
                    var payload = new Dictionary<string, object>();
                    payload.Add("ok", true);
                    WriteJson(response, 200, payload);
                    ThreadPool.QueueUserWorkItem(_ =>
                    {
                        Thread.Sleep(200);
                        Stop();
                    });
                    return;
                }

                var errorPayload = new Dictionary<string, object>();
                errorPayload.Add("ok", false);
                errorPayload.Add("error", "not_found");
                WriteJson(response, 404, errorPayload);
            }
            catch (Exception ex)
            {
                var errorPayload = new Dictionary<string, object>();
                errorPayload.Add("ok", false);
                errorPayload.Add("error", "internal_error");
                errorPayload.Add("detail", ex.Message);
                WriteJson(response, 500, errorPayload);
            }
        }

        private T ReadJson<T>(HttpListenerRequest request) where T : class
        {
            if (!request.HasEntityBody)
            {
                return null;
            }

            using (var reader = new StreamReader(request.InputStream, request.ContentEncoding ?? Encoding.UTF8))
            {
                string body = reader.ReadToEnd();
                if (string.IsNullOrWhiteSpace(body))
                {
                    return null;
                }
                return _json.Deserialize<T>(body);
            }
        }

        private void WriteJson(HttpListenerResponse response, int statusCode, object payload)
        {
            ApplyCors(response);
            response.StatusCode = statusCode;
            response.ContentType = "application/json";

            string json = _json.Serialize(payload);
            byte[] buffer = Encoding.UTF8.GetBytes(json);
            response.ContentLength64 = buffer.Length;

            using (var output = response.OutputStream)
            {
                output.Write(buffer, 0, buffer.Length);
            }
        }

        private void WriteHtml(HttpListenerResponse response, string html)
        {
            ApplyCors(response);
            response.StatusCode = 200;
            response.ContentType = "text/html; charset=utf-8";
            byte[] buffer = Encoding.UTF8.GetBytes(html ?? string.Empty);
            response.ContentLength64 = buffer.Length;
            using (var output = response.OutputStream)
            {
                output.Write(buffer, 0, buffer.Length);
            }
        }

        private static void ApplyCors(HttpListenerResponse response)
        {
            response.Headers["Access-Control-Allow-Origin"] = "*";
            response.Headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS";
            response.Headers["Access-Control-Allow-Headers"] = "Content-Type, X-Fingerprint-Token";
            response.Headers["Access-Control-Allow-Private-Network"] = "true";
        }

        public void Dispose()
        {
            Stop();
            _listener.Close();
        }
    }

    internal sealed class EnrollRequest
    {
        public string staff_code { get; set; }
        public int? slot { get; set; }
    }

    internal sealed class FingerDevice : IDisposable
    {
        private const int CaptureTimeoutMs = 20000;
        private const int CapturePollDelayMs = 200;
        private static readonly Regex StaffCodeRegex = new Regex(@"^\d+$", RegexOptions.Compiled);
        private const int MaxFingerprintsPerStaff = TemplateStore.MaxFingerprintsPerStaff;

        private readonly object _operationLock = new object();
        private readonly TemplateStore _store;
        private IntPtr _devHandle = IntPtr.Zero;
        private IntPtr _dbHandle = IntPtr.Zero;
        private byte[] _fpBuffer;
        private byte[] _capTmp;
        private int _fpWidth;
        private int _fpHeight;

        public string LastError { get; private set; }

        public FingerDevice(TemplateStore store)
        {
            _store = store;
        }

        public bool Initialize()
        {
            int ret = zkfp2.Init();
            if (ret != zkfperrdef.ZKFP_ERR_OK)
            {
                LastError = "init_failed_" + ret;
                return false;
            }

            int count = zkfp2.GetDeviceCount();
            if (count <= 0)
            {
                LastError = "no_device";
                zkfp2.Terminate();
                return false;
            }

            _devHandle = zkfp2.OpenDevice(0);
            if (_devHandle == IntPtr.Zero)
            {
                LastError = "open_device_failed";
                zkfp2.Terminate();
                return false;
            }

            _dbHandle = zkfp2.DBInit();
            if (_dbHandle == IntPtr.Zero)
            {
                LastError = "db_init_failed";
                zkfp2.CloseDevice(_devHandle);
                _devHandle = IntPtr.Zero;
                zkfp2.Terminate();
                return false;
            }

            byte[] paramValue = new byte[4];
            int size = 4;
            zkfp2.GetParameters(_devHandle, 1, paramValue, ref size);
            zkfp2.ByteArray2Int(paramValue, ref _fpWidth);

            size = 4;
            zkfp2.GetParameters(_devHandle, 2, paramValue, ref size);
            zkfp2.ByteArray2Int(paramValue, ref _fpHeight);

            _fpBuffer = new byte[_fpWidth * _fpHeight];
            _capTmp = new byte[2048];

            LoadTemplates();
            return true;
        }

        public Dictionary<string, object> GetStatus()
        {
            var payload = new Dictionary<string, object>();
            payload.Add("ok", true);
            payload.Add("device_ready", _devHandle != IntPtr.Zero && _dbHandle != IntPtr.Zero);
            payload.Add("templates", _store.Records.Count);
            payload.Add("last_error", LastError ?? string.Empty);
            return payload;
        }

        public Dictionary<string, object> Identify()
        {
            if (_devHandle == IntPtr.Zero || _dbHandle == IntPtr.Zero)
            {
                return Fail("device_not_ready");
            }

            if (!Monitor.TryEnter(_operationLock))
            {
                return Fail("busy");
            }

            try
            {
                byte[] template;
                string error;
                if (!TryCapture(out template, out error))
                {
                    return Fail(error);
                }

                int fid = 0;
                int score = 0;
                int ret = zkfp2.DBIdentify(_dbHandle, template, ref fid, ref score);
                if (ret != zkfperrdef.ZKFP_ERR_OK)
                {
                    return Fail("no_match");
                }

                TemplateRecord record = _store.FindByFid(fid);
                if (record == null || string.IsNullOrWhiteSpace(record.staff_code))
                {
                    return Fail("unknown_fid");
                }

                var payload = new Dictionary<string, object>();
                payload.Add("ok", true);
                payload.Add("staff_code", record.staff_code);
                payload.Add("fid", fid);
                payload.Add("score", score);
                payload.Add("slot", record.slot);
                return payload;
            }
            finally
            {
                Monitor.Exit(_operationLock);
            }
        }

        public Dictionary<string, object> Enroll(string staffCode, int slot)
        {
            if (_devHandle == IntPtr.Zero || _dbHandle == IntPtr.Zero)
            {
                return Fail("device_not_ready");
            }

            if (string.IsNullOrWhiteSpace(staffCode))
            {
                return Fail("staff_code_required");
            }

            staffCode = staffCode.Trim();
            if (!StaffCodeRegex.IsMatch(staffCode))
            {
                return Fail("staff_code_invalid");
            }

            if (slot < 0 || slot > MaxFingerprintsPerStaff)
            {
                return Fail("slot_invalid");
            }

            if (!Monitor.TryEnter(_operationLock))
            {
                return Fail("busy");
            }

            try
            {
                int resolvedSlot = slot;
                if (resolvedSlot <= 0)
                {
                    resolvedSlot = FindFirstFreeSlot(staffCode);
                    if (resolvedSlot <= 0)
                    {
                        return Fail("staff_code_limit_reached");
                    }
                }

                TemplateRecord existing = _store.FindByStaffCodeAndSlot(staffCode, resolvedSlot);
                int currentCount = _store.FindAllByStaffCode(staffCode).Count;
                if (existing != null)
                {
                    TryDeleteTemplate(existing.fid);
                    _store.Records.Remove(existing);
                    currentCount = Math.Max(0, currentCount - 1);
                }
                else if (currentCount >= MaxFingerprintsPerStaff)
                {
                    return Fail("staff_code_limit_reached");
                }

                int fid = existing != null ? existing.fid : _store.GetNextFid();

                var samples = new List<byte[]>();
                for (int i = 0; i < 3; i++)
                {
                    byte[] template;
                    string error;
                    if (!TryCapture(out template, out error))
                    {
                        return Fail(error);
                    }

                    int foundFid = 0;
                    int score = 0;
                    int identifyRet = zkfp2.DBIdentify(_dbHandle, template, ref foundFid, ref score);
                    if (identifyRet == zkfperrdef.ZKFP_ERR_OK)
                    {
                        return Fail("fingerprint_already_enrolled");
                    }

                    if (samples.Count > 0)
                    {
                        int match = zkfp2.DBMatch(_dbHandle, template, samples[samples.Count - 1]);
                        if (match <= 0)
                        {
                            return Fail("finger_mismatch");
                        }
                    }

                    samples.Add(template);
                }

                byte[] regTmp = new byte[2048];
                int regLen = 0;
                int mergeRet = zkfp2.DBMerge(_dbHandle, samples[0], samples[1], samples[2], regTmp, ref regLen);
                if (mergeRet != zkfperrdef.ZKFP_ERR_OK)
                {
                    return Fail("merge_failed");
                }

                TryDeleteTemplate(fid);
                int addRet = zkfp2.DBAdd(_dbHandle, fid, regTmp);
                if (addRet != zkfperrdef.ZKFP_ERR_OK)
                {
                    return Fail("db_add_failed");
                }

                var record = new TemplateRecord
                {
                    fid = fid,
                    staff_code = staffCode,
                    template_base64 = Convert.ToBase64String(regTmp),
                    slot = resolvedSlot,
                };
                _store.Records.Add(record);
                _store.Save();

                var payload = new Dictionary<string, object>();
                payload.Add("ok", true);
                payload.Add("staff_code", staffCode);
                payload.Add("fid", fid);
                payload.Add("slot", resolvedSlot);
                return payload;
            }
            finally
            {
                Monitor.Exit(_operationLock);
            }
        }

        private void LoadTemplates()
        {
            _store.Load();
            foreach (var record in _store.Records)
            {
                if (record == null || string.IsNullOrWhiteSpace(record.template_base64))
                {
                    continue;
                }

                byte[] template;
                try
                {
                    template = Convert.FromBase64String(record.template_base64);
                }
                catch (FormatException)
                {
                    continue;
                }

                int ret = zkfp2.DBAdd(_dbHandle, record.fid, template);
                if (ret != zkfperrdef.ZKFP_ERR_OK)
                {
                    LastError = "db_add_failed_" + ret;
                }
            }
        }

        private bool TryCapture(out byte[] template, out string error)
        {
            var sw = Stopwatch.StartNew();
            while (sw.ElapsedMilliseconds < CaptureTimeoutMs)
            {
                int cbCapTmp = _capTmp.Length;
                int ret = zkfp2.AcquireFingerprint(_devHandle, _fpBuffer, _capTmp, ref cbCapTmp);
                if (ret == zkfperrdef.ZKFP_ERR_OK)
                {
                    template = new byte[_capTmp.Length];
                    Buffer.BlockCopy(_capTmp, 0, template, 0, _capTmp.Length);
                    error = null;
                    return true;
                }
                Thread.Sleep(CapturePollDelayMs);
            }

            template = null;
            error = "capture_timeout";
            return false;
        }

        private int FindFirstFreeSlot(string staffCode)
        {
            var records = _store.FindAllByStaffCode(staffCode);
            var used = new HashSet<int>();
            foreach (var record in records)
            {
                if (record != null && record.slot > 0)
                {
                    used.Add(record.slot);
                }
            }

            for (int slot = 1; slot <= MaxFingerprintsPerStaff; slot++)
            {
                if (!used.Contains(slot))
                {
                    return slot;
                }
            }

            return 0;
        }

        private void TryDeleteTemplate(int fid)
        {
            try
            {
                zkfp2.DBDel(_dbHandle, fid);
            }
            catch
            {
                // ignore if SDK does not support delete
            }
        }

        private static Dictionary<string, object> Fail(string error)
        {
            var payload = new Dictionary<string, object>();
            payload.Add("ok", false);
            payload.Add("error", error);
            return payload;
        }

        public void Dispose()
        {
            if (_dbHandle != IntPtr.Zero)
            {
                try
                {
                    zkfp2.DBFree(_dbHandle);
                }
                catch
                {
                    // ignore
                }
                _dbHandle = IntPtr.Zero;
            }

            if (_devHandle != IntPtr.Zero)
            {
                zkfp2.CloseDevice(_devHandle);
                _devHandle = IntPtr.Zero;
            }

            zkfp2.Terminate();
        }
    }

    internal sealed class TemplateStore
    {
        private static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = int.MaxValue };
        private readonly string _path;
        public const int MaxFingerprintsPerStaff = 3;

        public List<TemplateRecord> Records { get; private set; }

        public TemplateStore(string path)
        {
            _path = path;
            Records = new List<TemplateRecord>();
        }

        public void Load()
        {
            if (!File.Exists(_path))
            {
                Records = new List<TemplateRecord>();
                return;
            }

            string json = File.ReadAllText(_path, Encoding.UTF8);
            if (string.IsNullOrWhiteSpace(json))
            {
                Records = new List<TemplateRecord>();
                return;
            }

            try
            {
                var records = Json.Deserialize<List<TemplateRecord>>(json);
                Records = records ?? new List<TemplateRecord>();
                NormalizeSlots();
            }
            catch
            {
                Records = new List<TemplateRecord>();
            }
        }

        public void Save()
        {
            string dir = Path.GetDirectoryName(_path);
            if (!string.IsNullOrWhiteSpace(dir))
            {
                Directory.CreateDirectory(dir);
            }

            string json = Json.Serialize(Records);
            File.WriteAllText(_path, json, Encoding.UTF8);
        }

        private void NormalizeSlots()
        {
            foreach (var record in Records)
            {
                if (record == null)
                {
                    continue;
                }

                if (record.slot <= 0)
                {
                    record.slot = 1;
                }
            }
        }

        public int GetNextFid()
        {
            int max = -1;
            foreach (var record in Records)
            {
                if (record != null && record.fid > max)
                {
                    max = record.fid;
                }
            }

            return max >= 0 ? max + 1 : 1;
        }

        public List<TemplateRecord> FindAllByStaffCode(string staffCode)
        {
            if (string.IsNullOrEmpty(staffCode))
            {
                return new List<TemplateRecord>();
            }

            return Records.FindAll(record =>
                record != null &&
                string.Equals(record.staff_code, staffCode, StringComparison.OrdinalIgnoreCase));
        }

        public TemplateRecord FindByStaffCodeAndSlot(string staffCode, int slot)
        {
            return Records.Find(record =>
                record != null &&
                record.slot == slot &&
                string.Equals(record.staff_code, staffCode, StringComparison.OrdinalIgnoreCase));
        }

        public TemplateRecord FindByFid(int fid)
        {
            return Records.Find(record => record.fid == fid);
        }

        public TemplateRecord FindByStaffCode(string staffCode)
        {
            return Records.Find(record =>
                string.Equals(record.staff_code, staffCode, StringComparison.OrdinalIgnoreCase));
        }
    }

    internal sealed class TemplateRecord
    {
        public int fid { get; set; }
        public string staff_code { get; set; }
        public int slot { get; set; }
        public string template_base64 { get; set; }
    }
}
