import asyncio
import bluetooth
import os
import time
import base
import struct
import syspr
import syscfg
import sensors
from ble_advertising import advertising_payload

_conn_handle = None
_hr_handle = None
_raw_handle = None
_ota_cmd_handle = None
_ota_data_handle = None
_ota_nonce_handle = None
_ota_reply_handle = None
_ble = None
dname = "btd"
noncelen = 8

ota_buffer = {"cmd": b"", "data": b"", "reply": b"", "nonce": b""}

reply_accumulator = ""

def ble_irq(event, data):
    global _conn_handle, _ble, _ota_nonce_handle, ota_buffer, reply_accumulator
    
    if event == 1: # _IRQ_CENTRAL_CONNECT
        _conn_handle, _, _ = data

        try:
           _ble.gattc_exchange_mtu(_conn_handle)
           syspr.log_print(dname, 3, "MTU Exchange Requested...")
        except:
            pass 

        if _ota_nonce_handle is not None:
            new_nonce = os.urandom(noncelen)
            _ble.gatts_write(_ota_nonce_handle, new_nonce)
            ota_buffer["nonce"] = new_nonce
            syspr.log_print(dname, 3, f"Session Nonce: {new_nonce.hex()}")
            
    elif event == 2: # _IRQ_CENTRAL_DISCONNECT
        _conn_handle = None
        reply_accumulator = "" 
    
    elif event == 21: # _IRQ_MTU_EXCHANGED
        conn_handle, mtu = data
        syspr.log_print(dname, 0, f"MTU finalized: {mtu} bytes")
        
    elif event == 3: # _IRQ_GATTS_WRITE
        conn_handle, value_handle = data
        received = _ble.gatts_read(value_handle)
        
        
        if value_handle == _ota_cmd_handle:
            ota_buffer["cmd"] = received
            syspr.log_print(dname, 0, "CMD received.")
            
        elif value_handle == _ota_data_handle:
            ota_buffer["data"] += received
            
            
        elif value_handle == _ota_reply_handle:
            try:
                
                chunk = received.decode()
                reply_accumulator += chunk
                
                
                syspr.log_print(dname, 0, f"Received {len(received)}b. Accumulator: {len(reply_accumulator)}b")
                
                if '}' in chunk:
                    ota_buffer["reply"] = reply_accumulator.encode()
                    reply_accumulator = "" 
                    syspr.log_print(dname, 0, "Full OTA Reply reassembled.")
            except Exception as e:
                syspr.log_print(dname, 1, f"Reassembly error: {e}")
                reply_accumulator = ""
                
        elif value_handle == _raw_handle:
            syspr.log_print(dname, 0, f"Raw Write: {received}")

async def run():
    global _conn_handle, _hr_handle, _raw_handle, _ota_cmd_handle, _ota_data_handle, _ota_nonce_handle, _ota_reply_handle, _ble
    TICK_WT_SEC = 0.5
    syspr.log_print(dname, 3, "Starting Bluetooth Hardware Init...")
    
    attempts = 0
    while attempts < 3:
        try:
            _ble = bluetooth.BLE()
            _ble.active(False) # Force shutdown
            await asyncio.sleep_ms(500)
            _ble.active(True)  # Try to wake it up
            _ble.config(mtu=512)
            break 
        except OSError as e:
            attempts += 1
            syspr.log_print(dname, 1, f"Hardware search attempt {attempts} failed: {e}")
            await asyncio.sleep(1)
            if attempts == 3: raise e

    HR_SVC = (bluetooth.UUID(0x180D), ((bluetooth.UUID(0x2A37), bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY),))
    RAW_SVC = (bluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E"), ((bluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E"), bluetooth.FLAG_READ | bluetooth.FLAG_WRITE | bluetooth.FLAG_NOTIFY),))
    
    OTA_SVC_UUID = bluetooth.UUID("C32225E6-5372-457A-885B-69ADA519C069")
    OTA_SVC = (OTA_SVC_UUID, (
        (bluetooth.UUID("C32225E6-5372-457A-885B-69ADA519C070"), bluetooth.FLAG_WRITE),
        (bluetooth.UUID("C32225E6-5372-457A-885B-69ADA519C071"), bluetooth.FLAG_WRITE),
        (bluetooth.UUID("C32225E6-5372-457A-885B-69ADA519C072"), bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY),
        (bluetooth.UUID("C32225E6-5372-457A-885B-69ADA519C073"), bluetooth.FLAG_WRITE),
    ))

    ( (_hr_handle,), (_raw_handle,), (_ota_cmd_handle, _ota_data_handle, _ota_nonce_handle, _ota_reply_handle) ) = \
        _ble.gatts_register_services((HR_SVC, RAW_SVC, OTA_SVC))
        
    _ble.irq(ble_irq)
    
    boot_nonce = os.urandom(noncelen)
    ota_buffer["nonce"] = boot_nonce
    _ble.gatts_write(_ota_nonce_handle, boot_nonce)

    payload = advertising_payload(name=syscfg.BTD_ADV_DVNM, services=[bluetooth.UUID(0x180D)])
    _ble.gap_advertise(100, adv_data=payload)
    
    syspr.log_print(dname, 0, "BTD: Radio Active. Hardware Synced.")
    
    local_counter = 0
    while True:
        startus = time.ticks_us()
        for t in base.running_tasks:
            if t["name"] == dname:
                t["last_tick"] = time.ticks_ms()
                break
        # Telemetry updates
        _ble.gatts_write(_hr_handle, struct.pack('<B', local_counter % 256))
        _ble.gatts_write(_raw_handle, struct.pack('<I', int(sensors.read_temp())))
        
        if _conn_handle is not None:
            _ble.gatts_notify(_conn_handle, _hr_handle)
            _ble.gatts_notify(_conn_handle, _raw_handle)
        
        local_counter += 1
        if local_counter > 255:
            local_counter = 0
        
        utilus = time.ticks_us() - startus
        loadratio = utilus / (TICK_WT_SEC * 1000 * 1000)
        for t in base.running_tasks:
            if t["name"] == dname:
                t["load"] = loadratio
                break
        await asyncio.sleep(TICK_WT_SEC)