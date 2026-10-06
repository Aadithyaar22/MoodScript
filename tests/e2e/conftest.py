"""Browser-test fixtures: starts the test backend and the real Vite frontend once per session,
resets backend state before every test, and fails loudly (with the server's own output) if a
server dies or never comes up."""
import os
import subprocess
import sys
import time
import urllib.request

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FRONTEND_DIR = os.path.join(BACKEND_ROOT, "frontend")
BACKEND_PORT = int(os.environ.get("E2E_BACKEND_PORT", "8765"))
FRONTEND_PORT = int(os.environ.get("E2E_FRONTEND_PORT", "5199"))
BACKEND_URL = f"http://127.0.0.1:{BACKEND_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"


def _wait(url, proc, name, log_path, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"{name} exited early (code {proc.returncode}):\n{open(log_path).read()[-3000:]}")
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"{name} did not become ready at {url} within {timeout}s:\n{open(log_path).read()[-3000:]}")


@pytest.fixture(scope="session")
def servers(tmp_path_factory):
    logdir = tmp_path_factory.mktemp("e2e-logs")
    procs = []
    try:
        be_log, fe_log = str(logdir / "backend.log"), str(logdir / "frontend.log")
        be = subprocess.Popen([sys.executable, os.path.join(HERE, "serve_backend.py")],
                              stdout=open(be_log, "w"), stderr=subprocess.STDOUT, cwd=BACKEND_ROOT,
                              env={**os.environ, "E2E_BACKEND_PORT": str(BACKEND_PORT),
                                   "E2E_FRONTEND_PORT": str(FRONTEND_PORT)})
        procs.append(be)
        fe = subprocess.Popen(["npm", "run", "dev", "--", "--port", str(FRONTEND_PORT), "--strictPort",
                               "--host", "localhost"],
                              stdout=open(fe_log, "w"), stderr=subprocess.STDOUT, cwd=FRONTEND_DIR,
                              env={**os.environ, "VITE_API_BASE": BACKEND_URL})
        procs.append(fe)
        _wait(f"{BACKEND_URL}/health", be, "test backend", be_log)
        _wait(FRONTEND_URL, fe, "frontend dev server", fe_log)
        yield {"backend": BACKEND_URL, "frontend": FRONTEND_URL}
    finally:
        for p in procs:
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


@pytest.fixture(scope="session")
def base_url(servers):
    return servers["frontend"]


@pytest.fixture(autouse=True)
def fresh_backend(servers):
    urllib.request.urlopen(urllib.request.Request(f"{servers['backend']}/__test/reset", method="POST"))


@pytest.fixture
def backend(servers):
    """Steer the fake model services / read what they were asked, from inside a test."""
    import json

    class Control:
        def set(self, **settings):
            req = urllib.request.Request(f"{servers['backend']}/__test/stub", method="POST",
                                         data=json.dumps(settings).encode(),
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req)

        def requests(self):
            return json.load(urllib.request.urlopen(f"{servers['backend']}/__test/requests"))
    return Control()


@pytest.fixture
def js_errors(page):
    """Collects uncaught JavaScript errors so a test can assert the page never threw."""
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    return errors
