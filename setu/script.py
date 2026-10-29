"""Script bridge between Devanagari (which Hindi speakers read) and Telugu.

Unicode lays both blocks out in the same order (ISCII heritage), so most letters convert by a fixed offset of
0x300 (क U+0915 <-> క U+0C15). The few places where a Hindi reader's habits mislead are handled explicitly and are
what the letter bridge teaches:
  * Telugu has short ఎ/ఒ (and signs ె/ొ) as well as long ఏ/ఓ; Hindi has only the long ones. Devanagari has
    ऎ/ऒ (U+090E/U+0912, used for Dravidian languages) for the short sounds, but Hindi speakers type ए/ओ.
  * Telugu ళ (retroflex l) and ఱ have Devanagari twins ळ / ऱ that Hindi does not use.
  * Hindi readers drop a word-final vowel 'a' (कमल = kamal); Telugu pronounces it. Many Telugu words end in ం,
    which a Hindi speaker may type as a final म.
These rules are drafts and need a native check (paper, Section 9)."""
from __future__ import annotations
import re
import unicodedata

DEVA, TELU, OFF = (0x0900, 0x097F), (0x0C00, 0x0C7F), 0x300
_SHORT_LONG = str.maketrans({"ఎ": "ఏ", "ఒ": "ఓ", "ె": "ే", "ొ": "ో"})


def _assigned(cp: int) -> bool:
    try:
        unicodedata.name(chr(cp)); return True
    except ValueError:
        return False


def has_devanagari(text: str) -> bool:
    return any(DEVA[0] <= ord(c) <= DEVA[1] for c in text)


def has_telugu(text: str) -> bool:
    return any(TELU[0] <= ord(c) <= TELU[1] for c in text)


def deva_to_telugu(text: str) -> str:
    """What a Hindi speaker typed in Devanagari -> Telugu script, letter by letter (see `final_m_variant`)."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("ँ", "ं")                            # chandrabindu -> anusvara
    out = []
    for c in text:
        cp = ord(c)
        if c in "।॥":
            out.append(c)
        elif DEVA[0] <= cp <= DEVA[1] and _assigned(cp + OFF):
            out.append(chr(cp + OFF))
        else:
            out.append(c)
    return "".join(out)


def telugu_to_deva(text: str) -> str:
    """Reading aid: Telugu -> Devanagari letters (short ఎ/ఒ become ऎ/ऒ, ళ becomes ळ)."""
    out = []
    for c in unicodedata.normalize("NFC", text):
        cp = ord(c)
        out.append(chr(cp - OFF) if TELU[0] <= cp <= TELU[1] and _assigned(cp - OFF) else c)
    return "".join(out)


def final_m_variant(telugu: str) -> str:
    """A Hindi speaker may type a final म for Telugu ం (पुस्तकम for పుస్తకం). Not applied after a virama, so అమ్మ stays."""
    return re.sub(r"(?<!్)మ(?=$|[\s?!.,।])", "ం", telugu)


def fold_vowel_length(text: str) -> str:
    """Telugu with short and long e/o merged; used only to forgive a Devanagari-typed ए/ओ for ఎ/ఒ."""
    return text.translate(_SHORT_LONG)


# The letter bridge (Step 0): what is new for a Hindi reader. Everything else is a new shape for a known sound.
DIFFERENCES = [
    {"telugu": "ఎ ె / ఏ ే", "deva": "ऎ / ए", "note": "Telugu has a short e and a long e. Hindi has only the long one.", "example": ["ఎవరు", "ఏమిటి"]},
    {"telugu": "ఒ ొ / ఓ ో", "deva": "ऒ / ओ", "note": "Telugu has a short o and a long o.", "example": ["ఒకటి", "ఓడ"]},
    {"telugu": "ళ", "deva": "ळ", "note": "Retroflex l: the tongue curls back, as in Marathi.", "example": ["పళ్ళు"]},
    {"telugu": "ఱ", "deva": "ऱ", "note": "An older strong r; in modern Telugu usually said like ర.", "example": []},
    {"telugu": "ం", "deva": "ं", "note": "Very common at the end of words (పుస్తకం). Type it as ं, or a final म.", "example": ["పుస్తకం"]},
    {"telugu": "final -a", "deva": "-अ", "note": "Telugu says the last vowel. Hindi readers drop it (कमल = kamal), Telugu does not.", "example": ["అది", "ఇది"]},
]
