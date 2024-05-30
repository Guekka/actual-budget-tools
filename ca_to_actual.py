from io import StringIO
import json
from math import isnan
import os
from typing import Optional
from re import sub

import pandas as pd

from banks.client import parser, parse_args


def read_csv(csv_file: str, cutoff: Optional[str] = None) -> pd.DataFrame:
    with open(csv_file, encoding="cp1252") as f:
        # replace non-breaking spaces with regular spaces. Yes, really.
        content = f.read().replace("\N{NBSP}", " ")

        df: pd.DataFrame = pd.read_csv(
            StringIO(content),
            sep=";",
            encoding="cp1252",  # who still uses this?
            decimal=",",
            thousands=" ",
            skiprows=10)  # worse, the first 10 lines are in a different format

    if cutoff:
        df = df[df["Date"] < cutoff]

    print (df.keys())

    return df


def convert(csv: pd.DataFrame):

    def fixdate(d: str):
        return "-".join(reversed(d.split("/"))) + "T12:00:00.000Z"

    def fixlbl(l: str):
        REMOVE = [
            "VIREMENT EMIS",
            "PRELEVEMENT",
            "VIREMENT EN VOTRE FAVEUR",
            "PAIEMENT PAR CARTE",
        ]

        for r in REMOVE:
            l = l.replace(r, "").strip()

        # if there's something after \n\n\n, it's the reference and we don't want it
        if "\n\n\n" in l:
            l = l.split("\n\n\n")[0]

        # There may be a date too, in the xx/xx format at the end. Remove it
        regex = r"\d{2}/\d{2}$"
        l = sub(regex, "", l).strip()

        # Remove card number
        regex = r"^X\d{4}"
        l = sub(regex, "", l).strip()

        return l

    def get_amount(row):
        # ca uses "Débit euros" and "Crédit euros" instead of a single column

        d: float = row["Débit euros"]
        c: float = row["Crédit euros"]

        if d and not isnan(d):
            return -d
        elif c and not isnan(c):
            return c
        else:
            raise ValueError(f"Invalid row: {row}")

    jobj = pd.DataFrame()
    # float
    jobj["amount"] = csv.apply(get_amount, axis=1)
    jobj["notes"] = csv["Libellé"]
    jobj["payee"] = csv["Libellé"].apply(fixlbl)
    jobj["date"] = csv["Date"].apply(fixdate)

    return jobj


def main():

    parser.add_argument("csv_file", help="CSV file to import")
    parser.add_argument("--cutoff",
                        help="Cutoff date (inclusive) in YYYY-MM-DD format")
    args = parse_args()

    csv = read_csv(args.csv_file, args.cutoff)
    out = convert(csv)

    print(len(out), "operations")
    
    out.to_csv('ca_to_actual.csv')


if __name__ == "__main__":
    main()
