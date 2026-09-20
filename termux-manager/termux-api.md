**Termux:API** provides command-line access to Android device hardware, sensors, and system services directly from the Termux shell.

### Prerequisites & Setup

To use these commands, two components from the same installation source (such as F-Droid or GitHub Releases) are required:

1. **The Android APK:** Install the `Termux:API` companion application.
2. **The Command-Line Package:** Run `pkg install termux-api` inside Termux.

---

### Command Reference by Category

#### 1. Hardware & Device State

* `termux-battery-status`: Returns battery percentage, health, temperature, and charging status as JSON.
* `termux-brightness <0-255>`: Sets screen brightness.
* `termux-torch <on|off>`: Toggles the LED camera flash.
* `termux-vibrate -d <ms>`: Triggers device vibration for a set duration.
* `termux-volume <stream> <level>`: Adjusts audio stream volume (e.g., `music`, `ring`, `alarm`).
* `termux-wallpaper -f <file>`: Sets the device lock screen or home wallpaper.
* `termux-wake-lock` / `termux-wake-unlock`: Prevents Android from entering deep sleep during long tasks.

#### 2. Sensors & Location

* `termux-location -p <gps|network>`: Fetches coordinates, altitude, and accuracy as JSON.
* `termux-sensor -s <sensor_name>`: Streams live readings from device sensors (accelerometer, gyroscope, light, etc.).
* `termux-fingerprint`: Prompts for biometric authentication via the fingerprint sensor.

#### 3. Multimedia & Audio

* `termux-camera-info`: Lists available cameras and supported resolutions.
* `termux-camera-photo -c <id> <output.jpg>`: Takes a picture (`0` = rear, `1` = front).
* `termux-microphone-record -d -f <file.m4a>`: Records audio via the internal microphone.
* `termux-media-player <play|pause|stop> <file>`: Controls local media playback.
* `termux-tts-speak "<text>"`: Speaks text aloud using Android's Text-to-Speech engine.
* `termux-speech-to-text`: Listens to speech and converts it to text.

#### 4. System UI & Interactions

* `termux-toast "<message>"`: Shows a small transient pop-up notification on the screen.
* `termux-notification -t "<title>" -c "<content>"`: Posts a persistent system notification.
* `termux-notification-remove <id>`: Dismisses an active notification by ID.
* `termux-dialog <text|confirm|date|time|radio>`: Renders interactive Android GUI inputs and returns the user's choice.
* `termux-clipboard-get`: Prints current clipboard contents.
* `termux-clipboard-set "<text>"`: Copies text into the clipboard.

#### 5. Telephony & Communications

* `termux-sms-send -n <number> "<message>"`: Sends an SMS.
* `termux-sms-list -l <count>`: Lists received and sent SMS messages as JSON.
* `termux-telephony-call <number>`: Dials a phone number directly.
* `termux-telephony-cellinfo`: Returns cell tower connections and signal strength.
* `termux-contact-list`: Outputs all device contacts in JSON format.
* `termux-call-log -l <count>`: Dumps the recent call history.

#### 6. Connectivity & System Tools

* `termux-wifi-connectioninfo`: Returns the active SSID, BSSID, IP, and link speed.
* `termux-wifi-scaninfo`: Scans and lists nearby Wi-Fi networks.
* `termux-download -d "<desc>" -t "<title>" <url>`: Hands off a file download to the Android download manager.
* `termux-share -a <send|view|edit> <file>`: Triggers the native Android "Share with" sheet.
* `termux-job-scheduler`: Schedules scripts to run at specific intervals or on device conditions (e.g., charging, Wi-Fi connected).

---

### Practical Scripting Tip

Most information-gathering commands output structured JSON. Combine them with `jq` to parse data cleanly in shell scripts:

```bash
# Check if battery is low and trigger an alert
battery_level=$(termux-battery-status | jq '.percentage')

if [ "$battery_level" -lt 20 ]; then
  termux-toast "Battery low: ${battery_level}%"
  termux-vibrate -d 500
fi

```