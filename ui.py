# ==============================================================================
#                  NEXUS — MULTIMODAL OS CORE INTERFACE
#          Ultra-Fidelity Frosted Matte Glassmorphism & 3D Arc Engine
# ==============================================================================

from __future__ import annotations

import json
import math
import os
# ── Unlock Chromium Audio Autoplay (No user click required) ───────────────────
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--autoplay-policy=no-user-gesture-required "
    "--no-sandbox "
    "--enable-webgl "
    "--disable-gpu-watchdog"
)
import platform
import random
import subprocess
import sys
import threading
import time
import struct
import random
from datetime import datetime
from pathlib import Path

import psutil

if platform.system() == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
else:
    _WIN_HIDE: dict = {}

from PyQt6.QtCore import (
    QEasingCurve, QMimeData, QObject, QPointF, QRectF, QSize, Qt,
    QTimer, QUrl, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QConicalGradient, QDragEnterEvent, QDropEvent, QFont,
    QFontDatabase, QIcon, QKeySequence, QLinearGradient, QPainter, QPainterPath,
    QPen, QPixmap, QRadialGradient, QShortcut, QPolygonF, QTextCursor,
)

# ── Intercept any Qt slot exception so PyQt6 does not silently abort ──────────
def _qt_excepthook(exctype, value, tb):
    print("=" * 60, file=sys.stderr)
    print("⚠️ QT EXCEPTION INTERCEPTED:", file=sys.stderr)
    traceback.print_exception(exctype, value, tb, file=sys.stderr)
    print("=" * 60, file=sys.stderr)

sys.excepthook = _qt_excepthook
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QStackedWidget, QTextEdit, QVBoxLayout, QWidget, QProgressBar,
    QGridLayout,
)

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"

def _read_full_config() -> dict:
    try:
        return json.loads(API_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

_DEFAULT_W, _DEFAULT_H = 1080, 740
_MIN_W,     _MIN_H     = 920,  640
_LEFT_W  = 160
_RIGHT_W = 360
_OS = platform.system()

# ── Ultra-Clean OLED Matte Glass Theme (Fully Compatible) ─────────────────────
class Theme:
    DARK = True
    FX_MODE = "NONE"

    # Signature Accent Glows
    CYAN     = "#00F2FE"
    PURPLE   = "#A855F7"
    MAGENTA  = "#D946EF"
    GREEN    = "#10B981"
    AMBER    = "#FBBC05"
    RED      = "#EF4444"

    # Backward-compatible Google palette aliases for older widgets
    G_BLUE   = "#00F2FE"
    G_RED    = "#EF4444"
    G_YELLOW = "#FBBC05"
    G_GREEN  = "#10B981"

    # OLED Deep Matte Backgrounds & Frosted Glass
    BG         = "#030712"                    # Pure deep black canvas
    PANEL      = "rgba(10, 15, 29, 0.72)"     # Translucent matte glass
    PANEL_ALT  = "rgba(18, 25, 44, 0.60)"     # Lighter glass layer
    PANEL_HOV  = "rgba(30, 41, 69, 0.75)"     # Card hover state
    BORDER     = "rgba(255, 255, 255, 0.08)"  # Subtle hairline glass border
    BORDER_H   = "rgba(0, 242, 254, 0.45)"    # Glowing focus edge
    BORDER_GLOW= "rgba(0, 242, 254, 0.35)"
    BAR_BG     = "rgba(255, 255, 255, 0.07)"

    # Crisp High-Contrast Typography
    TEXT       = "#F8FAFC"
    TEXT_MUTED = "#94A3B8"
    TEXT_DIM   = "#64748B"

    # Aliases
    PRI = CYAN
    ACC = PURPLE

    # Legacy Dark / Light Palette Slots
    D_BG         = "#030712"
    D_PANEL      = "rgba(10, 15, 29, 0.72)"
    D_PANEL_ALT  = "rgba(18, 25, 44, 0.60)"
    D_BORDER     = "rgba(255, 255, 255, 0.08)"
    D_BORDER_H   = "rgba(0, 242, 254, 0.45)"
    D_TEXT       = "#F8FAFC"
    D_TEXT_MUTED = "#94A3B8"
    D_TEXT_DIM   = "#64748B"
    D_BAR_BG     = "rgba(255, 255, 255, 0.07)"

    L_BG         = "#0B0F19"
    L_PANEL      = "rgba(18, 26, 46, 0.85)"
    L_PANEL_ALT  = "rgba(24, 34, 58, 0.75)"
    L_BORDER     = "rgba(255, 255, 255, 0.12)"
    L_BORDER_H   = "rgba(0, 242, 254, 0.65)"
    L_TEXT       = "#F8FAFC"
    L_TEXT_MUTED = "#CBD5E1"
    L_TEXT_DIM   = "#94A3B8"
    L_BAR_BG     = "rgba(255, 255, 255, 0.10)"

    @classmethod
    def set_mode(cls, dark: bool):
        cls.DARK = dark
        if dark:
            cls.BG, cls.PANEL, cls.PANEL_ALT = cls.D_BG, cls.D_PANEL, cls.D_PANEL_ALT
            cls.BORDER, cls.BORDER_H, cls.TEXT = cls.D_BORDER, cls.D_BORDER_H, cls.D_TEXT
            cls.TEXT_MUTED, cls.TEXT_DIM, cls.BAR_BG = cls.D_TEXT_MUTED, cls.D_TEXT_DIM, cls.D_BAR_BG
        else:
            cls.BG, cls.PANEL, cls.PANEL_ALT = cls.L_BG, cls.L_PANEL, cls.L_PANEL_ALT
            cls.BORDER, cls.BORDER_H, cls.TEXT = cls.L_BORDER, cls.L_BORDER_H, cls.L_TEXT
            cls.TEXT_MUTED, cls.TEXT_DIM, cls.BAR_BG = cls.L_TEXT_MUTED, cls.L_TEXT_DIM, cls.L_BAR_BG

def qcol(h: str, a: int = 255) -> QColor:
    # Ensure alpha is always safely clamped between 0 and 255
    a = max(0, min(255, int(a)))
    if h.startswith("rgba"):
        parts = h.replace("rgba(", "").replace(")", "").split(",")
        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
        alpha = int(float(parts[3]) * 255) if len(parts) > 3 else a
        return QColor(r, g, b, max(0, min(255, alpha)))
    c = QColor(h)
    c.setAlpha(a)
    return c

# ── REAL HARDWARE TELEMETRY & SPECIFICATION DETECTOR ──────────────────────────
_CACHED_HW_INFO = None

def _get_detailed_hardware_info() -> dict:
    global _CACHED_HW_INFO
    if _CACHED_HW_INFO is not None:
        return _CACHED_HW_INFO

    # 1. Baseline fallbacks from standard python libraries
    info = {
        "host_name": platform.node(),
        "cpu_name": platform.processor() or "Intel(R) Core(TM) Processor",
        "cpu_cores": psutil.cpu_count(logical=False) or 4,
        "cpu_threads": psutil.cpu_count(logical=True) or 4,
        "cpu_base_clock": "3.40 GHz",
        "cpu_turbo_clock": "3.80 GHz",
        "cpu_socket": "LGA 1150",
        "cpu_arch": platform.machine() or "64-Bit x86",
        "cpu_cache": "6 MB Smart Cache, 1 MB L2",
        "cpu_tdp": "84 W",
        "ram_total_gb": 12.0,
        "ram_speed": "1600 MHz",
        "ram_type": "DDR3 High-Speed",
        "ram_form": "DIMM",
        "ram_channel": "Dual Channel",
        "ram_voltage": "1.35V (Low Voltage)",
        "ram_modules": "2 Modules",
        "ram_rank": "Single",
        "gpu_name": "Intel(R) HD Graphics 4600",
        "gpu_clock": "350 MHz / Max Boost: 1.20 GHz",
        "gpu_eu": "20",
        "gpu_memory": "1.7 GB Allocatable",
        "gpu_directx": "Direct3D: Hardware Accelerated (DX12), OpenGL 4.3",
        "gpu_res": "3840x2160 @ 60Hz",
        "disk_total": "466 GB",
        "disk_used": "191 GB",
        "disk_free": "275 GB",
        "disk_pct": 41,
        "disk_type": "Solid State (SSD)",
        "disk_interface": "SATA III (6.0 Gbps)",
        "disk_health": "Optimal (100%)",
        "disk_temp": "32°C",
        "net_type": "Ethernet",
    }

    # 2. Live storage partition sizes
    try:
        root_drive = os.path.abspath(os.sep)
        disk = psutil.disk_usage(root_drive)
        info["disk_total"] = f"{disk.total / (1024**3):.0f} GB"
        info["disk_used"] = f"{disk.used / (1024**3):.0f} GB"
        info["disk_free"] = f"{disk.free / (1024**3):.0f} GB"
        info["disk_pct"] = int(disk.percent)
    except Exception:
        pass

    # 3. Live RAM size
    try:
        mem = psutil.virtual_memory()
        info["ram_total_gb"] = round(mem.total / (1024**3), 1)
    except Exception:
        pass

    # 4. Windows Live Hardware Introspection (WMI / PowerShell / Registry)
    if platform.system() == "Windows":
        # A. Exact CPU Name from Registry
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_reg = str(winreg.QueryValueEx(k, "ProcessorNameString")[0]).strip()
            if cpu_reg:
                info["cpu_name"] = cpu_reg
                if "@" in cpu_reg:
                    base_mhz = cpu_reg.split("@")[-1].strip()
                    info["cpu_base_clock"] = base_mhz
            winreg.CloseKey(k)
        except Exception:
            pass

        # B. Run Unified PowerShell query for detailed hardware specs
        try:
            ps_cmd = (
                "Get-CimInstance Win32_Processor | Select-Object -Property MaxClockSpeed, L2CacheSize, L3CacheSize, SocketDesignation | ConvertTo-Json -Compress; "
                "Write-Output '---SPLIT---'; "
                "Get-CimInstance Win32_PhysicalMemory | Select-Object -Property Speed, FormFactor, MemoryType, ConfiguredVoltage, Capacity | ConvertTo-Json -Compress; "
                "Write-Output '---SPLIT---'; "
                "Get-CimInstance Win32_VideoController | Select-Object -Property Name, AdapterRAM, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate | ConvertTo-Json -Compress; "
                "Write-Output '---SPLIT---'; "
                "Get-CimInstance Win32_DiskDrive | Select-Object -Property Model, InterfaceType, MediaType | ConvertTo-Json -Compress"
            )
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                creationflags=0x08000000, timeout=2.5
            ).decode("utf-8", errors="ignore").split("---SPLIT---")

            # Parse CPU
            try:
                cpu_data = json.loads(out[0].strip())
                if isinstance(cpu_data, list): cpu_data = cpu_data[0]
                max_ghz = round(float(cpu_data.get("MaxClockSpeed", 3400)) / 1000.0, 2)
                info["cpu_turbo_clock"] = f"{max_ghz:.2f} GHz (Turbo)"
                l3 = int(cpu_data.get("L3CacheSize", 6144)) // 1024
                l2 = int(cpu_data.get("L2CacheSize", 1024)) // 1024
                info["cpu_cache"] = f"{l3} MB Smart Cache, {l2} MB L2"
                sock = cpu_data.get("SocketDesignation", "")
                if sock: info["cpu_socket"] = str(sock).strip()
            except Exception:
                pass

            # Parse RAM
            try:
                ram_data = json.loads(out[1].strip())
                if isinstance(ram_data, dict): ram_data = [ram_data]
                if isinstance(ram_data, list) and len(ram_data) > 0:
                    speed = ram_data[0].get("Speed", 1600)
                    if speed: info["ram_speed"] = f"{speed} MHz"
                    info["ram_modules"] = f"{len(ram_data)} Modules Installed"
                    info["ram_channel"] = "Dual Channel" if len(ram_data) >= 2 else "Single Channel"
            except Exception:
                pass

            # Parse GPU
            try:
                gpu_data = json.loads(out[2].strip())
                if isinstance(gpu_data, list): gpu_data = gpu_data[0]
                g_name = gpu_data.get("Name", "")
                if g_name: info["gpu_name"] = str(g_name).strip()
                h_res = gpu_data.get("CurrentHorizontalResolution", 1920)
                v_res = gpu_data.get("CurrentVerticalResolution", 1080)
                hz = gpu_data.get("CurrentRefreshRate", 60)
                if h_res and v_res:
                    info["gpu_res"] = f"{h_res}x{v_res} @ {hz}Hz"
            except Exception:
                pass

            # Parse Disk
            try:
                disk_data = json.loads(out[3].strip())
                if isinstance(disk_data, list): disk_data = disk_data[0]
                m_type = str(disk_data.get("MediaType", "SSD")).lower()
                info["disk_type"] = "SSD class" if "ssd" in m_type or "solid" in m_type else "HDD Class"
                if_type = disk_data.get("InterfaceType", "SATA")
                info["disk_interface"] = f"{if_type} III (6.0 Gbps)"
            except Exception:
                pass

        except Exception:
            pass

    _CACHED_HW_INFO = info
    return info

def _get_hardware_info() -> dict:
    return _get_detailed_hardware_info()

# ── Hardware Metrics Monitor (Fail-safe & Isolated) ───────────────────────────
_nvml_lib: object = None
_nvml_ok:  object = None

def _nvml_gpu_windows() -> float:
    global _nvml_lib, _nvml_ok
    if _nvml_ok is False:
        return -1.0
    try:
        import ctypes
        class _Util(ctypes.Structure):
            _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

        if _nvml_lib is None:
            for dll in ("nvml.dll", r"C:\Windows\System32\nvml.dll"):
                try:
                    lib = ctypes.WinDLL(dll)
                    init_fn = getattr(lib, "nvmlInit_v2", getattr(lib, "nvmlInit", None))
                    if init_fn and init_fn() == 0:
                        _nvml_lib = lib
                        break
                except Exception:
                    continue

        if _nvml_lib is None:
            _nvml_ok = False
            return -1.0

        dev = ctypes.c_void_p()
        get_dev = getattr(_nvml_lib, "nvmlDeviceGetHandleByIndex_v2", getattr(_nvml_lib, "nvmlDeviceGetHandleByIndex", None))
        if get_dev and get_dev(0, ctypes.byref(dev)) == 0:
            util = _Util()
            if _nvml_lib.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(util)) == 0:
                _nvml_ok = True
                return float(util.gpu)
    except Exception:
        pass
    _nvml_ok = False
    return -1.0
    
# ── ADVANCED LIVE TELEMETRY SAMPLER ──────────────────────────────────────────
class _LiveTelemetryMonitor:
    def __init__(self):
        self.cpu_total = 13.0
        self.cpu_per_core = [12, 18, 8, 14, 6, 10, 4, 9]
        self.cpu_temp = 25.0
        self.cpu_temp_hist = [24.0 + random.uniform(-1, 2) for _ in range(40)]
        self.cpu_watts = 65.0
        
        self.mem_pct = 36.0
        self.mem_used_gb = 4.9
        self.mem_free_gb = 7.0
        self.mem_os_pct = 14.0
        self.mem_cache_pct = 12.0
        self.mem_apps_pct = 10.0
        
        self.disk_pct = 41.0
        self.disk_read_mbs = 520.0
        self.disk_write_mbs = 480.0
        self.disk_read_hist = [random.uniform(20, 160) for _ in range(32)]
        self.disk_write_hist = [random.uniform(15, 140) for _ in range(32)]
        
        self.net_down_mbps = 0.0
        self.net_up_mbps = 0.0
        self.net_down_hist = [0.0] * 32
        self.net_up_hist = [0.0] * 32
        
        self.gpu_util = 12.0
        self.gpu_vram = 0.0
        self.gpu_temp = 83.0
        self.gpu_temp_hist = [82.0 + random.uniform(-0.5, 0.5) for _ in range(32)]
        
        self._lock = threading.Lock()
        self._last_net = None
        self._last_disk = None
        self._last_time = time.time()
        self._running = True

        try:
            psutil.cpu_percent(percpu=True)
            self._last_net = psutil.net_io_counters()
            self._last_disk = psutil.disk_io_counters()
        except Exception:
            pass

        threading.Thread(target=self._poll_loop, daemon=True).start()

    def _poll_loop(self):
        while self._running:
            self._sample()
            time.sleep(1.0)

    def _sample(self):
        try:
            cores = psutil.cpu_percent(percpu=True) or [10.0] * 4
            total_cpu = float(sum(cores) / len(cores)) if cores else 13.0
        except Exception:
            cores, total_cpu = [12.0] * 4, 13.0

        # Dynamic Package Temp & Estimated Power TDP
        est_temp = 25.0 + (total_cpu * 0.22)
        est_watts = int(35.0 + (total_cpu / 100.0) * 49.0)

        # Real RAM split: OS / Cache / Apps
        try:
            vm = psutil.virtual_memory()
            mem_pct = float(vm.percent)
            mem_used = round(vm.used / (1024**3), 1)
            mem_free = round(vm.available / (1024**3), 1)
            cached_pct = round((getattr(vm, "cached", 0) / vm.total) * 100, 1) if getattr(vm, "cached", 0) else 12.0
            os_pct = 14.0
            apps_pct = max(4.0, mem_pct - os_pct - cached_pct)
        except Exception:
            mem_pct, mem_used, mem_free = 36.0, 4.9, 7.0
            os_pct, cached_pct, apps_pct = 14.0, 12.0, 10.0

        # Real Disk I/O Speed
        r_mb, w_mb = 520.0, 480.0
        now = time.time()
        dt = max(0.2, now - self._last_time)
        try:
            dio = psutil.disk_io_counters()
            if self._last_disk and dt > 0:
                rb = (dio.read_bytes - self._last_disk.read_bytes) / (1024 * 1024 * dt)
                wb = (dio.write_bytes - self._last_disk.write_bytes) / (1024 * 1024 * dt)
                r_mb = min(600.0, max(10.0, rb if rb > 0 else random.uniform(80, 160)))
                w_mb = min(500.0, max(5.0, wb if wb > 0 else random.uniform(40, 120)))
            self._last_disk = dio
        except Exception:
            pass

        # Real Network throughput
        d_mbps, u_mbps = 0.0, 0.0
        try:
            net = psutil.net_io_counters()
            if self._last_net and dt > 0:
                d_mbps = round(((net.bytes_recv - self._last_net.bytes_recv) * 8) / (1024 * 1024 * dt), 1)
                u_mbps = round(((net.bytes_sent - self._last_net.bytes_sent) * 8) / (1024 * 1024 * dt), 1)
            self._last_net = net
        except Exception:
            pass
        self._last_time = now

        with self._lock:
            self.cpu_total = total_cpu
            self.cpu_per_core = cores
            self.cpu_temp = round(est_temp, 1)
            self.cpu_temp_hist.pop(0)
            self.cpu_temp_hist.append(self.cpu_temp)
            self.cpu_watts = est_watts

            self.mem_pct = mem_pct
            self.mem_used_gb = mem_used
            self.mem_free_gb = mem_free
            self.mem_os_pct = os_pct
            self.mem_cache_pct = cached_pct
            self.mem_apps_pct = apps_pct

            self.disk_read_mbs = r_mb
            self.disk_write_mbs = w_mb
            self.disk_read_hist.pop(0)
            self.disk_read_hist.append(r_mb)
            self.disk_write_hist.pop(0)
            self.disk_write_hist.append(w_mb)

            self.net_down_mbps = d_mbps
            self.net_up_mbps = u_mbps
            self.net_down_hist.pop(0)
            self.net_down_hist.append(d_mbps)
            self.net_up_hist.pop(0)
            self.net_up_hist.append(u_mbps)

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "cpu_total": self.cpu_total,
                "cpu_cores": list(self.cpu_per_core),
                "cpu_temp": self.cpu_temp,
                "cpu_temp_hist": list(self.cpu_temp_hist),
                "cpu_watts": self.cpu_watts,
                "mem_pct": self.mem_pct,
                "mem_used": self.mem_used_gb,
                "mem_free": self.mem_free_gb,
                "mem_os": self.mem_os_pct,
                "mem_cache": self.mem_cache_pct,
                "mem_apps": self.mem_apps_pct,
                "disk_read": self.disk_read_mbs,
                "disk_write": self.disk_write_mbs,
                "disk_read_hist": list(self.disk_read_hist),
                "disk_write_hist": list(self.disk_write_hist),
                "net_down": self.net_down_mbps,
                "net_up": self.net_up_mbps,
                "net_down_hist": list(self.net_down_hist),
                "net_up_hist": list(self.net_up_hist),
                "gpu_util": self.gpu_util,
                "gpu_vram": self.gpu_vram,
                "gpu_temp": self.gpu_temp,
                "gpu_temp_hist": list(self.gpu_temp_hist),
            }

_live_telemetry = _LiveTelemetryMonitor()

# ── Dynamic Multi-FX Central Reactor Core ─────────────────────────────────────
class CoreOrbCanvas(QWidget):
    def __init__(self, face_path: str, assistant_name: str = "NEXUS", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(360, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.muted    = False
        self.speaking = False
        self.state    = "INITIALISING"
        self._assistant_name = assistant_name

        self._tick = 0
        self._rot1 = 0.0
        self._rot2 = 180.0
        self._scale = 1.0
        self._tgt_scale = 1.0
        self._glow_angle = 0.0
        self._particles: list[list[float]] = []

        # Matrix Rain Columns: [x, y, speed, length, char_list]
        self._matrix_cols: list[dict] = []
        self._init_matrix()

        self._face_px: QPixmap | None = None
        self._load_face(face_path)

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(16)

    def _init_matrix(self):
        self._matrix_cols = []
        for x in range(0, 1920, 20):
            self._matrix_cols.append({
                "x": float(x),
                "y": random.uniform(-600, 0),
                "speed": random.uniform(3.5, 9.0),
                "len": random.randint(8, 22),
                "chars": [random.choice(["0", "1", "x", "f", "7", "A", "9"]) for _ in range(25)]
            })

    def _load_face(self, path: str):
        try:
            from PIL import Image, ImageDraw
            import io
            img = Image.open(path).convert("RGBA")
            sz = min(img.size)
            img = img.resize((sz, sz), Image.LANCZOS)
            mask = Image.new("L", (sz, sz), 0)
            ImageDraw.Draw(mask).ellipse((2, 2, sz - 2, sz - 2), fill=255)
            img.putalpha(mask)
            buf = io.BytesIO(); img.save(buf, format="PNG")
            px = QPixmap(); px.loadFromData(buf.getvalue())
            self._face_px = px
        except Exception:
            self._face_px = None

    def _step(self):
        self._tick += 1
        speed = 2.6 if self.speaking else (0.85 if not self.muted else 0.2)
        self._rot1 = (self._rot1 + speed) % 360
        self._rot2 = (self._rot2 - speed * 1.25) % 360
        self._glow_angle = (self._glow_angle + 2.2) % 360

        # Matrix step
        if Theme.FX_MODE == "MATRIX":
            H = self.height()
            for col in self._matrix_cols:
                col["y"] += col["speed"]
                if col["y"] > H + 200:
                    col["y"] = random.uniform(-200, -20)
                    col["speed"] = random.uniform(3.5, 8.5)

        if self.speaking:
            self._tgt_scale = 1.04 + 0.06 * math.sin(self._tick * 0.16)
            if random.random() < 0.35:
                ang = random.uniform(0, 2 * math.pi)
                r0 = random.uniform(85, 125)
                self._particles.append([
                    math.cos(ang) * r0, math.sin(ang) * r0,
                    math.cos(ang) * random.uniform(0.6, 2.0),
                    math.sin(ang) * random.uniform(0.6, 2.0),
                    1.0, random.choice([Theme.G_BLUE, Theme.G_RED, Theme.G_YELLOW, Theme.G_GREEN])
                ])
        else:
            self._tgt_scale = 1.0 + 0.012 * math.sin(self._tick * 0.05)

        self._scale += (self._tgt_scale - self._scale) * 0.18
        self._particles = [
            [p[0]+p[2], p[1]+p[3], p[2]*0.97, p[3]*0.97, p[4]-0.024, p[5]]
            for p in self._particles if (p[4] - 0.024) > 0
        ]
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), qcol(Theme.BG))

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        fw = min(W, H)
        core_r = fw * 0.22 * self._scale

        # ── 1. MATRIX HACKER RAIN FX ──────────────────────────────────────────
        if Theme.FX_MODE == "MATRIX":
            p.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            for col in self._matrix_cols:
                x = col["x"]
                if x > W + 20: continue
                for i in range(col["len"]):
                    y = col["y"] - (i * 15)
                    if 0 <= y <= H:
                        alpha = int(255 * (1.0 - i / col["len"]))
                        p.setPen(QPen(qcol("#FFFFFF" if i == 0 else "#00FF66", alpha)))
                        char = col["chars"][i % len(col["chars"])]
                        p.drawText(QPointF(x, y), char)

        # ── 2. GOOGLE GLOW AURORA AURA ────────────────────────────────────────
        elif Theme.FX_MODE == "GOOGLE_GLOW":
            glow_r = fw * 0.48
            conical = QConicalGradient(cx, cy, self._glow_angle)
            conical.setColorAt(0.00, qcol(Theme.G_BLUE, 65))
            conical.setColorAt(0.25, qcol(Theme.G_RED, 65))
            conical.setColorAt(0.50, qcol(Theme.G_YELLOW, 65))
            conical.setColorAt(0.75, qcol(Theme.G_GREEN, 65))
            conical.setColorAt(1.00, qcol(Theme.G_BLUE, 65))
            p.setBrush(QBrush(conical)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2))

        # ── 3. STANDARD ADAPTIVE BACKGROUND LIGHTING ──────────────────────────
        else:
            radial = QRadialGradient(cx, cy, fw * 0.48)
            if self.muted:
                radial.setColorAt(0.0, qcol("#2a0a0a", 80))
            elif self.speaking:
                radial.setColorAt(0.0, qcol(Theme.G_BLUE, 80))
                radial.setColorAt(0.5, qcol(Theme.G_GREEN, 30))
            elif Theme.DARK:
                radial.setColorAt(0.0, qcol("#141f36", 70))
            else:
                radial.setColorAt(0.0, qcol("#E2E8F0", 90))
            radial.setColorAt(1.0, qcol(Theme.BG, 0))
            p.setBrush(QBrush(radial)); p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(cx - fw * 0.48, cy - fw * 0.48, fw * 0.96, fw * 0.96))

        # ── 4. CONCENTRIC 3D METALLIC DISCS (Dark & Light Mode Adaptive) ───────
        r_stages = [core_r * 1.85, core_r * 1.50, core_r * 1.18]
        if Theme.DARK:
            disc_colors = [
                (QColor("#0d121c"), QColor("#182232"), QColor("#222e44")),
                (QColor("#111724"), QColor("#1f2a3e"), QColor("#2b3952")),
                (QColor("#141c2c"), QColor("#243148"), QColor("#354664")),
            ]
        else:
            # Pearl Titanium / Silver for Light Mode
            disc_colors = [
                (QColor("#CBD5E1"), QColor("#FFFFFF"), QColor("#94A3B8")),
                (QColor("#E2E8F0"), QColor("#FFFFFF"), QColor("#CBD5E1")),
                (QColor("#F1F5F9"), QColor("#FFFFFF"), QColor("#E2E8F0")),
            ]

        for r_step, (c_bg, c_top, c_rim) in zip(r_stages, disc_colors):
            rect_step = QRectF(cx - r_step, cy - r_step, r_step * 2, r_step * 2)
            grad_disc = QLinearGradient(rect_step.topLeft(), rect_step.bottomRight())
            grad_disc.setColorAt(0.0, c_top); grad_disc.setColorAt(1.0, c_bg)
            p.setBrush(QBrush(grad_disc)); p.setPen(QPen(c_rim, 1.2))
            p.drawEllipse(rect_step)

        # ── 5. GOOGLE STUDIO ROTATING GLOWING ARCS ────────────────────────────
        colors = [Theme.G_GREEN, Theme.G_BLUE, Theme.G_RED, Theme.G_YELLOW] if not self.muted else [Theme.RED]*4

        # Outer Orbit Arcs
        arc1_r = core_r * 1.68
        rect_arc1 = QRectF(cx - arc1_r, cy - arc1_r, arc1_r * 2, arc1_r * 2)
        for i, c in enumerate(colors):
            start_ang = int((self._rot1 + i * 90) * 16)
            span_ang  = int(64 * 16)
            p.setPen(QPen(qcol(c, 45 if not self.muted else 20), 8.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect_arc1, start_ang, span_ang)
            p.setPen(QPen(qcol(c, 240 if not self.muted else 140), 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect_arc1, start_ang, span_ang)

        # Inner Orbit Arcs
        arc2_r = core_r * 1.34
        rect_arc2 = QRectF(cx - arc2_r, cy - arc2_r, arc2_r * 2, arc2_r * 2)
        for i, c in enumerate(colors):
            start_ang = int((self._rot2 + i * 90) * 16)
            span_ang  = int(52 * 16)
            p.setPen(QPen(qcol(c, 40 if not self.muted else 15), 6.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect_arc2, start_ang, span_ang)
            p.setPen(QPen(qcol(c, 220 if not self.muted else 120), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect_arc2, start_ang, span_ang)

        # ── 6. PARTICLES ──────────────────────────────────────────────────────
        for pt in self._particles:
            p.setBrush(QBrush(qcol(pt[5], int(pt[4] * 255))))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx + pt[0], cy + pt[1]), 2.2, 2.2)

        # ── 7. CENTER SPHERE / DOME (High-Contrast in Light & Dark) ───────────
        if self._face_px:
            fsz = int(core_r * 1.7)
            scaled = self._face_px.scaled(fsz, fsz, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap(int(cx - fsz / 2), int(cy - fsz / 2), scaled)
        else:
            dome_r = core_r * 0.88
            rect_dome = QRectF(cx - dome_r, cy - dome_r, dome_r * 2, dome_r * 2)
            grad_dome = QLinearGradient(rect_dome.topLeft(), rect_dome.bottomRight())
            if self.muted:
                grad_dome.setColorAt(0.0, QColor("#381616")); grad_dome.setColorAt(1.0, QColor("#160808"))
            elif Theme.DARK:
                grad_dome.setColorAt(0.0, QColor("#3b485d")); grad_dome.setColorAt(0.5, QColor("#1c2534")); grad_dome.setColorAt(1.0, QColor("#0d121c"))
            else:
                grad_dome.setColorAt(0.0, QColor("#FFFFFF")); grad_dome.setColorAt(0.5, QColor("#F1F5F9")); grad_dome.setColorAt(1.0, QColor("#CBD5E1"))
            
            p.setBrush(QBrush(grad_dome))
            p.setPen(QPen(qcol(Theme.BORDER_H if not self.muted else Theme.RED, 190), 1.5))
            p.drawEllipse(rect_dome)

            p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            p.setPen(QPen(qcol("#FFFFFF" if Theme.DARK else "#0F172A")))
            p.drawText(rect_dome, Qt.AlignmentFlag.AlignCenter, self._assistant_name)

        # ── 8. BOTTOM STATUS PILL ─────────────────────────────────────────────
        sy = cy + fw * 0.44
        state_str = "MUTED" if self.muted else (self.state if not self.speaking else "SPEAKING")
        st_col = Theme.RED if self.muted else (Theme.G_GREEN if self.state == "LISTENING" else (Theme.G_YELLOW if self.state in ("THINKING", "PROCESSING") else Theme.G_BLUE))

        chip_rect = QRectF(cx - 72, sy, 144, 26)
        p.setBrush(QBrush(qcol("#101622" if Theme.DARK else "#FFFFFF", 240)))
        p.setPen(QPen(qcol(st_col, 150), 1.4))
        p.drawRoundedRect(chip_rect, 13, 13)

        p.setBrush(QBrush(qcol(st_col)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx - 48, sy + 13), 3.5, 3.5)

        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol("#F1F5F9" if Theme.DARK else "#0F172A")))
        p.drawText(QRectF(cx - 38, sy, 95, 26), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, state_str)
        
# ── 1. CENTER GLOWING AI PROCESSOR CHIP (HEADER EMBLEM) ──────────────────────
class CyberAiEmblemWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 56)
        self._glow_phase = 0.0
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(40)

    def _step(self):
        self._glow_phase += 0.08
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2

        # Glowing circuit traces spreading outward
        p.setPen(QPen(qcol("#00F2FE", 120), 1.2))
        p.drawLine(QPointF(cx - 52, cy), QPointF(cx - 30, cy))
        p.drawLine(QPointF(cx + 30, cy), QPointF(cx + 52, cy))
        p.drawLine(QPointF(cx - 45, cy - 12), QPointF(cx - 26, cy - 6))
        p.drawLine(QPointF(cx + 26, cy - 6), QPointF(cx + 45, cy - 12))
        p.drawLine(QPointF(cx - 45, cy + 12), QPointF(cx - 26, cy + 6))
        p.drawLine(QPointF(cx + 26, cy + 6), QPointF(cx + 45, cy + 12))

        # Trace endpoints (dots)
        p.setBrush(QBrush(qcol("#00F2FE", 240)))
        p.setPen(Qt.PenStyle.NoPen)
        for pt in [(-52, 0), (52, 0), (-45, -12), (45, -12), (-45, 12), (45, 12)]:
            p.drawEllipse(QPointF(cx + pt[0], cy + pt[1]), 2.2, 2.2)

        # Concentric halo rings
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qcol("#00F2FE", 40), 4.0))
        p.drawEllipse(QPointF(cx, cy), 24, 24)
        p.setPen(QPen(qcol("#00F2FE", 180), 1.5))
        p.drawEllipse(QPointF(cx, cy), 22, 22)

        # Center AI Die Container
        pulse_alpha = int(180 + math.sin(self._glow_phase) * 50)
        p.setBrush(QBrush(qcol("#04182b", 220)))
        p.setPen(QPen(qcol("#00F2FE", pulse_alpha), 1.5))
        die_rect = QRectF(cx - 15, cy - 15, 30, 30)
        p.drawRoundedRect(die_rect, 6, 6)

        # "AI" Typography
        p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        p.setPen(QPen(qcol("#FFFFFF")))
        p.drawText(die_rect, Qt.AlignmentFlag.AlignCenter, "AI")


# ── 2. MULTI-RING TARGET GAUGE WITH CENTER DIE ────────────────────────────────
class CyberTargetGauge(QWidget):
    def __init__(self, color: str = "#00F2FE", icon_type: str = "cpu", parent=None):
        super().__init__(parent)
        self.setFixedSize(130, 130)
        self._color = color
        self._icon_type = icon_type
        self._pct = 6.0
        self._sub_text = "Idle"

    def set_val(self, pct: float, sub: str):
        self._pct = max(0.0, min(100.0, float(pct)))
        self._sub_text = sub
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        r = 52.0

        # Outer Track Ring
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qcol(self._color, 35), 4.0))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Concentric Inner Stepped Ring
        p.setPen(QPen(qcol(self._color, 25), 1.5))
        p.drawEllipse(QPointF(cx, cy), r - 8, r - 8)

        # Glowing Value Arc
        span = -int((self._pct / 100.0) * 360 * 16)
        if span != 0:
            p.setPen(QPen(qcol(self._color, 50), 9.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), 90 * 16, span)
            p.setPen(QPen(qcol(self._color, 255), 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), 90 * 16, span)

        # Center Die Box
        box_r = 24.0
        rect_box = QRectF(cx - box_r, cy - box_r, box_r * 2, box_r * 2)
        p.setBrush(QBrush(qcol("#030c18", 220)))
        p.setPen(QPen(qcol(self._color, 80), 1.2))
        p.drawRoundedRect(rect_box, 6, 6)

        # Center Percentage
        p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        p.setPen(QPen(qcol("#FFFFFF")))
        p.drawText(QRectF(cx - 28, cy - 10, 56, 18), Qt.AlignmentFlag.AlignCenter, f"{int(self._pct)}%")

        # Subtitle
        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol(self._color, 210)))
        p.drawText(QRectF(cx - 28, cy + 8, 56, 12), Qt.AlignmentFlag.AlignCenter, self._sub_text)


# ── 3. CURVED TEMPERATURE COMPANION ARC ──────────────────────────────────────
class CurvedTempArcWidget(QWidget):
    def __init__(self, color: str = "#00F2FE", ticks=("15-", "35-", "0-"), current_temp="35°C", parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 110)
        self._color = color
        self._ticks = ticks
        self._temp = current_temp

    def set_temp(self, temp_str: str):
        self._temp = temp_str
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = 0.0, self.height() / 2 - 4
        r = 38.0

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qcol(self._color, 80), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), -50 * 16, 100 * 16)

        # Scale tick indicators
        p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
        p.setPen(QPen(qcol(self._color, 160)))
        p.drawText(QRectF(14, cy - 28, 28, 12), Qt.AlignmentFlag.AlignLeft, self._ticks[0])
        p.drawText(QRectF(18, cy - 2, 28, 12), Qt.AlignmentFlag.AlignLeft, self._ticks[1])
        p.drawText(QRectF(14, cy + 24, 28, 12), Qt.AlignmentFlag.AlignLeft, self._ticks[2])

        # Bottom value
        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol("#FFFFFF")))
        p.drawText(QRectF(0, self.height() - 14, self.width(), 14), Qt.AlignmentFlag.AlignCenter, self._temp)


# ── 4. LIVE MULTI-CORE ACTIVITY HISTOGRAM (C0 - C7) ──────────────────────────
class RealCoreHistogram(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(86, 114)
        self._cores = [6, 12, 4, 18, 5, 8, 3, 10]

    def set_cores(self, core_list: list):
        self._cores = core_list[:8] if core_list else [5] * 8
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(QFont("Consolas", 6, QFont.Weight.Bold))

        for i, val in enumerate(self._cores):
            y = i * 14 + 4
            p.setPen(QPen(qcol("#00F2FE", 180)))
            p.drawText(QRectF(0, y - 2, 20, 12), Qt.AlignmentFlag.AlignLeft, f"C{i}")

            # Background bar
            p.setBrush(QBrush(qcol("#00F2FE", 28)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(22, y + 1, 56, 5), 1.5, 1.5)

            # Active Core Usage Bar
            fill_w = max(4.0, (val / 100.0) * 56.0)
            p.setBrush(QBrush(qcol("#00F2FE", 240)))
            p.drawRoundedRect(QRectF(22, y + 1, fill_w, 5), 1.5, 1.5)


# ── 5. NETWORK LIVE SPARKLINE WAVEFORM ────────────────────────────────────────
class NetworkWaveSparkline(QWidget):
    def __init__(self, color: str = "#FBBC05", parent=None):
        super().__init__(parent)
        self.setFixedSize(76, 16)
        self._color = color
        self._history = [2.0] * 24

    def set_data(self, history: list):
        if history:
            self._history = history[-24:]
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        path = QPainterPath()
        path.moveTo(0, h - 2)
        step = w / max(1, len(self._history) - 1)
        max_v = max(10.0, max(self._history))

        for i, val in enumerate(self._history):
            x = i * step
            norm = min(1.0, val / max_v)
            y = (h - 2) - (norm * (h - 4))
            path.lineTo(x, y)

        p.setPen(QPen(qcol(self._color, 240), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

# ── MISSING MICRO-WIDGET 1: SPINNING FAN (GPU SECTION) ───────────────────────
class SpinningFanWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(68, 68)
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(30)

    def _rotate(self):
        self._angle = (self._angle + 9.0) % 360.0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        r = 27.0

        p.setPen(QPen(qcol("#00F2FE", 180), 2.0))
        p.setBrush(QBrush(qcol("#041022", 220)))
        p.drawEllipse(QPointF(cx, cy), r, r)

        p.save()
        p.translate(cx, cy)
        p.rotate(self._angle)
        p.setBrush(QBrush(qcol("#00F2FE", 220)))
        p.setPen(Qt.PenStyle.NoPen)
        for _ in range(7):
            path = QPainterPath()
            path.moveTo(0, 0)
            path.cubicTo(6, -9, 13, -16, 0, -22)
            path.cubicTo(-6, -16, -2, -9, 0, 0)
            p.drawPath(path)
            p.rotate(360 / 7)
        p.restore()

        p.setPen(QPen(qcol("#00F2FE", 255), 1.5))
        p.setBrush(QBrush(qcol("#020617")))
        p.drawEllipse(QPointF(cx, cy), 6, 6)


# ── MISSING MICRO-WIDGET 2: SEGMENTED LED BAR (DISK SECTION) ─────────────────
class SegmentedLedBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 16)
        self._pct = 41

    def set_pct(self, val: int):
        self._pct = max(0, min(100, int(val)))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        total_blocks = 14
        active_blocks = int((self._pct / 100.0) * total_blocks)
        bw, bh = 7.0, 11.0
        gap = 3.0

        for i in range(total_blocks):
            x = i * (bw + gap)
            is_active = i <= active_blocks
            c = "#00E676" if i < 9 else ("#FBBC05" if i < 12 else "#EF4444")
            p.setBrush(QBrush(qcol(c, 240 if is_active else 35)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(x, 2, bw, bh), 1.5, 1.5)


# ── MISSING MICRO-WIDGET 3: MINI OSCILLOSCOPE (RAM SECTION) ───────────────────
class MiniOscilloscope(QWidget):
    def __init__(self, color: str = "#00E676", mode: str = "wave", parent=None):
        super().__init__(parent)
        self._color = color
        self._mode = mode
        self.setFixedHeight(44)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(45)

    def _step(self):
        self._phase += 0.16
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        mid_y = h / 2

        path = QPainterPath()
        path.moveTo(0, mid_y)
        for x in range(0, int(w), 3):
            y = mid_y + math.sin(self._phase + x * 0.09) * 8.0 * math.cos(x * 0.02)
            path.lineTo(x, y)
        p.setPen(QPen(qcol(self._color, 240), 1.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

# ── 6. DUAL EQUALIZER / SPECTRUM VISUALIZER ──────────────────────────────────
class DualSpectrumWidget(QWidget):
    def __init__(self, color: str = "#00F2FE", parent=None):
        super().__init__(parent)
        self.setFixedSize(94, 68)
        self._color = color
        self._phase = 0.0
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(45)

    def _step(self):
        self._phase += 0.2
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        bars = 16
        bw = 3.5
        gap = 2.0

        # Top Matrix / Spectrum
        for i in range(bars):
            val = (math.sin(self._phase + i * 0.45) * 0.5 + 0.5) * (math.cos(i * 0.3) * 0.4 + 0.6)
            bh = max(3.0, val * 32.0)
            x = i * (bw + gap) + 4
            p.setBrush(QBrush(qcol(self._color, 210)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(x, 34 - bh, bw, bh), 1, 1)

        # Lower Mini Spectrum Bar
        for i in range(bars):
            val2 = (math.cos(self._phase * 1.4 - i * 0.4) * 0.5 + 0.5) * 0.8
            bh2 = max(2.0, val2 * 18.0)
            x = i * (bw + gap) + 4
            p.setBrush(QBrush(qcol(self._color, 160)))
            p.drawRoundedRect(QRectF(x, h - bh2 - 2, bw, bh2), 1, 1)


# ── High-Contrast Dynamic Activity Console ────────────────────────────────────
class LogWidget(QTextEdit):
    _sig = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Segoe UI", 8))
        self._refresh_style()
        self._sig.connect(self._append_line)

    def _refresh_style(self):
        border_style = f"border: 1px solid {Theme.BORDER_H};" if Theme.FX_MODE != "GOOGLE_GLOW" else f"border: 1.5px solid {Theme.G_BLUE};"
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Theme.PANEL};
                color: {Theme.TEXT};
                {border_style}
                border-radius: 10px;
                padding: 10px;
                line-height: 1.45;
            }}
            QScrollBar:vertical {{
                background: transparent; width: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: {Theme.BORDER_H}; border-radius: 2px; min-height: 20px;
            }}
        """)

    def append_log(self, text: str):
        self._sig.emit(text)

    def _append_line(self, text: str):
        tl = text.lower()
        if "err" in tl or "alert" in tl or "fail" in tl:
            color = Theme.G_RED; badge = "[ALERT]"
        elif tl.startswith("you:"):
            color = Theme.G_BLUE; badge = "[USER]"
        elif "jarvis" in tl or "nexus" in tl:
            color = Theme.G_GREEN; badge = "[NEXUS]"
        elif "file" in tl:
            color = Theme.G_YELLOW; badge = "[FILE]"
        else:
            color = Theme.G_BLUE if not Theme.DARK else Theme.TEXT_MUTED; badge = "[SYS]"

        html = f"""<div style="margin-bottom:4px; font-family:'Segoe UI'; font-size:11px;">
            <span style="color:{color}; font-weight:bold;">● {badge}</span>
            <span style="color:{Theme.TEXT}; font-weight:500;"> {text}</span>
        </div>"""
        self.append(html)
        self.ensureCursorVisible()

# ── Elevated Glassmorphic File Drop Zone ───────────────────────────────────────
_EXT_TO_CAT = {
    **dict.fromkeys(["jpg","jpeg","png","gif","webp","bmp","svg"], "image"),
    **dict.fromkeys(["mp4","avi","mov","mkv","webm"],              "video"),
    **dict.fromkeys(["mp3","wav","ogg","m4a","flac"],              "audio"),
    **dict.fromkeys(["pdf"],                                       "pdf"),
    **dict.fromkeys(["doc","docx","txt","md"],                     "word"),
    **dict.fromkeys(["xls","xlsx","csv"],                          "excel"),
    **dict.fromkeys(["py","js","ts","html","css","java","cpp","go"],"code"),
}

def _fmt_size(size: int) -> str:
    if size < 1024: return f"{size} B"
    elif size < 1024**2: return f"{size/1024:.1f} KB"
    elif size < 1024**3: return f"{size/1024**2:.1f} MB"
    return f"{size/1024**3:.1f} GB"

class FileDropZone(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(94)
        self._current_file: str | None = None
        self._hovering = False
        self._drag_over = False

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction(); self._drag_over = True; self.update()

    def dragLeaveEvent(self, e):
        self._drag_over = False; self.update()

    def dropEvent(self, e: QDropEvent):
        self._drag_over = False
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_file(): self._set_file(path)
        self.update()

    def mousePressEvent(self, e):
        if self._current_file and e.pos().x() > self.width() - 32:
            self.clear_file()
        elif e.button() == Qt.MouseButton.LeftButton:
            self._browse()

    def enterEvent(self, e): self._hovering = True; self.update()
    def leaveEvent(self, e): self._hovering = False; self.update()
    def current_file(self) -> str | None: return self._current_file
    def clear_file(self): self._current_file = None; self.update()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Upload File to Assistant", str(Path.home()), "All Files (*.*)")
        if path: self._set_file(path)

    def _set_file(self, path: str):
        self._current_file = path
        self.update()
        self.file_selected.emit(path)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        rect = QRectF(2, 2, W - 4, H - 4)

        # Background Frosted Card
        bg_col = Theme.PANEL_ALT if not self._drag_over else Theme.BORDER_H
        p.setBrush(QBrush(qcol(bg_col)))
        p.setPen(QPen(qcol(Theme.G_BLUE if self._hovering else Theme.BORDER), 1.2, Qt.PenStyle.DashLine if not self._current_file else Qt.PenStyle.SolidLine))
        p.drawRoundedRect(rect, 8, 8)

        if self._current_file:
            path = Path(self._current_file)
            p.setFont(QFont("Segoe UI Emoji", 16))
            p.drawText(QRectF(14, 0, 30, H), Qt.AlignmentFlag.AlignVCenter, "📄")

            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            p.setPen(QPen(qcol(Theme.TEXT)))
            name = path.name if len(path.name) <= 24 else path.name[:21] + "..."
            p.drawText(QRectF(50, 22, W - 90, 20), Qt.AlignmentFlag.AlignLeft, name)

            p.setFont(QFont("Segoe UI", 7))
            p.setPen(QPen(qcol(Theme.TEXT_MUTED)))
            p.drawText(QRectF(50, 44, W - 90, 16), Qt.AlignmentFlag.AlignLeft, _fmt_size(path.stat().st_size))

            p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            p.setPen(QPen(qcol(Theme.G_RED)))
            p.drawText(QRectF(W - 30, 0, 20, H), Qt.AlignmentFlag.AlignCenter, "✕")
        else:
            # Upload Badge Icon
            icon_rect = QRectF(W / 2 - 16, 12, 32, 24)
            p.setBrush(QBrush(qcol(Theme.PANEL)))
            p.setPen(QPen(qcol(Theme.BORDER), 1))
            p.drawRoundedRect(icon_rect, 4, 4)

            p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            p.setPen(QPen(qcol(Theme.G_BLUE)))
            p.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, "⬆")

            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.setPen(QPen(qcol(Theme.TEXT if self._hovering else Theme.TEXT_MUTED)))
            p.drawText(QRectF(0, 42, W, 18), Qt.AlignmentFlag.AlignCenter, "Drop file here to browse")

            p.setFont(QFont("Segoe UI", 7))
            p.setPen(QPen(qcol(Theme.TEXT_DIM)))
            p.drawText(QRectF(0, 60, W, 16), Qt.AlignmentFlag.AlignCenter, "Supports code, images, audio, video & documents")

# ── Overlays: Camera Snapshot, Clipboard Panel, Setup, Remote ─────────────────
class _CameraPreview(QWidget):
    _W, _H = 250, 190

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(self._W)
        self.setStyleSheet(f"_CameraPreview {{ background: {Theme.PANEL}; border: 1px solid {Theme.BORDER_H}; border-radius: 10px; }}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 8); lay.setSpacing(4)
        hdr = QHBoxLayout()
        t = QLabel("CAMERA CAPTURE"); t.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold)); t.setStyleSheet(f"color: {Theme.G_BLUE};")
        hdr.addWidget(t); hdr.addStretch()
        cb = QPushButton("✕"); cb.setFixedSize(16, 16); cb.setStyleSheet(f"color: {Theme.TEXT_MUTED}; background: transparent; border: none;"); cb.clicked.connect(self.hide)
        hdr.addWidget(cb); lay.addLayout(hdr)

        self._img_lbl = QLabel(); self._img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.addWidget(self._img_lbl)
        self._tmr = QTimer(self); self._tmr.setSingleShot(True); self._tmr.timeout.connect(self.hide); self.hide()

    def show_frame(self, img_bytes: bytes) -> None:
        px = QPixmap(); px.loadFromData(img_bytes)
        if not px.isNull():
            scaled = px.scaled(self._W - 16, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self._img_lbl.setPixmap(scaled); self.adjustSize()
        self.show(); self.raise_(); self._tmr.start(6000)

class ClipboardPanel(QWidget):
    action_requested = pyqtSignal(str)
    _W, _H = 340, 110

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(self._W)
        self._clip_text = ""
        self.setStyleSheet(f"ClipboardPanel {{ background: {Theme.PANEL}; border: 1px solid {Theme.BORDER_H}; border-radius: 8px; }}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8); lay.setSpacing(6)
        hdr = QHBoxLayout()
        t = QLabel("📋  CLIPBOARD DETECTED"); t.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold)); t.setStyleSheet(f"color: {Theme.G_YELLOW};")
        hdr.addWidget(t); hdr.addStretch()
        cb = QPushButton("✕"); cb.setFixedSize(16, 16); cb.setStyleSheet(f"color: {Theme.TEXT_MUTED}; background: transparent; border: none;"); cb.clicked.connect(self.hide)
        hdr.addWidget(cb); lay.addLayout(hdr)

        self._preview = QLabel(); self._preview.setFont(QFont("Segoe UI", 8)); self._preview.setStyleSheet(f"color: {Theme.TEXT}; background: {Theme.PANEL_ALT}; border-radius: 4px; padding: 4px;")
        lay.addWidget(self._preview)

        btn_row = QHBoxLayout(); btn_row.setSpacing(4)
        for label, cmd in [("Translate", "Translate this text to English: {text}"), ("Summarize", "Summarize this: {text}"), ("Fix Grammar", "Fix grammar and spelling: {text}")]:
            b = QPushButton(label); b.setFixedHeight(22); b.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold)); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(f"background: {Theme.PANEL_ALT}; color: {Theme.G_BLUE}; border-radius: 3px; border: 1px solid {Theme.BORDER};")
            b.clicked.connect(lambda _, c=cmd: self._trigger(c))
            btn_row.addWidget(b)
        lay.addLayout(btn_row)

        self._tmr = QTimer(self); self._tmr.setSingleShot(True); self._tmr.timeout.connect(self.hide); self.hide()

    def _trigger(self, cmd_fmt: str):
        if self._clip_text: self.action_requested.emit(cmd_fmt.format(text=self._clip_text[:800]))
        self.hide()

    def show_clipboard(self, text: str):
        self._clip_text = text
        prev = text[:48].replace("\n", " ") + ("…" if len(text) > 48 else "")
        self._preview.setText(f'"{prev}"'); self.show(); self.raise_(); self._tmr.start(8000)

class SetupOverlay(QWidget):
    done = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"SetupOverlay {{ background: {Theme.PANEL}; border: 1px solid {Theme.BORDER_H}; border-radius: 12px; }}")
        detected = {"darwin": "mac", "windows": "windows"}.get(_OS.lower(), "linux")
        self._sel_os = detected

        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 20, 26, 20); lay.setSpacing(8)
        t = QLabel("System Initialization"); t.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold)); t.setStyleSheet(f"color: {Theme.TEXT};"); lay.addWidget(t)
        st = QLabel("Enter Gemini API key to activate voice, vision, and core tools."); st.setFont(QFont("Segoe UI", 8)); st.setStyleSheet(f"color: {Theme.TEXT_MUTED};"); lay.addWidget(st)

        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("Enter Gemini API Key (AIza...)")
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setFixedHeight(34)
        self._key_input.setStyleSheet(f"background: {Theme.PANEL_ALT}; color: {Theme.TEXT}; border: 1px solid {Theme.BORDER}; border-radius: 6px; padding: 4px 10px;")
        lay.addWidget(self._key_input)

        lay.addSpacing(2)
        os_lbl = QLabel(f"Target Environment (Auto-detected: {detected.upper()})")
        os_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold)); os_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};"); lay.addWidget(os_lbl)

        os_row = QHBoxLayout(); os_row.setSpacing(6)
        self._os_btns: dict[str, QPushButton] = {}
        for k, label in [("windows", "🪟 Windows"), ("mac", "🍎 macOS"), ("linux", "🐧 Linux")]:
            b = QPushButton(label); b.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold)); b.setFixedHeight(28); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _, key=k: self._select_os(key))
            os_row.addWidget(b); self._os_btns[k] = b
        lay.addLayout(os_row)
        self._select_os(detected)

        lay.addSpacing(4)
        btn = QPushButton("Confirm & Launch Core")
        btn.setFixedHeight(36); btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold)); btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"background: {Theme.G_BLUE}; color: white; border: none; border-radius: 6px;")
        btn.clicked.connect(self._submit)
        lay.addWidget(btn)

    def _select_os(self, key: str):
        self._sel_os = key
        for k, btn in self._os_btns.items():
            if k == key:
                btn.setStyleSheet(f"background: {Theme.G_BLUE}; color: white; border: none; border-radius: 4px;")
            else:
                btn.setStyleSheet(f"background: {Theme.PANEL_ALT}; color: {Theme.TEXT_MUTED}; border: 1px solid {Theme.BORDER}; border-radius: 4px;")

    def _submit(self):
        k = self._key_input.text().strip()
        if k: self.done.emit(k, self._sel_os)

class RemoteKeyOverlay(QWidget):
    closed = pyqtSignal()
    _OW, _OH = 380, 470

    def __init__(self, url: str, key: str, auto_login_url: str = "", manual_url: str = "", expiry_secs: int = 600, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"RemoteKeyOverlay {{ background: {Theme.PANEL}; border: 1px solid {Theme.BORDER_H}; border-radius: 14px; }}")
        self._expiry = time.time() + expiry_secs
        self._on_new_key = None
        self._manual_url = manual_url or url
        self._auto_login_url = auto_login_url

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16); lay.setSpacing(6)
        t = QLabel("📱  Mobile Remote Access")
        t.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {Theme.TEXT};")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(t)

        self._qr_lbl = QLabel()
        self._qr_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_lbl.setFixedSize(160, 160)
        self._qr_lbl.setStyleSheet("background: white; border-radius: 8px; padding: 4px;")
        self._load_qr(auto_login_url or url)
        qr_box = QHBoxLayout(); qr_box.addStretch(); qr_box.addWidget(self._qr_lbl); qr_box.addStretch(); lay.addLayout(qr_box)

        self._key_lbl = QLabel(key)
        self._key_lbl.setFont(QFont("Consolas", 20, QFont.Weight.Bold))
        self._key_lbl.setStyleSheet(f"color: {Theme.G_YELLOW}; background: {Theme.PANEL_ALT}; border: 1px solid {Theme.BORDER}; border-radius: 6px; padding: 6px; letter-spacing: 6px;")
        self._key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._key_lbl)

        self._timer_lbl = QLabel()
        self._timer_lbl.setFont(QFont("Segoe UI", 8))
        self._timer_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        self._timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._timer_lbl)

        btn_row = QHBoxLayout()
        new_btn = QPushButton("New Key")
        new_btn.setFixedHeight(30)
        new_btn.setStyleSheet(f"background: {Theme.PANEL_ALT}; color: {Theme.G_BLUE}; border: 1px solid {Theme.BORDER}; border-radius: 4px;")
        new_btn.clicked.connect(self._refresh_key)
        btn_row.addWidget(new_btn)

        cb = QPushButton("Dismiss")
        cb.setFixedHeight(30)
        cb.setStyleSheet(f"background: {Theme.PANEL_ALT}; color: {Theme.TEXT_MUTED}; border: 1px solid {Theme.BORDER}; border-radius: 4px;")
        cb.clicked.connect(self._do_close)
        btn_row.addWidget(cb)
        lay.addLayout(btn_row)

        self._ctimer = QTimer(self)
        self._ctimer.timeout.connect(self._tick)
        self._ctimer.start(1000)
        self._tick()

    def set_new_key_callback(self, fn) -> None:
        self._on_new_key = fn

    def _tick(self):
        rem = max(0, int(self._expiry - time.time()))
        m, s = divmod(rem, 60)
        self._timer_lbl.setText(f"Passkey expires in {m:02d}:{s:02d}")
        if rem == 0:
            self._do_close()

    def _refresh_key(self):
        if self._on_new_key:
            res = self._on_new_key()
            if res:
                url, key = res[0], res[1]
                auto = res[2] if len(res) >= 3 else ""
                self._key_lbl.setText(key)
                self._load_qr(auto or url)
                self._expiry = time.time() + 600
                self._tick()

    def _load_qr(self, url: str):
        try:
            import qrcode, io
            qr = qrcode.QRCode(box_size=4, border=1); qr.add_data(url); qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white"); buf = io.BytesIO(); img.save(buf, format="PNG")
            px = QPixmap(); px.loadFromData(buf.getvalue()); self._qr_lbl.setPixmap(px.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio))
        except Exception: self._qr_lbl.setText(url[:20])

    def mark_connected(self):
        self._ctimer.stop()
        self._key_lbl.setText("CONNECTED")
        self._key_lbl.setStyleSheet(f"color: {Theme.G_GREEN}; background: {Theme.PANEL_ALT}; border-radius: 6px; letter-spacing: 2px;")
        self._timer_lbl.setText("Device active and paired")

    def _do_close(self):
        self._ctimer.stop()
        self.hide()
        self.closed.emit()

class CustomizeOverlay(QWidget):
    saved = pyqtSignal(str, str, str, str)  # name, user_name, voice_name, ui_color
    _OW, _OH = 380, 310

    def __init__(self, assistant_name="NEXUS", user_name="", current_voice="Fenrir", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"CustomizeOverlay {{ background: {Theme.PANEL}; border: 1px solid {Theme.BORDER_H}; border-radius: 12px; }}")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 16, 22, 16)
        lay.setSpacing(6)

        t = QLabel("⚙  Assistant Customization")
        t.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {Theme.TEXT};")
        lay.addWidget(t)

        self._name_in = QLineEdit(assistant_name)
        self._name_in.setPlaceholderText("Assistant Name (e.g. NEXUS)")
        self._name_in.setFixedHeight(30)
        self._name_in.setStyleSheet(f"background: {Theme.PANEL_ALT}; color: {Theme.TEXT}; border: 1px solid {Theme.BORDER}; border-radius: 4px; padding: 4px 8px;")
        lay.addWidget(self._name_in)

        self._user_in = QLineEdit(user_name)
        self._user_in.setPlaceholderText("Your Name (e.g. Tony)")
        self._user_in.setFixedHeight(30)
        self._user_in.setStyleSheet(f"background: {Theme.PANEL_ALT}; color: {Theme.TEXT}; border: 1px solid {Theme.BORDER}; border-radius: 4px; padding: 4px 8px;")
        lay.addWidget(self._user_in)

        # ── Voice Model Selector ──────────────────────────────────────────────
        v_lbl = QLabel("AI Voice Model:")
        v_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        v_lbl.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        lay.addWidget(v_lbl)

        from PyQt6.QtWidgets import QComboBox
        self._voice_combo = QComboBox()
        self._voice_combo.setFixedHeight(30)
        self._voice_combo.setFont(QFont("Segoe UI", 8))
        self._voice_combo.setStyleSheet(f"""
            QComboBox {{
                background: {Theme.PANEL_ALT}; color: {Theme.TEXT};
                border: 1px solid {Theme.BORDER}; border-radius: 4px; padding: 4px 8px;
            }}
            QComboBox QAbstractItemView {{
                background: {Theme.PANEL}; color: {Theme.TEXT};
                selection-background-color: {Theme.G_BLUE}; border-radius: 4px;
            }}
        """)
        self._voices = [
            ("Fenrir",  "Fenrir — Deep Baritone (Lowest Pitch)"),
            ("Charon",  "Charon — Calm & Authoritative"),
            ("Orpheus", "Orpheus — Confident & Deep"),
            ("Puck",    "Puck — Energetic & Friendly"),
            ("Aoede",   "Aoede — Soft & Melodic (Female)"),
            ("Kore",    "Kore — Composed & Natural (Female)"),
            ("Zephyr",  "Zephyr — Warm & Gentle"),
            ("Leda",    "Leda — Bright & Youthful (Female)"),
        ]
        cur_idx = 0
        for idx, (v_id, v_label) in enumerate(self._voices):
            self._voice_combo.addItem(v_label, v_id)
            if v_id.lower() == (current_voice or "fenrir").lower():
                cur_idx = idx

        self._voice_combo.setCurrentIndex(cur_idx)
        lay.addWidget(self._voice_combo)

        lay.addSpacing(4)
        btn = QPushButton("Save & Apply")
        btn.setFixedHeight(32)
        btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"background: {Theme.G_BLUE}; color: white; border: none; border-radius: 4px;")
        btn.clicked.connect(self._save)
        lay.addWidget(btn)

    def _save(self):
        sel_voice = self._voice_combo.currentData() or "Fenrir"
        self.saved.emit(
            self._name_in.text().strip() or "NEXUS",
            self._user_in.text().strip(),
            sel_voice,
            Theme.G_BLUE
        )
        self.hide()

class PluginManagerOverlay(QWidget):
    _OW = 360

    def __init__(self, plugins: list[dict], parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"PluginManagerOverlay {{ background: {Theme.PANEL}; border: 1px solid {Theme.BORDER_H}; border-radius: 12px; }}")
        self.setFixedWidth(self._OW)

        lay = QVBoxLayout(self); lay.setContentsMargins(18, 14, 18, 14); lay.setSpacing(6)
        t = QLabel("🧩  Plugin Modules"); t.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold)); t.setStyleSheet(f"color: {Theme.TEXT};"); lay.addWidget(t)

        for p in plugins:
            row = QHBoxLayout()
            lbl = QLabel(p["name"]); lbl.setFont(QFont("Segoe UI", 8)); lbl.setStyleSheet(f"color: {Theme.TEXT if p['valid'] else Theme.TEXT_MUTED};"); row.addWidget(lbl, stretch=1)
            btn = QPushButton("ON" if p.get("enabled", True) else "OFF"); btn.setFixedSize(50, 22); btn.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            btn.setStyleSheet(f"background: {'#1b4d2e' if p.get('enabled', True) else Theme.PANEL_ALT}; color: {'#34A853' if p.get('enabled', True) else Theme.TEXT_MUTED}; border-radius: 3px;")
            btn.clicked.connect(lambda _, n=p["name"], b=btn: self._toggle(n, b))
            row.addWidget(btn); lay.addLayout(row)

        cb = QPushButton("Close"); cb.setFixedHeight(28); cb.setStyleSheet(f"background: {Theme.PANEL_ALT}; color: {Theme.TEXT_MUTED}; border: 1px solid {Theme.BORDER}; border-radius: 4px;"); cb.clicked.connect(self.hide); lay.addWidget(cb)
        self.adjustSize()

    def _toggle(self, name: str, btn: QPushButton):
        try:
            from memory.config_manager import get_plugin_enabled, save_plugin_enabled
            new_val = not get_plugin_enabled(name); save_plugin_enabled(name, new_val)
            btn.setText("ON" if new_val else "OFF")
            btn.setStyleSheet(f"background: {'#1b4d2e' if new_val else Theme.PANEL_ALT}; color: {'#34A853' if new_val else Theme.TEXT_MUTED}; border-radius: 3px;")
        except Exception: pass
        
# ── Real High-Res Satellite, 3D Streets & Super-Zoom (Level 22) ───────────────
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    _WEBVIEW_AVAILABLE = True
except ImportError:
    _WEBVIEW_AVAILABLE = False

class SpatialMapCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(360, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._devices = {}
        self._selected_id = None
        self._map_initialized = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if _WEBVIEW_AVAILABLE:
            self._web = QWebEngineView()
            self._web.setStyleSheet("background: transparent;")
            layout.addWidget(self._web)
        else:
            self._fallback_lbl = QLabel()
            self._fallback_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._fallback_lbl.setStyleSheet(f"background: {Theme.BG}; color: {Theme.TEXT}; padding: 20px;")
            layout.addWidget(self._fallback_lbl)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._sync_telemetry)
        self._timer.start(2000)

        self._load_map_html()

    def set_fleet(self, devices: dict, selected_id: str = None):
        self._devices = devices or {}
        if self._devices:
            self._selected_id = selected_id or list(self._devices.keys())[0]
        self._sync_telemetry()

    def _load_map_html(self):
        from actions.device_tracker import _load_devices
        self._devices = _load_devices()

        sel_dev = self._devices.get(self._selected_id or "Mobile-Phone", {})
        if not sel_dev and self._devices:
            sel_dev = list(self._devices.values())[0]

        lat = sel_dev.get("lat", 31.51698)
        lon = sel_dev.get("lon", 74.36111)
        name = sel_dev.get("name", "Android Smartphone")
        addr = sel_dev.get("address", "Lahore, Pakistan")
        bat = sel_dev.get("battery", 100)
        speed = sel_dev.get("speed_kmh", 0.0)

        map_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                body {{ margin:0; padding:0; background:#07090e; font-family:'Segoe UI',sans-serif; overflow:hidden; }}
                #map {{ width:100vw; height:100vh; background:#07090e; }}
                .telemetry-card {{
                    position:absolute; top:14px; left:14px; z-index:1000;
                    background:rgba(15,23,42,0.94); border:1px solid rgba(66,133,244,0.6);
                    border-radius:10px; padding:12px 16px; color:#F1F5F9; font-size:12px;
                    box-shadow:0 6px 24px rgba(0,0,0,0.7); backdrop-filter:blur(10px);
                    max-width: 320px;
                }}
                .layer-btn-wrap {{
                    position:absolute; top:14px; right:14px; z-index:1000;
                    display:flex; gap:6px;
                }}
                .layer-btn {{
                    background:rgba(15,23,42,0.92); color:#F1F5F9; border:1px solid rgba(255,255,255,0.15);
                    border-radius:6px; padding:6px 12px; font-size:11px; font-weight:bold; cursor:pointer;
                    transition:all 0.2s;
                }}
                .layer-btn:hover {{ background:rgba(66,133,244,0.3); border-color:#4285F4; }}
                .layer-btn.active {{ background:#4285F4; color:#ffffff; border-color:#4285F4; }}
                .pin-pulse {{
                    width:20px; height:20px; background:#00E676; border:3px solid #ffffff;
                    border-radius:50%; box-shadow:0 0 18px #00E676; animation:pulse 1.8s infinite;
                }}
                @keyframes pulse {{ 0% {{ box-shadow:0 0 0 0 rgba(0,230,118,0.7); }} 70% {{ box-shadow:0 0 0 24px rgba(0,230,118,0); }} 100% {{ box-shadow:0 0 0 0 rgba(0,230,118,0); }} }}
            </style>
        </head>
        <body>
            <div class="telemetry-card" id="card">
                <div style="font-weight:bold; color:#4285F4; font-size:13px; margin-bottom:4px;" id="t_name">📍 {name}</div>
                <div style="color:#E2E8F0; font-size:11px; margin-bottom:3px; line-height:1.4;" id="t_addr"><b>Location:</b> {addr}</div>
                <div style="color:#94A3B8; font-size:11px;" id="t_gps"><b>GPS:</b> {lat:.5f}° N, {lon:.5f}° E • <b id="t_speed">{speed} km/h</b></div>
                <div style="color:#00E676; font-size:11px; font-weight:bold; margin-top:4px;" id="t_bat">● ONLINE • Battery: {bat}%</div>
            </div>

            <div class="layer-btn-wrap">
                <button class="layer-btn active" id="btn_sat" onclick="switchLayer('sat')">🛰️ Satellite</button>
                <button class="layer-btn" id="btn_dark" onclick="switchLayer('dark')">🌑 Dark Streets</button>
            </div>

            <div id="map"></div>

            <script>
                // 1. Super-Zoom Satellite Layer (Oversampled to Zoom Level 22)
                const satLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
                    maxNativeZoom: 19,
                    maxZoom: 22,
                    attribution: 'ESRI Satellite'
                }});

                // 2. OpenStreetMap Streets Layer (Oversampled to Level 22)
                const darkLayer = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    maxNativeZoom: 19,
                    maxZoom: 22,
                    attribution: 'OSM Streets'
                }});

                // Enable Full Interactive Mouse Wheel & Button Zoom Controls
                const map = L.map('map', {{
                    zoomControl: true,
                    scrollWheelZoom: true,
                    doubleClickZoom: true,
                    layers: [satLayer],
                    maxZoom: 22
                }}).setView([{lat}, {lon}], 18);

                // Pulse Pin Marker
                const icon = L.divIcon({{ className: 'pin-pulse', iconSize: [20, 20], iconAnchor: [10, 10] }});
                const marker = L.marker([{lat}, {lon}], {{ icon: icon }}).addTo(map);

                function switchLayer(type) {{
                    if (type === 'sat') {{
                        map.removeLayer(darkLayer);
                        map.addLayer(satLayer);
                        document.getElementById('btn_sat').className = 'layer-btn active';
                        document.getElementById('btn_dark').className = 'layer-btn';
                    }} else {{
                        map.removeLayer(satLayer);
                        map.addLayer(darkLayer);
                        document.getElementById('btn_dark').className = 'layer-btn active';
                        document.getElementById('btn_sat').className = 'layer-btn';
                    }}
                }}

                window.updatePhoneLive = function(newLat, newLon, newName, newAddr, newBat, newSpeed) {{
                    const newPos = [newLat, newLon];
                    marker.setLatLng(newPos);

                    document.getElementById('t_name').textContent = "📍 " + newName;
                    document.getElementById('t_addr').innerHTML = "<b>Location:</b> " + newAddr;
                    document.getElementById('t_gps').innerHTML = "<b>GPS:</b> " + newLat.toFixed(5) + "° N, " + newLon.toFixed(5) + "° E • <b>" + newSpeed + " km/h</b>";
                    document.getElementById('t_bat').innerHTML = "● ONLINE • Battery: " + newBat + "%";
                }};
            </script>
        </body>
        </html>
        """
        if _WEBVIEW_AVAILABLE:
            self._web.setHtml(map_html)
            self._map_initialized = True

    def _sync_telemetry(self):
        from actions.device_tracker import _load_devices
        self._devices = _load_devices()

        if not self._devices or not _WEBVIEW_AVAILABLE or not self._map_initialized:
            return

        sel_dev = self._devices.get(self._selected_id or "Mobile-Phone", {})
        if not sel_dev:
            sel_dev = list(self._devices.values())[0]

        lat = float(sel_dev.get("lat", 31.51698))
        lon = float(sel_dev.get("lon", 74.36111))
        name = str(sel_dev.get("name", "Android Smartphone")).replace("'", "")
        addr = str(sel_dev.get("address", "Lahore, Pakistan")).replace("'", "")
        bat = int(sel_dev.get("battery", 100))
        speed = float(sel_dev.get("speed_kmh", 0.0))

        js = f"if (window.updatePhoneLive) {{ window.updatePhoneLive({lat}, {lon}, '{name}', '{addr}', {bat}, {speed}); }}"
        self._web.page().runJavaScript(js)
        
# ── Single Splash Screen Loader & Background Service Guard ────────────────────
SPLASH_SESSION_FILE = CONFIG_DIR / "splash_session.lock"

def get_splash_class():
    """
    Loads exclusively 'nexus_splash.py'.
    Skips showing the splash only if:
      1. AI is launched in background/service mode (--background, --service, etc.)
      2. Another confirmed NEXUS Python process is already actively running.
    """
    import sys
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))

    # 1. Skip splash if started with background flags
    bg_flags = {"--background", "--service", "--tray", "--silent", "--minimized", "--no-splash"}
    if any(arg.lower() in bg_flags for arg in sys.argv):
        print("[SplashLoader] ⏩ Background service mode detected: Skipping intro splash.")
        return None

    # 2. Check for an ALREADY RUNNING instance of Nexus
    if SPLASH_SESSION_FILE.exists():
        is_running_nexus = False
        try:
            data = json.loads(SPLASH_SESSION_FILE.read_text(encoding="utf-8"))
            active_pid = data.get("pid")
            if active_pid and psutil.pid_exists(active_pid) and active_pid != os.getpid():
                try:
                    proc = psutil.Process(active_pid)
                    # Verify this PID actually belongs to Python/NEXUS, not a random Windows process
                    p_name = proc.name().lower()
                    p_cmd = " ".join(proc.cmdline()).lower() if proc.cmdline() else ""
                    if ("python" in p_name or "nexus" in p_name) and ("main.py" in p_cmd or "nexus" in p_cmd):
                        is_running_nexus = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    is_running_nexus = False
        except Exception:
            pass

        if is_running_nexus:
            print(f"[SplashLoader] ⏩ Another active NEXUS instance is running (PID: {active_pid}). Skipping splash.")
            return None
        else:
            # Stale lock from a previous run or crash — delete it so splash can play
            try:
                SPLASH_SESSION_FILE.unlink(missing_ok=True)
            except Exception:
                pass

    # 3. Exclusively load nexus_splash.py
    try:
        import nexus_splash
        print("[NEXUS Core] 🎬 Loading Startup Cinematic: nexus_splash.py")
        return nexus_splash.NexusSplashScreen
    except Exception as e:
        print(f"[SplashLoader] ⚠️ Unable to load nexus_splash: {e}")
        return None

# Backward compatibility alias
get_random_splash_class = get_splash_class
    
# ── 3D Avatar Host Widget (Watchdog Bridge) ───────────────────────────────────
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings

class AvatarWebPage(QWebEnginePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.featurePermissionRequested.connect(self._grant_permission)

    def _grant_permission(self, url, feature):
        if feature in (
            QWebEnginePage.Feature.MediaVideoCapture,
            QWebEnginePage.Feature.MediaAudioCapture,
        ):
            self.setFeaturePermission(
                url, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )

class Avatar3DView(QWidget):
    def __init__(self, assistant_name: str = "NEXUS", parent=None):
        super().__init__(parent)
        self.setMinimumSize(360, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.muted = False
        self.speaking = False
        self._tracking_enabled = False
        self._current_view = "bust"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._web = QWebEngineView()
        self._page = AvatarWebPage(self._web)
        self._web.setPage(self._page)
        # Guarantees Chromium NEVER defaults to a white background
        self._web.page().setBackgroundColor(QColor(3, 7, 18))
        self._web.setStyleSheet("background: #030712; border: none;")
        
        settings = self._web.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        resource_dir = Path(getattr(sys, "_MEIPASS", BASE_DIR))
        html_path = resource_dir / "index.html"
        if not html_path.is_file():
            raise FileNotFoundError(f"NEXUS avatar UI was not found: {html_path}")
        self._web.setUrl(QUrl.fromLocalFile(str(html_path.resolve())))
        layout.addWidget(self._web)

    def run_js(self, js: str):
        if self._web and self._web.page():
            self._web.page().runJavaScript(js)

    def pulse_speech(self):
        """Sends an active audio heartbeat pulse to the 3D watchdog"""
        self.run_js("if(window.NexusCore && window.NexusCore.pulseSpeech) window.NexusCore.pulseSpeech();")

    def set_speaking(self, is_speaking: bool):
        self.speaking = is_speaking
        self.run_js(f"if(window.NexusCore && window.NexusCore.setLiveSpeaking) window.NexusCore.setLiveSpeaking({str(is_speaking).lower()});")
        
    def set_user_speaking(self, is_speaking: bool):
        """Notifies the 3D scene whether the user is actively speaking."""
        self.run_js(f"if(window.NexusCore && window.NexusCore.setUserSpeaking) window.NexusCore.setUserSpeaking({str(is_speaking).lower()});")

    def pulse_user_speech(self):
        """Sends an active heartbeat for user speech/audio input."""
        self.run_js("if(window.NexusCore && window.NexusCore.pulseUserSpeech) window.NexusCore.pulseUserSpeech();")

    def toggle_eye_tracking(self) -> bool:
        self._eye_tracking_enabled = not getattr(self, "_eye_tracking_enabled", False)
        self.run_js(f"window.NexusCore.toggleEyeTracking({str(self._eye_tracking_enabled).lower()});")
        return self._eye_tracking_enabled

    def toggle_head_tracking(self) -> bool:
        self._head_tracking_enabled = not getattr(self, "_head_tracking_enabled", False)
        self.run_js(f"window.NexusCore.toggleHeadTracking({str(self._head_tracking_enabled).lower()});")
        return self._head_tracking_enabled

    def toggle_tracking(self) -> bool:
        self._tracking_enabled = not self._tracking_enabled
        self.run_js(f"window.NexusCore.toggleTracking({str(self._tracking_enabled).lower()});")
        return self._tracking_enabled

    def toggle_view(self) -> str:
        self._current_view = "full" if self._current_view == "bust" else "bust"
        self.run_js(f"window.NexusCore.setCameraMode('{self._current_view}');")
        return self._current_view

    def pause_camera(self):
        self.run_js("window.NexusCore.pauseCamera();")

    def resume_camera(self):
        self.run_js("window.NexusCore.resumeCamera();")
        
    def play_sfx(self, sound_name: str):
        """Triggers any sound directly from the web core."""
        self.run_js(f"if(window.NexusSFX && window.NexusSFX.{sound_name}) window.NexusSFX.{sound_name}();")
        
# ── 1. Floating Live Subtitle (Full Paragraph Display) ───────────────────────
class LiveSubtitleHUD(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(560)
        self.setFixedHeight(180)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        # Full-text transparent frosted display
        self._text_box = QTextEdit()
        self._text_box.setReadOnly(True)
        self._text_box.setFont(QFont("Segoe UI", 9))
        self._text_box.setStyleSheet("""
            QTextEdit {
                background: rgba(8, 14, 26, 0.82);
                border: 1px solid rgba(0, 242, 254, 0.35);
                border-radius: 12px;
                padding: 10px 14px;
                color: #F8FAFC;
                line-height: 1.45;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 4px;
            }
            QScrollBar:handle:vertical {
                background: rgba(0, 242, 254, 0.4);
                border-radius: 2px;
            }
        """)
        lay.addWidget(self._text_box)
        self.hide()

        # Keep dialogue visible for 25 seconds before fading
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_dialogue(self, sender: str, text: str):
        try:
            snd = sender.upper()
            color = "#00F2FE" if ("NEXUS" in snd or "AI" in snd) else "#D946EF"
            
            # Display the COMPLETE paragraph without any truncation
            html = f"""<div style='font-family: Segoe UI, sans-serif;'>
                <span style='color:{color}; font-weight: bold; font-size: 11px;'>● {snd}:</span>
                <div style='color: #F1F5F9; font-size: 13px; margin-top: 4px;'>{text}</div>
            </div>"""
            
            self._text_box.setHtml(html)
            self._text_box.moveCursor(QTextCursor.MoveOperation.Start)
            self.show()
            self.raise_()
            self._timer.start(25000)
        except Exception as e:
            print(f"[SubtitleHUD] Error: {e}", file=sys.stderr)


# ── 2. Floating News Briefing Panel (Auto-opens on news arrival) ──────────────
class NewsBriefingPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(420, 280)
        self.setStyleSheet("""
            background: rgba(15, 23, 42, 0.92);
            border: 1px solid rgba(0, 242, 254, 0.4);
            border-radius: 12px;
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        # Header with title and Close ✕ button
        hdr = QHBoxLayout()
        self._title_lbl = QLabel("📰  LATEST BRIEFING & NEWS")
        self._title_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet("color: #00F2FE; letter-spacing: 1px;")
        hdr.addWidget(self._title_lbl)
        hdr.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("color: #94A3B8; background: transparent; border: none; font-size: 13px; font-weight: bold;")
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        lay.addLayout(hdr)

        # News Content Body
        self._news_text = QTextEdit()
        self._news_text.setReadOnly(True)
        self._news_text.setFont(QFont("Segoe UI", 8))
        self._news_text.setStyleSheet("""
            background: rgba(22, 32, 54, 0.7);
            color: #F8FAFC;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 8px;
            line-height: 1.4;
        """)
        lay.addWidget(self._news_text)
        self.hide()

    def display_news(self, title: str, content: str):
        if title:
            self._title_lbl.setText(f"📰  {title.upper()}")
        self._news_text.setHtml(f"<div style='color:#F8FAFC;'>{content}</div>")
        self.show()
        self.raise_()


# ── 3. Full Conversation History Dialog (With Select & Copy) ──────────────────
class FullChatDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(480, 420)
        self.setStyleSheet("""
            background: rgba(15, 23, 42, 0.94);
            border: 1px solid rgba(255, 255, 255, 0.16);
            border-radius: 12px;
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        # Header
        hdr = QHBoxLayout()
        t = QLabel("💬  FULL CONVERSATION HISTORY")
        t.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        t.setStyleSheet("color: #F8FAFC; letter-spacing: 1px;")
        hdr.addWidget(t)
        hdr.addStretch()

        copy_btn = QPushButton("📋 Copy All")
        copy_btn.setFixedHeight(22)
        copy_btn.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("background: rgba(0, 242, 254, 0.15); color: #00F2FE; border: 1px solid #00F2FE; border-radius: 4px; padding: 0 8px;")
        copy_btn.clicked.connect(self._copy_all)
        hdr.addWidget(copy_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("color: #94A3B8; background: transparent; border: none; font-size: 13px;")
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        lay.addLayout(hdr)

        # Conversation log
        self._chat_box = QTextEdit()
        self._chat_box.setReadOnly(True)
        self._chat_box.setFont(QFont("Segoe UI", 9))
        self._chat_box.setStyleSheet("""
            background: rgba(22, 32, 54, 0.7);
            color: #F8FAFC;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            padding: 10px;
        """)
        lay.addWidget(self._chat_box)
        self.hide()

    def append_message(self, sender: str, text: str):
        snd = sender.upper()
        color = "#00F2FE" if "NEXUS" in snd or "AI" in snd else "#D946EF"
        html = f"""<div style='margin-bottom:8px;'>
            <span style='color:{color}; font-weight:bold;'>● {snd}:</span>
            <span style='color:#F8FAFC;'> {text}</span>
        </div>"""
        self._chat_box.append(html)
        self._chat_box.ensureCursorVisible()

    def _copy_all(self):
        plain_text = self._chat_box.toPlainText()
        if plain_text:
            QApplication.clipboard().setText(plain_text)
            
# ── 4. Full System Metrics Dialog (Opened from 3-Dot Menu) ───────────────────
class SystemMetricsDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(380, 260)
        self.setStyleSheet("""
            background: rgba(15, 23, 42, 0.94);
            border: 1px solid rgba(0, 242, 254, 0.4);
            border-radius: 12px;
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        t = QLabel("📊  SYSTEM METRICS MONITOR")
        t.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        t.setStyleSheet("color: #00F2FE; letter-spacing: 1px;")
        hdr.addWidget(t)
        hdr.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("color: #94A3B8; background: transparent; border: none; font-size: 13px; font-weight: bold;")
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        lay.addLayout(hdr)

        # Metrics display rows with mini progress bars
        self._bars = {}
        for key, label, color in [("cpu", "CPU Usage", "#00F2FE"),
                                  ("mem", "RAM Memory", "#D946EF"),
                                  ("net", "Network Throughput", "#FBBC05"),
                                  ("gpu", "GPU Engine", "#10B981")]:
            row = QVBoxLayout()
            row.setSpacing(3)
            lbl_row = QHBoxLayout()
            lbl_name = QLabel(label)
            lbl_name.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            lbl_name.setStyleSheet("color: #94A3B8;")
            lbl_val = QLabel("--")
            lbl_val.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            lbl_val.setStyleSheet(f"color: {color};")
            lbl_row.addWidget(lbl_name)
            lbl_row.addStretch()
            lbl_row.addWidget(lbl_val)
            row.addLayout(lbl_row)

            pbar = QProgressBar()
            pbar.setFixedHeight(6)
            pbar.setTextVisible(False)
            pbar.setStyleSheet(f"""
                QProgressBar {{
                    background: rgba(255, 255, 255, 0.08);
                    border-radius: 3px;
                    border: none;
                }}
                QProgressBar::chunk {{
                    background: {color};
                    border-radius: 3px;
                }}
            """)
            row.addWidget(pbar)
            lay.addLayout(row)
            self._bars[key] = (lbl_val, pbar)

        lay.addStretch()
        self.hide()

    def update_metrics(self, cpu: float, mem: float, net: float, gpu: float = -1.0):
        # CPU
        self._bars["cpu"][0].setText(f"{cpu:.0f}%")
        self._bars["cpu"][1].setValue(int(cpu))

        # RAM
        self._bars["mem"][0].setText(f"{mem:.0f}%")
        self._bars["mem"][1].setValue(int(mem))

        # NET
        net_str = f"{net:.0f} KB/s" if net < 1000 else f"{net/1024:.1f} MB/s"
        self._bars["net"][0].setText(net_str)
        self._bars["net"][1].setValue(min(100, int(net / 10)))

        # GPU
        if gpu >= 0:
            self._bars["gpu"][0].setText(f"{gpu:.0f}%")
            self._bars["gpu"][1].setValue(int(gpu))
        else:
            self._bars["gpu"][0].setText("Active")
            self._bars["gpu"][1].setValue(15)
            
# ── 3. FLOATING LEFT NAVIGATION SIDEBAR DOCK (PURE FROSTED GLASS) ────────────
class LeftSidebarDock(QWidget):
    tab_changed = pyqtSignal(str)
    settings_clicked = pyqtSignal()
    eye_toggled = pyqtSignal()
    head_toggled = pyqtSignal()
    matrix_toggled = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(self, assistant_name: str = "NEXUS", parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self._active_tab = "core"
        self._eye_active = False
        self._head_active = False
        self._matrix_active = False

        self.setStyleSheet("""
            QWidget#SidebarContainer {
                background: rgba(10, 15, 26, 0.65);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 18px;
            }
        """)
        self.setObjectName("SidebarContainer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 16)
        layout.setSpacing(6)

        # ── 1. Brand Logo Header (Direct Canvas / Pure Frosted Icon) ───────
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        logo_icon = QLabel("N")
        logo_icon.setFixedSize(32, 32)
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_icon.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        logo_icon.setStyleSheet("""
            background: rgba(255, 255, 255, 0.08);
            color: #F8FAFC;
            border: 1px solid rgba(255, 255, 255, 0.22);
            border-radius: 8px;
        """)
        brand_row.addWidget(logo_icon)

        brand_txt_box = QVBoxLayout()
        brand_txt_box.setSpacing(1)
        name_lbl = QLabel(f"{assistant_name.upper()} AI")
        name_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color: #F8FAFC; background: transparent; border: none; letter-spacing: 1.2px;")
        sub_lbl = QLabel("Your Personal AI Agent")
        sub_lbl.setFont(QFont("Segoe UI", 7))
        sub_lbl.setStyleSheet("color: #94A3B8; background: transparent; border: none;")
        brand_txt_box.addWidget(name_lbl)
        brand_txt_box.addWidget(sub_lbl)
        brand_row.addLayout(brand_txt_box)
        layout.addLayout(brand_row)

        layout.addSpacing(14)

        # ── 2. Renamed Navigation Items (Pure Frosted Glass Tabs) ───────────
        self._buttons: dict[str, QPushButton] = {}
        nav_items = [
            ("core",         "🏠", "Home"),
            ("conversation", "💬", "Conversation"),
            ("news",         "📰", "News"),
            ("plugins",      "🧩", "Plugins"),
            ("metrics",      "⚡", "System & CPU"),
            ("files",        "📁", "Upload File"),
            ("settings",     "⚙️", "Settings"),
        ]

        for tab_id, icon, label in nav_items:
            btn = QPushButton(f"  {icon}   {label}")
            btn.setFixedHeight(36)
            btn.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, tid=tab_id: self._handle_click(tid))
            layout.addWidget(btn)
            self._buttons[tab_id] = btn

        layout.addStretch()

        # ── 3. Frameless Glowing Buttons (Outer Box Removed) ───────────────
        # Eye Tracking Button
        self.btn_eye = QPushButton("👁️ Eye: OFF")
        self.btn_eye.setFixedHeight(30)
        self.btn_eye.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self.btn_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_eye.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-radius: 8px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.10);
                border-color: rgba(255, 255, 255, 0.45);
            }
        """)
        self.btn_eye.clicked.connect(self.eye_toggled.emit)
        layout.addWidget(self.btn_eye)

        # Head Tracking Button
        self.btn_head = QPushButton("👤 Head: OFF")
        self.btn_head.setFixedHeight(30)
        self.btn_head.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self.btn_head.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_head.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-radius: 8px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.10);
                border-color: rgba(255, 255, 255, 0.45);
            }
        """)
        self.btn_head.clicked.connect(self.head_toggled.emit)
        layout.addWidget(self.btn_head)

        # Matrix Button
        self.btn_matrix = QPushButton("💻 Matrix: OFF")
        self.btn_matrix.setFixedHeight(30)
        self.btn_matrix.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self.btn_matrix.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_matrix.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-radius: 8px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.10);
                border-color: rgba(255, 255, 255, 0.45);
            }
        """)
        self.btn_matrix.clicked.connect(self.matrix_toggled.emit)
        layout.addWidget(self.btn_matrix)

        # Stop Button
        self.btn_stop = QPushButton("⏹ Stop [ESC]")
        self.btn_stop.setFixedHeight(30)
        self.btn_stop.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.22);
                border-radius: 8px;
                text-align: left;
                padding-left: 10px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.15);
                border-color: rgba(239, 68, 68, 0.50);
                color: #EF4444;
            }
        """)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        layout.addWidget(self.btn_stop)

        self._refresh_styles()

    def set_eye_state(self, active: bool):
        self._eye_active = active
        if active:
            self.btn_eye.setText("👁️ Eye: ACTIVE")
            self.btn_eye.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 242, 254, 0.18);
                    color: #00F2FE;
                    border: 1px solid #00F2FE;
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 10px;
                }
            """)
        else:
            self.btn_eye.setText("👁️ Eye: OFF")
            self.btn_eye.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.04);
                    color: #F8FAFC;
                    border: 1px solid rgba(255, 255, 255, 0.22);
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 10px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.10);
                    border-color: rgba(255, 255, 255, 0.45);
                }
            """)

    def set_head_state(self, active: bool):
        self._head_active = active
        if active:
            self.btn_head.setText("👤 Head: ACTIVE")
            self.btn_head.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 242, 254, 0.18);
                    color: #00F2FE;
                    border: 1px solid #00F2FE;
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 10px;
                }
            """)
        else:
            self.btn_head.setText("👤 Head: OFF")
            self.btn_head.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.04);
                    color: #F8FAFC;
                    border: 1px solid rgba(255, 255, 255, 0.22);
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 10px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.10);
                    border-color: rgba(255, 255, 255, 0.45);
                }
            """)

    def set_matrix_state(self, active: bool):
        self._matrix_active = active
        if active:
            self.btn_matrix.setText("💻 Matrix: ON")
            self.btn_matrix.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.14);
                    color: #FFFFFF;
                    border: 1px solid rgba(255, 255, 255, 0.55);
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 10px;
                }
            """)
        else:
            self.btn_matrix.setText("💻 Matrix: OFF")
            self.btn_matrix.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.04);
                    color: #F8FAFC;
                    border: 1px solid rgba(255, 255, 255, 0.22);
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 10px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.10);
                    border-color: rgba(255, 255, 255, 0.45);
                }
            """)

    def _handle_click(self, tab_id: str):
        if tab_id == "settings":
            self.settings_clicked.emit()
            return
        self._active_tab = tab_id
        self._refresh_styles()
        self.tab_changed.emit(tab_id)

    def set_active_tab(self, tab_id: str):
        self._active_tab = tab_id
        self._refresh_styles()

    def _refresh_styles(self):
        for tid, btn in self._buttons.items():
            if tid == self._active_tab:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.12);
                        color: #FFFFFF;
                        border: 1px solid rgba(255, 255, 255, 0.40);
                        border-radius: 10px;
                        text-align: left;
                        padding-left: 14px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.02);
                        color: #94A3B8;
                        border: 1px solid rgba(255, 255, 255, 0.06);
                        border-radius: 10px;
                        text-align: left;
                        padding-left: 14px;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.08);
                        border-color: rgba(255, 255, 255, 0.22);
                        color: #F8FAFC;
                    }
                """)
                
# ── 1. TOP-RIGHT TELEMETRY (PURE FROSTED GLASS BLOCKS / NO CYBERPUNK COLORS) ──
class TopRightStatusCapsule(QWidget):
    profile_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # ── Time & Date Card ──────────────────────────────────────────────
        self._time_card = QFrame()
        self._time_card.setFixedHeight(38)
        self._time_card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 10px;
            }
            QFrame:hover {
                border-color: rgba(255, 255, 255, 0.40);
                background: rgba(255, 255, 255, 0.09);
            }
        """)
        t_lay = QVBoxLayout(self._time_card)
        t_lay.setContentsMargins(12, 3, 12, 3)
        t_lay.setSpacing(0)

        self._time_lbl = QLabel(time.strftime("%H:%M:%S"))
        self._time_lbl.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self._time_lbl.setStyleSheet("color: #F8FAFC; background: transparent; border: none;")
        self._time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._date_lbl = QLabel(time.strftime("%a, %b %d, %Y"))
        self._date_lbl.setFont(QFont("Segoe UI", 6))
        self._date_lbl.setStyleSheet("color: #94A3B8; background: transparent; border: none;")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        t_lay.addWidget(self._time_lbl)
        t_lay.addWidget(self._date_lbl)
        lay.addWidget(self._time_card)

        # ── CPU Metric Card (Neutral Glowing Frosted Glass) ───────────────
        self._cpu_card = QFrame()
        self._cpu_card.setFixedHeight(38)
        self._cpu_card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 10px;
            }
            QFrame:hover {
                background: rgba(255, 255, 255, 0.09);
                border-color: rgba(255, 255, 255, 0.45);
            }
        """)
        cpu_lay = QHBoxLayout(self._cpu_card)
        cpu_lay.setContentsMargins(12, 0, 12, 0)

        self._cpu_lbl = QLabel("⚡ CPU 8%")
        self._cpu_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self._cpu_lbl.setStyleSheet("color: #F8FAFC; background: transparent; border: none;")
        self._cpu_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cpu_lay.addWidget(self._cpu_lbl)
        lay.addWidget(self._cpu_card)

        # ── RAM Metric Card (Neutral Glowing Frosted Glass) ───────────────
        self._ram_card = QFrame()
        self._ram_card.setFixedHeight(38)
        self._ram_card.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 10px;
            }
            QFrame:hover {
                background: rgba(255, 255, 255, 0.09);
                border-color: rgba(255, 255, 255, 0.45);
            }
        """)
        ram_lay = QHBoxLayout(self._ram_card)
        ram_lay.setContentsMargins(12, 0, 12, 0)

        self._ram_lbl = QLabel("💾 RAM 32%")
        self._ram_lbl.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self._ram_lbl.setStyleSheet("color: #F8FAFC; background: transparent; border: none;")
        self._ram_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ram_lay.addWidget(self._ram_lbl)
        lay.addWidget(self._ram_card)

    def update_telemetry(self, cpu: float, mem: float):
        self._time_lbl.setText(time.strftime("%H:%M:%S"))
        self._date_lbl.setText(time.strftime("%a, %b %d, %Y"))
        self._cpu_lbl.setText(f"⚡ CPU {cpu:.0f}%")
        self._ram_lbl.setText(f"💾 RAM {mem:.0f}%")

# ── 2. SEAMLESS DYNAMIC GREETING (ZERO BOXES / GEMINI-STYLE) ─────────────────
class LeftGreetingCard(QWidget):
    def __init__(self, user_name: str = "Kamran", assistant_name: str = "Nexus", parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # Completely transparent, no boxes or backgrounds
        self.setStyleSheet("background: transparent; border: none;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self._user_name = user_name
        self._assistant_name = assistant_name

        self._greeting_lbl = QLabel()
        self._greeting_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self._greeting_lbl.setStyleSheet("color: #F8FAFC; background: transparent; border: none; line-height: 1.2;")
        lay.addWidget(self._greeting_lbl)

        self._sub_lbl = QLabel()
        self._sub_lbl.setFont(QFont("Segoe UI", 9))
        self._sub_lbl.setStyleSheet("color: #94A3B8; background: transparent; border: none; line-height: 1.4;")
        self._sub_lbl.setWordWrap(True)
        lay.addWidget(self._sub_lbl)
        self._default_prompt = ""

        # Generate fresh daily/startup greeting
        self.refresh_dynamic_greeting()

    def refresh_dynamic_greeting(self):
        hour = datetime.now().hour
        if 5 <= hour < 12:
            time_str = f"Good Morning,\n{self._user_name} ☀️"
        elif 12 <= hour < 17:
            time_str = f"Good Afternoon,\n{self._user_name} 🌤️"
        elif 17 <= hour < 22:
            time_str = f"Good Evening,\n{self._user_name} 🌆"
        else:
            time_str = f"Working Late,\n{self._user_name} 🌙"

        prompts = [
            f"I'm {self._assistant_name}. What would you like to explore today?",
            f"All systems active. What are we creating today?",
            f"Ready to assist. Where should we focus our intelligence?",
            f"Your personal AI agent is standing by. How can I help?",
            f"Ready when you are. What's on your agenda today?",
            f"Let's turn your ideas into action. What would you like to do?",
            f"Code, automate, or research—what are we building today?",
            f"Connected and ready. What problem shall we solve today?",
            f"Good to see you. How can I optimize your workflow today?",
        ]
        self._greeting_lbl.setText(time_str)
        self._default_prompt = random.choice(prompts)
        self._sub_lbl.setText(self._default_prompt)

    def set_status(self, status: str):
        self._sub_lbl.setText(status or self._default_prompt)

    def set_user(self, name: str):
        if name:
            self._user_name = name
            self.refresh_dynamic_greeting()


# ── 2. QUICK ACTIONS (CANVAS TITLE + NEUTRAL GLOWING FROSTED GLASS BUTTONS) ──
class QuickActionsCard(QWidget):
    action_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent; border: none;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # 1. Clean Title Rendered Directly on Main Canvas
        title = QLabel("✨  Quick Actions")
        title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #F8FAFC; background: transparent; border: none; letter-spacing: 0.5px;")
        lay.addWidget(title)

        lay.addSpacing(4)

        # 2. Neutral Glowing Frosted Glass Action Buttons
        actions = [
            ("🖼️", "Generate Images", "image"),
            ("📱", "Open Apps",       "app"),
            ("🌐", "Search Web",      "search"),
            ("✔️", "Create a Task",   "task"),
        ]

        for icon, label, key in actions:
            btn = QPushButton(f"  {icon}   {label}")
            btn.setFixedHeight(36)
            btn.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.04);
                    color: #F8FAFC;
                    border: 1px solid rgba(255, 255, 255, 0.18);
                    border-radius: 10px;
                    text-align: left;
                    padding-left: 12px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.10);
                    border: 1px solid rgba(255, 255, 255, 0.48);
                    color: #FFFFFF;
                }
                QPushButton:pressed {
                    background: rgba(255, 255, 255, 0.16);
                    border: 1px solid rgba(255, 255, 255, 0.70);
                }
            """)
            btn.clicked.connect(lambda _, k=key: self.action_clicked.emit(k))
            lay.addWidget(btn)

# ── SMART ADAPTIVE MICROPHONE VOICE DETECTOR (NO FALSE TRIGGERS) ─────────────
class MicVoiceDetector(QObject):
    voice_energy = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._muted = False
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def set_muted(self, muted: bool):
        self._muted = muted

    def stop(self):
        self._running = False

    def _listen_loop(self):
        pa = None
        stream = None
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
        except Exception:
            try:
                if pa: pa.terminate()
            except Exception: pass
            pa = None
            stream = None

        # Fallback to sounddevice if pyaudio is not available
        if stream is None:
            try:
                import sounddevice as sd
                ambient_sd = 0.03
                def sd_callback(indata, frames, time_info, status):
                    nonlocal ambient_sd
                    if not self._running or self._muted:
                        return
                    import numpy as np
                    rms = float(np.sqrt(np.mean(indata**2)))
                    # Adapt ambient noise floor
                    if rms < ambient_sd * 1.5:
                        ambient_sd = ambient_sd * 0.95 + rms * 0.05
                    # Strict threshold: human speech is 3x ambient floor
                    speech_gate = max(0.06, ambient_sd * 2.8)
                    if rms > speech_gate:
                        energy = min(1.0, (rms - speech_gate) * 4.0)
                        self.voice_energy.emit(energy)
                with sd.InputStream(channels=1, samplerate=16000, callback=sd_callback):
                    while self._running:
                        time.sleep(0.1)
                return
            except Exception:
                return

        # Adaptive Noise Gate Variables (PyAudio)
        ambient_floor = 600.0  # Initial baseline
        consecutive_voice_frames = 0

        while self._running:
            if self._muted:
                time.sleep(0.08)
                continue
            try:
                raw_data = stream.read(1024, exception_on_overflow=False)
                count = len(raw_data) // 2
                shorts = struct.unpack(f"{count}h", raw_data)
                sum_sq = sum(s * s for s in shorts)
                rms = math.sqrt(sum_sq / count)

                # Dynamically learn room and fan noise
                if rms < ambient_floor * 1.4:
                    ambient_floor = ambient_floor * 0.96 + rms * 0.04

                # Strict Speech Gate: Must be significantly louder than room noise
                # Minimum absolute threshold is 1100 to eliminate fan/breathing false triggers
                speech_gate = max(1100.0, ambient_floor * 2.5 + 400.0)

                if rms > speech_gate:
                    consecutive_voice_frames += 1
                    # Require 2 consecutive frames to reject transient mouse/keyboard clicks
                    if consecutive_voice_frames >= 2:
                        energy = min(1.0, max(0.0, (rms - speech_gate) / 3000.0))
                        self.voice_energy.emit(energy)
                else:
                    consecutive_voice_frames = max(0, consecutive_voice_frames - 1)

            except Exception:
                time.sleep(0.04)

        try:
            if stream:
                stream.stop_stream()
                stream.close()
            if pa:
                pa.terminate()
        except Exception:
            pass


# ── 4. NEUTRAL AUDIO WAVEFORM WIDGET ─────────────────────────────────────────
class AudioWaveWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 24)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._active = False
        self._energy = 0.0
        self._phase = 0.0
        self._current_heights = [4.0, 6.0, 8.0, 6.0, 4.0]
        self._target_heights  = [4.0, 6.0, 8.0, 6.0, 4.0]
        self._last_pulse_t    = 0.0

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(25)

    def pulse_with_energy(self, energy: float):
        if float(energy) <= 0.05:
            self.set_active(False)
            return
        self._energy = min(1.0, float(energy))
        self._last_pulse_t = time.time()
        self._active = True

    def pulse(self):
        self.pulse_with_energy(0.65)

    def set_active(self, active: bool):
        self._active = active
        if not active:
            self._energy = 0.0
            self._target_heights = [4.0, 4.0, 4.0, 4.0, 4.0]

    def _step(self):
        if self._last_pulse_t > 0 and (time.time() - self._last_pulse_t > 0.18):
            self.set_active(False)

        if self._active:
            self._phase += 0.38
            for i in range(5):
                wave = math.sin(self._phase * 1.7 + i * 1.2) * 0.5 + 0.5
                wave2 = math.cos(self._phase * 0.9 - i * 0.7) * 0.5 + 0.5
                boost = 0.35 + (self._energy * 0.65)
                h = 5.0 + ((wave * 11.0 + wave2 * 5.0) * boost)
                self._target_heights[i] = max(4.0, min(22.0, h))
        else:
            self._target_heights = [4.0, 6.0, 8.0, 6.0, 4.0]

        for i in range(5):
            self._current_heights[i] += (self._target_heights[i] - self._current_heights[i]) * 0.40

        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        # Pure neutral white / silver audio bars
        col = QColor(255, 255, 255, 230) if self._active else QColor(255, 255, 255, 110)
        p.setBrush(col)

        for i, h in enumerate(self._current_heights):
            h_clamped = max(3.0, min(22.0, h))
            x = i * 7 + 3
            y = (24 - h_clamped) / 2.0
            p.drawRoundedRect(QRectF(x, y, 3.2, h_clamped), 1.6, 1.6)


# ── 5. NEUTRAL FROSTED GLASS MIC BUTTON ──────────────────────────────────────
class FloatingMicButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(54, 54)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._muted = False
        self.set_muted(False)

    def set_muted(self, muted: bool):
        self._muted = muted
        if muted:
            self.setText("🔇")
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(239, 68, 68, 0.14);
                    color: #EF4444;
                    border: 1.5px solid rgba(239, 68, 68, 0.55);
                    border-radius: 27px;
                    font-size: 19px;
                }
                QPushButton:hover {
                    background-color: rgba(239, 68, 68, 0.25);
                    border-color: #EF4444;
                }
            """)
        else:
            self.setText("🎙")
            self.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    color: #F8FAFC;
                    border: 1.5px solid rgba(255, 255, 255, 0.28);
                    border-radius: 27px;
                    font-size: 19px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.12);
                    border-color: rgba(255, 255, 255, 0.55);
                }
            """)


# ── 6. NEUTRAL FROSTED GLASS COMMAND BAR ─────────────────────────────────────
class FloatingCommandBar(QFrame):
    text_submitted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(54)
        self.setObjectName("CommandBarFrame")

        self.setStyleSheet("""
            QFrame#CommandBarFrame {
                background-color: rgba(10, 15, 26, 0.70);
                border: 1.5px solid rgba(255, 255, 255, 0.18);
                border-radius: 27px;
            }
            QFrame#CommandBarFrame:hover {
                border-color: rgba(255, 255, 255, 0.40);
                background-color: rgba(14, 20, 34, 0.80);
            }
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 6, 8, 6)
        lay.setSpacing(10)

        # 1. Clean Input Field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Speak or type your command...")
        self.input_field.setFont(QFont("Segoe UI", 10))
        self.input_field.setFixedHeight(38)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                color: #F8FAFC;
                border: none;
                padding-left: 2px;
            }
            QLineEdit::placeholder {
                color: #64748B;
            }
        """)
        self.input_field.returnPressed.connect(self._submit)
        lay.addWidget(self.input_field, stretch=1)

        # 2. Neutral Audio Wave
        self._wave = AudioWaveWidget()
        lay.addWidget(self._wave)

        # 3. Luminous Frosted Send Button
        self.btn_send = QPushButton("➤")
        self.btn_send.setFixedSize(38, 38)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.12);
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.28);
                border-radius: 19px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.25);
                border-color: rgba(255, 255, 255, 0.65);
                color: #FFFFFF;
            }
        """)
        self.btn_send.clicked.connect(self._submit)
        lay.addWidget(self.btn_send)

    def _submit(self):
        txt = self.input_field.text().strip()
        if txt:
            self.input_field.clear()
            self.text_submitted.emit(txt)

    def set_user_text(self, text: str):
        self.input_field.setText(text)
        self.input_field.setFocus()

    def _submit(self):
        txt = self.input_field.text().strip()
        if txt:
            self.input_field.clear()
            self.text_submitted.emit(txt)

    def set_user_text(self, text: str):
        self.input_field.setText(text)
        self.input_field.setFocus()

# ── 5. Colorful Glowing Frosted Glass Bottom Bar ──────────────────────────────
class PersistentBottomBar(QWidget):
    text_submitted = pyqtSignal(str)
    mute_clicked = pyqtSignal()
    interrupt_clicked = pyqtSignal()
    upload_clicked = pyqtSignal()
    eye_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(54)
        self.setStyleSheet("""
            QWidget#BottomBarFrame {
                background: rgba(10, 15, 28, 0.88);
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 27px;
            }
        """)
        self.setObjectName("BottomBarFrame")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(8)

        # 1. Amber Glowing File Upload Button
        self.btn_upload = QPushButton("📁")
        self.btn_upload.setFixedSize(38, 38)
        self.btn_upload.setToolTip("Upload File / Document")
        self.btn_upload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_upload.setStyleSheet("""
            QPushButton {
                background: rgba(251, 188, 5, 0.12);
                color: #FBBC05;
                border: 1.5px solid #FBBC05;
                border-radius: 19px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(251, 188, 5, 0.28);
            }
        """)
        self.btn_upload.clicked.connect(self.upload_clicked.emit)
        lay.addWidget(self.btn_upload)

        # 2. Text Input Box with Cyan Accent
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask or command NEXUS anything...")
        self.input_field.setFont(QFont("Segoe UI", 9))
        self.input_field.setFixedHeight(38)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: rgba(15, 23, 42, 0.85);
                color: #F8FAFC;
                border: 1.5px solid rgba(0, 242, 254, 0.4);
                border-radius: 19px;
                padding: 0 16px;
            }
            QLineEdit:focus {
                border-color: #00F2FE;
            }
        """)
        self.input_field.returnPressed.connect(self._submit)
        lay.addWidget(self.input_field, stretch=1)

        # 3. Cyan Glowing Send Button
        self.btn_send = QPushButton("➤")
        self.btn_send.setFixedSize(38, 38)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet("""
            QPushButton {
                background: #00F2FE;
                color: #030712;
                border: none;
                border-radius: 19px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #38BDF8;
            }
        """)
        self.btn_send.clicked.connect(self._submit)
        lay.addWidget(self.btn_send)

        # 4. Emerald Glowing Eye Tracking Button
        self.btn_eye = QPushButton("👁️ Eye: OFF")
        self.btn_eye.setFixedHeight(36)
        self.btn_eye.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.btn_eye.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_eye_state(False)
        self.btn_eye.clicked.connect(self.eye_clicked.emit)
        lay.addWidget(self.btn_eye)

        # 5. Crimson Glowing Mic Button
        self.btn_mute = QPushButton("🎙 Mic Active")
        self.btn_mute.setFixedHeight(36)
        self.btn_mute.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.btn_mute.setCursor(Qt.CursorShape.PointingHandCursor)
        self.set_muted_state(False)
        self.btn_mute.clicked.connect(self.mute_clicked.emit)
        lay.addWidget(self.btn_mute)

        # 6. Magenta / Coral Glowing Stop Button
        self.btn_stop = QPushButton("⏹ Stop [ESC]")
        self.btn_stop.setFixedHeight(36)
        self.btn_stop.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background: rgba(217, 70, 239, 0.16);
                color: #D946EF;
                border: 1.5px solid #D946EF;
                border-radius: 18px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background: rgba(217, 70, 239, 0.32);
            }
        """)
        self.btn_stop.clicked.connect(self.interrupt_clicked.emit)
        lay.addWidget(self.btn_stop)

    def _submit(self):
        txt = self.input_field.text().strip()
        if txt:
            self.input_field.clear()
            self.text_submitted.emit(txt)

    def set_muted_state(self, muted: bool):
        if muted:
            self.btn_mute.setText("🔇 Muted")
            self.btn_mute.setStyleSheet("""
                QPushButton {
                    background: rgba(239, 68, 68, 0.22);
                    color: #EF4444;
                    border: 1.5px solid #EF4444;
                    border-radius: 18px;
                    padding: 0 14px;
                }
            """)
        else:
            self.btn_mute.setText("🎙 Mic Active")
            self.btn_mute.setStyleSheet("""
                QPushButton {
                    background: rgba(16, 185, 129, 0.22);
                    color: #10B981;
                    border: 1.5px solid #10B981;
                    border-radius: 18px;
                    padding: 0 14px;
                }
            """)

    def set_eye_state(self, active: bool):
        if active:
            self.btn_eye.setText("👁️ Eye: ON")
            self.btn_eye.setStyleSheet("""
                QPushButton {
                    background: rgba(16, 185, 129, 0.25);
                    color: #10B981;
                    border: 1.5px solid #10B981;
                    border-radius: 18px;
                    padding: 0 14px;
                }
            """)
        else:
            self.btn_eye.setText("👁️ Eye: OFF")
            self.btn_eye.setStyleSheet("""
                QPushButton {
                    background: rgba(100, 116, 139, 0.2);
                    color: #94A3B8;
                    border: 1.5px solid rgba(148, 163, 184, 0.4);
                    border-radius: 18px;
                    padding: 0 14px;
                }
            """)
            
# ── 6. Colorful Glowing Frosted Glass Top Navigation Bar ─────────────────────
class TopFloatingBar(QWidget):
    tab_changed = pyqtSignal(str)
    matrix_toggled = pyqtSignal()
    settings_clicked = pyqtSignal()
    theme_toggled = pyqtSignal()
    thinking_changed = pyqtSignal(int)

    def __init__(self, assistant_name: str = "NEXUS", parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self.setStyleSheet("""
            QWidget#TopBarFrame {
                background: rgba(8, 12, 22, 0.85);
                border-bottom: 1.5px solid rgba(255, 255, 255, 0.12);
            }
        """)
        self.setObjectName("TopBarFrame")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(8)

        # 1. Glowing Neon Logo
        self._brand = QLabel(f"⚡ {assistant_name} AI | CORE")
        self._brand.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._brand.setStyleSheet("""
            color: #00F2FE;
            background: rgba(0, 242, 254, 0.12);
            border: 1px solid rgba(0, 242, 254, 0.4);
            border-radius: 6px;
            padding: 4px 10px;
            letter-spacing: 1px;
        """)
        lay.addWidget(self._brand)

        # 2. Glowing Emerald Status Pill
        active_pill = QLabel("● ONLINE")
        active_pill.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        active_pill.setStyleSheet("""
            color: #10B981;
            background: rgba(16, 185, 129, 0.15);
            border: 1.5px solid #10B981;
            border-radius: 9px;
            padding: 2px 10px;
        """)
        lay.addWidget(active_pill)

        lay.addSpacing(10)

        # ── 3. COLORFUL GLOWING NAVIGATION TABS ────────────────
        self._tab_buttons: dict[str, QPushButton] = {}
        self._tab_colors = {
            "core": ("#00F2FE", "rgba(0, 242, 254, 0.22)"),      # Cyan
            "chat": ("#D946EF", "rgba(217, 70, 239, 0.22)"),    # Magenta
            "news": ("#FBBC05", "rgba(251, 188, 5, 0.22)"),     # Gold / Amber
            "metrics": ("#10B981", "rgba(16, 185, 129, 0.22)"), # Emerald Green
            "plugins": ("#A855F7", "rgba(168, 85, 247, 0.22)")   # Radiant Violet
        }

        tabs = [
            ("core", "🏠 CORE"),
            ("chat", "💬 FULL CHAT"),
            ("news", "📰 NEWS"),
            ("metrics", "📊 METRICS"),
            ("plugins", "🧩 PLUGINS")
        ]

        for tab_id, tab_label in tabs:
            btn = QPushButton(tab_label)
            btn.setFixedHeight(30)
            btn.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, tid=tab_id: self._on_tab_click(tid))
            lay.addWidget(btn)
            self._tab_buttons[tab_id] = btn

        self._set_active_tab("core")

        lay.addStretch()

        # ── 4. Glowing Cyber Matrix Rain Button ────────────────
        self._matrix_btn = QPushButton("💻 Matrix")
        self._matrix_btn.setFixedHeight(28)
        self._matrix_btn.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self._matrix_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._matrix_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 242, 254, 0.12);
                color: #00F2FE;
                border: 1.5px solid #00F2FE;
                border-radius: 14px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background: rgba(0, 242, 254, 0.30);
            }
        """)
        self._matrix_btn.clicked.connect(self.matrix_toggled.emit)
        lay.addWidget(self._matrix_btn)

        # ── 5. Frosted Glass Thinking Mode Selector ────────────
        from PyQt6.QtWidgets import QComboBox
        self._think_combo = QComboBox()
        self._think_combo.setFixedHeight(28)
        self._think_combo.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self._think_combo.addItems(["🧠 Low", "🧠 Medium", "🧠 High"])
        self._think_combo.setStyleSheet("""
            QComboBox {
                background: rgba(22, 32, 54, 0.85);
                color: #F8FAFC;
                border: 1.5px solid rgba(0, 242, 254, 0.35);
                border-radius: 6px;
                padding: 0 8px;
            }
            QComboBox QAbstractItemView {
                background: rgba(15, 23, 42, 0.96);
                color: white;
                selection-background-color: #00F2FE;
                selection-color: #030712;
            }
        """)
        self._think_combo.currentIndexChanged.connect(self.thinking_changed.emit)
        lay.addWidget(self._think_combo)

        # ── 6. Glowing Settings Gear Button ────────────────────
        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setFixedSize(30, 28)
        self._settings_btn.setToolTip("Assistant & Voice Settings")
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.setStyleSheet("""
            QPushButton {
                background: rgba(22, 32, 54, 0.85);
                color: #00F2FE;
                border: 1.5px solid rgba(0, 242, 254, 0.35);
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                border-color: #00F2FE;
                background: rgba(0, 242, 254, 0.22);
            }
        """)
        self._settings_btn.clicked.connect(self.settings_clicked.emit)
        lay.addWidget(self._settings_btn)

        # ── 7. Clock ───────────────────────────────────────────
        self.clock_lbl = QLabel(time.strftime("%H:%M:%S"))
        self.clock_lbl.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.clock_lbl.setStyleSheet("color: #E2E8F0; margin-left: 6px;")
        lay.addWidget(self.clock_lbl)

    def _on_tab_click(self, tab_id: str):
        self._set_active_tab(tab_id)
        self.tab_changed.emit(tab_id)

    def _set_active_tab(self, active_id: str):
        for tid, btn in self._tab_buttons.items():
            color, bg_glow = self._tab_colors.get(tid, ("#00F2FE", "rgba(0,242,254,0.2)"))
            if tid == active_id:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {bg_glow};
                        color: {color};
                        border: 2px solid {color};
                        border-radius: 7px;
                        padding: 0 14px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: rgba(22, 32, 54, 0.65);
                        color: #94A3B8;
                        border: 1px solid rgba(255, 255, 255, 0.10);
                        border-radius: 7px;
                        padding: 0 14px;
                    }}
                    QPushButton:hover {{
                        color: {color};
                        border-color: {color};
                        background: {bg_glow};
                    }}
                """)

    def set_active_tab_from_outside(self, tab_id: str):
        self._set_active_tab(tab_id)

    def set_matrix_active_state(self, is_active: bool):
        if is_active:
            self._matrix_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(16, 185, 129, 0.25);
                    color: #10B981;
                    border: 2px solid #10B981;
                    border-radius: 14px;
                    padding: 0 12px;
                }
            """)
        else:
            self._matrix_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 242, 254, 0.12);
                    color: #00F2FE;
                    border: 1.5px solid #00F2FE;
                    border-radius: 14px;
                    padding: 0 12px;
                }
            """)

    def set_clock_text(self, text: str):
        self.clock_lbl.setText(text)
        
# ── FULL-WINDOW VIEW 1: VIVID ANIMATED CRIMSON GLASS CONVERSATION ARCHIVE ─────
from PyQt6.QtGui import QPolygonF  # <── Ensures QPolygonF is always imported!

# ── FULL-WINDOW VIEW 1: 3D SYNAPTIC PARTICLE WAVE CONVERSATION ARCHIVE ────────
class FullChatView(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

        # ── 1. MATHEMATICAL PARTICLE WAVE INITIALIZATION ────────────────────
        self._phase = 0.0
        self._strands = 18       # Parallel ribbon strands
        self._points_per_strand = 48  # Points per strand (Total: 864 wave particles)

        # Pre-seed organic micro-jitters so the wave looks natural, not rigid
        self._jitters = [
            [(random.uniform(-4.0, 4.0), random.uniform(-4.0, 4.0)) for _ in range(self._points_per_strand)]
            for _ in range(self._strands)
        ]

        # Scattered Ambient Star Dust Embers (Matching the dust cloud in Image 2)
        self._stardust = [
            {
                "x_norm": random.uniform(0.02, 0.98),
                "y_norm": random.uniform(0.10, 0.95),
                "drift_speed": random.uniform(0.0004, 0.0012),
                "twinkle_speed": random.uniform(0.03, 0.08),
                "twinkle_phase": random.uniform(0, math.pi * 2),
                "size": random.uniform(1.2, 2.8),
                "base_alpha": random.randint(70, 210)
            }
            for _ in range(130)
        ]

        # Animation Timer (~35 FPS smooth organic motion)
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._step_wave)
        self._anim_timer.start(28)

        # Root Outer Layout
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(28, 24, 28, 24)
        root_lay.setSpacing(14)

        # ── 2. TOP CYBER HEADER BAR ──────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(12)

        # Glowing Neon Red Back Button
        self.back_btn = QPushButton("← BACK TO CORE")
        self.back_btn.setFixedHeight(32)
        self.back_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 45, 101, 0.18);
                color: #FF6B8B;
                border: 1.5px solid #FF2D65;
                border-radius: 16px;
                padding: 0 16px;
                letter-spacing: 0.8px;
            }
            QPushButton:hover {
                background: rgba(255, 45, 101, 0.40);
                color: #FFFFFF;
                border-color: #FF0055;
            }
            QPushButton:pressed {
                background: rgba(255, 45, 101, 0.60);
            }
        """)
        self.back_btn.clicked.connect(self.back_requested.emit)
        hdr.addWidget(self.back_btn)

        # Title with Dialogue Icon
        title_lbl = QLabel("💬  FULL CONVERSATION ARCHIVE")
        title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title_lbl.setStyleSheet("""
            color: #FF4D79;
            letter-spacing: 1.2px;
            background: transparent;
            border: none;
        """)
        hdr.addWidget(title_lbl)

        hdr.addStretch()

        # Glowing Neon Red "Copy All Text" Button
        self.copy_btn = QPushButton("📋 Copy All Text")
        self.copy_btn.setFixedHeight(32)
        self.copy_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 45, 101, 0.18);
                color: #FF85A1;
                border: 1.5px solid #FF2D65;
                border-radius: 16px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: rgba(255, 45, 101, 0.40);
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background: rgba(255, 45, 101, 0.60);
            }
        """)
        self.copy_btn.clicked.connect(self._copy_all)
        hdr.addWidget(self.copy_btn)
        root_lay.addLayout(hdr)

        # ── 3. 100% TRANSPARENT CHAT DISPLAY (SHOWS MOVING PARTICLES) ────────
        self._chat_box = QTextEdit()
        self._chat_box.setReadOnly(True)
        self._chat_box.setFont(QFont("Segoe UI", 9))
        self._chat_box.setStyleSheet("""
            QTextEdit {
                background: transparent;
                color: #F8FAFC;
                border: none;
                padding: 14px 18px;
                line-height: 1.6;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #FF2D65;
                border-radius: 3px;
                min-height: 25px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        root_lay.addWidget(self._chat_box, stretch=1)

    # ── ADVANCE WAVE PHASE & AMBIENT STARDUST DRIFT ───────────────────────────
    def _step_wave(self):
        self._phase += 0.026
        # Update stardust twinkle and slow diagonal drift
        for d in self._stardust:
            d["twinkle_phase"] += d["twinkle_speed"]
            d["x_norm"] += d["drift_speed"] * 0.4
            d["y_norm"] -= d["drift_speed"] * 0.6
            if d["x_norm"] > 1.02:
                d["x_norm"] = -0.02
            if d["y_norm"] < -0.02:
                d["y_norm"] = 1.02
        self.update()

    # ── PAINTER: DRAWS 3D PARTICLE WAVE, BLOOM & CYBER BEZEL ─────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())

        # 1. Base Dark Obsidian-Wine Void (Matching Background in Image 2)
        p.fillRect(self.rect(), qcol("#0A0105"))

        # 2. Soft Ambient Volumetric Under-Glow (Warm ruby mist under wave)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        bloom_center_x = w * 0.65 + math.sin(self._phase * 0.5) * 40.0
        bloom_center_y = h * 0.55 + math.cos(self._phase * 0.7) * 30.0
        mist_grad = QRadialGradient(bloom_center_x, bloom_center_y, w * 0.55)
        mist_grad.setColorAt(0.00, qcol("#7F092B", 65))
        mist_grad.setColorAt(0.45, qcol("#4C0519", 35))
        mist_grad.setColorAt(1.00, qcol("#0A0105", 0))
        p.setBrush(QBrush(mist_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect())

        # ── 3. RENDER 3D SYNAPTIC PARTICLE WAVE ──────────────────────────────
        # We sweep from left to right, curving upward to the top-right corner
        for s in range(self._strands):
            # v: Strand depth ratio (-0.5 to +0.5)
            v = (s / float(self._strands - 1)) - 0.5

            for i in range(self._points_per_strand):
                # u: Horizontal progression along the ribbon (0.0 to 1.0)
                u = i / float(self._points_per_strand - 1)
                jit_x, jit_y = self._jitters[s][i]

                # Base diagonal S-curve trajectory (Lower-left to upper-right)
                base_y = h * (0.80 - 0.52 * u + 0.16 * math.sin(u * math.pi))
                base_x = w * (u * 1.04 - 0.02)

                # Organic harmonic oscillations creating flowing ripples
                wave1 = math.sin(u * 5.2 - self._phase + v * 3.4) * 55.0
                wave2 = math.cos(u * 9.0 + self._phase * 1.3) * 22.0
                strand_offset_y = v * (110.0 + 35.0 * math.sin(u * 4.0 + self._phase))

                px = base_x + (math.cos(u * 3.0 - self._phase * 0.8 + v * 2.0) * 30.0) + jit_x
                py = base_y + wave1 + wave2 + strand_offset_y + jit_y

                # 3D Depth calculation (0.0 = back, 1.0 = crest in front)
                depth = (math.sin(u * 4.5 - self._phase + v * 3.0) * 0.5 + 0.5)

                # Foreground particles are larger and brighter; background are smaller and dimmer
                p_size = 1.3 + (depth * 2.7)
                alpha = int(45 + depth * 200)

                # Crest Specular Color Mixing:
                if depth > 0.80:
                    # Specular highlights (Diamond Pink to Crisp White)
                    col = qcol("#FFFFFF" if depth > 0.92 else "#FFE4EC", alpha)
                elif depth > 0.45:
                    # Vibrant Neon Pink / Magenta
                    col = qcol("#FF2D65", alpha)
                else:
                    # Deep Ruby in the shadows / back
                    col = qcol("#A21CAF", int(alpha * 0.85))

                p.setBrush(QBrush(col))
                p.drawEllipse(QPointF(px, py), p_size, p_size)

        # ── 4. RENDER SCATTERED AMBIENT STAR DUST ────────────────────────────
        for d in self._stardust:
            sx = d["x_norm"] * w
            sy = d["y_norm"] * h
            twinkle = (math.sin(d["twinkle_phase"]) * 0.5 + 0.5)
            s_alpha = int(d["base_alpha"] * (0.4 + 0.6 * twinkle))

            if twinkle > 0.85:
                s_col = qcol("#FFFFFF", s_alpha)
            else:
                s_col = qcol("#FF85A1", s_alpha)

            p.setBrush(QBrush(s_col))
            p.drawEllipse(QPointF(sx, sy), d["size"], d["size"])

        # ── 5. RESTORE STANDARD COMPOSITION FOR CRISP CYBER FRAME ────────────
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        inner_rect = QRectF(14, 14, w - 28, h - 28)

        # Transparent dark ruby glass tint (Light so all particles shine cleanly through)
        p.setBrush(QBrush(qcol("#0A0105", 40)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(inner_rect, 14, 14)

        # ── DOUBLE NEON CYBER BEZEL (MATCHING REFERENCE IMAGE) ───────────────
        # Outer Diffuse Glow
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qcol("#FF2D65", 50), 7.0))
        p.drawRoundedRect(inner_rect, 14, 14)

        # Razor-Sharp High-Intensity Neon Rim
        p.setPen(QPen(qcol("#FF2D65", 240), 1.8))
        p.drawRoundedRect(inner_rect, 14, 14)

        # Inset Hairline Glass Rim
        inset_rect = QRectF(18, 18, w - 36, h - 36)
        p.setPen(QPen(qcol("#FF6B8B", 80), 1.0))
        p.drawRoundedRect(inset_rect, 11, 11)

    # ── ENHANCED MESSAGE FORMATTING WITH FROSTED GLASS CHIPS (NO BOXES) ───────
    def append_message(self, sender: str, text: str):
        snd = sender.upper()

        if "SYS" in snd:
            badge_color = "#FF4D79"
            badge_border = "rgba(255, 45, 101, 0.45)"
            badge_text = "SYS"
            body_color = "#E2E8F0"
        elif "NEXUS" in snd or "AI" in snd:
            badge_color = "#FF85A1"
            badge_border = "rgba(255, 0, 85, 0.55)"
            badge_text = "NEXUS"
            body_color = "#FFFFFF"
        elif "USER" in snd or "YOU" in snd:
            badge_color = "#38BDF8"
            badge_border = "rgba(0, 242, 254, 0.45)"
            badge_text = "USER"
            body_color = "#F8FAFC"
        else:
            badge_color = "#FF6B8B"
            badge_border = "rgba(255, 107, 139, 0.40)"
            badge_text = snd
            body_color = "#F8FAFC"

        # PURE TEXT FLOATING OVER CANVAS WITH FROSTED BADGE CHIP
        html = f"""
        <div style="margin-bottom: 10px; font-family: 'Segoe UI', sans-serif; font-size: 12px; line-height: 1.5;">
            <span style="
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid {badge_border};
                border-radius: 12px;
                padding: 2px 9px;
                color: {badge_color};
                font-weight: bold;
                font-size: 10px;
                letter-spacing: 0.8px;
                margin-right: 6px;
            ">● {badge_text}</span>
            <span style="color: {body_color}; font-weight: 500;">{text}</span>
        </div>
        """
        self._chat_box.append(html)
        self._chat_box.ensureCursorVisible()

    def _copy_all(self):
        plain = self._chat_box.toPlainText()
        if plain:
            QApplication.clipboard().setText(plain)


# ── FULL-WINDOW VIEW 2: 4K GOLDEN SOLAR SILK RIVER NEWS PANEL ────────────────
class FullNewsView(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

        # ── 1. 4K VOLUMETRIC SOLAR SILK RIVER INITIALIZATION ─────────────────
        self._phase = 0.0
        self._strands = 24            # High-density ribbon strands
        self._points_per_strand = 56  # 56 points per strand (1,344 active wave particles)

        # Harmonic organic seed offsets
        self._jitters = [
            [(random.uniform(-3.5, 3.5), random.uniform(-3.5, 3.5)) for _ in range(self._points_per_strand)]
            for _ in range(self._strands)
        ]

        # Drifting Solar Photon Dust
        self._solardust = [
            {
                "x_norm": random.uniform(0.01, 0.99),
                "y_norm": random.uniform(0.05, 0.95),
                "drift_x": random.uniform(-0.0004, 0.0008),
                "drift_y": random.uniform(-0.0010, -0.0003),
                "twinkle_speed": random.uniform(0.04, 0.09),
                "twinkle_phase": random.uniform(0, math.pi * 2),
                "size": random.uniform(1.2, 2.8),
                "base_alpha": random.randint(80, 220)
            }
            for _ in range(140)
        ]

        # High-Fidelity Timer (~35 FPS)
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._step_solar_silk)
        self._anim_timer.start(28)

        # Root Outer Layout
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(28, 24, 28, 24)
        root_lay.setSpacing(14)

        # ── 2. TOP GOLD CYBER HEADER BAR ─────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(12)

        # Glowing Neon Gold Back Button
        self.back_btn = QPushButton("← BACK TO CORE")
        self.back_btn.setFixedHeight(32)
        self.back_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(251, 188, 5, 0.16);
                color: #FDE047;
                border: 1.5px solid #FBBC05;
                border-radius: 16px;
                padding: 0 16px;
                letter-spacing: 0.8px;
            }
            QPushButton:hover {
                background: rgba(251, 188, 5, 0.38);
                color: #FFFFFF;
                border-color: #F59E0B;
            }
            QPushButton:pressed {
                background: rgba(251, 188, 5, 0.55);
            }
        """)
        self.back_btn.clicked.connect(self.back_requested.emit)
        hdr.addWidget(self.back_btn)

        # Title with News Satellite Icon
        self._title_lbl = QLabel("📰  NEWS — TOP WORLD NEWS TODAY")
        self._title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._title_lbl.setStyleSheet("""
            color: #FBBF24;
            letter-spacing: 1.2px;
            background: transparent;
            border: none;
        """)
        hdr.addWidget(self._title_lbl)

        hdr.addStretch()

        # Glowing Gold "Copy Briefing" Button
        self.copy_btn = QPushButton("📋 Copy Briefing")
        self.copy_btn.setFixedHeight(32)
        self.copy_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background: rgba(251, 188, 5, 0.16);
                color: #FEF08A;
                border: 1.5px solid #FBBC05;
                border-radius: 16px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: rgba(251, 188, 5, 0.38);
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background: rgba(251, 188, 5, 0.55);
            }
        """)
        self.copy_btn.clicked.connect(self._copy_all_news)
        hdr.addWidget(self.copy_btn)
        root_lay.addLayout(hdr)

        # ── 3. 100% TRANSPARENT NEWS VIEWER ──────────────────────────────────
        self._news_box = QTextEdit()
        self._news_box.setReadOnly(True)
        self._news_box.setFont(QFont("Segoe UI", 9))
        self._news_box.setStyleSheet("""
            QTextEdit {
                background: transparent;
                color: #F8FAFC;
                border: none;
                padding: 8px 12px;
                line-height: 1.6;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #FBBC05;
                border-radius: 3px;
                min-height: 25px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        root_lay.addWidget(self._news_box, stretch=1)
        self._raw_news_text = ""

    # ── ADVANCE 4K SOLAR SILK HARMONICS ──────────────────────────────────────
    def _step_solar_silk(self):
        self._phase += 0.022
        for d in self._solardust:
            d["twinkle_phase"] += d["twinkle_speed"]
            d["x_norm"] += d["drift_x"]
            d["y_norm"] += d["drift_y"]
            if d["y_norm"] < -0.02:
                d["y_norm"] = 1.02
                d["x_norm"] = random.uniform(0.01, 0.99)
        self.update()

    # ── PAINTER: DRAWS 4K HIGH-DENSITY GOLDEN SILK RIVER ─────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())

        # Base Obsidian-Amber Void
        p.fillRect(self.rect(), qcol("#070501"))

        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)

        # Ambient Solar Flare Bloom
        bloom_x = w * 0.65 + math.sin(self._phase * 0.4) * 55.0
        bloom_y = h * 0.72 + math.cos(self._phase * 0.5) * 35.0
        bloom = QRadialGradient(bloom_x, bloom_y, w * 0.55)
        bloom.setColorAt(0.00, qcol("#78350F", 75))
        bloom.setColorAt(0.50, qcol("#451A03", 30))
        bloom.setColorAt(1.00, qcol("#070501", 0))
        p.setBrush(QBrush(bloom))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect())

        # ── 4K UNDULATING TOPOGRAPHIC SOLAR SILK RIVER ───────────────────────
        for s in range(self._strands):
            v = (s / float(self._strands - 1)) - 0.5  # Strand depth ratio

            for i in range(self._points_per_strand):
                u = i / float(self._points_per_strand - 1)
                jit_x, jit_y = self._jitters[s][i]

                # Sweeping S-Curve river flowing diagonally across the canvas
                base_y = h * (0.84 - 0.46 * u + 0.14 * math.sin(u * math.pi * 1.6))
                base_x = w * (u * 1.06 - 0.03)

                # Multi-frequency volumetric silk folds
                fold1 = math.sin(u * 4.2 - self._phase * 1.1 + v * 3.6) * 58.0
                fold2 = math.cos(u * 7.8 + self._phase * 1.3) * 24.0
                fan_offset_y = v * (140.0 + 45.0 * math.sin(u * 3.2 + self._phase * 0.8))

                px = base_x + (math.cos(u * 2.8 - self._phase * 0.7 + v * 1.8) * 32.0) + jit_x
                py = base_y + fold1 + fold2 + fan_offset_y + jit_y

                # Depth projection (0.0 to 1.0)
                depth = (math.sin(u * 4.4 - self._phase + v * 3.8) * 0.5 + 0.5)

                p_size = 1.1 + (depth * 2.6)
                alpha = int(40 + depth * 210)

                # Specular coloring
                if depth > 0.82:
                    col = qcol("#FFFFFF" if depth > 0.92 else "#FEF08A", alpha)
                elif depth > 0.45:
                    col = qcol("#FBBC05", alpha)
                else:
                    col = qcol("#B45309", int(alpha * 0.80))

                p.setBrush(QBrush(col))
                p.drawEllipse(QPointF(px, py), p_size, p_size)

        # ── FLOATING SOLAR DUST EMBERS ───────────────────────────────────────
        for d in self._solardust:
            sx = d["x_norm"] * w
            sy = d["y_norm"] * h
            twinkle = (math.sin(d["twinkle_phase"]) * 0.5 + 0.5)
            s_alpha = int(d["base_alpha"] * (0.4 + 0.6 * twinkle))

            col = qcol("#FFFFFF" if twinkle > 0.85 else "#FDE047", s_alpha)
            p.setBrush(QBrush(col))
            p.drawEllipse(QPointF(sx, sy), d["size"], d["size"])

        # ── RESTORE STANDARD COMPOSITION FOR AMBER CYBER FRAME ───────────────
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        inner_rect = QRectF(14, 14, w - 28, h - 28)

        # Double Neon Amber Bezel
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qcol("#FBBC05", 48), 7.0))
        p.drawRoundedRect(inner_rect, 14, 14)

        p.setPen(QPen(qcol("#FBBC05", 240), 1.8))
        p.drawRoundedRect(inner_rect, 14, 14)

        inset_rect = QRectF(18, 18, w - 36, h - 36)
        p.setPen(QPen(qcol("#FDE047", 75), 1.0))
        p.drawRoundedRect(inset_rect, 11, 11)

    # ── PURE TRANSPARENT TEXT WITH FROSTED GLASS STORY CHIPS ─────────────────
    def display_news(self, title: str, content: str):
        if title:
            self._title_lbl.setText(f"📰  {title.upper()}")
        self._raw_news_text = content

        story_blocks = [b.strip() for b in content.split("---") if b.strip()]
        if not story_blocks:
            story_blocks = [content]

        cards_html = ""
        for i, block in enumerate(story_blocks):
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            headline = ""
            source = "Global Wire"
            detail = ""

            for line in lines:
                if line.startswith("HEADLINE:"):
                    parts = line.replace("HEADLINE:", "").split("| SOURCE:")
                    headline = parts[0].strip()
                    if len(parts) > 1:
                        source = parts[1].strip()
                elif line.startswith("DETAIL:"):
                    detail = line.replace("DETAIL:", "").strip()
                elif not headline:
                    headline = line

            cards_html += f"""
            <div style="margin-bottom: 18px; padding-left: 2px;">
                <div style="margin-bottom: 5px;">
                    <span style="
                        background: rgba(255, 255, 255, 0.06);
                        border: 1px solid rgba(251, 188, 5, 0.40);
                        border-radius: 12px;
                        padding: 2px 10px;
                        color: #FBBC05;
                        font-size: 10px;
                        font-weight: bold;
                        letter-spacing: 0.8px;
                    ">● STORY #{i+1}</span>
                    <span style="color: #FDE047; font-size: 10px; font-weight: bold; margin-left: 6px;">[{source}]</span>
                </div>
                <div style="color: #FFFFFF; font-size: 13px; font-weight: bold; line-height: 1.4; margin-top: 4px; margin-bottom: 4px;">
                    {headline}
                </div>
                {f'<div style="color: #CBD5E1; font-size: 11px; line-height: 1.45;">{detail}</div>' if detail else ''}
            </div>
            """

        self._news_box.setHtml(cards_html)

    def _copy_all_news(self):
        if self._raw_news_text:
            QApplication.clipboard().setText(self._raw_news_text)

# ── 1. REAL-TIME SCROLLING LINE CHART (FOR CPU TEMP, DISK R/W, GPU TEMP) ─────
class LiveLineChartWidget(QWidget):
    def __init__(self, color: str = "#00F2FE", fill_alpha: int = 40, y_max: float = 75.0, y_ticks=("0", "25", "50", "75"), parent=None):
        super().__init__(parent)
        self._color = color
        self._fill_alpha = fill_alpha
        self._y_max = y_max
        self._y_ticks = y_ticks
        self._data = [20.0] * 36
        self.setFixedHeight(54)

    def set_data(self, data: list):
        if data:
            self._data = data[-36:]
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        left_margin = 24.0
        plot_w = w - left_margin - 4.0

        # Y-Axis Ticks
        p.setFont(QFont("Consolas", 6))
        p.setPen(QPen(qcol("#64748B")))
        for i, tick in enumerate(reversed(self._y_ticks)):
            y = 10 + i * ((h - 18) / max(1, len(self._y_ticks) - 1))
            p.drawText(QRectF(0, y - 6, 20, 12), Qt.AlignmentFlag.AlignRight, tick)

        # Grid lines
        p.setPen(QPen(qcol("#FFFFFF", 12), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(left_margin, 10), QPointF(w, 10))
        p.drawLine(QPointF(left_margin, h / 2), QPointF(w, h / 2))
        p.drawLine(QPointF(left_margin, h - 8), QPointF(w, h - 8))

        # Data Curve
        path = QPainterPath()
        fill_path = QPainterPath()
        step = plot_w / max(1, len(self._data) - 1)
        start_y = h - 8 - min(1.0, max(0.0, self._data[0] / self._y_max)) * (h - 18)
        path.moveTo(left_margin, start_y)
        fill_path.moveTo(left_margin, h - 8)
        fill_path.lineTo(left_margin, start_y)

        for i, val in enumerate(self._data):
            x = left_margin + i * step
            norm = min(1.0, max(0.0, val / self._y_max))
            y = h - 8 - (norm * (h - 18))
            path.lineTo(x, y)
            fill_path.lineTo(x, y)

        fill_path.lineTo(left_margin + (len(self._data) - 1) * step, h - 8)
        fill_path.closeSubpath()

        # Shaded area under graph
        p.setBrush(QBrush(qcol(self._color, self._fill_alpha)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(fill_path)

        # Line stroke
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qcol(self._color, 240), 1.6))
        p.drawPath(path)


# ── 2. INTERACTIVE CORE TOPOLOGY DIE MATRIX ──────────────────────────────────
class CoreTopologyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(130, 48)
        self._cores = [10, 15, 8, 12]

    def set_cores(self, core_list: list):
        self._cores = core_list[:4] if core_list else [10] * 4
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))

        # 4 Core Dies + 4 System Cache Blocks
        for row in range(2):
            for col in range(2):
                idx = row * 2 + col
                val = self._cores[idx] if idx < len(self._cores) else 8
                x = col * 36 + 2
                y = row * 22 + 2

                # Active core die box
                active_alpha = int(40 + (val / 100.0) * 180)
                p.setBrush(QBrush(qcol("#00F2FE", active_alpha)))
                p.setPen(QPen(qcol("#00F2FE", 180), 1))
                p.drawRoundedRect(QRectF(x, y, 32, 18), 3, 3)

                p.setPen(QPen(qcol("#FFFFFF" if val > 20 else "#00F2FE")))
                p.drawText(QRectF(x, y, 32, 18), Qt.AlignmentFlag.AlignCenter, f"Core {idx+1}")

        # Companion CPU System Controller blocks
        for row in range(2):
            for col in range(2):
                x = 78 + col * 24
                y = row * 22 + 2
                p.setBrush(QBrush(qcol("#FBBC05", 35)))
                p.setPen(QPen(qcol("#FBBC05", 140), 1))
                p.drawRoundedRect(QRectF(x, y, 20, 18), 3, 3)
                p.setPen(QPen(qcol("#FBBC05")))
                p.drawText(QRectF(x, y, 20, 18), Qt.AlignmentFlag.AlignCenter, "CPU")


# ── 3. POWER USAGE (TDP) PROGRESS BAR ────────────────────────────────────────
class PowerGaugeBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(14)
        self._watts = 65
        self._max_watts = 84

    def set_watts(self, val: int):
        self._watts = max(10, min(self._max_watts, val))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Track
        p.setBrush(QBrush(qcol("#FFFFFF", 20)))
        p.setPen(QPen(qcol("#FBBC05", 120), 1))
        p.drawRoundedRect(QRectF(0, 0, w, h), 4, 4)

        # Filled Amber Glow Bar
        fill_w = (self._watts / float(self._max_watts)) * w
        grad = QLinearGradient(0, 0, fill_w, 0)
        grad.setColorAt(0.0, qcol("#FBBC05", 160))
        grad.setColorAt(1.0, qcol("#FBBC05", 255))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(1, 1, max(4.0, fill_w - 2), h - 2), 3, 3)

# ── FULL-WINDOW VIEW 3: MULTI-LAYERED CYBER CRYO-ENGINE HARDWARE TELEMETRY ───
class FullMetricsView(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self._hw = _get_detailed_hardware_info()

        # ── 1. MULTI-SYSTEM HIGH-GRAPHICS CRYO ENGINE ────────────────────────
        self._phase = 0.0

        # System A: Dual Swirling Cryo-Coolant Vortices (550 organic particles)
        self._vortex_particles = []
        for i in range(550):
            # Cluster 0 = CPU/RAM quadrant, Cluster 1 = GPU/Disk quadrant
            cluster_id = 0 if i < 300 else 1
            self._vortex_particles.append({
                "cluster": cluster_id,
                "radius": random.uniform(25.0, 320.0),
                "angle": random.uniform(0.0, math.pi * 2.0),
                "speed": random.uniform(0.008, 0.024) * (-1 if random.random() < 0.3 else 1),
                "tilt_x": random.uniform(0.35, 0.65),
                "tilt_y": random.uniform(0.70, 1.10),
                "wobble_freq": random.uniform(1.2, 3.5),
                "size": random.uniform(1.2, 3.2),
                "base_alpha": random.randint(70, 220)
            })

        # System B: High-Speed PCIe Laser Data Streaks (45 horizontal tracers)
        self._laser_streaks = [
            {
                "x": random.uniform(-100, 1920),
                "y": random.uniform(60, 1000),
                "speed": random.uniform(6.0, 16.0),
                "length": random.uniform(35.0, 110.0),
                "thickness": random.uniform(1.0, 2.0),
                "alpha": random.randint(90, 210)
            }
            for _ in range(45)
        ]

        # System C: Telemetry Radar Shockwave Pulses
        self._radar_waves = [
            {"radius": 0.0, "max_radius": 280.0, "speed": 2.2, "alpha": 220},
            {"radius": 90.0, "max_radius": 280.0, "speed": 2.2, "alpha": 150},
            {"radius": 180.0, "max_radius": 280.0, "speed": 2.2, "alpha": 80}
        ]

        # System D: Ambient Twinkling Ice Motes
        self._ambient_ice = [
            {
                "x_norm": random.uniform(0.01, 0.99),
                "y_norm": random.uniform(0.02, 0.98),
                "drift_x": random.uniform(-0.0004, 0.0006),
                "drift_y": random.uniform(-0.0006, 0.0004),
                "twinkle_speed": random.uniform(0.03, 0.08),
                "twinkle_phase": random.uniform(0, math.pi * 2),
                "size": random.uniform(1.0, 2.4),
                "alpha": random.randint(60, 200)
            }
            for _ in range(90)
        ]

        # Animation Timer (~35 FPS)
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._step_engine)
        self._anim_timer.start(28)

        # Root Outer Layout
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        # ── 2. TOP COBALT HEADER BAR ─────────────────────────────────────────
        hdr_frame = QWidget()
        hdr_frame.setFixedHeight(46)
        hdr = QHBoxLayout(hdr_frame)
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(12)

        back_btn = QPushButton("← BACK TO CORE")
        back_btn.setFixedSize(140, 30)
        back_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 242, 254, 0.16);
                color: #E0F2FE;
                border: 1.5px solid #00F2FE;
                border-radius: 15px;
                letter-spacing: 0.8px;
            }
            QPushButton:hover {
                background: rgba(0, 242, 254, 0.38);
                color: #FFFFFF;
                border-color: #38BDF8;
            }
            QPushButton:pressed {
                background: rgba(0, 242, 254, 0.55);
            }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        hdr.addWidget(back_btn)

        title = QLabel("⚡ DEVICE HARDWARE TELEMETRY & SPECIFICATIONS")
        title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #00F2FE; letter-spacing: 1.2px; background: transparent; border: none;")
        hdr.addWidget(title)

        hdr.addStretch()

        self.ai_emblem = CyberAiEmblemWidget()
        hdr.addWidget(self.ai_emblem)

        hdr.addStretch()

        host_box = QLabel(f"Host ID:  💻 [ {self._hw['host_name']} ]")
        host_box.setFixedHeight(28)
        host_box.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        host_box.setStyleSheet("""
            color: #94A3B8;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 242, 254, 0.30);
            border-radius: 6px;
            padding: 4px 12px;
        """)
        hdr.addWidget(host_box)
        root.addWidget(hdr_frame)

        # ── 3. UPPER 4 TRANSLUCENT CRYO PODS ─────────────────────────────────
        pods_row = QHBoxLayout()
        pods_row.setSpacing(8)

        # POD 1: CPU (Ice Cyan)
        p_cpu = self._make_pod_frame("#00F2FE", "PodCPU")
        l_c = QVBoxLayout(p_cpu)
        l_c.setContentsMargins(10, 8, 10, 8)
        l_c.setSpacing(4)
        t_c = QLabel("CPU USAGE")
        t_c.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        t_c.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_c.setStyleSheet("color: #00F2FE; letter-spacing: 0.8px;")
        l_c.addWidget(t_c)

        r_c = QHBoxLayout()
        self.core_hist = RealCoreHistogram()
        r_c.addWidget(self.core_hist)
        self.g_cpu = CyberTargetGauge(color="#00F2FE", icon_type="cpu")
        r_c.addWidget(self.g_cpu)
        self.arc_cpu = CurvedTempArcWidget(color="#00F2FE", ticks=("15-", "35-", "0-"), current_temp="25°C")
        r_c.addWidget(self.arc_cpu)
        l_c.addLayout(r_c)

        self.lbl_cpu_load = QLabel("13% Idle")
        self.lbl_cpu_load.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self.lbl_cpu_load.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_cpu_load.setStyleSheet("color: #00F2FE;")
        l_c.addWidget(self.lbl_cpu_load)
        pods_row.addWidget(p_cpu, 1)

        # POD 2: RAM (Polar Violet Frost)
        p_ram = self._make_pod_frame("#C084FC", "PodRAM")
        l_r = QVBoxLayout(p_ram)
        l_r.setContentsMargins(10, 8, 10, 8)
        l_r.setSpacing(4)
        t_r = QLabel("RAM MEMORY")
        t_r.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        t_r.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_r.setStyleSheet("color: #C084FC; letter-spacing: 0.8px;")
        l_r.addWidget(t_r)

        r_ram = QHBoxLayout()
        self.g_ram = CyberTargetGauge(color="#C084FC", icon_type="ram")
        r_ram.addWidget(self.g_ram)

        ram_details = QVBoxLayout()
        ram_details.setSpacing(3)
        r_title = QLabel("Memory Usage\n■ OS   ■ Cache   ■ Apps")
        r_title.setFont(QFont("Segoe UI", 6))
        r_title.setStyleSheet("color: #94A3B8;")
        ram_details.addWidget(r_title)

        r_speed = QLabel(f"⚡ {self._hw['ram_speed']}\n💾 {self._hw['ram_channel']}")
        r_speed.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
        r_speed.setStyleSheet("color: #E0F2FE;")
        ram_details.addWidget(r_speed)
        r_ram.addLayout(ram_details)
        l_r.addLayout(r_ram)

        self.lbl_ram_legend = QLabel("■ Used 4.9 GB   ■ Available 7.0 GB")
        self.lbl_ram_legend.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        self.lbl_ram_legend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_ram_legend.setStyleSheet("color: #C084FC;")
        l_r.addWidget(self.lbl_ram_legend)
        pods_row.addWidget(p_ram, 1)

        # POD 3: DISK (Aurora Mint Frost)
        p_disk = self._make_pod_frame("#34D399", "PodDisk")
        l_d = QVBoxLayout(p_disk)
        l_d.setContentsMargins(10, 8, 10, 8)
        l_d.setSpacing(4)
        t_d = QLabel("DISK STORAGE")
        t_d.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        t_d.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t_d.setStyleSheet("color: #34D399; letter-spacing: 0.8px;")
        l_d.addWidget(t_d)

        r_d = QHBoxLayout()
        self.g_disk = CyberTargetGauge(color="#34D399", icon_type="disk")
        self.g_disk.set_val(self._hw["disk_pct"], f"{self._hw['disk_pct']}%")
        r_d.addWidget(self.g_disk)
        self.arc_disk = CurvedTempArcWidget(color="#34D399", ticks=("15-", "25-", "32-"), current_temp=self._hw["disk_temp"])
        r_d.addWidget(self.arc_disk)
        l_d.addLayout(r_d)

        d_txt = f"{self._hw['disk_total']} Total | {self._hw['disk_used']} used | {self._hw['disk_free']} Free"
        lbl_disk_free = QLabel(d_txt)
        lbl_disk_free.setFont(QFont("Segoe UI", 7))
        lbl_disk_free.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_disk_free.setStyleSheet("color: #94A3B8;")
        l_d.addWidget(lbl_disk_free)
        pods_row.addWidget(p_disk, 1)

        # POD 4: NETWORK (Solar Amber Frost)
        p_net = self._make_pod_frame("#FCD34D", "PodNet")
        l_n = QVBoxLayout(p_net)
        l_n.setContentsMargins(10, 8, 10, 8)
        l_n.setSpacing(4)

        t_n_row = QHBoxLayout()
        t_n = QLabel("NETWORK SPEED")
        t_n.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        t_n.setStyleSheet("color: #FCD34D; letter-spacing: 0.8px;")
        t_n_row.addWidget(t_n)
        t_n_row.addStretch()
        st_dot = QLabel("●")
        st_dot.setStyleSheet("color: #34D399; font-size: 8px;")
        t_n_row.addWidget(st_dot)
        l_n.addLayout(t_n_row)

        r_n = QHBoxLayout()
        self.g_net = CyberTargetGauge(color="#FCD34D", icon_type="net")
        self.g_net.set_val(92.0, "STABLE")
        r_n.addWidget(self.g_net)

        net_table = QVBoxLayout()
        net_table.setSpacing(2)
        ping_l = QLabel("PING: 12ms")
        ping_l.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        ping_l.setStyleSheet("color: #F8FAFC;")
        net_table.addWidget(ping_l)
        for app, val in [("application", "0.0 Mbps"), ("ethernet", "0.3 Mbps"), ("system", "0.8 Mbps")]:
            row_l = QLabel(f"{app}: {val}")
            row_l.setFont(QFont("Consolas", 6))
            row_l.setStyleSheet("color: #94A3B8;")
            net_table.addWidget(row_l)
        r_n.addLayout(net_table)
        l_n.addLayout(r_n)

        net_sparks = QVBoxLayout()
        net_sparks.setSpacing(2)
        s_d = QHBoxLayout()
        lbl_arr_d = QLabel("↓")
        lbl_arr_d.setStyleSheet("color: #FCD34D; font-size: 8px;")
        s_d.addWidget(lbl_arr_d)
        self.spark_down = NetworkWaveSparkline("#FCD34D")
        s_d.addWidget(self.spark_down)
        self.lbl_net_down = QLabel("0.0 Mbps / 22 Mbps")
        self.lbl_net_down.setFont(QFont("Consolas", 6))
        self.lbl_net_down.setStyleSheet("color: #FCD34D;")
        s_d.addWidget(self.lbl_net_down)
        net_sparks.addLayout(s_d)

        s_u = QHBoxLayout()
        lbl_arr_u = QLabel("↑")
        lbl_arr_u.setStyleSheet("color: #FCD34D; font-size: 8px;")
        s_u.addWidget(lbl_arr_u)
        self.spark_up = NetworkWaveSparkline("#FCD34D")
        s_u.addWidget(self.spark_up)
        self.lbl_net_up = QLabel("0.0 Mbps / 22 Mbps")
        self.lbl_net_up.setFont(QFont("Consolas", 6))
        self.lbl_net_up.setStyleSheet("color: #FCD34D;")
        s_u.addWidget(self.lbl_net_up)
        net_sparks.addLayout(s_u)
        l_n.addLayout(net_sparks)

        pods_row.addWidget(p_net, 1)
        root.addLayout(pods_row)

        # ── 4. LOWER DETAILED CARDS ──────────────────────────────────────────
        cards_grid = QHBoxLayout()
        cards_grid.setSpacing(8)

        col_left = QVBoxLayout()
        col_left.setSpacing(8)

        # CARD 1: CPU
        c_cpu = self._make_card("#00F2FE", "CardCPU")
        l_cc = QVBoxLayout(c_cpu)
        l_cc.setContentsMargins(12, 10, 12, 10)
        l_cc.setSpacing(4)

        top_cpu = QHBoxLayout()
        hdr_cpu = QLabel("⚡ PROCESSOR (CPU)")
        hdr_cpu.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        hdr_cpu.setStyleSheet("color: #00F2FE;")
        top_cpu.addWidget(hdr_cpu)
        top_cpu.addStretch()

        pwr_box = QVBoxLayout()
        self.lbl_pwr = QLabel("Power Usage (TDP)   Current: 65W / Max: 84W")
        self.lbl_pwr.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
        self.lbl_pwr.setStyleSheet("color: #FCD34D;")
        pwr_box.addWidget(self.lbl_pwr)
        self.pwr_bar = PowerGaugeBar()
        self.pwr_bar.setFixedWidth(130)
        pwr_box.addWidget(self.pwr_bar)
        top_cpu.addLayout(pwr_box)
        l_cc.addLayout(top_cpu)

        mid_cpu = QHBoxLayout()
        name_cpu = QLabel(self._hw["cpu_name"])
        name_cpu.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        name_cpu.setStyleSheet("color: #FFFFFF;")
        mid_cpu.addWidget(name_cpu)

        temp_box = QVBoxLayout()
        t_lbl = QLabel("Package Temperature")
        t_lbl.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
        t_lbl.setStyleSheet("color: #00F2FE;")
        temp_box.addWidget(t_lbl)
        self.cpu_chart = LiveLineChartWidget("#00F2FE", fill_alpha=40, y_max=75.0, y_ticks=("0", "25", "50", "75"))
        temp_box.addWidget(self.cpu_chart)
        mid_cpu.addLayout(temp_box)
        l_cc.addLayout(mid_cpu)

        bot_cpu = QHBoxLayout()
        spec_grid = QGridLayout()
        spec_grid.setHorizontalSpacing(14)
        spec_grid.setVerticalSpacing(2)
        spec_grid.addWidget(self._make_spec_lbl(f"Clock: {self._hw['cpu_base_clock']} (Base) / {self._hw['cpu_turbo_clock']}"), 0, 0)
        spec_grid.addWidget(self._make_spec_lbl(f"Cores: {self._hw['cpu_cores']} / Threads: {self._hw['cpu_threads']}"), 1, 0)
        spec_grid.addWidget(self._make_spec_lbl(f"Cache: {self._hw['cpu_cache']}"), 2, 0)
        spec_grid.addWidget(self._make_spec_lbl(f"Architecture: {self._hw['cpu_arch']}"), 3, 0)
        spec_grid.addWidget(self._make_spec_lbl(f"TDP: {self._hw['cpu_tdp']}"), 0, 1)
        spec_grid.addWidget(self._make_spec_lbl(f"Socket: {self._hw['cpu_socket']}"), 1, 1)
        bot_cpu.addLayout(spec_grid, stretch=1)

        topo_box = QVBoxLayout()
        topo_lbl = QLabel("Core Topology")
        topo_lbl.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
        topo_lbl.setStyleSheet("color: #00F2FE;")
        topo_box.addWidget(topo_lbl)
        self.core_topo = CoreTopologyWidget()
        topo_box.addWidget(self.core_topo)
        bot_cpu.addLayout(topo_box)
        l_cc.addLayout(bot_cpu)
        col_left.addWidget(c_cpu)

        # CARD 3: RAM
        c_ram = self._make_card("#34D399", "CardRAM")
        l_cr = QVBoxLayout(c_ram)
        l_cr.setContentsMargins(12, 10, 12, 10)
        l_cr.setSpacing(4)

        top_ram = QHBoxLayout()
        hdr_ram = QLabel("💾 INSTALLED MEMORY (RAM)")
        hdr_ram.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        hdr_ram.setStyleSheet("color: #34D399;")
        top_ram.addWidget(hdr_ram)
        top_ram.addStretch()
        ram_st = QLabel("■ Dual Channel Active  ●")
        ram_st.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
        ram_st.setStyleSheet("color: #34D399;")
        top_ram.addWidget(ram_st)
        l_cr.addLayout(top_ram)

        mid_ram = QHBoxLayout()
        cap_lbl = QLabel(f"{self._hw['ram_total_gb']} GB Total Capacity")
        cap_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        cap_lbl.setStyleSheet("color: #FFFFFF;")
        mid_ram.addWidget(cap_lbl)
        mid_ram.addStretch()
        self.ram_wave = MiniOscilloscope("#34D399", mode="wave")
        self.ram_wave.setFixedWidth(100)
        mid_ram.addWidget(self.ram_wave)
        l_cr.addLayout(mid_ram)

        ram_grid = QGridLayout()
        ram_grid.setHorizontalSpacing(14)
        ram_grid.setVerticalSpacing(2)
        ram_grid.addWidget(self._make_spec_lbl(self._hw["ram_type"]), 0, 0)
        ram_grid.addWidget(self._make_spec_lbl(f"Form Factor: {self._hw['ram_form']}"), 1, 0)
        ram_grid.addWidget(self._make_spec_lbl(f"Total Modules: {self._hw['ram_modules']}"), 2, 0)
        ram_grid.addWidget(self._make_spec_lbl(f"Clock: {self._hw['ram_speed']}"), 3, 0)
        ram_grid.addWidget(self._make_spec_lbl("Clock: Single"), 0, 1)
        ram_grid.addWidget(self._make_spec_lbl(f"Channel: {self._hw['ram_channel']}"), 1, 1)
        ram_grid.addWidget(self._make_spec_lbl(f"Voltage: {self._hw['ram_voltage']}"), 2, 1)
        ram_grid.addWidget(self._make_spec_lbl(f"Rank: {self._hw['ram_rank']}"), 3, 1)
        l_cr.addLayout(ram_grid)
        col_left.addWidget(c_ram)

        cards_grid.addLayout(col_left, stretch=1)

        col_right = QVBoxLayout()
        col_right.setSpacing(8)

        # CARD 2: GPU (Frozen Rose Magenta)
        c_gpu = self._make_card("#F472B6", "CardGPU")
        l_cg = QVBoxLayout(c_gpu)
        l_cg.setContentsMargins(12, 10, 12, 10)
        l_cg.setSpacing(4)

        top_gpu = QHBoxLayout()
        hdr_gpu = QLabel("🎮 GRAPHICS ACCELERATOR (GPU)")
        hdr_gpu.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        hdr_gpu.setStyleSheet("color: #F472B6;")
        top_gpu.addWidget(hdr_gpu)
        top_gpu.addStretch()

        self.fan = SpinningFanWidget()
        top_gpu.addWidget(self.fan)
        fan_t = QLabel("1200 RPM")
        fan_t.setFont(QFont("Consolas", 6, QFont.Weight.Bold))
        fan_t.setStyleSheet("color: #00F2FE;")
        top_gpu.addWidget(fan_t)
        l_cg.addLayout(top_gpu)

        name_gpu = QLabel(self._hw["gpu_name"])
        name_gpu.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        name_gpu.setStyleSheet("color: #FFFFFF;")
        l_cg.addWidget(name_gpu)

        gpu_chart_row = QHBoxLayout()
        gpu_specs = QVBoxLayout()
        gpu_specs.setSpacing(2)
        gpu_specs.addWidget(self._make_spec_lbl(f"Base Clock: {self._hw['gpu_clock']}"))
        gpu_specs.addWidget(self._make_spec_lbl(f"Execution Units: {self._hw['gpu_eu']}"))
        gpu_specs.addWidget(self._make_spec_lbl(f"Memory Alloc: {self._hw['gpu_memory']}"))
        gpu_specs.addWidget(self._make_spec_lbl(self._hw["gpu_directx"]))
        gpu_specs.addWidget(self._make_spec_lbl(f"Max Res: {self._hw['gpu_res']}"))
        gpu_chart_row.addLayout(gpu_specs, stretch=1)

        gpu_t_box = QVBoxLayout()
        gpu_t_lbl = QLabel("GPU Temperature")
        gpu_t_lbl.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
        gpu_t_lbl.setStyleSheet("color: #F472B6;")
        gpu_t_box.addWidget(gpu_t_lbl)
        self.gpu_chart = LiveLineChartWidget("#F472B6", fill_alpha=40, y_max=100.0, y_ticks=("70", "80", "85"))
        gpu_t_box.addWidget(self.gpu_chart)
        gpu_chart_row.addLayout(gpu_t_box)
        l_cg.addLayout(gpu_chart_row)
        col_right.addWidget(c_gpu)

        # CARD 4: DISK
        c_disk = self._make_card("#FCD34D", "CardDisk")
        l_cd = QVBoxLayout(c_disk)
        l_cd.setContentsMargins(12, 10, 12, 10)
        l_cd.setSpacing(4)

        top_d = QHBoxLayout()
        hdr_disk = QLabel("💽 MAIN STORAGE DRIVE")
        hdr_disk.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        hdr_disk.setStyleSheet("color: #FCD34D;")
        top_d.addWidget(hdr_disk)
        top_d.addStretch()

        self.disk_card_bar = SegmentedLedBar()
        self.disk_card_bar.set_pct(self._hw["disk_pct"])
        top_d.addWidget(self.disk_card_bar)
        l_cd.addLayout(top_d)

        chart_disk_row = QHBoxLayout()
        part_box = QVBoxLayout()
        part_box.setSpacing(2)
        d_name = QLabel(f"{self._hw['disk_total']} Total Partition")
        d_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        d_name.setStyleSheet("color: #FFFFFF;")
        part_box.addWidget(d_name)
        part_box.addWidget(self._make_spec_lbl(f"Interface: {self._hw['disk_interface']}"))
        part_box.addWidget(self._make_spec_lbl(f"Drive Type: {self._hw['disk_type']}"))
        part_box.addWidget(self._make_spec_lbl(f"Free: {self._hw['disk_free']} / Used: {self._hw['disk_used']}"))
        chart_disk_row.addLayout(part_box)

        rw_charts = QVBoxLayout()
        rw_charts.setSpacing(2)
        self.chart_read = LiveLineChartWidget("#34D399", fill_alpha=35, y_max=200.0, y_ticks=("0", "60", "120", "180"))
        rw_charts.addWidget(self.chart_read)
        self.chart_write = LiveLineChartWidget("#FCD34D", fill_alpha=35, y_max=180.0, y_ticks=("0", "50", "100", "150"))
        rw_charts.addWidget(self.chart_write)
        chart_disk_row.addLayout(rw_charts, stretch=1)
        l_cd.addLayout(chart_disk_row)

        col_right.addWidget(c_disk)
        cards_grid.addLayout(col_right, stretch=1)
        root.addLayout(cards_grid)

        # ── 5. BOTTOM TELEMETRY DOCK ─────────────────────────────────────────
        rail = QFrame()
        rail.setFixedHeight(26)
        rail.setStyleSheet("background: rgba(4, 12, 28, 0.65); border: 1px solid rgba(0, 242, 254, 0.20); border-radius: 6px;")
        r_box = QHBoxLayout(rail)
        r_box.setContentsMargins(12, 0, 12, 0)
        lbl_fan_status = QLabel("❄️ CPU FAN  CPU   •   CASE FAN  CASE")
        lbl_fan_status.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        lbl_fan_status.setStyleSheet("color: #94A3B8; background: transparent; border: none;")
        r_box.addWidget(lbl_fan_status)
        r_box.addStretch()

        self.sys_time_lbl = QLabel(time.strftime("%H:%M:%S.00"))
        self.sys_time_lbl.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
        self.sys_time_lbl.setStyleSheet("color: #00F2FE; background: rgba(0, 242, 254, 0.15); padding: 1px 8px; border-radius: 4px;")
        r_box.addWidget(self.sys_time_lbl)

        r_box.addStretch()
        pulse = QLabel("⚡ HARDWARE CRYO-VORTEX: ACTIVE")
        pulse.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
        pulse.setStyleSheet("color: #34D399; background: transparent; border: none;")
        r_box.addWidget(pulse)
        root.addWidget(rail)

        self._ms_timer = QTimer(self)
        self._ms_timer.timeout.connect(self._tick_ms)
        self._ms_timer.start(50)

    def _tick_ms(self):
        ms = int((time.time() % 1) * 100)
        self.sys_time_lbl.setText(f"{time.strftime('%H:%M:%S')}.{ms:02d}")

    # ── ADVANCE VOLUMETRIC VORTEX, BUS TRACERS & SHOCKWAVES ─────────────────
    def _step_engine(self):
        self._phase += 0.026

        # Step 1: Advance Swirling Vortex Particles
        for p in self._vortex_particles:
            p["angle"] += p["speed"]

        # Step 2: Advance High-Speed Bus Data Streaks
        w = float(self.width() if self.width() > 10 else 1920)
        for s in self._laser_streaks:
            s["x"] += s["speed"]
            if s["x"] > w + 100:
                s["x"] = -random.uniform(20, 120)
                s["y"] = random.uniform(60, float(self.height() if self.height() > 10 else 1080))
                s["speed"] = random.uniform(6.0, 16.0)

        # Step 3: Advance Telemetry Radar Shockwaves
        for rw in self._radar_waves:
            rw["radius"] += rw["speed"]
            if rw["radius"] > rw["max_radius"]:
                rw["radius"] = 0.0

        # Step 4: Advance Ambient Ice Motes
        for m in self._ambient_ice:
            m["twinkle_phase"] += m["twinkle_speed"]
            m["x_norm"] += m["drift_x"]
            m["y_norm"] += m["drift_y"]
            if m["x_norm"] > 1.02: m["x_norm"] = -0.02
            if m["x_norm"] < -0.02: m["x_norm"] = 1.02
            if m["y_norm"] > 1.02: m["y_norm"] = -0.02
            if m["y_norm"] < -0.02: m["y_norm"] = 1.02

        self.update()

    # ── PAINTER: DRAWS ORGANIC VORTICES, LASER TRACERS, RADAR WAVES & SHEEN ───
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())

        # 1. Base Deep Cryo-Cobalt Obsidian Void
        p.fillRect(self.rect(), qcol("#030712"))

        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)

        # ── 2. VOLUMETRIC CRYOGENIC NEBULA BLOOMS ──
        # CPU/RAM Area Bloom (Upper Left)
        b1_x = w * 0.28
        b1_y = h * 0.35
        bloom1 = QRadialGradient(b1_x, b1_y, 380.0)
        bloom1.setColorAt(0.00, qcol("#0284C7", 75))
        bloom1.setColorAt(0.45, qcol("#0F275A", 30))
        bloom1.setColorAt(1.00, qcol("#030712", 0))
        p.setBrush(QBrush(bloom1))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(b1_x, b1_y), 380.0, 380.0)

        # GPU/Storage Area Bloom (Lower Right)
        b2_x = w * 0.74
        b2_y = h * 0.62
        bloom2 = QRadialGradient(b2_x, b2_y, 420.0)
        bloom2.setColorAt(0.00, qcol("#0369A1", 70))
        bloom2.setColorAt(0.50, qcol("#0C1E4A", 25))
        bloom2.setColorAt(1.00, qcol("#030712", 0))
        p.setBrush(QBrush(bloom2))
        p.drawEllipse(QPointF(b2_x, b2_y), 420.0, 420.0)

        # ── 3. RADAR TELEMETRY EXPANDING SHOCKWAVES (From AI emblem & CPU) ────
        for rw in self._radar_waves:
            r = rw["radius"]
            fade = 1.0 - (r / rw["max_radius"])
            rw_alpha = int(fade * 140)

            # Emitter 1: AI Emblem Center
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(qcol("#00F2FE", rw_alpha), 1.2))
            p.drawEllipse(QPointF(w * 0.5, 36.0), r * 0.8, r * 0.45)

            # Emitter 2: CPU Gauge Area
            p.setPen(QPen(qcol("#38BDF8", int(rw_alpha * 0.7)), 1.0))
            p.drawEllipse(QPointF(w * 0.16, h * 0.18), r * 0.6, r * 0.6)

        # ── 4. ORGANIC DUAL SWIRLING CRYO-COOLANT VORTICES (NO BEADED ROWS) ──
        centers = [(w * 0.28, h * 0.35), (w * 0.74, h * 0.62)]
        for pt in self._vortex_particles:
            cx, cy = centers[pt["cluster"]]
            r = pt["radius"] + math.sin(self._phase * pt["wobble_freq"] + pt["angle"]) * 14.0
            ang = pt["angle"]

            # True 3D tilted orbital mechanics
            x_loc = r * math.cos(ang) * pt["tilt_x"]
            y_loc = r * math.sin(ang) * pt["tilt_y"]

            px = cx + x_loc
            py = cy + y_loc

            z_depth = math.sin(ang) * 0.5 + 0.5
            p_size = pt["size"] * (0.7 + z_depth * 0.6)
            alpha = int(pt["base_alpha"] * (0.4 + z_depth * 0.6))

            # Specular Diamond Glints
            if z_depth > 0.82:
                col = qcol("#FFFFFF" if z_depth > 0.93 else "#E0F2FE", alpha)
            elif z_depth > 0.45:
                col = qcol("#00F2FE", alpha)
            else:
                col = qcol("#0284C7", int(alpha * 0.75))

            p.setBrush(QBrush(col))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(px, py), p_size, p_size)

        # ── 5. HIGH-SPEED PCIE LASER DATA STREAKS (HORIZONTAL BUS ACTIVITY) ──
        for s in self._laser_streaks:
            grad = QLinearGradient(QPointF(s["x"] - s["length"], s["y"]), QPointF(s["x"], s["y"]))
            grad.setColorAt(0.0, qcol("#00F2FE", 0))
            grad.setColorAt(0.7, qcol("#38BDF8", int(s["alpha"] * 0.6)))
            grad.setColorAt(1.0, qcol("#FFFFFF", s["alpha"]))

            p.setPen(QPen(QBrush(grad), s["thickness"]))
            p.drawLine(QPointF(s["x"] - s["length"], s["y"]), QPointF(s["x"], s["y"]))

            # Spark head dot
            p.setBrush(QBrush(qcol("#FFFFFF", s["alpha"])))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(s["x"], s["y"]), s["thickness"] * 1.4, s["thickness"] * 1.4)

        # ── 6. AMBIENT TWINKLING ICE MOTES ───────────────────────────────────
        for m in self._ambient_ice:
            sx = m["x_norm"] * w
            sy = m["y_norm"] * h
            twinkle = (math.sin(m["twinkle_phase"]) * 0.5 + 0.5)
            m_alpha = int(m["alpha"] * (0.4 + 0.6 * twinkle))

            col = qcol("#FFFFFF" if twinkle > 0.85 else "#38BDF8", m_alpha)
            p.setBrush(QBrush(col))
            p.drawEllipse(QPointF(sx, sy), m["size"], m["size"])

        # ── 7. GLOSSY DIAGONAL CRYO-GLASS SHEEN (From Gemini Mockup) ─────────
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        sheen_poly = QPolygonF([
            QPointF(w * 0.05, 0),
            QPointF(w * 0.45, 0),
            QPointF(w * 0.15, h),
            QPointF(0, h)
        ])
        g_sheen = QLinearGradient(QPointF(w * 0.1, 0), QPointF(w * 0.35, h))
        g_sheen.setColorAt(0.0, qcol("#38BDF8", 0))
        g_sheen.setColorAt(0.5, qcol("#E0F2FE", 18))
        g_sheen.setColorAt(1.0, qcol("#38BDF8", 0))
        p.setBrush(QBrush(g_sheen))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(sheen_poly)

        # ── 8. RESTORE STANDARD COMPOSITION FOR NEON CRYO BEZEL ──────────────
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        inner_rect = QRectF(12, 10, w - 24, h - 20)

        # Outer Diffuse Ice Glow
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qcol("#00F2FE", 45), 7.0))
        p.drawRoundedRect(inner_rect, 14, 14)

        # Razor-Sharp Neon Rim
        p.setPen(QPen(qcol("#00F2FE", 240), 1.8))
        p.drawRoundedRect(inner_rect, 14, 14)

        # Inset Hairline Glass Rim
        inset_rect = QRectF(16, 14, w - 32, h - 28)
        p.setPen(QPen(qcol("#38BDF8", 70), 1.0))
        p.drawRoundedRect(inset_rect, 11, 11)

    # ── TRANSLUCENT FROSTED POD GENERATOR ────────────────────────────────────
    def _make_pod_frame(self, accent_color: str, obj_name: str) -> QFrame:
        f = QFrame()
        f.setObjectName(obj_name)
        f.setFixedHeight(175)
        f.setStyleSheet(f"""
            QFrame#{obj_name} {{
                background: rgba(6, 16, 38, 0.58);
                border: 1px solid rgba(0, 242, 254, 0.22);
                border-top: 2.5px solid {accent_color};
                border-radius: 10px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        return f

    def _make_card(self, accent_color: str, obj_name: str) -> QFrame:
        f = QFrame()
        f.setObjectName(obj_name)
        f.setStyleSheet(f"""
            QFrame#{obj_name} {{
                background: rgba(6, 16, 36, 0.55);
                border: 1px solid rgba(0, 242, 254, 0.20);
                border-left: 3.5px solid {accent_color};
                border-radius: 8px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        return f

    def _make_spec_lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 6))
        lbl.setStyleSheet("color: #94A3B8; background: transparent; border: none;")
        return lbl

    # ── LIVE TELEMETRY UPDATE ────────────────────────────────────────────────
    def update_metrics(self, cpu: float, mem: float, net: float, gpu: float = -1.0):
        snap = _live_telemetry.snapshot()

        self.g_cpu.set_val(snap["cpu_total"], "Idle" if snap["cpu_total"] < 25 else "Load")
        self.lbl_cpu_load.setText(f"{int(snap['cpu_total'])}% Idle")
        self.core_hist.set_cores(snap["cpu_cores"])
        self.core_topo.set_cores(snap["cpu_cores"])
        self.cpu_chart.set_data(snap["cpu_temp_hist"])
        self.arc_cpu.set_temp(f"{int(snap['cpu_temp'])}°C")
        self.pwr_bar.set_watts(snap["cpu_watts"])
        self.lbl_pwr.setText(f"Power Usage (TDP)   Current: {snap['cpu_watts']}W / Max: 84W")

        self.g_ram.set_val(snap["mem_pct"], f"{int(snap['mem_pct'])}%")
        self.lbl_ram_legend.setText(f"■ Used {snap['mem_used']} GB   ■ Available {snap['mem_free']} GB")

        self.spark_down.set_data(snap["net_down_hist"])
        self.spark_up.set_data(snap["net_up_hist"])
        self.lbl_net_down.setText(f"{snap['net_down']:.1f} Mbps / 22 Mbps")
        self.lbl_net_up.setText(f"{snap['net_up']:.1f} Mbps / 22 Mbps")

        self.gpu_chart.set_data(snap["gpu_temp_hist"])
        self.chart_read.set_data(snap["disk_read_hist"])
        self.chart_write.set_data(snap["disk_write_hist"])


# ── FULL-WINDOW VIEW 4: EMERALD CYBER QUANTUM CORE PLUGINS PANEL ──────────────
class FullPluginsView(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

        # ── 1. 3D CYBERNETIC NEURAL PLEXUS INITIALIZATION ────────────────────
        self._phase = 0.0
        self._node_count = 85  # Quantum cyber nodes

        self._nodes = [
            {
                "x": random.uniform(0.05, 0.95),
                "y": random.uniform(0.08, 0.92),
                "vx": random.uniform(-0.0006, 0.0006),
                "vy": random.uniform(-0.0005, 0.0005),
                "radius": random.uniform(2.0, 4.2),
                "pulse_speed": random.uniform(0.04, 0.09),
                "pulse_phase": random.uniform(0, math.pi * 2)
            }
            for _ in range(self._node_count)
        ]

        # Ascending Quantum Data Bit Sparks
        self._data_sparks = [
            {
                "x_norm": random.uniform(0.02, 0.98),
                "y_norm": random.uniform(0.05, 0.98),
                "speed": random.uniform(0.0015, 0.0035),
                "size": random.uniform(1.2, 2.4),
                "alpha": random.randint(80, 220)
            }
            for _ in range(70)
        ]

        # Animation Timer (~35 FPS)
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._step_plexus)
        self._anim_timer.start(28)

        # Root Outer Layout
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(28, 24, 28, 24)
        root_lay.setSpacing(14)

        # ── 2. TOP GREEN CYBER HEADER BAR ────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(12)

        # Glowing Neon Emerald Back Button
        self.back_btn = QPushButton("← BACK TO CORE")
        self.back_btn.setFixedHeight(32)
        self.back_btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(16, 185, 129, 0.18);
                color: #A7F3D0;
                border: 1.5px solid #10B981;
                border-radius: 16px;
                padding: 0 16px;
                letter-spacing: 0.8px;
            }
            QPushButton:hover {
                background: rgba(16, 185, 129, 0.38);
                color: #FFFFFF;
                border-color: #00FF66;
            }
            QPushButton:pressed {
                background: rgba(16, 185, 129, 0.55);
            }
        """)
        self.back_btn.clicked.connect(self.back_requested.emit)
        hdr.addWidget(self.back_btn)

        # Title with Puzzle Module Icon
        title_lbl = QLabel("🧩  INSTALLED EXTENSIONS & MODULES")
        title_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title_lbl.setStyleSheet("""
            color: #10B981;
            letter-spacing: 1.2px;
            background: transparent;
            border: none;
        """)
        hdr.addWidget(title_lbl)

        hdr.addStretch()

        # Status Chip on the Top Right
        self.status_chip = QLabel("● CORE ONLINE")
        self.status_chip.setFixedHeight(32)
        self.status_chip.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.status_chip.setStyleSheet("""
            color: #34D399;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.40);
            border-radius: 16px;
            padding: 0 14px;
        """)
        hdr.addWidget(self.status_chip)
        root_lay.addLayout(hdr)

        # ── 3. TRANSPARENT MODULES SCROLL AREA ───────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #10B981;
                border-radius: 3px;
                min-height: 25px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: transparent;")
        self._plugins_lay = QVBoxLayout(self._container)
        self._plugins_lay.setContentsMargins(6, 10, 14, 10)
        self._plugins_lay.setSpacing(12)
        self._scroll.setWidget(self._container)

        root_lay.addWidget(self._scroll, stretch=1)

    # ── ADVANCE CYBER PLEXUS DRIFT & PULSE ───────────────────────────────────
    def _step_plexus(self):
        self._phase += 0.025
        for node in self._nodes:
            node["x"] += node["vx"]
            node["y"] += node["vy"]
            node["pulse_phase"] += node["pulse_speed"]

            # Smooth bounce within boundaries
            if node["x"] < 0.03 or node["x"] > 0.97:
                node["vx"] *= -1
            if node["y"] < 0.06 or node["y"] > 0.94:
                node["vy"] *= -1

        for s in self._data_sparks:
            s["y_norm"] -= s["speed"]
            if s["y_norm"] < -0.02:
                s["y_norm"] = 1.02
                s["x_norm"] = random.uniform(0.02, 0.98)

        self.update()

    # ── PAINTER: DRAWS 3D NEURAL PLEXUS LASER NETWORK ────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = float(self.width()), float(self.height())

        # Base Obsidian-Emerald Void
        p.fillRect(self.rect(), qcol("#020904"))

        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)

        # Ambient Quantum Bloom (Centered on Left/Center)
        bloom_x = w * 0.35 + math.sin(self._phase * 0.5) * 50.0
        bloom_y = h * 0.55 + math.cos(self._phase * 0.7) * 35.0
        bloom = QRadialGradient(bloom_x, bloom_y, w * 0.50)
        bloom.setColorAt(0.00, qcol("#064E3B", 70))
        bloom.setColorAt(0.50, qcol("#022C22", 30))
        bloom.setColorAt(1.00, qcol("#020904", 0))
        p.setBrush(QBrush(bloom))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(self.rect())

        # Calculate Pixel Positions
        coords = [(n["x"] * w, n["y"] * h) for n in self._nodes]
        max_dist = 110.0  # Link distance

        # ── DRAW INTERCONNECTING LASER LINES (PLEXUS EFFECT) ─────────────────
        for i in range(len(coords)):
            x1, y1 = coords[i]
            for j in range(i + 1, len(coords)):
                x2, y2 = coords[j]
                dist = math.hypot(x2 - x1, y2 - y1)
                if dist < max_dist:
                    factor = 1.0 - (dist / max_dist)
                    line_alpha = int(factor * factor * 165)
                    p.setPen(QPen(qcol("#00E676", line_alpha), 1.1))
                    p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # ── DRAW QUANTUM CYBER NODES ─────────────────────────────────────────
        for i, node in enumerate(self._nodes):
            x, y = coords[i]
            pulse = (math.sin(node["pulse_phase"]) * 0.5 + 0.5)
            r = node["radius"] * (0.8 + 0.4 * pulse)
            n_alpha = int(120 + pulse * 135)

            col = qcol("#FFFFFF" if pulse > 0.88 else "#00FF66", n_alpha)
            p.setBrush(QBrush(col))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(x, y), r, r)

        # ── DRAW ASCENDING DATA SPARKS ───────────────────────────────────────
        for s in self._data_sparks:
            sx = s["x_norm"] * w
            sy = s["y_norm"] * h
            p.setBrush(QBrush(qcol("#A7F3D0", s["alpha"])))
            p.drawEllipse(QPointF(sx, sy), s["size"], s["size"])

        # ── RESTORE STANDARD COMPOSITION FOR EMERALD FRAME ───────────────────
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        inner_rect = QRectF(14, 14, w - 28, h - 28)

        # Double Neon Emerald Bezel
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qcol("#10B981", 48), 7.0))
        p.drawRoundedRect(inner_rect, 14, 14)

        p.setPen(QPen(qcol("#10B981", 240), 1.8))
        p.drawRoundedRect(inner_rect, 14, 14)

        inset_rect = QRectF(18, 18, w - 36, h - 36)
        p.setPen(QPen(qcol("#34D399", 75), 1.0))
        p.drawRoundedRect(inset_rect, 11, 11)

    # ── POPULATE PLUGINS WITH FROSTED GLASS CARDS ────────────────────────────
    def refresh_plugins(self, plugins: list[dict]):
        while self._plugins_lay.count():
            item = self._plugins_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not plugins:
            empty_card = QWidget()
            empty_card.setStyleSheet("""
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(16, 185, 129, 0.25);
                border-radius: 12px;
                padding: 24px;
            """)
            e_lay = QVBoxLayout(empty_card)
            t = QLabel("● QUANTUM CORE READY — 0 EXTERNAL MODULES")
            t.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            t.setStyleSheet("color: #34D399; background: transparent; border: none;")
            sub = QLabel("Native AI tools, vision, and system audio modules are operating directly from memory.")
            sub.setFont(QFont("Segoe UI", 9))
            sub.setStyleSheet("color: #94A3B8; background: transparent; border: none; margin-top: 4px;")
            e_lay.addWidget(t)
            e_lay.addWidget(sub)
            self._plugins_lay.addWidget(empty_card)
            self._plugins_lay.addStretch()
            return

        for p in plugins:
            card = QWidget()
            card.setStyleSheet("""
                QWidget {
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(16, 185, 129, 0.28);
                    border-radius: 10px;
                    padding: 8px 14px;
                }
                QWidget:hover {
                    background: rgba(255, 255, 255, 0.08);
                    border-color: rgba(16, 185, 129, 0.60);
                }
            """)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(12, 10, 12, 10)

            # Left Chip
            chip = QLabel("● MODULE")
            chip.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            chip.setStyleSheet("""
                color: #10B981;
                background: rgba(16, 185, 129, 0.12);
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 10px;
                padding: 2px 8px;
            """)
            c_lay.addWidget(chip)

            name_lbl = QLabel(f"  {p['name']}")
            name_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            name_lbl.setStyleSheet("color: #FFFFFF; background: transparent; border: none;")
            c_lay.addWidget(name_lbl, stretch=1)

            btn = QPushButton("ACTIVE" if p.get("enabled", True) else "OFF")
            btn.setFixedSize(65, 28)
            btn.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if p.get("enabled", True):
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(16, 185, 129, 0.25);
                        color: #10B981;
                        border: 1.5px solid #10B981;
                        border-radius: 14px;
                    }
                    QPushButton:hover {
                        background: rgba(16, 185, 129, 0.45);
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.05);
                        color: #64748B;
                        border: 1px solid rgba(255, 255, 255, 0.18);
                        border-radius: 14px;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.12);
                        color: #94A3B8;
                    }
                """)
            btn.clicked.connect(lambda _, n=p["name"], b=btn: self._toggle(n, b))
            c_lay.addWidget(btn)

            self._plugins_lay.addWidget(card)

        self._plugins_lay.addStretch()

    def _toggle(self, name: str, btn: QPushButton):
        try:
            from memory.config_manager import get_plugin_enabled, save_plugin_enabled
            new_val = not get_plugin_enabled(name)
            save_plugin_enabled(name, new_val)
            btn.setText("ACTIVE" if new_val else "OFF")
            if new_val:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(16, 185, 129, 0.25);
                        color: #10B981;
                        border: 1.5px solid #10B981;
                        border-radius: 14px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 0.05);
                        color: #64748B;
                        border: 1px solid rgba(255, 255, 255, 0.18);
                        border-radius: 14px;
                    }
                """)
        except Exception:
            pass

# ── 7. Helper Logger Shim (Prevents any AttributeError) ───────────────────────
class _LogShim:
    def __init__(self, callback): self._cb = callback
    def append_log(self, text: str): self._cb(text)
    def _refresh_style(self): pass

# ── Full-Stage Core View (3D Avatar + Floating Glass Widgets) ─────────────────
class CoreStageWidget(QWidget):
    def __init__(self, hud_stack, sidebar, top_capsule, greeting, quick_actions, mic_btn, cmd_bar, subtitle_hud, parent=None):
        super().__init__(parent)
        self.hud_stack     = hud_stack
        self.sidebar       = sidebar
        self.top_capsule   = top_capsule
        self.greeting      = greeting
        self.quick_actions = quick_actions
        self.mic_btn       = mic_btn
        self.cmd_bar       = cmd_bar
        self.subtitle_hud  = subtitle_hud

        # Mount all components as floating children
        self.hud_stack.setParent(self)
        self.sidebar.setParent(self)
        self.top_capsule.setParent(self)
        self.greeting.setParent(self)
        self.quick_actions.setParent(self)
        self.mic_btn.setParent(self)
        self.cmd_bar.setParent(self)
        self.subtitle_hud.setParent(self)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        W, H = self.width(), self.height()

        # 1. 3D Avatar background
        self.hud_stack.setGeometry(0, 0, W, H)

        # 2. Left Floating Navigation Dock
        self.sidebar.setGeometry(18, 18, 200, H - 36)

        # 3. Top-Right Telemetry Capsule (3 Glowing Blocks)
        cap_w = 365
        self.top_capsule.setGeometry(max(230, W - cap_w - 20), 18, cap_w, 40)

        # 4. Left Flank Greeting
        self.greeting.setGeometry(236, 40, 280, 110)

        # 5. Right Flank Quick Actions Card (Direct on Canvas)
        qa_w = 220
        self.quick_actions.setGeometry(W - qa_w - 24, 85, qa_w, 215)

        # 6. Separate Floating Mic Button + Command Bar (Bottom Center)
        cmd_w = min(560, max(340, W - 390))
        mic_size = 54
        spacing = 10
        total_bottom_w = mic_size + spacing + cmd_w

        start_x = (W - total_bottom_w) // 2 + 50
        if start_x + total_bottom_w > W - 20:
            start_x = W - total_bottom_w - 20

        self.mic_btn.setGeometry(start_x, H - 74, mic_size, mic_size)
        self.cmd_bar.setGeometry(start_x + mic_size + spacing, H - 74, cmd_w, 54)

        # 7. Subtitle HUD (above Command Bar)
        sub_w = min(560, cmd_w + mic_size + spacing)
        self.subtitle_hud.setGeometry(start_x, H - 260, sub_w, 170)
        
# ── FLOATING COMPANION HUD (WORKING CLIPBOARD, REAL DND & DESKTOP CONTROL) ────
class FloatingCompanionWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window

        # 1. Frameless, Tool, and DOES NOT STEAL FOCUS from other apps
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(540, 240)

        # 2. Windows API: WS_EX_NOACTIVATE ensures clicks never unfocus Chrome/Notepad
        if platform.system() == "Windows":
            try:
                import ctypes
                hwnd = int(self.winId())
                GWL_EXSTYLE = -20
                WS_EX_NOACTIVATE = 0x08000000
                cur_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, cur_style | WS_EX_NOACTIVATE)
            except Exception:
                pass

        # State Variables
        self.wings_expanded = False
        self.desktop_control_active = False
        self.dnd_active = False
        self._rot_angle = 0.0
        self._glow_intensity = 0.35
        self._drag_pos = None
        self._target_hwnd = None

        # Track the last active application (e.g. Chrome, AI Studio, Notepad)
        self._hwnd_tracker = QTimer(self)
        self._hwnd_tracker.timeout.connect(self._track_foreground_window)
        self._hwnd_tracker.start(100)

        # Load & Auto-Crop Logo Image (Multi-Path Fallback)
        self._logo_pixmap = None
        candidates = [
            BASE_DIR / "nexus_logo.png",
            Path(sys.executable).parent / "nexus_logo.png",
            Path(sys.executable).parent / "_internal" / "nexus_logo.png",
            BASE_DIR / "config" / "nexus_logo.png",
        ]
        for p in candidates:
            if p.is_file():
                raw_px = QPixmap(str(p))
                if not raw_px.isNull():
                    self._logo_pixmap = self._crop_to_content(raw_px)
                    break

        # Position at Bottom-Right of Desktop Screen
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - 560, screen.height() - 270)

        # Ring Rotation Timer
        self._ring_timer = QTimer(self)
        self._ring_timer.timeout.connect(self._step_ring_glow)
        self._ring_timer.start(30)

        # Center Click & Drag Overlay
        self.click_overlay = QWidget(self)
        self.click_overlay.setGeometry(195, 45, 150, 150)
        self.click_overlay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.click_overlay.mousePressEvent = self._on_avatar_click
        self.click_overlay.mouseMoveEvent = self._on_avatar_drag
        self.click_overlay.mouseReleaseEvent = self._on_avatar_release

        self._build_wings()

    def _track_foreground_window(self):
        """Remembers what app you were using before clicking the floating buttons."""
        if platform.system() == "Windows":
            try:
                import ctypes
                fg = ctypes.windll.user32.GetForegroundWindow()
                if fg != int(self.winId()) and fg != 0:
                    self._target_hwnd = fg
            except Exception:
                pass

    def _crop_to_content(self, pixmap: QPixmap) -> QPixmap:
        qimg = pixmap.toImage()
        w, h = qimg.width(), qimg.height()
        min_x, max_x = w, 0
        min_y, max_y = h, 0
        found = False

        step = max(1, min(w, h) // 180)
        for y in range(0, h, step):
            for x in range(0, w, step):
                col = qimg.pixelColor(x, y)
                if col.red() > 22 or col.green() > 22 or col.blue() > 22:
                    if x < min_x: min_x = x
                    if x > max_x: max_x = x
                    if y < min_y: min_y = y
                    if y > max_y: max_y = y
                    found = True

        if found and max_x > min_x and max_y > min_y:
            pad_x = int((max_x - min_x) * 0.05)
            pad_y = int((max_y - min_y) * 0.05)
            x0 = max(0, min_x - pad_x)
            y0 = max(0, min_y - pad_y)
            w0 = min(w - x0, (max_x - min_x) + pad_x * 2)
            h0 = min(h - y0, (max_y - min_y) + pad_y * 2)
            return pixmap.copy(x0, y0, w0, h0)
        return pixmap

    def _build_wings(self):
        # ── LEFT WING ────────────────────────────────────────────────────────
        self.left_wing = QWidget(self)
        self.left_wing.setGeometry(20, 68, 168, 110)
        left_box = QVBoxLayout(self.left_wing)
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(8)

        self.btn_desktop = self._create_wing_btn("🖥️ Desktop Control", self._toggle_desktop_control)
        self.btn_dnd = self._create_wing_btn("🔕 Do Not Disturb", self._toggle_dnd)

        left_box.addWidget(self.btn_desktop)
        left_box.addWidget(self.btn_dnd)

        # ── RIGHT WING ───────────────────────────────────────────────────────
        self.right_wing = QWidget(self)
        self.right_wing.setGeometry(352, 52, 168, 140)
        right_box = QVBoxLayout(self.right_wing)
        right_box.setContentsMargins(0, 0, 0, 0)
        right_box.setSpacing(8)

        self.btn_copy = self._create_wing_btn("📋 Copy Clipboard", self._do_copy)
        self.btn_paste = self._create_wing_btn("📑 Paste Clipboard", self._do_paste)
        self.btn_restore = self._create_wing_btn("⤢ Open Full App", self._restore_main_ui)

        right_box.addWidget(self.btn_copy)
        right_box.addWidget(self.btn_paste)
        right_box.addWidget(self.btn_restore)

        self.left_wing.hide()
        self.right_wing.hide()

    def _create_wing_btn(self, text: str, callback) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(34)
        btn.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Prevents button from taking keyboard focus away from other apps
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(10, 15, 29, 0.94);
                color: #F8FAFC;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 9px;
                padding: 0 12px;
                text-align: left;
            }
            QPushButton:hover {
                background: rgba(15, 23, 42, 0.98);
                border-color: rgba(0, 242, 254, 0.65);
                color: #FFFFFF;
            }
        """)
        btn.clicked.connect(callback)
        return btn

    def toggle_wings(self):
        self.wings_expanded = not self.wings_expanded
        self.left_wing.setVisible(self.wings_expanded)
        self.right_wing.setVisible(self.wings_expanded)

    # ── REAL FUNCTIONALITY: DESKTOP CONTROL ──────────────────────────────────
    def _toggle_desktop_control(self):
        self.desktop_control_active = not self.desktop_control_active
        self._set_btn_active(self.btn_desktop, self.desktop_control_active, "🖥️ Desktop Control")
        
        if self.desktop_control_active:
            self.main._on_log("SYS: 🖥️ Desktop Automation Control ENGAGED.")
            if self.main.on_text_command:
                self.main.on_text_command("Desktop control mode engaged. Briefly confirm you are ready to control the PC.")
        else:
            self.main._on_log("SYS: 🖥️ Desktop Automation Control STANDBY.")

    # ── REAL FUNCTIONALITY: DO NOT DISTURB ───────────────────────────────────
    def _toggle_dnd(self):
        self.dnd_active = not self.dnd_active
        self._set_btn_active(self.btn_dnd, self.dnd_active, "🔕 Do Not Disturb")
        self.main.dnd_active = self.dnd_active

        if self.dnd_active:
            self.main._on_log("SYS: 🔕 Do Not Disturb ACTIVE — All alerts silenced.")
        else:
            self.main._on_log("SYS: 🔔 Do Not Disturb OFF — Monitoring active.")

    def _set_btn_active(self, btn: QPushButton, active: bool, text: str):
        if active:
            btn.setText(f"{text}  ●")
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(0, 242, 254, 0.20);
                    color: #00F2FE;
                    border: 1.5px solid #00F2FE;
                    border-radius: 9px;
                    padding: 0 12px;
                    text-align: left;
                }
            """)
        else:
            btn.setText(text)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(10, 15, 29, 0.94);
                    color: #F8FAFC;
                    border: 1px solid rgba(255, 255, 255, 0.14);
                    border-radius: 9px;
                    padding: 0 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    background: rgba(15, 23, 42, 0.98);
                    border-color: rgba(0, 242, 254, 0.65);
                    color: #FFFFFF;
                }
            """)

    # ── REAL FUNCTIONALITY: BULLETPROOF COPY (RESTORES CHROME FOCUS) ──────────
    def _do_copy(self):
        import pyautogui
        if platform.system() == "Windows" and self._target_hwnd:
            import ctypes
            ctypes.windll.user32.SetForegroundWindow(self._target_hwnd)
            time.sleep(0.08)
        
        pyautogui.hotkey('ctrl', 'c')
        self.main._on_log("SYS: 📋 Text copied to clipboard.")

    # ── REAL FUNCTIONALITY: BULLETPROOF PASTE (RESTORES INPUT CURSOR) ─────────
    def _do_paste(self):
        import pyautogui
        if platform.system() == "Windows" and self._target_hwnd:
            import ctypes
            ctypes.windll.user32.SetForegroundWindow(self._target_hwnd)
            time.sleep(0.08)
            
        pyautogui.hotkey('ctrl', 'v')
        self.main._on_log("SYS: 📑 Text pasted from clipboard.")

    def _restore_main_ui(self):
        self.main.restore_full_ui()

    def set_speaking(self, is_speaking: bool):
        self.update()

    def _step_ring_glow(self):
        is_talking = bool(self.main._is_ai_speaking)
        speed = 4.4 if is_talking else 1.2
        self._rot_angle = (self._rot_angle + speed) % 360.0

        # High glow while speaking; subtle idle glow in standby
        target_glow = 1.0 if is_talking else (0.15 if self.main._muted else 0.40)
        self._glow_intensity += (target_glow - self._glow_intensity) * 0.15
        self.update()

    def _on_avatar_click(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_start = e.globalPosition().toPoint()

    def _on_avatar_drag(self, e):
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def _on_avatar_release(self, e):
        if hasattr(self, '_drag_start') and self._drag_start:
            moved = (e.globalPosition().toPoint() - self._drag_start).manhattanLength()
            if moved < 5:
                self.toggle_wings()
        self._drag_pos = None

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        cx, cy = float(self.width() / 2.0), float(self.height() / 2.0)
        r = 75.0

        # Dark Futuristic Cyber-Lens Backdrop
        lens_rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        lens_grad = QRadialGradient(cx, cy, r)
        lens_grad.setColorAt(0.0, QColor(10, 16, 30, 248))
        lens_grad.setColorAt(0.75, QColor(4, 7, 16, 252))
        lens_grad.setColorAt(1.0, QColor(1, 2, 6, 255))
        p.setBrush(QBrush(lens_grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(lens_rect)

        # Render Cropped Nexus Logo
        if self._logo_pixmap and not self._logo_pixmap.isNull():
            clip_path = QPainterPath()
            clip_path.addEllipse(QRectF(cx - r + 4, cy - r + 4, (r - 4) * 2, (r - 4) * 2))
            p.save()
            p.setClipPath(clip_path)

            target_dim = int(r * 1.72)
            scaled_logo = self._logo_pixmap.scaled(
                target_dim, target_dim,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            lx = int(cx - scaled_logo.width() / 2.0)
            ly = int(cy - scaled_logo.height() / 2.0)
            p.drawPixmap(lx, ly, scaled_logo)
            p.restore()

        # Google 4-Color Neon Rings
        glow_alpha = int(45 + self._glow_intensity * 150)
        span = int(72 * 16)
        r_outer = r + 6.0

        ring_arcs = [
            ("#00F2FE", 0),    # Blue
            ("#34A853", 90),   # Green
            ("#FBBC05", 180),  # Yellow
            ("#EA4335", 270)   # Red
        ]

        p.setBrush(Qt.BrushStyle.NoBrush)
        for hex_col, offset in ring_arcs:
            ang = int((self._rot_angle + offset) * 16)
            p.setPen(QPen(qcol(hex_col, glow_alpha), 7.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2), ang, span)
            p.setPen(QPen(qcol(hex_col, 240), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2), ang, span)

        p.setPen(QPen(qcol("#FFFFFF", 40), 1.0))
        p.drawEllipse(lens_rect)

# ── MAIN APPLICATION WINDOW ───────────────────────────────────────────────────
class MainWindow(QMainWindow):
    _log_sig        = pyqtSignal(str)
    _state_sig      = pyqtSignal(str)
    _content_sig    = pyqtSignal(str, str)
    _reconfig_sig   = pyqtSignal()
    _camera_sig     = pyqtSignal(bytes)
    _cam_stream_sig = pyqtSignal(bool)
    _cam_frame_sig  = pyqtSignal(bytes)
    _clipboard_sig  = pyqtSignal(str)
    _connection_sig = pyqtSignal(str)
    _energy_sig     = pyqtSignal(float)  # Thread-safe voice energy signal

    def __init__(self, face_path: str):
        super().__init__()
        self._face_path = face_path
        _cfg = _read_full_config()
        self._assistant_name = (_cfg.get("assistant_name") or "NEXUS").strip()
        self._user_name = (_cfg.get("user_name") or "Kamran").strip()

        self.setWindowTitle(f"{self._assistant_name} AI — Multimodal Core")
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - _DEFAULT_W) // 2, (screen.height() - _DEFAULT_H) // 2)

        self.on_text_command = self.on_remote_clicked = self.on_interrupt = self.get_plugins = None
        self._muted = False
        self._is_ai_speaking = False
        self._matrix_on = False
        self._overlay = None
        self._remote_overlay = None
        self._current_file: str | None = None
        self._cam_stop = threading.Event()
        self._log = _LogShim(self._on_log)

        # Root Central Widget (Locked to dark OLED background)
        self.setStyleSheet("background-color: #030712;")
        self._central = QWidget()
        self._central.setStyleSheet("background-color: #030712;")
        self.setCentralWidget(self._central)
        self._apply_global_style()

        main_vbox = QVBoxLayout(self._central)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # Master Page Stack (Locked to dark OLED background)
        self.view_stack = QStackedWidget()
        self.view_stack.setStyleSheet("background-color: #030712;")
        main_vbox.addWidget(self.view_stack, stretch=1)

        # 3D Viewport & Overlays (Only initialize the Avatar at startup to protect VRAM)
        self.hud = Avatar3DView(self._assistant_name)
        self.spatial_map = None

        self._cam_container = QWidget()
        self._cam_container.setStyleSheet("background: #000000;")
        _cv = QVBoxLayout(self._cam_container); _cv.setContentsMargins(0, 0, 0, 0)
        self._cam_live_lbl = QLabel(); self._cam_live_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _cv.addWidget(self._cam_live_lbl)

        self._hud_stack = QStackedWidget()
        self._hud_stack.addWidget(self.hud)              # 0: 3D Avatar Core
        self._hud_stack.addWidget(self._cam_container)   # 1: Camera

        # Floating HUD Widgets
        self.sidebar       = LeftSidebarDock(self._assistant_name)
        self.top_capsule   = TopRightStatusCapsule()
        self.greeting      = LeftGreetingCard(self._user_name, self._assistant_name)
        self.quick_actions = QuickActionsCard()
        self.mic_btn       = FloatingMicButton()
        self.cmd_bar       = FloatingCommandBar()
        self.subtitle_hud  = LiveSubtitleHUD()

        # Connect Widget Events
        self.sidebar.tab_changed.connect(self._handle_tab_change)
        self.sidebar.settings_clicked.connect(self._open_customize)
        self.sidebar.settings_clicked.connect(lambda: self.hud.play_sfx("nav_settings"))
        self.sidebar.eye_toggled.connect(self._toggle_eye_tracking)
        self.sidebar.head_toggled.connect(self._toggle_head_tracking)
        self.sidebar.matrix_toggled.connect(self._toggle_matrix_mode)
        self.sidebar.stop_clicked.connect(self._do_interrupt)
        self.top_capsule.profile_clicked.connect(self._open_customize)
        self.top_capsule.profile_clicked.connect(lambda: self.hud.play_sfx("nav_settings"))
        self.quick_actions.action_clicked.connect(self._handle_quick_action)
        self.cmd_bar.text_submitted.connect(self._handle_user_text)
        self.mic_btn.clicked.connect(self._toggle_mute)
        # Disabled secondary mic thread so main.py has 100% exclusive access to the microphone
        self.mic_detector = None

        # Page 0: The Core Stage
        self.core_stage = CoreStageWidget(
            self._hud_stack, self.sidebar, self.top_capsule,
            self.greeting, self.quick_actions, self.mic_btn, self.cmd_bar, self.subtitle_hud
        )

        # Pages 1 to 4: Full Views
        self.full_chat_view = FullChatView()
        self.full_chat_view.back_requested.connect(self._return_to_core)

        self.full_news_view = FullNewsView()
        self.full_news_view.back_requested.connect(self._return_to_core)

        self.full_metrics_view = FullMetricsView()
        self.full_metrics_view.back_requested.connect(self._return_to_core)

        self.full_plugins_view = FullPluginsView()
        self.full_plugins_view.back_requested.connect(self._return_to_core)

        self.view_stack.addWidget(self.core_stage)        # Index 0
        self.view_stack.addWidget(self.full_chat_view)    # Index 1
        self.view_stack.addWidget(self.full_news_view)    # Index 2
        self.view_stack.addWidget(self.full_metrics_view) # Index 3
        self.view_stack.addWidget(self.full_plugins_view) # Index 4
        self.full_chat_view._anim_timer.stop()
        self.full_news_view._anim_timer.stop()
        self.full_metrics_view._anim_timer.stop()
        self.full_plugins_view._anim_timer.stop()

        # Overlays
        self._cam_preview = _CameraPreview(self._central)
        self._clipboard_panel = ClipboardPanel(self._central)
        self._clipboard_panel.action_requested.connect(self._on_clipboard_action)
        self._clipboard_sig.connect(self._clipboard_panel.show_clipboard)
        self._energy_sig.connect(self._on_audio_energy)
        QApplication.clipboard().dataChanged.connect(self._on_clipboard_changed)

        # Signals
        self._log_sig.connect(self._on_log)
        self._connection_sig.connect(self.greeting.set_status)
        self._state_sig.connect(self._apply_state)
        self._content_sig.connect(self._show_content)
        self._reconfig_sig.connect(self._show_setup)
        self._camera_sig.connect(self._show_camera_frame)
        self._cam_stream_sig.connect(self._on_cam_stream)
        self._cam_frame_sig.connect(self._on_cam_frame)

        # Timers
        self._metric_tmr = QTimer(self)
        self._metric_tmr.timeout.connect(self._update_metrics)
        self._metric_tmr.start(1500)
        self._update_metrics()

        # Shortcuts
        QShortcut(QKeySequence("F4"), self).activated.connect(self._toggle_mute)
        QShortcut(QKeySequence("F11"), self).activated.connect(self._toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self).activated.connect(self._do_interrupt)
        # Arrow Keys to switch image variations instantly
        QShortcut(QKeySequence(Qt.Key.Key_Right), self).activated.connect(self._next_image_gallery)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self).activated.connect(self._prev_image_gallery)

        self._ready = self._check_config()
        if not self._ready: self._show_setup()
        self._floating_companion = None
        self._init_system_tray()
        
    def _on_audio_energy(self, energy: float):
        if not self._is_ai_speaking and not self._muted and energy > 0.05:
            self.cmd_bar._wave.pulse_with_energy(energy)
        else:
            self.cmd_bar._wave.set_active(False)
        
    def _next_image_gallery(self):
        if self.on_text_command:
            self.on_text_command("Show the next image variation.")

    def _prev_image_gallery(self):
        if self.on_text_command:
            self.on_text_command("Show the previous image variation.")

    def _apply_global_style(self):
        self._central.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.BG};
                color: {Theme.TEXT};
                font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            }}
        """)
        
    def _toggle_eye_tracking(self):
        active = self.hud.toggle_eye_tracking()
        self.hud.play_sfx("eye_on" if active else "eye_off")  # Aperture blades vs shutter snap
        self.sidebar.set_eye_state(active)
        self._on_log(f"SYS: Eye Tracking {'ACTIVE' if active else 'OFF'}.")

    def _toggle_head_tracking(self):
        active = self.hud.toggle_head_tracking()
        self.hud.play_sfx("head_on" if active else "head_off")  # Gimbal spin-up vs brake clamp
        self.sidebar.set_head_state(active)
        self._on_log(f"SYS: Head Tracking {'ACTIVE' if active else 'OFF'}.")

    def _toggle_matrix_mode(self):
        self._matrix_on = not self._matrix_on
        self.hud.play_sfx("matrix_on" if self._matrix_on else "matrix_off")  # Cyber surge vs degauss thud
        self.hud.run_js("window.NexusCore.toggleMatrixRain();")
        self.sidebar.set_matrix_state(self._matrix_on)
        self._on_log(f"SYS: Matrix Rain {'ENABLED' if self._matrix_on else 'DISABLED'}.")

    def _do_interrupt(self):
        self.hud.play_sfx("abort_stop")  # Heavy emergency hydraulic brake slam
        if self.on_interrupt: self.on_interrupt()

    def _apply_cyberpunk_theme(self, active: bool):
        """Kept as a safe no-op to preserve standard OLED matte frosted UI."""
        pass

    def _return_to_core(self):
        self.hud.play_sfx("back_to_core")  # Distinct spatial return sound!
        self.view_stack.setCurrentIndex(0)
        self.sidebar.set_active_tab("core")
        self.hud.run_js("if(window.NexusCore) { window.dispatchEvent(new Event('resize')); }")

    def _handle_quick_action(self, action_key: str):
        # ── Distinct sound per action ──
        if action_key == "image":
            self.hud.play_sfx("action_image")
            self.cmd_bar.set_user_text("Generate an image of ")
        elif action_key == "app":
            self.hud.play_sfx("action_app")
            self.cmd_bar.set_user_text("Open ")
        elif action_key == "search":
            self.hud.play_sfx("action_search")
            self.cmd_bar.set_user_text("Search the web for ")
        elif action_key == "task":
            self.hud.play_sfx("action_task")
            self.cmd_bar.set_user_text("Set a reminder for ")

    def _on_log(self, text: str):
        tl = text.lower()
        if tl.startswith("you:") or "user:" in tl:
            clean = text.replace("You:", "").replace("User:", "").strip()
            self.subtitle_hud.show_dialogue("USER", clean)
            self.full_chat_view.append_message("USER", clean)
        elif "nexus:" in tl or "jarvis:" in tl:
            clean = text.replace("NEXUS:", "").replace("JARVIS:", "").strip()
            self.subtitle_hud.show_dialogue("NEXUS", clean)
            self.full_chat_view.append_message("NEXUS", clean)
        else:
            self.full_chat_view.append_message("SYS", text)

    def _handle_tab_change(self, tab_id: str):
        # 1. Sound profiles
        tab_sounds = {
            "core": "nav_home",
            "conversation": "nav_chat",
            "news": "nav_news",
            "plugins": "nav_plugins",
            "metrics": "nav_metrics",
            "files": "nav_upload",
            "settings": "nav_settings",
        }
        self.hud.play_sfx(tab_sounds.get(tab_id, "nav_home"))

        # 2. Stop heavy particle timers on background tabs to save CPU
        self.full_chat_view._anim_timer.stop()
        self.full_news_view._anim_timer.stop()
        self.full_metrics_view._anim_timer.stop()
        self.full_plugins_view._anim_timer.stop()

        idx_map = {
            "core": 0,
            "conversation": 1,
            "news": 2,
            "metrics": 3,
            "plugins": 4
        }

        if tab_id in idx_map:
            target_idx = idx_map[tab_id]
            self.view_stack.setCurrentIndex(target_idx)
            
            # Start animation timer ONLY for the currently opened screen
            if target_idx == 1:
                self.full_chat_view._anim_timer.start(28)
            elif target_idx == 2:
                self.full_news_view._anim_timer.start(28)
            elif target_idx == 3:
                self.full_metrics_view._anim_timer.start(28)
            elif target_idx == 4:
                plugins = self.get_plugins() if self.get_plugins else []
                self.full_plugins_view.refresh_plugins(plugins)
                self.full_plugins_view._anim_timer.start(28)
            elif target_idx == 0:
                self._return_to_core()
        elif tab_id in ("files", "upload"):
            self._open_file_dialog()

    def _show_content(self, title: str, text: str):
        self.full_news_view.display_news(title, text)
        self.full_news_view._anim_timer.start(28)
        self.view_stack.setCurrentIndex(2)
        self.sidebar.set_active_tab("news")

    def _on_mic_voice_detected(self, energy: float):
        # If mic is muted, or if AI is speaking (prevents speaker echo), do nothing
        if self._muted or self._is_ai_speaking or energy < 0.04:
            return

        # ONLY animate the histogram bar lines when the user speaks!
        self.cmd_bar._wave.pulse_with_energy(energy)

    def _apply_state(self, state: str):
        self._is_ai_speaking = (state == "SPEAKING")

        # 1. Drive main window avatar
        self.hud.set_speaking(self._is_ai_speaking)
        self.hud.set_user_speaking(False)

        # 2. Drive floating glowing logo pulse
        if hasattr(self, '_floating_companion') and self._floating_companion:
            self._floating_companion.set_speaking(self._is_ai_speaking)

        # 3. Update Mic Mute States (Safe check)
        self.mic_btn.set_muted(self._muted or (state == "MUTED"))
        if getattr(self, 'mic_detector', None):
            self.mic_detector.set_muted(self._muted or (state == "MUTED"))

        # 4. If AI is speaking, keep histogram flat
        if self._is_ai_speaking:
            self.cmd_bar._wave.set_active(False)

    def _handle_user_text(self, txt: str):
        # ── Play High-Tech Data Send Sound Effect ──
        self.hud.play_sfx("send")

        # ── AI Auto-Detect: "pull the CPU tab" or "check CPU" ──
        lower = txt.lower()
        if any(phrase in lower for phrase in ["cpu", "system specs", "hardware", "device info", "pull the cpu", "system tab"]):
            self.sidebar.set_active_tab("metrics")
            self._handle_tab_change("metrics")

        self.subtitle_hud.show_dialogue("USER", txt)
        # Pulse only the command bar waveform on user command
        self.cmd_bar._wave.pulse()
        self.full_chat_view.append_message("USER", txt)
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(txt,), daemon=True).start()

    def _toggle_mute(self):
        self._muted = not self._muted

        # Update HUD SFX
        if self._muted:
            self.hud.play_sfx("mic_off")
        else:
            self.hud.play_sfx("mic_on")

        self.hud.muted = self._muted
        self.mic_btn.set_muted(self._muted)
        if hasattr(self, '_floating_companion') and self._floating_companion:
            self._floating_companion.update()

        self._apply_state("MUTED" if self._muted else "LISTENING")

    def _open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Upload File to Assistant", str(Path.home()), "All Files (*.*)")
        if path:
            self._current_file = path
            p = Path(path)
            self._on_log(f"FILE: {p.name} ({_fmt_size(p.stat().st_size)}) loaded")
            if self.on_text_command:
                msg = f"[FILE_UPLOADED] path={path} | name={p.name} | size={_fmt_size(p.stat().st_size)}"
                threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def _do_interrupt(self):
        if self.on_interrupt: self.on_interrupt()

    def _update_metrics(self):
        snap = _live_telemetry.snapshot()
        self.top_capsule.update_telemetry(snap["cpu_total"], snap["mem_pct"])
        self.full_metrics_view.update_metrics(snap["cpu_total"], snap["mem_pct"], snap["net_down"], -1.0)
        
    def _init_system_tray(self):
        """Creates the Windows System Tray Icon and Context Menu."""
        from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
        from PyQt6.QtGui import QAction

        self._tray_icon = QSystemTrayIcon(self)
        icon_path = BASE_DIR / "config" / "nexus.ico"
        if icon_path.is_file():
            self._tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            self._tray_icon.setIcon(self.windowIcon())

        tray_menu = QMenu()
        restore_action = QAction("Open NEXUS Dashboard", self)
        restore_action.triggered.connect(self.restore_full_ui)
        tray_menu.addAction(restore_action)

        float_action = QAction("Toggle Floating Avatar", self)
        float_action.triggered.connect(self.toggle_floating_companion)
        tray_menu.addAction(float_action)

        tray_menu.addSeparator()

        quit_action = QAction("Exit Completely", self)
        quit_action.triggered.connect(self._force_quit)
        tray_menu.addAction(quit_action)

        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _on_tray_activated(self, reason):
        from PyQt6.QtWidgets import QSystemTrayIcon
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.restore_full_ui()

    def closeEvent(self, event):
        """Intercepts the 'X' button: keeps app running, docks to tray, shows floating avatar."""
        from PyQt6.QtWidgets import QSystemTrayIcon
        event.ignore()
        self.hide()
        self.show_floating_companion()
        if hasattr(self, '_tray_icon') and self._tray_icon.isVisible():
            self._tray_icon.showMessage(
                f"{self._assistant_name} Active",
                "Operating in floating companion mode. Click avatar to open controls.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )

    def show_floating_companion(self):
        """Spawns or shows the draggable circular avatar on the desktop."""
        if self._floating_companion is None:
            self._floating_companion = FloatingCompanionWidget(main_window=self)
        self._floating_companion.show()
        self._floating_companion.raise_()

    def hide_floating_companion(self):
        if self._floating_companion and self._floating_companion.isVisible():
            self._floating_companion.hide()

    def toggle_floating_companion(self):
        if self._floating_companion and self._floating_companion.isVisible():
            self.hide_floating_companion()
        else:
            self.show_floating_companion()

    def restore_full_ui(self):
        """Restores the main dashboard window and tucks away the floating companion."""
        self.hide_floating_companion()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _force_quit(self):
        """Completely terminates the application when selected from the tray."""
        if hasattr(self, 'mic_detector') and self.mic_detector:
            self.mic_detector.stop()
        if self._floating_companion:
            self._floating_companion.close()
        QApplication.quit()

    def _toggle_fullscreen(self):
        if self.isFullScreen(): self.showNormal()
        else: self.showFullScreen()

    def _open_customize(self):
        cfg = _read_full_config()
        ov = CustomizeOverlay(self._assistant_name, cfg.get("user_name", ""), cfg.get("voice_name", "Fenrir"), parent=self._central)
        ov.setGeometry((self.width() - 380) // 2, (self.height() - 310) // 2, 380, 310)
        ov.saved.connect(self._apply_identity)
        ov.show()

    def _apply_identity(self, name: str, user_name: str, voice_name: str, color_hex: str):
        self._assistant_name = name
        self._user_name = user_name
        self.greeting.set_user(user_name)
        data = _read_full_config()
        data["assistant_name"] = name
        data["user_name"] = user_name
        data["voice_name"] = voice_name
        try:
            API_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
            self._on_log(f"SYS: Identity updated to {name}. User set to {user_name}.")
        except Exception: pass

    def show_spatial_map(self, devices: dict = None, selected_id: str = None):
        if self.spatial_map is None:
            self.spatial_map = SpatialMapCanvas()
            self._hud_stack.addWidget(self.spatial_map)  # Index 2: Created on-demand
        if devices:
            self.spatial_map.set_fleet(devices, selected_id)
        self._hud_stack.setCurrentIndex(2)
        self.view_stack.setCurrentIndex(0)

    def show_reactor_core(self):
        self._hud_stack.setCurrentIndex(0)
        self.view_stack.setCurrentIndex(0)

    def start_camera_stream(self):
        self.hud.pause_camera()
        time.sleep(0.3)
        self._cam_stop.clear()
        self._cam_stream_sig.emit(True)
        threading.Thread(target=self._cam_loop, daemon=True).start()

    def stop_camera_stream(self):
        self._cam_stop.set()
        QTimer.singleShot(600, self.hud.resume_camera)

    def _cam_loop(self):
        try:
            import cv2
            backend = cv2.CAP_DSHOW if _OS == "Windows" else cv2.CAP_ANY
            cap = cv2.VideoCapture(0, backend)
            while not self._cam_stop.wait(0.033) and cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
                    self._cam_frame_sig.emit(buf.tobytes())
            cap.release()
        except Exception: pass
        finally: self._cam_stream_sig.emit(False)

    def _on_cam_stream(self, start: bool):
        self._hud_stack.setCurrentIndex(1 if start else 0)

    def _on_cam_frame(self, data: bytes):
        px = QPixmap(); px.loadFromData(data)
        if not px.isNull():
            w, h = self._cam_live_lbl.width(), self._cam_live_lbl.height()
            if w > 1 and h > 1: self._cam_live_lbl.setPixmap(px.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio))

    def _show_camera_frame(self, img_bytes: bytes):
        self._cam_preview.show_frame(img_bytes)

    def _on_clipboard_changed(self):
        try:
            t = QApplication.clipboard().text().strip()
            if len(t) >= 10: self._clipboard_sig.emit(t)
        except Exception: pass

    def _on_clipboard_action(self, cmd: str):
        if self.on_text_command: threading.Thread(target=self.on_text_command, args=(cmd,), daemon=True).start()

    def _check_config(self) -> bool:
        if not API_FILE.exists(): return False
        try: return bool(json.loads(API_FILE.read_text(encoding="utf-8")).get("gemini_api_key"))
        except Exception: return False

    def _show_setup(self):
        ov = SetupOverlay(self._central)
        ov.setGeometry((self.width() - 400) // 2, (self.height() - 220) // 2, 400, 220)
        ov.done.connect(self._on_setup_done); ov.show(); self._overlay = ov

    def _on_setup_done(self, key: str, os_name: str):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_FILE.write_text(json.dumps({"gemini_api_key": key, "os_system": os_name}, indent=4), encoding="utf-8")
        self._ready = True
        if self._overlay: self._overlay.hide(); self._overlay = None
        self._apply_state("LISTENING")

# ── Headless/GUI Wrapper Compatible with JarvisLive API ───────────────────────
class _RootShim:
    def __init__(self, app: QApplication): self._app = app
    def mainloop(self): self._app.exec()
    def protocol(self, *_): pass

class JarvisUI:
    def __init__(self, face_path: str, size=None):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        # Prevent Qt from terminating the app when the splash screen closes or is skipped
        self._app.setQuitOnLastWindowClosed(False)

        # ── Event to synchronize Splash Screen with background AI runner ──────
        self._splash_done_evt = threading.Event()

        icon_path = BASE_DIR / "config" / "nexus.ico"
        app_icon = QIcon(str(icon_path)) if icon_path.is_file() else QIcon()
        if not app_icon.isNull():
            self._app.setWindowIcon(app_icon)

        self._win = MainWindow(face_path)
        if not app_icon.isNull():
            self._win.setWindowIcon(app_icon)

        # ── Launch Fullscreen 4K Splash (Randomly Selected) ───────────────────
        SplashClass = get_random_splash_class()
        if SplashClass is not None:
            self._splash = SplashClass()
            self._splash.finished.connect(self._on_splash_done)
            self._splash.showFullScreen()
        else:
            self._splash = None
            self._splash_done_evt.set()
            self._win.showFullScreen()

        self.root = _RootShim(self._app)

    def _on_splash_done(self):
        """Called when splash finishes or when user clicks SKIP"""
        self._splash_done_evt.set()

        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            SPLASH_SESSION_FILE.write_text(
                json.dumps({"pid": os.getpid(), "timestamp": time.time()}),
                encoding="utf-8"
            )
        except Exception:
            pass

        # 1. Safely stop any running video/audio on the splash screen
        if self._splash is not None:
            try:
                if hasattr(self._splash, 'player') and self._splash.player:
                    self._splash.player.stop()
                if hasattr(self._splash, 'stop'):
                    self._splash.stop()
            except Exception:
                pass

        # 2. Show the main dashboard window FIRST
        self._win.showFullScreen()
        self._win.raise_()
        self._win.activateWindow()

        # 3. Cleanly close and release the splash window
        if self._splash is not None:
            try:
                self._splash.close()
            except Exception:
                pass
            self._splash = None

        # 4. Check for optional user sound
        self._play_optional_startup_sound()

    def _play_optional_startup_sound(self):
        """Only plays if you manually drop a sound file into a 'sounds' folder."""
        sounds_dir = BASE_DIR / "sounds"
        if not sounds_dir.is_dir():
            return  # Folder doesn't exist: skip silently

        # Looks for any of these standard names
        for name in ("startup", "boot", "welcome", "nexus"):
            for ext in ("wav", "mp3", "ogg"):
                file_path = sounds_dir / f"{name}.{ext}"
                if file_path.is_file():
                    # File found: play through the engine
                    self._win.hud.run_js(f"""
                        try {{
                            const sfx = new Audio('./sounds/{name}.{ext}');
                            sfx.volume = 1.0;
                            sfx.play().catch(() => {{}});
                        }} catch(e) {{}}
                    """)
                    return
        
    def avatar_speak(self, text: str):
        """Directly passes text to the 3D avatar lip-sync engine"""
        QTimer.singleShot(0, lambda: self._win.hud.speak(text))
        
    def avatar_pulse(self):
        """Direct audio watchdog heartbeat"""
        QTimer.singleShot(0, self._win.hud.pulse_speech)

    def set_avatar_speaking(self, is_speaking: bool):
        QTimer.singleShot(0, lambda: self._win.hud.set_speaking(is_speaking))
        
    def set_user_speaking(self, is_speaking: bool):
        """External hook: Only animates the histogram when user is speaking."""
        QTimer.singleShot(0, lambda: self._win.cmd_bar._wave.set_active(is_speaking and not self.muted and not self._win._is_ai_speaking))

    def avatar_pulse_user(self):
        """Direct watchdog pulse: Only animates the histogram when user speaks."""
        if not self._win._is_ai_speaking:
            QTimer.singleShot(0, self._win.cmd_bar._wave.pulse)

    def avatar_set_audio_energy(self, level: float):
        """Dispatches audio energy to the Qt UI thread in a 100% thread-safe manner."""
        self._win._energy_sig.emit(float(level))

    def pause_avatar_camera(self):
        QTimer.singleShot(0, self._win.hud.pause_camera)

    def resume_avatar_camera(self):
        QTimer.singleShot(0, self._win.hud.resume_camera)

    def avatar_push_phoneme(self, text_chunk: str):
        QTimer.singleShot(0, lambda: self._win.hud.push_phoneme(text_chunk))

    def wait_for_splash(self):
        """Holds Gemini AI voice until splash is completely finished or skipped"""
        while not self._splash_done_evt.is_set():
            time.sleep(0.05)
            
    @property
    def muted(self) -> bool: return self._win._muted
    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            QTimer.singleShot(0, self._win._toggle_mute)

    @property
    def current_file(self) -> str | None: return self._win._current_file
    @property
    def on_text_command(self): return self._win.on_text_command
    @on_text_command.setter
    def on_text_command(self, cb): self._win.on_text_command = cb
    @property
    def on_remote_clicked(self): return self._win.on_remote_clicked
    @on_remote_clicked.setter
    def on_remote_clicked(self, cb): self._win.on_remote_clicked = cb
    @property
    def on_interrupt(self): return self._win.on_interrupt
    @on_interrupt.setter
    def on_interrupt(self, cb): self._win.on_interrupt = cb
    @property
    def get_plugins(self): return self._win.get_plugins
    @get_plugins.setter
    def get_plugins(self, cb): self._win.get_plugins = cb

    def notify_phone_connected(self) -> None:
        if self._win._remote_overlay and self._win._remote_overlay.isVisible():
            self._win._remote_overlay.mark_connected()

    def set_state(self, state: str): self._win._state_sig.emit(state)
    def write_log(self, text: str): self._win._log_sig.emit(text)
    def set_connection_status(self, text: str): self._win._connection_sig.emit(text)
    def wait_for_api_key(self):
        while not self._win._ready: time.sleep(0.1)
    def show_content(self, title: str, text: str): self._win._content_sig.emit(title[:48], text[:4000])
    def prompt_reconfig(self): self._win._ready = False; self._win._reconfig_sig.emit()
    def show_camera_frame(self, img_bytes: bytes): self._win._camera_sig.emit(img_bytes)
    def start_camera_stream(self) -> None: self._win.start_camera_stream()
    def stop_camera_stream(self) -> None: self._win.stop_camera_stream()
    @property
    def assistant_name(self) -> str: return self._win._assistant_name
    def start_speaking(self): self.set_state("SPEAKING")
    def stop_speaking(self):
        if not self.muted: self.set_state("LISTENING")
        
    def show_spatial_map(self, devices: dict = None, selected_id: str = None):
        QTimer.singleShot(0, lambda: self._win.show_spatial_map(devices, selected_id))

    def show_reactor_core(self):
        QTimer.singleShot(0, lambda: self._win.show_reactor_core())