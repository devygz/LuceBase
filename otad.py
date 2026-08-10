import asyncio
import base
import time
import syspr
import btd
import json
import hashlib
import binascii
import os
import syscfg

dname = "otad"

def manual_hmac_sha256(key, msg):
    """
    Manual implementation of HMAC-SHA256 for builds missing the hmac module.
    """
    # SHA256 block size is 64 bytes
    block_size = 64
    if len(key) > block_size:
        key = hashlib.sha256(key).digest()
    if len(key) < block_size:
        key = key + b'\x00' * (block_size - len(key))

    o_key_pad = bytes(x ^ 0x5c for x in key)
    i_key_pad = bytes(x ^ 0x36 for x in key)

    inner_hash = hashlib.sha256(i_key_pad + msg).digest()
    return hashlib.sha256(o_key_pad + inner_hash).digest()

def verify_hmac(payload_bytes, incoming_hmac_hex, secret_key_str):
    try:
        secret = secret_key_str.encode()
        # Calculate expected HMAC manually
        expected_hmac = manual_hmac_sha256(secret, payload_bytes)
        expected_hex = binascii.hexlify(expected_hmac).decode()
        
        return expected_hex == incoming_hmac_hex
    except Exception as e:
        syspr.log_print(dname, 1, f"HMAC Error: {e}")
        return False

async def run():
    
    is_authenticated = False
    target_filename = ""
    expected_file_sha = ""
    current_file = None

    TICK_WT_MS = 50
    
    syspr.log_print(dname, 3, "OTA Daemon online. Security: Manual HMAC-SHA256.")

    while True:
        startus = time.ticks_us()
        # 1. Update Registry Tick
        for t in base.running_tasks:
            if t["name"] == dname:
                t["last_tick"] = time.ticks_ms()
                break

        # 2. Process Handshake Reply
        if btd.ota_buffer["reply"] != b"":
            raw_reply = btd.ota_buffer["reply"]
            btd.ota_buffer["reply"] = b"" 
            
            try:
                data = json.loads(raw_reply)
                client_nonce = data.get("nonce", "")
                client_file_sha = data.get("sig", "") 
                client_name = data.get("name", "")
                auth_sig_hex = data.get("auth_sig", "")

                if client_nonce != btd.ota_buffer["nonce"].hex():
                    syspr.log_print(dname, 1, "Auth Denied: Nonce mismatch.")
                    continue
                
                # Reconstruct payload (No spaces)
                verify_payload = json.dumps({
                    "nonce": client_nonce,
                    "sig": client_file_sha,
                    "name": client_name
                }, separators=(',', ':')).encode()

                if verify_hmac(verify_payload, auth_sig_hex, syscfg.FW_OTA_SIGN_PBK):
                    is_authenticated = True
                    target_filename = client_name
                    expected_file_sha = client_file_sha
                    syspr.log_print(dname, 2, f"Authenticated: {target_filename}")
                else:
                    syspr.log_print(dname, 1, "Auth Failed: Signature mismatch.")

            except Exception as e:
                syspr.log_print(dname, 1, f"Handshake Error: {e}")

        # 3. Handle Commands
        if (btd.ota_buffer["cmd"] != b"") and (not btd.ota_buffer["cmd"].decode().strip().startswith("CFX")):
            cmd_raw = btd.ota_buffer["cmd"].decode().strip()
            btd.ota_buffer["cmd"] = b"" 
            
            if cmd_raw == "START":
                if not is_authenticated:
                    syspr.log_print(dname, 1, "START Blocked.")
                else:
                    tmp_name = f"_otad-tmp_{target_filename}"
                    current_file = open(tmp_name, "wb")
                    syspr.log_print(dname, 2, f"Streaming: {tmp_name}")
            
            elif cmd_raw == "END":
                if current_file:
                    current_file.close()
                    current_file = None
                    
                    tmp_path = f"_otad-tmp_{target_filename}"
                    hasher = hashlib.sha256()
                    with open(tmp_path, "rb") as f:
                        while True:
                            chunk = f.read(1024)
                            if not chunk: break
                            hasher.update(chunk)
                        calc_sha = binascii.hexlify(hasher.digest()).decode()
                    
                    if calc_sha == expected_file_sha:
                        syspr.log_print(dname, 3, "Verified. Swapping files.")
                        try: os.remove(target_filename)
                        except: pass
                        os.rename(tmp_path, target_filename)
                        os.sync()
                    else:
                        syspr.log_print(dname, 1, "SHA Mismatch! Purging.")
                        os.remove(tmp_path)

                    is_authenticated = False 

        # 4. Handle Data
        if btd.ota_buffer["data"] != b"":
            if current_file:
                current_file.write(btd.ota_buffer["data"])
            btd.ota_buffer["data"] = b""
        
        utilus = time.ticks_us() - startus 
        loadratio = utilus / (TICK_WT_MS * 1000)
        for t in base.running_tasks:
            if t["name"] == dname:
                t["load"] = loadratio
                break
        await asyncio.sleep_ms(TICK_WT_MS)