#disk.py
import psutil
from typing import List, Dict, Optional
import psutil._common

class Disk:
    def __init__(self):
        self._partition = psutil.disk_partitions(all=False)
    
    def get_part(self) -> List[psutil._common.sdiskpart]:
        return self._partition
    
    def get_usage(self, path: str) -> Optional[psutil._common.sdiskusage]:
        try:
            return psutil.disk_usage(path)
        except FileNotFoundError:
            return None
    
    def get_usage(self) -> Dict[str, psutil._common.sdiskusage]:
        usage_info = {}
        for part in self._partition:
            try:
                usage_info[part.mountpoint] = psutil.disk_usage(part.mountpoint)
            except PermissionError:
                continue
        return usage_info
    
    def get_io_counters(self, perdisk: bool=False, nowrap:bool=False) -> Optional[Dict[str, psutil._common.sdiskio]]:
        return psutil.disk_io_counters(perdisk=perdisk)
                