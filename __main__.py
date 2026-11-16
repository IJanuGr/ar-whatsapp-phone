"""Command line: normalize numbers and print CSV.

    python -m ar_whatsapp_phone "011 15 1234-5678" "4567-8901 / 15-1234-5678" --area 11
    cat numbers.txt | python -m ar_whatsapp_phone --area 11 > out.csv
"""

import argparse
import csv
import sys

from .core import extract_all


def main() -> None:
    parser = argparse.ArgumentParser(prog="ar_whatsapp_phone", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("numbers", nargs="*", help="Numbers to normalize. Reads stdin, one per line, if empty.")
    parser.add_argument("--area", help='Default area code for numbers without one, e.g. "11".')
    parser.add_argument("--assume-mobile", action="store_true",
                        help="Build WhatsApp links for numbers with no mobile marker too.")
    args = parser.parse_args()

    lines = args.numbers or [line.rstrip("\n") for line in sys.stdin]
    writer = csv.writer(sys.stdout)
    writer.writerow(["raw", "kind", "e164", "wa_link", "reason"])
    for line in lines:
        for r in extract_all(line, args.area, args.assume_mobile):
            writer.writerow([r.raw, r.kind, r.e164 or "", r.wa_link or "", r.reason])


if __name__ == "__main__":
    main()
