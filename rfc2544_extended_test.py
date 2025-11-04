#!/usr/bin/env python3
"""
RFC 2544 Extended Test Suite
Additional tests: Back-to-Back Frames, Frame Loss Rate

Tests network equipment performance per RFC 2544 standard
"""

import subprocess
import json
import time
import sys
import os
import statistics
from pathlib import Path
from datetime import datetime
from scapy.all import *

class RFC2544ExtendedTest:
    def __init__(self, target_ip="192.168.1.3", interface="enp2s0"):
        self.target_ip = target_ip
        self.interface = interface

        # Create results directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_dir = Path(f"rfc2544_extended_{timestamp}")
        self.results_dir.mkdir(exist_ok=True)

        # RFC 2544 standard frame sizes (bytes)
        self.frame_sizes = [64, 128, 256, 512, 1024, 1280, 1518]

        # Test parameters
        self.trial_duration = 2  # seconds per trial
        self.num_trials = 3  # number of trials per test

    def log(self, message):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] {message}"
        print(msg)

        log_file = self.results_dir / "rfc2544_extended.log"
        with open(log_file, "a") as f:
            f.write(msg + "\n")

    def ping_test(self, count=10):
        """Quick connectivity test"""
        self.log(f"Testing connectivity to {self.target_ip}...")

        cmd = ["ping", "-c", str(count), "-W", "1", self.target_ip]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                # Extract statistics
                output = result.stdout
                for line in output.split('\n'):
                    if 'packets transmitted' in line:
                        self.log(f"  {line.strip()}")
                    elif 'rtt min/avg/max' in line:
                        self.log(f"  {line.strip()}")
                return True
            else:
                self.log(f"  Ping failed: {result.stderr}")
                return False
        except Exception as e:
            self.log(f"  Ping error: {e}")
            return False

    def back_to_back_test(self, frame_size=64, max_burst=10000):
        """
        RFC 2544 Back-to-Back Frames Test

        Measure maximum burst size that can be processed without loss

        Args:
            frame_size: Frame size in bytes
            max_burst: Maximum burst size to test

        Returns:
            dict: Test results
        """
        self.log(f"\n{'='*80}")
        self.log(f"BACK-TO-BACK FRAMES TEST - Frame Size: {frame_size} bytes")
        self.log(f"{'='*80}")

        # Binary search for maximum burst size
        min_burst = 100
        max_burst_size = max_burst
        best_burst = 0

        results = {
            "frame_size": frame_size,
            "trials": [],
            "max_burst_no_loss": 0
        }

        for trial in range(self.num_trials):
            self.log(f"\n  Trial {trial + 1}/{self.num_trials}")

            # Test increasing burst sizes
            test_bursts = [100, 500, 1000, 2000, 5000, 10000]
            burst_result = None

            for burst_size in test_bursts:
                self.log(f"    Testing burst size: {burst_size} frames")

                # Send burst using scapy
                packets_sent = 0
                packets_received = 0

                start_time = time.time()

                try:
                    # Create test packet
                    pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / \
                          IP(dst=self.target_ip) / \
                          ICMP(type=8, id=os.getpid() & 0xFFFF) / \
                          Raw(load=b"B" * (frame_size - 42))  # Adjust for headers

                    # Send burst
                    sendp([pkt] * burst_size, iface=self.interface, verbose=False, inter=0)
                    packets_sent = burst_size

                    # Wait for processing
                    time.sleep(0.5)

                    # Use iperf3 or ping to verify connectivity after burst
                    ping_cmd = ["ping", "-c", "10", "-W", "1", self.target_ip]
                    ping_result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=15)

                    # Parse packet loss
                    loss_rate = 100.0
                    for line in ping_result.stdout.split('\n'):
                        if 'packet loss' in line:
                            parts = line.split(',')
                            for part in parts:
                                if 'packet loss' in part:
                                    loss_str = part.split('%')[0].strip().split()[-1]
                                    loss_rate = float(loss_str)

                    duration = time.time() - start_time

                    self.log(f"      Sent: {packets_sent}, Loss: {loss_rate}%, Duration: {duration:.3f}s")

                    # If no loss, this is a successful burst
                    if loss_rate < 1.0:
                        best_burst = max(best_burst, burst_size)
                        self.log(f"      ✓ No loss at {burst_size} frames")
                    else:
                        self.log(f"      ✗ Loss detected at {burst_size} frames")
                        break  # Stop increasing burst size

                except Exception as e:
                    self.log(f"      Error: {e}")
                    break

            results["trials"].append({
                "trial": trial + 1,
                "max_burst": best_burst
            })

        # Calculate final result
        if results["trials"]:
            max_bursts = [t["max_burst"] for t in results["trials"]]
            results["max_burst_no_loss"] = min(max_bursts)  # Conservative estimate
            results["avg_burst"] = statistics.mean(max_bursts)
            results["std_burst"] = statistics.stdev(max_bursts) if len(max_bursts) > 1 else 0

        self.log(f"\n  RESULT:")
        self.log(f"    Max Burst (no loss): {results['max_burst_no_loss']} frames")
        self.log(f"    Average: {results.get('avg_burst', 0):.1f} frames")
        self.log(f"    Std Dev: {results.get('std_burst', 0):.1f} frames")

        return results

    def frame_loss_rate_test(self, frame_size=64, offered_loads=[10, 20, 50, 80, 100]):
        """
        RFC 2544 Frame Loss Rate Test

        Measure packet loss at various offered loads

        Args:
            frame_size: Frame size in bytes
            offered_loads: List of offered load percentages

        Returns:
            dict: Test results
        """
        self.log(f"\n{'='*80}")
        self.log(f"FRAME LOSS RATE TEST - Frame Size: {frame_size} bytes")
        self.log(f"{'='*80}")

        results = {
            "frame_size": frame_size,
            "load_tests": []
        }

        # Use iperf3 for bandwidth-based testing
        for load_pct in offered_loads:
            self.log(f"\n  Testing at {load_pct}% load")

            # Calculate target bandwidth
            # Assume 1 Gbps link for 100%
            link_speed_mbps = 1000
            target_mbps = link_speed_mbps * load_pct / 100

            load_result = {
                "offered_load_pct": load_pct,
                "target_mbps": target_mbps,
                "trials": []
            }

            for trial in range(self.num_trials):
                self.log(f"    Trial {trial + 1}/{self.num_trials}")

                # Use iperf3 UDP test
                iperf_cmd = [
                    "iperf3",
                    "-c", self.target_ip,
                    "-u",  # UDP
                    "-b", f"{target_mbps}M",  # Bandwidth
                    "-t", str(self.trial_duration),  # Duration
                    "-l", str(frame_size),  # Packet size
                    "-J"  # JSON output
                ]

                try:
                    result = subprocess.run(iperf_cmd, capture_output=True, text=True, timeout=self.trial_duration + 10)

                    if result.returncode == 0:
                        # Parse JSON output
                        data = json.loads(result.stdout)

                        sent_mbps = data["end"]["sum"]["bits_per_second"] / 1e6
                        sent_packets = data["end"]["sum"]["packets"]
                        lost_packets = data["end"]["sum"]["lost_packets"]
                        loss_percent = data["end"]["sum"]["lost_percent"]
                        jitter_ms = data["end"]["sum"]["jitter_ms"]

                        trial_result = {
                            "trial": trial + 1,
                            "sent_mbps": sent_mbps,
                            "sent_packets": sent_packets,
                            "lost_packets": lost_packets,
                            "loss_percent": loss_percent,
                            "jitter_ms": jitter_ms
                        }

                        load_result["trials"].append(trial_result)

                        self.log(f"      Sent: {sent_mbps:.2f} Mbps, "
                                f"Packets: {sent_packets}, "
                                f"Lost: {lost_packets} ({loss_percent:.2f}%), "
                                f"Jitter: {jitter_ms:.3f} ms")
                    else:
                        self.log(f"      iperf3 failed: {result.stderr}")

                except Exception as e:
                    self.log(f"      Error: {e}")

                time.sleep(1)  # Brief pause between trials

            # Calculate statistics
            if load_result["trials"]:
                loss_percentages = [t["loss_percent"] for t in load_result["trials"]]
                load_result["avg_loss_percent"] = statistics.mean(loss_percentages)
                load_result["max_loss_percent"] = max(loss_percentages)
                load_result["min_loss_percent"] = min(loss_percentages)

                self.log(f"\n    SUMMARY for {load_pct}% load:")
                self.log(f"      Avg Loss: {load_result['avg_loss_percent']:.3f}%")
                self.log(f"      Min Loss: {load_result['min_loss_percent']:.3f}%")
                self.log(f"      Max Loss: {load_result['max_loss_percent']:.3f}%")

            results["load_tests"].append(load_result)

        return results

    def run_all_tests(self):
        """Run complete RFC 2544 extended test suite"""
        self.log("=" * 80)
        self.log("RFC 2544 EXTENDED TEST SUITE")
        self.log("=" * 80)
        self.log(f"Target: {self.target_ip}")
        self.log(f"Interface: {self.interface}")
        self.log(f"Frame Sizes: {self.frame_sizes}")
        self.log("=" * 80)

        # Check if running as root
        if os.geteuid() != 0:
            self.log("\nWARNING: Back-to-Back test requires root privileges")
            self.log("Some tests may be skipped. Run with sudo for full test suite.")

        # Connectivity check
        if not self.ping_test():
            self.log("\nERROR: Cannot reach target. Aborting tests.")
            return None

        results = {
            "test_info": {
                "target_ip": self.target_ip,
                "interface": self.interface,
                "timestamp": datetime.now().isoformat()
            },
            "back_to_back": [],
            "frame_loss_rate": []
        }

        # Test 1: Back-to-Back Frames (selected frame sizes)
        if os.geteuid() == 0:
            self.log("\n" + "=" * 80)
            self.log("TEST 1: BACK-TO-BACK FRAMES")
            self.log("=" * 80)

            for frame_size in [64, 512, 1518]:  # Test subset of frame sizes
                b2b_result = self.back_to_back_test(frame_size=frame_size)
                results["back_to_back"].append(b2b_result)
                time.sleep(2)
        else:
            self.log("\nSkipping Back-to-Back test (requires root)")

        # Test 2: Frame Loss Rate (all frame sizes)
        self.log("\n" + "=" * 80)
        self.log("TEST 2: FRAME LOSS RATE")
        self.log("=" * 80)

        for frame_size in [64, 512, 1518]:  # Test subset for speed
            flr_result = self.frame_loss_rate_test(frame_size=frame_size)
            results["frame_loss_rate"].append(flr_result)
            time.sleep(2)

        # Save results
        self.log("\n" + "=" * 80)
        self.log("TEST SUITE COMPLETED")
        self.log("=" * 80)

        results_file = self.results_dir / "results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        self.log(f"Results saved to: {results_file}")

        # Generate summary report
        self.generate_summary_report(results)

        return results

    def generate_summary_report(self, results):
        """Generate markdown summary report"""
        report_file = self.results_dir / "SUMMARY.md"

        with open(report_file, "w") as f:
            f.write("# RFC 2544 Extended Test Report\n\n")
            f.write("Additional Performance Tests: Back-to-Back Frames & Frame Loss Rate\n\n")

            # Test Information
            f.write("## Test Information\n\n")
            info = results["test_info"]
            f.write(f"- **Target IP:** {info['target_ip']}\n")
            f.write(f"- **Interface:** {info['interface']}\n")
            f.write(f"- **Test Date:** {info['timestamp']}\n\n")

            # Back-to-Back Results
            if results.get("back_to_back"):
                f.write("## Back-to-Back Frames Test\n\n")
                f.write("Maximum burst size that can be processed without loss:\n\n")
                f.write("| Frame Size (bytes) | Max Burst (frames) | Avg Burst | Std Dev |\n")
                f.write("|-------------------:|-------------------:|----------:|--------:|\n")

                for b2b in results["back_to_back"]:
                    f.write(f"| {b2b['frame_size']} | "
                           f"{b2b['max_burst_no_loss']} | "
                           f"{b2b.get('avg_burst', 0):.1f} | "
                           f"{b2b.get('std_burst', 0):.1f} |\n")
                f.write("\n")

            # Frame Loss Rate Results
            if results.get("frame_loss_rate"):
                f.write("## Frame Loss Rate Test\n\n")

                for flr in results["frame_loss_rate"]:
                    f.write(f"### Frame Size: {flr['frame_size']} bytes\n\n")
                    f.write("| Offered Load (%) | Target (Mbps) | Avg Loss (%) | Min Loss (%) | Max Loss (%) |\n")
                    f.write("|-----------------:|--------------:|-------------:|-------------:|-------------:|\n")

                    for load_test in flr["load_tests"]:
                        if load_test.get("trials"):
                            f.write(f"| {load_test['offered_load_pct']} | "
                                   f"{load_test['target_mbps']} | "
                                   f"{load_test.get('avg_loss_percent', 0):.3f} | "
                                   f"{load_test.get('min_loss_percent', 0):.3f} | "
                                   f"{load_test.get('max_loss_percent', 0):.3f} |\n")
                    f.write("\n")

            f.write("---\n\n")
            f.write("*Generated by RFC 2544 Extended Test Suite*\n")

        self.log(f"Summary report saved to: {report_file}")

def main():
    """Main function"""
    target_ip = "192.168.1.3"
    interface = "enp2s0"

    if len(sys.argv) > 1:
        target_ip = sys.argv[1]
    if len(sys.argv) > 2:
        interface = sys.argv[2]

    print("=" * 80)
    print("RFC 2544 EXTENDED TEST SUITE")
    print("=" * 80)
    print(f"Target: {target_ip}")
    print(f"Interface: {interface}")
    print("=" * 80)
    print()

    if os.geteuid() != 0:
        print("WARNING: Some tests require root privileges")
        print("Run with sudo for complete test suite:")
        print(f"  sudo python3 {sys.argv[0]} {target_ip} {interface}")
        print()
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(0)

    tester = RFC2544ExtendedTest(target_ip=target_ip, interface=interface)
    results = tester.run_all_tests()

    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print(f"Results directory: {tester.results_dir}/")
    print(f"Summary report: {tester.results_dir}/SUMMARY.md")
    print("=" * 80)

if __name__ == "__main__":
    main()
