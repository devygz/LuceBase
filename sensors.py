import machine
from machine import Pin
import time
import network
import bluetooth

import syspr
import usrcfg

sensor_temp = machine.ADC(4) # Internal temp sensor pin

def read_temp():
    reading = sensor_temp.read_u16() * (3.3 / 65535)
    temperature = 27 - (reading - 0.706) / 0.001721
    return int(temperature)

def get_uptime():
    millis = time.ticks_ms()
    seconds = millis // 1000
    
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    return f"{days}d {hours}h {minutes}m {seconds}s"

def read_temp_raw():
    reading = sensor_temp.read_u16() * (3.3 / 65535)
    temperature = 27 - (reading - 0.706) / 0.001721
    return temperature

def is_on_usb():
    return Pin('WL_GPIO2', Pin.IN)

def read_vsys():
    conversion_factor = 3 * 3.3 / 65535
    wlan = network.WLAN(network.STA_IF)
    wlan_active = wlan.active()

    voltread = 0.0

    try:
        syspr.log_print("sensors", 4, "read_vsys Requested: Disabling Wi-Fi module for a moment...")
        # Disable WLAN temp
        wlan.active(False)
        Pin(25, mode=Pin.OUT, pull=Pin.PULL_DOWN).high()
        
        Pin(29, Pin.IN)
        
        vsys = machine.ADC(29)
        return vsys.read_u16() * conversion_factor

    finally:
        syspr.log_print("sensors", 4, "read_vsys: We're done now, enabling Wi-Fi again...")
        Pin(29, Pin.ALT, pull=Pin.PULL_DOWN, alt=7)
        wlan.active(wlan_active)
    

def estimate_percentage(voltage):
    # Li-Po 18650
    # 4.2V = 100%, 3.7V = ~50%, 3.0V = 0%
    if voltage >= 4.2:
        return 100
    if voltage <= 3.0:
        return 0

    if voltage > 3.8:
        return (voltage - 3.8) / (4.2 - 3.8) * 40 + 60
    elif voltage > 3.5:
        return (voltage - 3.5) / (3.8 - 3.5) * 40 + 20
    else:
        return (voltage - 3.0) / (3.5 - 3.0) * 20

def get_battery_health(design_cycles=500):
    total_drop = usrcfg.get("battd_total_drop", 0.0)
    cycles = total_drop / 100
    health = 100 - (cycles / design_cycles * 20)
    
    return max(0, min(100, health)), cycles

def format_health_report():
    health, cycles = get_battery_health()
    return f"Health: {health:.1f}% | Cycles: {cycles:.2f}"