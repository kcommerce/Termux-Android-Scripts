# Senior Caregiver Termux Hub (`termux-hub`)

A comprehensive, zero-friction senior care companion and remote caregiver dashboard system powered by Termux on Android devices (tested on Samsung Galaxy S7 Edge).

---

## 🌟 Pillars & Philosophy

The Senior Caregiver Termux Hub turns a repurposed Android smartphone into an automated safety and monitoring hub for elderly family members, requiring **zero physical interaction from the senior**.

1. **Microsoft Edge Neural TTS & Hourly Clock:** Speaks hourly chimes and routine reminders (medications, drinking water, meals) using Microsoft Edge Neural Text-to-Speech (`edge-tts` with `th-TH-PremwadeeNeural` voice) played via `termux-media-player`.
2. **Remote Intercom & Voice Broadcaster:** Caregiver voice drop-ins via high-volume voice announcements, WebRTC live audio streaming, custom MP3 playback, and Find Phone siren alarm.
3. **Remote Camera & Live Snapshot:** View front & rear camera hardware specifications (`termux-camera-info`), take live remote photos (`termux-camera-photo`), and view photo gallery history.
4. **Real-Time GPS & Safe Geofence Tracker:** Real-time satellite tracking with Leaflet.js interactive maps and safe boundary breach monitoring.
5. **Whitelist Telephony & Emergency Communications:** Speed-dial calling to whitelisted family contacts, remote SMS alerts, and real-time battery & 2-decimal temperature telemetry.
6. **Session Authentication & Dual Security:** Flask session protection (default `admin` / `admin123`) with full-screen login overlay, **System** tab for admin password updates, dual-port web access (HTTP 8888 / HTTPS 8443), and Dark/Light/Auto theme modes.

---

## 🏗 System Architecture & Data Flow

```
+-------------------------------------------------------------------------+
|        Caregiver Web Dashboard (HTTP Port 8888 / HTTPS Port 8443)       |
|            (Tailwind CSS + Leaflet.js + FontAwesome + Auth)             |
+-------------------------------------------------------------------------+
                                    |
                            HTTP / HTTPS REST
                                    v
+-------------------------------------------------------------------------+
|                    Flask Backend Application (app.py)                   |
|       (Session Auth + Concurrent HTTP 8888/HTTPS 8443 + Edge Neural TTS) |
+-------------------------------------------------------------------------+
                                    |
                           Async Subprocesses
                                    v
+-------------------------------------------------------------------------+
|                    Termux:API Binders & CLI Tools                       |
| (edge-tts-speak, termux-media-player, termux-camera-photo, termux-api)  |
+-------------------------------------------------------------------------+
                                    |
                           Android HAL & Sensors
                                    v
+-------------------------------------------------------------------------+
|                   Samsung Galaxy S7 Edge / Android OS                   |
+-------------------------------------------------------------------------+
```

---

## 🗣 Standalone CLI Speech Synthesizer (`edge-tts-speak`)

The hub includes a standalone CLI tool `edge-tts-speak` deployed to `~/bin/edge-tts-speak` and `/usr/bin/edge-tts-speak`:

```bash
# Speak Thai neural speech directly from Termux terminal:
edge-tts-speak "สวัสดีค่ะ ข้าพเจ้าขอประกาศว่า ขณะนี้เป็นเวลา 20 นาฬิกา ในราชอาณาจักรไทย"

# Select voice model or rate adjustment:
edge-tts-speak -v th-TH-NiwatNeural -r "+10%" "ข้อความเสียงผู้ชาย"
```

---

## 🚀 Quick Deployment to Samsung S7 Edge

Deploy the backend server, caregiver dashboard, CLI utilities, prerequisite checkers, and autostart configurations directly over SSH/SCP:

```bash
# Execute deployment script (IP: 10.81.8.161, Port: 8022, User: root)
./termux-hub/deploy.sh 10.81.8.161 8022 root
```

### What `deploy.sh` does automatically:
1. Verifies SSH connectivity to `termux-s7` (`10.81.8.161:8022`).
2. Transfers `app.py`, `senior_caregiver_termux_hub.html`, `requirements.txt`, `edge-tts-speak`, `manage-service.sh`, `check-prerequisites.sh`, and `README.md` via `scp`.
3. Installs `python`, `termux-api`, `termux-tools`, `termux-services`, `openssl-tool`, and `edge-tts` on the device.
4. Installs `edge-tts-speak` CLI tool to `~/bin/edge-tts-speak` and `/usr/bin/edge-tts-speak`.
5. Configures `Termux:Boot` autostart script at `~/.termux/boot/start-eldercare-hub` with `termux-wake-lock`.
6. Launches the Flask server on **HTTP (8888)** and **HTTPS (8443)**.

---

## 🔍 System Readiness Diagnostic Tool (`check-prerequisites.sh`)

Check system software, Termux:API connections, Python modules, SSL certs, and network ports on the phone:

```bash
# Run interactively (prompts before installing missing packages):
~/eldercare-hub/check-prerequisites.sh

# Run non-interactively (automatically installs missing software):
~/eldercare-hub/check-prerequisites.sh -y
```

---

## ⚙️ Post-Reboot Persistence (`Termux:Boot`)

To guarantee the service starts automatically after an Android reboot:

1. Ensure **Termux:Boot** app is installed on the phone.
2. Ensure battery optimization for Termux & Termux:Boot is set to **No restrictions**.
3. Open **Termux:Boot** app once manually to register autostart permissions.

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
| `/api/auth-check` | `GET` | Checks session authentication status |
| `/api/login` | `POST` | Authenticates user session |
| `/api/logout` | `POST` | Ends user session |
| `/api/change-password` | `POST` | Updates admin password |
| `/api/status` | `GET` | Returns battery, location, contacts, phone name, network info, device model, and settings |
| `/api/phone-name` | `GET`/`POST` | Fetches or updates and persists custom phone/senior name |
| `/api/tts` | `POST` | Speaks message aloud via Microsoft Edge Neural TTS (`edge-tts`) |
| `/api/intercom` | `POST` | Broadcasts high-volume voice announcement |
| `/api/camera/info` | `GET` | Returns hardware camera specifications (`termux-camera-info`) |
| `/api/camera/snap` | `POST` | Captures JPEG photo using front/rear camera (`termux-camera-photo`) |
| `/api/camera/photos` | `GET` | Lists captured photo history |
| `/api/camera/photo/<filename>` | `GET`/`DELETE` | Serves or deletes stored snapshot image |
| `/api/siren` | `POST` | Triggers Find Phone siren alarm and LED strobe |
| `/api/torch` | `POST` | Toggles flashlight on/off |
| `/api/vibrate` | `POST` | Triggers vibration alert |
| `/api/location` | `GET` | Fetches current GPS/Network coordinates |
| `/api/call` | `POST` | Dials phone number via `termux-telephony-call` |
| `/api/sms` | `POST` | Sends SMS via `termux-sms-send` |
| `/api/contacts` | `GET`/`POST` | Manages whitelisted family contact list |
| `/api/routines` | `GET`/`POST` | Manages scheduled routine reminders |
| `/api/logs` | `GET` | Retrieves real-time execution log stream |