#!/bin/bash
# Master script to run all network performance tests
# Runs: Sockperf, RFC 2544, FRER tests

set -e  # Exit on error

TARGET_IP="192.168.1.3"
INTERFACE="enp2s0"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MASTER_RESULTS_DIR="complete_test_results_${TIMESTAMP}"

echo "================================================================================"
echo "COMPREHENSIVE NETWORK PERFORMANCE TEST SUITE"
echo "================================================================================"
echo "Target: $TARGET_IP"
echo "Interface: $INTERFACE"
echo "Timestamp: $TIMESTAMP"
echo "================================================================================"
echo ""

# Create master results directory
mkdir -p "$MASTER_RESULTS_DIR"

# Check connectivity
echo "[0/4] Checking connectivity..."
if ping -c 3 -W 2 "$TARGET_IP" > /dev/null 2>&1; then
    echo "✓ Target is reachable"
else
    echo "✗ Target is NOT reachable"
    echo "ERROR: Cannot continue without connectivity to $TARGET_IP"
    echo ""
    echo "Please ensure:"
    echo "  1. Server is powered on and accessible"
    echo "  2. Network cable is connected"
    echo "  3. Server has IP $TARGET_IP configured"
    echo "  4. Firewall allows traffic"
    echo ""
    echo "To setup server, run on $TARGET_IP:"
    echo "  ./setup_server.sh"
    exit 1
fi

echo ""

# Test 1: Quick connectivity test
echo "[1/4] Running quick connectivity test..."
echo "--------------------------------------------------------------------------------"
python3 quick_test.py > "${MASTER_RESULTS_DIR}/01_quick_test.log" 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Quick test completed"
else
    echo "✗ Quick test failed (check ${MASTER_RESULTS_DIR}/01_quick_test.log)"
fi
echo ""

# Test 2: RFC 2544 Test
echo "[2/4] Running RFC 2544 test suite..."
echo "--------------------------------------------------------------------------------"
echo "This will take approximately 30-40 minutes..."
echo "Tests: Throughput, Latency, Frame Loss, Back-to-Back"
echo ""

sudo python3 advanced_rfc2544_test.py "$TARGET_IP" "$INTERFACE" > "${MASTER_RESULTS_DIR}/02_rfc2544.log" 2>&1 &
RFC_PID=$!

# Monitor progress
echo "Test running with PID: $RFC_PID"
echo "Monitor: tail -f ${MASTER_RESULTS_DIR}/02_rfc2544.log"
echo ""

# Wait for RFC 2544 test to complete
wait $RFC_PID
RFC_EXIT=$?

if [ $RFC_EXIT -eq 0 ]; then
    echo "✓ RFC 2544 test completed"

    # Find the most recent RFC 2544 results directory
    RFC_RESULTS=$(ls -td rfc2544_results_*/ 2>/dev/null | head -1)
    if [ -n "$RFC_RESULTS" ]; then
        # Copy results to master directory
        cp -r "$RFC_RESULTS" "${MASTER_RESULTS_DIR}/"

        # Generate visualizations
        echo "  Generating visualizations..."
        python3 advanced_visualizer.py "$RFC_RESULTS" >> "${MASTER_RESULTS_DIR}/02_rfc2544.log" 2>&1
        echo "  ✓ Visualizations generated"
    fi
else
    echo "✗ RFC 2544 test failed (check ${MASTER_RESULTS_DIR}/02_rfc2544.log)"
fi
echo ""

# Test 3: Sockperf comprehensive test
echo "[3/4] Running Sockperf tests..."
echo "--------------------------------------------------------------------------------"
echo "Tests: Throughput, Ping-Pong Latency, Under-Load Latency"
echo ""

# Throughput test
echo "  [3.1] Throughput test (TCP)..."
timeout 60 sockperf tp --tcp -i "$TARGET_IP" -p 11111 -t 30 > "${MASTER_RESULTS_DIR}/03_sockperf_throughput_tcp.txt" 2>&1 || true

echo "  [3.2] Throughput test (UDP)..."
timeout 60 sockperf tp --udp -i "$TARGET_IP" -p 11111 -t 30 > "${MASTER_RESULTS_DIR}/03_sockperf_throughput_udp.txt" 2>&1 || true

# Ping-pong latency test
echo "  [3.3] Ping-pong latency test..."
timeout 60 sockperf pp -i "$TARGET_IP" -p 11111 -t 30 --msg-size=1024 > "${MASTER_RESULTS_DIR}/03_sockperf_pingpong.txt" 2>&1 || true

# Under-load latency test
echo "  [3.4] Under-load latency test..."
timeout 60 sockperf ul -i "$TARGET_IP" -p 11111 -t 30 --mps=100000 > "${MASTER_RESULTS_DIR}/03_sockperf_underload.txt" 2>&1 || true

echo "✓ Sockperf tests completed"
echo ""

# Test 4: FRER Test (if running as root)
echo "[4/4] Running FRER test..."
echo "--------------------------------------------------------------------------------"

if [ "$EUID" -ne 0 ]; then
    echo "⚠  Skipping FRER test (requires root privileges)"
    echo "   To run FRER test separately: sudo python3 frer_reliability_test.py"
else
    echo "Tests: Frame Replication, Elimination, Path Redundancy"
    echo ""

    sudo python3 frer_reliability_test.py "$TARGET_IP" "$INTERFACE" > "${MASTER_RESULTS_DIR}/04_frer.log" 2>&1 &
    FRER_PID=$!

    wait $FRER_PID
    FRER_EXIT=$?

    if [ $FRER_EXIT -eq 0 ]; then
        echo "✓ FRER test completed"

        # Copy FRER results
        FRER_RESULTS=$(ls -td frer_results_*/ 2>/dev/null | head -1)
        if [ -n "$FRER_RESULTS" ]; then
            cp -r "$FRER_RESULTS" "${MASTER_RESULTS_DIR}/"
        fi
    else
        echo "✗ FRER test failed (check ${MASTER_RESULTS_DIR}/04_frer.log)"
    fi
fi

echo ""

# Generate master summary report
echo "================================================================================"
echo "GENERATING MASTER SUMMARY REPORT"
echo "================================================================================"

SUMMARY_FILE="${MASTER_RESULTS_DIR}/MASTER_SUMMARY.md"

cat > "$SUMMARY_FILE" <<EOF
# Comprehensive Network Performance Test Report

**Date:** $(date)
**Target:** $TARGET_IP
**Interface:** $INTERFACE

## Test Suite Overview

This report contains results from a comprehensive network performance test suite including:

1. **Quick Connectivity Test** - Basic network connectivity verification
2. **RFC 2544 Test Suite** - Industry-standard performance benchmarking
   - Throughput (zero-loss)
   - Latency (min, avg, max, percentiles)
   - Frame Loss (at various load levels)
   - Back-to-Back (burst capacity)
3. **Sockperf Tests** - Latency and throughput analysis
   - TCP/UDP throughput
   - Ping-pong latency
   - Under-load latency
4. **FRER Test** - Frame Replication and Elimination for Reliability

## Test Results

EOF

# Add RFC 2544 summary if available
RFC_RESULTS=$(ls -d "${MASTER_RESULTS_DIR}"/rfc2544_results_*/ 2>/dev/null | head -1)
if [ -n "$RFC_RESULTS" ] && [ -f "${RFC_RESULTS}/SUMMARY.md" ]; then
    echo "### RFC 2544 Test Results" >> "$SUMMARY_FILE"
    echo "" >> "$SUMMARY_FILE"
    tail -n +2 "${RFC_RESULTS}/SUMMARY.md" >> "$SUMMARY_FILE"
    echo "" >> "$SUMMARY_FILE"
fi

# Add FRER summary if available
FRER_RESULTS=$(ls -d "${MASTER_RESULTS_DIR}"/frer_results_*/ 2>/dev/null | head -1)
if [ -n "$FRER_RESULTS" ] && [ -f "${FRER_RESULTS}/SUMMARY.md" ]; then
    echo "### FRER Test Results" >> "$SUMMARY_FILE"
    echo "" >> "$SUMMARY_FILE"
    tail -n +2 "${FRER_RESULTS}/SUMMARY.md" >> "$SUMMARY_FILE"
    echo "" >> "$SUMMARY_FILE"
fi

# Add sockperf summary
echo "### Sockperf Test Results" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

if [ -f "${MASTER_RESULTS_DIR}/03_sockperf_throughput_tcp.txt" ]; then
    TCP_THROUGHPUT=$(grep "Summary: Throughput is" "${MASTER_RESULTS_DIR}/03_sockperf_throughput_tcp.txt" 2>/dev/null | awk '{print $4, $5}' || echo "N/A")
    echo "- **TCP Throughput:** $TCP_THROUGHPUT" >> "$SUMMARY_FILE"
fi

if [ -f "${MASTER_RESULTS_DIR}/03_sockperf_throughput_udp.txt" ]; then
    UDP_THROUGHPUT=$(grep "Summary: Throughput is" "${MASTER_RESULTS_DIR}/03_sockperf_throughput_udp.txt" 2>/dev/null | awk '{print $4, $5}' || echo "N/A")
    echo "- **UDP Throughput:** $UDP_THROUGHPUT" >> "$SUMMARY_FILE"
fi

if [ -f "${MASTER_RESULTS_DIR}/03_sockperf_pingpong.txt" ]; then
    PINGPONG_LAT=$(grep "Summary: Latency is" "${MASTER_RESULTS_DIR}/03_sockperf_pingpong.txt" 2>/dev/null | awk '{print $4, $5}' || echo "N/A")
    echo "- **Ping-Pong Latency:** $PINGPONG_LAT" >> "$SUMMARY_FILE"
fi

echo "" >> "$SUMMARY_FILE"

echo "---" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "*Generated by D10 FRER Network Performance Test Suite*" >> "$SUMMARY_FILE"

echo "✓ Master summary report generated"

# Final summary
echo ""
echo "================================================================================"
echo "TEST SUITE COMPLETED"
echo "================================================================================"
echo "Results directory: $MASTER_RESULTS_DIR/"
echo "Summary report: $MASTER_RESULTS_DIR/MASTER_SUMMARY.md"
echo ""
echo "Contents:"
ls -lh "$MASTER_RESULTS_DIR/" | tail -n +2
echo ""
echo "To view results:"
echo "  cat $MASTER_RESULTS_DIR/MASTER_SUMMARY.md"
echo ""
echo "To view visualizations:"
RFC_PLOTS=$(ls -d "${MASTER_RESULTS_DIR}"/rfc2544_results_*/plots/ 2>/dev/null | head -1)
if [ -n "$RFC_PLOTS" ]; then
    echo "  ls $RFC_PLOTS"
fi
echo "================================================================================"
