#!/bin/bash
# Server Setup Script for 192.168.1.3
# Run this on the target machine to set up all necessary servers

echo "Setting up test servers on 192.168.1.3..."

# Check if running on correct IP
CURRENT_IP=$(ip addr show | grep "192.168.1.3" | wc -l)
if [ $CURRENT_IP -eq 0 ]; then
    echo "WARNING: This script should be run on 192.168.1.3"
    echo "Current IP addresses:"
    ip addr show | grep "inet "
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install required packages
echo "Checking required packages..."

if ! command_exists sockperf; then
    echo "Installing sockperf..."
    sudo apt-get update
    sudo apt-get install -y sockperf
fi

if ! command_exists iperf3; then
    echo "Installing iperf3..."
    sudo apt-get install -y iperf3
fi

# Kill any existing servers
echo "Stopping any existing servers..."
sudo pkill -f "sockperf sr"
sudo pkill -f "iperf3 -s"

# Start sockperf server
echo "Starting sockperf server on port 11111..."
sockperf sr --tcp -i 192.168.1.3 -p 11111 > /tmp/sockperf_server.log 2>&1 &
SOCKPERF_PID=$!
echo "Sockperf server started (PID: $SOCKPERF_PID)"

# Start iperf3 server
echo "Starting iperf3 server on port 5201..."
iperf3 -s > /tmp/iperf3_server.log 2>&1 &
IPERF3_PID=$!
echo "iperf3 server started (PID: $IPERF3_PID)"

# Save PIDs
echo $SOCKPERF_PID > /tmp/sockperf_server.pid
echo $IPERF3_PID > /tmp/iperf3_server.pid

echo ""
echo "Server setup complete!"
echo "-----------------------------------"
echo "Sockperf server: TCP on port 11111 (PID: $SOCKPERF_PID)"
echo "iperf3 server: UDP/TCP on port 5201 (PID: $IPERF3_PID)"
echo ""
echo "Log files:"
echo "  - /tmp/sockperf_server.log"
echo "  - /tmp/iperf3_server.log"
echo ""
echo "To stop servers, run:"
echo "  kill $SOCKPERF_PID $IPERF3_PID"
echo "  or run: ./stop_server.sh"
echo ""
echo "Ready for testing from 192.168.1.2"
