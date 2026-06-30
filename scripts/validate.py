import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    python = sys.executable
    run([python, "-m", "py_compile", "app.py", "src/risk_model.py", "tests/test_risk_model.py"])
    run([python, "-m", "unittest", "discover", "-s", "tests"])
