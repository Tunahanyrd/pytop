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
