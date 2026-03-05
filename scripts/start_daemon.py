"""Helper: daemonize a Python script so it survives SSH disconnection."""

import os
import subprocess
import sys
import time


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <logfile> <script> [args...]")
        sys.exit(1)

    logfile = sys.argv[1]
    cmd = [sys.executable, "-u"] + sys.argv[2:]

    with open(logfile, "w") as log, open(os.devnull, "r") as devnull:
        proc = subprocess.Popen(
            cmd,
            stdin=devnull,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )

    # Wait briefly and verify process is alive
    time.sleep(0.5)
    if proc.poll() is None:
        print(f"[ok] PID {proc.pid}")
    else:
        print(f"[FAIL] exited with code {proc.returncode}")
        with open(logfile) as f:
            print(f.read())
        sys.exit(1)


if __name__ == "__main__":
    main()
