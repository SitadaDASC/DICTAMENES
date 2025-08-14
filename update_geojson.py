# -*- coding: utf-8 -*-
import re
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# URL pública del CSV (la tuya)
URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQJDO21sdc_3iUUYAPVbaizykV74VclgLlepgFFUW3q6OC2GiNMmnJ1eLoskiTlbO_1cJlU4ShW74MD/pub?gid=1021691292&single=true&output=csv"

# Si tus columnas son 'ESTE' y 'NORTE', cámbialas aquí:
COL_X_CANDIDATES = ["x", "este", "easting", "coordx", "crtm05x"]
COL_Y_CANDIDATES = ["y", "norte", "northing", "coordy", "crtm05y"]

df = pd.read_csv(URL)

def norm(s): return re.sub(r'\W+','', str(s).lower())

def find_col(candidates):
    for cand in candidates:
        for c in df.columns:
            if norm(c) == norm(cand):
                return c
    return None

x_col = find_col(COL_X_CANDIDATES)
y_col = find_col(COL_Y_CANDIDATES)
if not x_col or not y_col:
    raise RuntimeError(f"No encuentro columnas X/Y (CRTM05). Columnas: {list(df.columns)}")

def to_num(s):
    return pd.to_numeric(
        s.astype(str)
         .str.replace(r'[\u00A0\s]', '', regex=True)
         .str.replace(',', '.', regex=False)
         .str.replace(r'[^0-9.\-]', '', regex=True),
        errors="coerce"
    )

df[x_col] = to_num(df[x_col])
df[y_col] = to_num(df[y_col])
df = df.dropna(subset=[x_col, y_col])

# Geometría en CRTM05 (CR05) EPSG:5367 -> reproyectar a WGS84 (4326)
gdf = gpd.GeoDataFrame(
    df,
    geometry=[Point(xy) for xy in zip(df[x_col], df[y_col])],
    crs="EPSG:5367"
).to_crs(4326)

# Salida para GitHub Pages
gdf.to_file("docs/dictamenes.geojson", driver="GeoJSON")
print(f"OK: {len(gdf)} features generadas")

