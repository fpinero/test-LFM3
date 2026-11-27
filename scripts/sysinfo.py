"""Utilidades de memoria y CPU para Linux y macOS, compartidas por los scripts.

- Linux: lee /proc (MemAvailable, VmRSS, /proc/cpuinfo).
- macOS: usa sysctl, vm_stat y ps, porque no existe /proc.
Todas las funciones devuelven None si no pueden obtener el dato.
"""
import os
import re
import subprocess
import sys

ES_MAC = sys.platform == "darwin"


def _run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return ""


def cpu_name():
    if ES_MAC:
        return _run(["sysctl", "-n", "machdep.cpu.brand_string"]).strip() or None
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except FileNotFoundError:
        pass
    return None


def ram_total_mb():
    if ES_MAC:
        out = _run(["sysctl", "-n", "hw.memsize"]).strip()
        return int(out) // 2**20 if out.isdigit() else None
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) // 1024
    except FileNotFoundError:
        pass
    return None


def mem_available_mb():
    """RAM disponible. En macOS es una aproximación: páginas libres + inactivas + especulativas."""
    if ES_MAC:
        out = _run(["vm_stat"])
        m = re.search(r"page size of (\d+) bytes", out)
        if not m:
            return None
        page = int(m.group(1))
        pages = 0
        for key in ("Pages free", "Pages inactive", "Pages speculative"):
            mm = re.search(rf"{key}:\s+(\d+)", out)
            if mm:
                pages += int(mm.group(1))
        return pages * page // 2**20
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except FileNotFoundError:
        pass
    return None


def rss_mb(patrones):
    """Suma la RSS (MB) de los procesos cuyo comando contiene alguno de los patrones."""
    total_kb = 0
    if ES_MAC or not os.path.isdir("/proc"):
        for line in _run(["ps", "-axo", "rss=,command="]).splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2 and parts[0].isdigit() and any(p in parts[1] for p in patrones):
                total_kb += int(parts[0])
    else:
        for pid in filter(str.isdigit, os.listdir("/proc")):
            try:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmd = f.read().replace(b"\0", b" ").decode(errors="ignore")
                if not any(p in cmd for p in patrones):
                    continue
                with open(f"/proc/{pid}/status") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            total_kb += int(line.split()[1])
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue
    return total_kb // 1024 if total_kb else None
