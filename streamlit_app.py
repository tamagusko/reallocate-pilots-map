"""Streamlit app to visualise Reallocate pilots Geo data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import folium
import streamlit as st
from folium.plugins import Fullscreen
from streamlit_folium import st_folium

DATA_DIR: Path = Path(__file__).parent / "data"
DEFAULT_ZOOM: int = 12
TILES: str = "cartodbpositron"

def load_geojson_files() -> List[Path]:
    return sorted(DATA_DIR.glob("*.geojson"))

def extract_pilot_city(name: str) -> tuple[str, str]:
    parts = name.split(" ", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return name, ""

def enrich_geojson_content(data: dict, pilot: str, city: str) -> dict:
    if data.get("type") == "FeatureCollection":
        for feature in data.get("features", []):
            feature.setdefault("properties", {})
            feature["properties"]["pilot"] = pilot
            feature["properties"]["city"] = city
    else:
        data.setdefault("properties", {})
        data["properties"]["pilot"] = pilot
        data["properties"]["city"] = city
    return data

def combine_geojson_files(paths: List[Path]) -> dict:
    features: list = []
    for path in paths:
        pilot_name_full = path.stem.replace("_", " ").title()
        pilot, city = extract_pilot_city(pilot_name_full)

        with path.open(encoding="utf-8") as fp:
            data = json.load(fp)

        enriched = enrich_geojson_content(data, pilot, city)

        if enriched.get("type") == "FeatureCollection":
            features.extend(enriched.get("features", []))
        else:
            features.append(enriched)

    return {"type": "FeatureCollection", "features": features}

def enrich_geojson(path: Path) -> dict:
    pilot_name_full = path.stem.replace("_", " ").title()
    pilot, city = extract_pilot_city(pilot_name_full)

    with path.open(encoding="utf-8") as fp:
        data = json.load(fp)

    return enrich_geojson_content(data, pilot, city)

def get_map(geojson_data: dict, fit_bounds: bool = False) -> folium.Map:
    geojson_layer = folium.GeoJson(
        geojson_data,
        name="Pilot Area",
        style_function=lambda _: {
            "fillColor": "#3186cc",
            "color": "#3186cc",
            "weight": 2,
            "fillOpacity": 0.5,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["pilot", "city"],
            aliases=["Pilot:", "City:"],
            localize=True,
            sticky=True,
        ),
        popup=folium.GeoJsonPopup(
            fields=["pilot", "city"],
            aliases=["Pilot:", "City:"],
            localize=True,
        ),
    )

    bounds = geojson_layer.get_bounds()
    lat_center = (bounds[0][0] + bounds[1][0]) / 2
    lon_center = (bounds[0][1] + bounds[1][1]) / 2

    fmap = folium.Map(location=(lat_center, lon_center), zoom_start=DEFAULT_ZOOM, tiles=TILES)

    tooltip = folium.GeoJsonTooltip(
        fields=["pilot", "city"],
        aliases=["Pilot:", "City:"],
        localize=True,
        sticky=True,
    )

    popup = folium.GeoJsonPopup(
        fields=["pilot", "city"],
        aliases=["Pilot:", "City:"],
        localize=True,
    )

    geojson_layer = folium.GeoJson(
        geojson_data,
        name="Pilot Area",
        style_function=lambda _: {
            "fillColor": "#3186cc",
            "color": "#3186cc",
            "weight": 2,
            "fillOpacity": 0.5,
        },
        tooltip=tooltip,
        popup=popup,
    )
    geojson_layer.add_to(fmap)

    bounds = geojson_layer.get_bounds()
    lat_center = (bounds[0][0] + bounds[1][0]) / 2
    lon_center = (bounds[0][1] + bounds[1][1]) / 2
    fmap.location = (lat_center, lon_center)

    if fit_bounds:
        fmap.fit_bounds(bounds)

        if geojson_data.get("type") == "FeatureCollection":
            for feature in geojson_data.get("features", []):
                feature_bounds = folium.GeoJson(feature).get_bounds()
                feature_lat = (feature_bounds[0][0] + feature_bounds[1][0]) / 2
                feature_lon = (feature_bounds[0][1] + feature_bounds[1][1]) / 2
                pilot_name = feature.get("properties", {}).get("pilot", "Unknown")
                city_name = feature.get("properties", {}).get("city", "")

                folium.Marker(
                    location=(feature_lat, feature_lon),
                    popup=f"{pilot_name} ({city_name})",
                    tooltip=f"{pilot_name} ({city_name})",
                    icon=folium.Icon(color="blue", icon="info-sign"),
                ).add_to(fmap)

    Fullscreen().add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)

    return fmap

def main() -> None:
    st.set_page_config(page_title="REALLOCATE Pilots", layout="wide")
    st.title("REALLOCATE Pilots Map")

    geojson_paths = load_geojson_files()
    if not geojson_paths:
        st.error(
            "No GeoJSON files found in the `data` directory. "
            "Please add your pilot files before running the app.",
        )
        st.stop()

    pilot_names = [path.stem.replace("_", " ").title() for path in geojson_paths]
    selection = st.selectbox("Select the pilot", ["All Pilots"] + pilot_names)

    if selection == "All Pilots":
        geojson_content = combine_geojson_files(geojson_paths)
        map_object = get_map(geojson_content, fit_bounds=True)
        st_folium(map_object, width="100%", height=600)

        st.download_button(
            label="Download All Cities GeoJSON",
            data=json.dumps(geojson_content, ensure_ascii=False, indent=2),
            file_name="reallocate_all_pilots.geojson",
            mime="application/geo+json",
        )
    else:
        selected_index = pilot_names.index(selection)
        selected_path = geojson_paths[selected_index]
        geojson_content = enrich_geojson(selected_path)

        map_object = get_map(geojson_content, fit_bounds=True)
        st_folium(map_object, width="100%", height=600)

        st.download_button(
            label=f"Download {selection} GeoJSON",
            data=json.dumps(geojson_content, ensure_ascii=False, indent=2),
            file_name=selected_path.name,
            mime="application/geo+json",
        )

    st.markdown("---")
    st.caption("Data source: reallocatemobility.eu – visualised with Folium & Streamlit")

if __name__ == "__main__":
    main()
