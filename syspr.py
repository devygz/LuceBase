import machine
import time

logging_enabled = False
save_verb = False
log_history = []    # store last x logs
histmaxlen = 50

omitc = 0
totac = 0
ignrc = 0

LOG_LEVELS = ["", "ERR:", "WARN:", "INFO:", "VERB:"]

def store_log(log_msg):
    global omitc, totac
    totac += 1
    log_history.append(log_msg)
    if len(log_history) > histmaxlen:
        log_history.pop(0)
        omitc += 1

def get_timestamp():
    rtc = machine.RTC()
    t = rtc.datetime()
    ms = time.ticks_ms() % 1000
    return f"{t[4]:02d}:{t[5]:02d}:{t[6]:02d}.{ms:03d}"

def log_print(process, ltype, message):
    global ignrc
    if not logging_enabled and ltype == 4 and not save_verb:
        ignrc += 1
        return
    stype = LOG_LEVELS[ltype]
    prtms = f"[{get_timestamp()}] [{process}] {stype} {message}"
    if logging_enabled:
        print(prtms)
    
    if ltype != 4 or save_verb:
        store_log(prtms)