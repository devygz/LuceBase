import machine
import syspr
import b_utils

rtc = machine.RTC()
# (y, m, d, wkday, h, m, s, subsecs)
rtc.datetime((1970, 0, 0, 0, 0, 0, 0, 0))
syspr.log_print("boot", 3, "RTC set to 0")

# boot modes

bootcfg = b_utils.load_bcfg()
if not bootcfg or not bootcfg["BootTo"]:
    syspr.log_print('boot', 2, 'Missing BootTo or bcfg. Full Booting')
elif bootcfg["BootTo"] == "normal":
    syspr.log_print('boot', 3, 'BootTo set to normal. Full Booting')
elif bootcfg["BootTo"] and bootcfg["BootTo"] == "fwu":
    syspr.log_print('boot', 3, 'BootTo set to fwu. Firmware Update flow...')
elif bootcfg["BootTo"] and bootcfg["BootTo"] == "rec":
    syspr.log_print('boot', 3, 'BootTo set to rec. Recovery Mode flow...')
else:
    syspr.log_print('boot', 2, f'Unknown BootTo cfg: {bootcfg["BootTo"]}. Continuing with Full Boot...')