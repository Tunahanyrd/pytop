#memory.py
import psutil
from typing import List, Union, Optional
import psutil._common
import psutil._pslinux

class Memory:
    def get_virtual(self) -> psutil._pslinux.svmem:
        return psutil.virtual_memory()

    def get_swap(self) -> psutil._common.sswap:
        return psutil.swap_memory()