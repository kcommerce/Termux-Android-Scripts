# Senior Caregiver Termux Hub (`termux-hub`)

A comprehensive, zero-friction senior care companion and remote caregiver dashboard system powered by Termux on Android devices (tested on Samsung Galaxy S7 Edge).

---

## 🌟 Pillars & Philosophy

The Senior Caregiver Termux Hub turns a repurposed Android smartphone into an automated safety and monitoring hub for elderly family members, requiring **zero physical interaction from the senior**.

1. **Hourly Talking Clock & Contextual Routine Reminders:** Speaks hourly chimes and routine reminders (medications, drinking water, meals) via Google TTS (`-l th`).
2. **Remote Sound & Intercom Broadcaster:** Enables caregivers to drop-in via high-volume voice announcements, custom MP3 playback, or sound a Find Phone siren alarm.
3. **Real-Time GPS & Safe Geofence Tracker:** Tracks GPS location in real time with a Leaflet.js interactive map and geofence safe zone monitoring.
4. **Device Help & Hardware Playground:** Haptic vibration diagnostic patterns, LED torch strobe tests, and hardware alarm triggers.
5. **Whitelist Telephony & Emergency Communications:** Direct speed-dial calling to whitelisted contacts, target contact SMS alerts, and real-time battery & 2-decimal temperature telemetry.
6. **Dual HTTP/HTTPS Security & Theme Customization:** Dual-port web access (HTTP 8888 / HTTPS 8443 with self-signed SSL), customizable phone/senior name, and Dark/Light/Auto theme modes.

---

## 🏗 System Architecture & Data Flow

```
+-------------------------------------------------------------------------+
|        Caregiver Web Dashboard (HTTP Port 8888 / HTTPS Port 8443)       |
|                (Tailwind CSS + Leaflet.js + FontAwesome)                |
+-------------------------------------------------------------------------+
                                    |
                            HTTP / HTTPS REST
                                    v
+-------------------------------------------------------------------------+
|                    Flask Backend Application (app.py)                   |
|          (Concurrent HTTP 8888 + HTTPS 8443 + SSL Cert Auto-Gen)        |
+-------------------------------------------------------------------------+
                                    |
                           Async Subprocesses
                                    v
+-------------------------------------------------------------------------+
|                          Termux:API Binders                             |
| (termux-tts-speak, termux-volume, termux-location, termux-telephony)   |
+-------------------------------------------------------------------------+
                                    |
                           Android HAL & Sensors
                                    v
+-------------------------------------------------------------------------+
|                   Samsung Galaxy S7 Edge / Android OS                   |
+-------------------------------------------------------------------------+
```

---

## 🚀 Quick Deployment to Samsung S7 Edge

Deploy the backend server, caregiver dashboard, prerequisite checkers, and autostart configurations directly over SSH/SCP:

```bash
# Execute deployment script (IP: 10.81.8.161, Port: 8022, User: root)
./termux-hub/deploy.sh 10.81.8.161 8022 root
```

### What `deploy.sh` does automatically:
1. Verifies SSH connectivity to `termux-s7` (`10.81.8.161:8022`).
2. Transfers `app.py`, `senior_caregiver_termux_hub.html`, `requirements.txt`, `manage-service.sh`, `check-prerequisites.sh`, and `README.md` via `scp`.
3. Installs `python`, `termux-api`, `termux-tools`, `termux-services`, and `openssl-tool` on the device.
4. Configures a Python virtual environment (`venv`) and installs dependencies.
5. Configures `Termux:Boot` autostart script at `~/.termux/boot/start-eldercare-hub` with `termux-wake-lock`.
6. Launches the Flask server on **HTTP (8888)** and **HTTPS (8443)**.

---

## 🔍 System Readiness Diagnostic Tool (`check-prerequisites.sh`)

Check all required system software, Termux:API connections, Python modules, SSL certs, and network ports on the phone:

```bash
# Run interactively (prompts before installing missing packages):
~/eldercare-hub/check-prerequisites.sh

# Run non-interactively (automatically installs missing software):
~/eldercare-hub/check-prerequisites.sh -y
```

### What `check-prerequisites.sh` checks:
- **Core Binaries:** `python3`, `pip`, `openssl` (via `openssl-tool`), `curl`, `termux-wake-lock`, `netstat`/`ss`.
- **Termux:API CLI Tools & Connection:** `termux-battery-status`, `termux-location`, `termux-tts-speak`, `termux-vibrate`, `termux-torch`, `termux-telephony-call`, `termux-sms-send`, `termux-media-player`, `termux-notification`, `termux-volume`, plus live Android OS communication check.
- **Python Modules:** `flask`, `requests`, `pydantic`, `werkzeug`.
- **Directories & SSL:** `~/.config/eldercare`, `~/.config/eldercare/sounds`, `~/.termux/boot`, `cert.pem`, `key.pem`.
- **Network Ports:** HTTP `8888` and HTTPS `8443` binding status.

---

## ⚙️ Post-Reboot Persistence (`Termux:Boot`)

To guarantee the service starts automatically after an Android reboot:

1. Ensure **Termux:Boot** app is installed on the phone.
2. Ensure battery optimization for Termux & Termux:Boot is set to **No restrictions**.
3. Open **Termux:Boot** app once manually to register autostart permissions.
4. The deployment script creates `~/.termux/boot/start-eldercare-hub`:

```bash
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
mkdir -p $HOME/.config/eldercare
cd $HOME/eldercare-hub
if [ -d "venv" ]; then
    source venv/bin/activate
fi
export PORT=8888
export HTTPS_PORT=8443
export HOST=0.0.0.0
python3 app.py >> $HOME/.config/eldercare/app.log 2>&1 &
```

---

## 🛠 Operations & Maintenance (O&M) Script

Manage the service locally or remotely over SSH using `./manage-service.sh`:

### Local Commands (On Phone):
```bash
./manage-service.sh status     # Check process PID, HTTP 8888, HTTPS 8443, and API health
./manage-service.sh start      # Start backend server with termux-wake-lock
./manage-service.sh stop       # Stop running backend server
./manage-service.sh restart    # Restart backend server
./manage-service.sh enable     # Enable autostart on reboot
./manage-service.sh disable    # Disable autostart on reboot
./manage-service.sh logs       # Tail live server execution logs
```

### Remote Commands (From Mac/PC over SSH):
```bash
./manage-service.sh -r termux-s7 status
./manage-service.sh -r termux-s7 restart
./manage-service.sh -r termux-s7 logs
```

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Serves Caregiver Web Dashboard HTML |
| `/api/status` | `GET` | Returns battery status, location cache, contacts, phone name, and settings |
| `/api/phone-name` | `POST` | Updates and persists custom phone/senior name |
| `/api/tts` | `POST` | Speaks message aloud via `termux-tts-speak` (`-l th`) |
| `/api/intercom` | `POST` | Broadcasts high-volume voice announcement |
| `/api/siren` | `POST` | Triggers Find Phone siren alarm and LED strobe |
| `/api/torch` | `POST` | Toggles flashlight on/off |
| `/api/vibrate` | `POST` | Triggers vibration alert |
| `/api/location` | `GET` | Fetches current GPS/Network coordinates |
| `/api/call` | `POST` | Dials phone number via `termux-telephony-call` |
| `/api/sms` | `POST` | Sends SMS via `termux-sms-send` |
| `/api/contacts` | `GET`/`POST` | Manages whitelisted family contact list |
| `/api/routines` | `GET`/`POST` | Manages scheduled routine reminders |
| `/api/logs` | `GET` | Retrieves real-time execution log stream |