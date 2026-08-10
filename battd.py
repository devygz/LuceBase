import base
import asyncio
import time

import syspr
import sensors
import usrcfg

async def run():
    dname = "battd"
    TICK_WT_SEC = 4
    syspr.log_print(dname, 0, "Starting battd")

    batt_vHist = []
    last_avg = usrcfg.get("battd_last_pct", sensors.estimate_percentage(sensors.read_vsys()))
    total_drop = usrcfg.get("battd_total_drop", 0.0)

    while True:
        startus = time.ticks_us()
        for t in base.running_tasks:
            if t["name"] == dname: # Use the specific name of the daemon
                t["last_tick"] = time.ticks_ms()
                break
        
        curr_pct = sensors.estimate_percentage(sensors.read_vsys())
        
        batt_vHist.append(curr_pct)
        
        if len(batt_vHist) >= 20:
            avg_pct = sum(batt_vHist) / len(batt_vHist)
            batt_vHist = [] 
            
            if avg_pct < (last_avg - 0.01):
                drop = last_avg - avg_pct
                total_drop += drop
                
                usrcfg.set("battd_total_drop", total_drop)
                usrcfg.set("battd_last_pct", avg_pct)
                usrcfg.store()
                
                syspr.log_print(dname, 0, f"status: drain, avg: {avg_pct:.2f}, cycles: {total_drop / 100:.4f}")
                last_avg = avg_pct

            elif avg_pct > last_avg + 0.5:
                syspr.log_print(dname, 0, f"status: charging, baseline: {avg_pct:.2f}")
                last_avg = avg_pct
                usrcfg.set("battd_last_pct", last_avg)
                usrcfg.store()
        else:
            syspr.log_print(dname, 4, f"length: {len(batt_vHist)}")
        utilus = time.ticks_us() - startus
        loadratio = utilus / (TICK_WT_SEC * 1000 * 1000)
        for t in base.running_tasks:
            if t["name"] == dname:
                t["load"] = loadratio
                break
        await asyncio.sleep(TICK_WT_SEC)