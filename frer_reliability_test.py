#!/usr/bin/env python3
"""
FRER (Frame Replication and Elimination for Reliability) Test
IEEE 802.1CB Implementation Test

Tests redundant path reliability in TSN networks
"""

import subprocess
import json
import time
import datetime
import sys
import os
from pathlib import Path
from scapy.all import *

class FRERTest:
    def __init__(self, primary_ip="192.168.1.3", secondary_ip="192.168.1.4",
                 primary_iface="enp2s0", secondary_iface="enp11s0"):
        self.primary_ip = primary_ip
        self.secondary_ip = secondary_ip
        self.primary_iface = primary_iface
        self.secondary_iface = secondary_iface

        # Create results directory
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_dir = Path(f"frer_results_{timestamp}")
        self.results_dir.mkdir(exist_ok=True)

        self.sequence_number = 0

    def log(self, message):
        """Log message with timestamp"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp}] {message}"
        print(msg)

        log_file = self.results_dir / "frer_test.log"
        with open(log_file, "a") as f:
            f.write(msg + "\n")

    def create_frer_packet(self, seq_num, stream_id=1):
        """
        Create FRER-tagged packet

        Args:
            seq_num: Sequence number
            stream_id: Stream identification

        Returns:
            scapy packet
        """
        # Create Ethernet frame with FRER R-TAG
        # R-TAG EtherType: 0xF1C1
        pkt = Ether(dst="ff:ff:ff:ff:ff:ff", src=get_if_hwaddr(self.primary_iface))
        pkt = pkt / Raw(load=struct.pack("!HHI",
                                          0xF1C1,  # R-TAG EtherType
                                          stream_id,  # Stream ID
                                          seq_num))  # Sequence number

        # Add payload
        pkt = pkt / Raw(load=b"FRER_TEST_" + str(seq_num).encode() + b"_" + os.urandom(1000))

        return pkt

    def send_replicated_frames(self, count=1000, interval=0.001):
        """
        Send replicated frames on both paths

        Args:
            count: Number of frames to send
            interval: Interval between frames (seconds)

        Returns:
            dict: Send statistics
        """
        self.log(f"Sending {count} replicated frames...")

        sent_primary = 0
        sent_secondary = 0
        errors = 0

        start_time = time.time()

        for i in range(count):
            seq_num = self.sequence_number
            self.sequence_number += 1

            # Create FRER packet
            pkt = self.create_frer_packet(seq_num)

            try:
                # Send on primary path
                sendp(pkt, iface=self.primary_iface, verbose=False)
                sent_primary += 1

                # Send on secondary path (if available)
                if self.secondary_iface:
                    try:
                        sendp(pkt, iface=self.secondary_iface, verbose=False)
                        sent_secondary += 1
                    except Exception as e:
                        pass

            except Exception as e:
                self.log(f"  Error sending packet {seq_num}: {e}")
                errors += 1

            # Progress update every 100 packets
            if (i + 1) % 100 == 0:
                self.log(f"  Progress: {i + 1}/{count} packets sent")

            time.sleep(interval)

        end_time = time.time()
        duration = end_time - start_time

        stats = {
            "count": count,
            "sent_primary": sent_primary,
            "sent_secondary": sent_secondary,
            "errors": errors,
            "duration": duration,
            "rate_pps": count / duration if duration > 0 else 0
        }

        self.log(f"Sent {sent_primary} frames on primary path")
        if sent_secondary > 0:
            self.log(f"Sent {sent_secondary} frames on secondary path")
        self.log(f"Duration: {duration:.2f}s, Rate: {stats['rate_pps']:.1f} pps")

        return stats

    def capture_and_analyze(self, duration=30):
        """
        Capture and analyze FRER frames

        Args:
            duration: Capture duration in seconds

        Returns:
            dict: Analysis results
        """
        self.log(f"Capturing frames for {duration} seconds...")

        pcap_file = self.results_dir / "frer_capture.pcap"

        # Capture on primary interface
        capture_cmd = [
            "tcpdump",
            "-i", self.primary_iface,
            "-w", str(pcap_file),
            "-c", "10000",  # Capture up to 10000 packets
            "-W", str(duration)
        ]

        try:
            subprocess.run(capture_cmd, timeout=duration + 5)
        except subprocess.TimeoutExpired:
            pass

        self.log(f"Capture complete: {pcap_file}")

        # Analyze captured packets
        analysis = self.analyze_pcap(pcap_file)

        return analysis

    def analyze_pcap(self, pcap_file):
        """
        Analyze captured FRER packets

        Args:
            pcap_file: Path to pcap file

        Returns:
            dict: Analysis results
        """
        self.log("Analyzing captured packets...")

        if not os.path.exists(pcap_file):
            self.log("  No pcap file found")
            return None

        try:
            packets = rdpcap(str(pcap_file))
        except Exception as e:
            self.log(f"  Error reading pcap: {e}")
            return None

        self.log(f"  Total packets: {len(packets)}")

        # Analyze packet statistics
        total_packets = len(packets)
        duplicates = 0
        unique_seq = set()
        out_of_order = 0
        prev_seq = -1

        for pkt in packets:
            if Raw in pkt:
                payload = bytes(pkt[Raw].load)

                # Try to extract sequence number from FRER tag
                if len(payload) >= 8 and payload[0:2] == b'\xf1\xc1':
                    try:
                        ethertype, stream_id, seq_num = struct.unpack("!HHI", payload[0:8])

                        if seq_num in unique_seq:
                            duplicates += 1
                        else:
                            unique_seq.add(seq_num)

                        if seq_num < prev_seq:
                            out_of_order += 1

                        prev_seq = seq_num
                    except:
                        pass

        unique_packets = len(unique_seq)
        replication_ratio = (duplicates / unique_packets * 100) if unique_packets > 0 else 0

        analysis = {
            "total_packets": total_packets,
            "unique_packets": unique_packets,
            "duplicates": duplicates,
            "out_of_order": out_of_order,
            "replication_ratio": replication_ratio,
            "elimination_efficiency": (duplicates / total_packets * 100) if total_packets > 0 else 0
        }

        self.log(f"  Unique packets: {unique_packets}")
        self.log(f"  Duplicates: {duplicates}")
        self.log(f"  Out of order: {out_of_order}")
        self.log(f"  Replication ratio: {replication_ratio:.2f}%")

        return analysis

    def test_path_redundancy(self, count=1000):
        """
        Test path redundancy with simulated failures

        Args:
            count: Number of test packets

        Returns:
            dict: Redundancy test results
        """
        self.log("Testing path redundancy...")

        results = {
            "both_paths": None,
            "primary_only": None,
            "secondary_only": None
        }

        # Test 1: Both paths active
        self.log("\n  Test 1: Both paths active")
        stats = self.send_replicated_frames(count=count // 3, interval=0.001)
        results["both_paths"] = stats

        # Test 2: Primary path only (simulate secondary failure)
        self.log("\n  Test 2: Primary path only")
        old_secondary = self.secondary_iface
        self.secondary_iface = None
        stats = self.send_replicated_frames(count=count // 3, interval=0.001)
        results["primary_only"] = stats
        self.secondary_iface = old_secondary

        # Test 3: Secondary path only (simulate primary failure)
        self.log("\n  Test 3: Secondary path only")
        old_primary = self.primary_iface
        self.primary_iface = self.secondary_iface
        self.secondary_iface = None
        stats = self.send_replicated_frames(count=count // 3, interval=0.001)
        results["secondary_only"] = stats
        self.primary_iface = old_primary
        self.secondary_iface = old_secondary

        return results

    def run_all_tests(self):
        """Run complete FRER test suite"""
        self.log("=" * 80)
        self.log("FRER (Frame Replication and Elimination) TEST SUITE")
        self.log("=" * 80)
        self.log(f"Primary Path: {self.primary_iface} -> {self.primary_ip}")
        if self.secondary_iface:
            self.log(f"Secondary Path: {self.secondary_iface} -> {self.secondary_ip}")
        else:
            self.log("Secondary Path: Not configured (single path mode)")
        self.log("=" * 80)

        results = {
            "test_info": {
                "primary_ip": self.primary_ip,
                "secondary_ip": self.secondary_ip,
                "primary_iface": self.primary_iface,
                "secondary_iface": self.secondary_iface,
                "timestamp": datetime.datetime.now().isoformat()
            },
            "replication": None,
            "elimination": None,
            "redundancy": None
        }

        # Check if running as root (required for packet crafting)
        if os.geteuid() != 0:
            self.log("\nWARNING: This test requires root privileges for packet crafting")
            self.log("Please run with sudo")

            # Save preliminary results
            with open(self.results_dir / "results.json", "w") as f:
                json.dump(results, f, indent=2)

            return results

        # Test 1: Frame Replication
        self.log("\n[1/3] FRAME REPLICATION TEST")
        self.log("-" * 80)
        send_stats = self.send_replicated_frames(count=1000, interval=0.001)
        results["replication"] = send_stats

        # Test 2: Frame Elimination (capture and analyze)
        self.log("\n[2/3] FRAME ELIMINATION TEST")
        self.log("-" * 80)
        analysis = self.capture_and_analyze(duration=30)
        results["elimination"] = analysis

        # Test 3: Path Redundancy
        self.log("\n[3/3] PATH REDUNDANCY TEST")
        self.log("-" * 80)
        redundancy = self.test_path_redundancy(count=900)
        results["redundancy"] = redundancy

        # Save results
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
            f.write("# FRER Test Report\n\n")
            f.write("Frame Replication and Elimination for Reliability (IEEE 802.1CB)\n\n")

            # Test Information
            f.write("## Test Information\n\n")
            info = results["test_info"]
            f.write(f"- **Primary Path:** {info['primary_iface']} -> {info['primary_ip']}\n")
            if info.get("secondary_iface"):
                f.write(f"- **Secondary Path:** {info['secondary_iface']} -> {info['secondary_ip']}\n")
            f.write(f"- **Test Date:** {info['timestamp']}\n\n")

            # Replication Results
            if results.get("replication"):
                f.write("## Frame Replication Test\n\n")
                rep = results["replication"]
                f.write(f"- **Frames Sent (Primary):** {rep['sent_primary']}\n")
                if rep.get("sent_secondary"):
                    f.write(f"- **Frames Sent (Secondary):** {rep['sent_secondary']}\n")
                f.write(f"- **Errors:** {rep['errors']}\n")
                f.write(f"- **Duration:** {rep['duration']:.2f}s\n")
                f.write(f"- **Rate:** {rep['rate_pps']:.1f} pps\n\n")

            # Elimination Results
            if results.get("elimination"):
                f.write("## Frame Elimination Test\n\n")
                elim = results["elimination"]
                f.write(f"- **Total Packets Captured:** {elim['total_packets']}\n")
                f.write(f"- **Unique Packets:** {elim['unique_packets']}\n")
                f.write(f"- **Duplicates Eliminated:** {elim['duplicates']}\n")
                f.write(f"- **Out of Order:** {elim['out_of_order']}\n")
                f.write(f"- **Replication Ratio:** {elim['replication_ratio']:.2f}%\n")
                f.write(f"- **Elimination Efficiency:** {elim['elimination_efficiency']:.2f}%\n\n")

            # Redundancy Results
            if results.get("redundancy"):
                f.write("## Path Redundancy Test\n\n")
                red = results["redundancy"]

                f.write("### Both Paths Active\n")
                if red.get("both_paths"):
                    bp = red["both_paths"]
                    f.write(f"- Primary: {bp['sent_primary']} frames\n")
                    f.write(f"- Secondary: {bp.get('sent_secondary', 0)} frames\n")
                    f.write(f"- Rate: {bp['rate_pps']:.1f} pps\n\n")

                f.write("### Primary Path Only\n")
                if red.get("primary_only"):
                    po = red["primary_only"]
                    f.write(f"- Frames sent: {po['sent_primary']}\n")
                    f.write(f"- Rate: {po['rate_pps']:.1f} pps\n\n")

                f.write("### Secondary Path Only\n")
                if red.get("secondary_only"):
                    so = red["secondary_only"]
                    f.write(f"- Frames sent: {so['sent_primary']}\n")
                    f.write(f"- Rate: {so['rate_pps']:.1f} pps\n\n")

            f.write("---\n\n")
            f.write("*Generated by FRER Test Suite*\n")

        self.log(f"Summary report saved to: {report_file}")

def main():
    """Main function"""
    primary_ip = "192.168.1.3"
    secondary_ip = "192.168.1.4"
    primary_iface = "enp2s0"
    secondary_iface = None  # Set to interface name if available

    if len(sys.argv) > 1:
        primary_ip = sys.argv[1]
    if len(sys.argv) > 2:
        primary_iface = sys.argv[2]
    if len(sys.argv) > 3:
        secondary_iface = sys.argv[3]

    print("=" * 80)
    print("FRER TEST SUITE (IEEE 802.1CB)")
    print("=" * 80)
    print(f"Primary: {primary_iface} -> {primary_ip}")
    if secondary_iface:
        print(f"Secondary: {secondary_iface} -> {secondary_ip}")
    else:
        print("Secondary: Not configured (single path mode)")
    print("=" * 80)
    print()

    if os.geteuid() != 0:
        print("ERROR: This test requires root privileges")
        print("Please run with sudo:")
        print(f"  sudo python3 {sys.argv[0]}")
        sys.exit(1)

    tester = FRERTest(
        primary_ip=primary_ip,
        secondary_ip=secondary_ip,
        primary_iface=primary_iface,
        secondary_iface=secondary_iface
    )

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
