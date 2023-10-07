#!/data/data/com.termux/files/usr/bin/bash

BOOT_FILE="$HOME/.termux/boot/start-services"

echo "---------------------------------"
echo " Install based services for Termux "
echo "----------------------------------"

echo "*** Install Python "
pkg install python,python-pip -y

echo "*** Install Termux packages "
pkg install termux-services termux-tools termux-api -y

echo "*** Install Web(8080), SFTP(8021), SSH(8022) "
pkg install apache2 openssh-sftp-server -y
pkg install openssh neofetch fish nmap cronie -y

echo "--> Enable services"
sv-enable crond
sv up crond
sv-enable ftpd
sv up ftpd
sv-enable httpd
sv up httpd
sv-enable sshd
sv up sshd
echo "--> Check services using nmap:"
nmap localhost
echo "--> Install boot services"
echo "#!/data/data/com.termux/files/usr/bin/bash" > $BOOT_FILE
echo "termux-wake-lock" >> $BOOT_FILE
echo "source /data/data/com.termux/files/usr/etc/profile.d/start-services.sh " >> $BOOT_FILE
chmod +x $BOOT_FILE
echo "--> Check boot file:"
ls -al $BOOT_FILE
cat $BOOT_FILE

echo "** Install addtionals: "
pkg install vim screen mpg123 sox espeak cmus  -y
pkg install git -y
echo "Test espeak :"
espeak "Hello, World"
