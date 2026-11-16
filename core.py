"""Normalize messy Argentine phone numbers into WhatsApp-ready links.

Built on Google's libphonenumber (the `phonenumbers` package), plus the fixes
that real Argentine lead lists need: bare "15" mobiles without an area code,
the duplicated "9 ... 15" marker, extensions, several numbers in one field,
and 0800/0810 lines that can never receive WhatsApp.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Literal, Optional

import phonenumbers as pn
from phonenumbers import PhoneNumberType as T

Kind = Literal["mobile", "unmarked", "non_geographic", "invalid"]

_REGION = "AR"
_NSN_LENGTH = 10  # Argentine national numbers: area code + subscriber = 10 digits

_NON_GEOGRAPHIC = {
    T.TOLL_FREE,      # 0800
    T.UAN,            # 0810
    T.PREMIUM_RATE,   # 0600
    T.SHARED_COST,
    T.VOICEMAIL,
    T.PAGER,
}

_EXTENSION = re.compile(r"\s*(?:int(?:erno)?|ext(?:ensi[oó]n)?|x)\.?\s*\d{1,5}\s*$", re.IGNORECASE)
_SEPARATORS = re.compile(r"\s*(?:/|;|,|\||\n|\bo\b|\by\b)\s*", re.IGNORECASE)
_COUNTRY_PREFIX = re.compile(r"^(?:\+|00)?54")


@dataclass(frozen=True)
class PhoneResult:
    """The outcome of normalizing one phone number."""

    raw: str
    kind: Kind
    e164: Optional[str]
    wa_link: Optional[str]
    reason: str

    @property
    def whatsapp_ready(self) -> bool:
        return self.wa_link is not None

    def to_dict(self) -> dict:
        return asdict(self)


def _wa_link(number: pn.PhoneNumber) -> str:
    return "https://wa.me/" + pn.format_number(number, pn.PhoneNumberFormat.E164).lstrip("+")


def _parse(candidate: str) -> Optional[pn.PhoneNumber]:
    try:
        number = pn.parse(candidate, _REGION)
    except pn.NumberParseException:
        return None
    return number if pn.is_valid_number(number) else None


def _clean(raw: str) -> str:
    text = _EXTENSION.sub("", raw.strip())
    digits = re.sub(r"[^\d+]", "", text)
    # Keep a single leading "+", drop any others.
    return ("+" if digits.startswith("+") else "") + digits.replace("+", "")


def _add_default_area(digits: str, area_code: str) -> str:
    """Prefix an area code to local numbers written without one."""
    if digits.startswith(("+", "0")) or not area_code.isdigit():
        return digits
    subscriber_len = _NSN_LENGTH - len(area_code)
    if digits.startswith("15") and len(digits) == subscriber_len + 2:
        return "0" + area_code + digits  # "15 1234 5678" -> "011 15 1234 5678"
    if len(digits) == subscriber_len:
        return "0" + area_code + digits  # "4567 8901" -> "011 4567 8901"
    return digits


def _drop_duplicate_15(digits: str) -> Optional[pn.PhoneNumber]:
    """Fix "+54 9 11 15 1234 5678": the 9 and the 15 both mark a mobile."""
    national = _COUNTRY_PREFIX.sub("", digits)
    if not national.startswith("9"):
        return None
    for i in range(2, 6):  # "15" sits right after a 2- to 4-digit area code
        if national[i : i + 2] == "15":
            number = _parse("+54" + national[:i] + national[i + 2 :])
            if number is not None and pn.number_type(number) == T.MOBILE:
                return number
    return None


def normalize(
    raw: str,
    default_area_code: Optional[str] = None,
    assume_mobile: bool = False,
) -> PhoneResult:
    """Normalize one Argentine phone number.

    Args:
        raw: The number as it was written ("011 15-1234-5678", "+54 9 221 412 3456"...).
        default_area_code: Area code for numbers written without one, e.g. "11"
            for AMBA or "221" for La Plata. Without it, "15 1234 5678" is invalid.
        assume_mobile: Numbers with no mobile marker (no 9 or 15) may be landlines
            or mobiles. If True, they still get a WhatsApp link built as a mobile.

    Returns:
        A PhoneResult whose kind is "mobile", "unmarked", "non_geographic" or "invalid".
    """
    raw = "" if raw is None else str(raw)
    digits = _clean(raw)
    if len(digits.lstrip("+")) < 6:
        return PhoneResult(raw, "invalid", None, None, "Too few digits to be a phone number.")

    if default_area_code:
        digits = _add_default_area(digits, default_area_code.lstrip("0"))

    number = _parse(digits)
    fixed_marker = False
    if number is None:
        number = _drop_duplicate_15(digits)
        fixed_marker = number is not None
    if number is None:
        hint = "" if default_area_code else " If it has no area code, pass default_area_code."
        return PhoneResult(raw, "invalid", None, None, "Not a valid Argentine number." + hint)

    e164 = pn.format_number(number, pn.PhoneNumberFormat.E164)
    kind = pn.number_type(number)

    if kind == T.MOBILE:
        reason = "Mobile (duplicated 9 and 15 marker removed)." if fixed_marker else "Mobile."
        return PhoneResult(raw, "mobile", e164, _wa_link(number), reason)

    if kind in _NON_GEOGRAPHIC:
        return PhoneResult(raw, "non_geographic", e164, None, "Non-geographic line (0800/0810/0600): no WhatsApp.")

    if kind in (T.FIXED_LINE, T.FIXED_LINE_OR_MOBILE):
        reason = "No mobile marker (9 or 15): could be a landline or a mobile written without it."
        link = None
        if assume_mobile:
            as_mobile = _parse("+549" + str(number.national_number))
            if as_mobile is not None and pn.number_type(as_mobile) == T.MOBILE:
                link = _wa_link(as_mobile)
                reason += " WhatsApp link built assuming mobile."
        return PhoneResult(raw, "unmarked", e164, link, reason)

    return PhoneResult(raw, "invalid", e164, None, "Valid number of an unsupported type.")


def extract_all(
    text: str,
    default_area_code: Optional[str] = None,
    assume_mobile: bool = False,
) -> list[PhoneResult]:
    """Split a field that may hold several numbers ("4567-8901 / 15-1234-5678")
    and normalize each one. Duplicates are returned once."""
    results: list[PhoneResult] = []
    seen: set[str] = set()
    for chunk in _SEPARATORS.split(text or ""):
        if len(re.sub(r"\D", "", chunk)) < 6:
            continue
        result = normalize(chunk, default_area_code, assume_mobile)
        key = result.e164 or result.raw
        if key not in seen:
            seen.add(key)
            results.append(result)
    return results
