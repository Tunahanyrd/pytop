# engine/__init__.py
"""
engine paketi — sistem kaynaklarını (CPU, Memory, Disk, Process) izlemek için
yüksek seviye sınıfları dışa açar.

Kullanım örneği:
    from engine import CPU, Memory, Disk, ProcessManager

    cpu = CPU()
    print(cpu.get_percent())

"""

__version__ = "0.1.0"

from .cpu import CPU
from .memory import Memory
from .disk import Disk
from .processes import ProcessManager

__all__ = [
    "CPU",
    "Memory",
    "Disk",
    "ProcessManager",
]