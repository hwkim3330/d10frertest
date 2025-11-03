# D10 FRER Network Performance Test Suite

Comprehensive network performance testing suite implementing RFC 2544 benchmarking methodology, sockperf latency/throughput testing, and FRER (Frame Replication and Elimination for Reliability) evaluation.

## Test Configuration

- **Client:** 192.168.1.2 (enp2s0)
- **Server:** 192.168.1.3
- **Test Date:** 2025-11-03
- **Standards:** RFC 2544, IEEE 802.1CB (FRER)

## Test Suite Components

### 1. Sockperf Tests
- **Throughput Test:** TCP and UDP throughput measurement at various message rates
- **Ping-Pong Latency:** Round-trip latency measurement with different message sizes (64-1472 bytes)
- **Under-Load Latency:** Latency measurement under high load conditions

### 2. RFC 2544 Tests
- **Throughput:** Binary search to find maximum zero-loss throughput for frame sizes: 64, 128, 256, 512, 1024, 1280, 1518 bytes
- **Latency:** Round-trip latency measurement across different frame sizes
- **Frame Loss:** Packet loss measurement at various load percentages (50%, 75%, 90%, 95%, 98%, 100%)
- **Back-to-Back Frames:** Maximum burst size without frame loss

### 3. FRER Test
- Frame Replication and Elimination for Reliability (IEEE 802.1CB)
- Requires TSN-capable switch

## Prerequisites

### Server (192.168.1.3)
```bash
# Install required packages
sudo apt-get update
sudo apt-get install -y sockperf iperf3

# Or run the setup script
./setup_server.sh
```

### Client (192.168.1.2)
```bash
# Install required packages
sudo apt-get install -y sockperf iperf3 python3-matplotlib python3-numpy

# Or use pip
pip3 install matplotlib numpy
```

## Quick Start

### Step 1: Setup Server (on 192.168.1.3)
```bash
# Copy and run setup script on server
scp setup_server.sh user@192.168.1.3:~/
ssh user@192.168.1.3
./setup_server.sh
```

### Step 2: Run Tests (on 192.168.1.2)
```bash
# Run comprehensive test suite
sudo python3 comprehensive_network_test.py

# This will create a timestamped results directory
# Example: test_results_20251103_140000/
```

### Step 3: Generate Visualizations
```bash
# Generate plots and summary report
python3 visualize_results.py test_results_20251103_140000/

# View results
cd test_results_20251103_140000/
cat summary_report.md
ls plots/
```

### Step 4: Stop Server (on 192.168.1.3)
```bash
./stop_server.sh
```

## Test Results

Results are saved in timestamped directories with the following structure:

```
test_results_YYYYMMDD_HHMMSS/
├── comprehensive_results.json          # Complete test results (JSON)
├── summary_report.md                   # Markdown summary report
├── sockperf_throughput.txt            # Sockperf throughput logs
├── sockperf_latency_pingpong.txt      # Sockperf ping-pong logs
├── sockperf_latency_underload.txt     # Sockperf under-load logs
├── rfc2544_throughput.json            # RFC 2544 throughput data
├── rfc2544_latency.json               # RFC 2544 latency data
├── rfc2544_frame_loss.json            # RFC 2544 frame loss data
├── rfc2544_back_to_back.json          # RFC 2544 back-to-back data
└── plots/                              # Visualization plots
    ├── rfc2544_throughput.png
    ├── rfc2544_latency.png
    ├── rfc2544_frame_loss.png
    └── rfc2544_back_to_back.png
```

## Individual Test Execution

### Sockperf Tests

```bash
# Server (192.168.1.3)
sockperf sr --tcp -i 192.168.1.3 -p 11111

# Client (192.168.1.2)
# Throughput
sockperf tp --tcp -i 192.168.1.3 -p 11111 -t 30

# Ping-pong latency
sockperf pp -i 192.168.1.3 -p 11111 -t 30 --msg-size=1024

# Under-load latency
sockperf ul -i 192.168.1.3 -p 11111 -t 30 --mps=100000
```

### RFC 2544 Tests (using iperf3)

```bash
# Server (192.168.1.3)
iperf3 -s

# Client (192.168.1.2)
# Throughput test
iperf3 -c 192.168.1.3 -u -b 500M -t 30 -l 1024

# Latency test (using ping)
ping -c 1000 -s 1024 192.168.1.3
```

## RFC 2544 Methodology

### Throughput Test
Uses binary search algorithm to determine maximum throughput with zero frame loss:
1. Start with min=1 Mbps, max=1000 Mbps
2. Test at midpoint rate
3. If loss < 0.001%, increase rate (min = midpoint)
4. If loss >= 0.001%, decrease rate (max = midpoint)
5. Converge to 1% tolerance

### Frame Loss Test
Measures packet loss at different load percentages:
- 50%, 75%, 90%, 95%, 98%, 100% of line rate
- Tests all standard frame sizes
- 30-second test duration per configuration

### Latency Test
Measures round-trip time using ICMP ping:
- 1000 packets per frame size
- Statistical analysis: min, max, avg, median, stddev, 99th percentile
- Sub-millisecond interval between packets

### Back-to-Back Test
Measures maximum burst size:
- Send frames at maximum rate for 2 seconds
- Measure frames transmitted without loss
- Indicates buffer capacity

## Performance Metrics

### Throughput
- Measured in Mbps (Megabits per second)
- Zero-loss threshold: < 0.001% packet loss

### Latency
- Measured in milliseconds (ms)
- Metrics: min, avg, max, median, stddev, 99th percentile
- One-way latency = RTT / 2

### Frame Loss
- Measured in percentage (%)
- Calculated as: (lost_packets / sent_packets) × 100

### Jitter
- Latency variation
- Calculated from standard deviation

## Hardware Requirements

- **NICs:** TSN-capable for FRER tests (Intel i210/i225 recommended)
- **Switch:** IEEE 802.1CB compliant for FRER
- **Cable:** Cat6 or better for 1 Gbps testing
- **Network:** Dedicated test network recommended

## Troubleshooting

### Server Not Responding
```bash
# Check if servers are running
ssh user@192.168.1.3 "ps aux | grep -E 'sockperf|iperf3'"

# Check firewall
sudo ufw allow 11111/tcp
sudo ufw allow 5201/tcp
sudo ufw allow 5201/udp

# Restart servers
ssh user@192.168.1.3 "./stop_server.sh && ./setup_server.sh"
```

### Permission Denied
```bash
# Run with sudo for network operations
sudo python3 comprehensive_network_test.py
```

### Missing Dependencies
```bash
# Client
sudo apt-get install -y sockperf iperf3 python3-matplotlib python3-numpy

# Server
sudo apt-get install -y sockperf iperf3
```

## Publications & References

- RFC 2544: Benchmarking Methodology for Network Interconnect Devices
- IEEE 802.1CB: Frame Replication and Elimination for Reliability
- Sockperf: https://github.com/Mellanox/sockperf
- iperf3: https://software.es.net/iperf/

## Test Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| Test Duration | 30 seconds | Per test iteration |
| Frame Sizes | 64, 128, 256, 512, 1024, 1280, 1518 bytes | RFC 2544 standard sizes |
| Load Levels | 50%, 75%, 90%, 95%, 98%, 100% | For frame loss testing |
| Convergence Tolerance | 1% | For binary search |
| Loss Threshold | 0.001% | Zero-loss definition |
| Ping Count | 1000 packets | For latency testing |

## License

MIT License

## Author

Network Performance Testing Lab
2025-11-03

---

**Note:** This test suite is designed for controlled lab environments. Ensure proper authorization before testing on production networks.
