import gc
import os
import time
import hashlib
import binascii
import json

import base
import syspr
import syscfg
import sensors
import b_utils

rcu_ver = "1"
rcu_filestoupd = []
rcu_prepareinprogress = False

def _manual_hmac_sha256(key, msg):
    block_size = 64
    if len(key) > block_size:
        key = hashlib.sha256(key).digest()
    if len(key) < block_size:
        key = key + b'\x00' * (block_size - len(key))

    o_key_pad = bytes(x ^ 0x5c for x in key)
    i_key_pad = bytes(x ^ 0x36 for x in key)

    inner_hash = hashlib.sha256(i_key_pad + msg).digest()
    return hashlib.sha256(o_key_pad + inner_hash).digest()


def _verify_hmac(payload, incoming_hmac_hex, secret_key_str):
    try:
        secret = secret_key_str.encode()
        if isinstance(payload, str):
            payload = payload.encode()
        expected_hmac = _manual_hmac_sha256(secret, payload)
        expected_hex = binascii.hexlify(expected_hmac).decode()
        
        return expected_hex == incoming_hmac_hex
    except Exception as e:
        syspr.log_print("rcuutil", 1, f"HMAC Error: {e}")
        return False


def prepare(*args):
    global rcu_filestoupd, rcu_prepareinprogress, rcu_ver
    # args 0: rcuutil comm version; 1: (base64 encoded)-fwu_manifest; 2: (base64 encoded)-fwu_manifest_sign
    if not args or not args[0] or not args[1] or not args[2]:
        print("rcuutil::FAIL:PreCheck:Missing arguments.")
        return
    if args[0] != rcu_ver:
        print("rcuutil::FAIL:PreCheck:rcuutil version mismatch.")
        return
    
    if len(args[1]) >  syscfg.KRN_USPC_INPUTMAX or len(args[2]) > syscfg.KRN_USPC_INPUTMAX:
        print(f"rcuutil::FAIL:PreCheck:Arguments too long. Kernel mandated max size: {syscfg.KRN_USPC_INPUTMAX}")
        return
    
    hmac_check_result = _verify_hmac(args[1], args[2], syscfg.FW_OTA_SIGN_PBK)
    if not hmac_check_result:
        print("rcuutil::FAIL:SignErr:Manifest signature couldn't be verified.")
        return
    
    fwu_manifest = binascii.a2b_base64(args[1])
    fwu_m_decoded = json.loads(fwu_manifest)

    if not fwu_m_decoded or not fwu_m_decoded["FUMVersion"] or not fwu_m_decoded["FUFirmwareBuild"] or not fwu_m_decoded["FURelease"] or not fwu_m_decoded["FUNonce"]:
        print("rcuutil::FAIL:FlightCheck:Corrupted manifest? Missing arguments in the manifest. Report to lucefw-dev@yagz.eu.")
        return
    
    if fwu_m_decoded["FUMVersion"] != rcu_ver:
        print("rcuutil::FAIL:FlightCheck:Manifest version mismatch.")
        return
    device_nonce_hex = binascii.hexlify(syscfg.FUNonce).decode('utf-8') if isinstance(syscfg.FUNonce, bytes) else str(syscfg.FUNonce)

    if str(fwu_m_decoded["FUNonce"]).strip() != device_nonce_hex.strip():
        print(f"rcuutil::FAIL:FlightCheck:Nonce mismatch. Payload: '{fwu_m_decoded['FUNonce']}' vs Device: '{device_nonce_hex}'")
        return
    
    if syscfg.FU_LOCK_DOWNGRADE and fwu_m_decoded["FUFirmwareBuild"] <= syscfg.FW_BUILD:
        print("rcuutil::FAIL:FlightCheck:FU Bundle Firmware Build older than current build.")
        return
    
    if syscfg.FU_LOCK_DOWNGRADE and fwu_m_decoded["FUCFBuild"] <= syscfg.CF_BUILD:
        print("rcuutil::FAIL:FlightCheck:FU Bundle CF Build older than current build.")
        return
    
    rcu_filestoupd = fwu_m_decoded["FUMFileList"]
    rcu_prepareinprogress = True

    print("Firmware Upgrade progress accepted. You may now push the files.")
    print("rcuutil::OK:PushPrepareOK")


def push(*args):
    global rcu_filestoupd, rcu_prepareinprogress, rcu_ver
    # args 0: (base64 encoded)-fwu_filecontent; 1: (base64 encoded)-fwu_manifest_sign, 2: filename
    if not rcu_prepareinprogress:
        print("rcuutil::FAIL:PreCheck:RCU not ready. Prepare first!")
        return
    if not args or not args[0] or not args[1] or not args[2]:
        print("rcuutil::FAIL:PreCheck:Missing arguments.")
        return
    
    device_nonce_hex = binascii.hexlify(syscfg.FUNonce).decode('utf-8') if isinstance(syscfg.FUNonce, bytes) else str(syscfg.FUNonce)
    
    sig_check_input = args[0] + ":" + device_nonce_hex + ":" + args[2]
    sig_chk_result = _verify_hmac(sig_check_input, args[1], syscfg.FW_OTA_SIGN_PBK)

    if not sig_chk_result:
        print("rcuutil::FAIL:FlightCheck:Bag signature check failed.")
        return
    
    if args[2] not in rcu_filestoupd:
        print("rcuutil::FAIL:FlightCheck:File not in the manifest.")
        return
    
    with open(args[2]+".upd", 'w+') as file:
        file.write(binascii.a2b_base64(args[0]))
    
    print("File staged for FWU")
    print("rcuutil::OK:PushFileOK")

    rcu_filestoupd.remove(args[2])

    if len(rcu_filestoupd) < 1:
        b_utils.set_boot_to('fwu')
        print("rcuutil::OK:SetFWUNextBootOK:All manifested files have been received. BootTo set to 'fwu' for the next boot.\nReboot now for FWU.")
    
    

