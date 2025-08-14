# -*- coding: utf-8 -*-
import re, json
import pandas as pd
from pyproj import Transformer

URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQJDO21sdc_3iUUYAPVbaizykV74VclgLlepgFFUW3q6OC2GiNMmnJ1eLoskiTlbO_1cJlU4ShW74MD/pub?gid=1021691292&single=true&output=csv"
OUT = "docs/dictamenes.geojson"

# EPSG de entrada (CRTM05 - CR05). Si tus X/Y fueran CR-SIRGAS/CRTM05 usa 8908.
SOURCE_EPSG = 5367

# Candidatos de nombres
X_CANDS = ["x","este","easting","coordx","coordenadax","crtm05x","xcrtm05"]
Y_CANDS = ["y","norte","northing","coordy","coordenaday","crtm05y","ycrtm05"]

def norm(s): return re.sub(r'\W+','', str(s).lower())

def find_col(df, cands, prefer_exact=None):
    # 1) prefer exact (misma grafía)
    if prefer_exact:
        for ex in prefer_exact:
            if ex in df.columns: 
                return ex
            for c in df.columns:
                if c.strip() == ex:
                    return c
    # 2) igualdad normalizada
    for cand in cands:
        for c in df.columns:
            if norm(c) == norm(cand):
                return c
    # 3) por prefijo
    for c in df.columns:
        if any(norm(c).startswith(norm(cand)) for cand in cands[:2]):
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
    # Lee tolerante: autodetecta separador, ignora líneas malas y BOM
    df = pd.read_csv(
        URL,
        sep=None,
        engine="python",
        encoding="utf-8-sig",
        on_bad_lines="skip"
    )

    print("Columnas leídas:", list(df.columns))

    # Forzar primero X/Y exactos; si no, probar sinónimos
    x_col = find_col(df, X_CANDS, prefer_exact=["X"])
    y_col = find_col(df, Y_CANDS, prefer_exact=["Y"])

    if not x_col or not y_col:
        raise RuntimeError(f"No encuentro columnas X/Y. Encabezados: {list(df.columns)}")

    # Limpieza y filtrado
    df[x_col] = to_num(df[x_col]); df[y_col] = to_num(df[y_col])
    before = len(df)
    df = df.dropna(subset=[x_col, y_col])
    dropped = before - len(df)
    if df.empty:
        raise RuntimeError("No hay filas válidas con coordenadas luego de limpiar X/Y.")

    print(f"Usando columnas: X='{x_col}', Y='{y_col}'. Filas: {before}, descartadas: {dropped}")

    # Reproyección CRTM05 -> WGS84
    transformer = Transformer.from_crs(f"EPSG:{SOURCE_EPSG}", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(df[x_col].values, df[y_col].values)
    df["_lon"] = lon; df["_lat"] = lat

    # Construir GeoJSON
    feats = []
    for _, row in df.iterrows():
        props = {k: (None if pd.isna(v) else v) for k,v in row.items() if k not in ["_lon","_lat"]}
        feats.append({"type":"Feature",
                      "geometry":{"type":"Point","coordinates":[row["_lon"], row["_lat"]]},
                      "properties": props})
    fc = {"type":"FeatureCollection","features":feats}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"OK: {len(feats)} features → {OUT}")

if __name__ == "__main__":
    main()


