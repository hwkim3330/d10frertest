#!/bin/bash
# Run comprehensive network test in background with logging

TEST_DIR="/home/kim/d10frertest"
cd "$TEST_DIR"

# Create timestamp for this test run
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULT_DIR="test_results_${TIMESTAMP}"
LOG_FILE="test_execution_${TIMESTAMP}.log"

echo "Starting comprehensive network performance test..."
echo "Test results will be saved to: $RESULT_DIR"
echo "Log file: $LOG_FILE"
echo ""
echo "To monitor progress in real-time, run:"
echo "  tail -f $TEST_DIR/$LOG_FILE"
echo ""

# Run test with sudo and redirect all output to log file
nohup sudo -S python3 comprehensive_network_test.py > "$LOG_FILE" 2>&1 <<EOF &
1
EOF

TEST_PID=$!
echo "Test started with PID: $TEST_PID"
echo $TEST_PID > test_run.pid

echo ""
echo "Commands:"
echo "  Monitor: tail -f $LOG_FILE"
echo "  Check status: ps -p \$(cat test_run.pid)"
echo "  Stop test: kill \$(cat test_run.pid)"
echo ""
echo "Waiting 5 seconds to check if test started successfully..."
sleep 5

if ps -p $TEST_PID > /dev/null; then
    echo "✓ Test is running successfully"
else
    echo "✗ Test failed to start. Check log: $LOG_FILE"
fi
