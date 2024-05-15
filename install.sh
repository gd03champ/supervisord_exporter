#!/bin/bash

# ANSI color codes
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Confirm if Supervisor is up and running with RPC endpoint enabled
read -p "Is Supervisor up and running with RPC endpoint enabled? (y/n): " supervisor_confirmed
if [ "$supervisor_confirmed" != "y" ]; then
    echo "Exiting script..."
    exit 1
fi

# Install required packages
echo -e "${GREEN}Installing required packages...${NC}"
sudo apt install -y git python3 python3-pip

# Clone repository
echo -e "${GREEN}Cloning repository...${NC}"
git clone https://github.com/gd03champ/supervisord_exporter

# Change directory
echo -e "${GREEN}Changing directory...${NC}"
cd supervisord_exporter

# Install required Python packages
echo -e "${GREEN}Installing required Python packages...${NC}"
sudo pip3 install -r req-packages.txt

# Create directory
echo -e "${GREEN}Creating directory...${NC}"
sudo mkdir -p /usr/local/supervisord_exporter

# Copy main.py to destination
echo -e "${GREEN}Copying main.py to destination...${NC}"
sudo cp main.py /usr/local/supervisord_exporter/

# Create Supervisor configuration file
echo -e "${GREEN}Creating Supervisor configuration file...${NC}"
sudo tee /etc/supervisor/conf.d/supervisord_exporter.conf > /dev/null <<EOF
[program:supervisord_exporter]
; Path to executable
command=sudo python3 /usr/local/supervisord_exporter/main.py --supervisord-url "http://127.0.0.1:9001/RPC2" --listen-address ":9101" --metrics-path "/metrics"

; Set the working directory for the script (optional)
;directory=/path/to/script/directory

; Number of times to restart the program if it exits abnormally (optional)
autostart=true
autorestart=true
startretries=4

; How long to wait before retrying a restart (optional)
startsecs=3

; Redirect standard output and error to log files (optional, recommended)
stdout_logfile=/var/log/supervisor/supervisord_exporter.out
stderr_logfile=/var/log/supervisor/supervisord_exporter.err


; User and group to run the program (optional, defaults to the user who started Supervisor)
#user=your_user
#group=your_group
EOF

# Update Supervisor configurations
echo -e "${GREEN}Updating Supervisor configurations...${NC}"
sudo supervisorctl reread
sudo supervisorctl update

echo -e "${GREEN}Setup completed successfully.${NC}"
