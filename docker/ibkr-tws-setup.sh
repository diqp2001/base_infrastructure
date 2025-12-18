#!/bin/bash

# Interactive Brokers TWS API Setup Script
# This script downloads and configures IBKR TWS for API access

set -e

echo "Setting up Interactive Brokers TWS API..."

# Create TWS directory
mkdir -p /home/trader/tws-api
cd /home/trader/tws-api

# Download TWS API
echo "Downloading TWS API..."
wget -O tws-api.zip "https://interactivebrokers.github.io/downloads/twsapi_macunix.1019.01.zip"
unzip -q tws-api.zip
rm tws-api.zip

# Download TWS (Trading Workstation) if needed for GUI trading
echo "Downloading TWS Trading Workstation..."
wget -O tws-stable-standalone-linux-x64.sh "https://download2.interactivebrokers.com/installers/tws/stable-standalone/tws-stable-standalone-linux-x64.sh"
chmod +x tws-stable-standalone-linux-x64.sh

# Install TWS in silent mode
echo "Installing TWS..."
./tws-stable-standalone-linux-x64.sh -q

# Create TWS configuration for API access
mkdir -p ~/.config/IBJts
cat > ~/.config/IBJts/jts.ini << EOF
[IBJts]
APIDisable=false
TrustedIPs=127.0.0.1
AcceptIncomingConnectionAction=accept
PortSocketSecurity=0
PrecautionaryPasswordMode=false
LocalServerPort=7497
ReadOnlyApi=false
EOF

echo "IBKR TWS API setup complete!"
echo "TWS will be available at:"
echo "  - API Port: 7497 (paper trading)"
echo "  - API Port: 7496 (live trading)"
echo "  - GUI Access: Use VNC viewer to connect to port 5901"

# Create startup script for TWS
cat > /home/trader/tws-api/start-tws.sh << 'EOF'
#!/bin/bash
export DISPLAY=:1
cd /home/trader/tws-api
exec java -cp ".:IBJts/source/JavaClient/bin" -jar IBJts/source/JavaClient/bin/IBJts.jar
EOF
chmod +x /home/trader/tws-api/start-tws.sh