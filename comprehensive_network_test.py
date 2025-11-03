#!/usr/bin/env python3
"""
Comprehensive Network Performance Testing Suite
Target: 192.168.1.3
Local: 192.168.1.2

Tests:
1. Sockperf - Throughput & Latency
2. RFC 2544 - Throughput, Latency, Frame Loss, Back-to-Back
3. FRER - Frame Replication and Elimination

Author: Automated Test Suite
Date: 2025-11-03
"""

import subprocess
import json
import time
import datetime
import os
import sys
import statistics
from pathlib import Path

# Test configuration
TARGET_IP = "192.168.1.3"
LOCAL_IP = "192.168.1.2"
INTERFACE = "enp2s0"
TEST_DURATION = 30  # seconds for each test
RESULTS_DIR = f"test_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Create results directory
Path(RESULTS_DIR).mkdir(parents=True, exist_ok=True)

class NetworkTester:
    def __init__(self):
        self.results = {
            "test_info": {
                "target_ip": TARGET_IP,
                "local_ip": LOCAL_IP,
                "interface": INTERFACE,
                "timestamp": datetime.datetime.now().isoformat(),
                "duration_per_test": TEST_DURATION
            },
            "sockperf": {},
            "rfc2544": {},
            "frer": {}
        }

    def log(self, message):
        """Log with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

    def run_command(self, cmd, timeout=None):
        """Run shell command and return output"""
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

    def test_sockperf_throughput(self):
        """Test throughput using sockperf"""
        self.log("Starting Sockperf Throughput Test...")

        # Note: Server must be running on 192.168.1.3:11111
        # Command: sockperf sr --tcp -i 192.168.1.3 -p 11111

        results = {}

        # TCP Throughput
        self.log("  Testing TCP throughput...")
        cmd = f"sockperf tp --tcp -i {TARGET_IP} -p 11111 -t {TEST_DURATION} --full-log /tmp/sockperf_tcp.log"
        stdout, stderr, rc = self.run_command(cmd, timeout=TEST_DURATION+10)

        # Parse results
        if rc == 0:
            for line in stdout.split('\n'):
                if 'BandWidth' in line or 'throughput' in line.lower():
                    results['tcp_output'] = line
                if 'Summary:' in line:
                    results['tcp_summary'] = line

        results['tcp_stdout'] = stdout
        results['tcp_stderr'] = stderr

        # UDP Throughput - multiple message rates
        message_rates = [10000, 50000, 100000]  # messages per second
        udp_results = []

        for rate in message_rates:
            self.log(f"  Testing UDP throughput at {rate} msg/sec...")
            cmd = f"sockperf tp --udp -i {TARGET_IP} -p 11111 -t {TEST_DURATION} --mps={rate} --msg-size=1472"
            stdout, stderr, rc = self.run_command(cmd, timeout=TEST_DURATION+10)

            udp_results.append({
                'rate': rate,
                'output': stdout,
                'stderr': stderr
            })

        results['udp_tests'] = udp_results

        self.results['sockperf']['throughput'] = results

        # Save raw output
        with open(f"{RESULTS_DIR}/sockperf_throughput.txt", 'w') as f:
            f.write(f"TCP Test:\n{results.get('tcp_stdout', '')}\n\n")
            for udp in udp_results:
                f.write(f"UDP Test ({udp['rate']} msg/sec):\n{udp['output']}\n\n")

        self.log("Sockperf Throughput Test completed")
        return results

    def test_sockperf_latency_pingpong(self):
        """Test latency using sockperf ping-pong mode"""
        self.log("Starting Sockperf Ping-Pong Latency Test...")

        results = {}

        # Ping-pong mode - various message sizes
        msg_sizes = [64, 256, 512, 1024, 1472]

        for size in msg_sizes:
            self.log(f"  Testing ping-pong with {size} byte messages...")
            cmd = f"sockperf pp -i {TARGET_IP} -p 11111 -t {TEST_DURATION} --msg-size={size}"
            stdout, stderr, rc = self.run_command(cmd, timeout=TEST_DURATION+10)

            # Parse latency statistics
            latency_data = {
                'message_size': size,
                'raw_output': stdout
            }

            # Extract key metrics
            for line in stdout.split('\n'):
                if 'percentile' in line.lower() or 'latency' in line.lower():
                    latency_data['stats'] = latency_data.get('stats', [])
                    latency_data['stats'].append(line.strip())

            results[f'size_{size}'] = latency_data

        self.results['sockperf']['latency_pingpong'] = results

        # Save raw output
        with open(f"{RESULTS_DIR}/sockperf_latency_pingpong.txt", 'w') as f:
            for size, data in results.items():
                f.write(f"Message Size: {size}\n{data['raw_output']}\n\n")

        self.log("Sockperf Ping-Pong Latency Test completed")
        return results

    def test_sockperf_latency_underload(self):
        """Test latency under load using sockperf"""
        self.log("Starting Sockperf Under-Load Latency Test...")

        results = {}

        # Under load test - high message rate
        load_rates = [50000, 100000, 150000]

        for rate in load_rates:
            self.log(f"  Testing under-load latency at {rate} msg/sec...")
            cmd = f"sockperf ul -i {TARGET_IP} -p 11111 -t {TEST_DURATION} --mps={rate} --msg-size=1024"
            stdout, stderr, rc = self.run_command(cmd, timeout=TEST_DURATION+10)

            results[f'rate_{rate}'] = {
                'rate': rate,
                'raw_output': stdout,
                'stderr': stderr
            }

        self.results['sockperf']['latency_underload'] = results

        # Save raw output
        with open(f"{RESULTS_DIR}/sockperf_latency_underload.txt", 'w') as f:
            for rate_key, data in results.items():
                f.write(f"Load Rate: {data['rate']} msg/sec\n{data['raw_output']}\n\n")

        self.log("Sockperf Under-Load Latency Test completed")
        return results

    def test_rfc2544_throughput(self):
        """RFC 2544 Throughput Test with binary search"""
        self.log("Starting RFC 2544 Throughput Test...")

        results = {}
        frame_sizes = [64, 128, 256, 512, 1024, 1280, 1518]

        for frame_size in frame_sizes:
            self.log(f"  Testing with frame size {frame_size} bytes...")

            # Binary search for maximum throughput with 0% loss
            min_rate = 1  # Mbps
            max_rate = 1000  # Mbps
            tolerance = 0.01  # 1% tolerance

            best_rate = 0
            iterations = []

            for iteration in range(10):  # Max 10 iterations
                test_rate = (min_rate + max_rate) / 2

                self.log(f"    Iteration {iteration+1}: Testing {test_rate:.2f} Mbps...")

                # Use iperf3 for throughput testing
                cmd = f"iperf3 -c {TARGET_IP} -u -b {test_rate}M -t {TEST_DURATION} -l {frame_size} --json"
                stdout, stderr, rc = self.run_command(cmd, timeout=TEST_DURATION+10)

                try:
                    iperf_data = json.loads(stdout)
                    loss_percent = iperf_data['end']['sum']['lost_percent']
                    actual_rate = iperf_data['end']['sum']['bits_per_second'] / 1e6  # Convert to Mbps

                    iterations.append({
                        'target_rate': test_rate,
                        'actual_rate': actual_rate,
                        'loss_percent': loss_percent
                    })

                    if loss_percent < 0.001:  # < 0.001% loss
                        best_rate = test_rate
                        min_rate = test_rate
                    else:
                        max_rate = test_rate

                    if (max_rate - min_rate) / max_rate < tolerance:
                        break

                except (json.JSONDecodeError, KeyError) as e:
                    self.log(f"    Error parsing iperf3 output: {e}")
                    iterations.append({
                        'target_rate': test_rate,
                        'error': str(e)
                    })

            results[f'frame_{frame_size}'] = {
                'frame_size': frame_size,
                'max_throughput_mbps': best_rate,
                'iterations': iterations
            }

        self.results['rfc2544']['throughput'] = results

        # Save results
        with open(f"{RESULTS_DIR}/rfc2544_throughput.json", 'w') as f:
            json.dump(results, f, indent=2)

        self.log("RFC 2544 Throughput Test completed")
        return results

    def test_rfc2544_latency(self):
        """RFC 2544 Latency Test"""
        self.log("Starting RFC 2544 Latency Test...")

        results = {}
        frame_sizes = [64, 128, 256, 512, 1024, 1280, 1518]

        for frame_size in frame_sizes:
            self.log(f"  Testing latency with frame size {frame_size} bytes...")

            # Use ping with specific packet size
            # Note: ICMP header is 8 bytes, so we subtract that
            ping_size = frame_size - 8 if frame_size > 8 else 56

            cmd = f"ping -c 1000 -s {ping_size} -i 0.001 {TARGET_IP}"
            stdout, stderr, rc = self.run_command(cmd, timeout=60)

            # Parse ping statistics
            latencies = []
            for line in stdout.split('\n'):
                if 'time=' in line:
                    try:
                        time_str = line.split('time=')[1].split()[0]
                        latencies.append(float(time_str))
                    except (IndexError, ValueError):
                        pass

            if latencies:
                results[f'frame_{frame_size}'] = {
                    'frame_size': frame_size,
                    'count': len(latencies),
                    'min_ms': min(latencies),
                    'max_ms': max(latencies),
                    'avg_ms': statistics.mean(latencies),
                    'median_ms': statistics.median(latencies),
                    'stdev_ms': statistics.stdev(latencies) if len(latencies) > 1 else 0,
                    'percentile_99': sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 100 else max(latencies)
                }

        self.results['rfc2544']['latency'] = results

        # Save results
        with open(f"{RESULTS_DIR}/rfc2544_latency.json", 'w') as f:
            json.dump(results, f, indent=2)

        self.log("RFC 2544 Latency Test completed")
        return results

    def test_rfc2544_frame_loss(self):
        """RFC 2544 Frame Loss Test"""
        self.log("Starting RFC 2544 Frame Loss Test...")

        results = {}
        frame_sizes = [64, 128, 256, 512, 1024, 1280, 1518]
        load_percentages = [50, 75, 90, 95, 98, 100]

        for frame_size in frame_sizes:
            self.log(f"  Testing frame loss with frame size {frame_size} bytes...")

            frame_results = {}

            for load_pct in load_percentages:
                # Assume 1 Gbps link, calculate rate
                max_rate = 1000  # Mbps
                test_rate = max_rate * (load_pct / 100.0)

                self.log(f"    Testing at {load_pct}% load ({test_rate:.2f} Mbps)...")

                cmd = f"iperf3 -c {TARGET_IP} -u -b {test_rate}M -t {TEST_DURATION} -l {frame_size} --json"
                stdout, stderr, rc = self.run_command(cmd, timeout=TEST_DURATION+10)

                try:
                    iperf_data = json.loads(stdout)
                    sent = iperf_data['end']['sum']['packets']
                    lost = iperf_data['end']['sum']['lost_packets']
                    loss_percent = iperf_data['end']['sum']['lost_percent']

                    frame_results[f'load_{load_pct}'] = {
                        'load_percent': load_pct,
                        'sent_packets': sent,
                        'lost_packets': lost,
                        'loss_percent': loss_percent
                    }

                except (json.JSONDecodeError, KeyError) as e:
                    self.log(f"    Error parsing iperf3 output: {e}")
                    frame_results[f'load_{load_pct}'] = {'error': str(e)}

            results[f'frame_{frame_size}'] = {
                'frame_size': frame_size,
                'tests': frame_results
            }

        self.results['rfc2544']['frame_loss'] = results

        # Save results
        with open(f"{RESULTS_DIR}/rfc2544_frame_loss.json", 'w') as f:
            json.dump(results, f, indent=2)

        self.log("RFC 2544 Frame Loss Test completed")
        return results

    def test_rfc2544_back_to_back(self):
        """RFC 2544 Back-to-Back Frames Test"""
        self.log("Starting RFC 2544 Back-to-Back Frames Test...")

        results = {}
        frame_sizes = [64, 128, 256, 512, 1024, 1518]

        for frame_size in frame_sizes:
            self.log(f"  Testing back-to-back with frame size {frame_size} bytes...")

            # Send burst at maximum rate for 2 seconds
            burst_duration = 2

            cmd = f"iperf3 -c {TARGET_IP} -u -b 0 -t {burst_duration} -l {frame_size} --json"
            stdout, stderr, rc = self.run_command(cmd, timeout=burst_duration+10)

            try:
                iperf_data = json.loads(stdout)
                sent = iperf_data['end']['sum']['packets']
                lost = iperf_data['end']['sum']['lost_packets']
                loss_percent = iperf_data['end']['sum']['lost_percent']
                bitrate = iperf_data['end']['sum']['bits_per_second']

                results[f'frame_{frame_size}'] = {
                    'frame_size': frame_size,
                    'duration_sec': burst_duration,
                    'frames_sent': sent,
                    'frames_lost': lost,
                    'loss_percent': loss_percent,
                    'bitrate_bps': bitrate,
                    'bitrate_mbps': bitrate / 1e6
                }

            except (json.JSONDecodeError, KeyError) as e:
                self.log(f"    Error parsing iperf3 output: {e}")
                results[f'frame_{frame_size}'] = {'error': str(e)}

        self.results['rfc2544']['back_to_back'] = results

        # Save results
        with open(f"{RESULTS_DIR}/rfc2544_back_to_back.json", 'w') as f:
            json.dump(results, f, indent=2)

        self.log("RFC 2544 Back-to-Back Frames Test completed")
        return results

    def test_frer(self):
        """FRER (Frame Replication and Elimination) Test"""
        self.log("Starting FRER Test...")

        # Note: FRER requires specific switch/network configuration
        # This is a placeholder for FRER testing logic

        results = {
            'note': 'FRER test requires specialized hardware and configuration',
            'test_performed': False,
            'reason': 'Implementation pending - requires TSN switch with FRER capability'
        }

        self.results['frer'] = results

        self.log("FRER Test - Configuration Required")
        return results

    def save_results(self):
        """Save all results to JSON file"""
        output_file = f"{RESULTS_DIR}/comprehensive_results.json"

        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        self.log(f"Results saved to {output_file}")
        return output_file

    def run_all_tests(self):
        """Run all tests in sequence"""
        self.log("="*80)
        self.log("COMPREHENSIVE NETWORK PERFORMANCE TEST SUITE")
        self.log(f"Target: {TARGET_IP}")
        self.log(f"Local: {LOCAL_IP}")
        self.log(f"Interface: {INTERFACE}")
        self.log("="*80)

        # Check connectivity
        self.log("Checking connectivity...")
        stdout, stderr, rc = self.run_command(f"ping -c 3 {TARGET_IP}")
        if rc != 0:
            self.log(f"ERROR: Cannot reach {TARGET_IP}")
            return False
        self.log("Connectivity OK")

        # Sockperf tests
        try:
            self.test_sockperf_throughput()
        except Exception as e:
            self.log(f"Sockperf throughput test failed: {e}")

        try:
            self.test_sockperf_latency_pingpong()
        except Exception as e:
            self.log(f"Sockperf ping-pong test failed: {e}")

        try:
            self.test_sockperf_latency_underload()
        except Exception as e:
            self.log(f"Sockperf under-load test failed: {e}")

        # RFC 2544 tests
        try:
            self.test_rfc2544_throughput()
        except Exception as e:
            self.log(f"RFC 2544 throughput test failed: {e}")

        try:
            self.test_rfc2544_latency()
        except Exception as e:
            self.log(f"RFC 2544 latency test failed: {e}")

        try:
            self.test_rfc2544_frame_loss()
        except Exception as e:
            self.log(f"RFC 2544 frame loss test failed: {e}")

        try:
            self.test_rfc2544_back_to_back()
        except Exception as e:
            self.log(f"RFC 2544 back-to-back test failed: {e}")

        # FRER test
        try:
            self.test_frer()
        except Exception as e:
            self.log(f"FRER test failed: {e}")

        # Save results
        self.save_results()

        self.log("="*80)
        self.log("ALL TESTS COMPLETED")
        self.log(f"Results saved to: {RESULTS_DIR}/")
        self.log("="*80)

        return True


def main():
    """Main function"""
    if os.geteuid() != 0:
        print("WARNING: Some tests may require root privileges")
        print("Consider running with sudo for full functionality")

    tester = NetworkTester()
    success = tester.run_all_tests()

    if success:
        print("\nTest suite completed successfully!")
        print(f"Results directory: {RESULTS_DIR}/")
    else:
        print("\nTest suite encountered errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
