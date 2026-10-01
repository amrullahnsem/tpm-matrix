"""Convenience launcher:  python run.py [--port 8000] [--migrate] [--reports]"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="EFLOW TPM Competency Matrix")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="HTTP port (default: 8000)")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"), help="bind host (default: 127.0.0.1)")
    parser.add_argument("--workers", type=int, default=int(os.getenv("WORKERS", "1")), help="worker count (default: 1)")
    parser.add_argument(
        "--reload",
        dest="reload",
        action="store_true",
        default=os.getenv("RELOAD", "false").lower() in ("1", "true", "yes"),
        help="enable auto-reload on code change",
    )
    parser.add_argument("--no-reload", dest="reload", action="store_false", help="disable auto-reload")
    parser.add_argument("--migrate", action="store_true", help="apply pending DB migrations first")
    parser.add_argument("--reports", action="store_true", help="regenerate all reports and exit")
    args = parser.parse_args()

    # Check if migration requested via flag or environment variable
    if args.migrate or os.getenv("MIGRATE_ON_STARTUP", "").lower() in ("1", "true", "yes"):
        from seed.migrate import main as migrate

        migrate()
        print()

    if args.reports:
        from app import reports as report_builder
        from app.repository import Repository

        repo = Repository()
        artifacts = [
            report_builder.individual_competency_report(repo, "emp-101"),
            report_builder.department_competency_report(repo, "Crusher Maintenance"),
            report_builder.competency_gap_report(repo, department="Crusher Maintenance"),
            report_builder.training_needs_report(repo, department="Crusher Maintenance"),
            report_builder.competency_progress_report(repo, "emp-101"),
        ]
        for artifact in artifacts:
            print(f"{artifact.name:<32} {artifact.row_count:>4} rows  ->  {artifact.pdf.name}")
        return

    import uvicorn

    print(f"EFLOW TPM Competency Matrix  ->  http://{args.host}:{args.port}")
    print("  /                     employee list")
    print("  /employee/emp-101     dashboard + spider chart")
    print("  /assess/emp-101       supervisor assessment form")
    print("  /reports              PDF / Excel exports")
    print("  /docs                 OpenAPI + /redoc")
    print("  /healthz              Health check")
    
    uvicorn_kwargs: dict[str, object] = {
        "host": args.host,
        "port": args.port,
        "log_level": os.getenv("LOG_LEVEL", "info").lower(),
    }
    if args.reload:
        uvicorn_kwargs["reload"] = True
    elif args.workers > 1:
        uvicorn_kwargs["workers"] = args.workers

    uvicorn.run("app.server:app", **uvicorn_kwargs)


if __name__ == "__main__":
    main()
