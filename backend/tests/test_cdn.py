import pytest
import httpx
from app.cdn import nowm_url, fetch_image, ImageFetchError, CDN_HOSTS

def test_nowm_url_format():
    assert nowm_url("notes_pre_post/aaa") == \
        "https://sns-img-qc.xhscdn.com/notes_pre_post/aaa?imageView2/format/png"

def test_fetch_image_falls_back_on_error(monkeypatch):
    calls = []
    class FakeResp:
        def __init__(self, code, content=b""):
            self.status_code = code
            self.content = content
    class FakeClient:
        def get(self, url):
            calls.append(url)
            # 第一个 host 失败，第二个成功
            if CDN_HOSTS[0] in url:
                return FakeResp(403)
            return FakeResp(200, b"\x89PNG_data")
    data = fetch_image("notes_pre_post/aaa", client=FakeClient())
    assert data == b"\x89PNG_data"
    assert len(calls) == 2

def test_fetch_image_all_fail_raises(monkeypatch):
    calls = []
    class FakeResp:
        status_code = 403
        content = b""
    class FakeClient:
        def get(self, url):
            calls.append(url)
            return FakeResp()
    with pytest.raises(ImageFetchError):
        fetch_image("notes_pre_post/aaa", client=FakeClient())
    assert len(calls) == len(CDN_HOSTS)

def test_fetch_image_no_referer_header(monkeypatch):
    captured = {}

    class FakeHttpxClient:
        def __init__(self, *, headers=None, timeout=None):
            captured["headers"] = headers
            captured["timeout"] = timeout

        def get(self, url):
            class FakeResp:
                status_code = 200
                content = b"ok"
            return FakeResp()

        def close(self):
            pass

    monkeypatch.setattr("app.cdn.httpx.Client", FakeHttpxClient)
    data = fetch_image("notes_pre_post/aaa")
    headers = captured["headers"]
    assert "User-Agent" in headers
    assert "Referer" not in headers
    assert "referer" not in headers
    assert data == b"ok"

def test_fetch_image_continues_on_http_error():
    calls = []
    class FakeResp:
        def __init__(self, code, content=b""):
            self.status_code = code
            self.content = content
    class FakeClient:
        def get(self, url):
            calls.append(url)
            if CDN_HOSTS[0] in url:
                raise httpx.ConnectError("boom")
            return FakeResp(200, b"\x89PNG_data")
    data = fetch_image("notes_pre_post/aaa", client=FakeClient())
    assert data == b"\x89PNG_data"
    assert len(calls) == 2
