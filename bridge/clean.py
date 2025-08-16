from engine import CPU, Memory, Disk, ProcessManager

from datetime import datetime
from dataclasses import dataclass, field
from typing import (TypedDict, List, Dict, 
                    Optional, Literal, 
                    Tuple, Union, Callable,
                    Any)
from abc import ABC, abstractmethod
import time
from enum import Enum
import psutil
from parser import SimpleParse
parser = SimpleParse()
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
    
cpu = CPU()

ret = cpu_times(cpu.get_times, percpu=False)

ret = cpu_times(cpu.get_times_percent, percpu=True, interval=0.0)

ret = cpu_times(cpu.get_times_percent, percpu=True, interval=1.0)

def cpu_percent(interval: Optional[float] = None, 
            percpu: bool = False): 
    return parser.format_percent(list(cpu.get_percent(percpu=percpu, 
                                                 interval=interval)))
    
print(cpu_percent(percpu=True))

def get_stat():
    parts = cpu.get_stats()
    if parts is None: return None
    if hasattr(parts, "_asdict"):
        return parts._asdict()

print(get_stat())

def cpu_freq(percpu: bool = False):
    s = cpu.get_freq(percpu)
    
    def _test(v: Optional[float]):
        if v is None: return None
        v = float(v)
        return v if v > 0.0 else None
    def _map_one(f):
        if f is None: return {"current": None, "min_mhz": None, "max_mhz": None}
        d = f._asdict() if hasattr(f, "_asdict") else {}
        return {
            "current": _test(d.get("current")),
            "min_mhz": _test(d.get("min")),
            "max_mhz": _test(d.get("max")),
        }
    if s is None:
        mapped: Union[Dict[str, Optional[float]], List[Dict[str, Optional[float]]]] = {"current": None, "min_mhz": None, "max_mhz": None}
        avg = None
    elif percpu:
            mapped = [_map_one(x) for x in s]
            currents = [m["current"] for m in mapped if m["current"] is not None]
            avg = (sum(currents) / len(currents)) if currents else None
    else:
        mapped = _map_one(s)
        avg = mapped.get("current") if isinstance(mapped, dict) else None
        
    out: Dict[str, Union[bool, float, int, None, Dict[str, Optional[float]], List[Dict[str, Optional[float]]]]] = {
    "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
    "percpu": percpu,
    "logical_count": psutil.cpu_count(logical=True) or 0,
    "freq": mapped,
    }
    if percpu:
        out["freq_avg_mhz"] = avg
    return out
def getloadavg(logical_count:int):
    try:
        la1, la5, la15 = cpu.get_loadavg()
    except (AttributeError, OSError):
        return {
            "supported": False,
            "raw": None,               # {"1m":..., "5m":..., "15m":...}
            "per_core": None,          # raw/core_count
            "util_percent_est": None,  # min(100, per_core*100)
        }
    cores = max(1, int(logical_count) if logical_count else (psutil.cpu_count(True) or 1))
    raw = {"1m": float(la1), "5m": float(la5), "15m": float(la15)}
    per_core = {k: v / cores for k, v in raw.items()}
    util_est = {k: min(100.0, max(0.0, v * 100.0)) for k, v in per_core.items()}
    
    return {
        "supported": True,
        "raw": raw,
        "per_core": per_core,
        "util_percent_est": util_est,
    }
    