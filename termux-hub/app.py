#!/usr/bin/env python3
"""
Senior Caregiver Termux Hub - Flask Backend Server
===================================================
Provides REST API endpoints to interface with Android hardware via Termux:API,
serves the Caregiver Web Dashboard, handles MP3 uploads & deletion, routine MP3 associations,
enforces Google TTS with Thai language parameter '-l th', and maps real GPS coordinates.
"""

import os
import sys
import json
import time
import subprocess
import threading
import logging
from datetime import datetime
import shutil
from typing import Dict, Any, Optional, List

from flask import Flask, request, jsonify, send_file, send_from_directory, session
from werkzeug.utils import secure_filename

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TermuxHub")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "senior_caregiver_termux_hub.html")
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "eldercare")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
SOUNDS_DIR = os.path.join(CONFIG_DIR, "sounds")
TALKING_CLOCK_DIR = os.path.join(SOUNDS_DIR, "talking-clock")
PHOTOS_DIR = os.path.join(CONFIG_DIR, "photos")
CERT_FILE = os.path.join(CONFIG_DIR, "cert.pem")
KEY_FILE = os.path.join(CONFIG_DIR, "key.pem")

os.makedirs(SOUNDS_DIR, exist_ok=True)
os.makedirs(TALKING_CLOCK_DIR, exist_ok=True)
os.makedirs(PHOTOS_DIR, exist_ok=True)

def get_talking_clock_mp3_path(hour: int) -> Optional[str]:
    filename = f"{hour:02d}-00.mp3"
    candidates = [
        os.path.join(TALKING_CLOCK_DIR, filename),
        os.path.join(SOUNDS_DIR, filename),
        os.path.join(BASE_DIR, "talking-clock", filename),
        os.path.join(BASE_DIR, "..", "talking-clock", filename),
    ]
    for cand in candidates:
        if os.path.exists(cand):
            return cand
    return None

# Enforce Google Text-to-speech Engine System-Wide with Thai language
GOOGLE_TTS_ENGINE = "com.google.android.tts"
DEFAULT_TTS_LANG = "th"

app = Flask(__name__, static_folder=BASE_DIR)
app.secret_key = "termux_hub_admin_secret_key_2026"

@app.before_request
def require_authentication():
    if request.method == "OPTIONS":
        return "", 200

    path = request.path
    if path in ["/", "/index.html", "/favicon.ico", "/api/login", "/api/auth-check"]:
        return None
    if not path.startswith("/api/"):
        return None

    if not session.get("user"):
        return jsonify({"success": False, "error": "Unauthorized. Please log in.", "auth_required": True}), 401

# Enable CORS for all routes manually
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response

# In-memory System Logs Buffer (capped at 100 entries)
system_logs: List[Dict[str, Any]] = []

def log_system_event(tag: str, cmd_str: str, returncode: int = 0, stdout: str = "", stderr: str = "", details: Any = None):
    """Logs execution details and commands to in-memory system log stream."""
    entry = {
        "id": f"log_{int(time.time() * 1000)}",
        "timestamp": datetime.now().isoformat(),
        "time_str": datetime.now().strftime("%H:%M:%S"),
        "tag": tag,
        "cmd": cmd_str,
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "details": details
    }
    system_logs.append(entry)
    if len(system_logs) > 100:
        system_logs.pop(0)

# ==============================================================================
# Helper Function for Executing Termux Commands
# ==============================================================================
def run_termux_cmd(cmd: list, timeout: int = 12) -> Dict[str, Any]:
    """Execute a termux-api CLI command synchronously with error handling and log recording."""
    cmd_str = " ".join(cmd)
    logger.info(f"Executing command: {cmd_str}")
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True
        )
        output_str = proc.stdout.strip()
        error_str = proc.stderr.strip()

        if proc.returncode != 0:
            logger.warning(f"Command {cmd_str} exited with code {proc.returncode}: {error_str}")

        json_data = None
        if output_str.startswith("{") or output_str.startswith("["):
            try:
                json_data = json.loads(output_str)
            except json.JSONDecodeError:
                pass

        log_system_event(
            tag="TERMUX-CLI",
            cmd_str=cmd_str,
            returncode=proc.returncode,
            stdout=output_str,
            stderr=error_str,
            details=json_data
        )

        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": output_str,
            "stderr": error_str,
            "data": json_data
        }
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out after {timeout}s: {cmd_str}")
        log_system_event(tag="TIMEOUT", cmd_str=cmd_str, returncode=-1, stderr=f"Timed out after {timeout}s")
        return {"success": False, "error": f"Command timed out after {timeout}s"}
    except Exception as e:
        logger.error(f"Error executing {cmd_str}: {e}")
        log_system_event(tag="ERROR", cmd_str=cmd_str, returncode=-1, stderr=str(e))
        return {"success": False, "error": str(e)}

# ==============================================================================
# In-Memory State & Storage Helpers
# ==============================================================================
hub_state = {
    "clock_settings": {
        "enabled": True,
        "start_hour": 8,
        "end_hour": 20,
        "volume": 12,
        "rate": 1.0,
        "engine": GOOGLE_TTS_ENGINE,
        "language": DEFAULT_TTS_LANG,
        "message_preset": "ขณะนี้เวลา {hour} นาฬิกา อย่าลืมจิบน้ำและรับประทานยาตามเวลาค่ะ"
    },
    "routines": [
        {
            "id": "rt_1",
            "time": "08:30",
            "message": "ขณะนี้เวลา 8 นาฬิกา 30 นาที ได้เวลาทานยารอบเช้าและจิบน้ำแล้วค่ะ",
            "days": "EVERYDAY",
            "enabled": True,
            "mp3_file": ""
        },
        {
            "id": "rt_2",
            "time": "12:00",
            "message": "ขณะนี้เวลา 12 นาฬิกา ได้เวลารับประทานอาหารกลางวันแล้วค่ะ",
            "days": "EVERYDAY",
            "enabled": True,
            "mp3_file": ""
        },
        {
            "id": "rt_3",
            "time": "18:00",
            "message": "ขณะนี้เวลา 18 นาฬิกา ได้เวลาทานยารอบเย็นแล้วค่ะ",
            "days": "EVERYDAY",
            "enabled": True,
            "mp3_file": ""
        }
    ],
    "last_known_location": {
        "latitude": 13.924787,
        "longitude": 100.695719,
        "provider": "gps"
    },
    "last_fall_alert": None,
    "geofence": {
        "center_lat": 13.924787,
        "center_lng": 100.695719,
        "radius_meters": 500
    },
    "contacts": [
        {"id": "c1", "name": "Alex (Primary Caregiver)", "phone": "+66812345678"},
        {"id": "c2", "name": "Sarah (Daughter)", "phone": "+66898765432"}
    ],
    "find_phone_message": "โทรศัพท์อยู่ที่ไหน ฉันกำลังตามหาอยู่ โทรศัพท์อยู่ที่ไหน ฉันกำลังตามหาอยู่",
    "phone_name": "Grandma Evelyn",
    "auth": {
        "username": "admin",
        "password": "admin123"
    }
}

def format_battery_data(raw_data: Any) -> Dict[str, Any]:
    """Ensures battery temperature is rounded to exactly 2 decimal places."""
    data = raw_data if isinstance(raw_data, dict) else {}
    if "temperature" in data:
        try:
            data["temperature"] = round(float(data["temperature"]), 2)
        except Exception:
            data["temperature"] = 36.00
    else:
        data["temperature"] = 36.00

    if "percentage" not in data:
        data["percentage"] = 100
    if "plugged" not in data and "status" not in data:
        data["plugged"] = "PLUGGED_USB"
    return data

def load_settings():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
                hub_state.update(saved)
                hub_state["clock_settings"]["engine"] = GOOGLE_TTS_ENGINE
                hub_state["clock_settings"]["language"] = DEFAULT_TTS_LANG
                hub_state.setdefault("auth", {"username": "admin", "password": "admin123"})
                logger.info("Loaded settings from config file.")
        except Exception as e:
            logger.error(f"Error reading config: {e}")
    else:
        hub_state.setdefault("auth", {"username": "admin", "password": "admin123"})

def save_settings():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(hub_state, f, indent=2)
            logger.info("Saved settings to config file.")
    except Exception as e:
        logger.error(f"Error saving config: {e}")

# ==============================================================================
# Routes: Web Dashboard & Options Pre-flight & Authentication
# ==============================================================================
@app.route("/", methods=["GET"])
def get_dashboard():
    """Serves the caregiver web dashboard."""
    if os.path.exists(HTML_FILE):
        return send_file(HTML_FILE)
    return "<h2>Error: Dashboard HTML file not found</h2>", 404

@app.route("/<path:path>", methods=["OPTIONS"])
def handle_options(path):
    return "", 200

@app.route("/api/auth-check", methods=["GET"])
def check_auth_status():
    user = session.get("user")
    if user:
        return jsonify({"authenticated": True, "user": user})
    return jsonify({"authenticated": False})

@app.route("/api/login", methods=["POST"])
def login_route():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    auth_cfg = hub_state.get("auth", {"username": "admin", "password": "admin123"})
    if username == auth_cfg.get("username", "admin") and password == auth_cfg.get("password", "admin123"):
        session["user"] = username
        logger.info(f"User '{username}' logged in successfully.")
        return jsonify({"success": True, "message": "Login successful", "user": username})

    logger.warning(f"Failed login attempt for username: '{username}'")
    return jsonify({"success": False, "error": "Invalid username or password"}), 401

@app.route("/api/logout", methods=["POST"])
def logout_route():
    user = session.pop("user", None)
    logger.info(f"User '{user}' logged out.")
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route("/api/change-password", methods=["POST"])
def change_password_route():
    data = request.json or {}
    old_pw = data.get("old_password", "").strip()
    new_pw = data.get("new_password", "").strip()

    auth_cfg = hub_state.setdefault("auth", {"username": "admin", "password": "admin123"})
    if old_pw != auth_cfg.get("password", "admin123"):
        return jsonify({"success": False, "error": "Current password is incorrect"}), 400

    if not new_pw or len(new_pw) < 3:
        return jsonify({"success": False, "error": "New password must be at least 3 characters long"}), 400

    auth_cfg["password"] = new_pw
    save_settings()
    logger.info("Admin password changed successfully.")
    return jsonify({"success": True, "message": "Password changed successfully"})

# ==============================================================================
def get_device_model_info():
    """Queries actual hardware brand and model from Android system props."""
    res_model = run_termux_cmd(["getprop", "ro.product.model"], timeout=2)
    model = res_model.get("stdout", "").strip() or "Android Device"

    res_brand = run_termux_cmd(["getprop", "ro.product.brand"], timeout=2)
    brand = res_brand.get("stdout", "").strip()

    if "G935" in model or "g935" in model:
        friendly_name = "Samsung S7 Edge"
    elif brand and not model.lower().startswith(brand.lower()):
        friendly_name = f"{brand.capitalize()} {model}"
    else:
        friendly_name = model

    trimmed_name = friendly_name[:20].strip()
    return {
        "model": model,
        "brand": brand,
        "full_name": friendly_name,
        "display_name": trimmed_name
    }

def get_network_info():
    """Queries current network connection (WiFi or Cellular)."""
    res = run_termux_cmd(["termux-wifi-connectioninfo"], timeout=4)
    wifi_data = res.get("data")
    if not wifi_data and res.get("stdout"):
        try:
            wifi_data = json.loads(res["stdout"])
        except Exception:
            pass

    if wifi_data and isinstance(wifi_data, dict) and wifi_data.get("supplicant_state") == "COMPLETED" and wifi_data.get("ip") and wifi_data.get("ip") != "0.0.0.0":
        ssid = wifi_data.get("ssid", "").strip('"') or "WiFi"
        rssi = wifi_data.get("rssi", 0)
        return {
            "type": "wifi",
            "ssid": ssid,
            "rssi": rssi,
            "ip": wifi_data.get("ip"),
            "speed_mbps": wifi_data.get("link_speed_mbps", 0)
        }

    # Cellular / mobile data route check fallback
    route_res = run_termux_cmd(["ip", "route", "get", "1.1.1.1"], timeout=3)
    route_out = route_res.get("stdout", "")
    if "dev" in route_out:
        if "wlan" in route_out:
            return {"type": "wifi", "ssid": "WiFi Connected", "rssi": -60}
        else:
            return {"type": "cellular", "ssid": "Cellular Data", "rssi": -70}

    return {"type": "disconnected", "ssid": "Offline", "rssi": 0}

# ==============================================================================
# Routes: System Telemetry & Status
# ==============================================================================
@app.route("/api/status", methods=["GET"])
def get_system_status():
    """Fetches overall system battery, location cache, routines, device info, network info, and hub state."""
    battery_res = run_termux_cmd(["termux-battery-status"])
    battery_data = battery_res.get("data")
    if not battery_data and battery_res.get("stdout"):
        try:
            battery_data = json.loads(battery_res["stdout"])
        except Exception:
            battery_data = {"percentage": 100, "status": "OK", "temperature": 36.00}

    formatted_battery = format_battery_data(battery_data)

    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "battery": formatted_battery,
        "geofence": hub_state["geofence"],
        "clock_settings": hub_state["clock_settings"],
        "routines": hub_state["routines"],
        "contacts": hub_state.get("contacts", []),
        "last_known_location": hub_state["last_known_location"],
        "last_fall_alert": hub_state["last_fall_alert"],
        "phone_name": hub_state.get("phone_name", "Grandma Evelyn"),
        "device_info": get_device_model_info(),
        "network_info": get_network_info()
    })

@app.route("/api/phone-name", methods=["GET", "POST"])
def manage_phone_name():
    """Gets or updates and persists custom phone name to config file."""
    if request.method == "POST":
        data = request.get_json(force=True, silent=True) or {}
        name = data.get("phone_name", "").strip()
        if name:
            hub_state["phone_name"] = name
            save_settings()
            log_system_event("PHONE-NAME", f"Phone name updated to '{name}'")
            return jsonify({"success": True, "phone_name": name})
        return jsonify({"success": False, "error": "Phone name cannot be empty"}), 400

    return jsonify({"success": True, "phone_name": hub_state.get("phone_name", "Grandma Evelyn")})


@app.route("/api/logs", methods=["GET"])
def get_system_logs():
    """Returns recent system telemetry, CLI execution, and server log file lines."""
    file_lines = []
    log_file_path = os.path.join(CONFIG_DIR, "app.log")
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                file_lines = [l.strip() for l in lines[-100:] if l.strip()]
        except Exception:
            pass

    return jsonify({
        "success": True,
        "logs": system_logs,
        "file_logs": file_lines
    })

@app.route("/api/battery", methods=["GET"])
def get_battery_status():
    """Fetches real-time battery status via termux-battery-status with 2-decimal temperature."""
    res = run_termux_cmd(["termux-battery-status"])
    data = res.get("data")
    if not data and res.get("stdout"):
        try:
            data = json.loads(res["stdout"])
        except Exception:
            data = {"percentage": 100, "temperature": 36.00}

    formatted_battery = format_battery_data(data)
    res["data"] = formatted_battery
    return jsonify(res)

# ==============================================================================
# Routes: Speech & TTS Controls (Always Google TTS with '-l th')
# ==============================================================================
@app.route("/api/tts/engines", methods=["GET"])
def get_tts_engines():
    """Queries available TTS engines installed on the Android device."""
    res = run_termux_cmd(["termux-tts-engines"])
    engines = res.get("data")
    if not engines and res.get("stdout"):
        try:
            engines = json.loads(res["stdout"])
        except Exception:
            engines = []

    if not engines:
        engines = [
            {"name": GOOGLE_TTS_ENGINE, "label": "Google Text-to-speech Engine", "default": True}
        ]
    else:
        for eng in engines:
            eng["default"] = (eng.get("name") == GOOGLE_TTS_ENGINE)

    return jsonify({"success": True, "engines": engines, "default_engine": GOOGLE_TTS_ENGINE, "language": DEFAULT_TTS_LANG})

def speak_text_sync(text: str, rate: str = "1.0") -> Dict[str, Any]:
    """
    Synthesizes and speaks text using termux-tts-speak (-e com.google.android.tts -l th).
    """
    clean_msg = text.strip('"').strip("'")
    if not clean_msg:
        return {"success": False, "error": "Empty message"}

    cmd = ["termux-tts-speak", "-e", GOOGLE_TTS_ENGINE, "-l", DEFAULT_TTS_LANG, "-r", str(rate), clean_msg]
    log_system_event("TTS-SPEAK", f"Spoke via Google TTS: '{clean_msg}'")
    return run_termux_cmd(cmd)

@app.route("/api/tts", methods=["POST"])
def speak_tts():
    """Sets volume and speaks text aloud using Google TTS (termux-tts-speak)."""
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "ทดสอบการพูดด้วยเสียง")
    rate = str(data.get("rate", 1.0))
    volume = str(data.get("volume", 12))

    run_termux_cmd(["termux-volume", "music", volume])
    clean_msg = message.strip('"')
    res = speak_text_sync(clean_msg, rate=rate)
    return jsonify(res)

@app.route("/api/clock/test", methods=["POST"])
def test_clock_chime():
    """Plays the fixed hourly chime MP3 (HH-MM.mp3) for current or requested hour."""
    data = request.get_json(force=True, silent=True) or {}
    hour = data.get("hour")
    if hour is None:
        hour = datetime.now().hour
    else:
        try:
            hour = int(hour)
        except (ValueError, TypeError):
            hour = datetime.now().hour

    volume = str(data.get("volume", hub_state["clock_settings"].get("volume", 12)))
    mp3_path = get_talking_clock_mp3_path(hour)
    filename = f"{hour:02d}-00.mp3"

    run_termux_cmd(["termux-volume", "music", volume])
    if mp3_path and os.path.exists(mp3_path):
        run_termux_cmd(["termux-media-player", "stop"], timeout=2)
        res = run_termux_cmd(["termux-media-player", "play", mp3_path])
        log_system_event("TALKING-CLOCK", f"Tested hourly chime MP3: {filename}")
        return jsonify({"success": True, "file": filename, "path": mp3_path, "result": res})
    else:
        fallback_msg = f"ขณะนี้เวลา {hour} นาฬิกา"
        res = speak_text_sync(fallback_msg)
        log_system_event("TALKING-CLOCK", f"Hourly chime MP3 missing for hour {hour:02d}, used TTS fallback")
        return jsonify({"success": True, "file": filename, "fallback_tts": True, "result": res})

@app.route("/api/clock/settings", methods=["POST"])
def update_clock_settings():
    """Updates the Talking Clock routine schedule settings."""
    data = request.get_json(force=True, silent=True) or {}
    hub_state["clock_settings"].update(data)
    hub_state["clock_settings"]["engine"] = GOOGLE_TTS_ENGINE
    hub_state["clock_settings"]["language"] = DEFAULT_TTS_LANG
    save_settings()
    return jsonify({"status": "success", "settings": hub_state["clock_settings"]})

# ==============================================================================
# Routes: Custom Routine Scheduler Management & Playback
# ==============================================================================
@app.route("/api/routines", methods=["GET"])
def get_routines():
    """Lists all configured custom routine reminders."""
    return jsonify({"success": True, "routines": hub_state.get("routines", [])})

@app.route("/api/routines", methods=["POST"])
def save_routine():
    """Adds a new custom routine or updates an existing one."""
    data = request.get_json(force=True, silent=True) or {}
    routine_id = data.get("id") or f"rt_{int(time.time())}"
    time_str = data.get("time", "08:00")
    message = data.get("message", "Routine reminder")
    days = data.get("days", "EVERYDAY")
    enabled = data.get("enabled", True)
    mp3_file = data.get("mp3_file", "")

    routines = hub_state.setdefault("routines", [])
    updated = False
    for rt in routines:
        if rt["id"] == routine_id:
            rt["time"] = time_str
            rt["message"] = message
            rt["days"] = days
            rt["enabled"] = enabled
            rt["mp3_file"] = mp3_file
            updated = True
            break

    if not updated:
        routines.append({
            "id": routine_id,
            "time": time_str,
            "message": message,
            "days": days,
            "enabled": enabled,
            "mp3_file": mp3_file
        })

    save_settings()
    return jsonify({"success": True, "routines": hub_state["routines"]})

@app.route("/api/routines/toggle", methods=["POST"])
def toggle_routine():
    """Toggles enabled status of a specific routine reminder."""
    data = request.get_json(force=True, silent=True) or {}
    routine_id = data.get("id")
    enabled = data.get("enabled")

    for rt in hub_state.get("routines", []):
        if rt["id"] == routine_id:
            rt["enabled"] = enabled if enabled is not None else not rt["enabled"]
            break

    save_settings()
    return jsonify({"success": True, "routines": hub_state["routines"]})

@app.route("/api/routines/play/<routine_id>", methods=["POST"])
def play_routine_now(routine_id):
    """Immediately triggers a custom routine reminder (Google TTS '-l th' + associated MP3)."""
    routine = None
    for rt in hub_state.get("routines", []):
        if rt["id"] == routine_id:
            routine = rt
            break

    if not routine:
        return jsonify({"success": False, "error": f"Routine {routine_id} not found"}), 404

    volume = str(hub_state["clock_settings"].get("volume", 12))
    rate = str(hub_state["clock_settings"].get("rate", 1.0))
    msg = routine.get("message", "")
    mp3 = routine.get("mp3_file", "")

    run_termux_cmd(["termux-volume", "music", volume])
    clean_msg = msg.strip('"')
    res = speak_text_sync(clean_msg, rate=rate)

    if mp3:
        mp3_path = os.path.join(SOUNDS_DIR, secure_filename(mp3))
        if os.path.exists(mp3_path):
            time.sleep(1)
            run_termux_cmd(["termux-media-player", "play", mp3_path])

    return jsonify({"success": True, "routine": routine, "tts_result": res})

@app.route("/api/routines/<routine_id>", methods=["DELETE"])
def delete_routine(routine_id):
    """Deletes a custom routine reminder by ID."""
    hub_state["routines"] = [rt for rt in hub_state.get("routines", []) if rt["id"] != routine_id]
    save_settings()
    return jsonify({"success": True, "routines": hub_state["routines"]})

# ==============================================================================
# Routes: Module 2 - Intercom & Siren Alarm
# ==============================================================================
@app.route("/api/intercom", methods=["POST"])
def broadcast_intercom():
    """Broadcasts high-priority caregiver voice message using Google TTS '-l th'."""
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "ข้อความจากผู้ดูแล")
    rate = str(data.get("rate", 1.0))

    run_termux_cmd(["termux-volume", "music", "15"])
    run_termux_cmd(["termux-vibrate", "-d", "300", "-f"])

    clean_msg = message.strip('"')
    res = speak_text_sync(f"ประกาศจากผู้ดูแล: {clean_msg}", rate=rate)
    return jsonify(res)

@app.route("/api/intercom/live-stream", methods=["POST"])
def live_stream_intercom():
    """Receives WebRTC / MediaRecorder live audio stream blob, saves to live_intercom.webm, and plays immediately on phone speaker."""
    if "audio" not in request.files:
        return jsonify({"success": False, "error": "No audio blob provided"}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"success": False, "error": "Empty audio file name"}), 400

    target_path = os.path.join(SOUNDS_DIR, "live_intercom.webm")
    audio_file.save(target_path)
    file_size = os.path.getsize(target_path)
    logger.info(f"Received WebRTC live voice stream: {target_path} ({file_size} bytes)")

    # Boost music volume to maximum and trigger gentle vibration hint
    run_termux_cmd(["termux-volume", "music", "15"])
    run_termux_cmd(["termux-vibrate", "-d", "150", "-f"])

    # Stop any current playback and play live intercom voice audio blob
    run_termux_cmd(["termux-media-player", "stop"])
    res = run_termux_cmd(["termux-media-player", "play", target_path])
    if res.get("returncode") != 0 or (res.get("stderr") and "Error" in res.get("stderr")):
        # Fallback to mpv player
        res_mpv = run_termux_cmd(["mpv", "--no-video", target_path])
        return jsonify({"success": True, "size_bytes": file_size, "player": "mpv", "result": res_mpv})

    return jsonify({"success": True, "size_bytes": file_size, "player": "termux-media-player", "result": res})

@app.route("/api/siren", methods=["POST"])
def trigger_siren():
    """Triggers siren alert / find phone strobe with optional custom speech text."""
    data = request.get_json(force=True, silent=True) or {}
    active = data.get("active", True)
    custom_msg = data.get("message")
    if custom_msg:
        hub_state["find_phone_message"] = custom_msg.strip()
        save_settings()

    state_str = "on" if active else "off"

    run_termux_cmd(["termux-torch", state_str])
    if active:
        speech_msg = hub_state.get("find_phone_message", "โทรศัพท์อยู่ที่ไหน ฉันกำลังตามหาอยู่ โทรศัพท์อยู่ที่ไหน ฉันกำลังตามหาอยู่")
        clean_msg = speech_msg.strip('"')
        run_termux_cmd(["termux-volume", "music", "15"])
        run_termux_cmd(["termux-vibrate", "-d", "1000", "-f"])
        speak_text_sync(clean_msg, rate="1.2")
    return jsonify({"status": "ok", "siren_active": active, "find_phone_message": hub_state.get("find_phone_message")})

@app.route("/api/torch", methods=["POST"])
def set_torch():
    """Toggles LED flashlight on or off."""
    data = request.get_json(force=True, silent=True) or {}
    state = data.get("state", "off")
    res = run_termux_cmd(["termux-torch", state])
    return jsonify(res)

@app.route("/api/vibrate", methods=["POST"])
def trigger_vibration():
    """Triggers device vibration."""
    data = request.get_json(force=True, silent=True) or {}
    duration = str(data.get("duration_ms", 500))
    res = run_termux_cmd(["termux-vibrate", "-d", duration, "-f"])
    return jsonify(res)

# ==============================================================================
# Routes: Module 2 - Custom Audio MP3 Upload, Playback & Deletion
# ==============================================================================
@app.route("/api/upload-audio", methods=["POST"])
def upload_audio():
    """Uploads an MP3 / WAV / WEBM audio file to Termux storage for remote playback."""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    if not filename:
        filename = f"custom_audio_{int(time.time())}.mp3"

    file_path = os.path.join(SOUNDS_DIR, filename)
    file.save(file_path)
    logger.info(f"Saved uploaded audio file to: {file_path}")

    run_termux_cmd(["termux-media-scan", file_path])

    return jsonify({
        "success": True,
        "filename": filename,
        "file_path": file_path,
        "size_bytes": os.path.getsize(file_path)
    })

@app.route("/api/audio-files", methods=["GET"])
def list_audio_files():
    """Lists all uploaded audio files available for playback."""
    files = []
    if os.path.exists(SOUNDS_DIR):
        for fname in os.listdir(SOUNDS_DIR):
            fpath = os.path.join(SOUNDS_DIR, fname)
            if os.path.isfile(fpath) and fname.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a', '.aac', '.webm')):
                files.append({
                    "filename": fname,
                    "file_path": fpath,
                    "size_bytes": os.path.getsize(fpath)
                })
    return jsonify({"success": True, "files": files})

@app.route("/api/audio-files/<filename>", methods=["DELETE"])
def delete_audio_file(filename):
    """Deletes an uploaded MP3 audio file by filename."""
    fname = secure_filename(filename)
    file_path = os.path.join(SOUNDS_DIR, fname)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Deleted audio file: {file_path}")
            return jsonify({"success": True, "filename": fname})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": False, "error": f"File not found: {fname}"}), 404

@app.route("/api/play-audio", methods=["POST"])
def play_audio():
    """Plays an uploaded custom audio file via termux-media-player."""
    data = request.get_json(force=True, silent=True) or {}
    filename = data.get("filename")
    file_path = data.get("file_path")

    if not file_path and filename:
        file_path = os.path.join(SOUNDS_DIR, secure_filename(filename))

    if not file_path or not os.path.exists(file_path):
        return jsonify({"success": False, "error": f"Audio file not found: {file_path}"}), 404

    run_termux_cmd(["termux-volume", "music", "15"])
    res = run_termux_cmd(["termux-media-player", "play", file_path])
    return jsonify(res)

# ==============================================================================
# Routes: Module 3 - Real GPS Location & Geofence
# ==============================================================================
@app.route("/api/location", methods=["GET"])
def get_gps_location():
    """Fetches current real GPS coordinates using termux-location -r last."""
    res = run_termux_cmd(["termux-location", "-r", "last"], timeout=5)
    data = res.get("data")
    if not data and res.get("stdout"):
        try:
            data = json.loads(res["stdout"])
        except Exception:
            pass

    if data and isinstance(data, dict) and "latitude" in data:
        hub_state["last_known_location"] = data
        return jsonify({"success": True, "data": data})

    # Fallback to network provider
    res_net = run_termux_cmd(["termux-location", "-p", "network", "-r", "once"], timeout=6)
    if res_net.get("data"):
        hub_state["last_known_location"] = res_net["data"]
        return jsonify(res_net)

    return jsonify({"success": True, "data": hub_state["last_known_location"]})

@app.route("/api/geofence", methods=["POST"])
def update_geofence():
    """Updates the safe zone geofence center and radius."""
    data = request.get_json(force=True, silent=True) or {}
    hub_state["geofence"]["center_lat"] = data.get("lat", hub_state["geofence"]["center_lat"])
    hub_state["geofence"]["center_lng"] = data.get("lng", hub_state["geofence"]["center_lng"])
    hub_state["geofence"]["radius_meters"] = data.get("radius", hub_state["geofence"]["radius_meters"])
    save_settings()
    return jsonify({"status": "success", "geofence": hub_state["geofence"]})

# ==============================================================================
# Routes: Module 4 - Fall Detection & Notifications
# ==============================================================================
@app.route("/api/notification", methods=["POST"])
def post_notification():
    """Posts a system status bar notification via termux-notification."""
    data = request.get_json(force=True, silent=True) or {}
    res = run_termux_cmd([
        "termux-notification",
        "--id", data.get("id", "eldercare_alert"),
        "--title", data.get("title", "ElderCare Alert"),
        "--content", data.get("content", "Alert trigger"),
        "--priority", data.get("priority", "high")
    ])
    return jsonify(res)

@app.route("/api/sos", methods=["POST"])
def trigger_sos_alert():
    """Triggers emergency SOS fall guard alert."""
    data = request.get_json(force=True, silent=True) or {}
    phone = data.get("phone_number")
    message = data.get("message", "🚨 แจ้งเตือนฉุกเฉิน: ตรวจพบเหตุขอความช่วยเหลือที่เครื่องผู้สูงอายุ!")

    hub_state["last_fall_alert"] = datetime.now().isoformat()
    run_termux_cmd(["termux-torch", "on"])
    run_termux_cmd(["termux-vibrate", "-d", "1500", "-f"])
    run_termux_cmd([
        "termux-notification",
        "--id", "eldercare_sos",
        "--title", "🚨 EMERGENCY SOS ALERT",
        "--content", "Emergency triggered on Senior Device!",
        "--priority", "high"
    ])

    if phone:
        run_termux_cmd(["termux-sms-send", "-n", phone, message])

    return jsonify({"status": "alert_triggered", "timestamp": hub_state["last_fall_alert"]})

# ==============================================================================
# Routes: Module 5 - Telephony, SMS & Whitelist Contacts CRUD
# ==============================================================================
@app.route("/api/contacts", methods=["GET"])
def get_contacts():
    """Lists all whitelisted contacts."""
    return jsonify({"success": True, "contacts": hub_state.get("contacts", [])})

@app.route("/api/contacts", methods=["POST"])
def save_contact():
    """Adds a new whitelist contact or updates an existing one."""
    data = request.get_json(force=True, silent=True) or {}
    cid = data.get("id") or f"c_{int(time.time() * 1000)}"
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()

    if not name or not phone:
        return jsonify({"success": False, "error": "Name and phone number are required"}), 400

    contacts = hub_state.setdefault("contacts", [])
    updated = False
    for c in contacts:
        if c["id"] == cid:
            c["name"] = name
            c["phone"] = phone
            updated = True
            break

    if not updated:
        contacts.append({"id": cid, "name": name, "phone": phone})

    save_settings()
    log_system_event("CONTACTS", f"Saved contact '{name}' ({phone})")
    return jsonify({"success": True, "contacts": hub_state["contacts"]})

@app.route("/api/contacts/<contact_id>", methods=["DELETE"])
def delete_contact(contact_id):
    """Deletes a whitelist contact by ID."""
    hub_state["contacts"] = [c for c in hub_state.get("contacts", []) if c["id"] != contact_id]
    save_settings()
    log_system_event("CONTACTS", f"Deleted contact [{contact_id}]")
    return jsonify({"success": True, "contacts": hub_state["contacts"]})

@app.route("/api/call", methods=["POST"])
def make_call():
    """Initiates a phone call to a whitelisted number."""
    data = request.get_json(force=True, silent=True) or {}
    phone = data.get("phone_number")
    if not phone:
        return jsonify({"success": False, "error": "Phone number required"}), 400
    res = run_termux_cmd(["termux-telephony-call", phone])
    return jsonify(res)

@app.route("/api/sms", methods=["POST"])
def send_sms():
    """Sends an SMS message to a specified recipient."""
    data = request.get_json(force=True, silent=True) or {}
    phone = data.get("phone_number")
    message = data.get("message", "")
    if not phone or not message:
        return jsonify({"success": False, "error": "Phone number and message required"}), 400
    res = run_termux_cmd(["termux-sms-send", "-n", phone, message])
    return jsonify(res)

# ==============================================================================
# Background Task: Hourly Talking Clock, Custom Routines & Battery Guard
# ==============================================================================
BATTERY_ALERT_THRESHOLDS = [70, 50, 30, 20, 10, 5]
alerted_battery_levels = set()

def check_battery_low_alert():
    """Checks battery level and triggers 3x TTS charge alert when dropping to 70%, 50%, 30%, 20%, 10%, or 5%."""
    global alerted_battery_levels
    try:
        res = run_termux_cmd(["termux-battery-status"])
        data = res.get("data")
        if not data and res.get("stdout"):
            try:
                data = json.loads(res["stdout"])
            except Exception:
                data = {}
        if not isinstance(data, dict):
            return

        pct = data.get("percentage")
        status = str(data.get("status", "")).upper()
        plugged = str(data.get("plugged", "")).upper()

        is_charging = "CHARGING" in status or ("PLUGGED" in plugged and "UNPLUGGED" not in plugged)

        if is_charging:
            if alerted_battery_levels:
                logger.info("Device is charging/plugged in. Resetting low battery alert thresholds.")
                alerted_battery_levels.clear()
            return

        if pct is not None:
            pct = int(pct)
            for threshold in BATTERY_ALERT_THRESHOLDS:
                if pct <= threshold and threshold not in alerted_battery_levels:
                    alerted_battery_levels.add(threshold)
                    msg = "ช่วยหนูด้วยค่ะ ช่วย charge battery ให้หนูด้วย"
                    clean_msg = msg.strip('"')
                    logger.warning(f"Low battery alert triggered! Level: {pct}% (Threshold: {threshold}%). Playing alert 3 times.")
                    log_system_event("BATTERY-ALERT", f"Low battery at {pct}% (Threshold: {threshold}%) - Playing alert 3x: '{clean_msg}'")

                    run_termux_cmd(["termux-volume", "music", "15"])
                    for i in range(3):
                        speak_text_sync(clean_msg, rate="0.9")
                        time.sleep(3)
                    break
    except Exception as e:
        logger.error(f"Error checking low battery alert: {e}")

def play_startup_announcement():
    """Plays TTS announcement when app starts: 'System is ready สวัสดีค่ะ ระบบ Termux Hub เริ่มทำงาน '."""
    try:
        time.sleep(1)
        msg = "System is ready สวัสดีค่ะ ระบบ Termux Hub เริ่มทำงาน "
        clean_msg = msg.strip('"')
        logger.info(f"Playing startup announcement: '{clean_msg}'")
        log_system_event("STARTUP", f"Startup announcement: '{clean_msg}'")

        run_termux_cmd(["termux-volume", "music", "15"])
        speak_text_sync(clean_msg, rate="0.9")
    except Exception as e:
        logger.error(f"Error in startup announcement: {e}")

def hourly_clock_daemon():
    """Background thread for hourly reminders, custom routines, and low battery checks using Google TTS '-l th'."""
    logger.info("Starting Hourly Talking Clock & Custom Routine Daemon Thread...")
    last_spoken_hour = -1
    last_triggered_key = ""

    while True:
        try:
            now = datetime.now()
            current_hhmm = now.strftime("%H:%M")
            is_weekend = now.weekday() >= 5
            settings = hub_state.get("clock_settings", {})
            volume = str(settings.get("volume", 12))
            rate = str(settings.get("rate", 1.0))

            # 1. Custom Routine Reminder Checks
            routines = hub_state.get("routines", [])
            for rt in routines:
                if rt.get("enabled", True) and rt.get("time") == current_hhmm:
                    rt_key = f"{rt.get('id')}_{current_hhmm}_{now.strftime('%Y%m%d')}"
                    if rt_key != last_triggered_key:
                        days_filter = rt.get("days", "EVERYDAY")
                        should_trigger = False
                        if days_filter == "EVERYDAY":
                            should_trigger = True
                        elif days_filter == "WEEKDAYS" and not is_weekend:
                            should_trigger = True
                        elif days_filter == "WEEKENDS" and is_weekend:
                            should_trigger = True

                        if should_trigger:
                            last_triggered_key = rt_key
                            msg = rt.get("message", "")
                            mp3 = rt.get("mp3_file", "")
                            logger.info(f"Custom Routine Triggered [{rt.get('id')}] at {current_hhmm}: '{msg}' (MP3: {mp3})")

                            run_termux_cmd(["termux-volume", "music", volume])
                            clean_msg = msg.strip('"')
                            speak_text_sync(clean_msg, rate=rate)

                            if mp3:
                                mp3_path = os.path.join(SOUNDS_DIR, secure_filename(mp3))
                                if os.path.exists(mp3_path):
                                    time.sleep(1)
                                    run_termux_cmd(["termux-media-player", "play", mp3_path])

            # 2. Hourly Talking Clock Announcement (plays fixed HH-MM.mp3)
            if settings.get("enabled", True):
                start_h = settings.get("start_hour", 8)
                end_h = settings.get("end_hour", 20)

                if start_h <= now.hour <= end_h and now.minute == 0 and now.hour != last_spoken_hour:
                    last_spoken_hour = now.hour
                    filename = f"{now.hour:02d}-00.mp3"
                    mp3_path = get_talking_clock_mp3_path(now.hour)

                    logger.info(f"Hourly chime triggering at {now.hour}:00 - MP3: '{filename}'")
                    run_termux_cmd(["termux-volume", "music", volume])
                    if mp3_path and os.path.exists(mp3_path):
                        run_termux_cmd(["termux-media-player", "stop"], timeout=2)
                        run_termux_cmd(["termux-media-player", "play", mp3_path])
                        log_system_event("TALKING-CLOCK", f"Triggered hourly chime MP3: {filename}")
                    else:
                        msg = f"ขณะนี้เวลา {now.hour} นาฬิกา"
                        speak_text_sync(msg, rate=rate)
                        log_system_event("TALKING-CLOCK", f"Hourly chime MP3 missing for hour {now.hour:02d}, used TTS fallback")

            # 3. Check Battery Low Level Alert (70%, 50%, 30%, 20%, 10%, 5%)
            check_battery_low_alert()

        except Exception as e:
            logger.error(f"Error in hourly clock & routine daemon: {e}")

        time.sleep(30)  # Check every 30 seconds

# ==============================================================================
# SSL & Dual Server Launchers (HTTP + HTTPS Support)
# ==============================================================================
def ensure_ssl_certs() -> bool:
    """Generates self-signed SSL certificate and key if missing."""
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return True
    os.makedirs(CONFIG_DIR, exist_ok=True)
    openssl_bin = shutil.which("openssl") or "/data/data/com.termux/files/usr/bin/openssl"
    try:
        cmd = [
            openssl_bin, "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", KEY_FILE, "-out", CERT_FILE,
            "-days", "3650", "-nodes",
            "-subj", "/CN=Termux-Hub"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
            logger.info(f"Generated self-signed SSL certificate: {CERT_FILE}")
            return True
        else:
            logger.error(f"OpenSSL cert generation failed: {res.stderr}")
    except Exception as e:
        logger.error(f"Error generating SSL certs: {e}")
    return False

# ==============================================================================
# Camera REST API Endpoints
# ==============================================================================
@app.route("/api/camera/info", methods=["GET"])
def get_camera_info():
    """Queries hardware camera specifications via termux-camera-info."""
    res = run_termux_cmd(["termux-camera-info"], timeout=5)
    if res.get("success") and res.get("data"):
        return jsonify({"success": True, "cameras": res["data"]})
    
    if res.get("stdout"):
        try:
            cameras = json.loads(res["stdout"])
            return jsonify({"success": True, "cameras": cameras})
        except Exception:
            pass
            
    return jsonify({"success": False, "error": res.get("stderr") or "Failed to query camera info"}), 500

@app.route("/api/camera/snap", methods=["POST"])
def capture_camera_photo():
    """Captures a photo using termux-camera-photo for specified camera ID."""
    data = request.json or {}
    camera_id = str(data.get("camera_id", "0")).strip()
    if camera_id not in ["0", "1"]:
        camera_id = "0"
        
    filename = f"snap_cam{camera_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    filepath = os.path.join(PHOTOS_DIR, filename)
    
    res = run_termux_cmd(["termux-camera-photo", "-c", camera_id, filepath], timeout=15)
    
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        log_system_event("CAMERA", f"Captured photo using camera {camera_id}: {filename}")
        return jsonify({
            "success": True,
            "filename": filename,
            "url": f"/api/camera/photo/{filename}",
            "camera_id": camera_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
    return jsonify({
        "success": False,
        "error": res.get("stderr") or "Failed to capture photo (camera busy or permission denied)"
    }), 500

@app.route("/api/camera/photo/<filename>", methods=["GET"])
def serve_camera_photo(filename):
    """Serves captured camera photo file."""
    safe_name = secure_filename(filename)
    filepath = os.path.join(PHOTOS_DIR, safe_name)
    if os.path.exists(filepath):
        return send_file(filepath, mimetype="image/jpeg")
    return "Photo not found", 404

@app.route("/api/camera/photos", methods=["GET"])
def list_camera_photos():
    """Lists all captured camera photos sorted by newest first."""
    photos = []
    if os.path.exists(PHOTOS_DIR):
        for f in sorted(os.listdir(PHOTOS_DIR), reverse=True):
            if f.lower().endswith((".jpg", ".jpeg", ".png")):
                f_path = os.path.join(PHOTOS_DIR, f)
                stat = os.stat(f_path)
                photos.append({
                    "filename": f,
                    "url": f"/api/camera/photo/{f}",
                    "size_bytes": stat.st_size,
                    "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
    return jsonify({"success": True, "photos": photos})

@app.route("/api/camera/photo/<filename>", methods=["DELETE"])
def delete_camera_photo(filename):
    """Deletes a captured camera photo."""
    safe_name = secure_filename(filename)
    filepath = os.path.join(PHOTOS_DIR, safe_name)
    if os.path.exists(filepath):
        os.remove(filepath)
        log_system_event("CAMERA", f"Deleted photo: {safe_name}")
        return jsonify({"success": True, "message": "Photo deleted successfully"})
    return jsonify({"success": False, "error": "Photo not found"}), 404

def run_http_server(host: str, port: int):
    try:
        from werkzeug.serving import make_server
        logger.info(f"Starting HTTP server on http://{host}:{port}")
        http_server = make_server(host, port, app, threaded=True)
        http_server.serve_forever()
    except Exception as e:
        logger.error(f"HTTP server error: {e}")

def run_https_server(host: str, port: int, cert_file: str, key_file: str):
    try:
        import ssl
        from werkzeug.serving import make_server
        logger.info(f"Starting HTTPS server on https://{host}:{port}")
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_ctx.load_cert_chain(cert_file, key_file)
        https_server = make_server(host, port, app, ssl_context=ssl_ctx, threaded=True)
        https_server.serve_forever()
    except Exception as e:
        logger.error(f"HTTPS server error: {e}")

# ==============================================================================
# Startup Initialization & Entry Point
# ==============================================================================
load_settings()
daemon_thread = threading.Thread(target=hourly_clock_daemon, daemon=True)
daemon_thread.start()

startup_thread = threading.Thread(target=play_startup_announcement, daemon=True)
startup_thread.start()

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    http_port = int(os.getenv("PORT", "8888"))
    https_port = int(os.getenv("HTTPS_PORT", "8443"))

    has_ssl = ensure_ssl_certs()
    if has_ssl:
        https_thread = threading.Thread(
            target=run_https_server,
            args=(host, https_port, CERT_FILE, KEY_FILE),
            daemon=True
        )
        https_thread.start()
        logger.info(f"ElderCare Hub active on HTTPS: https://{host}:{https_port}")

    logger.info(f"ElderCare Hub active on HTTP: http://{host}:{http_port}")
    run_http_server(host, http_port)
