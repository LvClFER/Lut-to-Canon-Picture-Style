"""Verify color math against actual isolated compiler calls, not synthetic labels."""
import argparse
import json
from pathlib import Path
from .color_math_reference import forward_color, inverse_color


def validate(trace):
    checks, coverage = [], []
    for row in trace["files"]:
        if "error" in row:
            coverage.append({"model": row["model"], "error": row["error"]}); continue
        color_calls = {key: value for key, value in row["mlibCalls"]["counts"].items() if key.startswith("color_")}
        coverage.append({"model": row["model"], "payloadSize": row["payloadSize"], "observedCalls": color_calls})
        for item in row["mlibCalls"]["captures"]:
            if item["functionRva"] == "0x1000":
                expected, rc = forward_color(item["input"], item["mode"]), 0
            elif item["functionRva"] == "0x1790":
                expected, rc = inverse_color(item["input"], item["mode"])
            else:
                continue
            error = max(abs(a - b) for a, b in zip(expected, item["output"]))
            checks.append({"model": row["model"], "functionRva": item["functionRva"], "mode": item["mode"],
                "maxAbsoluteError": error, "within1eMinus14": error <= 1e-14,
                "rcMatches": rc == item["result"]})
    return {"cameraAcceptanceEstablished": False, "coverage": coverage, "checks": checks,
            "passed": sum(item["within1eMinus14"] and item["rcMatches"] for item in checks)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = validate(json.loads(args.trace.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"cases": len(report["checks"]), "passed": report["passed"],
                      "maxError": max((item["maxAbsoluteError"] for item in report["checks"]), default=None)}))


if __name__ == "__main__":
    main()
