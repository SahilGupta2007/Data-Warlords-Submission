"""
AgentIQ FinTech single-command launcher.

Usage:
    python run_all.py
    python run_all.py --rebuild
    python run_all.py --pipeline-only
"""

from pathlib import Path
import socket
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
PIPELINE_STEPS = (
    ("Data Rescue & Harmonization Pipeline", "pipeline/clean_pipeline.py"),
    ("Analytical Data Warehouse (DuckDB Views)", "pipeline/analytics_store.py"),
    ("Fraud Ring & Network Detector", "pipeline/graph_detector.py"),
)
REQUIRED_OUTPUTS = (
    "data/processed/fintech_warehouse.duckdb",
    "data/processed/fraud_rings.json",
    "data/processed/audit_proof.json",
)


def run(command):
    """Run a project command from the repository root or stop on failure."""
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def outputs_are_ready():
    return all((PROJECT_ROOT / output).is_file() for output in REQUIRED_OUTPUTS)


def available_port(start=8501, attempts=20):
    for port in range(start, start + attempts):
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No available local port found for Streamlit.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 66)
    print("       AGENTIQ FINTECH - PIPELINE & DASHBOARD LAUNCHER")
    print("=" * 66)
    print(f"Using Python: {sys.executable}\n")

    try:
        rebuild = "--rebuild" in sys.argv or "--pipeline-only" in sys.argv
        if rebuild or not outputs_are_ready():
            for index, (label, script) in enumerate(PIPELINE_STEPS, start=1):
                print(f"[{index}/3] Running {label}...")
                run([sys.executable, str(PROJECT_ROOT / script)])

            print("\n[SUCCESS] All data pipelines and analytics are ready.")
            print(f"Processed data: {PROJECT_ROOT / 'data' / 'processed'}")
        else:
            print("Processed data is ready; skipping the rebuild.")
            print("Use `python run_all.py --rebuild` when source data changes.")

        if "--pipeline-only" in sys.argv:
            return

        port = available_port()
        print(f"\nLaunching AgentIQ FinTech at http://localhost:{port} ...")
        run([
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(PROJECT_ROOT / "dashboard" / "app.py"),
            "--server.port",
            str(port),
        ])
    except subprocess.CalledProcessError as exc:
        print(f"\n[ERROR] Command failed with exit code {exc.returncode}.", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
    except KeyboardInterrupt:
        print("\nAgentIQ FinTech stopped.")


if __name__ == "__main__":
    main()
