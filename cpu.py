# cpu.py
import psutil
from typing import List, Union, Optional
import psutil._common

class CPU:
    def __init__(self):
        psutil.cpu_percent()
        psutil.cpu_percent(percpu=True)

    def get_times(self, percpu: bool = False) -> Union[psutil._common.scputimes, List[psutil._common.scputimes]]:
        return psutil.cpu_times(percpu=percpu)

    def get_times_percent(self, percpu: bool = False, interval: Optional[float] = None) -> Union[psutil._common.scputimes, List[psutil._common.scputimes]]:
        return psutil.cpu_times_percent(interval=interval, percpu=percpu)

    def get_percent(self, interval: Optional[float] = None, percpu: bool = False) -> Union[float, List[float]]:
        return psutil.cpu_percent(interval=interval, percpu=percpu)

    def get_count(self, logical: bool = True) -> int:
        return psutil.cpu_count(logical=logical)

    def get_stats(self) -> psutil._common.scpustats:
        return psutil.cpu_stats()

    def get_freq(self, percpu: bool = False) -> Union[psutil._common.shwtemp, List[psutil._common.shwtemp]]:
        return psutil.cpu_freq(percpu=percpu)

    def get_loadavg(self) -> Optional[tuple[float, float, float]]:
        try:
            return psutil.getloadavg()
        except (AttributeError, OSError):
            return None
