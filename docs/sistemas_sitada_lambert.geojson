# -*- coding: utf-8 -*-
import io, re
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# URL pública del CSV (la que me pasaste)
URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQJDO21sdc_3iUUYAPVbaizykV74VclgLlepgFFUW3q6OC2GiNMmnJ1eLoskiTlbO_1cJlU4ShW74MD/pub?gid=1021691292&single=true&output=csv"

# Nombres de columnas en CRTM05 (cámbialos si en tu Sheet se llaman distinto)
COL_X = "X"       # o "ESTE", "EASTING", etc.
COL_Y = "Y"       # o "NORTE", "NORTHING", etc.

# Leer CSV
df = pd.read_csv(URL)

# Normalizar nombres (por si vienen con may/min)
cols = {c.lower(): c for c in df.columns}
# intenta detectar X/Y si no existen tal cual
def find(colnames):
    for key in colnames:
        for c in df.columns:
            if re.sub(r'\W+','',c.lower()) == re.sub(r'\W+','',key.lower()):
                return c
    return None

x_col = find([COL_X, "x", "este", "easting", "coordx", "crtm05x"])
y_col = find([COL_Y, "y", "norte", "northing", "coordy", "crtm05y"])

if not x_col or not y_col:
    raise RuntimeError(f"No encuentro columnas X/Y (CRTM05). Revisa nombres. Tengo: {list(df.columns)}")

# Limpiar a número
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

# Geometría en CRTM05 → reproyectar a WGS84
gdf = gpd.GeoDataFrame(
    df,
    geometry=[Point(xy) for xy in zip(df[x_col], df[y_col])],
    crs="EPSG:5367"   # CRTM05
).to_crs(4326)       # WGS84

# Guardar en docs/
gdf.to_file("docs/sistemas_sitada_lambert.geojson", driver="GeoJSON")
print(f"OK: {len(gdf)} features")
