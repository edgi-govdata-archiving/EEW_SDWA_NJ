# streamlit place picker test
# Pick a place and get ECHO facilities
#https://docs.streamlit.io/library/get-started/create-an-app
import pandas as pd
import urllib.parse
import streamlit as st
from streamlit_extras.switch_page_button import switch_page
from streamlit_folium import st_folium
import geopandas
import folium
from folium.plugins import Draw
import branca
import json
import requests, zipfile, io

st.set_page_config(layout="wide")
#st.markdown('![EEW logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/eew.jpg?raw=true) ![EDGI logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/edgi.png?raw=true)')

previous = st.button("Previous: Welcome")
if previous:
    switch_page("welcome")

st.markdown("""
# What are the Public Water Systems of New Jersey?
## Statewide Overview of Public Water Systems (PWS)""")
st.markdown("""
Below, you will find an interactive map of all public water systems* in New Jersey. Click on the circles to see more information.
""")

st.caption("*Public water systems = water systems that serve at least 25 people, so not private wells.")

st.markdown("***The map might take a minute to load.***")

def main():
  @st.cache_data
  def get_data(query):
    try:
      # Get data
      url= 'https://portal.gss.stonybrook.edu/echoepa/?query='
      data_location = url + urllib.parse.quote_plus(query) + '&pg'
      data = pd.read_csv(data_location, encoding='iso-8859-1', dtype={"REGISTRY_ID": "Int64"})

      # Map all SDWA PWS
      sdwa = geopandas.GeoDataFrame(data, crs = 4269, geometry = geopandas.points_from_xy(data["FAC_LONG"], data["FAC_LAT"]))
      # String manipulations to make output more readable
      sdwa['SOURCE_WATER'] = sdwa['SOURCE_WATER'].str.replace('GW', 'Groundwater')
      sdwa['SOURCE_WATER'] = sdwa['SOURCE_WATER'].str.replace('SW', 'Surface water')
      sdwa['PWS_TYPE_CODE'] = sdwa['PWS_TYPE_CODE'].str.replace('NTNCWS', 'Non-Transient, Non-Community Water System')
      sdwa['PWS_TYPE_CODE'] = sdwa['PWS_TYPE_CODE'].str.replace('TNCWS', 'Transient Non-Community Water System')
      sdwa['PWS_TYPE_CODE'] = sdwa['PWS_TYPE_CODE'].str.replace('CWS', 'Community Water System')
      ## Convert to circle markers
      sdwa = sdwa.loc[sdwa["FISCAL_YEAR"] == 2021]  # for mapping purposes, delete any duplicates
      markers = [folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], 
        popup=folium.Popup(mark["PWS_NAME"]+'<br>Source = '+mark["SOURCE_WATER"]+'<br>Size = '+mark["SYSTEM_SIZE"]+'<br>Type = '+mark["PWS_TYPE_CODE"]),
        radius=6, fill_color="orange") for index,mark in sdwa.iterrows() if not mark.geometry.is_empty]

      return sdwa, markers
    except:
      print("Sorry, can't get data")

  # Initial query (NJ PWS)
  sql = 'select * from "SDWA_PUBLIC_WATER_SYSTEMS_MVIEW" where "STATE" = \'NJ\'' # About 3500 = 40000 records for multiple FYs #'
  sdwa, markers = get_data(sql)
  if "sdwa" not in st.session_state:
    st.session_state["sdwa"] = sdwa # save for later

  # Streamlit section
  # Map
  if "markers" not in st.session_state:
    st.session_state["markers"] = []
  if "last_active_drawing" not in st.session_state:
    st.session_state["last_active_drawing"] = None

  c1, c2 = st.columns(2)

  with c1:
    st.markdown("## Locations of PWS")
    m = folium.Map(location = [40.25,-74], zoom_start = 7, tiles="cartodb positron")

    #add markers
    for marker in markers:
      m.add_child(marker)

    out = st_folium(
      m,
      key="new",
      height=400,
      width=700,
      returned_objects=[]
    )
    
  st.markdown("""
    ### Why are there PWS shown outside of New Jersey?
    That's because EPA doesn't do a great job of tracking facilities. Sometimes, a facility will be listed with a NJ address
    but it's latitude and longitude actually correspond to somewhere out of state
  """)

  st.markdown("""

  You can also use the dropdown menu in the middle of the page to learn more about the different kinds of public water systems including:
  * Where they source their water from
  * The size of water systems (very small to very large)
  * *other aspects to be determined*
  """)

  st.markdown("""
    ### :face_with_monocle: What do all the acronyms mean?
    * GW = Groundwater
    * SW = Surface water
    * CWS = Community Water System - year-round service to the same set of people, e.g. municipal drinking water
    * NTNCWS = Non-Transient, Non-Community Water System - e.g. schools, offices, and hospitals that serve a community but not the same people every day 
    * TNCWS = Transient non-community water systems - e.g. gas stations and campgrounds that serve transient populations
  """)

  with c2:
    st.markdown("## Summary of PWS by Type, Size, and Source")
    p = st.selectbox(
      "PWS?",
      ['PWS_TYPE_CODE', 'SOURCE_WATER', 'SYSTEM_SIZE'],
      label_visibility = "hidden"
    )
    st.dataframe(st.session_state["sdwa"].groupby(by=p)[[p]].count())
    st.bar_chart(st.session_state["sdwa"].groupby(by=p)[[p]].count().rename(columns={p:"COUNT"}))

if __name__ == "__main__":
  main()

next = st.button("Next: Safe Drinking Water Act Violations")
if next:
    switch_page("sdwa violations")