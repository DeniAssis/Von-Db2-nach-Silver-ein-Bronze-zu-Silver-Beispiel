# Von-Db2-nach-Silver-ein-Bronze-zu-Silver-Beispiel

Ein kleines, in sich geschlossenes Beispiel, das zeigt, wie typische Probleme in Mainframe-Daten (Db2 / VSAM) bereinigt werden, wenn die Daten in ein Lakehouse wandern. Es nutzt das Medaillon-Muster (Bronze, Silver, Gold).

Alle Daten sind **simuliert**. Es kommen keine echten Tabellen, Kunden- oder Firmendaten vor.

## Was das Projekt zeigt

- Wie eine Db2-Tabelle aussieht, nachdem sie 1:1 in eine Bronze-Schicht kopiert wurde (alle Spalten als Text)
- Wie man diese Daten für eine Silver-Schicht bereinigt und typisiert
- Wie man typische Db2-Eigenheiten behandelt:
  - `CHAR`-Felder, die mit Leerzeichen aufgefüllt sind
  - Platzhalterdaten wie `9999-12-31` und `0001-01-01`, die „kein Datum" bedeuten
  - Uneinheitliche Schreibweise von Codes (`kfz` und `KFZ`)
  - Duplikate aus mehreren Ladungen (der neueste Satz bleibt)
  - Unbekannte Statuscodes
- Wie man ungültige Sätze in eine Fehlertabelle auslagert, statt sie still zu laden

## Dateien

| Datei | Zweck |
|---|---|
| `db2_bronze_nach_silver_pandas.py` | Läuft überall mit Python und pandas (getestet in DataCamp DataLab). Simuliert die Bronze-Tabelle und erzeugt Silver. |
| `bronze_db2_vertrag_beispieldaten.py` | PySpark-Notebook für Microsoft Fabric: legt die simulierte Bronze-Tabelle `bronze.db2_vertrag` an. |
| `bronze_nach_silver_db2_vertrag.py` | PySpark-Notebook für Microsoft Fabric: wandelt Bronze in `silver.vertrag` und `silver.vertrag_fehler` um. |

## Das Szenario

Eine vereinfachte Versicherungs-Vertragstabelle `VERTRAG` mit diesen Spalten:

`VERTRAG_NR`, `KUNDEN_NR`, `PRODUKT_CD`, `BEITRAG`, `VERS_BEGINN`, `VERS_ENDE`, `STATUS_CD`, dazu `load_date`, das beim Kopieren ergänzt wird.

Das Beispiel hat 10 Zeilen: 5 gültige Verträge (einer davon mit einem älteren Duplikat) und 4 ungültige Sätze.

## Verarbeitungsschritte

1. **Bereinigen und typisieren:** Aufgefüllten Text kürzen, Produktcodes in Großbuchstaben setzen, Beträge in Zahlen umwandeln, Datumstexte in Datumswerte umwandeln, Platzhalterdaten zu leeren Werten machen, Statuscodes in lesbaren Text übersetzen.
2. **Duplikate entfernen:** Pro Vertragsnummer bleibt nur der zuletzt geladene Satz.
3. **Prüfen:** Ein Satz ist ungültig, wenn die Vertragsnummer leer ist, der Betrag fehlt oder negativ ist, das Beginndatum fehlt oder das Ende vor dem Beginn liegt.
4. **Ergebnis schreiben:** Gültige Sätze gehen nach `silver_vertrag`, ungültige nach `silver_fehler`.

## Ausführen

### Variante A: Python und pandas (DataLab, Colab oder lokal)

1. Öffne in DataLab eine **Python**-Zelle (keine SQL-Zelle), ein Colab-Notebook, oder führe das Skript lokal aus.
2. Kopiere den Inhalt von `db2_bronze_nach_silver_pandas.py` hinein und führe ihn aus.
3. Voraussetzung: Python 3 und `pandas`.

### Variante B: Microsoft Fabric (PySpark)

1. Verbinde ein Notebook mit einem Lakehouse, bei dem Schemas aktiviert sind.
2. Führe `bronze_db2_vertrag_beispieldaten.py` aus, um `bronze.db2_vertrag` anzulegen.
3. Führe `bronze_nach_silver_db2_vertrag.py` aus, um `silver.vertrag` und `silver.vertrag_fehler` zu erzeugen.

Die Zellen in jedem Skript sind durch `# %%`-Zeilen getrennt. Füge jeden Block in eine eigene Notebook-Zelle ein.

## Erwartetes Ergebnis

- Bronze: 10 Zeilen
- `silver_vertrag`: 5 gültige Verträge (Vertrag `V0000001` mit Beitrag 45,90, dem neueren Ladestand)
- `silver_fehler`: 4 ungültige Sätze (negativer Beitrag, leere Vertragsnummer, Ende vor Beginn, Beitrag kein Zahlenwert)

- ## Ergebnisse

Die Bronze-Schicht enthält 10 Zeilen. Davon sind 5 gültig und 4 fehlerhaft.

### Fehlerhafte Zeilen (aussortiert)

| vertrag_nr | kunden_nr | produkt_cd | beitrag | vers_beginn | vers_ende  | Problem                     |
|------------|-----------|------------|---------|-------------|------------|-----------------------------|
| *(leer)*   | K005      | KFZ        | 50      | 2023-06-01  |            | Vertragsnummer fehlt        |
| V0000005   | K004      | KFZ        | -30     | 2023-04-01  |            | Negativer Beitrag           |
| V0000006   | K006      | HAUS       | 22      | 2024-01-01  | 2023-01-01 | Ende liegt vor Beginn       |
| V0000008   | K008      | KFZ        | *(leer)*| 2024-02-01  |            | Beitrag fehlt               |

### Silver-Tabelle `silver_vertrag` (bereinigt)

| vertrag_nr | kunden_nr | produkt_cd | beitrag | vers_beginn | vers_ende  |
|------------|-----------|------------|---------|-------------|------------|
| V0000001   | K001      | KFZ        | 45.9    | 2020-01-01  |            |
| V0000002   | K002      | HAUS       | 12.5    | 2019-05-15  |            |
| V0000003   | K003      | LEBEN      | 120     | 2015-03-01  | 2025-03-01 |
| V0000004   | K001      | HAUS       | 18      | 2021-07-01  |            |
| V0000007   | K007      | LEBEN      | 80      | 2022-02-01  |            |

## Einschränkungen

- Die pandas-Version wurde in DataCamp DataLab ausgeführt und geprüft. Die **Fabric-Version (PySpark) wurde nicht in einer Fabric-Umgebung ausgeführt** und kann kleine Anpassungen brauchen, zum Beispiel bei Tabellen- oder Schemanamen.
- Der Silver-Schritt überschreibt die Zieltabellen. In echten Projekten lädt man meist inkrementell, etwa mit `MERGE`.
- Statuscodes und Spaltennamen sind Beispiele und müssen an echte Daten angepasst werden.
- Echte Mainframe-Exporte (VSAM, EBCDIC, gepackte Zahlen / COMP-3) brauchen einen zusätzlichen Umwandlungsschritt, der nicht Teil dieses Beispiels ist.
- Die Gold-Schicht (Sternschema für Power BI) ist nicht enthalten.

## Hinweis zur KI-Unterstützung

Ich habe dieses Beispiel mit Unterstützung eines KI-Assistenten (Claude) erstellt. Den Code habe ich geprüft, die pandas-Version ausgeführt und an typische Mainframe-Datenprobleme angepasst.
