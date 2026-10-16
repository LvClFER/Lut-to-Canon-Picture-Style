"""Compare original compiler output sensitivity within each recorded model route."""
import argparse
import json
from collections import defaultdict
from pathlib import Path


def summarize_sensitivity(trace):
    models = defaultdict(list)
    for row in trace["files"]:
        models[(row["model"], row["cameraId"])].append(row)
    results = []
    for (model, camera_id), rows in models.items():
        baseline = next((row for row in rows if Path(row["source"]).name == "01_IDENTITY.pf3"), None)
        if baseline is None or "error" in baseline:
            results.append({"model": model, "cameraId": camera_id, "error": "Missing/successless baseline"})
            continue
        variants = [{"source": row["source"], "compiled": "error" not in row,
                     "payloadChanged": "error" not in row and row["payloadSha256"] != baseline["payloadSha256"],
                     "error": row.get("error")} for row in rows if row is not baseline]
        results.append({"model": model, "cameraId": camera_id, "payloadSize": baseline["payloadSize"],
                        "baselineSha256": baseline["payloadSha256"], "variants": variants})
    return {"onlyStockCompilerBehavior": True, "physicalCompatibilityEstablished": False, "models": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize_sensitivity(json.loads(args.trace.read_text(encoding="utf-8")))
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    for model in result["models"]:
        print(model["model"], model.get("payloadSize"),
              sum(variant["payloadChanged"] for variant in model.get("variants", [])),
              '/', len(model.get("variants", [])))


if __name__ == "__main__":
    main()
