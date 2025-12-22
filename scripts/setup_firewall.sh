#!/bin/bash
# Firewall Setup Script for Air-Gapped System
# Blocks all external network access
# WARNING: Requires root privileges

set -e

echo "========================================"
echo "NETWORK ISOLATION SETUP"
echo "========================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root"
    echo "Usage: sudo ./setup_firewall.sh"
    exit 1
fi

echo "This will configure firewall rules to block all external network access."
echo "Only localhost communication will be allowed."
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Backing up existing iptables rules..."
iptables-save > /tmp/iptables-backup-$(date +%Y%m%d-%H%M%S).rules

echo "Configuring firewall rules..."

# Flush existing rules
iptables -F
iptables -X

# Default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

# Allow loopback interface
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Allow established connections (for localhost)
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Save rules
if command -v netfilter-persistent &> /dev/null; then
    netfilter-persistent save
    echo "Rules saved with netfilter-persistent"
elif command -v iptables-save &> /dev/null; then
    iptables-save > /etc/iptables/rules.v4
    echo "Rules saved to /etc/iptables/rules.v4"
fi

echo ""
echo "✓ Firewall configured successfully"
echo ""
echo "Current rules:"
iptables -L -n

echo ""
echo "========================================"
echo "VERIFICATION"
echo "========================================"
echo ""
echo "Testing network isolation..."

# Test DNS
if timeout 2 ping -c 1 8.8.8.8 &> /dev/null; then
    echo "✗ WARNING: Network is still accessible"
else
    echo "✓ External network blocked"
fi

echo ""
echo "Setup complete. System is now air-gapped."
echo "Backup saved at: /tmp/iptables-backup-*.rules"
