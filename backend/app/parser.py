import re
import json
from dataclasses import dataclass
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

_LINK_RE = re.compile(r"https?://(?:xhslink\.com|www\.xiaohongshu\.com)/\S+")
_STATE_RE = re.compile(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>", re.S)


class XhsError(Exception):
    """基类"""


class NoLinkError(XhsError):
    pass


class ExpiredError(XhsError):
    pass


class ParseError(XhsError):
    pass


@dataclass
class ImageMeta:
    file_id: str
    width: int
    height: int


@dataclass
class NoteData:
    note_id: str
    title: str
    author: str
    images: list[ImageMeta]


def extract_link(text: str) -> str:
    m = _LINK_RE.search(text)
    if not m:
        raise NoLinkError("未识别到小红书链接")
    return m.group(0).rstrip("，,。）)]】")


def resolve(text: str, client: httpx.Client | None = None) -> str:
    url = extract_link(text)
    if "xhslink.com" not in url:
        return url
    own = client or httpx.Client(headers={"User-Agent": UA}, timeout=15,
                                 follow_redirects=False)
    try:
        r = own.get(url)
        loc = r.headers.get("location")
        if not loc:
            raise ParseError("短链未返回跳转地址")
        return loc
    finally:
        if client is None:
            own.close()


def parse_note(html: str) -> NoteData:
    m = _STATE_RE.search(html)
    if not m:
        raise ExpiredError("链接已失效，请重新复制分享链接")
    try:
        data = json.loads(m.group(1).replace("undefined", "null"))
        detail_map = data["note"]["noteDetailMap"]
        if not detail_map:
            raise ExpiredError("链接已失效，请重新复制分享链接")
        note = next(iter(detail_map.values()))["note"]
        images = [
            ImageMeta(file_id=i["fileId"], width=int(i.get("width", 0)),
                      height=int(i.get("height", 0)))
            for i in note.get("imageList", []) if i.get("fileId")
        ]
    except ExpiredError:
        raise
    except (KeyError, ValueError, TypeError, StopIteration) as e:
        raise ParseError(f"解析失败，接口可能已变更: {e}") from e
    if not images:
        raise ExpiredError("链接已失效，请重新复制分享链接")
    return NoteData(
        note_id=note.get("noteId", ""),
        title=note.get("title") or note.get("desc", "")[:20] or "小红书笔记",
        author=note.get("user", {}).get("nickname", ""),
        images=images,
    )
