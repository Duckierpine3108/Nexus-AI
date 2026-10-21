"""
actions/system_monitor.py
Nexus AI — Enterprise Hardware Telemetry & Process Governance Core (v4.0)

Capabilities:
- Comprehensive Hardware Telemetry: CPU (cores/frequency/temp), RAM/Swap, GPU/VRAM, Storage, Battery
- Deep NVML Integration: Subprocess-free NVIDIA GPU load, memory, and thermal inspection
- Root-Cause Diagnostics: Real-time top resource-consuming process identification
- Process Governance: Remedial process termination with system-critical safety shields
- Stateful Background Monitor: Threshold alerts with cooldown rate-limiters
- Adaptive PyQt6 HUD Integration: Mode 3 Knowledge Search HUD real-time display
"""

import os
import re
import sys
import time
import ctypes
import platform
from pathlib import Path
from datetime import datetime

import psutil

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"

DEFAULT_THRESHOLDS = {
    "cpu": 90.0,
    "ram": 90.0,
    "temp": 85.0,
    "gpu": 95.0,
}

_COOLDOWN = 300
_CPU_STREAK = 3

# ─────────────────────────────────────────────────────────────────────────────
# UI HUD INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

def _push_to_ui_hud(title: str, content: str, mode: int = 3, items: list = None) -> None:
    """Streams hardware telemetry to ui.py Adaptive HUD if loaded."""
    try:
        ui_mod = sys.modules.get("ui")
        if not ui_mod:
            return
        if hasattr(ui_mod, "update_adaptive_hud"):
            ui_mod.update_adaptive_hud(title=title, content=content, mode=mode, items=items)
        elif hasattr(ui_mod, "app_instance") and ui_mod.app_instance:
            inst = ui_mod.app_instance
            if hasattr(inst, "show_hud"):
                inst.show_hud(title=title, content=content, mode=mode, items=items)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# ZERO-SUBPROCESS NVIDIA NVML TELEMETRY
# ─────────────────────────────────────────────────────────────────────────────

_nvml_lib: object = None
_nvml_ok: object = None  # None = untested, True = operational, False = unavailable


def _init_nvml() -> bool:
    global _nvml_lib, _nvml_ok
    if _nvml_ok is not None:
        return _nvml_ok

    try:
        if _OS == "Windows":
            candidates = ("nvml.dll", r"C:\Windows\System32\nvml.dll")
            _load = ctypes.WinDLL
        else:
            candidates = (
                "libnvidia-ml.so.1",
                "libnvidia-ml.so",
                "libnvidia-ml.dylib",
            )
            _load = ctypes.CDLL

        for name in candidates:
            try:
                lib = _load(name)
                res = lib.nvmlInit_v2()
                if res == 0:
                    _nvml_lib = lib
                    _nvml_ok = True
                    return True
            except Exception:
                continue
    except Exception:
        pass

    _nvml_ok = False
    return False


def _get_gpu_telemetry() -> dict:
    """Extracts GPU core utilization, VRAM usage, temperature, and device name."""
    # Method 1: pynvml wrapper if installed
    try:
        import pynvml  # type: ignore
        pynvml.nvmlInit()
        h = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(h)
        if isinstance(name, bytes):
            name = name.decode("utf-8")
        util = pynvml.nvmlDeviceGetUtilizationRates(h)
        mem = pynvml.nvmlDeviceGetMemoryInfo(h)
        temp = pynvml.nvmlDeviceGetTemperature(h, 0)

        return {
            "name": name,
            "gpu_percent": float(util.gpu),
            "vram_used_gb": round(mem.used / (1024 ** 3), 2),
            "vram_total_gb": round(mem.total / (1024 ** 3), 2),
            "vram_percent": round((mem.used / mem.total) * 100, 1) if mem.total else 0.0,
            "temp_c": float(temp),
        }
    except Exception:
        pass

    # Method 2: Pure ctypes direct DLL call
    if _init_nvml() and _nvml_lib:
        try:
            class _Util(ctypes.Structure):
                _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

            class _Memory(ctypes.Structure):
                _fields_ = [
                    ("total", ctypes.c_ulonglong),
                    ("free", ctypes.c_ulonglong),
                    ("used", ctypes.c_ulonglong),
                ]

            dev = ctypes.c_void_p()
            _nvml_lib.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev))

            name_buf = ctypes.create_string_buffer(64)
            _nvml_lib.nvmlDeviceGetName(dev, name_buf, 64)
            name = name_buf.value.decode("utf-8", errors="ignore")

            u = _Util()
            _nvml_lib.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(u))

            m = _Memory()
            _nvml_lib.nvmlDeviceGetMemoryInfo(dev, ctypes.byref(m))

            temp = ctypes.c_uint()
            _nvml_lib.nvmlDeviceGetTemperature(dev, 0, ctypes.byref(temp))

            return {
                "name": name or "NVIDIA GPU",
                "gpu_percent": float(u.gpu),
                "vram_used_gb": round(m.used / (1024 ** 3), 2),
                "vram_total_gb": round(m.total / (1024 ** 3), 2),
                "vram_percent": round((m.used / m.total) * 100, 1) if m.total else 0.0,
                "temp_c": float(temp.value),
            }
        except Exception:
            pass

    return {
        "name": None,
        "gpu_percent": None,
        "vram_used_gb": None,
        "vram_total_gb": None,
        "vram_percent": None,
        "temp_c": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CPU, STORAGE & POWER TELEMETRY
# ─────────────────────────────────────────────────────────────────────────────

def _get_cpu_temp() -> float:
    """Retrieves CPU temperature in Celsius without external CLI subprocesses."""
    try:
        temps = psutil.sensors_temperatures()
        for name in [
            "coretemp", "k10temp", "cpu_thermal", "acpitz",
            "cpu-thermal", "zenpower", "it8688",
        ]:
            if name in temps and temps[name]:
                return temps[name][0].current
        for entries in temps.values():
            if entries:
                return entries[0].current
    except Exception:
        pass

    if _OS == "Windows":
        try:
            import wmi  # type: ignore
            w = wmi.WMI(namespace="root/wmi")
            tz = w.MSAcpi_ThermalZoneTemperature()
            if tz:
                return (tz[0].CurrentTemperature / 10.0) - 273.15
        except Exception:
            pass

    return -1.0


def _get_battery_status() -> dict:
    """Checks power source, percentage, and time remaining."""
    try:
        battery = psutil.sensors_battery()
        if battery:
            return {
                "percent": round(battery.percent, 1),
                "power_plugged": battery.power_plugged,
                "secsleft": battery.secsleft,
            }
    except Exception:
        pass
    return {"percent": None, "power_plugged": None, "secsleft": None}


def _get_primary_disk_usage() -> dict:
    """Inspects root/C: partition capacity and free storage."""
    try:
        root_path = "C:\\" if _OS == "Windows" else "/"
        usage = psutil.disk_usage(root_path)
        return {
            "total_gb": round(usage.total / (1024 ** 3), 1),
            "used_gb": round(usage.used / (1024 ** 3), 1),
            "free_gb": round(usage.free / (1024 ** 3), 1),
            "percent": round(usage.percent, 1),
            "mount": root_path,
        }
    except Exception:
        return {"total_gb": None, "used_gb": None, "free_gb": None, "percent": None, "mount": "N/A"}


# ─────────────────────────────────────────────────────────────────────────────
# ROOT-CAUSE PROCESS INSPECTION & GOVERNANCE
# ─────────────────────────────────────────────────────────────────────────────

def _get_top_processes(limit: int = 5) -> list[dict]:
    """Identifies the heaviest resource-consuming applications."""
    procs = []
    current_pid = os.getpid()

    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "memory_info"]):
        try:
            info = p.info
            if not info["name"] or info["pid"] == current_pid:
                continue

            mem_mb = round((info["memory_info"].rss / (1024 ** 2)), 1) if info.get("memory_info") else 0.0
            procs.append({
                "pid": info["pid"],
                "name": info["name"],
                "cpu_percent": round(info.get("cpu_percent") or 0.0, 1),
                "memory_mb": mem_mb,
                "memory_percent": round(info.get("memory_percent") or 0.0, 1),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort primarily by CPU, secondarily by Memory
    procs.sort(key=lambda x: (x["cpu_percent"], x["memory_mb"]), reverse=True)
    return procs[:limit]


def _kill_process(target: str) -> str:
    """Safely terminates a rogue or hung process by name or PID."""
    target_clean = str(target).strip()
    if not target_clean:
        return "Please specify a process name or PID to terminate, sir."

    # Shield critical system processes and Nexus AI itself
    protected = {
        "explorer.exe", "system", "csrss.exe", "smss.exe", "lsass.exe",
        "services.exe", "svchost.exe", "winlogon.exe", "python.exe",
        "python", "systemd", "kernel", "launchd"
    }

    current_pid = os.getpid()
    killed = []

    # Case 1: PID target
    if target_clean.isdigit():
        pid = int(target_clean)
        if pid == current_pid:
            return "Action blocked: I cannot terminate my own core runtime process, sir."
        try:
            proc = psutil.Process(pid)
            pname = proc.name()
            if pname.lower() in protected:
                return f"Action blocked: '{pname}' is a protected system process."
            proc.terminate()
            return f"Process '{pname}' (PID {pid}) terminated successfully."
        except psutil.NoSuchProcess:
            return f"No active process found with PID {pid}."
        except psutil.AccessDenied:
            return f"Access denied: Administrator privileges required to terminate PID {pid}."

    # Case 2: Process Name target
    q = target_clean.lower()
    if not q.endswith(".exe") and _OS == "Windows":
        q_alt = f"{q}.exe"
    else:
        q_alt = q

    if q in protected or q_alt in protected:
        return f"Action blocked: '{target_clean}' is a protected operating system process."

    for p in psutil.process_iter(["pid", "name"]):
        try:
            pname = p.info["name"].lower()
            if p.info["pid"] == current_pid:
                continue
            if q == pname or q_alt == pname or q in pname:
                p.terminate()
                killed.append(f"{p.info['name']} (PID {p.info['pid']})")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if killed:
        return f"Terminated {len(killed)} process(es): {', '.join(killed)}."
    return f"No running processes matching '{target_clean}' were found, sir."


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM SNAPSHOT & FORMATTER
# ─────────────────────────────────────────────────────────────────────────────

def get_system_status() -> dict:
    """Comprehensive snapshot of hardware vitals for telemetry logging."""
    cpu = psutil.cpu_percent(interval=0.15)
    cpu_cores = psutil.cpu_count(logical=True)
    cpu_freq = psutil.cpu_freq()
    ram = psutil.virtual_memory()
    temp = _get_cpu_temp()
    gpu_data = _get_gpu_telemetry()
    disk = _get_primary_disk_usage()
    batt = _get_battery_status()

    boot_time = psutil.boot_time()
    uptime_secs = time.time() - boot_time
    uptime_h = int(uptime_secs // 3600)
    uptime_m = int((uptime_secs % 3600) // 60)

    return {
        "cpu_percent": round(cpu, 1),
        "cpu_cores": cpu_cores,
        "cpu_freq_ghz": round(cpu_freq.current / 1000, 2) if cpu_freq else None,
        "cpu_temp_c": round(temp, 1) if temp > 0 else None,
        "ram_percent": round(ram.percent, 1),
        "ram_used_gb": round(ram.used / (1024 ** 3), 1),
        "ram_total_gb": round(ram.total / (1024 ** 3), 1),
        "gpu": gpu_data,
        "disk": disk,
        "battery": batt,
        "uptime": f"{uptime_h}h {uptime_m}m",
        "process_count": len(psutil.pids()),
    }


def _format_status_report(snap: dict) -> tuple[str, str, list]:
    """Produces detailed Markdown for the UI HUD and a concise spoken voice lead."""
    gpu = snap["gpu"]
    disk = snap["disk"]
    batt = snap["battery"]

    lines = [
        f"**System Vitals Telemetry ({_OS})**",
        f"• **CPU Load:** {snap['cpu_percent']}% ({snap['cpu_cores']} logical cores" +
        (f" @ {snap['cpu_freq_ghz']} GHz" if snap['cpu_freq_ghz'] else "") +
        (f", {snap['cpu_temp_c']}°C" if snap['cpu_temp_c'] else "") + ")",
        f"• **RAM Memory:** {snap['ram_used_gb']} / {snap['ram_total_gb']} GB ({snap['ram_percent']}%)",
    ]

    hud_items = [
        {"title": f"CPU Utilization: {snap['cpu_percent']}%", "snippet": f"Cores: {snap['cpu_cores']} | Temp: {snap['cpu_temp_c'] or 'N/A'}°C", "url": ""},
        {"title": f"RAM Utilization: {snap['ram_percent']}%", "snippet": f"{snap['ram_used_gb']} GB used of {snap['ram_total_gb']} GB total", "url": ""},
    ]

    if gpu.get("name"):
        lines.append(
            f"• **GPU:** {gpu['name']} — {gpu['gpu_percent']}% load" +
            (f", {gpu['temp_c']}°C" if gpu.get("temp_c") is not None else "") +
            (f" (VRAM: {gpu['vram_used_gb']} / {gpu['vram_total_gb']} GB)" if gpu.get("vram_used_gb") is not None else "")
        )
        hud_items.append({
            "title": f"GPU: {gpu['name']} ({gpu['gpu_percent']}%)",
            "snippet": f"Temp: {gpu.get('temp_c')}°C | VRAM: {gpu.get('vram_used_gb')}/{gpu.get('vram_total_gb')} GB",
            "url": ""
        })

    if disk.get("total_gb"):
        lines.append(f"• **Primary Disk ({disk['mount']}):** {disk['free_gb']} GB free of {disk['total_gb']} GB ({disk['percent']}% used)")
        hud_items.append({
            "title": f"Storage ({disk['mount']}): {disk['free_gb']} GB Free",
            "snippet": f"Total: {disk['total_gb']} GB | Usage: {disk['percent']}%",
            "url": ""
        })

    if batt.get("percent") is not None:
        charging_str = "Plugged in / Charging" if batt["power_plugged"] else "On Battery"
        lines.append(f"• **Battery:** {batt['percent']}% ({charging_str})")

    lines.append(f"• **System Uptime:** {snap['uptime']} ({snap['process_count']} active processes)")

    detailed_md = "\n".join(lines)

    # Conversational 2-sentence spoken voice hook
    spoken = (
        f"Your system is running smoothly, sir. CPU is at {snap['cpu_percent']} percent, "
        f"and RAM is at {snap['ram_percent']} percent."
    )
    if snap["cpu_percent"] > 80:
        spoken = f"Warning, sir: CPU utilization is elevated at {snap['cpu_percent']} percent. RAM is at {snap['ram_percent']} percent."
    elif gpu.get("gpu_percent") is not None and gpu["gpu_percent"] > 85:
        spoken = f"Your GPU load is elevated at {gpu['gpu_percent']} percent. Overall system metrics are on your HUD, sir."

    return detailed_md, spoken, hud_items


# ─────────────────────────────────────────────────────────────────────────────
# STATEFUL BACKGROUND MONITOR (BACKWARDS COMPATIBILITY)
# ─────────────────────────────────────────────────────────────────────────────

class SystemMonitor:
    """
    Stateful background daemon monitor with cooldown protection against voice spamming.
    """

    def __init__(self, thresholds: dict | None = None):
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._last_alert: dict[str, float] = {}
        self._cpu_streak = 0

    def _can_alert(self, key: str) -> bool:
        return (time.monotonic() - self._last_alert.get(key, 0)) > _COOLDOWN

    def _record(self, key: str):
        self._last_alert[key] = time.monotonic()

    def check(self) -> str | None:
        try:
            snap = get_system_status()
            cpu = snap["cpu_percent"]
            ram = snap["ram_percent"]
            temp = snap["cpu_temp_c"] or -1.0
            gpu_data = snap["gpu"]
            gpu_load = gpu_data.get("gpu_percent") if gpu_data.get("gpu_percent") is not None else -1.0
        except Exception:
            return None

        alerts: list[str] = []

        if cpu >= self.thresholds["cpu"]:
            self._cpu_streak += 1
            if self._cpu_streak >= _CPU_STREAK and self._can_alert("cpu"):
                top_proc = _get_top_processes(limit=1)
                culprit = f" Primarily driven by {top_proc[0]['name']}." if top_proc else ""
                alerts.append(
                    f"[SYSTEM_ALERT] CPU load is critically high at {cpu:.0f}% for several seconds.{culprit} "
                    "Warn the user concisely."
                )
                self._record("cpu")
                self._cpu_streak = 0
        else:
            self._cpu_streak = 0

        if ram >= self.thresholds["ram"] and self._can_alert("ram"):
            top_mem = _get_top_processes(limit=1)
            culprit = f" Top memory consumer is {top_mem[0]['name']} ({top_mem[0]['memory_mb']} MB)." if top_mem else ""
            alerts.append(
                f"[SYSTEM_ALERT] RAM is at {ram:.0f}% — nearly exhausted.{culprit} "
                "Warn the user concisely."
            )
            self._record("ram")

        if temp > 0 and temp >= self.thresholds["temp"] and self._can_alert("temp"):
            alerts.append(
                f"[SYSTEM_ALERT] CPU temperature has reached {temp:.0f}°C, exceeding safe thermal limits. "
                "Advise cooling down the machine."
            )
            self._record("temp")

        if gpu_load >= 0 and gpu_load >= self.thresholds["gpu"] and self._can_alert("gpu"):
            alerts.append(
                f"[SYSTEM_ALERT] GPU load is peaked at {gpu_load:.0f}%. Inform the user."
            )
            self._record("gpu")

        return " ".join(alerts) if alerts else None


# ─────────────────────────────────────────────────────────────────────────────
# NATURAL INTENT ROUTER
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_system_intent(params: dict) -> tuple[str, dict]:
    """Disambiguates conversational requests for hardware vitals."""
    action = params.get("action", "").lower().strip()
    query = (action + " " + params.get("query", "") + " " + params.get("task", "")).lower().strip()

    # Process Governance
    if any(k in query for k in ["kill process", "terminate", "close app", "kill app", "end task", "kill heaviest"]):
        target = params.get("target") or params.get("process") or params.get("app", "")
        if not target:
            # Extract target from query
            m = re.search(r"(?:kill|terminate|end|close)\s+(?:process\s+|app\s+)?([a-zA-Z0-9_\-\.]+)", query)
            if m and m.group(1) not in ["process", "app", "task"]:
                target = m.group(1).strip()
        params["target"] = target
        return "kill_process", params

    # Root Cause Inspection
    if any(k in query for k in [
        "top process", "what is using ram", "what is using cpu",
        "why is pc slow", "heaviest process", "resource hog", "task manager"
    ]):
        return "top_processes", params

    # GPU Inspection
    if any(k in query for k in ["gpu", "graphics card", "vram", "gpu temp"]):
        return "gpu_status", params

    # Battery
    if any(k in query for k in ["battery", "power status", "charging", "charger"]):
        return "battery", params

    # Storage
    if any(k in query for k in ["disk space", "storage", "hard drive", "c drive", "free space"]):
        return "disk_status", params

    return action or "status", params


# ─────────────────────────────────────────────────────────────────────────────
# ACTION HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

def _handle_top_processes(params: dict, player, speak) -> str:
    procs = _get_top_processes(limit=5)
    if not procs:
        return "Could not retrieve process statistics at this time."

    lines = ["**Top Resource-Consuming Applications:**"]
    hud_items = []
    for i, p in enumerate(procs, 1):
        line = f"{i}. **{p['name']}** (PID {p['pid']}) — CPU: `{p['cpu_percent']}%` | RAM: `{p['memory_mb']} MB`"
        lines.append(line)
        hud_items.append({
            "title": f"#{i} {p['name']} (PID {p['pid']})",
            "snippet": f"CPU: {p['cpu_percent']}% | Memory: {p['memory_mb']} MB ({p['memory_percent']}%)",
            "url": ""
        })

    md = "\n".join(lines)
    _push_to_ui_hud(title="Top Resource Consumers", content=md, mode=3, items=hud_items)

    if speak:
        top1 = procs[0]
        spoken = f"The heaviest application right now is {top1['name']}, using {top1['cpu_percent']} percent CPU and {top1['memory_mb']} megabytes of RAM."
        speak(spoken)

    return md


def _handle_gpu_status(params: dict, player, speak) -> str:
    gpu = _get_gpu_telemetry()
    if not gpu.get("name"):
        msg = "No dedicated NVIDIA GPU telemetry detected on this system."
        _push_to_ui_hud(title="GPU Telemetry", content=msg, mode=3)
        return msg

    lines = [
        f"**Graphics Card Telemetry ({gpu['name']})**",
        f"• **Core Utilization:** {gpu['gpu_percent']}%",
        f"• **Temperature:** {gpu['temp_c']}°C" if gpu.get("temp_c") is not None else "• Temperature: N/A",
        f"• **VRAM Allocation:** {gpu['vram_used_gb']} / {gpu['vram_total_gb']} GB ({gpu['vram_percent']}%)" if gpu.get("vram_used_gb") is not None else "• VRAM: N/A",
    ]
    md = "\n".join(lines)
    _push_to_ui_hud(title="GPU Telemetry", content=md, mode=3)

    if speak:
        spoken = f"Your {gpu['name']} is at {gpu['gpu_percent']} percent load"
        if gpu.get("temp_c"):
            spoken += f" and running at {gpu['temp_c']} degrees Celsius."
        else:
            spoken += "."
        speak(spoken)

    return md


def _handle_battery_status(params: dict, player, speak) -> str:
    batt = _get_battery_status()
    if batt.get("percent") is None:
        return "No battery detected (desktop workstation or AC power)."

    status_str = "Plugged in and charging" if batt["power_plugged"] else "Running on battery power"
    msg = f"Battery is at **{batt['percent']}%** ({status_str})."
    _push_to_ui_hud(title="Battery Status", content=msg, mode=3)

    if speak:
        speak(f"Your battery is at {batt['percent']} percent, {status_str.lower()}, sir.")

    return msg


def _handle_disk_status(params: dict, player, speak) -> str:
    disk = _get_primary_disk_usage()
    if not disk.get("total_gb"):
        return "Could not inspect drive storage."

    msg = (
        f"**Primary Storage ({disk['mount']})**\n"
        f"• **Free Space:** {disk['free_gb']} GB\n"
        f"• **Used Space:** {disk['used_gb']} GB of {disk['total_gb']} GB ({disk['percent']}%)"
    )
    _push_to_ui_hud(title="Storage Telemetry", content=msg, mode=3)

    if speak:
        speak(f"You have {disk['free_gb']} gigabytes free on drive {disk['mount']}, out of {disk['total_gb']} gigabytes total.")

    return msg


# ─────────────────────────────────────────────────────────────────────────────
# MAIN DISPATCH ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def system_monitor(
    parameters: dict = None,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """
    Central orchestration router for all hardware monitoring and process governance.
    Thread-safe, state-aware, and natural-intent compliant.
    """
    raw_params = parameters or {}
    resolved_action, clean_params = _normalize_system_intent(raw_params)

    if player:
        player.write_log(f"[SystemMonitor] Intent: {resolved_action}")
    print(f"[SystemMonitor] ▶️ Intent: '{resolved_action}' | Params: {clean_params}")

    try:
        # Full System Telemetry
        if resolved_action in ["status", "system_status", "overview"]:
            snap = get_system_status()
            detailed_md, spoken_lead, hud_items = _format_status_report(snap)
            _push_to_ui_hud(title="Hardware Telemetry", content=detailed_md, mode=3, items=hud_items)
            if speak:
                speak(spoken_lead)
            return detailed_md

        # Root Cause Process Inspection
        elif resolved_action in ["top_processes", "processes"]:
            return _handle_top_processes(clean_params, player, speak)

        # Process Governance
        elif resolved_action == "kill_process":
            target = clean_params.get("target")
            if not target:
                # If user said "kill the heaviest app", pick the top 1 consumer
                top = _get_top_processes(limit=1)
                if top:
                    target = str(top[0]["pid"])
            res = _kill_process(target)
            if speak:
                speak(res)
            return res

        # GPU Telemetry
        elif resolved_action in ["gpu_status", "gpu"]:
            return _handle_gpu_status(clean_params, player, speak)

        # Battery Status
        elif resolved_action in ["battery", "power"]:
            return _handle_battery_status(clean_params, player, speak)

        # Storage Status
        elif resolved_action in ["disk_status", "disk", "storage"]:
            return _handle_disk_status(clean_params, player, speak)

        # Fallback to standard status snapshot
        snap = get_system_status()
        detailed_md, spoken_lead, hud_items = _format_status_report(snap)
        _push_to_ui_hud(title="Hardware Telemetry", content=detailed_md, mode=3, items=hud_items)
        if speak:
            speak(spoken_lead)
        return detailed_md

    except Exception as e:
        print(f"[SystemMonitor] ❌ Execution exception: {e}")
        return f"System monitor error: {e}"