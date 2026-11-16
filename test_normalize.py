import pytest

from ar_whatsapp_phone import extract_all, normalize


@pytest.mark.parametrize(
    "raw, e164",
    [
        ("011 15 1234-5678", "+5491112345678"),
        ("(011) 15-1234-5678", "+5491112345678"),
        ("+54 9 11 1234 5678", "+5491112345678"),
        ("0054 9 11 1234 5678", "+5491112345678"),
        ("5491112345678", "+5491112345678"),
        ("0221 15 412 3456", "+5492214123456"),
        ("2954 15 412345", "+5492954412345"),
        ("011-15-1234-5678 int 23", "+5491112345678"),
    ],
)
def test_mobiles(raw, e164):
    r = normalize(raw)
    assert r.kind == "mobile"
    assert r.e164 == e164
    assert r.wa_link == "https://wa.me/" + e164.lstrip("+")


@pytest.mark.parametrize(
    "raw, e164",
    [
        ("+54 9 221 15 412 3456", "+5492214123456"),
        ("9 11 15 1234 5678", "+5491112345678"),
    ],
)
def test_duplicated_9_and_15_marker(raw, e164):
    r = normalize(raw)
    assert r.kind == "mobile"
    assert r.e164 == e164
    assert "duplicated" in r.reason


def test_bare_15_needs_area_code():
    assert normalize("15 1234 5678").kind == "invalid"
    r = normalize("15 1234 5678", default_area_code="11")
    assert r.kind == "mobile"
    assert r.e164 == "+5491112345678"


def test_bare_15_with_three_digit_area():
    r = normalize("15 412 3456", default_area_code="0221")
    assert r.e164 == "+5492214123456"


def test_local_landline_with_default_area():
    r = normalize("4567-8901", default_area_code="11")
    assert r.kind == "unmarked"
    assert r.e164 == "+541145678901"
    assert r.wa_link is None


@pytest.mark.parametrize("raw", ["011 4567 8901", "+54 11 4567 8901", "11 2345 6789"])
def test_unmarked_numbers_get_no_link_by_default(raw):
    r = normalize(raw)
    assert r.kind == "unmarked"
    assert r.wa_link is None


def test_assume_mobile_builds_link():
    r = normalize("+54 11 2345 6789", assume_mobile=True)
    assert r.kind == "unmarked"
    assert r.wa_link == "https://wa.me/5491123456789"


@pytest.mark.parametrize("raw", ["0800 333 1234", "0810 222 3333", "0600 123 4567"])
def test_non_geographic(raw):
    r = normalize(raw)
    assert r.kind == "non_geographic"
    assert r.wa_link is None


@pytest.mark.parametrize("raw", ["", "123", "abc", None, "99999999999999999"])
def test_invalid(raw):
    r = normalize(raw)
    assert r.kind == "invalid"
    assert r.wa_link is None


def test_extract_all_splits_and_dedupes():
    results = extract_all("4567-8901 / 15-1234-5678 o 011 15 1234 5678", default_area_code="11")
    assert [r.kind for r in results] == ["unmarked", "mobile"]
    assert results[1].e164 == "+5491112345678"


def test_extract_all_empty():
    assert extract_all("") == []
    assert extract_all(None) == []
