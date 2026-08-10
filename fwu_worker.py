import base
import asyncio
import time
import os

import syspr

async def run():
    dname = "fwu_worker"
    TICK_WT_SEC = 1
    syspr.logging_enabled = True
    syspr.log_print(dname, 3, "Firmware Update Worker v1.0.0.")
    syspr.log_print(dname, 0, "Log streaming has been enabled")
    start_time = time.ticks_ms()

    syspr.log_print(dname, 0, "Checking staged files for Firmware Upgrade")
    osfiles = os.listdir()
    staged_files = []

    for fn in osfiles:
        if fn.endswith('.upd'):
            staged_files.append(fn)
            syspr.log_print(dname, 0, f"File added to the queue: {fn.replace('.upd', '')}")
    
    syspr.log_print(dname, 0, f'{len(staged_files)} files added for FWU queue.\nOverview:\n\n{"  ".join(staged_files)}\n\n')

    syspr.log_print(dname, 3, "FWU starts in 20 seconds.")
    await asyncio.sleep(20)

    for fn in staged_files:
        orig_name = fn.replace('.upd', '')
        syspr.log_print(dname, 3, f"Replacing {orig_name} with newer version.")
        try:
            os.remove(orig_name)
            syspr.log_print(dname, 0, f"File {orig_name} deleted successfully.")
        except OSError:
            syspr.log_print(dname, 2, f"File {orig_name} does not exist. No problem, replacing anyway...")
        os.rename(fn, orig_name)
        syspr.log_print(dname, 3, f"File {orig_name} has been updated.")
    
    syspr.log_print(dname, 3, f"All files have been updated successfully. Setting boot to normal")
    import b_utils
    b_utils.set_boot_to('normal')
    syspr.log_print(dname, 3, f"Everything is OK. Rebooting in 30 seconds...")
    await asyncio.sleep(30)
    import machine
    machine.soft_reset()

    while True:
        startus = time.ticks_us()
        for t in base.running_tasks:
            if t["name"] == dname: # Use the specific name of the daemon
                t["last_tick"] = time.ticks_ms()
                break

        utilus = time.ticks_us() - startus
        loadratio = utilus / (TICK_WT_SEC * 1000 * 1000)
        for t in base.running_tasks:
            if t["name"] == dname:
                t["load"] = loadratio
                break
        await asyncio.sleep(TICK_WT_SEC)