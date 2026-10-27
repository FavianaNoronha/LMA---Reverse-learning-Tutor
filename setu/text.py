import re, unicodedata

_PUNCT = re.compile(r"[?!.,।\"'“”‘’:;()]")
_INVIS = re.compile("[​‌‍]")


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFC", text)
    t = _INVIS.sub("", t)
    t = _PUNCT.sub(" ", t)
    return " ".join(t.split())


def tokens(text: str) -> list[str]:
    n = normalize(text)
    return n.split() if n else []
