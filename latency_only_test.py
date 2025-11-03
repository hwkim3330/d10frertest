#!/usr/bin/env python3
"""
Quick Latency Test - RFC 2544 Latency Only
"""
import subprocess
import json
import statistics
import datetime
from pathlib import Path

def test_latency_icmp(target_ip, frame_size, count=1000):
    """Test latency using ICMP ping"""
    print(f"  Testing {frame_size} bytes... ", end='', flush=True)

    # ICMP adds 8 bytes for header
    payload_size = frame_size - 8
    if payload_size < 0:
        payload_size = 0

    cmd = [
        "ping",
        "-c", str(count),
        "-s", str(payload_size),
        "-i", "0.01",  # 10ms interval (more reliable)
        "-W", "2",
        target_ip
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("FAILED")
        return None

    # Parse ping output
    latencies = []
    for line in result.stdout.split("\n"):
        if "time=" in line:
            try:
                time_str = line.split("time=")[1].split()[0]
                latency = float(time_str)
                latencies.append(latency)
            except:
                pass

    if not latencies:
        print("NO DATA")
        return None

    # Calculate statistics
    def percentile(data, percent):
        sorted_data = sorted(data)
        index = (len(sorted_data) - 1) * percent / 100
        floor = int(index)
        ceil = floor + 1
        if ceil >= len(sorted_data):
            return sorted_data[floor]
        fraction = index - floor
        return sorted_data[floor] * (1 - fraction) + sorted_data[ceil] * fraction

    stats = {
        "frame_size": frame_size,
        "count": len(latencies),
        "min": min(latencies),
        "max": max(latencies),
        "avg": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "stddev": statistics.stdev(latencies) if len(latencies) > 1 else 0,
        "p50": percentile(latencies, 50),
        "p90": percentile(latencies, 90),
        "p95": percentile(latencies, 95),
        "p99": percentile(latencies, 99),
        "p99.9": percentile(latencies, 99.9),
        "jitter": statistics.stdev(latencies) if len(latencies) > 1 else 0
    }

    print(f"avg: {stats['avg']:.3f}ms, p99: {stats['p99']:.3f}ms ✓")

    return stats

def main():
    target_ip = "192.168.1.3"
    frame_sizes = [64, 128, 256, 512, 1024, 1280, 1518]

    print("=" * 80)
    print("RFC 2544 LATENCY TEST")
    print("=" * 80)
    print(f"Target: {target_ip}")
    print(f"Samples: 1000 per frame size")
    print("=" * 80)
    print()

    results = {}

    for frame_size in frame_sizes:
        stats = test_latency_icmp(target_ip, frame_size, count=1000)
        if stats:
            results[frame_size] = stats

    # Save results
    output_dir = Path("latency_test_results_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "latency.json", "w") as f:
        json.dump(results, f, indent=2)

    # Generate summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"{'Frame Size':<12} {'Min':<10} {'Avg':<10} {'Max':<10} {'P99':<10} {'Jitter':<10}")
    print("-" * 80)

    for frame_size in frame_sizes:
        if frame_size in results:
            r = results[frame_size]
            print(f"{frame_size:<12} {r['min']:<10.3f} {r['avg']:<10.3f} {r['max']:<10.3f} {r['p99']:<10.3f} {r['jitter']:<10.3f}")

    print()
    print(f"Results saved to: {output_dir}/latency.json")
    print("=" * 80)

if __name__ == "__main__":
    main()
