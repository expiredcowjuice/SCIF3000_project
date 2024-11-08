import pandas as pd

import branca
import folium
import geopandas as gpd
import streamlit as st
from streamlit_folium import st_folium

# Caching the data loading to improve performance
@st.cache_data
def load_gpkg(file_path, layer_name=None):
    """
    Load a GeoPackage file.
    :param file_path: Path to the GeoPackage file.
    :param layer_name: Specific layer to load (if GeoPackage contains multiple layers).
    :return: GeoDataFrame
    """
    return gpd.read_file(file_path, layer=layer_name)


def load_csv(file_path):
    """
    Load a CSV file.
    :param file_path: Path to the CSV file.
    :return: DataFrame
    """
    df = pd.read_csv(file_path)

    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.long, df.lat), crs='EPSG:4326')


def get_color(risk_level):
    """
    Return color based on risk level.
    :param risk_level: String indicating the risk level.
    :return: Hex color code as a string.
    """
    if risk_level == 'High Risk':
        return 'red'
    elif risk_level == 'Moderate Risk':
        return 'orange'
    else:
        return 'green'

def get_color_gradient_function(min_value, max_value, colors):
    return branca.colormap.LinearColormap(colors, vmin=min_value, vmax=max_value)    

def get_size_gradient_function(min_count, max_count, min_radius=1, max_radius=20):
    return lambda species_count: (min_radius + max_radius) / 2 if max_count == min_count else min_radius + (species_count - min_count) * (max_radius - min_radius) / (max_count - min_count)

# Load GeoDataFrame
soil_gdf = load_gpkg('soil.gpkg')
waterways_gdf = load_gpkg('waterways_distances.gpkg')
chs_gdf = load_gpkg('CHS_distances.gpkg')
biodiversity_gdf = load_gpkg('biodiversity.gpkg')
vegetation_gdf = load_gpkg('vegetation_5km.gpkg')
socioeconomic_gdf = load_csv('socioeconomic_data.csv')
health_gdf = load_csv('health_data.csv')
aboriginal_gdf = load_csv('aboriginal_risk_data.csv')
environmental_gdf = load_csv('environmental_risk_data.csv')


# Convert distance to km
waterways_gdf['distance_km'] = waterways_gdf['distance'] / 1000
chs_gdf['distance_km'] = chs_gdf['distance'] / 1000

# Ensure GeoDataFrame is in WGS84 CRS for Folium
if soil_gdf.crs != 'EPSG:4326':
    soil_gdf = soil_gdf.to_crs(epsg=4326)

if waterways_gdf.crs != 'EPSG:4326':
    waterways_gdf = waterways_gdf.to_crs(epsg=4326)

if chs_gdf.crs != 'EPSG:4326':
    chs_gdf = chs_gdf.to_crs(epsg=4326)

if biodiversity_gdf.crs != 'EPSG:4326':
    biodiversity_gdf = biodiversity_gdf.to_crs(epsg=4326)

if vegetation_gdf.crs != 'EPSG:4326':
    vegetation_gdf = vegetation_gdf.to_crs(epsg=4326)

# Define the center of Australia for initial map view
australia_center = [-25.2744, 133.7751]


st.title("Risk Assessment Map for Transition Metal Mining")
st.markdown("""
This interactive map displays various environmental and socioeconomic factors related to transition metal mining impacts on Indigenous communities in Australia. Use the layer control to toggle different data layers on and off.
""")

# Sidebar Controls for Layer Toggling
st.sidebar.header("Data Layers")

risk_type = st.sidebar.selectbox("Choose Layer", ["Environmental", "Aboriginal"])

toggle_environmental = False
toggle_aboriginal = False

if risk_type == "Environmental":
    toggle_environmental = True
    toggle_soil = st.sidebar.checkbox("Soil Classifications", value=False)
    toggle_waterways = st.sidebar.checkbox("Waterways Distances", value=False)
    toggle_biodiversity = st.sidebar.checkbox("Biodiversity", value=False)
    toggle_vegetation = st.sidebar.checkbox("Vegetation", value=False)
elif risk_type == "Aboriginal":
    toggle_aboriginal = True
    toggle_chs = st.sidebar.checkbox("Cultural Heritage Sites Distances", value=False)
    toggle_socioeconomic = st.sidebar.checkbox("Socioeconomic", value=False)
    toggle_health = st.sidebar.checkbox("Health", value=False)

# Initialize Folium map
m = folium.Map(location=australia_center, zoom_start=4, tiles=None)

# Google Satellite
folium.TileLayer(
    tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    attr='Google',
    name='Google Satellite',
).add_to(m)

# OpenStreetMap
folium.TileLayer(
    tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attr='OpenStreetMap',
    name='OpenStreetMap',
).add_to(m)



def get_popup_html(deposit, metric, value):
    return f"""<b>{deposit}</b><br><b>{metric}:</b> {value}"""

def add_circle_marker(data_point, popup, color, radius=8):
    folium.CircleMarker(
        location=[data_point.geometry.y, data_point.geometry.x],
        radius=radius,
        popup=popup,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.9
    ).add_to(m)

if toggle_environmental:
    # Create a LinearColormap from light blue to dark blue
    color_map = get_color_gradient_function(0, 1, ['#FFFFFF', '#228B22'])

    for _, row in environmental_gdf.iterrows():
        deposit = row['deposit']
        risk = round(row['environmental_risk'], 2)
        color = color_map(risk)
        
        html_popup = get_popup_html(deposit, 'Environmental Risk', risk)
        iframe = folium.IFrame(html=html_popup, width=200, height=55)
        popup = folium.Popup(iframe, max_width=300)

        add_circle_marker(row, popup, color)

    # Add Soil Classifications layer if toggled
    if toggle_soil:
        for _, row in soil_gdf.iterrows():
            deposit = row['deposit']
            risk = row['risk']
            color = get_color(risk)
            
            html_popup = get_popup_html(deposit, 'Soil Risk', risk.replace(' Risk', ''))
            iframe = folium.IFrame(html=html_popup, width=200, height=55)
            popup = folium.Popup(iframe, max_width=200)

            add_circle_marker(row, popup, color)


    # Add Waterway Distances layer if toggled
    if toggle_waterways:
        min_distance = waterways_gdf['distance_km'].min()
        max_distance = waterways_gdf['distance_km'].max()
        
        color_map = get_color_gradient_function(min_distance, max_distance, ['#FFFFFF', '#0000FF'])
        
        for _, row in waterways_gdf.iterrows():
            deposit = row['deposit']
            distance_km = row['distance_km']
            distance_km = round(distance_km, 2)
            color = color_map(distance_km)
            
            html_popup = get_popup_html(deposit, 'Distance to Waterway', str(distance_km) + ' km')
            iframe = folium.IFrame(html=html_popup, width=250, height=55)
            popup = folium.Popup(iframe, max_width=200)
            
            add_circle_marker(row, popup, color)

    # Add Biodiversity layer if toggled
    if toggle_biodiversity:
        min_count = biodiversity_gdf['species_count'].min()
        max_count = biodiversity_gdf['species_count'].max()
        size_map = get_size_gradient_function(min_count, max_count)

        for _, row in biodiversity_gdf.iterrows():
            deposit = row['deposit']
            species_count = row['species_count']
            size = size_map(species_count)

            html_popup = get_popup_html(deposit, 'Species Count', str(species_count))
            iframe = folium.IFrame(html=html_popup, width=200, height=55)
            popup = folium.Popup(iframe, max_width=200)

            add_circle_marker(row, popup, color='orange', radius=size)

    # Add Biodiversity layer if toggled
    if toggle_vegetation:
        min_count = vegetation_gdf['%vegetation'].min()
        max_count = vegetation_gdf['%vegetation'].max()
        size_map = get_size_gradient_function(min_count, max_count)

        for _, row in vegetation_gdf.iterrows():
            deposit = row['deposit']
            vegetation_percent = row['%vegetation']
            size = size_map(vegetation_percent)

            html_popup = get_popup_html(deposit, 'Vegetation', str(round(vegetation_percent, 1)) + '%')
            iframe = folium.IFrame(html=html_popup, width=200, height=55)
            popup = folium.Popup(iframe, max_width=200)

            add_circle_marker(row, popup, color='green', radius=size)

if toggle_aboriginal:
    color_map = get_color_gradient_function(0, 1, ['#FFFFFF', '#A0522D'])

    for _, row in aboriginal_gdf.iterrows():
        deposit = row['deposit']
        risk = round(row['aboriginal_risk'], 2)
        color = color_map(risk)

        html_popup = get_popup_html(deposit, 'Aboriginal Risk', risk)
        iframe = folium.IFrame(html=html_popup, width=200, height=55)
        popup = folium.Popup(iframe, max_width=300)

        add_circle_marker(row, popup, color)

    # Add Cultural Heritage Sites Distances layer if toggled
    if toggle_chs:
        min_distance = chs_gdf['distance_km'].min()
        max_distance = chs_gdf['distance_km'].max()
        
        color_map = get_color_gradient_function(min_distance, max_distance, ['#FFFFFF', '#FF0000'])
        
        for _, row in chs_gdf.iterrows():
            deposit = row['deposit']
            distance_km = row['distance_km']
            distance_km = round(distance_km, 2)
            color = color_map(distance_km)
            
            html_popup = get_popup_html(deposit, 'Distance to Cultural Heritage Site', str(distance_km) + ' km')
            iframe = folium.IFrame(html=html_popup, width=350, height=55)
            popup = folium.Popup(iframe, max_width=350)
            
            add_circle_marker(row, popup, color)


    # Add Socioeconomic layer if toggled
    if toggle_socioeconomic:
        max_value = socioeconomic_gdf['socioeconomic'].max()
        min_value = socioeconomic_gdf['socioeconomic'].min()
        
        color_map = get_color_gradient_function(min_value, max_value, ['#FFFFFF', '#7900FF'])
        
        for _, row in socioeconomic_gdf.iterrows():
            deposit = row['deposit']
            socioeconomic = row['socioeconomic']
            color = color_map(socioeconomic)
            
            html_popup = get_popup_html(deposit, 'Socioeconomic Score', socioeconomic)
            iframe = folium.IFrame(html=html_popup, width=250, height=55)
            popup = folium.Popup(iframe, max_width=250)
            
            add_circle_marker(row, popup, color)
    
    if toggle_health:
        max_value = health_gdf['health'].max()
        min_value = health_gdf['health'].min()
        
        color_map = get_color_gradient_function(min_value, max_value, ['#FFFFFF', '#8B0000'])
        
        for _, row in health_gdf.iterrows():
            deposit = row['deposit']
            health = row['health']
            color = color_map(health)
            
            html_popup = get_popup_html(deposit, 'Health Score', health)
            iframe = folium.IFrame(html=html_popup, width=250, height=55)
            popup = folium.Popup(iframe, max_width=250)
            
            add_circle_marker(row, popup, color)


# Add Layer Control
folium.LayerControl().add_to(m)

# Display the map in Streamlit
st_data = st_folium(m, width=700, height=500)
