# E32 Flight Guide

Windows PC ground control station for INAV flight controllers connected through two LoRa E32 serial modules.

The E32 pair is used as a transparent serial bridge:

```text
INAV FC UART/MSP -> LoRa E32 air <RF> LoRa E32 ground -> USB-UART -> Windows COM port
```

The app is built with Python, PySide6, pyserial, Qt WebEngine and Leaflet/OpenStreetMap.

## Features

- Connect to an INAV flight controller through a Windows COM port.
- Poll and display live MSP telemetry:
  - API version
  - GPS fix and satellite count
  - latitude and longitude
  - altitude
  - ground speed
  - battery voltage
  - ARM state
  - current navigation mode
  - link latency and RX/TX counters
- Online Leaflet map using OpenStreetMap tiles through a local Python tile proxy.
- Satellite layer through Esri imagery, also routed through the local tile proxy.
- Click on the map to add mission waypoints.
- Edit waypoint type, coordinate, altitude and INAV parameters.
- Delete a selected waypoint.
- Add mission command actions:
  - `SET_HEAD`
  - `JUMP`
  - `RTH`
- Save and load `.mission` files.
- Fetch mission from FC.
- Upload mission to FC.
- Write mission to EEPROM.
- Automatically verify uploaded mission by fetching it back from FC and comparing all MSP waypoint fields.
- Show MSP command rejection packets from the FC.

## Current Flight Scope

This app can upload and verify missions, but it does not arm the aircraft or switch INAV flight modes by itself.

For real flight, ARM and NAV/MISSION mode should still be controlled from your radio transmitter or another approved INAV mode switch setup.

Recommended workflow:

```text
Plan mission in app
Upload mission
Wait for MISSION VERIFIED
Check GPS fix and battery
Use radio to ARM
Use radio to enable NAV WP / MISSION mode
Monitor mission from app
```

## Requirements

- Windows 10 or Windows 11
- Python 3.10 or newer
- INAV flight controller with MSP enabled on one UART
- Two configured LoRa E32 modules
- USB-UART adapter on the ground side
- Internet access for online map tiles

Python dependencies:

```text
PySide6>=6.7
pyserial>=3.5
```

## Installation

Open PowerShell:

```powershell
cd D:\mpfpv\e32-gcs-pyqt
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the app:

```powershell
python -m app.main
```

If you run from another folder, use:

```powershell
cd D:\mpfpv\e32-gcs-pyqt
python -m app.main
```

Do not run `app/main.py` directly from inside the `app` folder. Use `python -m app.main` so Python can resolve the `app` package correctly.

## LoRa E32 Setup

Both E32 modules must use compatible settings:

- Same channel.
- Same air data rate.
- Same address mode or transparent/broadcast mode.
- UART baud rate matching the baud selected in the app.
- Normal mode on M0/M1.
- FC UART must have MSP enabled in INAV.

Typical initial app baud:

```text
57600
```

If telemetry is unstable or mission upload fails, try:

- lower baud rate,
- lower E32 air data rate,
- better antennas,
- shorter initial test distance,
- ensure FC TX/RX are crossed correctly with the air-side E32 UART.

## Basic Use

1. Power the FC and both LoRa E32 modules.
2. Connect the ground E32 module to Windows through USB-UART.
3. Start the app.
4. Select the COM port.
5. Select the baud rate.
6. Click `Connect`.
7. Wait for:

```text
MSP response received. FC and GCS are communicating.
```

If the app shows `No MSP`, check:

- selected COM port,
- selected baud rate,
- INAV UART MSP setting,
- TX/RX wiring,
- E32 channel/settings,
- E32 M0/M1 mode pins.

## Map

The app uses a bundled local Leaflet library and loads map tiles through a local proxy:

```text
http://127.0.0.1:8787/tiles/map/{z}/{x}/{y}.png
http://127.0.0.1:8787/tiles/sat/{z}/{x}/{y}.png
```

The proxy is started automatically by the app.

Use `Check Map` to test:

- local map tile proxy,
- local satellite tile proxy,
- OpenStreetMap upstream access,
- Esri upstream access.

If the map is black:

1. Close all old app windows.
2. Start again with `python -m app.main`.
3. Click `Check Map`.
4. Check the log panel for `Map tile loaded` or `Map tile failed`.

## Mission Planning

Click on the map to add waypoints.

Each waypoint can be edited in the left panel:

- `Type`
  - `WAYPOINT`
  - `PH_TIME`
  - `POI`
  - `LAND`
- `Lat`
- `Lon`
- `Alt`
- `P1`
- `P2`
- `P3`

The `Command Action` section can attach one action to the selected waypoint:

- `SET_HEAD`
- `JUMP`
- `RTH`

Useful INAV parameter notes:

- `SET_HEAD p1 = -1` cancels heading control.
- `SET_HEAD p1 = 0..360` sets heading.
- `JUMP p1` is the target waypoint number.
- `JUMP p2 = -1` repeats forever.
- `JUMP p2 >= 1` repeats a fixed number of times.

## Mission Buttons

`Save`

Save the current mission to a `.mission` file.

`Load`

Load a `.mission` file into the app.

`Fetch`

Read the current mission from FC memory.

`Upload`

Upload the current mission to FC memory, save it and automatically verify it.

Expected successful log:

```text
Uploading X mission item(s) to FC...
Mission upload complete. Starting FC verification...
Verifying mission from FC...
FC reports X mission item(s)
Mission loaded from FC: X waypoint(s)
MISSION VERIFIED: X item(s) match FC memory
```

`EEPROM`

Send `MSP_EEPROM_WRITE` to the FC.

`Clear`

Clear the mission in the app UI only.

`Delete WP`

Delete the selected waypoint from the app mission list.

## Upload Verification

After upload, the app fetches the mission back from FC and compares:

- waypoint number,
- INAV action code,
- latitude,
- longitude,
- altitude,
- P1,
- P2,
- P3,
- final waypoint flag.

If verification fails, the app prints the mismatched item in the log. Do not fly the mission until upload verification passes.

## Project Layout

```text
app/
  core/
    msp.py              MSP v1 packet builder and binary helpers
    msp_parser.py       MSP stream parser and telemetry decoder
    telemetry_state.py  Live telemetry state model

  transport/
    serial_worker.py    COM port connection, polling and serial IO

  mission/
    mission_model.py    Mission and action data models
    mission_file.py     .mission save/load
    mission_msp.py      INAV MSP mission fetch/upload/verify
    mission_validator.py

  map/
    map.html            Leaflet map UI
    map_view.py         Qt WebEngine bridge
    tile_proxy.py       Local map/satellite tile proxy
    vendor/leaflet/     Bundled Leaflet JS/CSS

  ui/
    main_window.py      Main app window
    mission_panel.py    Mission editor
    telemetry_panel.py  Telemetry strip
    log_panel.py        Runtime log panel
    theme.py            Dark UI stylesheet
```

## Safety Notes

- Test with props removed first.
- Verify telemetry before mission upload.
- Verify mission upload before arming.
- Keep manual RC control available.
- Do not rely on the app as the only failsafe.
- Configure INAV failsafe, RTH and geofence separately in INAV.
- Confirm GPS fix and home position before enabling mission mode.

## Known Limitations

- The app does not arm the FC.
- The app does not switch INAV modes.
- Map requires internet access unless offline tile support is added later.
- Telemetry parser currently covers the main fields only.
- It does not yet show detailed INAV arming disabled reasons or full navigation error states.
