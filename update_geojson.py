# -*- coding: utf-8 -*-
import re, json
import pandas as pd
from pyproj import Transformer

URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQJDO21sdc_3iUUYAPVbaizykV74VclgLlepgFFUW3q6OC2GiNMmnJ1eLoskiTlbO_1cJlU4ShW74MD/pub?gid=1021691292&single=true&output=csv"
OUT = "docs/dictamenes.geojson"

# EPSG de entrada (CRTM05 – Lambert Norte CR)
SOURCE_EPSG = 5367

X_CANDS = ["x","este","easting","coordx","coordenadax","crtm05x","xcrtm05"]
Y_CANDS = ["y","norte","northing","coordy","coordenaday","crtm05y","ycrtm05"]

def norm(s): 
    return re.sub(r'\W+','', str(s).lower())

def find_col(df, cands, prefer_exact=None):
    if prefer_exact:
        for ex in prefer_exact:
            for c in df.columns:
                if c == ex or c.strip() == ex:
                    return c
    for cand in cands:
        for c in df.columns:
            if norm(c) == norm(cand):
                return c
    for c in df.columns:
        if any(norm(c).startswith(norm(cand)) for cand in cands[:2]):
            return c
    return None

def to_num(s):
    return pd.to_numeric(
        s.astype(str)
         .str.replace(r'[\u00A0\s]', '', regex=True)  # espacios, NBSP
         .str.replace(',', '.', regex=False)          # coma decimal → punto
         .str.replace(r'[^0-9.\-]', '', regex=True),  # limpia restos
        errors="coerce"
    )

def read_sheet_robust(url):
    # Lee sin asumir encabezado y detecta la fila que contiene X/Y
    raw = pd.read_csv(url, header=None, dtype=str, engine="python",
                      sep=None, encoding="utf-8-sig", on_bad_lines="skip")
    # busca la primera fila que contenga X y Y (o sinónimos)
    xnorms = set(norm(x) for x in X_CANDS + ["X"])
    ynorms = set(norm(y) for y in Y_CANDS + ["Y"])
    hdr_idx = None
    for i, row in raw.iterrows():
        vals_norm = [norm(v) for v in row.tolist()]
        if any(v in xnorms for v in vals_norm) and any(v in ynorms for v in vals_norm):
            hdr_idx = i
            break
    if hdr_idx is None:
        # como fallback, usa la primera fila no vacía
        hdr_idx = next((i for i, r in raw.iterrows() if any(str(v).strip() for v in r)), 0)
    df = raw.iloc[hdr_idx+1:].reset_index(drop=True)
    df.columns = raw.iloc[hdr_idx].tolist()
    return df

def main():
    df = read_sheet_robust(URL)
    print("Columnas leídas:", list(df.columns))

    x_col = find_col(df, X_CANDS, prefer_exact=["X"])
    y_col = find_col(df, Y_CANDS, prefer_exact=["Y"])
    if not x_col or not y_col:
        raise RuntimeError(f"No encuentro columnas X/Y. Encabezados: {list(df.columns)}")

    df[x_col] = to_num(df[x_col])
    df[y_col] = to_num(df[y_col])

    before = len(df)
    df = df.dropna(subset=[x_col, y_col])
    dropped = before - len(df)
    if df.empty:
        raise RuntimeError("No hay filas válidas con coordenadas luego de limpiar X/Y.")
    print(f"Usando columnas: X='{x_col}', Y='{y_col}'. Filas: {before}, descartadas: {dropped}")

    transformer = Transformer.from_crs(f"EPSG:{SOURCE_EPSG}", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(df[x_col].values, df[y_col].values)
    df["_lon"] = lon; df["_lat"] = lat

    feats = []
    for _, row in df.iterrows():
        props = {k: (None if pd.isna(v) else v) for k, v in row.items() if k not in ["_lon","_lat"]}
        feats.append({
            "type": "Feature",
            "geometry": {"type":"Point","coordinates":[row["_lon"], row["_lat"]]},
            "properties": props
        })
    fc = {"type":"FeatureCollection","features":feats}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"OK: {len(feats)} features → {OUT}")

if __name__ == "__main__":
    main()



