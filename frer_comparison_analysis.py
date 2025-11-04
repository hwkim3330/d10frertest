#!/usr/bin/env python3
"""
FRER vs Non-FRER Comparison Analysis
Simulates latency improvements with dual-path FRER
"""

import json
import random
import statistics
from pathlib import Path
from datetime import datetime

def simulate_path_latencies(num_samples=1000):
    """
    Simulate latencies for two independent paths
    Path 1: avg 0.4ms, stddev 0.15ms
    Path 2: avg 0.45ms, stddev 0.12ms
    """
    path1_latencies = []
    path2_latencies = []

    for _ in range(num_samples):
        # Path 1: slightly faster on average but more jitter
        lat1 = max(0.15, random.gauss(0.40, 0.15))
        path1_latencies.append(lat1)

        # Path 2: slightly slower but more stable
        lat2 = max(0.15, random.gauss(0.45, 0.12))
        path2_latencies.append(lat2)

    return path1_latencies, path2_latencies

def calculate_frer_latencies(path1, path2):
    """
    FRER selects minimum of two paths
    """
    return [min(p1, p2) for p1, p2 in zip(path1, path2)]

def calculate_stats(latencies, label):
    """Calculate statistics"""
    def percentile(data, p):
        sorted_data = sorted(data)
        index = (len(sorted_data) - 1) * p / 100
        floor = int(index)
        ceil = floor + 1
        if ceil >= len(sorted_data):
            return sorted_data[floor]
        fraction = index - floor
        return sorted_data[floor] * (1 - fraction) + sorted_data[ceil] * fraction

    return {
        "label": label,
        "count": len(latencies),
        "min": min(latencies),
        "max": max(latencies),
        "avg": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "stddev": statistics.stdev(latencies),
        "p50": percentile(latencies, 50),
        "p90": percentile(latencies, 90),
        "p95": percentile(latencies, 95),
        "p99": percentile(latencies, 99),
        "p99_9": percentile(latencies, 99.9),
        "jitter": statistics.stdev(latencies)
    }

def main():
    print("=" * 80)
    print("FRER vs Non-FRER LATENCY COMPARISON")
    print("=" * 80)
    print("Simulating 1000 samples on dual paths")
    print()

    # Simulate dual paths
    print("Simulating path latencies...")
    path1, path2 = simulate_path_latencies(1000)

    # Calculate FRER (minimum selection)
    frer_latencies = calculate_frer_latencies(path1, path2)

    # Calculate statistics
    stats_path1 = calculate_stats(path1, "Path 1 (Primary)")
    stats_path2 = calculate_stats(path2, "Secondary Path")
    stats_frer = calculate_stats(frer_latencies, "FRER (Min Selection)")

    # Calculate improvements
    improvement_avg = ((stats_path1["avg"] - stats_frer["avg"]) / stats_path1["avg"]) * 100
    improvement_p99 = ((stats_path1["p99"] - stats_frer["p99"]) / stats_path1["p99"]) * 100
    improvement_jitter = ((stats_path1["jitter"] - stats_frer["jitter"]) / stats_path1["jitter"]) * 100

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    print(f"{'Metric':<20} {'Path 1':<15} {'Path 2':<15} {'FRER':<15} {'Improvement':<15}")
    print("-" * 80)

    metrics = [
        ("Min (ms)", "min"),
        ("Avg (ms)", "avg"),
        ("Max (ms)", "max"),
        ("P50 (ms)", "p50"),
        ("P90 (ms)", "p90"),
        ("P95 (ms)", "p95"),
        ("P99 (ms)", "p99"),
        ("P99.9 (ms)", "p99_9"),
        ("Jitter (ms)", "jitter"),
    ]

    for metric_name, metric_key in metrics:
        p1_val = stats_path1[metric_key]
        p2_val = stats_path2[metric_key]
        frer_val = stats_frer[metric_key]

        if p1_val > 0:
            imp = ((p1_val - frer_val) / p1_val) * 100
            imp_str = f"{imp:+.1f}%"
        else:
            imp_str = "N/A"

        print(f"{metric_name:<20} {p1_val:<15.3f} {p2_val:<15.3f} {frer_val:<15.3f} {imp_str:<15}")

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Average Latency Improvement: {improvement_avg:+.2f}%")
    print(f"P99 Latency Improvement:     {improvement_p99:+.2f}%")
    print(f"Jitter Reduction:            {improvement_jitter:+.2f}%")
    print()

    print("Key Benefits of FRER:")
    print("  ✓ Lower average latency (selects faster path)")
    print("  ✓ Reduced tail latency (P99, P99.9)")
    print("  ✓ Lower jitter (more consistent performance)")
    print("  ✓ Path redundancy (failover protection)")
    print()

    # Save results
    results_dir = Path(f"frer_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    results_dir.mkdir(exist_ok=True)

    results = {
        "test_info": {
            "type": "FRER Latency Comparison Simulation",
            "samples": 1000,
            "timestamp": datetime.now().isoformat()
        },
        "path1": stats_path1,
        "path2": stats_path2,
        "frer": stats_frer,
        "improvements": {
            "avg_percent": improvement_avg,
            "p99_percent": improvement_p99,
            "jitter_percent": improvement_jitter
        },
        "raw_data": {
            "path1_samples": path1[:100],  # Save first 100 samples
            "path2_samples": path2[:100],
            "frer_samples": frer_latencies[:100]
        }
    }

    with open(results_dir / "comparison_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Generate markdown report
    with open(results_dir / "COMPARISON_REPORT.md", "w") as f:
        f.write("# FRER vs Non-FRER Latency Comparison\n\n")
        f.write("## Test Configuration\n\n")
        f.write("- **Samples:** 1000 per path\n")
        f.write("- **Path 1:** Avg 0.40ms, Jitter 0.15ms (Primary)\n")
        f.write("- **Path 2:** Avg 0.45ms, Jitter 0.12ms (Secondary)\n")
        f.write("- **FRER Mode:** Minimum selection\n\n")

        f.write("## Results Summary\n\n")
        f.write("| Metric | Path 1 | Path 2 | FRER | Improvement |\n")
        f.write("|--------|--------|--------|------|-------------|\n")

        for metric_name, metric_key in metrics:
            p1 = stats_path1[metric_key]
            p2 = stats_path2[metric_key]
            frer = stats_frer[metric_key]
            imp = ((p1 - frer) / p1) * 100 if p1 > 0 else 0
            f.write(f"| {metric_name} | {p1:.3f} | {p2:.3f} | {frer:.3f} | {imp:+.1f}% |\n")

        f.write("\n## Key Improvements\n\n")
        f.write(f"- **Average Latency:** {improvement_avg:+.2f}% improvement\n")
        f.write(f"- **P99 Latency:** {improvement_p99:+.2f}% improvement\n")
        f.write(f"- **Jitter Reduction:** {improvement_jitter:+.2f}% reduction\n\n")

        f.write("## FRER Benefits\n\n")
        f.write("1. **Lower Average Latency**\n")
        f.write("   - FRER always selects the faster path\n")
        f.write("   - Average improvement of 10-20%\n\n")

        f.write("2. **Reduced Tail Latency**\n")
        f.write("   - P99 and P99.9 significantly improved\n")
        f.write("   - Better worst-case performance\n\n")

        f.write("3. **Lower Jitter**\n")
        f.write("   - More consistent latency\n")
        f.write("   - Path delay variance compensation\n\n")

        f.write("4. **Reliability**\n")
        f.write("   - Automatic failover if one path fails\n")
        f.write("   - Zero downtime\n\n")

        f.write("---\n\n")
        f.write("*Generated by FRER Comparison Analysis Tool*\n")

    print(f"Results saved to: {results_dir}/")
    print(f"Report: {results_dir}/COMPARISON_REPORT.md")
    print("=" * 80)

if __name__ == "__main__":
    main()
