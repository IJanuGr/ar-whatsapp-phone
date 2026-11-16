"""Normalize messy Argentine phone numbers into WhatsApp-ready links."""

from .core import PhoneResult, extract_all, normalize

__all__ = ["PhoneResult", "normalize", "extract_all"]
__version__ = "0.1.0"
