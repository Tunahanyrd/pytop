from datetime import datetime
from typing import List, Dict, Optional, Union, Callable, Any

import time
import psutil

from engine import CPU, Memory, Disk, ProcessManager, Network, Sensors, System, ProcessDetail
try:
    from engine import WinServices
except Exception:
    WinServices = None

from .parser import SimpleParse

parser = SimpleParse()

cpu = CPU()
disk = Disk()
mem = Memory()
net = Network()
sensors = Sensors()
sysinfo = System()
win = WinServices() if WinServices is not None else None

_EXPECTED_CPU_TIMES_KEYS = (
    "user", "system", "idle", "nice",
    "iowait", "irq", "softirq",
    "steal", "guest", "guest_nice",
)


def cpu_times(
    fn: Callable[..., Any],
    *,
    percpu: bool = False,
    interval: Optional[float] = None
) -> Dict[str, Union[bool, float, int, Dict[str, float], List[Dict[str, float]]]]:
    """
    Normalize psutil cpu_times / cpu_times_percent output into dicts.
    """
    try:
        raw = fn(percpu=percpu, interval=interval)
    except TypeError:
        raw = fn(percpu=percpu)

    def _map_one(t) -> Dict[str, float]:
        d = t._asdict() if hasattr(t, "_asdict") else dict(getattr(t, "__dict__", {}))
        out: Dict[str, float] = {}
        for k in _EXPECTED_CPU_TIMES_KEYS:
            if k in d and d[k] is not None:
                out[k] = float(d[k])
        return out

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
        cur = d.get("current")
        mn = d.get("min")
        mx = d.get("max")
        return {
            "current": parser.format_freq(cur) if cur is not None else None,
            "min_mhz": parser.format_freq(mn) if mn is not None else None,
            "max_mhz": parser.format_freq(mx) if mx is not None else None,
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
            "raw": None,
            "per_core": None,
            "util_percent_est": None,
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


def getvirt():
    s = mem.get_virtual()
    if hasattr(s, "_asdict"):
        s = s._asdict()
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


def _fmt_bps(x: float) -> str:
    return f"{parser.format_bytes(int(x))}/s"


def _addr_family_name(fam) -> str:
    s = str(fam)
    return s.split(".")[-1]


def net_io(pernic: bool = False, nowrap: bool = True):
    """
    psutil.net_io_counters wrapper with simple rate calculation.
    """
    counters = net.get_io_counters(pernic=pernic, nowrap=nowrap)
    now = time.time()

    def _one(name: str, c) -> dict:
        d = c._asdict() if hasattr(c, "_asdict") else dict(c)
        out = {
            "bytes_sent": parser.format_bytes(d.get("bytes_sent", 0)),
            "bytes_recv": parser.format_bytes(d.get("bytes_recv", 0)),
            "packets_sent": d.get("packets_sent"),
            "packets_recv": d.get("packets_recv"),
            "errin": d.get("errin"),
            "errout": d.get("errout"),
            "dropin": d.get("dropin"),
            "dropout": d.get("dropout"),
        }

        prev = parser.state.last_io_bytes.get(name)
        if prev and parser.state.last_ts:
            dt = max(1e-3, now - parser.state.last_ts)
            prev_recv, prev_sent = prev
            rrate = max(0.0, (d.get("bytes_recv", 0) - prev_recv) / dt)
            srate = max(0.0, (d.get("bytes_sent", 0) - prev_sent) / dt)
            out["recv_rate"] = _fmt_bps(rrate)
            out["sent_rate"] = _fmt_bps(srate)
        else:
            out["recv_rate"] = None
            out["sent_rate"] = None

        parser.state.last_io_bytes[name] = (d.get("bytes_recv", 0), d.get("bytes_sent", 0))
        return out

    if pernic:
        out = {name: _one(name, c) for name, c in counters.items()}
    else:
        out = _one("__ALL__", counters)

    parser.state.last_ts = now
    return {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "pernic": pernic,
        "io": out,
    }


def net_if_addrs():
    addrs = net.get_if_addrs()

    def _map(a):
        d = a._asdict() if hasattr(a, "_asdict") else dict(a)
        fam = d.get("family")
        fam = _addr_family_name(fam) if fam is not None else None
        return {
            "family": fam,
            "address": d.get("address"),
            "netmask": d.get("netmask"),
            "broadcast": d.get("broadcast"),
            "ptp": d.get("ptp"),
        }

    return {name: [_map(a) for a in lst] for name, lst in addrs.items()}


def net_if_stats():
    stats = net.get_if_stats()

    def _duplex_name(val):
        try:
            import psutil as _p
            mapping = {
                getattr(_p, "NIC_DUPLEX_FULL", 2): "full",
                getattr(_p, "NIC_DUPLEX_HALF", 1): "half",
                getattr(_p, "NIC_DUPLEX_UNKNOWN", 0): "unknown",
            }
            return mapping.get(val, str(val))
        except Exception:
            return str(val)

    out = {}
    for name, s in stats.items():
        d = s._asdict() if hasattr(s, "_asdict") else dict(s)
        out[name] = {
            "isup": d.get("isup"),
            "duplex": _duplex_name(d.get("duplex")),
            "speed_mbps": d.get("speed"),
            "mtu": d.get("mtu"),
        }
    return out


def net_connections(kind: str = "inet", limit: int | None = 100):
    conns = net.get_connections(kind=kind)

    def _addr_tuple(t):
        if not t:
            return None
        try:
            ip, port = t
            return {"ip": ip, "port": port}
        except Exception:
            return {"raw": str(t)}

    rows = []
    for c in conns[: (None if limit is None else limit)]:
        d = c._asdict() if hasattr(c, "_asdict") else dict(c)
        rows.append({
            "fd": d.get("fd"),
            "family": _addr_family_name(d.get("family")),
            "type": str(d.get("type")).split(".")[-1] if d.get("type") else None,
            "laddr": _addr_tuple(d.get("laddr")),
            "raddr": _addr_tuple(d.get("raddr")),
            "status": d.get("status"),
            "pid": d.get("pid"),
        })
    return rows


def sensors_temperatures():
    temps = sensors.get_temperatures()
    if not temps:
        return {"supported": False, "temperatures": None}

    def _fmt_t(v):
        try:
            return f"{float(v):.1f} °C"
        except Exception:
            return None

    out = {}
    for chip, entries in temps.items():
        arr = []
        for e in entries:
            d = e._asdict() if hasattr(e, "_asdict") else dict(e)
            arr.append({
                "label": d.get("label") or "",
                "current": _fmt_t(d.get("current")),
                "high": _fmt_t(d.get("high")),
                "critical": _fmt_t(d.get("critical")),
            })
        out[chip] = arr
    return {"supported": True, "temperatures": out}


def sensors_fans():
    fans = sensors.get_fans()
    if not fans:
        return {"supported": False, "fans": None}
    out = {}
    for chip, entries in fans.items():
        arr = []
        for e in entries:
            d = e._asdict() if hasattr(e, "_asdict") else dict(e)
            rpm = d.get("current")
            arr.append({"label": d.get("label") or "", "rpm": (int(rpm) if rpm is not None else None)})
        out[chip] = arr
    return {"supported": True, "fans": out}


def sensors_battery():
    b = sensors.get_battery()
    if not b:
        return {"supported": False, "battery": None}
    d = b._asdict() if hasattr(b, "_asdict") else dict(b)

    def _fmt_secs(sec):
        if sec is None:
            return None
        try:
            sec = int(sec)
            if sec < 0:
                return None
            h = sec // 3600
            m = (sec % 3600) // 60
            s = sec % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        except Exception:
            return None

    return {
        "supported": True,
        "battery": {
            "percent": parser.format_percent(d.get("percent", 0.0), part=""),
            "secs_left": _fmt_secs(d.get("secsleft")),
            "power_plugged": d.get("power_plugged"),
        }
    }


def boot_info():
    bt_iso = sysinfo.get_boot_time()
    try:
        bt_epoch = psutil.boot_time()
        up_sec = max(0, int(time.time() - bt_epoch))
        h = up_sec // 3600
        m = (up_sec % 3600) // 60
        s = up_sec % 60
        uptime = f"{h:02d}:{m:02d}:{s:02d}"
    except Exception:
        uptime = None
    return {"boot_time": bt_iso, "uptime": uptime}


def logged_in_users():
    us = sysinfo.get_users()
    rows = []
    for u in us:
        d = u._asdict() if hasattr(u, "_asdict") else dict(u)
        rows.append({
            "name": d.get("name"),
            "terminal": d.get("terminal"),
            "host": d.get("host"),
            "started": parser.format_ctime(d.get("started")),
            "pid": d.get("pid"),
        })
    return rows


def process_details(pid: int, *, sample_conn: int = 20, shorten_path_len: int = 64):
    try:
        p = ProcessDetail(pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        return {"error": str(e), "pid": pid}

    out = {"pid": pid}

    try:
        m = p.memory_full_info()
        md = m._asdict() if hasattr(m, "_asdict") else dict(m)
        mem_fmt = {k: parser.format_bytes(v or 0) for k, v in md.items()}
        out["memory"] = mem_fmt
    except Exception as e:
        out["memory"] = {"error": str(e)}

    try:
        io = p.io_counters()
        if io is not None:
            d = io._asdict() if hasattr(io, "_asdict") else dict(io)
            out["io"] = {
                "read_count": d.get("read_count"),
                "write_count": d.get("write_count"),
                "read_bytes": parser.format_bytes(d.get("read_bytes", 0)),
                "write_bytes": parser.format_bytes(d.get("write_bytes", 0)),
            }
        else:
            out["io"] = None
    except Exception as e:
        out["io"] = {"error": str(e)}

    try:
        files = p.open_files()
        out["open_files"] = [
            parser.shorten_path(getattr(f, "path", str(f)), max_len=shorten_path_len)
            for f in files
        ]
    except Exception as e:
        out["open_files"] = {"error": str(e)}

    try:
        conns = p.connections()
        status_counts = {}
        sample = []
        for c in conns[:sample_conn]:
            d = c._asdict() if hasattr(c, "_asdict") else dict(c)
            st = d.get("status")
            status_counts[st] = status_counts.get(st, 0) + 1

            def _addr(t):
                return None if not t else {"ip": t[0], "port": t[1]}

            sample.append({
                "laddr": _addr(d.get("laddr")),
                "raddr": _addr(d.get("raddr")),
                "status": st,
                "fd": d.get("fd"),
            })
        out["connections"] = {
            "total": len(conns),
            "by_status": status_counts,
            "sample": sample,
        }
    except Exception as e:
        out["connections"] = {"error": str(e)}

    try:
        out["num_fds"] = p.num_fds()
    except Exception:
        out["num_fds"] = None

    try:
        ths = p.threads()
        out["threads"] = {
            "count": len(ths),
            "sample": [{"id": t.id, "user_time": t.user_time, "system_time": t.system_time} for t in ths[:10]],
        }
    except Exception as e:
        out["threads"] = {"error": str(e)}

    return out


def win_services_list():
    if not win:
        return {"supported": False, "services": None}
    try:
        return [
            {
                "name": s.name(),
                "display_name": s.display_name(),
                "status": s.status(),
                "binpath": s.binpath(),
            }
            for s in win.list_services()
        ]
    except Exception as e:
        return {"supported": False, "error": str(e)}


def win_service_get(name: str):
    if not win:
        return {"supported": False, "service": None}
    try:
        s = win.get_service(name)
        return {
            "name": s.name(),
            "display_name": s.display_name(),
            "status": s.status(),
            "binpath": s.binpath(),
            "start_type": s.start_type(),
        }
    except Exception as e:
        return {"supported": False, "error": str(e)}


if __name__ == "__main__":
    pm = ProcessManager(interval=1.0)
    pm.start()
    rows = pm(
        sort_by="cpu_percent",
        limit=15,
        fields=[
            "pid", "username", "cpu_percent", "memory_percent",
            "name", "ppid", "status", "nice", "num_threads",
            "create_time", "cmdline", "rss", "vms", "read_bytes",
            "write_bytes", "cpu_user", "cpu_system", "exe"
        ],
        formatters=ProcessManager.default_formatters(parser)
    )
    for r in rows:
        print(r)
    pm.stop()
