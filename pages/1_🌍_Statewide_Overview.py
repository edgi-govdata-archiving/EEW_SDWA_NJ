# streamlit place picker test
# Pick a place and get ECHO facilities
#https://docs.streamlit.io/library/get-started/create-an-app
import pandas as pd
import urllib.parse
import streamlit as st
from streamlit_folium import st_folium
import geopandas
import folium
from folium.plugins import Draw
import branca
import json
import requests, zipfile, io

st.set_page_config(layout="wide")
st.markdown('![EEW logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/eew.jpg?raw=true) ![EDGI logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/edgi.png?raw=true)')

@st.cache_data
def get_data(query):
  try:
    url= 'https://portal.gss.stonybrook.edu/echoepa/?query='
    data_location = url + urllib.parse.quote_plus(query) + '&pg'
    data = pd.read_csv(data_location, encoding='iso-8859-1', dtype={"REGISTRY_ID": "Int64"})
    return data
  except:
    print("Sorry, can't get data")

# Initial query (NJ PWS)
sql = 'select * from "SDWA_PUBLIC_WATER_SYSTEMS_MVIEW" where "STATE" = \'NJ\'' # About 3500 = 40000 records for multiple FYs #'
sdwa = get_data(sql)
sdwa = geopandas.GeoDataFrame(sdwa, crs = 4269, geometry = geopandas.points_from_xy(sdwa["FAC_LONG"], sdwa["FAC_LAT"]))
if "sdwa" not in st.session_state:
  st.session_state["sdwa"] = sdwa # save for later
sdwa_map = sdwa.drop_duplicates(subset=["PWSID"]) # for mapping purposes, delete any duplicates

# Map all SDWA PWS
## Convert to circle markers
sdwa = sdwa.loc[sdwa["FISCAL_YEAR"] == 2021]  # for mapping purposes, delete any duplicates
markers = [folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], popup=folium.Popup(''+mark["PWS_NAME"]+': '+mark["SOURCE_WATER"]), radius=6, fill_color="orange") for index,mark in sdwa.iterrows() if not mark.geometry.is_empty]

# Streamlit section
# Map
def main():
  #if "bounds" not in st.session_state:
  #  st.session_state["bounds"] = None # could set initial bounds here
  if "markers" not in st.session_state:
    st.session_state["markers"] = []
  if "last_active_drawing" not in st.session_state:
    st.session_state["last_active_drawing"] = None
  if "echo" not in st.session_state:
    st.session_state["echo"] = []
  if "echo_data" not in st.session_state:
    st.session_state["echo_data"] = None
  if "sdwa" not in st.session_state:
    st.session_state["sdwa"] = None
  
  c1, c2, c3 = st.columns(3)

  with c1:
    m = folium.Map(location = [40,-74], zoom_start = 8)
    #if st.session_state["bounds"]:
    #m.fit_bounds() #st.session_state["bounds"] #st.session_state["bounds"]

    #add markers
    for marker in markers:
      m.add_child(marker)

    #Draw(export=True).add_to(m)

    out = st_folium(
      m,
      key="new",
      #feature_group_to_add=fg,
      height=400,
      width=700,
      returned_objects=[]
    )

  with c2:
    st.markdown("# Public Water Systems")
    p = st.selectbox(
      "PWS?",
      ['PWS_TYPE_CODE', 'SOURCE_WATER', 'SYSTEM_SIZE', 'IS_TRIBAL'],
      label_visibility = "hidden"
    )
    st.dataframe(sdwa.groupby(by=p)[[p]].count())

  with c3:
    st.markdown("# Public Water Systems")
    st.bar_chart(sdwa.groupby(by=p)[[p]].count().rename(columns={p:"COUNT"}))

if __name__ == "__main__":
  main()