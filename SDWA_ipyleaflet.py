# streamlit place picker test
# Pick a place and get ECHO facilities
#https://docs.streamlit.io/library/get-started/create-an-app
import pandas as pd
import urllib.parse
import streamlit as st
from st_leaflet import st_leaflet
from streamlit_folium import st_folium
import geopandas
from ipyleaflet import Map, Marker, CircleMarker, LayerGroup, GeoJSON, basemaps, basemap_to_tiles

col1, col2, col3 = st.columns(3)

def get_data(query):
  try:
    url= 'https://portal.gss.stonybrook.edu/echoepa/?query='
    data_location = url + urllib.parse.quote_plus(sql) + '&pg'
    data = pd.read_csv(data_location, encoding='iso-8859-1', dtype={"REGISTRY_ID": "Int64"})
    return data
  except:
    print("Sorry, can't get data")

# Initial query (NJ PWS)
sql = 'select * from "SDWA_PUBLIC_WATER_SYSTEMS_MVIEW" where "STATE" = \'NJ\'' # About 3500 = 40000 records for multiple FYs #and "FISCAL_YEAR" = \'2021\'
sdwa = get_data(sql)
njpws = sdwa.drop_duplicates(subset=["PWSID"]) # for mapping purposes, delete duplicates
njpws = geopandas.GeoDataFrame(njpws, crs = 4269, geometry = geopandas.points_from_xy(njpws["FAC_LONG"], njpws["FAC_LAT"]))
njpws.to_crs(crs = 26918, inplace=True) # Local projection

# Handle interactive map
layer_group = LayerGroup()
search_radius = CircleMarker()
def handle_move(**kwargs):
  # Make the location a geopandas object
  print(kwargs)
  point = geopandas.GeoSeries(geopandas.points_from_xy(x=[kwargs["location"][1]], y=[kwargs["location"][0]], crs=4326)).to_crs(crs=26918)
  # Clip PWS to those within 10km of the point
  buffer = point.buffer(10000)
  these_pws = geopandas.clip(njpws, buffer)
  # Convert to webmap crs
  these_pws = these_pws.to_crs(4326)
  buffer = buffer.to_crs(4326)
  # Remove previous markers from map
  global layer_group 
  global search_radius
  try:
    m.remove_layer(layer_group)
    m.remove_layer(search_radius)
  except:
    pass
  # Add search radius to map
  search_radius = GeoJSON(
    data = json.loads(buffer.to_json()), # load as geojson
  )
  m.add_layer(search_radius)
  # Add new markers to map
  radius = 10
  marks = [CircleMarker(location=(mark.geometry.y, mark.geometry.x), radius = radius, popup=HTML(mark["FAC_NAME"])) for index,mark in these_pws.iterrows() if not mark.geometry.is_empty]
  layer_group = LayerGroup(layers=marks)
  m.add_layer(layer_group)
  # Filter data
  these_pws = these_pws["PWSID"].unique()
  display(these_pws)
  # Pass to chart constructor
  make_chart(these_pws)

# Map
m = Map(
    basemap=basemap_to_tiles(basemaps.CartoDB.Positron),
    center=(40, -74), 
    zoom=10
  ) # Default to NJ
marker = Marker(location=(40, -74), draggable=True) # defaults to New Jersey for SDWA project
m.add_layer(marker);
marker.on_move(handle_move)

# Data Processing
def get_data_from_ids(input, key, table):
  ids  = ""
  for id in input:
    ids += "'"+id +"',"
  ids = ids[:-1]
  
  # get data
  sql = 'select * from "'+table+'" where "'+key+'" in ({})'.format(ids)
  data = get_data(sql)
  return data

def make_chart(ids):
  data = get_data_from_ids("SDWA_VIOLATIONS_MVIEW", "PWSID", ids)
  # Manipulate data
  data = data.groupby(by="PWSID")[["PWSID"]].count().sort_values(by="PWSID", ascending=False)
  col2.bar_chart(data=data)

# Streamlit section
col1.write(st_folium(m))
col3.metric("Violations", "20", "-8%")