# psutil-bridge

Clean, normalized API layer built on top of [psutil](https://github.com/giampaolo/psutil).  
No more digging through raw structs — this package gives you **ready-to-use functions** for CPU, Memory, Disk, Processes, Network, Sensors, System Info, and even Windows services.

---

##  Features
- Unified high-level API: no need to remember `psutil.cpu_times()._asdict()`, just call `cpu_times()`.
- Human-readable formatting (bytes → GiB, percentages formatted, safe handling of `None`).
- Cross-platform: gracefully degrades if a feature is unsupported (e.g. sensors).
- Organized into:
  - `engine/`: low-level psutil wrappers
  - `bridge/clean.py`: normalized API functions
  - `bridge/__init__.py`: re-exports for clean imports

---

##  Quick Start
```bash
git clone https://github.com/<yourname>/psutil-bridge.git
cd psutil-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
````

Example:

```python
from bridge import (
    cpu_percent, diskusage, net_io, sensors_temperatures,
    boot_info, process_details
)

print(cpu_percent(percpu=True))
print(diskusage())
print(net_io(pernic=True))
print(sensors_temperatures())
print(boot_info())
print(process_details(1))
```

---

##  API Surface

### CPU

* `cpu_times`
* `cpu_percent`
* `cpu_freq`
* `get_stat`
* `getloadavg`

### Memory

* `getvirt`
* `getswap`

### Disk

* `diskusage`
* `disk_io`
* `getpart`

### Network

* `net_io` (with throughput rates)
* `net_if_addrs`
* `net_if_stats`
* `net_connections`

### Sensors

* `sensors_temperatures`
* `sensors_fans`
* `sensors_battery`

### System

* `boot_info`
* `logged_in_users`

### Process

* `process_details(pid)` → memory\_full\_info, io\_counters, open\_files, connections, num\_fds, threads

### Windows

* `win_services_list`
* `win_service_get`

---

##  Roadmap

* [ ] Add TUI (Textual / Rich / Urwid / Curses) frontend
* [ ] CLI demo (`python -m bridge`)
* [ ] Packaging (pipx, Arch AUR, Flatpak)

---

##  Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).