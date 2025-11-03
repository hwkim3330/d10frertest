#!/usr/bin/env python3
"""
Advanced Network Performance Visualizer
Creates publication-quality plots for network test results

Supports:
- RFC 2544 test results
- Sockperf test results
- FRER test results
"""

import json
import sys
import os
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

# Use non-interactive backend
matplotlib.use('Agg')

# Set publication-quality defaults
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12
plt.rcParams['legend.fontsize'] = 12
plt.rcParams['figure.titlesize'] = 18
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3

class NetworkVisualizer:
    def __init__(self, results_dir):
        self.results_dir = Path(results_dir)
        self.plots_dir = self.results_dir / "plots"
        self.plots_dir.mkdir(exist_ok=True)

    def load_rfc2544_results(self):
        """Load RFC 2544 test results"""
        results_file = self.results_dir / "results.json"

        if not results_file.exists():
            print(f"Results file not found: {results_file}")
            return None

        with open(results_file, "r") as f:
            return json.load(f)

    def plot_rfc2544_throughput(self, results):
        """Plot RFC 2544 throughput results"""
        throughput_data = results.get("throughput", {})

        if not throughput_data:
            print("No throughput data found")
            return

        frame_sizes = sorted([int(k) for k in throughput_data.keys()])
        throughputs = [throughput_data[str(fs)] for fs in frame_sizes]

        fig, ax = plt.subplots(figsize=(12, 8))

        # Bar plot
        bars = ax.bar(range(len(frame_sizes)), throughputs,
                       color='steelblue', edgecolor='black', alpha=0.8)

        # Add value labels on top of bars
        for i, (fs, tp) in enumerate(zip(frame_sizes, throughputs)):
            ax.text(i, tp + 10, f'{tp:.1f}',
                    ha='center', va='bottom', fontweight='bold')

        ax.set_xlabel('Frame Size (bytes)')
        ax.set_ylabel('Throughput (Mbps)')
        ax.set_title('RFC 2544 Throughput Test\nMaximum Zero-Loss Throughput')
        ax.set_xticks(range(len(frame_sizes)))
        ax.set_xticklabels(frame_sizes)
        ax.set_ylim(0, max(throughputs) * 1.15)

        # Add grid
        ax.yaxis.grid(True, linestyle='--', alpha=0.7)
        ax.set_axisbelow(True)

        plt.tight_layout()
        output_file = self.plots_dir / "rfc2544_throughput.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Saved: {output_file}")

    def plot_rfc2544_latency(self, results):
        """Plot RFC 2544 latency results"""
        latency_data = results.get("latency", {})

        if not latency_data:
            print("No latency data found")
            return

        frame_sizes = sorted([int(k) for k in latency_data.keys()])

        metrics = ['min', 'avg', 'p99', 'max']
        metric_labels = ['Min', 'Avg', 'P99', 'Max']
        colors = ['green', 'blue', 'orange', 'red']

        fig, ax = plt.subplots(figsize=(12, 8))

        x = np.arange(len(frame_sizes))
        width = 0.2

        for i, (metric, label, color) in enumerate(zip(metrics, metric_labels, colors)):
            values = [latency_data[str(fs)].get(metric, 0) for fs in frame_sizes]
            offset = width * (i - 1.5)
            ax.bar(x + offset, values, width, label=label, color=color, alpha=0.8)

        ax.set_xlabel('Frame Size (bytes)')
        ax.set_ylabel('Latency (ms)')
        ax.set_title('RFC 2544 Latency Test\nRound-Trip Time Statistics')
        ax.set_xticks(x)
        ax.set_xticklabels(frame_sizes)
        ax.legend()

        ax.yaxis.grid(True, linestyle='--', alpha=0.7)
        ax.set_axisbelow(True)

        plt.tight_layout()
        output_file = self.plots_dir / "rfc2544_latency.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Saved: {output_file}")

    def plot_rfc2544_latency_cdf(self, results):
        """Plot latency CDF (Cumulative Distribution Function)"""
        latency_data = results.get("latency", {})

        if not latency_data:
            return

        fig, ax = plt.subplots(figsize=(12, 8))

        frame_sizes = sorted([int(k) for k in latency_data.keys()])
        colors = plt.cm.viridis(np.linspace(0, 1, len(frame_sizes)))

        for fs, color in zip(frame_sizes, colors):
            lat = latency_data[str(fs)]

            percentiles = [0, 50, 90, 95, 99, 99.9, 100]
            values = [
                lat.get('min', 0),
                lat.get('p50', 0),
                lat.get('p90', 0),
                lat.get('p95', 0),
                lat.get('p99', 0),
                lat.get('p99.9', 0),
                lat.get('max', 0)
            ]

            ax.plot(values, percentiles, marker='o', label=f'{fs} bytes',
                    color=color, linewidth=2, markersize=6)

        ax.set_xlabel('Latency (ms)')
        ax.set_ylabel('Percentile')
        ax.set_title('RFC 2544 Latency Distribution\nCumulative Distribution Function')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7)

        plt.tight_layout()
        output_file = self.plots_dir / "rfc2544_latency_cdf.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Saved: {output_file}")

    def plot_rfc2544_frame_loss(self, results):
        """Plot RFC 2544 frame loss results"""
        frame_loss_data = results.get("frame_loss", {})

        if not frame_loss_data:
            print("No frame loss data found")
            return

        frame_sizes = sorted([int(k) for k in frame_loss_data.keys()])

        # Get load percentages from first frame size
        first_size = str(frame_sizes[0])
        load_percentages = sorted([int(k) for k in frame_loss_data[first_size].keys()])

        fig, ax = plt.subplots(figsize=(14, 8))

        x = np.arange(len(frame_sizes))
        width = 0.12

        colors = plt.cm.Reds(np.linspace(0.3, 0.9, len(load_percentages)))

        for i, load in enumerate(load_percentages):
            loss_values = []
            for fs in frame_sizes:
                load_data = frame_loss_data[str(fs)].get(str(load), {})
                loss = load_data.get("loss_percent", 0)
                loss_values.append(loss)

            offset = width * (i - len(load_percentages) / 2 + 0.5)
            ax.bar(x + offset, loss_values, width, label=f'{load}% load',
                   color=colors[i], alpha=0.8)

        ax.set_xlabel('Frame Size (bytes)')
        ax.set_ylabel('Frame Loss (%)')
        ax.set_title('RFC 2544 Frame Loss Test\nPacket Loss at Different Load Levels')
        ax.set_xticks(x)
        ax.set_xticklabels(frame_sizes)
        ax.legend(ncol=2)

        ax.yaxis.grid(True, linestyle='--', alpha=0.7)
        ax.set_axisbelow(True)

        plt.tight_layout()
        output_file = self.plots_dir / "rfc2544_frame_loss.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Saved: {output_file}")

    def plot_rfc2544_back_to_back(self, results):
        """Plot RFC 2544 back-to-back results"""
        b2b_data = results.get("back_to_back", {})

        if not b2b_data:
            print("No back-to-back data found")
            return

        frame_sizes = sorted([int(k) for k in b2b_data.keys()])
        burst_sizes = [b2b_data[str(fs)].get("max_burst_size", 0) for fs in frame_sizes]

        fig, ax = plt.subplots(figsize=(12, 8))

        bars = ax.bar(range(len(frame_sizes)), burst_sizes,
                       color='darkgreen', edgecolor='black', alpha=0.8)

        # Add value labels on top of bars
        for i, (fs, burst) in enumerate(zip(frame_sizes, burst_sizes)):
            ax.text(i, burst * 1.02, f'{burst:,}',
                    ha='center', va='bottom', fontweight='bold', fontsize=10)

        ax.set_xlabel('Frame Size (bytes)')
        ax.set_ylabel('Maximum Burst Size (frames)')
        ax.set_title('RFC 2544 Back-to-Back Test\nMaximum Burst Capacity')
        ax.set_xticks(range(len(frame_sizes)))
        ax.set_xticklabels(frame_sizes)

        ax.yaxis.grid(True, linestyle='--', alpha=0.7)
        ax.set_axisbelow(True)

        plt.tight_layout()
        output_file = self.plots_dir / "rfc2544_back_to_back.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Saved: {output_file}")

    def plot_comprehensive_dashboard(self, results):
        """Create comprehensive dashboard with all metrics"""
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)

        # 1. Throughput
        ax1 = fig.add_subplot(gs[0, 0])
        throughput_data = results.get("throughput", {})
        if throughput_data:
            frame_sizes = sorted([int(k) for k in throughput_data.keys()])
            throughputs = [throughput_data[str(fs)] for fs in frame_sizes]
            ax1.bar(range(len(frame_sizes)), throughputs, color='steelblue', alpha=0.8)
            ax1.set_xlabel('Frame Size (bytes)')
            ax1.set_ylabel('Throughput (Mbps)')
            ax1.set_title('Throughput (Zero-Loss)')
            ax1.set_xticks(range(len(frame_sizes)))
            ax1.set_xticklabels(frame_sizes, rotation=45)
            ax1.grid(True, alpha=0.3)

        # 2. Average Latency
        ax2 = fig.add_subplot(gs[0, 1])
        latency_data = results.get("latency", {})
        if latency_data:
            frame_sizes = sorted([int(k) for k in latency_data.keys()])
            avg_latencies = [latency_data[str(fs)].get('avg', 0) for fs in frame_sizes]
            ax2.plot(frame_sizes, avg_latencies, marker='o', linewidth=2,
                     markersize=8, color='blue')
            ax2.fill_between(frame_sizes, avg_latencies, alpha=0.3)
            ax2.set_xlabel('Frame Size (bytes)')
            ax2.set_ylabel('Latency (ms)')
            ax2.set_title('Average Latency')
            ax2.grid(True, alpha=0.3)

        # 3. Latency Percentiles
        ax3 = fig.add_subplot(gs[0, 2])
        if latency_data:
            frame_sizes = sorted([int(k) for k in latency_data.keys()])
            p50 = [latency_data[str(fs)].get('p50', 0) for fs in frame_sizes]
            p95 = [latency_data[str(fs)].get('p95', 0) for fs in frame_sizes]
            p99 = [latency_data[str(fs)].get('p99', 0) for fs in frame_sizes]

            ax3.plot(frame_sizes, p50, marker='o', label='P50', linewidth=2)
            ax3.plot(frame_sizes, p95, marker='s', label='P95', linewidth=2)
            ax3.plot(frame_sizes, p99, marker='^', label='P99', linewidth=2)
            ax3.set_xlabel('Frame Size (bytes)')
            ax3.set_ylabel('Latency (ms)')
            ax3.set_title('Latency Percentiles')
            ax3.legend()
            ax3.grid(True, alpha=0.3)

        # 4. Frame Loss Heatmap
        ax4 = fig.add_subplot(gs[1, :2])
        frame_loss_data = results.get("frame_loss", {})
        if frame_loss_data:
            frame_sizes = sorted([int(k) for k in frame_loss_data.keys()])
            first_size = str(frame_sizes[0])
            load_percentages = sorted([int(k) for k in frame_loss_data[first_size].keys()])

            loss_matrix = []
            for load in load_percentages:
                row = []
                for fs in frame_sizes:
                    load_data = frame_loss_data[str(fs)].get(str(load), {})
                    loss = load_data.get("loss_percent", 0)
                    row.append(loss)
                loss_matrix.append(row)

            im = ax4.imshow(loss_matrix, aspect='auto', cmap='YlOrRd', interpolation='nearest')
            ax4.set_xlabel('Frame Size (bytes)')
            ax4.set_ylabel('Load (%)')
            ax4.set_title('Frame Loss Heatmap')
            ax4.set_xticks(range(len(frame_sizes)))
            ax4.set_xticklabels(frame_sizes)
            ax4.set_yticks(range(len(load_percentages)))
            ax4.set_yticklabels(load_percentages)

            # Add colorbar
            cbar = plt.colorbar(im, ax=ax4)
            cbar.set_label('Loss (%)')

            # Add text annotations
            for i in range(len(load_percentages)):
                for j in range(len(frame_sizes)):
                    text = ax4.text(j, i, f'{loss_matrix[i][j]:.2f}',
                                   ha="center", va="center", color="black", fontsize=8)

        # 5. Back-to-Back
        ax5 = fig.add_subplot(gs[1, 2])
        b2b_data = results.get("back_to_back", {})
        if b2b_data:
            frame_sizes = sorted([int(k) for k in b2b_data.keys()])
            burst_sizes = [b2b_data[str(fs)].get("max_burst_size", 0) for fs in frame_sizes]
            ax5.bar(range(len(frame_sizes)), burst_sizes, color='darkgreen', alpha=0.8)
            ax5.set_xlabel('Frame Size (bytes)')
            ax5.set_ylabel('Burst Size')
            ax5.set_title('Back-to-Back Capacity')
            ax5.set_xticks(range(len(frame_sizes)))
            ax5.set_xticklabels(frame_sizes, rotation=45)
            ax5.grid(True, alpha=0.3)

        # Main title
        test_info = results.get("test_info", {})
        fig.suptitle(f'RFC 2544 Network Performance Dashboard\n'
                     f'Target: {test_info.get("target_ip", "N/A")} | '
                     f'Interface: {test_info.get("interface", "N/A")}',
                     fontsize=20, fontweight='bold')

        output_file = self.plots_dir / "comprehensive_dashboard.png"
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"Saved: {output_file}")

    def generate_all_plots(self):
        """Generate all visualization plots"""
        print("=" * 80)
        print("GENERATING VISUALIZATIONS")
        print("=" * 80)

        results = self.load_rfc2544_results()

        if not results:
            print("No results found to visualize")
            return

        print("\nGenerating individual plots...")
        self.plot_rfc2544_throughput(results)
        self.plot_rfc2544_latency(results)
        self.plot_rfc2544_latency_cdf(results)
        self.plot_rfc2544_frame_loss(results)
        self.plot_rfc2544_back_to_back(results)

        print("\nGenerating comprehensive dashboard...")
        self.plot_comprehensive_dashboard(results)

        print("\n" + "=" * 80)
        print("VISUALIZATION COMPLETE")
        print("=" * 80)
        print(f"Plots saved to: {self.plots_dir}/")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 advanced_visualizer.py <results_directory>")
        print("\nExample:")
        print("  python3 advanced_visualizer.py rfc2544_results_20251103_140000/")
        sys.exit(1)

    results_dir = sys.argv[1]

    if not os.path.exists(results_dir):
        print(f"Error: Results directory not found: {results_dir}")
        sys.exit(1)

    visualizer = NetworkVisualizer(results_dir)
    visualizer.generate_all_plots()

if __name__ == "__main__":
    main()
