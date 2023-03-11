# streamlit place picker test
# Pick a place and get ECHO facilities
#https://docs.streamlit.io/library/get-started/create-an-app 

import pandas as pd
import urllib.parse
import hello

hello_world()

# Map
from ipyleaflet import Map, Marker, basemaps, basemap_to_tiles

m = Map(
    basemap=basemap_to_tiles(basemaps.CartoDB.Positron),
    center=(40, -74), 
    zoom=7
  ) # Default to NJ

marker = Marker(location=(40, -74), draggable=True) # defaults to New Jersey for SDWA project
m.add_layer(marker);

"""
sql= 'select * from "ECHO_EXPORTER" where "FAC_CITY" = \'PEEKSKILL\''

def load_data(sql):
  url= 'https://portal.gss.stonybrook.edu/echoepa/?query='
  data_location = url + urllib.parse.quote_plus(sql) + '&pg'
  data = pd.read_csv(data_location, encoding='iso-8859-1', dtype={"REGISTRY_ID": "Int64"})
  data["LAT"] = data["FAC_LAT"]
  data["LON"] = data["FAC_LONG"]
  return data
"""

# Streamlit section
import streamlit as st
#data_load_state = st.text('Loading data...')
#data = load_data(sql)
#data_load_state.text('Loading data...done!')

display(m)