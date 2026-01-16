# -*- coding: utf-8 -*-
import re
import json
from pathlib import Path

import pandas as pd
from pyproj import Transformer


# =========================
# CONFIGURACION
# =========================
URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQJDO21sdc_3iUUYAPVbaizykV74VclgLlepgFFUW3q6OC2GiNMmnJ1eLoskiTlbO_1cJlU4ShW74MD/pub?gid=1021691292&single=true&output=csv"
OUT = Path("docs/dictamenes.geojson")

# EPSG de entrada (CRTM05 - Lambert Norte CR)
SOURCE_EPSG = 5367

X_CANDS = ["x", "este", "easting", "coordx", "coordenadax", "crtm05x", "xcrtm05"]
Y_CANDS = ["y", "norte", "northing", "coordy", "coordenaday", "crtm05y", "ycrtm05"]


# =========================
# UTILIDADES
# =========================
def norm(s: object) -> str:
    # Normaliza para comparar encabezados: minusculas y sin simbolos/espacios
    return re.sub(r"\W+", "", str(s).lower()).strip()


def find_col(df: pd.DataFrame, cands: list[str], prefer_exact: list[str] | None = None) -> str | None:
    cols = list(df.columns)

    # 1) Prefer exact match (por ejemplo: "X" y "Y")
    if prefer_exact:
        for ex in prefer_exact:
            for c in cols:
                if str(c).strip() == ex:
                    return c

    # 2) Match normalizado exacto (x, este, etc)
    c_norm_map = {c: norm(c) for c in cols}
    for cand in cands:
        nc = norm(cand)
        for c in cols:
            if c_norm_map[c] == nc:
                return c

    # 3) Fallback: empieza con (x/este) o (y/norte)
    # (Solo usa los 2 primeros candidatos como prefijo)
    pref = [norm(x) for x in cands[:2]]
    for c in cols:
        if any(c_norm_map[c].startswith(p) for p in pref):
            return c

    return None


def to_num(series: pd.Series) -> pd.Series:
    # Convierte a numero limpiando espacios, NBSP y texto raro
    return pd.to_numeric(
        series.astype(str)
        .str.replace(r"[\u00A0\s]", "", regex=True)  # espacios y NBSP
        .str.replace(",", ".", regex=False)          # coma decimal -> punto
        .str.replace(r"[^0-9.\-]", "", regex=True),  # limpia letras y simbolos
        errors="coerce",
    )


def read_sheet_robust(url: str) -> pd.DataFrame:
    """
    Lee el CSV sin asumir encabezado y detecta automaticamente
    la fila que contiene los headers (buscando X/Y o sinonimos).
    """
    raw = pd.read_csv(
        url,
        header=None,
        dtype=str,
        engine="python",
        sep=None,
        encoding="utf-8-sig",
        on_bad_lines="skip",
    )

    xnorms = set(norm(x) for x in (X_CANDS + ["X"]))
    ynorms = set(norm(y) for y in (Y_CANDS + ["Y"]))

    hdr_idx = None
    for i, row in raw.iterrows():
        vals_norm = [norm(v) for v in row.tolist()]
        if any(v in xnorms for v in vals_norm) and any(v in ynorms for v in vals_norm):
            hdr_idx = i
            break

    if hdr_idx is None:
        # Fallback: usa primera fila no vacia
        hdr_idx = next((i for i, r in raw.iterrows() if any(str(v).strip() for v in r)), 0)

    df = raw.iloc[hdr_idx + 1 :].reset_index(drop=True)
    df.columns = [str(c).strip() for c in raw.iloc[hdr_idx].tolist()]
    return df


def build_feature_collection(df: pd.DataFrame, lon_col: str, lat_col: str) -> dict:
    feats = []
    for _, row in df.iterrows():
        props = {}
        for k, v in row.items():
            if k in (lon_col, lat_col):
                continue
            props[k] = None if pd.isna(v) else v

        feats.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row[lon_col], row[lat_col]]},
                "properties": props,
            }
        )

    return {"type": "FeatureCollection", "features": feats}


# =========================
# MAIN
# =========================
def main() -> None:
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

    df["_lon"] = lon
    df["_lat"] = lat

    OUT.parent.mkdir(parents=True, exist_ok=True)

    fc = build_feature_collection(df, "_lon", "_lat")
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)

    print(f"OK: {len(fc['features'])} features -> {OUT.as_posix()}")


if __name__ == "__main__":
    main()



