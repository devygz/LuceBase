# terminalc.py
import gc
import os
import time
from asyncio import CancelledError as _asyncCancelledError

import base
import syspr
import syscfg
import sensors
import b_utils


def tsk(*args):
    loadtot = 0
    loadmax = 0
    headr = f"{'Name':<12} {'State':<10} {'Type':<10} {'Last Tick':<15} {'Load Mem':<10} {'Load':<6}"
    print(f"\n{headr}")
    print("-" * len(headr))
    
    for item in base.running_tasks:
        state = "STOPPED" if item["task"].done() else "RUNNING"
        state = f"{item['state']}" if item["task"].done() else state
        last = item.get("last_tick")
        load = item.get("load")
        loadstr = ""
        tick_str = "Default"
        if last is not None:
            delta = time.ticks_diff(time.ticks_ms(), last) / 1000
            tick_str = f"{delta:.3f}s ago"
        else:
            tick_str = "(Never)"
        
        if load is not None:
            loadtot += load
            if load > loadmax:
                loadmax = load
            loadstr = f"{load:.3f}"
        print(f"{item['name']:<12} {state:<10} {item['type']:<10} {tick_str:<15} {item['mem_use']:<10} {loadstr:<6}")
    
    # Also show kernel as a "task"
    tick_str = "(Never)"
    if base.kernel_last_tick is not None:
            delta = time.ticks_diff(time.ticks_ms(), base.kernel_last_tick) / 1000
            tick_str = f"{delta:.3f}s ago"
    print(f'{"kernel":<12} {"RUNNING":<10} {"kernel":<10} {tick_str:<15}')
    print("")
    print(f"Total Load: {loadtot:.3f}")
    print(f"Max.  Load: {loadmax:.3f}")

    return f"\nTotal Tasks: {len(base.running_tasks)}"

def memstat(*args):
    gc.collect()
    allc = gc.mem_alloc()
    frer = gc.mem_free()
    tota = allc + frer
    util = allc / tota * 100
    utils = f"{util:.2f}"
    return f"{allc} bytes allocated ({utils}% util), {frer} bytes free, {tota} bytes total."

def flstat():
    st = os.statvfs('/')
    
    block_size = st[0]
    total_blocks = st[2]
    free_blocks = st[3]
    
    total_bytes = total_blocks * block_size
    free_bytes = free_blocks * block_size
    used_bytes = total_bytes - free_bytes
    
    total_kb = total_bytes / (1024)
    used_kb = used_bytes / (1024)
    free_kb = free_bytes / (1024)
    util_pct = (used_bytes / total_bytes) * 100
    
    return (f"Flash: {used_kb:.1f}KB used ({util_pct:.1f}% util), "
            f"{free_kb:.1f}KB free, {total_kb:.1f}KB total.")

def kill(name):
    for item in base.running_tasks:
        if item["name"] == name:
            item["task"].cancel()  # This triggers the 'CancelledError' in your daemon
            return f"Process {name} terminated."
    return "Process not found."

def logs(*args):
    syspr.logging_enabled = True if args[0] == "on" else False

def bcfg(*args):
    if len(args) >= 2 and args[0] == "boot-to":
        if args[1] == "fwu" and (len(args) < 3 or args[2] != "i-understand-the-risks-of-forcing-this"):
            print('!!! STOP !!!\n\nYou are forcing the system MANUALLY to boot-up to the Firmware Upgrade workflow on the next boot. Normally, BootTo is set to "fwu" automatically by the rcuutil when the new versions of every file in the FUManifest is received.\n\nIn the best case, forcing the device to the FWU will just result in FWU leaving to the normal boot, since there are no staged updates. However, if there are any leftover staged files because of any kind of interruptions, this might CORRUPT the firmware IRREVERSIBLY.\n\nIf you are really sure on what you are doing, pass the "i-understand-the-risks-of-forcing-this" as the last argument.')
        
        else:    
            rslt = b_utils.set_boot_to(args[1])
            if rslt:
                print(f"BootTo successfully changed to {args[1]}")
            else:
                print("An error occurred while trying to set the BootTo. See the loghist.")
        return
    try:
        with open('bcfg.txt', 'r') as file:
            print(file.read())
            print("")
    except OSError:
        print("bcfg.txt not found.")

def fwinfo(*args):
    print(f"{syscfg.CF_STRING} v{syscfg.CF_HR_VERSION} (variant of {syscfg.FW_STRING}); Release {syscfg.CF_RELEASE}; Build {syscfg.CF_BUILD}, {syscfg.CF_BUILD_TS}; {syscfg.FW_STRING} v{syscfg.FW_HR_VERSION}; Release {syscfg.FW_RELEASE}; Build {syscfg.FW_BUILD}, {syscfg.FW_BUILD_TS}; {syscfg.FW_HW_ARCH}")

def hwinfo(*args):
    import machine

    # The Raspberry Pi Manufacturer ID is 0x942 (bits 11:0 of CHIP_ID)
    RPI_MANUF_ID = 0x942
    # Search range for SYSINFO block
    SEARCH_START = 0x400e8000
    SEARCH_END = 0x400e8100

    print("Searching for Raspberry Pi CHIP_ID register...")

    found = False
    for addr in range(SEARCH_START, SEARCH_END, 4):
        val = machine.mem32[addr]
        if (val & 0xFFF) == RPI_MANUF_ID:
            rev = (val >> 28) & 0xF
            part = (val >> 12) & 0xFFFF
            print(f"\n--- MATCH FOUND ---")
            print(f"Address: {hex(addr)}")
            print(f"Raw Value: {hex(val)}")
            print(f"Revision: {rev} (Stepping A{rev})")
            print(f"Part ID: {hex(part)}")
            found = True
            break

    if not found:
        print("\nCould not find Manufacturer ID 0x942 in the SYSINFO block.")
        print("This may be due to TrustZone security restrictions in your MicroPython build.")
    rom_ver = machine.mem8[0x00000013] 
    print(f"ROM Version: {rom_ver}")
    print(f"Hardware Series: {syscfg.FW_HW_HR_MODEL} ({syscfg.FW_HW_MODEL})\nVariant: {syscfg.FW_HW_VARIANT} ({syscfg.FW_HW_VRTNM})\nArchitecture: {syscfg.FW_HW_ARCH}\nMain Platform: {syscfg.FW_HW_BASE}")

def reboot(*args): # soft reset
    import machine
    machine.soft_reset()

def reset(*args): # hard reset
    import machine
    machine.reset()

def dbg_enter_bl(*args): # hard reset
    import machine
    machine.bootloader()

def temps(*args):
    ctemp = f"{sensors.read_temp_raw():.1f}"
    print(f"CPU Temp: {ctemp}°C")

def uptime(*args):
    print(f"{sensors.get_uptime()}")

def batts(*args):
    v = sensors.read_vsys()
    p = sensors.estimate_percentage(v)
    isusb = "Yes" if sensors.is_on_usb() else "No"
    print(f"VSYS Voltage: {v:.2f}V\nEstimated Battery: {p:.1f}%\nUSB Connected: {isusb}")
    print(sensors.format_health_report())

def loghist(*args):
    for x in syspr.log_history:
        print(x)

def logstat(*args):
    return f"{len(syspr.log_history)} logs stored, {syspr.omitc} logs omitted, {syspr.ignrc} logs ignored, {syspr.totac} logs since boot."

def krncfg(*args):
    return f"Active Kernel Configuration\nKRN_MEM_MAX = {syscfg.KRN_MEM_MAX}\nKRN_MEM_GCX = {syscfg.KRN_MEM_GCX}"

def fsls(*args):
    return " ".join(os.listdir())

def fsrm(name):
    if not name:
        print("Specify file to delete in args.")
        return
    
    os.remove(name)
    print(f"Removed: {name}")
    
def rcu_info():
    if not b_utils.bootcfg or not b_utils.bootcfg["BootTo"] or not b_utils.bootcfg["BootTo"] == "rec":
        print("This utility can only run in Recovery Mode!")
        return
    
    print(f"FirmwareVersion={syscfg.FW_VERSION}\nFirmwareBuild={syscfg.FW_BUILD}\nFirmwareRelease={syscfg.FW_RELEASE}\nHardwareModel={syscfg.FW_HW_MODEL}\nHardwareVariantNumber={syscfg.FW_HW_VRTNM}\nHardwareArch={syscfg.FW_HW_ARCH}\nHardwareBase={syscfg.FW_HW_BASE}\nCFVersion={syscfg.CF_VERSION}\nCFRelease={syscfg.CF_RELEASE}\nCFBuild={syscfg.CF_BUILD}\nCFString={syscfg.CF_STRING}")

def rcu_session():
    if not b_utils.bootcfg or not b_utils.bootcfg["BootTo"] or not b_utils.bootcfg["BootTo"] == "rec":
        print("This utility can only run in Recovery Mode!")
        return
    
    print(f"FUNonce={syscfg.FUNonce.hex()}")


def help():
    all_names = globals()
    
    commands = []
    for name in all_names:
        obj = all_names[name]
        if hasattr(obj, "__name__") and not name.startswith("_") and not (b_utils.bootcfg and b_utils.bootcfg["BootTo"] and b_utils.bootcfg["BootTo"] == "normal" and name.startswith("rcu_")):
            if callable(obj):
                commands.append(name)
    
    commands.sort()
    return " ".join(commands)