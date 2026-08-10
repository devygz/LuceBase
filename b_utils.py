import syspr

bootcfg = {}

def load_bcfg():
    bcfg = {}
    try:
        with open('bcfg.txt', 'r') as file:
            syspr.log_print('b_utils', 4, 'Reading bcfg')
            for line in file:
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    bcfg[key.strip()] = value.strip()
    except OSError:
        syspr.log_print('b_utils', 1, 'bcfg file not found.')
    return bcfg

def set_boot_to(mode):
    valid_modes = ["normal", "rec", "fwu"]
    
    if mode not in valid_modes:
        syspr.log_print('b_utils', 1, f"Invalid BootTo mode: {mode}. Must be one of {valid_modes}")
        return False
        
    bootcfg['BootTo'] = mode

    try:
        with open('bcfg.txt', 'w') as file:
            for key, value in bootcfg.items():
                file.write(f"{key}={value}\n")
                
        syspr.log_print('b_utils', 4, f"BootTo successfully set to '{mode}'")
        return True
        
    except OSError as e:
        syspr.log_print('b_utils', 1, f"Failed to write bcfg.txt: {e}")
        return False

bootcfg = load_bcfg()