# http_util.py — shared httpx timeout settings
import httpx

from config import http_timeout


def client_timeout() -> httpx.Timeout:
    t = http_timeout()
    return httpx.Timeout(t, connect=min(15.0, t))


def make_client() -> httpx.Client:
    return httpx.Client(timeout=client_timeout())
