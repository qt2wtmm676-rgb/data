"""Extract NHS_2023_24_FINAL_COMPLETE.csv from the official xlsx workbook."""
import pandas as pd
from pathlib import Path
import re

XLSX = Path("hosp-epis-stat-admi-diag-2023-24-tab.xlsx")
OUT_DIR = Path("data")
OUT_DIR.mkdir(exist_ok=True)
OUT = OUT_DIR / "NHS_2023_24_FINAL_COMPLETE.csv"

# Sheet uses primary diagnosis 3-character codes. The code+description
# live in columns 0 and 1; FAE_Total is column 8; Emergency_Admissions is column 12.
raw = pd.read_excel(XLSX, sheet_name="Primary Diagnosis 3 Character", header=None)

CODE_COL, DESC_COL, FAE_COL, EMG_COL = 0, 1, 8, 12

records = []
code_pattern = re.compile(r"^[A-Z]\d{2}$")
for _, row in raw.iterrows():
    code = row[CODE_COL]
    if not isinstance(code, str):
        continue
    code = code.strip()
    if not code_pattern.match(code):
        continue
    desc = row[DESC_COL]
    fae = row[FAE_COL]
    emg = row[EMG_COL]
    records.append({
        "Diagnosis_Code": code,
        "Diagnosis_Desc": str(desc).strip() if isinstance(desc, str) else desc,
        "Chapter_Letter": code[0],
        "FAE_Total": pd.to_numeric(fae, errors="coerce"),
        "Emergency_Admissions": pd.to_numeric(emg, errors="coerce"),
    })

df = pd.DataFrame(records)
df.to_csv(OUT, index=False)
print(f"Wrote {len(df)} rows to {OUT}")
print(df.head())
