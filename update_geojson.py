# -*- coding: utf-8 -*-
import io, re, json
import pandas as pd
from pyproj import Transformer

# URL del CSV público
URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQJDO21sdc_3iUUYAPVbaizykV74VclgLlepgFFUW3q6OC2GiNMmnJ1eLoskiTlbO_1cJlU4ShW74MD/pub?gid=1021691292&single=true&output=csv"

# Candidatos de nombres para X (Este) y Y (Norte) en CRTM05
X_CANDS = ["x","este","easting","coordx","coordenadax","crtm05x","xcrtm05"]
Y_CANDS = ["y","norte","northing","coordy","coordenaday","crtm05y","ycrtm05"]

OUT = "docs/dictamenes.geojson"
SOURCE_EPSG = 5367  # CRTM05 (CR05). Usa 8908 si tu hoja está en CR-SIRGAS/CRTM05.

def norm(s): return re.sub(r'\W+','', str(s).lower())

def find_col(df, cands):
    for cand in cands:
        for c in df.columns:
            if norm(c) == norm(cand):
                return c
    # fallback por prefijo
    for c in df.columns:
        if any(norm(c).startswith(pref) for pref in [cands[0], cands[1]]):
            return c
    return None

def to_num(s):
    return pd.to_numeric(
        s.astype(str)
         .str.replace(r'[\u00A0\s]', '', regex=True)
         .str.replace(',', '.', regex=False)
         .str.replace(r'[^0-9.\-]', '', regex=True),
        errors="coerce"
    )

def main():
    df = pd.read_csv(URL)
    x_col = find_col(df, X_CANDS)
    y_col = find_col(df, Y_CANDS)
    if not x_col or not y_col:
        raise RuntimeError(f"No encuentro columnas X/Y CRTM05. Columnas: {list(df.columns)}")

    df[x_col] = to_num(df[x_col])
    df[y_col] = to_num(df[y_col])
    before = len(df)
    df = df.dropna(subset=[x_col, y_col])
    dropped = before - len(df)
    if df.empty:
        raise RuntimeError("No hay filas válidas con coordenadas.")

    # reproyección CRTM05 -> WGS84
    transformer = Transformer.from_crs(f"EPSG:{SOURCE_EPSG}", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(df[x_col].values, df[y_col].values)
    df["_lon"] = lon
    df["_lat"] = lat

    features = []
    for _, row in df.iterrows():
        props = {k: (None if pd.isna(v) else v) for k,v in row.items() if k not in ["_lon","_lat"]}
        features.append({
            "type":"Feature",
            "geometry":{"type":"Point","coordinates":[row["_lon"], row["_lat"]]},
            "properties": props
        })
    fc = {"type":"FeatureCollection","features":features}
    with open(OUT,"w",encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"OK: {len(features)} features. Descartadas: {dropped}. Escrito → {OUT}")

if __name__ == "__main__":
    main()

