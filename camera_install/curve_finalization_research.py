"""Independent translation of observed 1df30 finalization, private research."""
import argparse
import json
import struct
from pathlib import Path


def finalize_samples(points, samples):
    if len(samples) < 2 or not points:
        raise ValueError("Need points and at least two samples")
    result = list(samples)
    index = 0
    for i in range(1, len(result)):
        x = i / (len(result) - 1)
        if x > points[index][0]:
            index += 1
        if index >= len(points):
            raise ValueError("Control-point coverage insufficient")
        result[i] = min(max(result[i - 1], result[i]), 1., points[index][1])
    return result


def check_trace(report):
    rows = []
    for row in report["files"]:
        if "error" in row:
            rows.append({"error": row["error"]}); continue
        captures = row["mlibCalls"]["captures"]
        initial = {(item["normalizedPairsFloat64Hex"], item["domainSize"]): item
                   for item in captures if item["functionRva"] == "0x1dc90"}
        for item in captures:
            if item["functionRva"] != "0x1df30":
                continue
            key = (item["normalizedPairsFloat64Hex"], item["domainSize"])
            before = initial[key]
            count, domain = item["curveCount"], item["domainSize"]
            values = struct.unpack(f"<{count * 2}d", bytes.fromhex(key[0]))
            points = list(zip(values[::2], values[1::2]))
            raw = struct.unpack(f"<{domain * 2}d", bytes.fromhex(before["sampledPairsFloat64Hex"]))
            predicted_y = finalize_samples(points, raw[1::2])
            predicted = struct.pack(f"<{domain * 2}d", *[v for pair in zip(raw[::2], predicted_y) for v in pair])
            actual = bytes.fromhex(item["finalizedPairsFloat64Hex"])
            rows.append({"source": row["source"], "points": count, "domain": domain,
                "byteExactFinalization": predicted == actual,
                "changedSamples": sum(a != b for a, b in zip(raw[1::2], predicted_y))})
    return {"cameraAccess": False, "checks": rows,
            "passed": sum(row.get("byteExactFinalization", False) for row in rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = check_trace(json.loads(args.trace.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
