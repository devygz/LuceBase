import base
import asyncio
import time

import syspr

async def run():
    dname = "dummyd"
    TICK_WT_SEC = 1
    syspr.log_print("dummyd", 0, "Dummy process starting finishing timer (20s)...")
    start_time = time.ticks_ms()
    while True:
        startus = time.ticks_us()
        for t in base.running_tasks:
            if t["name"] == "dummyd": # Use the specific name of the daemon
                t["last_tick"] = time.ticks_ms()
                break
        if time.ticks_diff(time.ticks_ms(), start_time) > 20000:
            syspr.log_print("dummyd", 3, "Simulating resolved task...")
            break
        
        utilus = time.ticks_us() - startus
        loadratio = utilus / (TICK_WT_SEC * 1000 * 1000)
        for t in base.running_tasks:
            if t["name"] == dname:
                t["load"] = loadratio
                break
        await asyncio.sleep(TICK_WT_SEC)