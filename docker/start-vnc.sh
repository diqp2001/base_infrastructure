#!/bin/bash

# Start VNC server for IBKR TWS GUI access
export DISPLAY=:1

# Set VNC password if provided
if [ ! -z "$VNC_PASSWORD" ]; then
    mkdir -p ~/.vnc
    echo "$VNC_PASSWORD" | vncpasswd -f > ~/.vnc/passwd
    chmod 600 ~/.vnc/passwd
fi

# Start x11vnc server
exec x11vnc -display :1 -forever -usepw -create -rfbport 5901 -noxrecord -noxfixes -noxdamage -wait 5