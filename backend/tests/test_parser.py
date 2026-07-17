import pathlib
import pytest
from app.parser import extract_link, parse_note, NoLinkError, ExpiredError, NoteData

FIX = pathlib.Path(__file__).parent / "fixtures" / "sample_note.html"

def test_extract_link_from_share_text():
    text = "标题党 http://xhslink.com/o/4bDk4vyM9uJ 存下这段话，去【小红书】"
    assert extract_link(text) == "http://xhslink.com/o/4bDk4vyM9uJ"

def test_extract_link_none_raises():
    with pytest.raises(NoLinkError):
        extract_link("没有链接的一段文字")

def test_parse_note_returns_images():
    note = parse_note(FIX.read_text(encoding="utf-8"))
    assert isinstance(note, NoteData)
    assert note.note_id == "6a53ad2500000000060323d6"
    assert note.title == "测试标题"
    assert note.author == "测试作者"
    assert [i.file_id for i in note.images] == ["notes_pre_post/aaa111", "notes_pre_post/bbb222"]
    assert note.images[0].width == 1440

def test_parse_note_empty_raises_expired():
    html = "<html><body>login wall no state</body></html>"
    with pytest.raises(ExpiredError):
        parse_note(html)
