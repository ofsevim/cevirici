from flask import Flask, render_template_string
import pandas as pd

app = Flask(__name__)

EXCEL_PATH = "BMS SEND?KA KADROLU a?ustos 2025.xlsx"

@app.route("/")
def index():
    # Excel oku
    df = pd.read_excel(EXCEL_PATH)

    # Kolon e?le?tirme (farkl? yaz?mlara toleransl?)
    column_map = {}

    for col in df.columns:
        key = col.lower().strip()

        if "uye" in key and "no" in key:
            column_map[col] = "Uye No"
        elif "ad" in key or "soyad" in key:
            column_map[col] = "Ad Soyad"
        elif "tc" in key:
            column_map[col] = "TC"
        elif "aidat" in key:
            column_map[col] = "Aidat"

    # Yaln?zca gerekli kolonlar
    df = df[list(column_map.keys())]
    df = df.rename(columns=column_map)

    # S?ra no ekle
    df.insert(0, "S?ra No", range(1, len(df) + 1))

    html = """
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Aidat Listesi</title>
        <style>
            body { font-family: Arial; padding: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: center; }
            th { background: #f4f4f4; }
        </style>
    </head>
    <body>
        <h2>Aidat Listesi</h2>
        {{ table | safe }}
    </body>
    </html>
    """

    return render_template_string(html, table=df.to_html(index=False))

if __name__ == "__main__":
    app.run(debug=True)
