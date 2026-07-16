import io
import zipfile
import pytest
from fastapi.testclient import TestClient
from app import main

@pytest.fixture
def client(monkeypatch):
    # 打桩：绕开真实网络
    from app import parser, cdn
    monkeypatch.setattr(main, "load_note", lambda share: parser.NoteData(
        note_id="n1", title="标题", author="作者",
        images=[parser.ImageMeta("notes_pre_post/aaa", 1440, 1920),
                parser.ImageMeta("notes_pre_post/bbb", 1080, 1440)]))
    monkeypatch.setattr(main, "fetch_image", lambda fid: b"\x89PNG" + fid.encode())
    return TestClient(main.app)

def test_parse_endpoint(client):
    r = client.post("/api/parse", json={"share": "http://xhslink.com/o/x"})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "标题"
    assert len(body["images"]) == 2
    assert body["images"][0]["url"].startswith("/api/image?file_id=")

def test_image_endpoint(client):
    r = client.get("/api/image", params={"file_id": "notes_pre_post/aaa"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content.startswith(b"\x89PNG")

def test_package_endpoint(client):
    r = client.post("/api/package",
                    json={"file_ids": ["notes_pre_post/aaa", "notes_pre_post/bbb"],
                          "title": "我的笔记"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    assert len(zf.namelist()) == 2

def test_package_endpoint_all_failed(client, monkeypatch):
    from app import cdn

    def _raise(fid):
        raise cdn.ImageFetchError("boom")

    monkeypatch.setattr(main, "fetch_image", _raise)
    r = client.post("/api/package",
                    json={"file_ids": ["notes_pre_post/aaa", "notes_pre_post/bbb"],
                          "title": "我的笔记"})
    assert r.status_code == 502
