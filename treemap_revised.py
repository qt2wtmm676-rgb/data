import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

# -----------------------------
# Paths
# -----------------------------
DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATA_FILE = DATA_DIR / "NHS_2023_24_FINAL_COMPLETE.csv"

# -----------------------------
# Load and clean data
# -----------------------------
df = pd.read_csv(DATA_FILE)

required_cols = [
    "FAE_Total",
    "Emergency_Admissions",
    "Chapter_Letter",
    "Diagnosis_Code",
    "Diagnosis_Desc",
]
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

df_clean = df.copy()

# Keep valid records only.
df_clean = df_clean[df_clean["FAE_Total"].notna()]
df_clean = df_clean[df_clean["FAE_Total"] > 0]
df_clean = df_clean[df_clean["Chapter_Letter"].notna()]
df_clean = df_clean[~df_clean["Chapter_Letter"].isin(["*", "§", "‡"])]

# Recalculate emergency rate to make the method explicit and reproducible.
# Emergency Rate = Emergency Admissions / Finished Admission Episodes * 100
df_clean["Emergency_Rate_Pct"] = (
    df_clean["Emergency_Admissions"] / df_clean["FAE_Total"] * 100
)
df_clean["Emergency_Rate_Pct"] = df_clean["Emergency_Rate_Pct"].clip(0, 100)

# -----------------------------
# ICD-10 chapter names
# -----------------------------
ICD10_NAMES = {
    "A": "Infectious diseases",
    "B": "Viral infections",
    "C": "Neoplasms",
    "D": "Blood disorders",
    "E": "Endocrine/metabolic",
    "F": "Mental disorders",
    "G": "Nervous system",
    "H": "Eye/ear diseases",
    "I": "Circulatory",
    "J": "Respiratory",
    "K": "Digestive",
    "L": "Skin",
    "M": "Musculoskeletal",
    "N": "Genitourinary",
    "O": "Pregnancy/birth",
    "P": "Perinatal",
    "Q": "Congenital",
    "R": "Symptoms & Signs",
    "S": "Injuries (S)",
    "T": "Injuries (T)",
    "U": "Other causes (U)",
    "Z": "Other causes (Z)",
}

df_clean["Chapter_Name"] = df_clean["Chapter_Letter"].map(ICD10_NAMES)
df_clean = df_clean.dropna(subset=["Chapter_Name"])

# -----------------------------
# Optional: mark the two chapters used in the unique observation.
# This makes the key finding visible in the static PDF image.
# -----------------------------
KEY_CHAPTER_LABELS = {
    "R": "★ R: Symptoms & Signs — high volume + high emergency",
    "H": "★ H: Eye/ear diseases — high volume + low emergency",
}

df_clean["Chapter_Display"] = np.where(
    df_clean["Chapter_Letter"].isin(KEY_CHAPTER_LABELS),
    df_clean["Chapter_Letter"].map(KEY_CHAPTER_LABELS),
    df_clean["Chapter_Name"],
)

# -----------------------------
# Labels
# -----------------------------
def short_desc(text: str, n: int = 28) -> str:
    """Shorten long medical descriptions for static treemap labels."""
    text = str(text).replace("\n", " ").strip()
    return text if len(text) <= n else text[: n - 1] + "…"


# Treemaps become unreadable if every small box has a full label.
# Show detailed labels only for large boxes or the two key observation chapters.
large_box_threshold = df_clean["FAE_Total"].quantile(0.65)

def make_label(row):
    code = str(row["Diagnosis_Code"])
    desc = short_desc(row["Diagnosis_Desc"], 30)
    vol_k = row["FAE_Total"] / 1000
    pct = row["Emergency_Rate_Pct"]

    is_key_chapter = row["Chapter_Letter"] in ["R", "H"]
    is_large_box = row["FAE_Total"] >= large_box_threshold

    if is_key_chapter or is_large_box:
        return (
            f"<b>{code}</b> {desc}<br>"
            f"{vol_k:.0f}K admissions<br>"
            f"<b>Emergency admission rate: {pct:.0f}%</b>"
        )

    # Smaller rectangles still carry code and emergency rate, but avoid visual clutter.
    return f"<b>{code}</b><br>{pct:.0f}%"

df_clean["Sub_Label"] = df_clean.apply(make_label, axis=1)

# -----------------------------
# Build hierarchy
# -----------------------------
hier_df = df_clean[
    [
        "Chapter_Display",
        "Sub_Label",
        "Diagnosis_Code",
        "Diagnosis_Desc",
        "FAE_Total",
        "Emergency_Admissions",
        "Emergency_Rate_Pct",
        "Chapter_Letter",
    ]
].copy()

hier_df.columns = [
    "Chapter",
    "SubCategory",
    "Diagnosis_Code",
    "Diagnosis_Desc",
    "Admissions",
    "Emergency_Admissions",
    "Emergency_Rate",
    "Chapter_Letter",
]

total_adm = hier_df["Admissions"].sum()
print(f"Data: {len(hier_df)} sub-categories across {hier_df['Chapter'].nunique()} chapters")
print(f"Total admissions: {total_adm / 1e6:.2f}M")

# Print the two key chapters for checking the written observation.
chapter_stats = (
    hier_df.groupby("Chapter_Letter")
    .agg(
        Admissions=("Admissions", "sum"),
        Emergency_Admissions=("Emergency_Admissions", "sum"),
    )
    .reset_index()
)
chapter_stats["Emergency_Rate"] = (
    chapter_stats["Emergency_Admissions"] / chapter_stats["Admissions"] * 100
)

for chapter in ["R", "H"]:
    row = chapter_stats.loc[chapter_stats["Chapter_Letter"] == chapter]
    if not row.empty:
        row = row.iloc[0]
        print(
            f"Chapter {chapter}: "
            f"{row['Admissions'] / 1e6:.2f}M admissions, "
            f"{row['Emergency_Rate']:.1f}% emergency"
        )

# -----------------------------
# Colour scale
# Green = low emergency rate, red = high emergency rate.
# -----------------------------
SOFT_COLORS = [
    (0.00, "#a8e6cf"),
    (0.12, "#88d8b0"),
    (0.25, "#c5e99b"),
    (0.38, "#fef3bd"),
    (0.50, "#f9d56e"),
    (0.62, "#f4a261"),
    (0.75, "#e07a5f"),
    (0.87, "#c95d63"),
    (1.00, "#a13d47"),
]

# -----------------------------
# Treemap
# -----------------------------
fig = px.treemap(
    data_frame=hier_df,
    path=["Chapter", "SubCategory"],
    values="Admissions",
    color="Emergency_Rate",
    color_continuous_scale=SOFT_COLORS,
    range_color=[0, 100],
    custom_data=[
        "Diagnosis_Code",
        "Diagnosis_Desc",
        "Admissions",
        "Emergency_Admissions",
        "Emergency_Rate",
    ],
    width=1900,
    height=1150,
)

fig.update_traces(
    root_color="#f4f4f5",
    marker=dict(line=dict(color="#ffffff", width=2)),
    textfont=dict(size=15, family="Helvetica Neue, Arial"),
    tiling=dict(pad=3),
    hovertemplate=(
        "<b>%{customdata[0]}</b> %{customdata[1]}<br>"
        "Admissions: %{customdata[2]:,.0f}<br>"
        "Emergency admissions: %{customdata[3]:,.0f}<br>"
        "Emergency admission rate: <b>%{customdata[4]:.1f}%</b>"
        "<extra></extra>"
    ),
)

# -----------------------------
# Layout and static callouts
# -----------------------------
fig.update_layout(
    title=dict(
        text=(
            "<b>Disease Burden vs Urgency: NHS Admissions by Category</b><br>"
            "<sup style='font-size:13px; color:#4b5563'>"
            "Box size = Finished Admission Episodes | "
            "Colour = Emergency admission rate (%) | "
            "Focus cohort = all ages and genders, FY 2023–24"
            "</sup>"
        ),
        x=0.02,
        xanchor="left",
        font=dict(size=24, family="Helvetica Neue, Arial", color="#111827"),
    ),
    font=dict(family="Helvetica Neue, Arial", size=15, color="#111827"),
    margin=dict(t=150, l=16, r=120, b=28),
    paper_bgcolor="#fafafa",
    plot_bgcolor="#fafafa",
    coloraxis_colorbar=dict(
        title=dict(
            text="<b>Emergency admission<br>rate (%)</b>",
            font=dict(size=14, color="#374151"),
        ),
        thickness=22,
        len=0.80,
        x=1.02,
        tickfont=dict(size=12, color="#4b5563"),
        tickvals=[0, 20, 40, 60, 80, 100],
        ticktext=["0", "20", "40", "60", "80", "100"],
        bgcolor="#f3f4f6",
        bordercolor="#d1d5db",
        outlinewidth=1,
    ),
)

# These callouts are deliberately placed above the treemap so the key observation
# remains visible in the submitted static PDF image.
fig.add_annotation(
    xref="paper",
    yref="paper",
    x=0.02,
    y=1.045,
    xanchor="left",
    yanchor="top",
    showarrow=False,
    align="left",
    bordercolor="#c95d63",
    borderwidth=2,
    borderpad=6,
    bgcolor="rgba(255,255,255,0.92)",
    font=dict(size=14, color="#111827"),
    text=(
        "<b>Key observation 1</b><br>"
        "Symptoms & Signs combines high admission volume with high emergency dependence."
    ),
)

fig.add_annotation(
    xref="paper",
    yref="paper",
    x=0.42,
    y=1.045,
    xanchor="left",
    yanchor="top",
    showarrow=False,
    align="left",
    bordercolor="#88d8b0",
    borderwidth=2,
    borderpad=6,
    bgcolor="rgba(255,255,255,0.92)",
    font=dict(size=14, color="#111827"),
    text=(
        "<b>Key observation 2</b><br>"
        "Eye/ear diseases has high admission volume but a predominantly elective profile."
    ),
)

fig.add_annotation(
    xref="paper",
    yref="paper",
    x=0.02,
    y=-0.035,
    xanchor="left",
    yanchor="bottom",
    showarrow=False,
    align="left",
    font=dict(size=12, color="#6b7280"),
    text=(
        "Emergency admission rate = Emergency Admissions / Finished Admission Episodes × 100. "
        "Small rectangles use compact labels to reduce clutter."
    ),
)

# -----------------------------
# Export
# -----------------------------
png_path = OUTPUT_DIR / "CW2_Treemap_Disease_Burden_vs_Urgency.png"
pdf_path = OUTPUT_DIR / "CW2_Treemap_Disease_Burden_vs_Urgency.pdf"
html_path = OUTPUT_DIR / "CW2_Treemap_Disease_Burden_vs_Urgency.html"

fig.write_image(str(png_path), scale=4)
fig.write_image(str(pdf_path))
fig.write_html(str(html_path), include_plotlyjs="cdn")

print(f"Saved PNG:  {png_path}")
print(f"Saved PDF:  {pdf_path}")
print(f"Saved HTML: {html_path}")
