#!/usr/bin/env python3
"""
Quick network test - doesn't require server setup
Tests that work without remote server configuration
"""

import subprocess
import json
import time
import datetime
import os
import statistics
from pathlib import Path

TARGET_IP = "192.168.1.3"
LOCAL_IP = "192.168.1.2"
RESULTS_DIR = f"quick_test_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)

class QuickTester:
    def __init__(self):
        self.results = {
            "test_info": {
                "target_ip": TARGET_IP,
                "local_ip": LOCAL_IP,
                "timestamp": datetime.datetime.now().isoformat()
            }
        }

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def run_command(self, cmd, timeout=None):
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return "", "Timeout expired", -1
        except Exception as e:
            return "", str(e), -1

    def test_basic_connectivity(self):
        """Test basic connectivity and RTT"""
        self.log("Testing basic connectivity...")

        cmd = f"ping -c 100 -i 0.01 {TARGET_IP}"
        stdout, stderr, rc = self.run_command(cmd, timeout=30)

        latencies = []
        for line in stdout.split('\n'):
            if 'time=' in line:
                try:
                    time_str = line.split('time=')[1].split()[0]
                    latencies.append(float(time_str))
                except (IndexError, ValueError):
                    pass

        if latencies:
            results = {
                'packets_sent': 100,
                'packets_received': len(latencies),
                'packet_loss_percent': (100 - len(latencies)),
                'min_ms': min(latencies),
                'max_ms': max(latencies),
                'avg_ms': statistics.mean(latencies),
                'median_ms': statistics.median(latencies),
                'stdev_ms': statistics.stdev(latencies) if len(latencies) > 1 else 0
            }
        else:
            results = {'error': 'No response'}

        self.results['basic_connectivity'] = results
        self.log(f"  Average latency: {results.get('avg_ms', 'N/A'):.3f} ms")
        return results

    def test_rfc2544_latency_detailed(self):
        """RFC 2544 Latency Test - Detailed"""
        self.log("Starting detailed RFC 2544 Latency Test...")

        frame_sizes = [64, 128, 256, 512, 1024, 1280, 1518]
        results = {}

        for frame_size in frame_sizes:
            self.log(f"  Testing frame size {frame_size} bytes...")

            ping_size = frame_size - 8 if frame_size > 8 else 56
            cmd = f"ping -c 1000 -s {ping_size} -i 0.001 {TARGET_IP}"
            stdout, stderr, rc = self.run_command(cmd, timeout=60)

            latencies = []
            for line in stdout.split('\n'):
                if 'time=' in line:
                    try:
                        time_str = line.split('time=')[1].split()[0]
                        latencies.append(float(time_str))
                    except (IndexError, ValueError):
                        pass

            if latencies:
                sorted_lat = sorted(latencies)
                results[f'frame_{frame_size}'] = {
                    'frame_size': frame_size,
                    'count': len(latencies),
                    'min_ms': min(latencies),
                    'max_ms': max(latencies),
                    'avg_ms': statistics.mean(latencies),
                    'median_ms': statistics.median(latencies),
                    'stdev_ms': statistics.stdev(latencies) if len(latencies) > 1 else 0,
                    'percentile_50': sorted_lat[int(len(sorted_lat) * 0.50)],
                    'percentile_95': sorted_lat[int(len(sorted_lat) * 0.95)],
                    'percentile_99': sorted_lat[int(len(sorted_lat) * 0.99)],
                    'percentile_999': sorted_lat[int(len(sorted_lat) * 0.999)] if len(sorted_lat) >= 1000 else sorted_lat[-1]
                }
                self.log(f"    Avg: {results[f'frame_{frame_size}']['avg_ms']:.3f} ms, "
                        f"99th: {results[f'frame_{frame_size}']['percentile_99']:.3f} ms")

        self.results['rfc2544_latency'] = results

        # Save results
        with open(f"{RESULTS_DIR}/rfc2544_latency.json", 'w') as f:
            json.dump(results, f, indent=2)

        self.log("RFC 2544 Latency Test completed")
        return results

    def test_iperf3_check(self):
        """Check if iperf3 server is available"""
        self.log("Checking iperf3 server availability...")

        cmd = f"iperf3 -c {TARGET_IP} -t 5 --json"
        stdout, stderr, rc = self.run_command(cmd, timeout=10)

        if rc == 0:
            try:
                data = json.loads(stdout)
                self.log("  iperf3 server is available!")
                return True
            except json.JSONDecodeError:
                pass

        self.log("  iperf3 server not available (this is OK)")
        return False

    def test_sockperf_check(self):
        """Check if sockperf server is available"""
        self.log("Checking sockperf server availability...")

        # Try ping-pong mode with 1 second timeout
        cmd = f"timeout 5 sockperf pp -i {TARGET_IP} -p 11111 -t 1 2>&1"
        stdout, stderr, rc = self.run_command(cmd, timeout=10)

        if "connection refused" in stdout.lower() or "connection refused" in stderr.lower():
            self.log("  sockperf server not available (connection refused)")
            return False
        elif "summary" in stdout.lower():
            self.log("  sockperf server is available!")
            return True
        else:
            self.log("  sockperf server not available")
            return False

    def run_quick_tests(self):
        """Run quick tests without server setup"""
        self.log("="*80)
        self.log("QUICK NETWORK PERFORMANCE TESTS")
        self.log(f"Target: {TARGET_IP}")
        self.log(f"Local: {LOCAL_IP}")
        self.log("="*80)

        # Basic connectivity
        self.test_basic_connectivity()

        # Check servers
        iperf3_available = self.test_iperf3_check()
        sockperf_available = self.test_sockperf_check()

        # RFC 2544 Latency (works without server)
        self.test_rfc2544_latency_detailed()

        # Save all results
        output_file = f"{RESULTS_DIR}/quick_test_results.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        self.log("="*80)
        self.log("QUICK TESTS COMPLETED")
        self.log(f"Results saved to: {RESULTS_DIR}/")
        self.log("")
        self.log("NEXT STEPS:")
        if not iperf3_available or not sockperf_available:
            self.log("")
            self.log("To run full tests, please start servers on 192.168.1.3:")
            self.log("")
            self.log("Option 1: Manual setup on 192.168.1.3")
            self.log("  # Install packages")
            self.log("  sudo apt-get install -y sockperf iperf3")
            self.log("")
            self.log("  # Start sockperf server")
            self.log("  sockperf sr --tcp -p 11111 &")
            self.log("")
            self.log("  # Start iperf3 server")
            self.log("  iperf3 -s &")
            self.log("")
            self.log("Option 2: Copy and run setup script")
            self.log(f"  scp setup_server.sh user@{TARGET_IP}:~/")
            self.log(f"  ssh user@{TARGET_IP} ./setup_server.sh")
            self.log("")
            self.log("Then run: sudo python3 comprehensive_network_test.py")
        else:
            self.log("All servers are available!")
            self.log("You can now run: sudo python3 comprehensive_network_test.py")
        self.log("="*80)

        return True


def main():
    tester = QuickTester()
    tester.run_quick_tests()


if __name__ == "__main__":
    main()
