from setu.leveler import level, score, BANDS


def test_short_is_a1():
    assert level("నువ్వు వస్తావా")[0] == "A1"
    assert level("यह मेरी किताब है")[0] in ("A1", "A2")


def test_longer_with_markers_is_harder():
    assert score("मैंने कल उसको घर में खाना दिया क्योंकि वह नहीं आया") > score("वह आया")
    assert BANDS.index(level("जो लड़का कल आया था उसने मुझे किताब दी क्योंकि मैंने कहा")[0]) >= 2


def test_empty_raises():
    import pytest
    with pytest.raises(ValueError):
        score("!!")
