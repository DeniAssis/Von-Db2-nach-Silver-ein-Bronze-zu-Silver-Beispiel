A small, self-contained example that shows how typical problems in mainframe data (Db2 / VSAM) are cleaned up when the data moves into a lakehouse, using the medallion pattern (Bronze, Silver, Gold).

All data is **simulated**. It contains no real tables, customers or company data.

## What this project shows

- How a Db2 table looks after it was copied 1:1 into a Bronze layer (all columns as text)
- How to clean and type that data for a Silver layer
- How to handle common Db2 quirks:
  - `CHAR` columns padded with trailing spaces
  - Placeholder dates such as `9999-12-31` and `0001-01-01` that mean "no date"
  - Inconsistent spelling of codes (`kfz` vs. `KFZ`)
  - Duplicate records from several loads (keep the latest)
  - Unknown status codes
- How to separate invalid records into an error table instead of silently loading them

## Files

| File | Purpose |
|---|---|
| `db2_bronze_nach_silver_pandas.py` | Runs anywhere with Python and pandas (tested in DataCamp DataLab). Simulates the Bronze table and builds Silver. |
| `bronze_db2_vertrag_beispieldaten.py` | PySpark notebook for Microsoft Fabric: creates the simulated Bronze table `bronze.db2_vertrag`. |
| `bronze_nach_silver_db2_vertrag.py` | PySpark notebook for Microsoft Fabric: transforms Bronze into `silver.vertrag` and `silver.vertrag_fehler`. |

## The scenario

A simplified insurance contract table `VERTRAG` with these columns:

`VERTRAG_NR`, `KUNDEN_NR`, `PRODUKT_CD`, `BEITRAG`, `VERS_BEGINN`, `VERS_ENDE`, `STATUS_CD`, plus a `load_date` that is added during the copy.

The sample has 10 rows: 5 valid contracts (one of them with an older duplicate), plus 4 invalid rows.

## Processing steps

1. **Clean and type:** trim padded text, uppercase product codes, convert amounts to numbers, convert date text to dates, turn placeholder dates into empty values, map status codes to readable text.
2. **Remove duplicates:** keep only the most recently loaded record per contract number.
3. **Validate:** a record is invalid if the contract number is empty, the amount is missing or negative, the start date is missing, or the end date is before the start date.
4. **Write the result:** valid records go to `silver_vertrag`, invalid ones to `silver_fehler`.

## How to run

### Option A: Python and pandas (DataLab, Colab or local)

1. Open a **Python** cell (not a SQL cell) in DataLab, a Colab notebook, or run the script locally.
2. Copy the contents of `db2_bronze_nach_silver_pandas.py` into it and run it.
3. Requires: Python 3 and `pandas`.

### Option B: Microsoft Fabric (PySpark)

1. Attach a notebook to a Lakehouse with schemas enabled.
2. Run `bronze_db2_vertrag_beispieldaten.py` to create `bronze.db2_vertrag`.
3. Run `bronze_nach_silver_db2_vertrag.py` to create `silver.vertrag` and `silver.vertrag_fehler`.

The cells in each script are separated by `# %%` lines. Paste each block into its own notebook cell.

## Expected result

- Bronze: 10 rows
- `silver_vertrag`: 5 valid contracts (contract `V0000001` with amount 45.90, the newer load)
- `silver_fehler`: 4 invalid records (negative amount, empty contract number, end date before start date, non-numeric amount)

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

## Limitations

- The pandas version was run and checked in DataCamp DataLab. The **Fabric (PySpark) version has not been run in a Fabric environment** and may need small adjustments, for example to table or schema names.
- The Silver step overwrites the target tables. Real projects usually load incrementally, for example with `MERGE`.
- Status codes and column names are examples and have to be adapted to real data.
- Real mainframe exports (VSAM, EBCDIC, packed decimals / COMP-3) need an additional conversion step that is not part of this example.
- The Gold layer (star schema for Power BI) is not included.

## Note on AI assistance

I created this example with the help of an AI assistant (Claude). I reviewed the code, ran the pandas version, and adapted it to typical mainframe data problems.

