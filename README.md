# Prerequisites
- Android Phones with version 8.0 or 8.1
- I tested with with the following version
- Redmi 5A (Android verion 8.0) : Termux App - OK , Termux Boot - auto start : OK
- Redmi 7A (Android version 8.1) : Termux App - OK, Termux Boot - installation OK ; but cannot configure auto start 
# Termux Android Scripts : Installation

This guide will walk you through the steps to install Termux and required scripts on your Android device using either adb tools or manual APK download.
You can check [Termux - the official web site here ](https://termux.dev/en/)
## Installation Steps

### 1. Install Termux and Termux:Boot
- You can download copies of apks here: [download link](https://github.com/kcommerce/Termux-Android-Scripts/tree/main/apk)
- Alternatively, you can download the latest version of Termux at [F-droid link](https://f-droid.org/en/)
- **Option 1: Using adb tools**
  - Ensure you have adb tools installed on your computer. You can find adb tools for macOS here: [download link](https://github.com/kcommerce/Termux-Android-Scripts/tree/main/adb-tools)
  - Connect your Android device to your computer via USB.
  - Run the following command to install Termux and Termux:Boot APKs:
    ```bash
    adb install path/to/Termux.apk
    adb install path/to/TermuxBoot.apk
    ```

- **Option 2: Manual APK Download**
  - Download the APK files for Termux and Termux:Boot manually to your phone.
  - Install the APKs on your Android device manually.

### 2. Set Autostart for Termux:Boot

- Open the Termux:Boot app on your device.
- Set up the autostart functionality as per the app's instructions.

### 3. Set Battery Permission to "No Restricted"

- Navigate to your device settings.
- Find the battery settings and set the permission for Termux to "No restrictions."
- Example Termux settings on Redmi 7A
- 
  <img src="images/Screenshot_2023-10-07-18-21-27-785_com.miui.powerkeeper.jpg" alt="Termux Battery Setting" width="30%" height="30%">
- For Termux:Boot , same like Termux
 
### 4. Launch Termux Application

- Locate and open the Termux application on your Android device.

### 5. Configure Termux

- Run the following commands in the Termux terminal to configure the storage and install root-repo:
  ```bash
  termux-setup-storage
  pkg install root-repo
  ```
- (Optional): Change repository to nearest location; The default is in the US.
  ```bash
  termux-change-repo
  ```
- Example Termux terminal on Redmi 7A
-
  <img src="images/Screenshot_2023-10-07-18-26-04-376_com.termux.jpg" alt="Termux Battery Setting" width="30%" height="30%">
### 6. Update and Upgrade Packages
- Run the following commands to update and upgrade Termux packages:
  ```bash
  pkg update -y
  pkg upgrade -y
  ```

### 7. Download and Run Installation Script
- Run the following commands to download and run the installation script:
  ```bash
  curl -o install.sh https://raw.githubusercontent.com/kcommerce/Termux-Android-Scripts/main/bin/install-base.sh
  chmod +x install.sh
  ./install.sh
  ```
The installation process will begin, and you'll be guided through the setup of the base Termux scripts. If the script prompts for Yes/No, just enter "Y" to accept it.
### 8. Verify Services
- Run the following commands to verify running ports: ftpd(8021), sshd(8022), httpd(8080):
  ```bash
  nmap localhost
  ```
- Run the following command to check process tree:
  ```bash
  pstree
  ```
### 9. Change Password
- Run the passwd command to change the password:
  ```bash
  passwd
  ```
