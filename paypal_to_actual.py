import json
from math import isnan
import os

import pandas as pd
from datetime import datetime
from banks.client import parser, parse_args

parser.add_argument("tsv_file", help="TSV file to import")
parser.add_argument("--cutoff",
                    help="Cutoff date (inclusive) in YYYY-MM-DD format")
parser.add_argument("--remove_other_currencies", action="store_true", help="Remove rows with other currencies than EUR", default=True)
args = parse_args()

df = pd.read_csv(args.tsv_file, sep="\t", encoding="utf-8", decimal=",")

# remove all rows where "État" is not "Terminé" or "En attente"
# surprisingly, we have to take in account "En attente"
df = df[df["État"].isin(["Terminé", "En attente"])]

# remove all rows where "Impact sur le solde" is not "Crédit" or "Débit"
df = df[df["Impact sur le solde"].isin(["Crédit", "Débit"])]

# remove all rows where "Devise" is not "EUR"
if args.remove_other_currencies:
    print("Removing rows with other currencies than EUR")
    df = df[df["Devise"] == "EUR"]


def dmy_to_ymd(a):
    """
    dd/mm/yyyy to yyyy-mm-dd
    """
    d, m, y = tuple(map(int, a.split("/")))
    return f"{y:04d}-{m:02d}-{d:02d}"


df["Date"] = df["Date"].apply(dmy_to_ymd)

if args.cutoff:
    df = df[df["Date opération"] < args.cutoff]


def timezone_name_to_offset(tz: str):
    """
    Python strptime only supports UTC and GMT as timezone names.
    So we need to convert the timezone name to offset.
    """

    match tz:
        case "CEST":
            return "+0200"
        case "CET":
            return "+0100"
        case "UTC":
            return "+0000"
        case _:
            raise ValueError(f"Unknown timezone: {tz}")

def get_date(row):
    ymd = row["Date"]  # 2019-12-31
    hms = row["Heure"]  # 12:34:56
    tz = timezone_name_to_offset(row["Fuseau horaire"])  # CEST, CET, UTC, etc.

    dt = datetime.strptime(f"{ymd} {hms} {tz}", "%Y-%m-%d %H:%M:%S %z")
    return dt.isoformat()



def fix_amount(a):
    if type(a) == float and isnan(a):
        return 0
    return a


jobj = pd.DataFrame()
# Note: maybe use "Avant commission" instead?
jobj["amount"] = df["Net"].apply(fix_amount)
jobj["payee"] = df["Nom"]
jobj["note"] = df["Titre de l'objet"]

jobj["date"] = df.apply(get_date, axis=1)

print("Total amount:", sum(jobj["amount"]))

# write to csv
print("Sanitized version written to paypal_to_actual.csv")
jobj.to_csv("paypal_to_actual.csv")
