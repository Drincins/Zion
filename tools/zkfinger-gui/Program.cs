using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Net;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using libzkfpcsharp;

namespace ZkFingerGui
{
    internal static class Program
    {
        [STAThread]
        private static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }
    }

    internal sealed class MainForm : Form
    {
        private readonly TemplateStore _store;
        private FingerDevice _device;
        private readonly SettingsStore _settings;
        private readonly TextBox _staffCodeText;
        private readonly ComboBox _slotCombo;
        private readonly Label _employeeNameLabel;
        private readonly Button _enrollButton;
        private readonly Button _identifyButton;
        private readonly Button _refreshButton;
        private readonly Label _deviceLabel;
        private readonly Label _infoLabel;
        private readonly TextBox _logText;
        private readonly Label _dbPathLabel;
        private readonly Label _dbCountLabel;
        private readonly Label _dbUpdatedLabel;
        private readonly Label _lastExportLabel;
        private readonly Label _lastImportLabel;
        private readonly Label _nextSyncLabel;
        private readonly NumericUpDown _syncIntervalInput;
        private readonly DataGridView _fingerprintsGrid;
        private readonly CheckBox _loadNamesCheck;
        private readonly Label _fingerprintsSummaryLabel;
        private readonly PictureBox _fingerPreview;
        private readonly System.Threading.Timer _dailySyncTimer;
        private readonly object _autoExportLock = new object();
        private readonly object _staffNameLock = new object();
        private readonly Dictionary<string, string> _staffNameCache = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        private const string AgentBaseUrl = "http://127.0.0.1:47123/";
        private readonly System.Windows.Forms.Timer _lookupTimer;
        private readonly string _serverUrl;
        private readonly string _serverToken;
        private readonly string _dataset;
        private const string DefaultServerUrl = "http://a8oleg9696.fvds.ru";

        private bool _busy;
        private bool _deviceActive;
        private bool _autoExportRequested;
        private string _autoExportReason;
        private bool _lookupInProgress;
        private string _lastLookupCode;
        private DateTime? _lastExportAt;
        private DateTime? _lastImportAt;
        private DateTime? _nextSyncAt;
        private int _fingerprintsRefreshToken;
        private BindingList<StaffFingerprintRow> _fingerprintRows;

        public MainForm()
        {
            Text = "ZionScan";
            Font = new Font("Segoe UI", 10F, FontStyle.Regular, GraphicsUnit.Point);
            BackColor = Color.FromArgb(245, 245, 245);
            MinimumSize = new Size(720, 480);

            string settingsPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "settings.json");
            _settings = SettingsStore.Load(settingsPath);

            string dataPath = ResolveTemplatesPath();
            TryMigrateTemplates(ResolveLegacyTemplatesPath(), dataPath);
            _store = new TemplateStore(dataPath);
            _dailySyncTimer = new System.Threading.Timer(_ => OnDailySyncTimer(), null, Timeout.Infinite, Timeout.Infinite);

            string defaultServerUrl = ResolveDefaultServerUrl();
            _serverUrl = string.IsNullOrEmpty(defaultServerUrl)
                ? (string.IsNullOrEmpty(_settings.ServerUrl) ? DefaultServerUrl : _settings.ServerUrl)
                : defaultServerUrl;
            string defaultToken = ResolveDefaultToken();
            _serverToken = string.IsNullOrEmpty(defaultToken) ? (_settings.Token ?? string.Empty) : defaultToken;
            string defaultDataset = ResolveDefaultDataset();
            _dataset = string.IsNullOrEmpty(defaultDataset)
                ? (string.IsNullOrEmpty(_settings.Dataset) ? "default" : _settings.Dataset)
                : defaultDataset;
            int syncIntervalMinutes = _settings.SyncIntervalMinutes;
            if (syncIntervalMinutes < 0)
            {
                syncIntervalMinutes = 0;
            }
            if (syncIntervalMinutes > 10080)
            {
                syncIntervalMinutes = 10080;
            }

            _lookupTimer = new System.Windows.Forms.Timer
            {
                Interval = 500,
            };
            _lookupTimer.Tick += OnLookupTimerTick;

            var root = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                ColumnCount = 1,
                RowCount = 4,
                Padding = new Padding(24),
            };
            root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            root.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));
            root.RowStyles.Add(new RowStyle(SizeType.AutoSize));

            var title = new Label
            {
                Text = "ZionScan",
                Font = new Font("Segoe UI", 16F, FontStyle.Bold, GraphicsUnit.Point),
                AutoSize = true,
                ForeColor = Color.FromArgb(20, 20, 20),
            };

            _deviceLabel = new Label
            {
                Text = "Сканер: инициализация...",
                AutoSize = true,
                ForeColor = Color.FromArgb(80, 80, 80),
                Margin = new Padding(0, 4, 0, 16),
            };

            var content = new TableLayoutPanel
            {
                ColumnCount = 2,
                RowCount = 1,
                AutoSize = true,
                Dock = DockStyle.Top,
            };
            content.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 60F));
            content.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 40F));

            var leftPanel = new TableLayoutPanel
            {
                ColumnCount = 1,
                RowCount = 6,
                AutoSize = true,
                Dock = DockStyle.Fill,
            };
            leftPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            leftPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            leftPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            leftPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            leftPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            leftPanel.RowStyles.Add(new RowStyle(SizeType.AutoSize));

            var staffLabel = new Label
            {
                Text = "Код сотрудника",
                AutoSize = true,
                ForeColor = Color.FromArgb(90, 90, 90),
                Margin = new Padding(0, 0, 0, 4),
            };

            _staffCodeText = new TextBox
            {
                Width = 220,
                Font = new Font("Segoe UI", 12F, FontStyle.Regular, GraphicsUnit.Point),
            };
            _staffCodeText.TextChanged += OnStaffCodeChanged;

            _employeeNameLabel = new Label
            {
                Text = "Сотрудник: —",
                AutoSize = true,
                ForeColor = Color.FromArgb(110, 110, 110),
                Margin = new Padding(0, 4, 0, 12),
            };

            var slotLabel = new Label
            {
                Text = "Отпечаток №",
                AutoSize = true,
                ForeColor = Color.FromArgb(90, 90, 90),
                Margin = new Padding(0, 0, 0, 4),
            };

            _slotCombo = new ComboBox
            {
                Width = 120,
                DropDownStyle = ComboBoxStyle.DropDownList,
                Font = new Font("Segoe UI", 11F, FontStyle.Regular, GraphicsUnit.Point),
            };
            _slotCombo.Items.AddRange(new object[] { "1", "2", "3" });
            _slotCombo.SelectedIndex = 0;

            var actions = new FlowLayoutPanel
            {
                FlowDirection = FlowDirection.LeftToRight,
                AutoSize = true,
                Margin = new Padding(0, 16, 0, 0),
            };

            _enrollButton = new Button
            {
                Text = "Регистрация (3 скана)",
                BackColor = Color.FromArgb(47, 107, 255),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                AutoSize = true,
                Padding = new Padding(10, 6, 10, 6),
            };
            _enrollButton.FlatAppearance.BorderSize = 0;
            _enrollButton.Click += EnrollClicked;

            _identifyButton = new Button
            {
                Text = "Проверить",
                BackColor = Color.FromArgb(240, 242, 247),
                ForeColor = Color.FromArgb(30, 30, 30),
                FlatStyle = FlatStyle.Flat,
                AutoSize = true,
                Padding = new Padding(10, 6, 10, 6),
            };
            _identifyButton.FlatAppearance.BorderSize = 0;
            _identifyButton.Click += IdentifyClicked;

            _refreshButton = new Button
            {
                Text = "Обновить статус",
                BackColor = Color.FromArgb(240, 242, 247),
                ForeColor = Color.FromArgb(30, 30, 30),
                FlatStyle = FlatStyle.Flat,
                AutoSize = true,
                Padding = new Padding(10, 6, 10, 6),
            };
            _refreshButton.FlatAppearance.BorderSize = 0;
            _refreshButton.Click += RefreshClicked;

            actions.Controls.Add(_enrollButton);
            actions.Controls.Add(_identifyButton);
            actions.Controls.Add(_refreshButton);

            leftPanel.Controls.Add(staffLabel);
            leftPanel.Controls.Add(_staffCodeText);
            leftPanel.Controls.Add(_employeeNameLabel);
            leftPanel.Controls.Add(slotLabel);
            leftPanel.Controls.Add(_slotCombo);
            leftPanel.Controls.Add(actions);

            var previewGroup = new GroupBox
            {
                Text = "Отпечаток",
                AutoSize = true,
                Dock = DockStyle.Top,
                Padding = new Padding(12),
                Margin = new Padding(24, 0, 0, 0),
            };

            _fingerPreview = new PictureBox
            {
                Width = 180,
                Height = 220,
                SizeMode = PictureBoxSizeMode.Zoom,
                BorderStyle = BorderStyle.FixedSingle,
                BackColor = Color.White,
            };

            previewGroup.Controls.Add(_fingerPreview);

            content.Controls.Add(leftPanel, 0, 0);
            content.Controls.Add(previewGroup, 1, 0);

            var scanPanel = new Panel
            {
                Dock = DockStyle.Fill,
                AutoScroll = true,
            };
            scanPanel.Controls.Add(content);

            var tabControl = new TabControl
            {
                Dock = DockStyle.Fill,
            };

            var scanTab = new TabPage
            {
                Text = "Сканер",
                BackColor = BackColor,
            };
            scanTab.Controls.Add(scanPanel);

            var syncTab = new TabPage
            {
                Text = "Синхронизация",
                BackColor = BackColor,
                AutoScroll = true,
            };

            var syncRoot = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                ColumnCount = 1,
                RowCount = 3,
                Padding = new Padding(4),
            };
            syncRoot.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            syncRoot.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            syncRoot.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));

            var syncGroup = new GroupBox
            {
                Text = "Синхронизация",
                AutoSize = true,
                Dock = DockStyle.Top,
                Padding = new Padding(12),
            };

            var syncLayout = new TableLayoutPanel
            {
                ColumnCount = 1,
                RowCount = 3,
                AutoSize = true,
                Dock = DockStyle.Top,
            };

            var syncButtons = new FlowLayoutPanel
            {
                FlowDirection = FlowDirection.LeftToRight,
                AutoSize = true,
            };

            var exportButton = new Button
            {
                Text = "Отправить на сервер",
                BackColor = Color.FromArgb(47, 107, 255),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                AutoSize = true,
                Padding = new Padding(10, 6, 10, 6),
            };
            exportButton.FlatAppearance.BorderSize = 0;
            exportButton.Click += ExportClicked;

            var importButton = new Button
            {
                Text = "Скачать с сервера",
                BackColor = Color.FromArgb(240, 242, 247),
                ForeColor = Color.FromArgb(30, 30, 30),
                FlatStyle = FlatStyle.Flat,
                AutoSize = true,
                Padding = new Padding(10, 6, 10, 6),
            };
            importButton.FlatAppearance.BorderSize = 0;
            importButton.Click += ImportClicked;

            syncButtons.Controls.Add(exportButton);
            syncButtons.Controls.Add(importButton);

            var intervalPanel = new FlowLayoutPanel
            {
                FlowDirection = FlowDirection.LeftToRight,
                AutoSize = true,
                Margin = new Padding(0, 8, 0, 0),
            };

            var intervalLabel = new Label
            {
                Text = "Интервал синхронизации (мин)",
                AutoSize = true,
                ForeColor = Color.FromArgb(90, 90, 90),
                Margin = new Padding(0, 6, 6, 0),
            };

            _syncIntervalInput = new NumericUpDown
            {
                Minimum = 0,
                Maximum = 10080,
                Value = syncIntervalMinutes,
                Width = 90,
            };
            _syncIntervalInput.ValueChanged += OnSyncIntervalChanged;

            var intervalHint = new Label
            {
                Text = "0 = ежедневно в 07:00",
                AutoSize = true,
                ForeColor = Color.FromArgb(120, 120, 120),
                Margin = new Padding(6, 6, 0, 0),
            };

            intervalPanel.Controls.Add(intervalLabel);
            intervalPanel.Controls.Add(_syncIntervalInput);
            intervalPanel.Controls.Add(intervalHint);

            _nextSyncLabel = new Label
            {
                Text = "Следующая синхронизация: -",
                AutoSize = true,
                ForeColor = Color.FromArgb(90, 90, 90),
                Margin = new Padding(0, 8, 0, 0),
            };

            syncLayout.Controls.Add(syncButtons);
            syncLayout.Controls.Add(intervalPanel);
            syncLayout.Controls.Add(_nextSyncLabel);
            syncGroup.Controls.Add(syncLayout);

            var dbGroup = new GroupBox
            {
                Text = "База отпечатков",
                AutoSize = true,
                Dock = DockStyle.Top,
                Padding = new Padding(12),
                Margin = new Padding(0, 12, 0, 0),
            };

            var dbLayout = new TableLayoutPanel
            {
                ColumnCount = 1,
                RowCount = 5,
                AutoSize = true,
                Dock = DockStyle.Top,
            };

            _dbPathLabel = new Label
            {
                Text = "Файл базы: -",
                AutoSize = true,
                ForeColor = Color.FromArgb(90, 90, 90),
            };

            _dbCountLabel = new Label
            {
                Text = "Записей: 0",
                AutoSize = true,
                ForeColor = Color.FromArgb(90, 90, 90),
            };

            _dbUpdatedLabel = new Label
            {
                Text = "Последнее изменение: -",
                AutoSize = true,
                ForeColor = Color.FromArgb(90, 90, 90),
            };

            _lastExportLabel = new Label
            {
                Text = "Последняя отправка: -",
                AutoSize = true,
                ForeColor = Color.FromArgb(90, 90, 90),
            };

            _lastImportLabel = new Label
            {
                Text = "Последнее получение: -",
                AutoSize = true,
                ForeColor = Color.FromArgb(90, 90, 90),
            };

            dbLayout.Controls.Add(_dbPathLabel);
            dbLayout.Controls.Add(_dbCountLabel);
            dbLayout.Controls.Add(_dbUpdatedLabel);
            dbLayout.Controls.Add(_lastExportLabel);
            dbLayout.Controls.Add(_lastImportLabel);
            dbGroup.Controls.Add(dbLayout);

            var logGroup = new GroupBox
            {
                Text = "Логи",
                Dock = DockStyle.Fill,
                Padding = new Padding(12),
                Margin = new Padding(0, 12, 0, 0),
            };

            _logText = new TextBox
            {
                Multiline = true,
                ReadOnly = true,
                ScrollBars = ScrollBars.Vertical,
                Dock = DockStyle.Fill,
                BackColor = Color.White,
            };
            logGroup.Controls.Add(_logText);

            syncRoot.Controls.Add(syncGroup, 0, 0);
            syncRoot.Controls.Add(dbGroup, 0, 1);
            syncRoot.Controls.Add(logGroup, 0, 2);

            syncTab.Controls.Add(syncRoot);

            var dataTab = new TabPage
            {
                Text = "База отпечатков",
                BackColor = BackColor,
                AutoScroll = true,
            };

            var dataRoot = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                ColumnCount = 1,
                RowCount = 2,
                Padding = new Padding(4),
            };
            dataRoot.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            dataRoot.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));

            var dataHeader = new FlowLayoutPanel
            {
                FlowDirection = FlowDirection.LeftToRight,
                AutoSize = true,
            };

            var refreshDataButton = new Button
            {
                Text = "Обновить список",
                BackColor = Color.FromArgb(240, 242, 247),
                ForeColor = Color.FromArgb(30, 30, 30),
                FlatStyle = FlatStyle.Flat,
                AutoSize = true,
                Padding = new Padding(10, 6, 10, 6),
            };
            refreshDataButton.FlatAppearance.BorderSize = 0;
            refreshDataButton.Click += (sender, args) =>
                RefreshFingerprintGrid(_loadNamesCheck != null && _loadNamesCheck.Checked);

            _loadNamesCheck = new CheckBox
            {
                Text = "Подтягивать имена с сервера",
                AutoSize = true,
                Checked = true,
                Margin = new Padding(12, 6, 0, 0),
            };
            _loadNamesCheck.CheckedChanged += (sender, args) =>
                RefreshFingerprintGrid(_loadNamesCheck.Checked);

            _fingerprintsSummaryLabel = new Label
            {
                Text = "Сотрудников: 0",
                AutoSize = true,
                ForeColor = Color.FromArgb(90, 90, 90),
                Margin = new Padding(12, 8, 0, 0),
            };

            dataHeader.Controls.Add(refreshDataButton);
            dataHeader.Controls.Add(_loadNamesCheck);
            dataHeader.Controls.Add(_fingerprintsSummaryLabel);

            _fingerprintsGrid = new DataGridView
            {
                Dock = DockStyle.Fill,
                ReadOnly = true,
                AllowUserToAddRows = false,
                AllowUserToDeleteRows = false,
                AutoGenerateColumns = false,
                RowHeadersVisible = false,
                SelectionMode = DataGridViewSelectionMode.FullRowSelect,
                MultiSelect = false,
                BackgroundColor = Color.White,
                BorderStyle = BorderStyle.FixedSingle,
            };

            var codeColumn = new DataGridViewTextBoxColumn
            {
                HeaderText = "Код",
                DataPropertyName = "StaffCode",
                Width = 110,
            };

            var nameColumn = new DataGridViewTextBoxColumn
            {
                HeaderText = "Сотрудник",
                DataPropertyName = "StaffName",
                AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill,
            };

            var slot1Column = new DataGridViewCheckBoxColumn
            {
                HeaderText = "Отпечаток 1",
                DataPropertyName = "Slot1",
                Width = 110,
            };
            slot1Column.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter;

            var slot2Column = new DataGridViewCheckBoxColumn
            {
                HeaderText = "Отпечаток 2",
                DataPropertyName = "Slot2",
                Width = 110,
            };
            slot2Column.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter;

            var slot3Column = new DataGridViewCheckBoxColumn
            {
                HeaderText = "Отпечаток 3",
                DataPropertyName = "Slot3",
                Width = 110,
            };
            slot3Column.DefaultCellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter;

            _fingerprintsGrid.Columns.Add(codeColumn);
            _fingerprintsGrid.Columns.Add(nameColumn);
            _fingerprintsGrid.Columns.Add(slot1Column);
            _fingerprintsGrid.Columns.Add(slot2Column);
            _fingerprintsGrid.Columns.Add(slot3Column);

            dataRoot.Controls.Add(dataHeader, 0, 0);
            dataRoot.Controls.Add(_fingerprintsGrid, 0, 1);
            dataTab.Controls.Add(dataRoot);

            tabControl.TabPages.Add(scanTab);
            tabControl.TabPages.Add(syncTab);
            tabControl.TabPages.Add(dataTab);

            _infoLabel = new Label
            {
                AutoSize = true,
                ForeColor = Color.FromArgb(70, 70, 70),
                MaximumSize = new Size(640, 0),
                Text = "Готово к работе.",
                Margin = new Padding(0, 16, 0, 0),
            };

            root.Controls.Add(title);
            root.Controls.Add(_deviceLabel);
            root.Controls.Add(tabControl);
            root.Controls.Add(_infoLabel);

            Controls.Add(root);

            Load += OnLoad;
            FormClosed += OnClosed;
        }

        private async void OnLoad(object sender, EventArgs e)
        {
            SetStatus("Проверка агента...");
            await StartAgentIfNotRunningAsync();
            UpdateDeviceStatus();
            Debug.WriteLine("Файл базы: " + _store.FilePath);
            _store.Load();
            UpdateDatabaseStatus();
            RefreshFingerprintGrid(_loadNamesCheck != null && _loadNamesCheck.Checked);
            ScheduleAutoSync(true);
            SetStatus("Ожидание");
            SetInfo("Готово к работе.");
        }

        private void OnClosed(object sender, FormClosedEventArgs e)
        {
            _dailySyncTimer.Dispose();
            _lookupTimer.Stop();
            SafeDisposeDevice();
            _deviceActive = false;
            StopAgentOnExit();
        }

        private async void EnrollClicked(object sender, EventArgs e)
        {
            string staffCode = (_staffCodeText.Text ?? string.Empty).Trim();
            if (string.IsNullOrEmpty(staffCode))
            {
                Log("Введите код сотрудника.");
                return;
            }

            if (_busy)
            {
                Log("Сканер занят.");
                return;
            }

            SetBusy(true);
            if (!await StartScannerSessionAsync())
            {
                SetBusy(false);
                SetStatus("Ожидание");
                return;
            }

            int slot = GetSelectedSlot();
            SetStatus("Регистрация началась. Приложите один и тот же палец 3 раза.");
            SetInfo(string.Format("Регистрация отпечатка №{0}. Приложите палец 3 раза.", slot));

            FingerResult result = await Task.Run(() =>
                _device.Enroll(staffCode, slot, message => SafeUi(() =>
                {
                    SetStatus(message);
                    SetInfo(message);
                })));

            HandleResult(result);
            await EndScannerSessionAsync();
            SetBusy(false);
        }

        private async void IdentifyClicked(object sender, EventArgs e)
        {
            if (_busy)
            {
                Log("Сканер занят.");
                return;
            }

            SetBusy(true);
            if (!await StartScannerSessionAsync())
            {
                SetBusy(false);
                SetStatus("Ожидание");
                return;
            }

            SetStatus("Приложите палец к сканеру.");
            SetInfo("Проверка отпечатка. Приложите палец.");

            FingerResult result = await Task.Run(() =>
                _device.Identify(message => SafeUi(() =>
                {
                    SetStatus(message);
                    SetInfo(message);
                })));

            HandleResult(result);
            await EndScannerSessionAsync();
            SetBusy(false);
        }

        private void RefreshClicked(object sender, EventArgs e)
        {
            UpdateDeviceStatus();
            SetStatus("Ожидание");
            SetInfo("Готово к работе.");
        }

        private void OnStaffCodeChanged(object sender, EventArgs e)
        {
            if (_lookupTimer == null)
            {
                return;
            }

            _lookupTimer.Stop();
            _lookupTimer.Start();
        }

        private async void OnLookupTimerTick(object sender, EventArgs e)
        {
            _lookupTimer.Stop();
            string staffCode = (_staffCodeText.Text ?? string.Empty).Trim();
            await LookupEmployeeAsync(staffCode);
        }

        private async Task LookupEmployeeAsync(string staffCode)
        {
            if (_lookupInProgress)
            {
                _lookupTimer.Stop();
                _lookupTimer.Start();
                return;
            }

            if (string.IsNullOrEmpty(staffCode))
            {
                SetEmployeeName(null);
                _lastLookupCode = string.Empty;
                return;
            }

            if (string.Equals(staffCode, _lastLookupCode, StringComparison.Ordinal))
            {
                return;
            }

            _lookupInProgress = true;
            SetEmployeeName("поиск...");
            StaffLookupResponse response = await Task.Run(() => FetchStaffInfo(staffCode));
            _lookupInProgress = false;

            SafeUi(() =>
            {
                string currentCode = (_staffCodeText.Text ?? string.Empty).Trim();
                if (!string.Equals(currentCode, staffCode, StringComparison.Ordinal))
                {
                    return;
                }

                if (response == null || !response.ok)
                {
                    SetEmployeeName("не найден");
                }
                else
                {
                    string name = BuildEmployeeName(response);
                    SetEmployeeName(string.IsNullOrEmpty(name) ? "найден" : name);
                }
            });

            _lastLookupCode = staffCode;
        }

        private void SetEmployeeName(string name)
        {
            if (_employeeNameLabel == null)
            {
                return;
            }

            if (string.IsNullOrEmpty(name))
            {
                _employeeNameLabel.Text = "Сотрудник: —";
                return;
            }

            _employeeNameLabel.Text = "Сотрудник: " + name;
        }

        private StaffLookupResponse FetchStaffInfo(string staffCode)
        {
            string endpoint = BuildStaffLookupEndpoint(staffCode);
            if (string.IsNullOrEmpty(endpoint))
            {
                return null;
            }

            try
            {
                using (var client = new WebClient())
                {
                    client.Encoding = Encoding.UTF8;
                    if (!string.IsNullOrEmpty(_serverToken))
                    {
                        client.Headers["X-Fingerprint-Token"] = _serverToken;
                    }

                    string json = client.DownloadString(endpoint);
                    if (string.IsNullOrEmpty(json))
                    {
                        return null;
                    }

                    var serializer = new JavaScriptSerializer();
                    return serializer.Deserialize<StaffLookupResponse>(json);
                }
            }
            catch
            {
                return null;
            }
        }

        private string BuildStaffLookupEndpoint(string staffCode)
        {
            string baseUrl = (_serverUrl ?? string.Empty).Trim().TrimEnd('/');
            if (string.IsNullOrEmpty(baseUrl) || string.IsNullOrEmpty(staffCode))
            {
                return null;
            }

            return string.Format("{0}/api/fingerprints/staff?staff_code={1}",
                baseUrl,
                Uri.EscapeDataString(staffCode));
        }

        private static string BuildEmployeeName(StaffLookupResponse response)
        {
            if (response == null)
            {
                return string.Empty;
            }

            var parts = new List<string>();
            if (!string.IsNullOrEmpty(response.last_name))
            {
                parts.Add(response.last_name);
            }
            if (!string.IsNullOrEmpty(response.first_name))
            {
                parts.Add(response.first_name);
            }
            if (!string.IsNullOrEmpty(response.middle_name))
            {
                parts.Add(response.middle_name);
            }

            return parts.Count == 0 ? string.Empty : string.Join(" ", parts);
        }

        private async void ExportClicked(object sender, EventArgs e)
        {
            await StartExportAsync(null, false);
        }

        private async void ImportClicked(object sender, EventArgs e)
        {
            if (_busy)
            {
                Log("Сканер занят.");
                return;
            }

            string endpoint = BuildSyncEndpoint();
            if (string.IsNullOrEmpty(endpoint))
            {
                Log("URL сервера не задан.");
                return;
            }

            SetBusy(true);
            bool agentWasRunning = IsAgentAlive();
            if (agentWasRunning)
            {
                SetStatus("Остановка агента...");
                bool stopped = await StopAgentIfRunningAsync();
                if (!stopped)
                {
                    Log("Не удалось остановить агент. Закройте его вручную.");
                    SetBusy(false);
                    SetStatus("Ожидание");
                    return;
                }
            }

            SetStatus("Импорт с сервера...");

            try
            {
                byte[] data = await Task.Run(() =>
                {
                    using (var client = new WebClient())
                    {
                        string token = _serverToken;
                        if (!string.IsNullOrEmpty(token))
                        {
                            client.Headers["X-Fingerprint-Token"] = token;
                        }
                        return client.DownloadData(endpoint);
                    }
                });

                if (data == null || data.Length == 0)
                {
                    Log("Сервер вернул пустой файл.");
                    return;
                }

                _store.Load();
                string json = TemplateStore.NormalizeJsonText(Encoding.UTF8.GetString(data));
                TemplateMergeReport report;
                string error;
                if (!_store.TryMergeFromJson(json, out report, out error))
                {
                    Log("Ошибка импорта: " + error);
                    return;
                }

                _store.Save();
                if (_deviceActive && _device != null)
                {
                    _device.ReloadTemplates();
                }
                UpdateDeviceStatus();
                _lastImportAt = DateTime.Now;
                UpdateDatabaseStatus();
                RefreshFingerprintGrid(_loadNamesCheck != null && _loadNamesCheck.Checked);
                Log(string.Format(
                    "Импорт завершен. Получено: {0}, добавлено: {1}, пропущено: {2}, некорректных: {3}, всего: {4}.",
                    report.Total,
                    report.Added,
                    report.Skipped,
                    report.Invalid,
                    _store.Records.Count));
            }
            catch (WebException ex)
            {
                Log("Ошибка импорта: " + ExtractWebError(ex));
            }
            finally
            {
                SetBusy(false);
                SetStatus("Ожидание");
                if (agentWasRunning)
                {
                    StartAgentIfNotRunning();
                }
            }
        }

        private async Task StartExportAsync(string reason, bool isAuto)
        {
            if (_busy)
            {
                if (!isAuto)
                {
                    Log("Сканер занят.");
                }
                return;
            }

            string endpoint = BuildSyncEndpoint();
            if (string.IsNullOrEmpty(endpoint))
            {
                Log("URL сервера не задан.");
                return;
            }

            SetBusy(true);
            SetStatus(isAuto ? "Автосохранение на сервер..." : "Сохранение на сервер...");

            try
            {
                _store.Save();
                await Task.Run(() =>
                {
                    using (var client = new WebClient())
                    {
                        string token = _serverToken;
                        if (!string.IsNullOrEmpty(token))
                        {
                            client.Headers["X-Fingerprint-Token"] = token;
                        }
                        client.UploadFile(endpoint, _store.FilePath);
                    }
                });

                string message;
                if (string.IsNullOrEmpty(reason))
                {
                    message = isAuto ? "Автосохранение на сервер завершено." : "Сохранение на сервер завершено.";
                }
                else
                {
                    message = string.Format("{0}: сохранение на сервер завершено.", reason);
                }
                Log(message);
                _lastExportAt = DateTime.Now;
                UpdateDatabaseStatus();
            }
            catch (WebException ex)
            {
                Log((isAuto ? "Ошибка автосохранения: " : "Ошибка сохранения: ") + ExtractWebError(ex));
            }
            finally
            {
                SetBusy(false);
                SetStatus("Ожидание");
            }
        }

        private void RequestAutoExport(string reason)
        {
            lock (_autoExportLock)
            {
                _autoExportRequested = true;
                _autoExportReason = reason;
            }

            TryStartAutoExport();
        }

        private void TryStartAutoExport()
        {
            string reason = null;
            lock (_autoExportLock)
            {
                if (_busy || !_autoExportRequested)
                {
                    return;
                }

                _autoExportRequested = false;
                reason = _autoExportReason;
                _autoExportReason = null;
            }

            Task exportTask = StartExportAsync(reason, true);
        }

        private void OnDailySyncTimer()
        {
            SafeUi(() =>
            {
                RequestAutoExport("Автосинхронизация");
                ScheduleAutoSync(false);
            });
        }

        private void ScheduleAutoSync(bool logNext)
        {
            DateTime now = DateTime.Now;
            DateTime next;
            int intervalMinutes = GetSyncIntervalMinutes();
            if (intervalMinutes <= 0)
            {
                next = now.Date.AddHours(7);
                if (next <= now)
                {
                    next = next.AddDays(1);
                }
            }
            else
            {
                next = now.AddMinutes(intervalMinutes);
            }

            double dueMs = (next - now).TotalMilliseconds;
            if (dueMs < 0)
            {
                dueMs = 0;
            }
            int due = (int)Math.Min(dueMs, int.MaxValue);
            _dailySyncTimer.Change(due, Timeout.Infinite);
            _nextSyncAt = next;
            UpdateDatabaseStatus();

            if (logNext)
            {
                Debug.WriteLine("Следующая автосинхронизация: " + next.ToString("dd.MM.yyyy HH:mm"));
            }
        }

        private int GetSyncIntervalMinutes()
        {
            if (_syncIntervalInput != null)
            {
                return (int)_syncIntervalInput.Value;
            }

            return _settings.SyncIntervalMinutes;
        }

        private void OnSyncIntervalChanged(object sender, EventArgs e)
        {
            if (_syncIntervalInput == null)
            {
                return;
            }

            _settings.SyncIntervalMinutes = (int)_syncIntervalInput.Value;
            SaveSettings();
            ScheduleAutoSync(true);
        }

        private void UpdateDatabaseStatus()
        {
            SafeUi(() =>
            {
                if (_dbPathLabel != null)
                {
                    _dbPathLabel.Text = "Файл базы: " + _store.FilePath;
                }

                int count = _store != null && _store.Records != null ? _store.Records.Count : 0;
                if (_dbCountLabel != null)
                {
                    _dbCountLabel.Text = "Записей: " + count;
                }

                DateTime? updatedAt = null;
                if (_store != null && !string.IsNullOrEmpty(_store.FilePath) && File.Exists(_store.FilePath))
                {
                    updatedAt = File.GetLastWriteTime(_store.FilePath);
                }

                if (_dbUpdatedLabel != null)
                {
                    _dbUpdatedLabel.Text = "Последнее изменение: " + FormatTimestamp(updatedAt);
                }

                if (_lastExportLabel != null)
                {
                    _lastExportLabel.Text = "Последняя отправка: " + FormatTimestamp(_lastExportAt);
                }

                if (_lastImportLabel != null)
                {
                    _lastImportLabel.Text = "Последнее получение: " + FormatTimestamp(_lastImportAt);
                }

                if (_nextSyncLabel != null)
                {
                    _nextSyncLabel.Text = "Следующая синхронизация: " + FormatTimestamp(_nextSyncAt);
                }
            });
        }

        private void RefreshFingerprintGrid(bool loadNames)
        {
            if (_fingerprintsGrid == null || _store == null)
            {
                return;
            }

            _store.Load();
            var rows = BuildFingerprintRows(loadNames);
            _fingerprintRows = new BindingList<StaffFingerprintRow>(rows);
            _fingerprintsGrid.DataSource = _fingerprintRows;
            UpdateFingerprintSummary(rows.Count);

            if (loadNames && rows.Count > 0)
            {
                int token = Interlocked.Increment(ref _fingerprintsRefreshToken);
                Task.Run(() => LoadStaffNames(rows, token));
            }
        }

        private List<StaffFingerprintRow> BuildFingerprintRows(bool loadNames)
        {
            var grouped = new Dictionary<string, bool[]>(StringComparer.OrdinalIgnoreCase);
            foreach (var record in _store.Records)
            {
                if (record == null || string.IsNullOrEmpty(record.staff_code))
                {
                    continue;
                }

                if (record.slot < 1 || record.slot > 3)
                {
                    continue;
                }

                bool[] slots;
                if (!grouped.TryGetValue(record.staff_code, out slots))
                {
                    slots = new bool[3];
                    grouped[record.staff_code] = slots;
                }

                slots[record.slot - 1] = true;
            }

            var codes = new List<string>(grouped.Keys);
            codes.Sort(StringComparer.OrdinalIgnoreCase);

            var rows = new List<StaffFingerprintRow>();
            foreach (var code in codes)
            {
                bool[] slots = grouped[code];
                string name = GetCachedStaffName(code);
                if (string.IsNullOrEmpty(name))
                {
                    name = loadNames ? "..." : "—";
                }

                rows.Add(new StaffFingerprintRow
                {
                    StaffCode = code,
                    StaffName = name,
                    Slot1 = slots[0],
                    Slot2 = slots[1],
                    Slot3 = slots[2],
                });
            }

            return rows;
        }

        private void LoadStaffNames(List<StaffFingerprintRow> rows, int token)
        {
            if (rows == null || rows.Count == 0)
            {
                return;
            }

            if (string.IsNullOrEmpty(_serverUrl))
            {
                return;
            }

            foreach (var row in rows)
            {
                if (token != Volatile.Read(ref _fingerprintsRefreshToken))
                {
                    return;
                }

                string code = row.StaffCode;
                if (string.IsNullOrEmpty(code))
                {
                    continue;
                }

                string cached = GetCachedStaffName(code);
                if (!string.IsNullOrEmpty(cached))
                {
                    UpdateRowName(row, cached, token);
                    continue;
                }

                StaffLookupResponse response = FetchStaffInfo(code);
                string name;
                if (response == null)
                {
                    name = "нет ответа";
                }
                else if (!response.ok)
                {
                    name = "не найден";
                }
                else
                {
                    name = BuildEmployeeName(response);
                    if (string.IsNullOrEmpty(name))
                    {
                        name = "найден";
                    }
                }

                lock (_staffNameLock)
                {
                    _staffNameCache[code] = name;
                }

                UpdateRowName(row, name, token);
            }
        }

        private void UpdateRowName(StaffFingerprintRow row, string name, int token)
        {
            if (row == null)
            {
                return;
            }

            SafeUi(() =>
            {
                if (token != _fingerprintsRefreshToken)
                {
                    return;
                }

                row.StaffName = name;
            });
        }

        private string GetCachedStaffName(string staffCode)
        {
            if (string.IsNullOrEmpty(staffCode))
            {
                return null;
            }

            lock (_staffNameLock)
            {
                string name;
                if (_staffNameCache.TryGetValue(staffCode, out name))
                {
                    return name;
                }
            }

            return null;
        }

        private void UpdateFingerprintSummary(int count)
        {
            if (_fingerprintsSummaryLabel != null)
            {
                _fingerprintsSummaryLabel.Text = "Сотрудников: " + count;
            }
        }

        private static string FormatTimestamp(DateTime? value)
        {
            return value.HasValue ? value.Value.ToString("dd.MM.yyyy HH:mm") : "нет";
        }

        private async Task<bool> StartScannerSessionAsync()
        {
            if (_deviceActive)
            {
                return true;
            }

            bool agentRunning = IsAgentAlive();
            if (agentRunning)
            {
                SetStatus("Остановка агента...");
                Log("Останавливаю локальный агент...");
                bool stopped = await StopAgentIfRunningAsync();
                if (!stopped)
                {
                    Log("Не удалось остановить агент. Закройте его вручную.");
                    return false;
                }
                Log("Локальный агент остановлен.");
            }

            _store.Load();
            _device = new FingerDevice(_store);
            _device.FingerprintCaptured += OnFingerprintCaptured;
            SetStatus("Инициализация сканера...");
            bool ok = await Task.Run(() => _device.Initialize());
            if (!ok)
            {
                Log("Ошибка инициализации: " + _device.LastError);
                SafeDisposeDevice();
                await StartAgentIfNotRunningAsync();
                return false;
            }

            _deviceActive = true;
            UpdateDeviceStatus();
            return true;
        }

        private async Task EndScannerSessionAsync()
        {
            SafeDisposeDevice();
            _deviceActive = false;
            UpdateDeviceStatus();
            ClearFingerprintPreview();
            await StartAgentIfNotRunningAsync();
        }

        private void SafeDisposeDevice()
        {
            if (_device == null)
            {
                return;
            }

            try
            {
                _device.FingerprintCaptured -= OnFingerprintCaptured;
                _device.Dispose();
            }
            catch
            {
                // ignore
            }
            finally
            {
                _device = null;
            }
        }

        private async Task StartAgentIfNotRunningAsync()
        {
            if (IsAgentAlive())
            {
                return;
            }

            string path = ResolveAgentExecutablePath();
            if (string.IsNullOrEmpty(path))
            {
                Log("Не найден ZkFingerAgent.exe. Запустите агент вручную.");
                return;
            }

            string error;
            if (!StartAgentProcess(path, out error))
            {
                Log("Не удалось запустить агент: " + error);
                return;
            }

            bool started = await WaitForAgentUpAsync();
            if (started)
            {
                Log("Локальный агент запущен.");
                UpdateDeviceStatus();
            }
            else
            {
                Log("Агент не запустился. Запустите его вручную.");
            }
        }

        private void StartAgentIfNotRunning()
        {
            if (IsAgentAlive())
            {
                return;
            }

            string path = ResolveAgentExecutablePath();
            if (string.IsNullOrEmpty(path))
            {
                Log("Не найден ZkFingerAgent.exe. Запустите агент вручную.");
                return;
            }

            string error;
            if (!StartAgentProcess(path, out error))
            {
                Log("Не удалось запустить агент: " + error);
                return;
            }

            Log("Запускаю локальный агент...");
        }

        private async Task<bool> StopAgentIfRunningAsync()
        {
            bool running = await Task.Run(() => IsAgentAlive());
            if (!running)
            {
                return true;
            }

            bool shutdownSent = await Task.Run(() => SendAgentShutdown());
            if (!shutdownSent)
            {
                return false;
            }

            return await WaitForAgentDownAsync();
        }

        private void StopAgentOnExit()
        {
            if (!IsAgentAlive())
            {
                return;
            }

            Log("Останавливаю локальный агент...");
            bool stopped = SendAgentShutdown();
            if (!stopped)
            {
                Log("Не удалось остановить агент. Закройте его вручную.");
            }
        }

        private static bool StartAgentProcess(string path, out string error)
        {
            error = null;
            try
            {
                var startInfo = new ProcessStartInfo
                {
                    FileName = path,
                    WorkingDirectory = Path.GetDirectoryName(path) ?? string.Empty,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                };
                Process.Start(startInfo);
                return true;
            }
            catch (Exception ex)
            {
                error = ex.Message;
                return false;
            }
        }

        private static bool SendAgentShutdown()
        {
            try
            {
                var request = (HttpWebRequest)WebRequest.Create(AgentBaseUrl + "shutdown");
                request.Method = "POST";
                request.Timeout = 1000;
                request.ReadWriteTimeout = 1000;
                request.ContentLength = 0;
                using (var response = (HttpWebResponse)request.GetResponse())
                {
                    return response.StatusCode == HttpStatusCode.OK;
                }
            }
            catch
            {
                return false;
            }
        }

        private static async Task<bool> WaitForAgentUpAsync()
        {
            for (int i = 0; i < 15; i++)
            {
                await Task.Delay(300);
                if (IsAgentAlive())
                {
                    return true;
                }
            }
            return false;
        }

        private static async Task<bool> WaitForAgentDownAsync()
        {
            for (int i = 0; i < 15; i++)
            {
                await Task.Delay(300);
                if (!IsAgentAlive())
                {
                    return true;
                }
            }
            return false;
        }

        private static bool IsAgentAlive()
        {
            try
            {
                var request = (HttpWebRequest)WebRequest.Create(AgentBaseUrl + "status");
                request.Method = "GET";
                request.Timeout = 1000;
                request.ReadWriteTimeout = 1000;

                using (var response = (HttpWebResponse)request.GetResponse())
                {
                    return response.StatusCode == HttpStatusCode.OK;
                }
            }
            catch
            {
                return false;
            }
        }

        private bool TryGetAgentStatus(out AgentStatus status)
        {
            status = null;
            try
            {
                using (var client = new WebClient())
                {
                    client.Encoding = Encoding.UTF8;
                    string json = client.DownloadString(AgentBaseUrl + "status");
                    if (string.IsNullOrEmpty(json))
                    {
                        return false;
                    }

                    var serializer = new JavaScriptSerializer();
                    var payload = serializer.Deserialize<AgentStatus>(json);
                    if (payload != null && payload.ok)
                    {
                        status = payload;
                        return true;
                    }
                }
            }
            catch
            {
                return false;
            }

            return false;
        }

        private static string ResolveAgentExecutablePath()
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string local = Path.Combine(baseDir, "ZkFingerAgent.exe");
            if (File.Exists(local))
            {
                return local;
            }

            string relative = Path.GetFullPath(Path.Combine(baseDir, "..", "..", "zkfinger-agent", "bin", "ZkFingerAgent.exe"));
            if (File.Exists(relative))
            {
                return relative;
            }

            string root = FindProjectRoot(baseDir);
            if (!string.IsNullOrEmpty(root))
            {
                string candidate = Path.Combine(root, "tools", "zkfinger-agent", "bin", "ZkFingerAgent.exe");
                if (File.Exists(candidate))
                {
                    return candidate;
                }
            }

            return null;
        }

        private void HandleResult(FingerResult result)
        {
            if (result == null)
            {
                Log("Нет результата.");
                return;
            }

            if (result.Ok)
            {
                if (!string.IsNullOrEmpty(result.StaffCode))
                {
                    _staffCodeText.Text = result.StaffCode;
                }

                if (result.Action == FingerAction.Enroll)
                {
                    Log(string.Format("Регистрация успешна. Код сотрудника: {0}, отпечаток №{1}.",
                        result.StaffCode,
                        result.Slot > 0 ? result.Slot : 1));
                    SetInfo(string.Format("Отпечаток №{0} сохранен.",
                        result.Slot > 0 ? result.Slot : 1));
                    RequestAutoExport("После регистрации");
                    RefreshFingerprintGrid(_loadNamesCheck != null && _loadNamesCheck.Checked);
                }
                else
                {
                    if (result.Slot > 0)
                    {
                        Log("Проверка успешна. Код сотрудника: " + result.StaffCode + ", отпечаток №" + result.Slot +
                            ", точность: " + result.Score);
                    }
                    else
                    {
                        Log("Проверка успешна. Код сотрудника: " + result.StaffCode + ", точность: " + result.Score);
                    }
                    SetInfo("Отпечаток распознан.");
                }
                SetStatus("Успешно");
            }
            else
            {
                Log("Ошибка: " + ResolveError(result.Error));
                SetStatus("Ошибка");
                SetInfo(ResolveError(result.Error));
            }

            QueueFingerprintEvent(result);
            UpdateDatabaseStatus();
        }

        private int GetSelectedSlot()
        {
            if (_slotCombo == null || _slotCombo.SelectedItem == null)
            {
                return 1;
            }

            int slot;
            if (int.TryParse(_slotCombo.SelectedItem.ToString(), out slot))
            {
                return slot;
            }

            return 1;
        }

        private static string ResolveTemplatesPath()
        {
            string overridePath = ReadEnvValue("FINGERPRINT_TEMPLATES_PATH");
            if (!string.IsNullOrEmpty(overridePath))
            {
                return overridePath;
            }

            string baseDir = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (!string.IsNullOrEmpty(baseDir))
            {
                return Path.Combine(baseDir, "ZKFinger", "templates.json");
            }

            return Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "data", "templates.json");
        }

        private static string ResolveLegacyTemplatesPath()
        {
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

        private static string ResolveDefaultServerUrl()
        {
            string envUrl = ReadEnvValue("FINGERPRINT_SERVER_URL");
            if (!string.IsNullOrEmpty(envUrl))
            {
                return envUrl;
            }

            envUrl = ReadEnvValue("VITE_SERVER_URL");
            if (!string.IsNullOrEmpty(envUrl))
            {
                return envUrl;
            }

            string root = FindProjectRoot(AppDomain.CurrentDomain.BaseDirectory);
            if (!string.IsNullOrEmpty(root))
            {
                string directUrl = TryReadEnvFileValue(Path.Combine(root, ".env"), "FINGERPRINT_SERVER_URL");
                if (!string.IsNullOrEmpty(directUrl))
                {
                    return directUrl;
                }

                string viteUrl = TryReadEnvFileValue(Path.Combine(root, "frontend", ".env"), "VITE_SERVER_URL");
                if (!string.IsNullOrEmpty(viteUrl))
                {
                    return viteUrl;
                }

                string portValue = TryReadEnvFileValue(Path.Combine(root, ".env"), "PORT");
                int port;
                if (int.TryParse(portValue, out port) && port > 0)
                {
                    return "http://localhost:" + port;
                }
            }

            return null;
        }

        private static string ResolveDefaultToken()
        {
            string token = ReadEnvValue("FINGERPRINT_SYNC_TOKEN");
            if (!string.IsNullOrEmpty(token))
            {
                return token;
            }

            string root = FindProjectRoot(AppDomain.CurrentDomain.BaseDirectory);
            if (!string.IsNullOrEmpty(root))
            {
                string value = TryReadEnvFileValue(Path.Combine(root, ".env"), "FINGERPRINT_SYNC_TOKEN");
                if (!string.IsNullOrEmpty(value))
                {
                    return value;
                }
            }

            return string.Empty;
        }

        private static string ResolveDefaultDataset()
        {
            string dataset = ReadEnvValue("FINGERPRINT_DATASET");
            if (!string.IsNullOrEmpty(dataset))
            {
                return dataset;
            }

            string root = FindProjectRoot(AppDomain.CurrentDomain.BaseDirectory);
            if (!string.IsNullOrEmpty(root))
            {
                string value = TryReadEnvFileValue(Path.Combine(root, ".env"), "FINGERPRINT_DATASET");
                if (!string.IsNullOrEmpty(value))
                {
                    return value;
                }
            }

            return null;
        }

        private static string ReadEnvValue(string key)
        {
            string value = Environment.GetEnvironmentVariable(key);
            return string.IsNullOrEmpty(value) ? null : value.Trim();
        }

        private static string FindProjectRoot(string startDir)
        {
            if (string.IsNullOrEmpty(startDir))
            {
                return null;
            }

            string current = startDir;
            for (int i = 0; i < 6; i++)
            {
                if (File.Exists(Path.Combine(current, ".env")) ||
                    Directory.Exists(Path.Combine(current, "backend")) ||
                    Directory.Exists(Path.Combine(current, "frontend")))
                {
                    return current;
                }

                DirectoryInfo parent = Directory.GetParent(current);
                if (parent == null)
                {
                    break;
                }
                current = parent.FullName;
            }

            return null;
        }

        private static string TryReadEnvFileValue(string path, string key)
        {
            if (string.IsNullOrEmpty(path) || !File.Exists(path))
            {
                return null;
            }

            foreach (string raw in File.ReadAllLines(path, Encoding.UTF8))
            {
                string line = raw.Trim();
                if (string.IsNullOrEmpty(line) || line.StartsWith("#"))
                {
                    continue;
                }

                int idx = line.IndexOf('=');
                if (idx <= 0)
                {
                    continue;
                }

                string lineKey = line.Substring(0, idx).Trim();
                if (!string.Equals(lineKey, key, StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                string value = line.Substring(idx + 1).Trim();
                value = StripEnvValue(value);
                return string.IsNullOrEmpty(value) ? null : value;
            }

            return null;
        }

        private static string StripEnvValue(string value)
        {
            if (string.IsNullOrEmpty(value))
            {
                return value;
            }

            if ((value.StartsWith("\"") && value.EndsWith("\"")) ||
                (value.StartsWith("'") && value.EndsWith("'")))
            {
                if (value.Length >= 2)
                {
                    return value.Substring(1, value.Length - 2);
                }
            }

            return value;
        }

        private string BuildSyncEndpoint()
        {
            string baseUrl = (_serverUrl ?? string.Empty).Trim().TrimEnd('/');
            if (string.IsNullOrEmpty(baseUrl))
            {
                return null;
            }

            string dataset = (_dataset ?? string.Empty).Trim();
            if (string.IsNullOrEmpty(dataset))
            {
                dataset = "default";
            }

            return string.Format("{0}/api/fingerprints/templates?dataset={1}",
                baseUrl,
                Uri.EscapeDataString(dataset));
        }

        private string BuildEventEndpoint()
        {
            string baseUrl = (_serverUrl ?? string.Empty).Trim().TrimEnd('/');
            if (string.IsNullOrEmpty(baseUrl))
            {
                return null;
            }

            return string.Format("{0}/api/fingerprints/events", baseUrl);
        }

        private void QueueFingerprintEvent(FingerResult result)
        {
            if (result == null)
            {
                return;
            }

            string staffCode = result.StaffCode;
            if (string.IsNullOrEmpty(staffCode))
            {
                staffCode = _staffCodeText != null ? _staffCodeText.Text : string.Empty;
            }
            staffCode = (staffCode ?? string.Empty).Trim();
            if (string.IsNullOrEmpty(staffCode))
            {
                return;
            }

            string action = result.Action == FingerAction.Enroll ? "enroll" : "identify";
            bool ok = result.Ok;
            int slot = result.Slot;
            int score = result.Score;
            string errorCode = result.Error;

            Task.Run(() => SendFingerprintEvent(staffCode, action, ok, slot, score, errorCode));
        }

        private void SendFingerprintEvent(
            string staffCode,
            string action,
            bool ok,
            int slot,
            int score,
            string errorCode)
        {
            string endpoint = BuildEventEndpoint();
            if (string.IsNullOrEmpty(endpoint))
            {
                return;
            }

            try
            {
                var payload = new Dictionary<string, object>
                {
                    { "staff_code", staffCode },
                    { "action", action },
                    { "ok", ok },
                    { "source", "gui" },
                };
                if (slot > 0)
                {
                    payload["slot"] = slot;
                }
                if (score > 0)
                {
                    payload["score"] = score;
                }
                if (!string.IsNullOrEmpty(errorCode))
                {
                    payload["error_code"] = errorCode;
                }

                var serializer = new JavaScriptSerializer();
                string json = serializer.Serialize(payload);

                using (var client = new WebClient())
                {
                    client.Headers["Content-Type"] = "application/json";
                    if (!string.IsNullOrEmpty(_serverToken))
                    {
                        client.Headers["X-Fingerprint-Token"] = _serverToken;
                    }
                    client.UploadString(endpoint, "POST", json);
                }
            }
            catch
            {
                // ignore event logging failures
            }
        }

        private void SaveSettings()
        {
            _settings.ServerUrl = _serverUrl ?? string.Empty;
            _settings.Token = _serverToken ?? string.Empty;
            _settings.Dataset = _dataset ?? string.Empty;
            _settings.SyncIntervalMinutes = GetSyncIntervalMinutes();
            _settings.Save();
        }

        private static string ExtractWebError(WebException ex)
        {
            if (ex == null)
            {
                return "Ошибка соединения.";
            }

            try
            {
                if (ex.Response == null)
                {
                    return ex.Message;
                }

                using (var responseStream = ex.Response.GetResponseStream())
                {
                    if (responseStream == null)
                    {
                        return ex.Message;
                    }

                    using (var reader = new StreamReader(responseStream, Encoding.UTF8))
                    {
                        string body = reader.ReadToEnd();
                        return string.IsNullOrEmpty(body) ? ex.Message : body;
                    }
                }
            }
            catch
            {
                return ex.Message;
            }
        }

        private string ResolveError(string error)
        {
            if (string.IsNullOrEmpty(error))
            {
                return "Неизвестная ошибка.";
            }

            switch (error)
            {
                case "device_not_ready":
                    return "Сканер не готов.";
                case "capture_timeout":
                    return "Не удалось считать отпечаток (таймаут).";
                case "finger_mismatch":
                    return "Отпечатки не совпали. Сканируйте один и тот же палец.";
                case "fingerprint_already_enrolled":
                    return "Этот отпечаток уже зарегистрирован.";
                case "no_match":
                    return "Совпадений не найдено.";
                case "staff_code_required":
                    return "Нужен код сотрудника.";
                case "staff_code_invalid":
                    return "Код сотрудника должен быть числом.";
                case "staff_code_limit_reached":
                    return "Достигнут лимит 3 отпечатка на сотрудника. Выберите другой слот.";
                case "slot_invalid":
                    return "Некорректный номер отпечатка. Допустимо 1-3.";
                case "merge_failed":
                    return "Не удалось объединить шаблоны.";
                case "db_add_failed":
                    return "Не удалось сохранить шаблон.";
                default:
                    return error;
            }
        }

        private void UpdateDeviceStatus()
        {
            if (_deviceActive && _device != null)
            {
                var status = _device.GetStatus();
                if (status != null && status.Ok)
                {
                    _deviceLabel.Text = string.Format("Сканер: готов={0}",
                        status.DeviceReady ? "да" : "нет");
                }
                else
                {
                    _deviceLabel.Text = "Сканер: ошибка";
                }
                return;
            }

            AgentStatus agentStatus;
            if (TryGetAgentStatus(out agentStatus))
            {
                _deviceLabel.Text = string.Format("Сканер: агент, готов={0}",
                    agentStatus.device_ready ? "да" : "нет");
                return;
            }

            _deviceLabel.Text = "Сканер: агент не запущен";
        }

        private void OnFingerprintCaptured(FingerprintFrame frame)
        {
            if (frame == null || frame.Image == null || frame.Image.Length == 0)
            {
                return;
            }

            Bitmap bitmap = CreateFingerprintBitmap(frame.Image, frame.Width, frame.Height);
            SafeUi(() =>
            {
                if (_fingerPreview == null)
                {
                    bitmap.Dispose();
                    return;
                }

                Image old = _fingerPreview.Image;
                _fingerPreview.Image = bitmap;
                if (old != null)
                {
                    old.Dispose();
                }
            });
        }

        private void ClearFingerprintPreview()
        {
            SafeUi(() =>
            {
                if (_fingerPreview == null)
                {
                    return;
                }

                Image old = _fingerPreview.Image;
                _fingerPreview.Image = null;
                if (old != null)
                {
                    old.Dispose();
                }
            });
        }

        private static Bitmap CreateFingerprintBitmap(byte[] buffer, int width, int height)
        {
            if (buffer == null || buffer.Length == 0 || width <= 0 || height <= 0)
            {
                return new Bitmap(1, 1);
            }

            var bitmap = new Bitmap(width, height, PixelFormat.Format24bppRgb);
            Rectangle rect = new Rectangle(0, 0, width, height);
            BitmapData data = bitmap.LockBits(rect, ImageLockMode.WriteOnly, bitmap.PixelFormat);

            int stride = data.Stride;
            int bytesPerPixel = 3;
            byte[] rgb = new byte[stride * height];

            for (int y = 0; y < height; y++)
            {
                int srcRow = y * width;
                int dstRow = y * stride;
                for (int x = 0; x < width; x++)
                {
                    byte value = buffer[srcRow + x];
                    int dstIndex = dstRow + x * bytesPerPixel;
                    rgb[dstIndex] = value;
                    rgb[dstIndex + 1] = value;
                    rgb[dstIndex + 2] = value;
                }
            }

            Marshal.Copy(rgb, 0, data.Scan0, rgb.Length);
            bitmap.UnlockBits(data);
            return bitmap;
        }

        private void SetBusy(bool value)
        {
            _busy = value;
            _enrollButton.Enabled = !value;
            _identifyButton.Enabled = !value;
            _refreshButton.Enabled = !value;
            _staffCodeText.Enabled = !value;
            _slotCombo.Enabled = !value;

            if (!value)
            {
                TryStartAutoExport();
            }
        }

        private void SetStatus(string text)
        {
            if (_infoLabel != null)
            {
                _infoLabel.Text = "Статус: " + text;
            }
        }

        private void SetInfo(string text)
        {
            if (_infoLabel != null)
            {
                _infoLabel.Text = text;
            }
        }

        private void Log(string message)
        {
            Debug.WriteLine(message);
            SafeUi(() =>
            {
                if (_logText != null)
                {
                    string line = string.Format("[{0}] {1}", DateTime.Now.ToString("HH:mm:ss"), message);
                    _logText.AppendText(line + Environment.NewLine);
                }

                if (_infoLabel != null)
                {
                    _infoLabel.Text = message;
                }
            });
        }

        private void SafeUi(Action action)
        {
            if (IsHandleCreated && InvokeRequired)
            {
                BeginInvoke(action);
            }
            else
            {
                action();
            }
        }
    }

    internal enum FingerAction
    {
        Enroll,
        Identify
    }

    internal sealed class FingerResult
    {
        public bool Ok;
        public string Error;
        public string StaffCode;
        public int Score;
        public FingerAction Action;
        public int Slot;
    }

    internal sealed class FingerStatus
    {
        public bool Ok;
        public bool DeviceReady;
        public int TemplateCount;
    }

    internal sealed class FingerprintFrame
    {
        public byte[] Image;
        public int Width;
        public int Height;
    }

    internal sealed class AgentStatus
    {
        public bool ok { get; set; }
        public bool device_ready { get; set; }
        public int templates { get; set; }
        public string last_error { get; set; }
    }

    internal sealed class StaffLookupResponse
    {
        public bool ok { get; set; }
        public string staff_code { get; set; }
        public string first_name { get; set; }
        public string last_name { get; set; }
        public string middle_name { get; set; }
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
        public event Action<FingerprintFrame> FingerprintCaptured;

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

        public FingerStatus GetStatus()
        {
            var status = new FingerStatus();
            status.Ok = true;
            status.DeviceReady = _devHandle != IntPtr.Zero && _dbHandle != IntPtr.Zero;
            status.TemplateCount = _store.Records.Count;
            return status;
        }

        public FingerResult Identify(Action<string> statusCallback)
        {
            var result = new FingerResult();
            result.Action = FingerAction.Identify;

            if (_devHandle == IntPtr.Zero || _dbHandle == IntPtr.Zero)
            {
                result.Ok = false;
                result.Error = "device_not_ready";
                return result;
            }

            lock (_operationLock)
            {
                if (statusCallback != null)
                {
                    statusCallback("Приложите палец к сканеру.");
                }

                byte[] template;
                string error;
                if (!TryCapture(out template, out error))
                {
                    result.Ok = false;
                    result.Error = error;
                    return result;
                }

                int fid = 0;
                int score = 0;
                int ret = zkfp2.DBIdentify(_dbHandle, template, ref fid, ref score);
                if (ret != zkfperrdef.ZKFP_ERR_OK)
                {
                    result.Ok = false;
                    result.Error = "no_match";
                    return result;
                }

                TemplateRecord record = _store.FindByFid(fid);
                if (record == null || string.IsNullOrEmpty(record.staff_code))
                {
                    result.Ok = false;
                    result.Error = "no_match";
                    return result;
                }

                result.Ok = true;
                result.StaffCode = record.staff_code;
                result.Score = score;
                result.Slot = record.slot;
                return result;
            }
        }

        public FingerResult Enroll(string staffCode, int slot, Action<string> statusCallback)
        {
            var result = new FingerResult();
            result.Action = FingerAction.Enroll;

            if (_devHandle == IntPtr.Zero || _dbHandle == IntPtr.Zero)
            {
                result.Ok = false;
                result.Error = "device_not_ready";
                return result;
            }

            if (string.IsNullOrEmpty(staffCode))
            {
                result.Ok = false;
                result.Error = "staff_code_required";
                return result;
            }

            staffCode = staffCode.Trim();
            if (!StaffCodeRegex.IsMatch(staffCode))
            {
                result.Ok = false;
                result.Error = "staff_code_invalid";
                return result;
            }

            if (slot < 1 || slot > MaxFingerprintsPerStaff)
            {
                result.Ok = false;
                result.Error = "slot_invalid";
                return result;
            }

            lock (_operationLock)
            {
                TemplateRecord existing = _store.FindByStaffCodeAndSlot(staffCode, slot);
                int currentCount = _store.FindAllByStaffCode(staffCode).Count;
                if (existing != null)
                {
                    TryDeleteTemplate(existing.fid);
                    _store.Records.Remove(existing);
                    currentCount = Math.Max(0, currentCount - 1);
                }
                else if (currentCount >= MaxFingerprintsPerStaff)
                {
                    result.Ok = false;
                    result.Error = "staff_code_limit_reached";
                    return result;
                }

                int fid = existing != null ? existing.fid : _store.GetNextFid();

                var samples = new List<byte[]>();
                for (int i = 0; i < 3; i++)
                {
                    if (statusCallback != null)
                    {
                        statusCallback(string.Format("Сканирование {0}/3. Приложите палец.", i + 1));
                    }

                    byte[] template;
                    string error;
                    if (!TryCapture(out template, out error))
                    {
                        result.Ok = false;
                        result.Error = error;
                        return result;
                    }

                    int foundFid = 0;
                    int score = 0;
                    int identifyRet = zkfp2.DBIdentify(_dbHandle, template, ref foundFid, ref score);
                    if (identifyRet == zkfperrdef.ZKFP_ERR_OK)
                    {
                        result.Ok = false;
                        result.Error = "fingerprint_already_enrolled";
                        return result;
                    }

                    if (samples.Count > 0)
                    {
                        int match = zkfp2.DBMatch(_dbHandle, template, samples[samples.Count - 1]);
                        if (match <= 0)
                        {
                            result.Ok = false;
                            result.Error = "finger_mismatch";
                            return result;
                        }
                    }

                    samples.Add(template);
                    if (statusCallback != null)
                    {
                        statusCallback(string.Format("Сканирование {0}/3: отпечаток считан.", i + 1));
                    }
                }

                byte[] regTmp = new byte[2048];
                int regLen = 0;
                int mergeRet = zkfp2.DBMerge(_dbHandle, samples[0], samples[1], samples[2], regTmp, ref regLen);
                if (mergeRet != zkfperrdef.ZKFP_ERR_OK)
                {
                    result.Ok = false;
                    result.Error = "merge_failed";
                    return result;
                }

                TryDeleteTemplate(fid);
                int addRet = zkfp2.DBAdd(_dbHandle, fid, regTmp);
                if (addRet != zkfperrdef.ZKFP_ERR_OK)
                {
                    result.Ok = false;
                    result.Error = "db_add_failed";
                    return result;
                }

                var record = new TemplateRecord();
                record.fid = fid;
                record.staff_code = staffCode;
                record.template_base64 = Convert.ToBase64String(regTmp);
                record.slot = slot;
                _store.Records.Add(record);
                _store.Save();

                result.Ok = true;
                result.StaffCode = staffCode;
                result.Slot = slot;
                return result;
            }
        }

        private void LoadTemplates()
        {
            _store.Load();
            foreach (var record in _store.Records)
            {
                if (record == null || string.IsNullOrEmpty(record.template_base64))
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

        public void ReloadTemplates()
        {
            lock (_operationLock)
            {
                if (_dbHandle == IntPtr.Zero)
                {
                    return;
                }

                ResetDatabase();
                LoadTemplates();
            }
        }

        private void ResetDatabase()
        {
            try
            {
                zkfp2.DBFree(_dbHandle);
            }
            catch
            {
                // ignore
            }

            _dbHandle = zkfp2.DBInit();
        }

        private bool TryCapture(out byte[] template, out string error)
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            while (sw.ElapsedMilliseconds < CaptureTimeoutMs)
            {
                int cbCapTmp = _capTmp.Length;
                int ret = zkfp2.AcquireFingerprint(_devHandle, _fpBuffer, _capTmp, ref cbCapTmp);
                if (ret == zkfperrdef.ZKFP_ERR_OK)
                {
                    RaiseFingerprintCaptured();
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

        private void RaiseFingerprintCaptured()
        {
            var handler = FingerprintCaptured;
            if (handler == null)
            {
                return;
            }

            if (_fpBuffer == null || _fpBuffer.Length == 0)
            {
                return;
            }

            var copy = new byte[_fpBuffer.Length];
            Buffer.BlockCopy(_fpBuffer, 0, copy, 0, _fpBuffer.Length);
            handler(new FingerprintFrame
            {
                Image = copy,
                Width = _fpWidth,
                Height = _fpHeight,
            });
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

    internal sealed class SettingsStore
    {
        private static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = int.MaxValue };
        private readonly string _path;

        public string ServerUrl;
        public string Token;
        public string Dataset;
        public int SyncIntervalMinutes;

        private SettingsStore(string path)
        {
            _path = path;
        }

        public static SettingsStore Load(string path)
        {
            var store = new SettingsStore(path);
            if (!File.Exists(path))
            {
                return store;
            }

            string json = File.ReadAllText(path, Encoding.UTF8);
            if (string.IsNullOrEmpty(json))
            {
                return store;
            }

            try
            {
                var payload = Json.Deserialize<SettingsPayload>(json);
                if (payload != null)
                {
                    store.ServerUrl = payload.ServerUrl;
                    store.Token = payload.Token;
                    store.Dataset = payload.Dataset;
                    store.SyncIntervalMinutes = payload.SyncIntervalMinutes;
                }
            }
            catch
            {
                return store;
            }

            return store;
        }

        public void Save()
        {
            string dir = Path.GetDirectoryName(_path);
            if (!string.IsNullOrEmpty(dir))
            {
                Directory.CreateDirectory(dir);
            }

            var payload = new SettingsPayload
            {
                ServerUrl = ServerUrl,
                Token = Token,
                Dataset = Dataset,
                SyncIntervalMinutes = SyncIntervalMinutes,
            };
            string json = Json.Serialize(payload);
            File.WriteAllText(_path, json, Encoding.UTF8);
        }

        private sealed class SettingsPayload
        {
            public string ServerUrl { get; set; }
            public string Token { get; set; }
            public string Dataset { get; set; }
            public int SyncIntervalMinutes { get; set; }
        }
    }

    internal sealed class TemplateStore
    {
        private static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = int.MaxValue };
        private readonly string _path;
        public const int MaxFingerprintsPerStaff = 3;

        public List<TemplateRecord> Records { get; private set; }
        public string FilePath
        {
            get { return _path; }
        }

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
            json = NormalizeJsonText(json);
            if (string.IsNullOrEmpty(json))
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

        public static string NormalizeJsonText(string json)
        {
            if (string.IsNullOrEmpty(json))
            {
                return json;
            }

            json = json.TrimStart('\uFEFF');
            if (json.StartsWith("ï»¿", StringComparison.Ordinal))
            {
                json = json.Substring(3);
            }
            return json.TrimStart();
        }

        public void Save()
        {
            string dir = Path.GetDirectoryName(_path);
            if (!string.IsNullOrEmpty(dir))
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

        public bool TryMergeFromJson(string json, out TemplateMergeReport report, out string error)
        {
            report = new TemplateMergeReport();
            error = null;

            if (string.IsNullOrWhiteSpace(json))
            {
                return true;
            }

            List<TemplateRecord> incoming;
            try
            {
                incoming = Json.Deserialize<List<TemplateRecord>>(json);
            }
            catch
            {
                error = "Некорректный JSON.";
                return false;
            }

            if (incoming == null || incoming.Count == 0)
            {
                return true;
            }

            report.Total = incoming.Count;

            var staffSlots = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var staffCounts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
            var fids = new HashSet<int>();
            foreach (var record in Records)
            {
                TemplateRecord normalized;
                if (!TryNormalizeRecord(record, out normalized))
                {
                    continue;
                }

                string staffCode = normalized.staff_code;
                staffSlots.Add(BuildStaffSlotKey(staffCode, normalized.slot));
                fids.Add(normalized.fid);
                int count;
                staffCounts.TryGetValue(staffCode, out count);
                staffCounts[staffCode] = count + 1;
            }

            foreach (var record in incoming)
            {
                TemplateRecord normalized;
                if (!TryNormalizeRecord(record, out normalized))
                {
                    report.Invalid++;
                    continue;
                }

                string staffCode = normalized.staff_code;
                string slotKey = BuildStaffSlotKey(staffCode, normalized.slot);
                int count;
                staffCounts.TryGetValue(staffCode, out count);

                if (fids.Contains(normalized.fid) || staffSlots.Contains(slotKey) || count >= MaxFingerprintsPerStaff)
                {
                    report.Skipped++;
                    continue;
                }

                Records.Add(normalized);
                staffSlots.Add(slotKey);
                fids.Add(normalized.fid);
                staffCounts[staffCode] = count + 1;
                report.Added++;
            }

            return true;
        }

        private static bool TryNormalizeRecord(TemplateRecord record, out TemplateRecord normalized)
        {
            normalized = null;
            if (record == null)
            {
                return false;
            }

            string staffCode = (record.staff_code ?? string.Empty).Trim();
            if (string.IsNullOrEmpty(staffCode))
            {
                return false;
            }

            if (record.fid < 0)
            {
                return false;
            }

            if (record.slot <= 0)
            {
                record.slot = 1;
            }

            if (record.slot < 1 || record.slot > MaxFingerprintsPerStaff)
            {
                return false;
            }

            if (string.IsNullOrEmpty(record.template_base64))
            {
                return false;
            }

            try
            {
                Convert.FromBase64String(record.template_base64);
            }
            catch
            {
                return false;
            }

            record.staff_code = staffCode;
            normalized = record;
            return true;
        }

        private static string BuildStaffSlotKey(string staffCode, int slot)
        {
            return string.Format("{0}#{1}", staffCode ?? string.Empty, slot);
        }

        public TemplateRecord FindByFid(int fid)
        {
            return Records.Find(record => record.fid == fid);
        }

        public TemplateRecord FindByStaffCode(string staffCode)
        {
            return Records.Find(record => string.Equals(record.staff_code, staffCode, StringComparison.OrdinalIgnoreCase));
        }
    }

    internal sealed class TemplateMergeReport
    {
        public int Total;
        public int Added;
        public int Skipped;
        public int Invalid;
    }

    internal sealed class TemplateRecord
    {
        public int fid;
        public string staff_code;
        public int slot;
        public string template_base64;
    }

    internal sealed class StaffFingerprintRow : INotifyPropertyChanged
    {
        private string _staffCode;
        private string _staffName;
        private bool _slot1;
        private bool _slot2;
        private bool _slot3;

        public string StaffCode
        {
            get { return _staffCode; }
            set
            {
                if (string.Equals(_staffCode, value, StringComparison.Ordinal))
                {
                    return;
                }

                _staffCode = value;
                OnPropertyChanged("StaffCode");
            }
        }

        public string StaffName
        {
            get { return _staffName; }
            set
            {
                if (string.Equals(_staffName, value, StringComparison.Ordinal))
                {
                    return;
                }

                _staffName = value;
                OnPropertyChanged("StaffName");
            }
        }

        public bool Slot1
        {
            get { return _slot1; }
            set
            {
                if (_slot1 == value)
                {
                    return;
                }

                _slot1 = value;
                OnPropertyChanged("Slot1");
            }
        }

        public bool Slot2
        {
            get { return _slot2; }
            set
            {
                if (_slot2 == value)
                {
                    return;
                }

                _slot2 = value;
                OnPropertyChanged("Slot2");
            }
        }

        public bool Slot3
        {
            get { return _slot3; }
            set
            {
                if (_slot3 == value)
                {
                    return;
                }

                _slot3 = value;
                OnPropertyChanged("Slot3");
            }
        }

        public event PropertyChangedEventHandler PropertyChanged;

        private void OnPropertyChanged(string propertyName)
        {
            var handler = PropertyChanged;
            if (handler != null)
            {
                handler(this, new PropertyChangedEventArgs(propertyName));
            }
        }
    }
}
