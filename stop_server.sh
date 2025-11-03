#!/bin/bash
# Stop all test servers

echo "Stopping test servers..."

# Stop sockperf server
if [ -f /tmp/sockperf_server.pid ]; then
    SOCKPERF_PID=$(cat /tmp/sockperf_server.pid)
    if kill -0 $SOCKPERF_PID 2>/dev/null; then
        kill $SOCKPERF_PID
        echo "Stopped sockperf server (PID: $SOCKPERF_PID)"
    fi
    rm /tmp/sockperf_server.pid
fi

# Stop iperf3 server
if [ -f /tmp/iperf3_server.pid ]; then
    IPERF3_PID=$(cat /tmp/iperf3_server.pid)
    if kill -0 $IPERF3_PID 2>/dev/null; then
        kill $IPERF3_PID
        echo "Stopped iperf3 server (PID: $IPERF3_PID)"
    fi
    rm /tmp/iperf3_server.pid
fi

# Kill any remaining instances
sudo pkill -f "sockperf sr"
sudo pkill -f "iperf3 -s"

echo "All servers stopped"
