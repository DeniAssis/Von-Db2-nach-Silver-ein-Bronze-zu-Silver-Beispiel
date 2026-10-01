# Fabric Notebook (PySpark): simulierte Db2-Tabelle VERTRAG im Bronze-Schema anlegen
#
# Alle Daten sind erfunden. Die Tabelle sieht so aus, wie sie nach dem Kopieren
# aus Db2 per Data Factory aussehen koennte: alle Spalten als Text, CHAR-Felder
# mit Leerzeichen aufgefuellt, Platzhalterdaten, Duplikate und fehlerhafte Saetze.

# %% Zelle 1: Schema und Struktur
from pyspark.sql.types import StructType, StructField, StringType

spark.sql("CREATE SCHEMA IF NOT EXISTS bronze")

schema = StructType([
    StructField("VERTRAG_NR",  StringType()),   # Db2 CHAR(10), aufgefuellt
    StructField("KUNDEN_NR",   StringType()),   # Db2 CHAR(6), aufgefuellt
    StructField("PRODUKT_CD",  StringType()),   # Schreibweise uneinheitlich
    StructField("BEITRAG",     StringType()),   # Db2 DECIMAL, als Text uebernommen
    StructField("VERS_BEGINN", StringType()),
    StructField("VERS_ENDE",   StringType()),   # 9999-12-31 = unbefristet
    StructField("STATUS_CD",   StringType()),
    StructField("load_date",   StringType()),   # beim Kopieren hinzugefuegt
])


# %% Zelle 2: Beispieldaten
zeilen = [
    # Normale Saetze
    ("V0000001  ", "K001  ", "kfz  ",  "45.90",  "2020-01-01", "9999-12-31", "A", "2026-09-01"),
    ("V0000002  ", "K002  ", "HAUS ",  "12.50",  "2019-05-15", "9999-12-31", "A", "2026-09-01"),
    ("V0000003  ", "K003  ", "LEBEN",  "120.00", "2015-03-01", "2025-03-01", "K", "2026-09-01"),
    ("V0000004  ", "K001  ", "haus ",  "18.00",  "2021-07-01", "9999-12-31", "R", "2026-09-01"),

    # Duplikat: aelterer Ladestand von V0000001 (Silver soll nur den neueren behalten)
    ("V0000001  ", "K001  ", "kfz  ",  "39.90",  "2020-01-01", "9999-12-31", "A", "2026-08-01"),

    # Platzhalterdatum 0001-01-01 und unbekannter Statuscode X (bleibt gueltig)
    ("V0000007  ", "K007  ", "LEBEN",  "80.00",  "2022-02-01", "0001-01-01", "X", "2026-09-01"),

    # Fehlerhafte Saetze (sollen in silver.vertrag_fehler landen)
    ("V0000005  ", "K004  ", "KFZ  ",  "-30.00", "2023-04-01", "9999-12-31", "A", "2026-09-01"),  # negativer Beitrag
    ("          ", "K005  ", "KFZ  ",  "50.00",  "2023-06-01", "9999-12-31", "A", "2026-09-01"),  # keine Vertragsnummer
    ("V0000006  ", "K006  ", "HAUS ",  "22.00",  "2024-01-01", "2023-01-01", "A", "2026-09-01"),  # Ende vor Beginn
    ("V0000008  ", "K008  ", "KFZ  ",  "abc",    "2024-02-01", "9999-12-31", "A", "2026-09-01"),  # Beitrag kein Zahlenwert
]

df = spark.createDataFrame(zeilen, schema)


# %% Zelle 3: Als Bronze-Tabelle speichern und kontrollieren
(df.write
   .mode("overwrite")
   .format("delta")
   .saveAsTable("bronze.db2_vertrag"))

print("Bronze-Zeilen:", spark.read.table("bronze.db2_vertrag").count())

# Erwartetes Ergebnis nach dem Bronze-nach-Silver-Notebook:
#   silver.vertrag         -> 5 gueltige Vertraege (V0000001 mit Beitrag 45.90, V0000002, 3, 4, 7)
#   silver.vertrag_fehler  -> 4 fehlerhafte Saetze (V0000005, leere Nummer, V0000006, V0000008)
