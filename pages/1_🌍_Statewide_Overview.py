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
import altair as alt
import json
import requests, zipfile, io

st.set_page_config(layout="wide")
#st.markdown('![EEW logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/eew.jpg?raw=true) ![EDGI logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/edgi.png?raw=true)')

previous = st.button("Previous: Welcome")
if previous:
    switch_page("welcome")

st.markdown("""
  # Exploring Safe Drinking Water in New Jersey
  ## Statewide Overview of Public Water Systems (PWS)
  The Safe Drinking Water Act (SDWA) regulates the provision of drinking water from sources that serve the public*. The US Environmental Protection Agency (EPA) oversees  state agencies that enforce regulations about what kinds of contaminants are allowable in drinking water and at
  what concentration.
""")

st.caption("*Public water systems = water systems that serve at least 25 people, so not private wells.")

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
      source_acronym_dict = {
        'GW': 'Groundwater',
        'SW': 'Surface water'
        }
      for key, value in source_acronym_dict.items():
        sdwa['SOURCE_WATER'] = sdwa['SOURCE_WATER'].str.replace(key, value)

      type_acronym_dict = {
        'NTNCWS': 'Non-Transient, Non-Community Water System',
        'TNCWS': 'Transient Non-Community Water System',
        'CWS': 'Community Water System'
      }
      for key, value in type_acronym_dict.items():
        sdwa['PWS_TYPE_CODE'] = sdwa['PWS_TYPE_CODE'].str.replace(key, value)

      ## Convert to circle markers
      sdwa = sdwa.loc[sdwa["FISCAL_YEAR"] == 2021]  # for mapping purposes, delete any duplicates
      markers = [folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], 
        popup=folium.Popup(mark["PWS_NAME"]+'<br><b>Source:</b> '+mark["SOURCE_WATER"]+'<br><b>Size:</b> '+mark["SYSTEM_SIZE"]+'<br><b>Type:</b> '+mark["PWS_TYPE_CODE"]),
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

  c1 = st.container()
  c2 = st.container()

  with c1:
    st.markdown("## Locations of New Jersey's Public Water Systems")
    st.markdown("""
    Below, you will find an interactive map of all public water systems in New Jersey. Click on the circles to see more information.
    """)
    with st.spinner(text="Loading interactive map..."):
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
      ### :face_with_monocle: Why are there PWS shown outside of New Jersey?
      This is an example of data errors in the EPA database. Sometimes, a facility will be listed with a NJ address
      but its latitude and longitude actually correspond to somewhere out of state.

      :arrow_right: What are some implications of a data error like this? How might a misclassification by state or incorrect location impact the regulation of safe drinking water at a facility?
    """)

    st.markdown("""
      ### Public Water System (PWS) Type Codes

      | Type | What it means |
      |------|---------------|
      | Community Water System | Provides year-round service to the same set of people, e.g. municipal drinking water |
      | Non-Transient, Non-Community Water System | Services e.g. schools, offices, and hospitals that serve a community but not the same people every day |
      | Transient Non-Community Water Systems | Services e.g. gas stations and campgrounds that serve transient populations |

      :arrow_right: Why would the EPA designate water systems in this way? Are they regulated differently?
    """)


  with c2:
    st.markdown("## Summary of Public Water Systems by Type, Size, and Source")
    st.markdown("""

    You can also use the dropdown menu below to learn more about the different kinds of public water systems including:
    * Where they source their water from
    * The size of water systems (very small to very large)
    * *other aspects to be determined*
    """)
    selected_category = st.selectbox(
      "PWS?",
      ['PWS_TYPE_CODE', 'SOURCE_WATER', 'SYSTEM_SIZE'],
      label_visibility = "hidden"
    )
    counts = st.session_state["sdwa"].groupby(by=selected_category)[[selected_category]].count().rename(columns={selected_category:"COUNT"})
    counts.sort_values(by="COUNT",ascending=False, inplace=True) # Sort table by selected_category
    st.dataframe(counts)
    counts = counts.rename_axis(selected_category).reset_index()
    st.altair_chart(
      alt.Chart(counts).mark_bar().encode(
        x = alt.X('COUNT'),
        y = alt.Y(selected_category, axis=alt.Axis(labelLimit = 500), title=None).sort('-x') # Sort horizontal bar chart
      ),
    use_container_width=True
    )

if __name__ == "__main__":
  main()

next = st.button("Next: Safe Drinking Water Act Violations")
if next:
    switch_page("sdwa violations")
