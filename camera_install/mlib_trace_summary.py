"""Group observed compiler routes, without inferring physical compatibility."""
import argparse
import json
from collections import Counter
from pathlib import Path


def summarize(report):
    routes, failures = {}, []
    for row in report["files"]:
        if "error" in row:
            failures.append({"model": row["model"], "cameraId": row["cameraId"], "error": row["error"]})
            continue
        observation = row["mlibCalls"]
        counts = {key: value for key, value in observation["counts"].items() if key != "curveNormalized"}
        signature = json.dumps({"payloadSize": row["payloadSize"], "counts": counts}, sort_keys=True)
        route = routes.setdefault(signature, {"payloadSize": row["payloadSize"], "counts": counts,
            "models": [], "curveCallers": Counter()})
        route["models"].append({"model": row["model"], "cameraId": row["cameraId"]})
        for capture in observation["captures"]:
            route["curveCallers"].update(capture.get("callers", {}))
    return {"physicalCompatibilityEstablished": False, "cases": len(report["files"]),
            "routeSignatureExcludesOptionalNormalizationObserver": True,
            "successfulCases": sum(len(route["models"]) for route in routes.values()),
            "failedCases": len(failures), "routes": list(routes.values()), "failures": failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("cases", "successfulCases", "failedCases")}))
    for route in result["routes"]:
        print(route["payloadSize"], len(route["models"]), route["counts"], dict(route["curveCallers"]))


if __name__ == "__main__":
    main()
