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
    class FakeResp:
        status_code = 403
        content = b""
    class FakeClient:
        def get(self, url):
            return FakeResp()
    with pytest.raises(ImageFetchError):
        fetch_image("notes_pre_post/aaa", client=FakeClient())
