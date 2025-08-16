#memory.py
import psutil
from typing import List, Union, Optional
import psutil._common
import psutil._pslinux

class Memory:
    def __init__(self):
        self._vmem = psutil.virtual_memory()
        self._swap = psutil.swap_memory()

    def get_virtual(self) -> psutil._pslinux.svmem:
        return self._vmem

    def get_swap(self) -> psutil._common.sswap:
        return self._swap