import psutil
from typing import Dict, Any, Optional

class Sensors:
    def get_temperatures(self) -> Optional[Dict[str, Any]]:
        try:
            return psutil.sensors_temperatures(fahrenheit=False)
        except Exception:
            return None

    def get_fans(self) -> Optional[Dict[str, Any]]:
        try:
            return psutil.sensors_fans()
        except Exception:
            return None

    def get_battery(self) -> Optional[psutil._common.sbattery]:
        try:
            return psutil.sensors_battery()
        except Exception:
            return None
