import psutil
from typing import Dict, Any

class Network:
    def get_io_counters(self, pernic: bool = False, nowrap: bool = True) -> Dict[str, Any]:
        return psutil.net_io_counters(pernic=pernic, nowrap=nowrap)

    def get_connections(self, kind: str = "inet") -> list:
        # kind: 'tcp', 'udp', 'inet', 'all'
        return psutil.net_connections(kind=kind)

    def get_if_addrs(self) -> Dict[str, list]:
        return psutil.net_if_addrs()

    def get_if_stats(self) -> Dict[str, psutil._common.snicstats]:
        return psutil.net_if_stats()
