# LuceBase

LuceBase is a MicroPython-based, kernel-like framework for rapidly building
firmware for small, resource-constrained devices (targeting the Raspberry Pi
Pico 2 / RP2040). It handles the parts every device needs: async task
scheduling, a terminal/CLI, BLE, boot mode management, and signed,
cloud-driven firmware upgrades, so that building a new device becomes
"add a daemon," not "build all from scratch."

LuceBase (and LuceFirmware projects in general) is developed for my personal IoT and RC remotes first. LuceBase is a result of trying to reduce the redundant work I do every single time I have a new device idea.

> **Status:** This project is currently **in development / draft**. Core (task scheduler, boot modes, terminal,
> OTA/recovery flow) is implemented and running on hardware. This repo is for the
> LuceBase, the device-specific logic (sensors, RF, control loops) lives in
> separate Variant Firmwares built on top of it.

## LuceBase Structure: Base + Variant = Firmware

LuceBase follows a strict distinction between the base and the device-specific features and utilities: **one base, many devices (variants).**

- **LuceBase (this repo)**: This is the shared core. It includes task scheduling, terminal,
  Bluetooth LE, boot mode logic, and the signed OTA/recovery pipeline. Shared
  across all devices.
- **Variant Firmwares**: These are the product-specific firmware that are built *on* LuceBase by adding a
  handful of device-specific daemons and a `syscfg.py`/`usrcfg.py` pair. For example, a
  thermostat could add a `heatingd.py`, and an RC remote can add RF/IR daemons. All of the features that the base has are inherited automatically. 
  
This means every device built on LuceBase gets async task management, crash
isolation, a terminal, and signed OTA upgrades without having to reimplement
any of it. The only code a new Variant needs to write is the logic that
makes that specific device do its specific job.

### Boot modes

LuceBase boots into one of three modes, chosen by a `BootTo` flag persisted
in `bcfg.txt`:

| Mode | Purpose |
|------|---------|
| **normal** | Normal, full boot. All Variant daemons, BLE, and OTA-over-BLE daemons are started. |
| **rec** (Recovery) | Only the terminal and `rcuutil` (recovery CLI) load. Recovery mode allows, well, the recovery of the device if something behaves weirdly, and it also allows the device to receive and stage a signed firmware upgrade bundle. Firmware upgrades are only staged, not replaced yet. |
| **fwu** (Firmware Upgrade) | Only the terminal and the FWU worker load. The worker verifies staged files and atomically replaces old files with new ones by renaming the replacement files. |

Modes can be changed using the built-in `terminalc bcfg set-boot <mode>` command.

### Task scheduler

`main.py` runs each daemon (`terminald`, `heartbeatd`, `battd`, `btd`, a
Variant's own daemons, etc.) as an async task. The supervisor:

- Measures each daemon's live RAM usage on startup.
- Tracks per-task load and last-tick time (similar in spirit to OS process
  accounting).
- Isolates crashes and faults. A daemon that throws an error is marked `CRASHED` without taking
  down the rest of the system, and cancellation is handled cleanly so
  hardware and GPIO is left in a safe state. Same applies when a user explciity stops a daemon from running by using the `kill` command.

## Firmware Upgrades

Every upgrade (both OTA or serial)
goes through the same verification pipeline before a single file changes:

1. **Firmware Upgrade Manifest:** A signed manifest describing the upgrade (version,
   build numbers, list of files, a nonce) is sent and verified before any
   file content is accepted.
2. **HMAC-SHA256 signing:** Both the manifest and every individual upgrade asset are
   signed with HMAC-SHA256. Each file's signature also binds in the device's
   current boot nonce and filename, so a signed blob can't be replayed
   against a different file or a different boot session.
3. **Per-boot nonce:** A fresh nonce is generated every boot. Since file
   signatures are computed as Payload + Nonce, a captured upgrade
   session cannot be replayed after a reboot.
4. **(Optional) Downgrade Prevention:** Upgrade bundles with an equal or older build number
   than the currently running firmware can be rejected.
5. **Atomic Operations:** Verified files are staged with a `.upd` suffix. The
   FWU worker only renames them into place after every file in the manifest
   has been received and verified. The rename step itself is
   also power-loss safe: if power is lost mid-upgrade, the worker resumes and
   finishes the rename on next boot rather than corrupting the firmware.

### Server-side personalization

The signing key used to verify upgrades (`FW_OTA_SIGN_PBK` in `syscfg.py`)
is a placeholder in this repo. In a real deployment, each device's
`syscfg.py` is created on-the-fly with an actual key during a **personalization**
step, managed by a firmware cloud server that tracks the fleet of deployed
devices. This key is called as Device-Specific Signing Key (DSSK) and it is designed to change between every device. Further implementations will also consider asymmetrical signature validation.

## Building a Variant

A Variant is LuceBase plus:

1. A `syscfg.py` describing the hardware/product identity (`FW_HW_MODEL`,
   `CF_STRING` etc.).
2. One or more daemons implementing device-specific behavior (like
   `heatingd.py` for a thermostat), following the same async task pattern as
   `battd.py` or `btd.py`.
3. Registration of those daemons in the main task scheduling controller.

Everything else (such as the terminal, boot modes, OTA security, task supervision and other features) is
inherited.

## Repository layout

| File | Role |
|------|------|
| `boot.py` | Basic Boot Handler. Reads `bcfg.txt`, decides boot mode, hands off to `main.py`. |
| `main.py` | Task scheduler / supervisor. |
| `terminald.py` / `terminalc.py` | Serial terminal daemon and command controller. |
| `rcuutil.py` | Recovery-mode utilities. Able to verify and stage signed upgrade bundles. |
| `fwu_worker.py` | Firmware Upgrade Worker |
| `b_utils.py` | Boot configuration read/write helpers. |
| `syscfg.py` | Hardcoded, per-Variant identity and security config. |
| `usrcfg.py` | Runtime, user-modifiable settings (JSON-backed). |
| `btd.py` / `ble_advertising.py` | Bluetooth LE daemon and advertising helpers. |
| `battd.py`, `sensors.py`, `heartbeatd.py`, `diags.py`| Supporting daemons/utilities. |

## Further Improvements

LuceBase is still in active development. In the future, I plan to add the following too:
  
- **Asymmetrical Signing Key**: Similar to DSSK, but will be asymmetrical so multiple devices can be managed with a single private key. 
- **Full Documentation**: A longer documentation that would include much more details on the implementation, the actual command-line examples and more.

## Disclaimer

LuceBase is a personal systems project, being built and developed in my personal free-time. Although it is functional and running on real hardware (testing it on Raspberry Pi Pico 2 W), of course it should be treated as a prototype, and not as a
production-hardened or production-tested firmware base.

