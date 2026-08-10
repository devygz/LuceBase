"""
    syscfg stores the hardcoded configuration values for the firmware. This script isn't
    designed to be changed on the fly, by the firmware itself. Instead, user settings and
    overrides should be saved into another controller called "usrcfgc".

    This file might be generated on the fly or might be modified from a base template
    during Firmware Personalization. OTA/Delta updates should avoid modifying this file
    as much as possible, though having the reduced-state environment would likely reduce
    possible problems that might arise.

    For Variant firmwares, if a new key added to the syscfg as a kernel update, this file
    might create conflicts. In this case, please add the new keys to syscfg and retain the
    HW and CF (Customized Firmware) strings per the branch/project. Another important point
    is that during the development in branch, only the CF_BUILD MUST be increased. Increasing
    FW_BUILD or changing it in any way WILL cause very hard to fix versioning conflicts.

    CF = Customized Firmware
"""

import os

" *--- [CF] Variant Settings  ---* "

CF_STRING       =   "LuceThermostat (Example Variant)"
CF_VERSION      =   1
CF_HR_VERSION   =   "1.0"
CF_RELEASE      =   "DEV"
CF_BUILD        =   1
CF_BUILD_TS     =   "Jan 1, 1971 00:00:00 UTC+0"

" *--- [FW] Firmware Settings ---* "

FW_STRING       =   "LuceFirmware 2 (Prototype)"
FW_VERSION      =   1                           # Firmware Version Code. Integer related with standard version.
FW_HR_VERSION   =   "1.0"
FW_RELEASE      =   "DEV"                       # Build Release type. DEV = Development, PRD = Production. 
FW_BUILD        =   29                          # Build Number. Increase per deployment + also when needed while debugging.
FW_BUILD_TS     =   "Jan 1, 1970 00:00:00 UTC+0"    # Build Human-Readable Timestamp

FW_VRT_VARIANT  =   "STANDARD"                  # Firmware Variant. Future use.

FW_HW_MODEL     =   "HC-1"                      # Product Family Code
FW_HW_HR_MODEL  =   "HC-1 Heating Controller"   # Human-Readable Product Family
FW_HW_BASE      =   "RPi_Pico2W"
FW_HW_ARCH      =   "ARM-M33"                   # Firmware Target Architecture, though cross-compatibility with RISC-V based Hazard3 cores is a priority.
FW_HW_VARIANT   =   "HC-1 (2.4GHz RF)"          # Human-Readable Variant Model Name
FW_HW_VRTNM     =   "HC1-24G"                   # Variant Model Code


" *--- [BTD] Bluetooth Daemon ---* "

BTD_ENABLE_BT   =   True
BTD_ADV_UUID    =   "12872433-76FD-4362-B274-DFFAEA68454E" # example
BTD_ADV_DVNM    =   "InnsbruckBT"               # DVNM: Device Name

FW_OTA_SIGN_PBK = "[OTA_SIGNING_SYM_KEY]"

" *--- [KRN] Kernel ---* "
KRN_MEM_MAX = 95
KRN_MEM_KLLS = ["otad", "heartbeatd"]

KRN_MEM_GCX = 70
KRN_USPC_INPUTMAX = 8192

" *--- [FU] Firmware Upgrade ---*"

FU_CHECK_SIG = True
FU_LOCK_DOWNGRADE = False

" *--- DYNAMICS ---*"
FUNonce = os.urandom(16)