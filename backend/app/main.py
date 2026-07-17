import io
import os
import re
import time
import zipfile
import pathlib
import urllib.parse
import httpx
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.parser import (resolve, parse_note, NoteData, UA,
                        NoLinkError, ExpiredError, ParseError)
from app.cdn import fetch_image, ImageFetchError
from app.logging_conf import setup_logging, log_event

logger = setup_logging()
app = FastAPI(title="nowm · cynic 工具箱")

FRONTEND_DIST = pathlib.Path(
    os.environ.get("FRONTEND_DIST",
                   str(pathlib.Path(__file__).resolve().parents[2] / "frontend" / "dist")))

MAX_PACKAGE_IMAGES = 50


class ParseIn(BaseModel):
    share: str


class PackageIn(BaseModel):
    file_ids: list[str]
    title: str = "xiaohongshu"


def load_note(share: str) -> NoteData:
    """解析分享文案 -> NoteData（含真实网络请求）"""
    with httpx.Client(headers={"User-Agent": UA}, timeout=15,
                      follow_redirects=False) as c:
        url = resolve(share, client=c)
        html = c.get(url, follow_redirects=True).text
    return parse_note(html)


def _safe_name(title: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", title).strip() or "xiaohongshu"


@app.post("/api/parse")
def api_parse(body: ParseIn, request: Request):
    t0 = time.time()
    try:
        note = load_note(body.share)
    except NoLinkError as e:
        log_event(logger, client_ip=request.client.host, action="parse",
                  input=body.share, status="no_link")
        raise HTTPException(400, str(e))
    except ExpiredError as e:
        log_event(logger, client_ip=request.client.host, action="parse",
                  input=body.share, status="expired")
        raise HTTPException(422, str(e))
    except (ParseError, httpx.HTTPError):
        log_event(logger, client_ip=request.client.host, action="parse",
                  input=body.share, status="parse_error")
        raise HTTPException(502, "解析失败，接口可能已变更")
    log_event(logger, client_ip=request.client.host, action="parse",
              input=body.share, note_id=note.note_id,
              image_count=len(note.images), status="ok",
              duration_ms=int((time.time() - t0) * 1000))
    return {
        "note_id": note.note_id,
        "title": note.title,
        "author": note.author,
        "images": [
            {"index": i, "file_id": im.file_id, "width": im.width,
             "height": im.height,
             "url": "/api/image?file_id=" + urllib.parse.quote(im.file_id, safe="")}
            for i, im in enumerate(note.images)
        ],
    }


@app.get("/api/image")
def api_image(request: Request, file_id: str = Query(...),
              download: int = 0):
    try:
        data = fetch_image(file_id)
    except ImageFetchError as e:
        log_event(logger, client_ip=request.client.host, action="image",
                  file_id=file_id, status="fetch_error")
        raise HTTPException(502, str(e))
    log_event(logger, client_ip=request.client.host, action="image",
              file_id=file_id, status="ok", bytes=len(data))
    headers = {}
    if download:
        name = file_id.split("/")[-1] + ".png"
        headers["Content-Disposition"] = f'attachment; filename="{name}"'
    return Response(content=data, media_type="image/png", headers=headers)


@app.post("/api/package")
def api_package(body: PackageIn, request: Request):
    if not body.file_ids:
        raise HTTPException(400, "未提供图片")
    if len(body.file_ids) > MAX_PACKAGE_IMAGES:
        raise HTTPException(400, "图片数量超出上限")

    buf = io.BytesIO()
    ok = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as zf:
        for idx, fid in enumerate(body.file_ids, 1):
            try:
                data = fetch_image(fid)
            except ImageFetchError:
                continue
            zf.writestr(f"{idx:02d}.png", data)
            ok += 1
    buf.seek(0)

    if ok == 0:
        log_event(logger, client_ip=request.client.host, action="package",
                  image_count=len(body.file_ids), ok=ok, status="all_failed")
        raise HTTPException(502, "全部图片拉取失败")

    status = "ok" if ok == len(body.file_ids) else "partial"
    log_event(logger, client_ip=request.client.host, action="package",
              image_count=len(body.file_ids), ok=ok, status=status)
    name = urllib.parse.quote(_safe_name(body.title) + ".zip")
    return StreamingResponse(
        buf, media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{name}"})


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
