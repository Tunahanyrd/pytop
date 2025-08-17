from datetime import datetime
from dataclasses import dataclass, field
from typing import (
    TypedDict, List, Dict, Optional, Literal,
    Tuple, Union, Callable, Any,
)
from abc import ABC, abstractmethod
from enum import Enum
import time

import psutil

from engine import CPU, Memory, Disk, ProcessManager
from parser import SimpleParse


parser = SimpleParse()
cpu = CPU()

@dataclass
class CpuTimes:
    user: float
    nice: float
    system: float
    idle: float
    iowait: float
    irq: float
    softirq: float
    steal: float
    guest: float
    guest_nice: float


_EXPECTED_CPU_TIMES_KEYS = (
    "user", "system", "idle", "nice",
    "iowait", "irq", "softirq",
    "steal", "guest", "guest_nice",
)


def cpu_times(
    fonk: Callable[..., Any],
    *,
    percpu: bool = False,
    interval: Optional[float] = None
) -> Dict[str, Union[bool, float, int, Dict[str, float], List[Dict[str, float]]]]:
    """
    - percpu=False -> tek dict
    - percpu=True  -> dict listesi

    Dönüş:
    {
      "ts": <epoch>,
      "percpu": <bool>,
      "logical_count": <int>,
      "times": {..} veya [{..}, ...]
    }

    Not: cpu_times() interval kabul etmez; cpu_times_percent() kabul eder.
         Her iki fonksiyonla da çalışsın diye TypeError yakalıyoruz.
    """
    # fonksiyona güvenli çağrı: bazıları interval desteklemez
    try:
        raw = fonk(percpu=percpu, interval=interval)
    except TypeError:
        # Örn. psutil.cpu_times / senin CPU.get_times interval almaz
        raw = fonk(percpu=percpu)

    def _map_one(t) -> Dict[str, float]:
        d = t._asdict() if hasattr(t, "_asdict") else dict(getattr(t, "__dict__", {}))
        out: Dict[str, float] = {}
        for k in _EXPECTED_CPU_TIMES_KEYS:
            if k in d and d[k] is not None:
                out[k] = float(d[k])
        return out  # <-- return for'un DIŞINDA

    mapped = [_map_one(x) for x in raw] if percpu else _map_one(raw)

    return {
        "ts": time.time(),
        "percpu": percpu,
        "logical_count": psutil.cpu_count(logical=True) or 0,
        "times": mapped,
    }


def cpu_percent(
    interval: Optional[float] = None,
    percpu: bool = False
):
    return parser.format_percent(
        cpu.get_percent(percpu=percpu, interval=interval)
    )


def get_stat():
    parts = cpu.get_stats()
    if parts is None:
        return None
    if hasattr(parts, "_asdict"):
        return parts._asdict()


def cpu_freq(percpu: bool = False):
    s = cpu.get_freq(percpu)

    def _map_one(f):
        if f is None:
            return {"current": None, "min_mhz": None, "max_mhz": None}
        d = f._asdict() if hasattr(f, "_asdict") else {}
        return {
            "current": parser.format_freq(d.get("current")),
            "min_mhz": parser.format_freq(d.get("min")),
            "max_mhz": parser.format_freq(d.get("max"))
        }

    if s is None:
        mapped: Union[
            Dict[str, Optional[float]],
            List[Dict[str, Optional[float]]]
        ] = {"current": None, "min_mhz": None, "max_mhz": None}
        avg = None
    elif percpu:
        mapped = [_map_one(x) for x in s]
        currents = [m["current"] for m in mapped if m["current"] is not None]
        avg = (sum(currents) / len(currents)) if currents else None
    else:
        mapped = _map_one(s)
        avg = mapped.get("current") if isinstance(mapped, dict) else None

    out = {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "percpu": percpu,
        "logical_count": psutil.cpu_count(logical=True) or 0,
        "freq": mapped,
    }
    if percpu:
        out["freq_avg_mhz"] = avg
    return out


def getloadavg(logical_count: int):
    try:
        la1, la5, la15 = cpu.get_loadavg()
    except (AttributeError, OSError):
        return {
            "supported": False,
            "raw": None,               # {"1m":..., "5m":..., "15m":...}
            "per_core": None,          # raw/core_count
            "util_percent_est": None,  # min(100, per_core*100)
        }

    cores = max(
        1,
        int(logical_count) if logical_count else (psutil.cpu_count(True) or 1)
    )
    raw = {"1m": float(la1), "5m": float(la5), "15m": float(la15)}
    per_core = {k: v / cores for k, v in raw.items()}
    util_est = {k: min(100.0, max(0.0, v * 100.0)) for k, v in per_core.items()}

    return {
        "supported": True,
        "raw": raw,
        "per_core": per_core,
        "util_percent_est": util_est,
    }


disk = Disk()


def disk_io(perdisk: bool = False, nowrap: bool = False):
    d = disk.get_io_counters(perdisk, nowrap)

    def _fmt_entry(stats):
        s = stats._asdict() if hasattr(stats, "_asdict") else dict(stats)
        out = {}
        for k, v in s.items():
            if v is None:
                out[k] = None
                continue

            if k in ("read_bytes", "write_bytes"):
                out[k] = parser.format_bytes(v)
            elif k in ("read_time", "write_time", "busy_time"):
                out[k] = f"{int(v)} ms"
            else:
                out[k] = v
        return out

    if perdisk:
        return {name: _fmt_entry(stats) for name, stats in d.items()}

    return _fmt_entry(d)


def diskusage():
    order = ("total", "used", "free", "percent")
    d = disk.get_usage()
    out = {}
    for mount, stats in d.items():
        s = stats._asdict() if hasattr(stats, "_asdict") else dict(stats)
        pretty = {}
        
        for k in order:
            v = s[k]
            if k == "percent":
                pretty[k] = parser.format_percent(v, part="")
            else:
                pretty[k] = parser.format_bytes(v)

        out[mount] = pretty

    return out      

def getpart():
    d = disk.get_part()
    return [stats._asdict() for stats in d]

mem = Memory()

def getvirt():
    s = mem.get_virtual()
    if hasattr(s, "_asdict"):
        s =  s._asdict()
    out = {}
    
    for k, v in s.items():
        if k == "percent":
            out[k] = parser.format_percent(v, part="")
        else:
            out[k] = parser.format_bytes(v)
    return out
    
    
def getswap():
    s = mem.get_swap()
    if hasattr(s, "_asdict"):
        s = s._asdict()
    out = {}
    
    for k, v in s.items():
        if k == "percent":
            out[k] = parser.format_percent(v, part="")
        else:
            out[k] = parser.format_bytes(v)
    return out