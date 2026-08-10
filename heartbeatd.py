import base
import machine
import time
import asyncio
import syspr

dname = "heartbeatd"

async def run():
    # me = asyncio.current_task()
    # base.running_tasks.append({"name": "heartbeatd", "task": me, "type": "daemon"})
    TICK_WT_SEC = 2
    
    led = machine.Pin("LED", machine.Pin.OUT)
    syspr.log_print(dname, 0, "Onboard LED configured. Starting heartbeatd")
    while True:
        startus = time.ticks_us()
        for t in base.running_tasks:
            if t["name"] == "heartbeatd": # Use the specific name of the daemon
                t["last_tick"] = time.ticks_ms()
                break
        led.toggle() # Light will blink every 5 seconds
        syspr.log_print(dname, 4, "Heartbeat OK. Onboard LED toggled.")

        utilus = time.ticks_us() - startus
        loadratio = utilus / (TICK_WT_SEC * 1000 * 1000)
        for t in base.running_tasks:
            if t["name"] == dname:
                t["load"] = loadratio
                break
        await asyncio.sleep(TICK_WT_SEC)
