# Built in Dependencies
from statistics import mean

# External Dependencies
import psutil

print("Temperature sensors")
temps = psutil.sensors_temperatures()
for name, entries in temps.items():
    print(f"Temp sensor {name}")
    for entry in entries:
        print(f"\tCurrent: {entry.current}\tHigh: {entry.high}\tCritical: {entry.critical}")
    currAvg = mean([entry.current for entry in entries if entry.current > 0])
    print(f"Avg: {currAvg}")
    print()
    
print("Fan speeds")

fans = psutil.sensors_fans()
for name, entries in fans.items():
    print(f"Fan sensor {name}")
    for entry in entries:
        print(f"\tCurrent: {entry.current}")
        
battery = psutil.sensors_battery()
print(battery)