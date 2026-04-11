import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPTS = ["epic.PY", "steam.py"]


def run_script(script_name):
    script_path = ROOT / script_name
    print(f"Running {script_name}...")
    result = subprocess.run([sys.executable, str(script_path)], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(f"{script_name} failed with exit code {result.returncode}")
    print(f"Finished {script_name}.")


def main():
    for script_name in SCRIPTS:
        run_script(script_name)
    print("All notifier scripts completed successfully.")


if __name__ == "__main__":
    main()
