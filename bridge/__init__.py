# bridge/__init__.py
"""
Yüksek seviye, formatlanmış (clean) API:
- CPU / Memory / Disk
- Network
- Sensors
- System info
- Process deep dive
- Windows servisleri

Kullanım:
    from bridge import (
        cpu_times, cpu_percent, get_stat, cpu_freq, getloadavg,
        disk_io, diskusage, getpart,
        getvirt, getswap,
        net_io, net_if_addrs, net_if_stats, net_connections,
        sensors_temperatures, sensors_fans, sensors_battery,
        boot_info, logged_in_users,
        process_details,
        win_services_list, win_service_get,
        SimpleParse, make_default_config,
    )
"""

from .clean import (
    # CPU
    cpu_times, cpu_percent, get_stat, cpu_freq, getloadavg,
    # Disk
    disk_io, diskusage, getpart,
    # Memory
    getvirt, getswap,
    # Network
    net_io, net_if_addrs, net_if_stats, net_connections,
    # Sensors
    sensors_temperatures, sensors_fans, sensors_battery,
    # System
    boot_info, logged_in_users,
    # Process deep dive
    process_details,
    # Windows services (destek yoksa supported=False döner)
    win_services_list, win_service_get,
)


from .parser import SimpleParse, make_default_config, SeverityLevel, SeverityProfile, ParserConfig

__all__ = [
    # CPU
    "cpu_times", "cpu_percent", "get_stat", "cpu_freq", "getloadavg",
    # Disk
    "disk_io", "diskusage", "getpart",
    # Memory
    "getvirt", "getswap",
    # Network
    "net_io", "net_if_addrs", "net_if_stats", "net_connections",
    # Sensors
    "sensors_temperatures", "sensors_fans", "sensors_battery",
    # System
    "boot_info", "logged_in_users",
    # Process deep dive
    "process_details",
    # Windows services
    "win_services_list", "win_service_get",
    # Parser public API
    "SimpleParse", "make_default_config", "SeverityLevel", "SeverityProfile", "ParserConfig",
]
