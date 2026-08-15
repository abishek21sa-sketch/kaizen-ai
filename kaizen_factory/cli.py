from __future__ import annotations

import argparse
import json
from pathlib import Path

from .io import export_result
from .models import FactoryConfig
from .simulator import simulate_factory


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kaizen-factory", description="KAIZEN AI Hidden Factory CLI")
    sub = p.add_subparsers(dest="command", required=True)
    g = sub.add_parser("generate", help="Generate one manufacturing incident")
    g.add_argument("--scenario", default="random")
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--units", type=int, default=2500)
    g.add_argument("--activation", type=float, default=0.42)
    g.add_argument("--out", default="data/runs")
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "generate":
        cfg = FactoryConfig(seed=args.seed, units=args.units, activation_fraction=args.activation)
        result = simulate_factory(cfg, args.scenario)
        paths = export_result(result, Path(args.out))
        print(json.dumps({"run_id": result.run_id, "public_summary": result.public_summary, "paths": paths}, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
