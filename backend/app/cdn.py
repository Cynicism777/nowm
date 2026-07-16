# backend/app/cdn.py
import httpx
from app.parser import XhsError, UA

CDN_HOSTS = [
    "sns-img-qc.xhscdn.com",
    "sns-img-bd.xhscdn.com",
    "sns-img-hw.xhscdn.com",
    "sns-img-qn.xhscdn.com",
]


class ImageFetchError(XhsError):
    pass


def nowm_url(file_id: str, host: str = "sns-img-qc.xhscdn.com") -> str:
    return f"https://{host}/{file_id}?imageView2/format/png"


def fetch_image(file_id: str, client: httpx.Client | None = None,
                timeout: float = 15) -> bytes:
    # 关键：不带 Referer，避免源站防盗链 403
    own = client or httpx.Client(headers={"User-Agent": UA}, timeout=timeout)
    try:
        for host in CDN_HOSTS:
            try:
                r = own.get(nowm_url(file_id, host))
            except httpx.HTTPError:
                continue
            if r.status_code == 200 and r.content:
                return r.content
        raise ImageFetchError(f"图片拉取失败: {file_id}")
    finally:
        if client is None:
            own.close()
