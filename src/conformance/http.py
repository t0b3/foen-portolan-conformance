"""Anonymous HTTP access with retries, range reads and a recorded (offline) mode.

Every network call in the package goes through `Fetcher`, so tests and offline demos
can swap in `RecordedTransport` without touching the crawler or the probes.
"""

from __future__ import annotations

import base64
import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import requests

OFFLINE = "not recorded (offline replay)"
USER_AGENT = "foen-portolan-conformance/0.1 (+https://github.com/foen-portolan-conformance)"


@dataclass
class Response:
    url: str
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 300

    def header(self, name: str) -> str | None:
        name = name.lower()
        for k, v in self.headers.items():
            if k.lower() == name:
                return v
        return None

    def json(self):
        return json.loads(self.body.decode("utf-8"))


class RecordedTransport:
    """Replays responses from a JSON index: {url: {status, headers, body|body_b64|body_file}}.

    Keys may also be "METHOD url" to record HEAD/OPTIONS separately.
    """

    def __init__(self, index_path: str | Path):
        self.root = Path(index_path).parent
        self.index: dict = json.loads(Path(index_path).read_text())

    def request(self, method: str, url: str, headers: dict[str, str]) -> Response:
        rec = self.index.get(f"{method} {url}") or self.index.get(url)
        if rec is None:
            return Response(url, 0, {}, b"", OFFLINE)
        body = b""
        if "body_b64" in rec:
            body = base64.b64decode(rec["body_b64"])
        elif "body_file" in rec:
            body = (self.root / rec["body_file"]).read_bytes()
        elif "body" in rec:
            b = rec["body"]
            body = (json.dumps(b) if not isinstance(b, str) else b).encode()
        status = rec.get("status", 200)
        rng = headers.get("Range")
        if rng and rec.get("ranges", True) and status == 200 and method == "GET":
            start, _, end = rng.removeprefix("bytes=").partition("-")
            s, e = int(start), min(int(end or len(body) - 1), len(body) - 1)
            hdrs = dict(rec.get("headers", {}))
            hdrs["Content-Range"] = f"bytes {s}-{e}/{len(body)}"
            return Response(url, 206, hdrs, body[s : e + 1])
        if method == "HEAD":
            hdrs = {"Content-Length": str(len(body)), **rec.get("headers", {})}
            return Response(url, status, hdrs, b"")
        return Response(url, status, dict(rec.get("headers", {})), body)


class Fetcher:
    def __init__(
        self,
        timeout: float = 30,
        retries: int = 3,
        transport: RecordedTransport | None = None,
    ):
        self.timeout = timeout
        self.retries = retries
        self.transport = transport
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.calls = 0

    # -- public helpers ------------------------------------------------------------------
    def get(self, url: str, headers: dict[str, str] | None = None) -> Response:
        return self.request("GET", url, headers)

    def head(self, url: str) -> Response:
        return self.request("HEAD", url)

    def get_range(self, url: str, start: int, end: int, extra: dict | None = None) -> Response:
        return self.request("GET", url, {"Range": f"bytes={start}-{end}", **(extra or {})})

    def get_json(self, url: str):
        r = self.get(url)
        if not r.ok:
            raise FetchError(url, r.status, r.error)
        try:
            return r.json()
        except ValueError as e:
            raise FetchError(url, r.status, f"invalid JSON: {e}") from e

    def size(self, url: str) -> int | None:
        r = self.head(url)
        cl = r.header("Content-Length") if r.ok else None
        if cl and cl.isdigit():
            return int(cl)
        # Some hosts refuse HEAD: fall back to a 1-byte range read.
        r = self.get_range(url, 0, 0)
        cr = r.header("Content-Range") or ""
        if "/" in cr and cr.rsplit("/", 1)[1].isdigit():
            return int(cr.rsplit("/", 1)[1])
        return None

    # -- core --------------------------------------------------------------------------
    def request(self, method: str, url: str, headers: dict[str, str] | None = None) -> Response:
        headers = dict(headers or {})
        self.calls += 1
        if _is_local(url):
            return _local(method, url, headers)
        if self.transport is not None:
            return self.transport.request(method, url, headers)
        last: Response | None = None
        for attempt in range(self.retries + 1):
            try:
                r = self.session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    stream=method == "GET",
                )
                # Never pull a whole large file by accident: cap un-ranged GET bodies at 64 MB.
                body = b""
                if method == "GET":
                    chunks, total = [], 0
                    for chunk in r.iter_content(1 << 16):
                        chunks.append(chunk)
                        total += len(chunk)
                        if total > 64 * 1024 * 1024 and "Range" not in headers:
                            break
                    body = b"".join(chunks)
                    r.close()
                last = Response(url, r.status_code, dict(r.headers), body)
                if r.status_code in (429, 500, 502, 503, 504) and attempt < self.retries:
                    _backoff(attempt)
                    continue
                return last
            except requests.RequestException as e:
                last = Response(url, 0, {}, b"", f"{type(e).__name__}: {e}")
                if attempt < self.retries:
                    _backoff(attempt)
        assert last is not None
        return last


class FetchError(RuntimeError):
    def __init__(self, url: str, status: int, error: str | None):
        super().__init__(f"{url}: HTTP {status} {error or ''}".strip())
        self.url, self.status, self.error = url, status, error


def _backoff(attempt: int) -> None:
    time.sleep(min(30, (2**attempt) + random.random()))


def _is_local(url: str) -> bool:
    p = urlparse(url)
    return p.scheme in ("", "file") and not url.startswith("//")


def _local(method: str, url: str, headers: dict[str, str]) -> Response:
    path = Path(urlparse(url).path if url.startswith("file:") else url)
    if not path.exists():
        return Response(url, 404)
    if path.is_dir():
        return Response(url, 403)
    size = path.stat().st_size
    if method == "HEAD":
        return Response(url, 200, {"Content-Length": str(size)})
    rng = headers.get("Range")
    with path.open("rb") as fh:
        if rng:
            start, _, end = rng.removeprefix("bytes=").partition("-")
            s, e = int(start), min(int(end or size - 1), size - 1)
            fh.seek(s)
            return Response(
                url, 206, {"Content-Range": f"bytes {s}-{e}/{size}"}, fh.read(e - s + 1)
            )
        return Response(url, 200, {"Content-Length": str(size)}, fh.read())
