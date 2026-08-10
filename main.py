import asyncio
import time
import gc

import base
from syspr import log_print
import syscfg
import terminalc

import b_utils

import terminald




async def supervised_run(name, coro):
    entry = next((p for p in base.running_tasks if p["name"] == name), None)
    
    gc.collect()
    mem_before = gc.mem_free()


    child_task = asyncio.create_task(coro)

    try:

        await asyncio.sleep_ms(150) 
        
        gc.collect()
        mem_after = gc.mem_free()
        usage = (mem_before - mem_after) / 1024
        
        if entry:
            entry["mem_use"] = max(-1, usage) # Ensure a minimum of -1KB
            log_print("kernel", 3, f"Measured startup RAM for {name}: {usage:.2f} KB")

        await child_task

    except asyncio.CancelledError:
        child_task.cancel()
        if entry: entry["state"] = "KILLED"
        log_print("kernel", 2, f"Process '{name}' was killed.")
        try: await child_task
        except: pass
        raise 

    except Exception as e:
        if entry: entry["state"] = "CRASHED"
        log_print("kernel", 1, f"Process '{name}' CRASHED: {e}")

    finally:
        if entry and entry["state"] == "RUNNING":
            entry["state"] = "EXITED"

async def main():
    global terminald
    mem_prs_ac = False
    log_print("kernel", 0, "Kernel is starting...")
    bootcfg = b_utils.load_bcfg()
    daemons = {}

    if bootcfg["BootTo"] == "normal":
        import battd
        import heartbeatd
        import terminald
        import btd
        import otad
        import dummyd
        daemons = {
            "terminald": terminald.run(),
            "heartbeatd": heartbeatd.run(),
            "battd" : battd.run(),
            "btd": btd.run(),
            "otad" : otad.run(),
            "dummyd" : dummyd.run(),
        }

    elif bootcfg["BootTo"] == "rec":
        log_print("kernel", 3, "Device is in Recovery Mode. Only launching the essentials.")
        daemons = {
            "terminald": terminald.run()
        }
    
    elif bootcfg["BootTo"] == "fwu":
        log_print("kernel", 3, "Device is in Firmware Upgrade Mode. Only launching the essentials.")
        import fwu_worker
        daemons = {
            "terminald": terminald.run(),
            "fwu_worker": fwu_worker.run()
        }

    else:
        log_print("kernel", 3, f"Unsupported BootTo: {bootcfg['BootTo']}. Falling back to Terminal-only boot.")
        daemons = {
            "terminald": terminald.run()
        }

    for name, coro in daemons.items():
        task = asyncio.create_task(supervised_run(name, coro))
        
        base.running_tasks.append({
            "name": name,
            "task": task,
            "type": "daemon",
            "state": "RUNNING",
            "last_tick": time.ticks_ms()
        })

    while True:
        base.kernel_last_tick = time.ticks_ms()
        allc = gc.mem_alloc()
        frer = gc.mem_free()
        tota = allc + frer
        util = allc / tota * 100
        if util > syscfg.KRN_MEM_GCX:
            log_print("kernel", 4, f"Mem util over threshold {syscfg.KRN_MEM_GCX}%. Soft release.")
            gc.collect()
        if util > syscfg.KRN_MEM_MAX and not mem_prs_ac:
            log_print("kernel", 2, f"Memory free space is lower than critical threshold, {(100 - syscfg.KRN_MEM_MAX):.1f}%. Stopping non-required daemons.")
            for x in syscfg.KRN_MEM_KLLS:
                log_print("kernel", 2, f"Requesting daemon kill: {x}")
                terminalc.kill(x)
                gc.collect()
            mem_prs_ac = True
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n[kernel] PANIC: {e}")