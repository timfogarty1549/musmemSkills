"""
Make sure the local musclememory node server (~/workspace/node/musmem) is
running on port 3000, starting it if necessary. Its /api/* endpoints work
without a signed request when called as localhost -- unlike musclememory.net,
which now rejects unsigned requests.

Importable: call ensure_server() before hitting http://localhost:3000/api/*.
Standalone: python3 ensure_local_server.py
"""
import os
import subprocess
import sys
import time
import urllib.request

SERVER_DIR = os.path.expanduser("~/workspace/node/musmem")
BASE_URL = "http://localhost:3000"
CHECK_URL = f"{BASE_URL}/api/contests"


def is_up():
    try:
        with urllib.request.urlopen(CHECK_URL, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_server(startup_timeout=60):
    if is_up():
        return True

    print(f"Local server not responding on {BASE_URL} -- starting it from {SERVER_DIR} ...", file=sys.stderr)
    if not os.path.isdir(SERVER_DIR):
        print(f"ERROR: {SERVER_DIR} not found. Start the local musmem server manually.", file=sys.stderr)
        return False

    subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=SERVER_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )

    waited = 0
    while waited < startup_timeout:
        time.sleep(2)
        waited += 2
        if is_up():
            print(f"Local server is up (took ~{waited}s).", file=sys.stderr)
            return True

    print(f"ERROR: local server did not come up within {startup_timeout}s.", file=sys.stderr)
    return False


if __name__ == "__main__":
    ok = ensure_server()
    sys.exit(0 if ok else 1)
