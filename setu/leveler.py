"""Structure-only leveler v0 for Telugu and Hindi target sentences (A1-B2).

Deterministic, no lexical frequency (IndicCorp not downloaded), no model. A sentence gets a difficulty score from
length, conjuncts and grammatical markers; fixed a-priori thresholds map the score to A1..B2. Weights are
hand-set BEFORE looking at the native levels and are a draft: validate with scripts/level_items.py. It does not
replace Madhav's leveler-v0 (script/vocab/word-forms/structure bands); it is a cheap sentence-level second opinion.
"""
import re
import unicodedata

VERSION = "setu-leveler-v0"
BANDS = ("A1", "A2", "B1", "B2")
THRESHOLDS = (1.5, 3.0, 4.5)
VIRAMA = {"te": "్", "hi": "्"}

# marker -> weight. Telugu: suffix on a token (len>3 guard avoids short pronouns like నేను); Hindi: whole token.
TE_SUFFIX = {"కి": .7, "ని": .7, "లో": .7, "తో": .7, "కంటే": 1.0, "గా": .7, "ల": .4, "లు": .4,
             "తున్నా": 1.0, "తోంది": 1.0, "లేదు": 1.0, "లేరు": 1.0, "ఉన్నా": .6, "ఆరు": .6,
             "తే": 1.5, "ఉంటే": 1.5, "న": 0.0}
TE_REL = ("ఏ", "ఎవరు", "ఏది")  # kept empty-ish on purpose; relative participles are not detectable by surface
HI_TOKENS = {"को": .7, "से": .7, "में": .7, "पर": .7, "का": .7, "की": .7, "के": .7, "ने": 1.5, "तक": .7,
             "नहीं": 1.0, "मत": 1.0, "रहा": 1.0, "रही": 1.0, "रहे": 1.0, "चुका": 1.2, "चुकी": 1.2,
             "अगर": 1.5, "तो": .6, "जो": 3.0, "जिसने": 3.0, "जिसे": 3.0, "कि": 1.5, "क्योंकि": 2.0, "आप": .8, "इसलिए": 1.5}


def _tokens(text):
    return re.findall(r"[ऀ-ॿఀ-౿]+", unicodedata.normalize("NFC", text))


def _lang(text):
    return "te" if re.search(r"[ఀ-౿]", text) else "hi"


def score(text, lang=None):
    lang = lang or _lang(text)
    toks = _tokens(text)
    if not toks:
        raise ValueError("cannot level an empty text")
    s = 0.4 * max(0, len(toks) - 3)
    s += 0.4 * sum(t.count(VIRAMA[lang]) for t in toks if not t.endswith(VIRAMA[lang]))
    if lang == "hi":
        s += sum(HI_TOKENS.get(t, 0) for t in toks)
    else:
        for t in toks:
            for suf, w in TE_SUFFIX.items():
                if len(t) > len(suf) + 1 and t.endswith(suf):
                    s += w
                    break
    return round(s, 2)


def level(text, lang=None):
    sc = score(text, lang)
    return BANDS[sum(sc >= t for t in THRESHOLDS)], sc
