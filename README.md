# ar-whatsapp-phone

Turn messy Argentine phone numbers into WhatsApp-ready links.

Lead lists scraped from Google Maps, forms or spreadsheets write Argentine numbers in a dozen ways: `011 15-1234-5678`, `+54 9 11 1234 5678`, `15 1234 5678`, `4567-8901 / 15-2345-6789`. WhatsApp only accepts one: `+54 9` + area code + number. This library gets you there and tells you honestly when it can't.

It is built on Google's [libphonenumber](https://github.com/daviddrysdale/python-phonenumbers) and adds the fixes real lists need:

- **Bare `15` mobiles without an area code** (`15 1234 5678`), using a default area code you choose.
- **The duplicated marker** (`+54 9 11 15 1234 5678`): the 9 and the 15 both mean "mobile".
- **Extensions** (`int 23`, `ext. 4`) and **several numbers in one field**.
- **0800 / 0810 / 0600 lines**, which can never receive WhatsApp.
- **No guessing on unmarked numbers.** Without a 9 or a 15, an Argentine number may be a landline or a mobile. It is reported as `unmarked` instead of being silently treated as one or the other.

## Install

```bash
pip install git+https://github.com/IJanuGr/ar-whatsapp-phone
```

## Use

```python
from ar_whatsapp_phone import normalize, extract_all

r = normalize("011 15-1234-5678")
r.kind      # "mobile"
r.e164      # "+5491112345678"
r.wa_link   # "https://wa.me/5491112345678"

normalize("15 1234 5678", default_area_code="11").e164   # "+5491112345678"
normalize("0800 333 1234").kind                          # "non_geographic"
normalize("+54 11 2345 6789").kind                       # "unmarked" (no link)
normalize("+54 11 2345 6789", assume_mobile=True).wa_link  # "https://wa.me/5491123456789"

[r.e164 for r in extract_all("4567-8901 / 15-1234-5678", default_area_code="11")]
# ["+541145678901", "+5491112345678"]
```

Every result has `raw`, `kind`, `e164`, `wa_link` and a plain-language `reason`.

| kind | meaning | WhatsApp link |
| --- | --- | --- |
| `mobile` | Has a mobile marker (9 or 15) | Yes |
| `unmarked` | Valid, but no marker: landline or mobile | Only with `assume_mobile=True` |
| `non_geographic` | 0800, 0810, 0600 | No |
| `invalid` | Not a valid Argentine number | No |

## Command line

```bash
python -m ar_whatsapp_phone "011 15 1234-5678" "4567-8901 / 15-1234-5678" --area 11
cat numbers.txt | python -m ar_whatsapp_phone --area 11 > numbers.csv
```

Outputs CSV with `raw, kind, e164, wa_link, reason`.

## Tests

```bash
pip install -e . pytest
pytest
```

---

## En español

Convierte teléfonos argentinos escritos de cualquier forma en links de WhatsApp. Resuelve el `15` sin código de área, el `9` y el `15` duplicados, internos, varios números en un mismo campo y líneas 0800/0810. Cuando un número no tiene 9 ni 15 no adivina: lo marca como `unmarked`, porque puede ser fijo o celular.

## License

MIT
