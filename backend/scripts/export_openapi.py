"""Export the FastAPI OpenAPI schema to a file (default ``../docs/openapi.json``).

Usage:
    python -m scripts.export_openapi [--out PATH]

The spec is derived from the live app definition, so regenerate it after changing
any route or Pydantic model to keep the checked-in copy in sync.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.main import app


def main() -> None:
    default_out = Path(__file__).resolve().parent.parent.parent / "docs" / "openapi.json"
    parser = argparse.ArgumentParser(description="Export the OpenAPI schema to JSON.")
    parser.add_argument("--out", default=str(default_out), help="Output file path.")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    out_path.write_text(json.dumps(schema, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"Wrote OpenAPI {schema['openapi']} spec to {out_path.resolve()}")


if __name__ == "__main__":
    main()
