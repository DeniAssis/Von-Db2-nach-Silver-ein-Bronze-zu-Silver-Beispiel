# DataLab / Colab / lokal (Python + pandas): simulierte Db2-Tabelle VERTRAG, Bronze -> Silver
#
# Alle Daten sind erfunden. Kein Spark und kein Lakehouse noetig.
# Jede Zelle ("# %%") kommt in eine eigene Python-Zelle (nicht in eine SQL-Zelle).

# %% Zelle 1: Simulierte Bronze-Tabelle (so wie nach einem Db2-Export, alles als Text)
import pandas as pd

spalten = ["VERTRAG_NR", "KUNDEN_NR", "PRODUKT_CD", "BEITRAG",
           "VERS_BEGINN", "VERS_ENDE", "STATUS_CD", "load_date"]

zeilen = [
    # Normale Saetze
    ("V0000001  ", "K001  ", "kfz  ",  "45.90",  "2020-01-01", "9999-12-31", "A", "2026-09-01"),
    ("V0000002  ", "K002  ", "HAUS ",  "12.50",  "2019-05-15", "9999-12-31", "A", "2026-09-01"),
    ("V0000003  ", "K003  ", "LEBEN",  "120.00", "2015-03-01", "2025-03-01", "K", "2026-09-01"),
    ("V0000004  ", "K001  ", "haus ",  "18.00",  "2021-07-01", "9999-12-31", "R", "2026-09-01"),
    # Duplikat: aelterer Ladestand von V0000001
    ("V0000001  ", "K001  ", "kfz  ",  "39.90",  "2020-01-01", "9999-12-31", "A", "2026-08-01"),
    # Platzhalterdatum 0001-01-01 und unbekannter Statuscode X
    ("V0000007  ", "K007  ", "LEBEN",  "80.00",  "2022-02-01", "0001-01-01", "X", "2026-09-01"),
    # Fehlerhafte Saetze
    ("V0000005  ", "K004  ", "KFZ  ",  "-30.00", "2023-04-01", "9999-12-31", "A", "2026-09-01"),  # negativer Beitrag
    ("          ", "K005  ", "KFZ  ",  "50.00",  "2023-06-01", "9999-12-31", "A", "2026-09-01"),  # keine Vertragsnummer
    ("V0000006  ", "K006  ", "HAUS ",  "22.00",  "2024-01-01", "2023-01-01", "A", "2026-09-01"),  # Ende vor Beginn
    ("V0000008  ", "K008  ", "KFZ  ",  "abc",    "2024-02-01", "9999-12-31", "A", "2026-09-01"),  # Beitrag kein Zahlenwert
]

bronze = pd.DataFrame(zeilen, columns=spalten)
print("Bronze-Zeilen:", len(bronze))
bronze


# %% Zelle 2: Bereinigen und typisieren
# Db2-CHAR-Felder sind mit Leerzeichen aufgefuellt -> strip
# Platzhalterdaten wie 9999-12-31 oder 0001-01-01 bedeuten "kein Datum" -> leer
PLATZHALTER_DATEN = ["9999-12-31", "0001-01-01", ""]

def sauberes_datum(spalte):
    text = spalte.str.strip()
    text = text.mask(text.isin(PLATZHALTER_DATEN))
    return pd.to_datetime(text, format="%Y-%m-%d", errors="coerce")

STATUS = {"A": "aktiv", "K": "gekuendigt", "R": "ruhend"}   # Beispielwerte

silver = pd.DataFrame({
    "vertrag_nr":  bronze["VERTRAG_NR"].str.strip(),
    "kunden_nr":   bronze["KUNDEN_NR"].str.strip(),
    "produkt_cd":  bronze["PRODUKT_CD"].str.strip().str.upper(),
    "beitrag":     pd.to_numeric(bronze["BEITRAG"].str.strip(), errors="coerce"),
    "vers_beginn": sauberes_datum(bronze["VERS_BEGINN"]),
    "vers_ende":   sauberes_datum(bronze["VERS_ENDE"]),
    "status":      bronze["STATUS_CD"].str.strip().map(STATUS).fillna("unbekannt"),
    "load_date":   bronze["load_date"],
})


# %% Zelle 3: Duplikate entfernen (jeweils der zuletzt geladene Satz pro Vertrag)
silver = (
    silver
    .sort_values("load_date", ascending=False)
    .drop_duplicates(subset="vertrag_nr", keep="first")
    .sort_values("vertrag_nr")
    .reset_index(drop=True)
)


# %% Zelle 4: Qualitaetspruefung - fehlerhafte Saetze getrennt ablegen
ist_gueltig = (
    (silver["vertrag_nr"] != "")
    & silver["beitrag"].notna() & (silver["beitrag"] >= 0)
    & silver["vers_beginn"].notna()
    & (silver["vers_ende"].isna() | (silver["vers_ende"] >= silver["vers_beginn"]))
)

silver_vertrag = silver[ist_gueltig].reset_index(drop=True)
silver_fehler = silver[~ist_gueltig].reset_index(drop=True)

print("Gueltig:", len(silver_vertrag), "| Fehlerhaft:", len(silver_fehler))


# %% Zelle 5: Ergebnisse ansehen
silver_vertrag


# %% Zelle 6: Fehlerhafte Saetze ansehen
silver_fehler

# Erwartet: 5 gueltige Vertraege (V0000001 mit Beitrag 45.90, V0000002, 3, 4, 7)
#           4 fehlerhafte Saetze (V0000005, leere Nummer, V0000006, V0000008)
