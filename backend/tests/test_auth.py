import pytest
from fastapi.testclient import TestClient
from app import main, auth


@pytest.fixture
def client(monkeypatch):
    from app import parser
    monkeypatch.setattr(main, "load_note", lambda share: parser.NoteData(
        note_id="n1", title="标题", author="作者",
        images=[parser.ImageMeta("notes_pre_post/aaa", 1440, 1920)]))
    monkeypatch.setattr(main, "fetch_image", lambda fid: b"\x89PNG" + fid.encode())
    with TestClient(main.app) as c:
        yield c


def test_status_unauthenticated(client):
    r = client.get("/api/auth/status")
    assert r.status_code == 200
    assert r.json() == {"authenticated": False}


def test_claim_bad_invite(client):
    r = client.get("/api/auth/claim", params={"invite": "wrong"})
    assert r.status_code == 401
    assert auth.COOKIE_NAME not in r.cookies


def test_claim_and_status(client):
    r = client.get("/api/auth/claim",
                   params={"invite": "test-invite-token-xxxxxxxxxxxxxxxx"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert auth.COOKIE_NAME in r.cookies
    s = client.get("/api/auth/status")
    assert s.json() == {"authenticated": True}


def test_parse_requires_auth(client):
    r = client.post("/api/parse", json={"share": "http://xhslink.com/o/x"})
    assert r.status_code == 401


def test_parse_ok_after_claim(client):
    client.get("/api/auth/claim",
               params={"invite": "test-invite-token-xxxxxxxxxxxxxxxx"})
    r = client.post("/api/parse", json={"share": "http://xhslink.com/o/x"})
    assert r.status_code == 200
