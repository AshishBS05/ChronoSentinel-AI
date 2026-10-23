from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.ml.engine import *

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["train", "score", "run", "status"])
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()

    initialize()
    if args.action == "train":
        train(args.limit)
    elif args.action == "score":
        score(min(args.limit, 5000))
    elif args.action == "run":
        if train(args.limit):
            score(min(args.limit, 5000))
    else:
        status()
