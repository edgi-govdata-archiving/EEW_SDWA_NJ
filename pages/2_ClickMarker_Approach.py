# streamlit place picker test
# Pick a place and get ECHO facilities
#https://docs.streamlit.io/library/get-started/create-an-app
import pandas as pd
import json
import urllib.parse
import streamlit as st
from streamlit_extras.switch_page_button import switch_page
from streamlit_folium import st_folium
import geopandas
import folium
from folium.plugins import Draw
import altair as alt

st.set_page_config(layout="wide")

previous = st.button("Previous: Statewide Overview")
if previous:
    switch_page("statewide overview")

st.markdown(""" # Search for Public Water Systems

  ### Click on a marker to retrieve information about this public water system

""")

# Reload, but don't map, PWS
with st.spinner(text="Loading data..."):
  try:
    sdwa = st.session_state["sdwa"]
    sdwa = sdwa.loc[sdwa["FISCAL_YEAR"] == 2021]  # for mapping purposes, delete any duplicates
    psa = st.session_state["service_areas"]
  except:
    st.error("### Error: Please start on the 'Welcome' page.")
    st.stop()


def main():
  with st.spinner(text="Loading map..."):
    # Streamlit section
    # Map
    if "last_object_clicked_tooltip" not in st.session_state:
      st.session_state["last_object_clicked_tooltip"] = None
    if "last_object_clicked" not in st.session_state:
      st.session_state["last_object_clicked"] = None
    if "facility" not in st.session_state:
      st.session_state["facility"] = None
    if "psa_gdf" not in st.session_state:
      st.session_state["psa_gdf"] = None

    center = None
    if st.session_state["last_object_clicked"]:
      center = st.session_state["last_object_clicked"]

    m = folium.Map(location=[40.21932319852321, -74.75292012500869], zoom_start=12)
    fg = folium.FeatureGroup(name="data")

    if st.session_state["psa_gdf"] is None:
      pass
    else:
      for this_psa in st.session_state["psa_gdf"]:
        fg.add_child(folium.GeoJson(
          this_psa,
          style_function = lambda sa: {"fillColor": 'grey', "fillOpacity": .25, "weight": 1, "color": "white"},
          tooltip=folium.GeoJsonTooltip(fields=['SYS_NAME', 'AGENCY_URL'])
          )
        )
    data = sdwa[~sdwa.is_empty]
    markers = [folium.CircleMarker(location=[mark["FAC_LAT"], mark["FAC_LONG"]], 
      fill_color="orange" if mark["FAC_NAME"] == st.session_state["facility"] else "blue", 
      fill_opacity=1, 
      tooltip=folium.Tooltip(text=mark["FAC_NAME"] + ", " + mark["PWSID"] )) for index,mark in data.iterrows() if (mark["FAC_LONG"] is not None and mark["FAC_LAT"] is not None)]
    for mark in markers:
      fg.add_child(mark)

    c1, c2 = st.columns(2)
    with c1:
      output = st_folium(m, width=700, height=500, feature_group_to_add=fg, center = center, returned_objects=["last_object_clicked_tooltip", "last_object_clicked"]) #
  
    if ((output["last_object_clicked_tooltip"]) and (output["last_object_clicked_tooltip"] != st.session_state["last_object_clicked_tooltip"])):
      st.session_state["last_object_clicked_tooltip"] = output["last_object_clicked_tooltip"]
      st.session_state["last_object_clicked"] = output["last_object_clicked"]
      st.session_state["facility"] = output["last_object_clicked_tooltip"].split(", ")[0]
      pwsid = output["last_object_clicked_tooltip"].split(", ")[1]
      # Find the matching PSA, if there is one
      # Get PSAs
      this_psa = psa.loc[psa.index == pwsid]
      if type(this_psa) == list:
        pass
      else:
        this_psa = [this_psa]
      st.session_state["psa_gdf"] = this_psa
      st.experimental_rerun()

if __name__ == "__main__":
  main()

next = st.button("Next: Environmental Justice")
if next:
    switch_page("environmental justice")
