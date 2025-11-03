#!/usr/bin/env python3
"""
Visualize comprehensive network test results
Generates publication-quality plots and analysis
"""

import json
import sys
import os
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import numpy as np
from datetime import datetime

# Use publication-quality settings
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.titlesize'] = 16


class ResultVisualizer:
    def __init__(self, results_dir):
        self.results_dir = Path(results_dir)
        self.results_file = self.results_dir / "comprehensive_results.json"

        if not self.results_file.exists():
            raise FileNotFoundError(f"Results file not found: {self.results_file}")

        with open(self.results_file, 'r') as f:
            self.data = json.load(f)

        self.plots_dir = self.results_dir / "plots"
        self.plots_dir.mkdir(exist_ok=True)

    def plot_rfc2544_throughput(self):
        """Plot RFC 2544 Throughput vs Frame Size"""
        print("Generating RFC 2544 Throughput plot...")

        throughput_data = self.data.get('rfc2544', {}).get('throughput', {})
        if not throughput_data:
            print("  No throughput data found")
            return

        frame_sizes = []
        max_throughputs = []

        for key, value in throughput_data.items():
            if isinstance(value, dict) and 'frame_size' in value:
                frame_sizes.append(value['frame_size'])
                max_throughputs.append(value.get('max_throughput_mbps', 0))

        if not frame_sizes:
            print("  No valid data to plot")
            return

        # Sort by frame size
        sorted_data = sorted(zip(frame_sizes, max_throughputs))
        frame_sizes, max_throughputs = zip(*sorted_data)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(frame_sizes, max_throughputs, 'o-', linewidth=2, markersize=8, label='Maximum Throughput (0% loss)')
        ax.set_xlabel('Frame Size (bytes)')
        ax.set_ylabel('Throughput (Mbps)')
        ax.set_title('RFC 2544 Throughput Test - Zero Frame Loss Throughput')
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()
        plt.savefig(self.plots_dir / 'rfc2544_throughput.png', dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  Saved to {self.plots_dir / 'rfc2544_throughput.png'}")

    def plot_rfc2544_latency(self):
        """Plot RFC 2544 Latency vs Frame Size"""
        print("Generating RFC 2544 Latency plot...")

        latency_data = self.data.get('rfc2544', {}).get('latency', {})
        if not latency_data:
            print("  No latency data found")
            return

        frame_sizes = []
        avg_latencies = []
        min_latencies = []
        max_latencies = []
        p99_latencies = []

        for key, value in latency_data.items():
            if isinstance(value, dict) and 'frame_size' in value:
                frame_sizes.append(value['frame_size'])
                avg_latencies.append(value.get('avg_ms', 0))
                min_latencies.append(value.get('min_ms', 0))
                max_latencies.append(value.get('max_ms', 0))
                p99_latencies.append(value.get('percentile_99', 0))

        if not frame_sizes:
            print("  No valid data to plot")
            return

        # Sort by frame size
        sorted_data = sorted(zip(frame_sizes, avg_latencies, min_latencies, max_latencies, p99_latencies))
        frame_sizes, avg_latencies, min_latencies, max_latencies, p99_latencies = zip(*sorted_data)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(frame_sizes, avg_latencies, 'o-', linewidth=2, markersize=8, label='Average Latency')
        ax.plot(frame_sizes, min_latencies, 's--', linewidth=1, markersize=6, label='Min Latency')
        ax.plot(frame_sizes, max_latencies, '^--', linewidth=1, markersize=6, label='Max Latency')
        ax.plot(frame_sizes, p99_latencies, 'd-', linewidth=2, markersize=6, label='99th Percentile')
        ax.set_xlabel('Frame Size (bytes)')
        ax.set_ylabel('Latency (ms)')
        ax.set_title('RFC 2544 Latency Test')
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()
        plt.savefig(self.plots_dir / 'rfc2544_latency.png', dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  Saved to {self.plots_dir / 'rfc2544_latency.png'}")

    def plot_rfc2544_frame_loss(self):
        """Plot RFC 2544 Frame Loss vs Load"""
        print("Generating RFC 2544 Frame Loss plot...")

        frame_loss_data = self.data.get('rfc2544', {}).get('frame_loss', {})
        if not frame_loss_data:
            print("  No frame loss data found")
            return

        # Create a plot for each frame size
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()

        plot_idx = 0
        for key, value in sorted(frame_loss_data.items()):
            if not isinstance(value, dict) or 'tests' not in value:
                continue

            frame_size = value['frame_size']
            tests = value['tests']

            loads = []
            losses = []

            for test_key, test_data in sorted(tests.items()):
                if isinstance(test_data, dict) and 'load_percent' in test_data:
                    loads.append(test_data['load_percent'])
                    losses.append(test_data.get('loss_percent', 0))

            if loads and plot_idx < len(axes):
                ax = axes[plot_idx]
                ax.plot(loads, losses, 'o-', linewidth=2, markersize=8)
                ax.set_xlabel('Load (%)')
                ax.set_ylabel('Frame Loss (%)')
                ax.set_title(f'Frame Loss - {frame_size} bytes')
                ax.grid(True, alpha=0.3)
                ax.set_ylim(bottom=0)
                plot_idx += 1

        # Hide unused subplots
        for idx in range(plot_idx, len(axes)):
            axes[idx].axis('off')

        plt.suptitle('RFC 2544 Frame Loss Test', fontsize=16)
        plt.tight_layout()
        plt.savefig(self.plots_dir / 'rfc2544_frame_loss.png', dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  Saved to {self.plots_dir / 'rfc2544_frame_loss.png'}")

    def plot_rfc2544_back_to_back(self):
        """Plot RFC 2544 Back-to-Back Frames"""
        print("Generating RFC 2544 Back-to-Back plot...")

        b2b_data = self.data.get('rfc2544', {}).get('back_to_back', {})
        if not b2b_data:
            print("  No back-to-back data found")
            return

        frame_sizes = []
        frames_sent = []
        loss_percents = []

        for key, value in b2b_data.items():
            if isinstance(value, dict) and 'frame_size' in value:
                frame_sizes.append(value['frame_size'])
                frames_sent.append(value.get('frames_sent', 0))
                loss_percents.append(value.get('loss_percent', 0))

        if not frame_sizes:
            print("  No valid data to plot")
            return

        # Sort by frame size
        sorted_data = sorted(zip(frame_sizes, frames_sent, loss_percents))
        frame_sizes, frames_sent, loss_percents = zip(*sorted_data)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Frames sent
        ax1.bar(range(len(frame_sizes)), frames_sent, tick_label=frame_sizes)
        ax1.set_xlabel('Frame Size (bytes)')
        ax1.set_ylabel('Frames Sent')
        ax1.set_title('Back-to-Back Burst Size')
        ax1.grid(True, alpha=0.3, axis='y')

        # Loss percent
        ax2.bar(range(len(frame_sizes)), loss_percents, tick_label=frame_sizes, color='red', alpha=0.7)
        ax2.set_xlabel('Frame Size (bytes)')
        ax2.set_ylabel('Frame Loss (%)')
        ax2.set_title('Back-to-Back Frame Loss')
        ax2.grid(True, alpha=0.3, axis='y')

        plt.suptitle('RFC 2544 Back-to-Back Frames Test', fontsize=16)
        plt.tight_layout()
        plt.savefig(self.plots_dir / 'rfc2544_back_to_back.png', dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  Saved to {self.plots_dir / 'rfc2544_back_to_back.png'}")

    def generate_summary_report(self):
        """Generate comprehensive summary report"""
        print("Generating summary report...")

        report_file = self.results_dir / "summary_report.md"

        with open(report_file, 'w') as f:
            f.write("# Comprehensive Network Performance Test Report\n\n")

            # Test information
            test_info = self.data.get('test_info', {})
            f.write("## Test Configuration\n\n")
            f.write(f"- **Target IP:** {test_info.get('target_ip', 'N/A')}\n")
            f.write(f"- **Local IP:** {test_info.get('local_ip', 'N/A')}\n")
            f.write(f"- **Interface:** {test_info.get('interface', 'N/A')}\n")
            f.write(f"- **Test Date:** {test_info.get('timestamp', 'N/A')}\n")
            f.write(f"- **Duration per Test:** {test_info.get('duration_per_test', 'N/A')} seconds\n\n")

            # RFC 2544 Throughput Summary
            f.write("## RFC 2544 Throughput Test Results\n\n")
            throughput_data = self.data.get('rfc2544', {}).get('throughput', {})
            if throughput_data:
                f.write("| Frame Size (bytes) | Max Throughput (Mbps) | 0% Loss |\n")
                f.write("|-------------------|-----------------------|---------|\n")

                for key in sorted(throughput_data.keys()):
                    value = throughput_data[key]
                    if isinstance(value, dict) and 'frame_size' in value:
                        frame_size = value['frame_size']
                        max_tp = value.get('max_throughput_mbps', 0)
                        f.write(f"| {frame_size} | {max_tp:.2f} | Yes |\n")
                f.write("\n")
            else:
                f.write("*No throughput data available*\n\n")

            # RFC 2544 Latency Summary
            f.write("## RFC 2544 Latency Test Results\n\n")
            latency_data = self.data.get('rfc2544', {}).get('latency', {})
            if latency_data:
                f.write("| Frame Size (bytes) | Min (ms) | Avg (ms) | Max (ms) | 99th %ile (ms) | Std Dev (ms) |\n")
                f.write("|-------------------|----------|----------|----------|----------------|-------------|\n")

                for key in sorted(latency_data.keys()):
                    value = latency_data[key]
                    if isinstance(value, dict) and 'frame_size' in value:
                        frame_size = value['frame_size']
                        min_lat = value.get('min_ms', 0)
                        avg_lat = value.get('avg_ms', 0)
                        max_lat = value.get('max_ms', 0)
                        p99_lat = value.get('percentile_99', 0)
                        std_lat = value.get('stdev_ms', 0)
                        f.write(f"| {frame_size} | {min_lat:.3f} | {avg_lat:.3f} | {max_lat:.3f} | {p99_lat:.3f} | {std_lat:.3f} |\n")
                f.write("\n")
            else:
                f.write("*No latency data available*\n\n")

            # RFC 2544 Frame Loss Summary
            f.write("## RFC 2544 Frame Loss Test Results\n\n")
            frame_loss_data = self.data.get('rfc2544', {}).get('frame_loss', {})
            if frame_loss_data:
                f.write("### Frame Loss at Different Load Levels\n\n")
                for key in sorted(frame_loss_data.keys()):
                    value = frame_loss_data[key]
                    if isinstance(value, dict) and 'tests' in value:
                        frame_size = value['frame_size']
                        f.write(f"#### {frame_size} bytes\n\n")
                        f.write("| Load (%) | Sent | Lost | Loss (%) |\n")
                        f.write("|----------|------|------|-----------|\n")

                        tests = value['tests']
                        for test_key in sorted(tests.keys()):
                            test_data = tests[test_key]
                            if isinstance(test_data, dict) and 'load_percent' in test_data:
                                load = test_data['load_percent']
                                sent = test_data.get('sent_packets', 0)
                                lost = test_data.get('lost_packets', 0)
                                loss_pct = test_data.get('loss_percent', 0)
                                f.write(f"| {load} | {sent} | {lost} | {loss_pct:.3f} |\n")
                        f.write("\n")
            else:
                f.write("*No frame loss data available*\n\n")

            # RFC 2544 Back-to-Back Summary
            f.write("## RFC 2544 Back-to-Back Frames Test Results\n\n")
            b2b_data = self.data.get('rfc2544', {}).get('back_to_back', {})
            if b2b_data:
                f.write("| Frame Size (bytes) | Frames Sent | Frames Lost | Loss (%) | Bitrate (Mbps) |\n")
                f.write("|-------------------|-------------|-------------|----------|----------------|\n")

                for key in sorted(b2b_data.keys()):
                    value = b2b_data[key]
                    if isinstance(value, dict) and 'frame_size' in value:
                        frame_size = value['frame_size']
                        sent = value.get('frames_sent', 0)
                        lost = value.get('frames_lost', 0)
                        loss = value.get('loss_percent', 0)
                        bitrate = value.get('bitrate_mbps', 0)
                        f.write(f"| {frame_size} | {sent} | {lost} | {loss:.3f} | {bitrate:.2f} |\n")
                f.write("\n")
            else:
                f.write("*No back-to-back data available*\n\n")

            # Sockperf summary
            f.write("## Sockperf Test Results\n\n")
            f.write("*See detailed logs in test results directory*\n\n")

            # FRER summary
            f.write("## FRER Test Results\n\n")
            frer_data = self.data.get('frer', {})
            if frer_data:
                f.write(f"- **Test Performed:** {frer_data.get('test_performed', False)}\n")
                if 'note' in frer_data:
                    f.write(f"- **Note:** {frer_data['note']}\n")
                if 'reason' in frer_data:
                    f.write(f"- **Reason:** {frer_data['reason']}\n")
                f.write("\n")

            # Plots
            f.write("## Visualizations\n\n")
            f.write("The following plots have been generated:\n\n")
            f.write("- RFC 2544 Throughput: `plots/rfc2544_throughput.png`\n")
            f.write("- RFC 2544 Latency: `plots/rfc2544_latency.png`\n")
            f.write("- RFC 2544 Frame Loss: `plots/rfc2544_frame_loss.png`\n")
            f.write("- RFC 2544 Back-to-Back: `plots/rfc2544_back_to_back.png`\n\n")

            # Conclusion
            f.write("## Conclusion\n\n")
            f.write("This comprehensive test suite evaluated network performance using industry-standard ")
            f.write("RFC 2544 benchmarking methodology and sockperf tools. The results provide detailed ")
            f.write("insights into throughput, latency, frame loss, and burst handling capabilities of ")
            f.write("the network path between 192.168.1.2 and 192.168.1.3.\n\n")

            f.write("---\n\n")
            f.write(f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

        print(f"  Saved to {report_file}")

    def generate_all_plots(self):
        """Generate all visualizations"""
        print("Generating all visualizations...")
        print("="*60)

        self.plot_rfc2544_throughput()
        self.plot_rfc2544_latency()
        self.plot_rfc2544_frame_loss()
        self.plot_rfc2544_back_to_back()
        self.generate_summary_report()

        print("="*60)
        print("All visualizations generated successfully!")
        print(f"Output directory: {self.plots_dir}/")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 visualize_results.py <results_directory>")
        print("\nExample:")
        print("  python3 visualize_results.py test_results_20251103_140000")
        sys.exit(1)

    results_dir = sys.argv[1]

    if not os.path.exists(results_dir):
        print(f"Error: Directory not found: {results_dir}")
        sys.exit(1)

    try:
        visualizer = ResultVisualizer(results_dir)
        visualizer.generate_all_plots()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
