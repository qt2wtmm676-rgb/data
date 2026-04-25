import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")

df = pd.read_csv(DATA_DIR / "NHS_2023_24_FINAL_COMPLETE.csv")
df_clean = df[df['FAE_Total'] > 0].copy()
df_clean = df_clean[df_clean['Chapter_Letter'].notna()]
df_clean = df_clean[~df_clean['Chapter_Letter'].isin(['*', '§', '‡'])]

ICD10_NAMES = {
    'A': 'Infectious diseases', 'B': 'Viral infections',
    'C': 'Neoplasms', 'D': 'Blood disorders',
    'E': 'Endocrine/metabolic', 'F': 'Mental disorders',
    'G': 'Nervous system', 'H': 'Eye/ear diseases',
    'I': 'Circulatory', 'J': 'Respiratory',
    'K': 'Digestive', 'L': 'Skin', 'M': 'Musculoskeletal',
    'N': 'Genitourinary', 'O': 'Pregnancy/birth', 'P': 'Perinatal',
    'Q': 'Congenital', 'R': 'Symptoms & Signs',
    'S': 'Injuries (S)', 'T': 'Injuries (T)',
    'U': 'Other causes (U)', 'Z': 'Other causes (Z)'
}

SOFT_COLORS = [
    (0.0, '#a8e6cf'),
    (0.12, '#88d8b0'),
    (0.25, '#c5e99b'),
    (0.38, '#fef3bd'),
    (0.50, '#f9d56e'),
    (0.62, '#f4a261'),
    (0.75, '#e07a5f'),
    (0.87, '#c95d63'),
    (1.0, '#a13d47')
]

df_clean['Chapter_Name'] = df_clean['Chapter_Letter'].map(ICD10_NAMES)
df_clean = df_clean.dropna(subset=['Chapter_Name'])

def make_label(row):
    code = row['Diagnosis_Code']
    desc = row['Diagnosis_Desc'][:22]
    vol = row['FAE_Total'] / 1000
    pct = row['Emergency_Rate_Pct']
    return (f"<b>{code}</b> {desc}<br>"
            f"{vol:.0f}K adms<br>"
            f'<span style="font-size:18px; color:rgba(255,255,255,0.92);'
            f'text-shadow:0px 0px 4px rgba(0,0,0,0.5);">'
            f'<b>{pct:.0f}%</b></span>')

df_clean['Sub_Label'] = df_clean.apply(make_label, axis=1)

hier_df = df_clean[['Chapter_Name', 'Sub_Label', 'FAE_Total', 'Emergency_Rate_Pct']].copy()
hier_df.columns = ['Chapter', 'SubCategory', 'Admissions', 'Emergency_Rate']

print(f"\nData: {len(hier_df)} sub-categories across {hier_df['Chapter'].nunique()} chapters")
total_adm = hier_df['Admissions'].sum()
print(f"Total admissions: {total_adm/1e6:.2f}M")

fig = px.treemap(
    data_frame=hier_df,
    path=['Chapter', 'SubCategory'],
    values='Admissions',
    color='Emergency_Rate',
    color_continuous_scale=SOFT_COLORS,
    range_color=[0, 100],
    width=1800,
    height=1100,
)

fig.update_layout(
    title=dict(
        text='<b>Disease Burden vs Urgency: NHS Admissions by Category</b><br>' +
            '<sup style="font-size:12px; color:#666">Box Size = Number of Admissions | Color = Emergency Admission Rate (%) | FY 2023-24</sup>',
        x=0.02,
        xanchor='left',
        font=dict(size=21, family='Helvetica Neue, Arial', color='#1a202c')
    ),
    font=dict(family='Helvetica Neue, Arial', size=14),
    margin=dict(t=90, l=12, r=12, b=12),
    paper_bgcolor='#fafafa',
    coloraxis_colorbar=dict(
        title=dict(text='<b>Emergency<br>Rate (%)</b>', font=dict(size=13, color='#374151')),
        thickness=20,
        len=0.86,
        x=1.01,
        tickfont=dict(size=11, color='#4b5563'),
        tickformat='.0f',
        bgcolor='#f3f4f6',
        bordercolor='#d1d5db',
        outlinewidth=1
    )
)

fig.update_traces(
    textfont=dict(size=14, family='Helvetica Neue, Arial'),
    hovertemplate='<b>%{label}</b><br>Admissions: %{value:,.0f}<br>Emergency Rate: <b>%{color:.1f}%</b><extra></extra>',
    marker=dict(line=dict(color='#ffffff', width=2))
)

output_path = OUTPUT_DIR / "CPRO_FINAL_Treemap_Hierarchical.png"
fig.write_image(str(output_path), scale=3)
fig.write_html(str(OUTPUT_DIR / "CPRO_FINAL_Treemap_Hierarchical.html"))

print(f"\nSaved: {output_path.name}")
