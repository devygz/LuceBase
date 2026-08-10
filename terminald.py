import asyncio
import sys
import time
import uselect
import base
import terminalc


import b_utils

spoll = uselect.poll()
spoll.register(sys.stdin, uselect.POLLIN)

dname = "terminald"

controllers = {
    "terminalc": terminalc,
    "tsk": terminalc,
    "memstat": terminalc,
    "flstat": terminalc,
    "fwinfo": terminalc,
    "hwinfo": terminalc,
    "temps": terminalc,
    "loghist": terminalc,
    "logstat": terminalc,
    "help": terminalc,
    "batts": terminalc,
    "reboot": terminalc,
    "reset": terminalc,
    "fsls": terminalc,
    "fsrm": terminalc,
    "uptime": terminalc,
    "krncfg": terminalc,
    "dbg_enter_bl": terminalc,
    "bcfg" : terminalc,
    "rcu_info": terminalc,
    "rcu_session": terminalc,
}

if b_utils.bootcfg['BootTo'] == "rec":
    import rcuutil
    controllers["rcuutil"] = rcuutil

async def run():
    # me = asyncio.current_task()
    # base.running_tasks.append({"name": "terminald", "task": me, "type": "daemon"})
    global dname
    TICK_WT_SEC = 0.01
    buffer = ""

    if b_utils.bootcfg and b_utils.bootcfg["BootTo"] and b_utils.bootcfg["BootTo"] == "rec":
        sys.stdout.write("\r\nRecovery Mode Terminal\r\n> ")
    elif b_utils.bootcfg and b_utils.bootcfg["BootTo"] and b_utils.bootcfg["BootTo"] == "fwu":
        sys.stdout.write("\r\n! WARNING: A firmware upgrade is in progress. DO NOT use the terminal UNLESS you know what you are doing.\r\n> ")
    else:
        sys.stdout.write("\r\nSystem Shell Ready (Full Boot)\r\n> ")
    
    while True:
        startus = time.ticks_us()
        for t in base.running_tasks:
            if t["name"] == "terminald": # Use the specific name of the daemon
                t["last_tick"] = time.ticks_ms()
                break
        if spoll.poll(0):
            char = sys.stdin.read(1)
            
            if char in ('\r', '\n'):
                sys.stdout.write("\r\n")
                cmd_line = buffer.strip()
                
                if cmd_line:
                    parts = cmd_line.split(" ")
                    utility = parts[0].lower()
                    
                    if utility in controllers:
                        module = controllers[utility]
                        # Handle commands like 'ps' or 'terminalc ps'
                        has_sub = len(parts) > 1
                        cmd = parts[1].replace("-", "_") if has_sub else utility
                        args = parts[2:] if has_sub else parts[1:]
                        
                        try:
                            func = getattr(module, cmd)
                            result = func(*args)
                            if result: 
                                sys.stdout.write(str(result) + "\r\n")
                        except AttributeError:
                            sys.stdout.write(f"Error: '{utility}' has no command '{cmd}'\r\n")
                    else:
                        sys.stdout.write(f"Unknown utility: {utility}\r\n")
                
                buffer = ""
                sys.stdout.write("> ")

            # bspace
            elif char in ('\x08', '\x7f'):
                if len(buffer) > 0:
                    buffer = buffer[:-1]
                    sys.stdout.write("\b \b")
            
            # char back
            else:
                buffer += char
                sys.stdout.write(char)

        # yield back
        utilus = time.ticks_us() - startus
        loadratio = utilus / (TICK_WT_SEC * 1000 * 1000)
        for t in base.running_tasks:
            if t["name"] == dname:
                t["load"] = loadratio
                break
        await asyncio.sleep(TICK_WT_SEC)