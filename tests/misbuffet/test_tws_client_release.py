"""BI-020: a process that connected an IBTWSClient and never disconnected still exits and releases its client id.

The subprocess replaces EClient.connect / disconnect with a stand-in that starts a NON-daemon thread ending only on
disconnect — what ibapi's EReader does with the socket. No socket is opened."""

import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCRIPT = textwrap.dedent("""
    import threading
    from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient

    closed = threading.Event()

    class FakeClient(IBTWSClient):
        def connect(self, host, port, client_id):
            self._fake_connected = True
            threading.Thread(target=closed.wait, name="EReader-standin").start()   # non-daemon, like EReader
            self.connection_event.set()
        def disconnect(self):
            self._fake_connected = False
            print("DISCONNECTED", flush=True)
            closed.set()
        def isConnected(self):
            return getattr(self, "_fake_connected", False)
        def run(self):
            pass

    client = FakeClient("127.0.0.1", 1, 77)
    assert client.connect_to_tws()
    print("RUN FINISHED WITHOUT DISCONNECT", flush=True)
""")


def test_a_run_that_never_disconnects_still_exits_and_disconnects():
    proc = subprocess.run([sys.executable, "-c", SCRIPT], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "RUN FINISHED WITHOUT DISCONNECT" in proc.stdout and "DISCONNECTED" in proc.stdout


def test_the_exit_hook_is_registered_once():
    from unittest.mock import patch
    from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
    client = IBTWSClient("127.0.0.1", 1, 78)
    with patch("threading._register_atexit") as register:
        client._release_at_exit()
        client._release_at_exit()
    assert register.call_count == 1
