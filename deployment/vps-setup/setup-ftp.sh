#!/bin/bash

# FTP Setup Script for Ubuntu VPS
# Sets up vsftpd for FileZilla access

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Setting up FTP server (vsftpd)...${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Install vsftpd
echo -e "${GREEN}Installing vsftpd...${NC}"
apt-get update
apt-get install -y vsftpd

# Backup original config
cp /etc/vsftpd.conf /etc/vsftpd.conf.backup

# Create new config
cat > /etc/vsftpd.conf <<'FTP_CONFIG'
# Basic FTP Configuration
listen=NO
listen_ipv6=YES
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES
chroot_local_user=YES
secure_chroot_dir=/var/run/vsftpd/empty
pam_service_name=vsftpd
rsa_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
rsa_private_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
ssl_enable=NO

# Security settings
allow_writeable_chroot=YES
user_sub_token=$USER
local_root=/home/$USER

# Passive mode (important for FileZilla)
pasv_enable=YES
pasv_min_port=40000
pasv_max_port=50000
pasv_address=YOUR_SERVER_IP

# Additional security
hide_ids=YES
FTP_CONFIG

# Get server IP
SERVER_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
sed -i "s/YOUR_SERVER_IP/$SERVER_IP/" /etc/vsftpd.conf

echo -e "${GREEN}Server IP detected: $SERVER_IP${NC}"
echo -e "${YELLOW}If this is wrong, edit /etc/vsftpd.conf and update pasv_address${NC}"

# Create required directory
mkdir -p /var/run/vsftpd/empty

# Configure firewall
echo -e "${GREEN}Configuring firewall...${NC}"
ufw allow 21/tcp comment 'FTP'
ufw allow 40000:50000/tcp comment 'FTP Passive'

# Restart vsftpd
systemctl restart vsftpd
systemctl enable vsftpd

# Check status
if systemctl is-active --quiet vsftpd; then
    echo -e "${GREEN}FTP server is running!${NC}"
else
    echo -e "${RED}FTP server failed to start. Check logs: journalctl -u vsftpd${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}FTP Setup Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}FileZilla Connection Settings:${NC}"
echo "  Protocol: FTP - File Transfer Protocol"
echo "  Host: $SERVER_IP (or your domain)"
echo "  Port: 21"
echo "  Username: ubuntu (or your username)"
echo "  Password: (your user password)"
echo "  Encryption: Only use plain FTP (insecure, not recommended)"
echo ""
echo -e "${YELLOW}For SFTP (more secure):${NC}"
echo "  Protocol: SFTP - SSH File Transfer Protocol"
echo "  Host: $SERVER_IP"
echo "  Port: 22"
echo "  Username: ubuntu"
echo "  Password: (your password or use SSH key)"
echo ""
echo -e "${YELLOW}Note: SFTP is recommended over FTP (more secure)${NC}"
echo ""

