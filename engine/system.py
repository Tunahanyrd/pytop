import psutil
import datetime
from typing import List

class System:
    def get_boot_time(self) -> str:
        bt = psutil.boot_time()
        return datetime.datetime.fromtimestamp(bt).isoformat()

    def get_users(self) -> List[psutil._common.suser]:
        return psutil.users()
