"""Start the host pilot model using a verified GGUF and llama.cpp b12125."""
import argparse
import shutil
import subprocess
from pathlib import Path

from scripts.pilot_setup import MODEL, MODEL_SHA, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", default="llama-server")
    parser.add_argument("--model", type=Path, default=MODEL)
    args = parser.parse_args()
    binary = shutil.which(args.binary)
    if not binary:
        parser.error("Install llama.cpp b12125 or supply --binary with its executable path")
    try:
        verify(args.model, MODEL_SHA)
        version = subprocess.run([binary, "--version"], capture_output=True, timeout=15, check=True)
        if b"12125" not in (version.stdout + version.stderr):
            parser.error("Expected llama.cpp build b12125; inspect llama-server --version")
        subprocess.run([binary, "-m", str(args.model), "-a", "qwen-pilot", "--host", "127.0.0.1",
                        "--port", "18963", "-c", "8192", "-t", "4", "-np", "1", "--temp", "0",
                        "--offline"], check=True)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
