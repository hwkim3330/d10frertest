#!/bin/bash
# 192.168.1.3 서버에서 직접 실행하는 스크립트
# 서버 상태 확인 및 테스트 서버 시작

echo "=========================================="
echo "Network Test Server Setup"
echo "=========================================="
echo ""

# 1. IP 확인
echo "[1/5] Checking IP configuration..."
IP_ADDR=$(ip addr show | grep "inet 192.168.1.3" | wc -l)
if [ $IP_ADDR -eq 0 ]; then
    echo "✗ ERROR: This machine does not have IP 192.168.1.3"
    echo "Current IPs:"
    ip addr show | grep "inet "
    exit 1
else
    echo "✓ IP 192.168.1.3 is configured"
fi
echo ""

# 2. 방화벽 확인
echo "[2/5] Checking firewall..."
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(sudo ufw status | grep "Status: active" | wc -l)
    if [ $UFW_STATUS -gt 0 ]; then
        echo "⚠ UFW firewall is active"
        echo "Opening required ports..."
        sudo ufw allow 11111/tcp
        sudo ufw allow 11111/udp
        sudo ufw allow 5201/tcp
        sudo ufw allow 5201/udp
        echo "✓ Firewall rules added"
    else
        echo "✓ UFW firewall is inactive"
    fi
fi

if command -v firewall-cmd &> /dev/null; then
    FIREWALLD_STATUS=$(sudo firewall-cmd --state 2>/dev/null | grep "running" | wc -l)
    if [ $FIREWALLD_STATUS -gt 0 ]; then
        echo "⚠ firewalld is active"
        echo "Opening required ports..."
        sudo firewall-cmd --permanent --add-port=11111/tcp
        sudo firewall-cmd --permanent --add-port=11111/udp
        sudo firewall-cmd --permanent --add-port=5201/tcp
        sudo firewall-cmd --permanent --add-port=5201/udp
        sudo firewall-cmd --reload
        echo "✓ Firewall rules added"
    fi
fi
echo ""

# 3. 필요한 패키지 확인
echo "[3/5] Checking required packages..."
MISSING_PACKAGES=""

if ! command -v sockperf &> /dev/null; then
    echo "✗ sockperf not found"
    MISSING_PACKAGES="$MISSING_PACKAGES sockperf"
else
    echo "✓ sockperf found"
fi

if ! command -v iperf3 &> /dev/null; then
    echo "✗ iperf3 not found"
    MISSING_PACKAGES="$MISSING_PACKAGES iperf3"
else
    echo "✓ iperf3 found"
fi

if [ -n "$MISSING_PACKAGES" ]; then
    echo ""
    echo "Installing missing packages..."
    sudo apt-get update
    sudo apt-get install -y $MISSING_PACKAGES
fi
echo ""

# 4. 기존 서버 프로세스 정리
echo "[4/5] Cleaning up old processes..."
pkill -f "sockperf.*sr" || true
pkill -f "iperf3.*-s" || true
sleep 2
echo "✓ Old processes cleaned"
echo ""

# 5. 테스트 서버 시작
echo "[5/5] Starting test servers..."

# Sockperf 서버 (TCP)
sockperf sr --tcp -i 192.168.1.3 -p 11111 > /tmp/sockperf_server.log 2>&1 &
SOCKPERF_PID=$!
echo $SOCKPERF_PID > /tmp/sockperf_server.pid
echo "✓ Sockperf server started (PID: $SOCKPERF_PID)"

# iperf3 서버
iperf3 -s > /tmp/iperf3_server.log 2>&1 &
IPERF3_PID=$!
echo $IPERF3_PID > /tmp/iperf3_server.pid
echo "✓ iperf3 server started (PID: $IPERF3_PID)"

sleep 2

# 6. 서버 상태 확인
echo ""
echo "=========================================="
echo "Server Status"
echo "=========================================="

if ps -p $SOCKPERF_PID > /dev/null; then
    echo "✓ Sockperf server is running (TCP port 11111)"
else
    echo "✗ Sockperf server failed to start"
fi

if ps -p $IPERF3_PID > /dev/null; then
    echo "✓ iperf3 server is running (TCP/UDP port 5201)"
else
    echo "✗ iperf3 server failed to start"
fi

echo ""
echo "Listening ports:"
ss -tulpn | grep -E "11111|5201" || echo "No ports found (may need sudo)"

echo ""
echo "=========================================="
echo "Ready for testing!"
echo "=========================================="
echo "Client (192.168.1.2) can now run tests"
echo ""
echo "To stop servers:"
echo "  kill \$(cat /tmp/sockperf_server.pid)"
echo "  kill \$(cat /tmp/iperf3_server.pid)"
echo "=========================================="
