# Fabric Notebook (PySpark): Bronze -> Silver am Beispiel einer Db2-Tabelle VERTRAG
#
# Annahmen (frei erfundenes Beispiel, bitte an die echten Daten anpassen):
# - Data Factory hat Db2 "VERTRAG" 1:1 nach bronze.db2_vertrag kopiert
#   (alle Spalten als Text, plus Zusatzspalte load_date beim Laden)
# - Spalten: VERTRAG_NR, KUNDEN_NR, PRODUKT_CD, BEITRAG, VERS_BEGINN, VERS_ENDE, STATUS_CD, load_date
# - Das Lakehouse hat Schemas aktiviert (bronze, silver)

# %% Zelle 1: Setup
from itertools import chain
from pyspark.sql import functions as F
from pyspark.sql.window import Window

spark.sql("CREATE SCHEMA IF NOT EXISTS silver")

bronze = spark.read.table("bronze.db2_vertrag")
print("Bronze-Zeilen:", bronze.count())


# %% Zelle 2: Bereinigen und typisieren
# Db2-CHAR-Felder sind mit Leerzeichen aufgefuellt -> trim
# Db2-Platzhalterdaten wie 9999-12-31 oder 0001-01-01 bedeuten "kein Datum" -> NULL
PLATZHALTER_DATEN = ["9999-12-31", "0001-01-01", ""]

def sauberes_datum(spalte):
    text = F.trim(F.col(spalte))
    return F.when(text.isin(PLATZHALTER_DATEN), None).otherwise(F.to_date(text, "yyyy-MM-dd"))

# Schluessel-Codes in lesbare Werte uebersetzen (Beispielwerte)
STATUS = {"A": "aktiv", "K": "gekuendigt", "R": "ruhend"}
status_map = F.create_map([F.lit(x) for x in chain(*STATUS.items())])

silver = (
    bronze
    .withColumn("vertrag_nr", F.trim("VERTRAG_NR"))
    .withColumn("kunden_nr", F.trim("KUNDEN_NR"))
    .withColumn("produkt_cd", F.upper(F.trim("PRODUKT_CD")))
    .withColumn("beitrag", F.trim("BEITRAG").cast("decimal(11,2)"))
    .withColumn("vers_beginn", sauberes_datum("VERS_BEGINN"))
    .withColumn("vers_ende", sauberes_datum("VERS_ENDE"))
    .withColumn("status", F.coalesce(status_map[F.trim("STATUS_CD")], F.lit("unbekannt")))
    .select("vertrag_nr", "kunden_nr", "produkt_cd", "beitrag",
            "vers_beginn", "vers_ende", "status", "load_date")
)


# %% Zelle 3: Duplikate entfernen (jeweils der zuletzt geladene Satz pro Vertrag)
neueste_zuerst = Window.partitionBy("vertrag_nr").orderBy(F.col("load_date").desc())

silver = (
    silver
    .withColumn("rn", F.row_number().over(neueste_zuerst))
    .filter("rn = 1")
    .drop("rn")
)


# %% Zelle 4: Qualitaetspruefung - fehlerhafte Saetze getrennt ablegen
ist_gueltig = (
    (F.col("vertrag_nr") != "")
    & F.col("beitrag").isNotNull() & (F.col("beitrag") >= 0)
    & F.col("vers_beginn").isNotNull()
    & (F.col("vers_ende").isNull() | (F.col("vers_ende") >= F.col("vers_beginn")))
)

gueltig = silver.filter(ist_gueltig)
fehler = silver.filter(~ist_gueltig)

print("Gueltig:", gueltig.count(), "| Fehlerhaft:", fehler.count())


# %% Zelle 5: Als Delta-Tabellen in Silver schreiben
(gueltig.write
    .mode("overwrite")
    .format("delta")
    .saveAsTable("silver.vertrag"))

(fehler.write
    .mode("overwrite")
    .format("delta")
    .saveAsTable("silver.vertrag_fehler"))
