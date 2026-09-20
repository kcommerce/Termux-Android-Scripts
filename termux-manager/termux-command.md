The full suite of official **Termux:API** commands is organized below by system domain, complete with description and practical syntax examples.

---

### 1. Battery, Power & Hardware Controls

* **`termux-battery-status`**
Returns battery percentage, health, temperature, and charging status as JSON.
```bash
termux-battery-status

```


* **`termux-brightness`**
Adjusts the screen brightness (value between `0` and `255`, or `auto`).
```bash
termux-brightness 180

```


* **`termux-torch`**
Toggles the LED camera flashlight on or off.
```bash
termux-torch on
termux-torch off

```


* **`termux-vibrate`**
Vibrates the device for a specified duration in milliseconds.
```bash
termux-vibrate -d 500 -f

```


* **`termux-wallpaper`**
Sets the device wallpaper for the home screen or lock screen.
```bash
termux-wallpaper -f /path/to/image.png -l   # -l for lockscreen, -h for home screen

```


* **`termux-usb`**
Lists or accesses attached USB devices via file descriptor.
```bash
termux-usb -l

```



---

### 2. Audio & Media

* **`termux-volume`**
Inspects or adjusts audio stream volume levels (`call`, `system`, `ring`, `music`, `alarm`, `notification`).
```bash
termux-volume music 10

```


* **`termux-media-player`**
Controls playback of local audio files.
```bash
termux-media-player play song.mp3
termux-media-player pause
termux-media-player stop

```


* **`termux-media-scan`**
Invokes Android's MediaScanner to index newly added or modified files for the Gallery/Music apps.
```bash
termux-media-scan -r ~/storage/shared/DCIM/

```


* **`termux-microphone-record`**
Records audio using the device microphone.
```bash
# Record a 10-second AAC audio clip
termux-microphone-record -f recording.m4a -l 10 -e aac
# Stop manual recording
termux-microphone-record -q

```


* **`termux-tts-engines`**
Lists installed Text-to-Speech engines and available languages.
```bash
termux-tts-engines

```


* **`termux-tts-speak`**
Speaks text aloud using the device TTS engine.
```bash
termux-tts-speak -p 1.0 -r 1.0 "Compilation complete"

```


* **`termux-speech-to-text`**
Converts spoken audio into text via speech recognition.
```bash
termux-speech-to-text

```



---

### 3. Camera & Sensors

* **`termux-camera-info`**
Lists available cameras and their supported resolutions/formats.
```bash
termux-camera-info

```


* **`termux-camera-photo`**
Takes a photo and saves it to a JPEG file (`-c 0` for rear, `-c 1` for front camera).
```bash
termux-camera-photo -c 0 photo.jpg

```


* **`termux-location`**
Fetches device GPS/Network location coordinates as JSON.
```bash
termux-location -p gps -r once

```


* **`termux-sensor`**
Lists available device sensors or streams real-time sensor data.
```bash
termux-sensor -l                        # List sensors
termux-sensor -s "Gravity" -n 1         # Get a single reading

```


* **`termux-fingerprint`**
Prompts for biometric/fingerprint authentication and returns success/fail JSON.
```bash
termux-fingerprint -t "Confirm Authorization"

```



---

### 4. System UI, Prompts & Dialogs

* **`termux-toast`**
Displays a short floating popup notification.
```bash
termux-toast -b black -c white -g middle "Task Finished!"

```


* **`termux-notification`**
Creates an Android system status bar notification.
```bash
termux-notification --id "task1" --title "Download" --content "File ready" --priority high

```


* **`termux-notification-remove`**
Removes a notification previously displayed by ID.
```bash
termux-notification-remove "task1"

```


* **`termux-notification-list`**
Lists currently active status bar notifications posted by apps.
```bash
termux-notification-list

```


* **`termux-dialog`**
Opens a native GUI pop-up dialog to capture user input.
```bash
# Text input
termux-dialog text -t "Enter API Key"
# Confirmation (Yes / No)
termux-dialog confirm -t "Do you want to proceed?"
# Date / Time picker
termux-dialog date
# Radio list
termux-dialog radio -v "Option A,Option B,Option C"

```


* **`termux-clipboard-get`**
Reads text from the system clipboard.
```bash
clip=$(termux-clipboard-get)

```


* **`termux-clipboard-set`**
Sets text into the system clipboard.
```bash
echo "Copied from Termux" | termux-clipboard-set

```



---

### 5. Telephony, Messaging & Contacts

* **`termux-telephony-call`**
Initiates a direct phone call to a given number.
```bash
termux-telephony-call 123456789

```


* **`termux-telephony-cellinfo`**
Dumps cell tower and radio information (signal strength, cell IDs).
```bash
termux-telephony-cellinfo

```


* **`termux-telephony-deviceinfo`**
Returns telephony state (network operator, SIM state, data activity).
```bash
termux-telephony-deviceinfo

```


* **`termux-sms-list`**
Dumps inbox and sent SMS messages as JSON.
```bash
termux-sms-list -l 5 -t inbox

```


* **`termux-sms-send`**
Sends an SMS message to one or more recipient numbers.
```bash
termux-sms-send -n +1234567890 "Your server backup is complete."

```


* **`termux-call-log`**
Retrieves device call history as JSON.
```bash
termux-call-log -l 10

```


* **`termux-contact-list`**
Lists all contacts stored in the Android contacts provider.
```bash
termux-contact-list

```



---

### 6. Networking & Connectivity

* **`termux-wifi-connectioninfo`**
Returns details on the current Wi-Fi network (SSID, BSSID, IP, link speed).
```bash
termux-wifi-connectioninfo

```


* **`termux-wifi-scaninfo`**
Lists Wi-Fi access points detected in the latest scan.
```bash
termux-wifi-scaninfo

```


* **`termux-wifi-enable`**
Toggles device Wi-Fi state (Note: restricted on newer Android releases).
```bash
termux-wifi-enable true

```



---

### 7. Storage, Files & Automation

* **`termux-download`**
Delegates a URL download to the native Android Download Manager.
```bash
termux-download -t "ISO Image" -d "Ubuntu Minimal" "https://example.com/image.iso"

```


* **`termux-storage-get`**
Opens the Android Storage Access Framework (SAF) document picker to import a file into Termux.
```bash
termux-storage-get ~/imported_file.pdf

```


* **`termux-share`**
Opens Android's native "Share with..." intent sheet to send a file or text to other apps.
```bash
termux-share -a send report.pdf
echo "Share this snippet" | termux-share -a send

```


* **`termux-job-scheduler`**
Schedules background scripts to execute under specific battery/network conditions via Android's JobScheduler.
```bash
termux-job-scheduler -s ~/backup.sh --period-ms 3600000 --charging true --battery-not-low true
termux-job-scheduler -p          # List pending jobs
termux-job-scheduler --cancel-all

```



---

### 8. Infrared (Hardware-dependent)

* **`termux-infrared-frequencies`**
Queries carrier frequencies supported by the phone's IR blaster.
```bash
termux-infrared-frequencies

```


* **`termux-infrared-transmit`**
Transmits an IR pattern at a specified frequency.
```bash
termux-infrared-transmit -f 38000 200,400,200,800

```