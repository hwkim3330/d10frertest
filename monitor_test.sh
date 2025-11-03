#!/bin/bash
# Monitor the running test

TEST_DIR="/home/kim/d10frertest"
cd "$TEST_DIR"

# Find the most recent log file
LOG_FILE=$(ls -t test_execution_*.log 2>/dev/null | head -1)

if [ -z "$LOG_FILE" ]; then
    echo "No test log file found"
    exit 1
fi

echo "Monitoring test progress: $LOG_FILE"
echo "Press Ctrl+C to stop monitoring (test will continue running)"
echo "=========================================="
echo ""

tail -f "$LOG_FILE"
