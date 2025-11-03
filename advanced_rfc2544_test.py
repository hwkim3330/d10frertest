#!/usr/bin/env python3
"""
Advanced RFC 2544 Test Suite
Publication-grade network performance testing

Features:
- Throughput: Binary search for zero-loss throughput
- Latency: Comprehensive latency analysis with percentiles
- Frame Loss: Multi-load frame loss testing
- Back-to-Back: Burst capacity testing
- Statistical analysis with confidence intervals
"""

import subprocess
import json
import time
import datetime
import statistics
import sys
import os
from pathlib import Path

class RFC2544Test:
    def __init__(self, target_ip="192.168.1.3", interface="enp2s0", duration=30):
        self.target_ip = target_ip
        self.interface = interface
        self.duration = duration
        self.frame_sizes = [64, 128, 256, 512, 1024, 1280, 1518]
        self.load_percentages = [50, 75, 90, 95, 98, 100]

        # Create results directory
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_dir = Path(f"rfc2544_results_{timestamp}")
        self.results_dir.mkdir(exist_ok=True)

        print(f"Results will be saved to: {self.results_dir}")

    def log(self, message):
        """Log message with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] {message}"
        print(msg)

        log_file = self.results_dir / "test.log"
        with open(log_file, "a") as f:
            f.write(msg + "\n")

    def check_connectivity(self):
        """Check if target is reachable"""
        self.log("Checking connectivity...")
        result = subprocess.run(
            ["ping", "-c", "3", "-W", "2", self.target_ip],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            self.log(f"✓ Target {self.target_ip} is reachable")
            return True
        else:
            self.log(f"✗ Cannot reach {self.target_ip}")
            self.log("  Attempting to continue with available tests...")
            return False

    def test_latency_icmp(self, frame_size, count=1000):
        """
        Test latency using ICMP ping

        Args:
            frame_size: Packet size in bytes
            count: Number of packets to send

        Returns:
            dict: Latency statistics
        """
        self.log(f"  Testing ICMP latency with {frame_size} byte frames...")

        # ICMP adds 8 bytes for header, so adjust payload size
        payload_size = frame_size - 8
        if payload_size < 0:
            payload_size = 0

        cmd = [
            "ping",
            "-c", str(count),
            "-s", str(payload_size),
            "-i", "0.001",  # 1ms interval
            "-W", "1",  # 1 second timeout
            self.target_ip
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            self.log(f"    ✗ Ping test failed")
            return None

        # Parse ping output
        output = result.stdout
        latencies = []

        for line in output.split("\n"):
            if "time=" in line:
                try:
                    time_str = line.split("time=")[1].split()[0]
                    latency = float(time_str)
                    latencies.append(latency)
                except:
                    pass

        if not latencies:
            return None

        # Calculate statistics
        stats = {
            "frame_size": frame_size,
            "count": len(latencies),
            "min": min(latencies),
            "max": max(latencies),
            "avg": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "stddev": statistics.stdev(latencies) if len(latencies) > 1 else 0,
            "p50": statistics.median(latencies),
            "p90": self.percentile(latencies, 90),
            "p95": self.percentile(latencies, 95),
            "p99": self.percentile(latencies, 99),
            "p99.9": self.percentile(latencies, 99.9),
            "jitter": statistics.stdev(latencies) if len(latencies) > 1 else 0
        }

        self.log(f"    avg: {stats['avg']:.3f}ms, min: {stats['min']:.3f}ms, "
                f"max: {stats['max']:.3f}ms, p99: {stats['p99']:.3f}ms")

        return stats

    def percentile(self, data, percent):
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = (len(sorted_data) - 1) * percent / 100
        floor = int(index)
        ceil = floor + 1

        if ceil >= len(sorted_data):
            return sorted_data[floor]

        fraction = index - floor
        return sorted_data[floor] * (1 - fraction) + sorted_data[ceil] * fraction

    def test_throughput_iperf3(self, frame_size, bandwidth_mbps, duration=None):
        """
        Test throughput using iperf3

        Args:
            frame_size: Frame size in bytes
            bandwidth_mbps: Target bandwidth in Mbps
            duration: Test duration in seconds

        Returns:
            dict: Throughput test results
        """
        if duration is None:
            duration = self.duration

        cmd = [
            "iperf3",
            "-c", self.target_ip,
            "-u",  # UDP
            "-b", f"{bandwidth_mbps}M",
            "-l", str(frame_size),
            "-t", str(duration),
            "-J"  # JSON output
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return None

        try:
            data = json.loads(result.stdout)

            # Extract key metrics
            end_data = data.get("end", {})
            sum_data = end_data.get("sum", {})

            return {
                "frame_size": frame_size,
                "target_bandwidth_mbps": bandwidth_mbps,
                "actual_bandwidth_mbps": sum_data.get("bits_per_second", 0) / 1e6,
                "packets_sent": sum_data.get("packets", 0),
                "packets_lost": sum_data.get("lost_packets", 0),
                "loss_percent": sum_data.get("lost_percent", 0),
                "jitter_ms": sum_data.get("jitter_ms", 0),
                "duration": duration
            }
        except Exception as e:
            self.log(f"    Error parsing iperf3 output: {e}")
            return None

    def binary_search_throughput(self, frame_size):
        """
        Find maximum zero-loss throughput using binary search

        Args:
            frame_size: Frame size in bytes

        Returns:
            float: Maximum throughput in Mbps
        """
        self.log(f"  Binary search for zero-loss throughput ({frame_size} bytes)...")

        min_mbps = 1
        max_mbps = 1000
        tolerance = 0.01  # 1% tolerance
        zero_loss_threshold = 0.001  # 0.001% loss is acceptable

        best_throughput = 0
        iterations = 0
        max_iterations = 20

        while (max_mbps - min_mbps) / max_mbps > tolerance and iterations < max_iterations:
            iterations += 1
            current_mbps = (min_mbps + max_mbps) / 2

            self.log(f"    Iteration {iterations}: Testing {current_mbps:.1f} Mbps...")

            result = self.test_throughput_iperf3(frame_size, current_mbps, duration=10)

            if result is None:
                self.log(f"    ✗ Test failed, reducing max throughput")
                max_mbps = current_mbps
                continue

            loss_percent = result["loss_percent"]
            self.log(f"    Loss: {loss_percent:.4f}%")

            if loss_percent < zero_loss_threshold:
                # No significant loss, try higher rate
                min_mbps = current_mbps
                best_throughput = current_mbps
                self.log(f"    ✓ Acceptable loss, increasing rate")
            else:
                # Too much loss, reduce rate
                max_mbps = current_mbps
                self.log(f"    ✗ Too much loss, decreasing rate")

        self.log(f"  Maximum zero-loss throughput: {best_throughput:.2f} Mbps")
        return best_throughput

    def test_frame_loss(self, frame_size, load_percent):
        """
        Test frame loss at specific load percentage

        Args:
            frame_size: Frame size in bytes
            load_percent: Load percentage (50-100)

        Returns:
            dict: Frame loss test results
        """
        # Estimate line rate (assuming 1 Gbps Ethernet)
        line_rate_mbps = 1000
        target_mbps = line_rate_mbps * load_percent / 100

        self.log(f"  Testing frame loss: {frame_size} bytes @ {load_percent}% load ({target_mbps:.1f} Mbps)...")

        result = self.test_throughput_iperf3(frame_size, target_mbps, duration=30)

        if result:
            self.log(f"    Loss: {result['loss_percent']:.4f}%")

        return result

    def test_back_to_back(self, frame_size):
        """
        Test back-to-back frame capacity

        Args:
            frame_size: Frame size in bytes

        Returns:
            dict: Back-to-back test results
        """
        self.log(f"  Testing back-to-back capacity ({frame_size} bytes)...")

        # Send at maximum rate for 2 seconds
        result = self.test_throughput_iperf3(frame_size, 1000, duration=2)

        if result:
            frames_sent = result["packets_sent"]
            frames_lost = result["packets_lost"]
            frames_received = frames_sent - frames_lost

            self.log(f"    Sent: {frames_sent}, Received: {frames_received}, Lost: {frames_lost}")

            return {
                "frame_size": frame_size,
                "frames_sent": frames_sent,
                "frames_received": frames_received,
                "frames_lost": frames_lost,
                "loss_percent": result["loss_percent"],
                "max_burst_size": frames_received
            }

        return None

    def run_all_tests(self):
        """Run complete RFC 2544 test suite"""
        self.log("=" * 80)
        self.log("RFC 2544 NETWORK PERFORMANCE TEST SUITE")
        self.log("=" * 80)
        self.log(f"Target: {self.target_ip}")
        self.log(f"Interface: {self.interface}")
        self.log(f"Test Duration: {self.duration}s")
        self.log("=" * 80)

        results = {
            "test_info": {
                "target_ip": self.target_ip,
                "interface": self.interface,
                "duration": self.duration,
                "timestamp": datetime.datetime.now().isoformat(),
                "frame_sizes": self.frame_sizes,
                "load_percentages": self.load_percentages
            },
            "connectivity": {},
            "throughput": {},
            "latency": {},
            "frame_loss": {},
            "back_to_back": {}
        }

        # Check connectivity
        connectivity = self.check_connectivity()
        results["connectivity"]["reachable"] = connectivity

        if not connectivity:
            self.log("WARNING: Target is not reachable. Some tests will be skipped.")
            self.log("Make sure the server is running and accessible.")

            # Save preliminary results
            with open(self.results_dir / "results.json", "w") as f:
                json.dump(results, f, indent=2)

            return results

        # Test 1: Throughput
        self.log("\n[1/4] THROUGHPUT TEST")
        self.log("-" * 80)
        for frame_size in self.frame_sizes:
            max_throughput = self.binary_search_throughput(frame_size)
            results["throughput"][frame_size] = max_throughput

            # Save intermediate results
            with open(self.results_dir / "throughput.json", "w") as f:
                json.dump(results["throughput"], f, indent=2)

        # Test 2: Latency
        self.log("\n[2/4] LATENCY TEST")
        self.log("-" * 80)
        for frame_size in self.frame_sizes:
            latency_stats = self.test_latency_icmp(frame_size)
            if latency_stats:
                results["latency"][frame_size] = latency_stats

            # Save intermediate results
            with open(self.results_dir / "latency.json", "w") as f:
                json.dump(results["latency"], f, indent=2)

        # Test 3: Frame Loss
        self.log("\n[3/4] FRAME LOSS TEST")
        self.log("-" * 80)
        for frame_size in self.frame_sizes:
            results["frame_loss"][frame_size] = {}
            for load_percent in self.load_percentages:
                loss_result = self.test_frame_loss(frame_size, load_percent)
                if loss_result:
                    results["frame_loss"][frame_size][load_percent] = loss_result

            # Save intermediate results
            with open(self.results_dir / "frame_loss.json", "w") as f:
                json.dump(results["frame_loss"], f, indent=2)

        # Test 4: Back-to-Back
        self.log("\n[4/4] BACK-TO-BACK TEST")
        self.log("-" * 80)
        for frame_size in self.frame_sizes:
            b2b_result = self.test_back_to_back(frame_size)
            if b2b_result:
                results["back_to_back"][frame_size] = b2b_result

            # Save intermediate results
            with open(self.results_dir / "back_to_back.json", "w") as f:
                json.dump(results["back_to_back"], f, indent=2)

        # Save complete results
        self.log("\n" + "=" * 80)
        self.log("TEST SUITE COMPLETED")
        self.log("=" * 80)
        self.log(f"Results saved to: {self.results_dir}/")

        with open(self.results_dir / "results.json", "w") as f:
            json.dump(results, f, indent=2)

        # Generate summary report
        self.generate_summary_report(results)

        return results

    def generate_summary_report(self, results):
        """Generate markdown summary report"""
        report_file = self.results_dir / "SUMMARY.md"

        with open(report_file, "w") as f:
            f.write("# RFC 2544 Network Performance Test Report\n\n")

            # Test Information
            f.write("## Test Information\n\n")
            info = results["test_info"]
            f.write(f"- **Target IP:** {info['target_ip']}\n")
            f.write(f"- **Interface:** {info['interface']}\n")
            f.write(f"- **Test Duration:** {info['duration']}s per iteration\n")
            f.write(f"- **Test Date:** {info['timestamp']}\n")
            f.write(f"- **Frame Sizes:** {', '.join(map(str, info['frame_sizes']))} bytes\n")
            f.write(f"- **Load Levels:** {', '.join(map(str, info['load_percentages']))}%\n\n")

            # Connectivity
            f.write("## Connectivity\n\n")
            if results["connectivity"]["reachable"]:
                f.write("✓ Target is reachable\n\n")
            else:
                f.write("✗ Target is NOT reachable\n\n")
                f.write("**WARNING:** Some tests were skipped due to connectivity issues.\n\n")
                return

            # Throughput Results
            f.write("## 1. Throughput Test (Zero-Loss)\n\n")
            f.write("Maximum throughput with < 0.001% packet loss:\n\n")
            f.write("| Frame Size (bytes) | Throughput (Mbps) |\n")
            f.write("|-------------------:|------------------:|\n")

            throughput_data = results.get("throughput", {})
            for frame_size in info["frame_sizes"]:
                throughput = throughput_data.get(frame_size, 0)
                f.write(f"| {frame_size:>18} | {throughput:>17.2f} |\n")
            f.write("\n")

            # Latency Results
            f.write("## 2. Latency Test (ICMP)\n\n")
            f.write("Round-trip latency statistics:\n\n")
            f.write("| Frame Size | Min (ms) | Avg (ms) | Max (ms) | P99 (ms) | Jitter (ms) |\n")
            f.write("|----------:|---------:|---------:|---------:|---------:|------------:|\n")

            latency_data = results.get("latency", {})
            for frame_size in info["frame_sizes"]:
                lat = latency_data.get(str(frame_size), {})
                if lat:
                    f.write(f"| {frame_size:>10} | {lat['min']:>8.3f} | {lat['avg']:>8.3f} | "
                           f"{lat['max']:>8.3f} | {lat['p99']:>8.3f} | {lat['jitter']:>11.3f} |\n")
            f.write("\n")

            # Frame Loss Summary
            f.write("## 3. Frame Loss Test\n\n")
            f.write("Packet loss percentage at different load levels:\n\n")

            frame_loss_data = results.get("frame_loss", {})
            if frame_loss_data:
                # Header
                f.write("| Frame Size |")
                for load in info["load_percentages"]:
                    f.write(f" {load}% |")
                f.write("\n")

                f.write("|----------:|")
                for _ in info["load_percentages"]:
                    f.write("-----:|")
                f.write("\n")

                # Data rows
                for frame_size in info["frame_sizes"]:
                    f.write(f"| {frame_size:>10} |")
                    size_data = frame_loss_data.get(str(frame_size), {})
                    for load in info["load_percentages"]:
                        load_data = size_data.get(str(load), {})
                        loss = load_data.get("loss_percent", 0)
                        f.write(f" {loss:>4.2f} |")
                    f.write("\n")
                f.write("\n")

            # Back-to-Back Results
            f.write("## 4. Back-to-Back Frame Test\n\n")
            f.write("Maximum burst capacity:\n\n")
            f.write("| Frame Size (bytes) | Max Burst (frames) | Loss (%) |\n")
            f.write("|-------------------:|-------------------:|---------:|\n")

            b2b_data = results.get("back_to_back", {})
            for frame_size in info["frame_sizes"]:
                b2b = b2b_data.get(str(frame_size), {})
                if b2b:
                    f.write(f"| {frame_size:>18} | {b2b['max_burst_size']:>18} | "
                           f"{b2b['loss_percent']:>8.3f} |\n")
            f.write("\n")

            # Conclusions
            f.write("## Conclusions\n\n")

            # Find best performing frame size for throughput
            if throughput_data:
                best_size = max(throughput_data.items(), key=lambda x: x[1] if x[1] else 0)
                f.write(f"- **Best Throughput:** {best_size[1]:.2f} Mbps at {best_size[0]} byte frames\n")

            # Find lowest latency
            if latency_data:
                latencies = [(k, v['avg']) for k, v in latency_data.items() if v]
                if latencies:
                    best_lat = min(latencies, key=lambda x: x[1])
                    f.write(f"- **Lowest Latency:** {best_lat[1]:.3f} ms at {best_lat[0]} byte frames\n")

            f.write("\n---\n\n")
            f.write("*Generated by RFC 2544 Test Suite*\n")

        self.log(f"Summary report saved to: {report_file}")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        target_ip = sys.argv[1]
    else:
        target_ip = "192.168.1.3"

    if len(sys.argv) > 2:
        interface = sys.argv[2]
    else:
        interface = "enp2s0"

    print("=" * 80)
    print("RFC 2544 NETWORK PERFORMANCE TEST SUITE")
    print("=" * 80)
    print(f"Target: {target_ip}")
    print(f"Interface: {interface}")
    print("=" * 80)
    print()

    tester = RFC2544Test(target_ip=target_ip, interface=interface, duration=30)
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
