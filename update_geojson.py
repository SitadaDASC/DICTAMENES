# -*- coding: utf-8 -*-
import re, json
import pandas as pd
from pyproj import Transformer

# URL del CSV público
URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQJDO21sdc_3iUUYAPVbaizykV74VclgLlepgFFUW3q6OC2GiNMmnJ1eLoskiTlbO_1cJlU4ShW74MD/pub?gid=1021691292&single=true&output=csv"

# <<< CAMBIA AQUÍ si tus encabezados exactos NO son 'X' y 'Y' >>>
X_COL = "X"   # ejemplo: "X" o "ESTE"
Y_COL = "Y"   # ejemplo: "Y" o "NORTE"

OUT = "docs/dictamenes.geojson"
SOURCE_EPSG = 5367  # CRTM05 (CR05). Usa 8908 si tus X/Y están en CR-SIRGAS/CRTM05.

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

    # Verifica que existan exactamente esas columnas
    cols_lower = {c.lower(): c for c in df.columns}
    x_col = cols_lower.get(X_COL.lower())
    y_col = cols_lower.get(Y_COL.lower())
    if not x_col or not y_col:
        raise RuntimeError(f"No se encontraron columnas exactas '{X_COL}' y '{Y_COL}'. Encabezados: {list(df.columns)}")

    # Limpieza y filtrado
    df[x_col] = to_num(df[x_col])
    df[y_col] = to_num(df[y_col])
    df = df.dropna(subset=[x_col, y_col])
    if df.empty:
        raise RuntimeError("No hay filas válidas con coordenadas luego de limpiar X/Y.")

    # Reproyección CRTM05 -> WGS84
    transformer = Transformer.from_crs(f"EPSG:{SOURCE_EPSG}", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(df[x_col].values, df[y_col].values)
    df["_lon"] = lon
    df["_lat"] = lat

    # Construir GeoJSON
    features = []
    for _, row in df.iterrows():
        props = {k: (None if pd.isna(v) else v) for k, v in row.items() if k not in ["_lon","_lat"]}
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [row["_lon"], row["_lat"]]},
            "properties": props
        })
    fc = {"type": "FeatureCollection", "features": features}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)
    print(f"OK: {len(features)} features → {OUT}")

if __name__ == "__main__":
    main()


