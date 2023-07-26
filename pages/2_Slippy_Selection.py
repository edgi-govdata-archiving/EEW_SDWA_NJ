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

  ### Move the map into the area you'd like to explore then click Get data to retrieve info about nearby public water systems

""")

@st.cache_data
def get_data(query):
  try:
    url= 'https://portal.gss.stonybrook.edu/echoepa/?query='
    data_location = url + urllib.parse.quote_plus(query) + '&pg'
    data = pd.read_csv(data_location, encoding='iso-8859-1', dtype={"REGISTRY_ID": "Int64"})
    return data
  except:
    print("Sorry, can't get data")

# Data Processing
def get_data_from_ids(table, key, list_of_ids):
  ids  = ""
  for i in list_of_ids:
    ids += "'"+i +"',"
  ids = ids[:-1]
  # get data
  sql = 'select * from "'+table+'" where "'+key+'" in ({})'.format(ids)
  data = get_data(sql)
  return data

# Reload, but don't map, PWS
#with st.spinner(text="Loading map..."): # For some reason, not working
try:
  sdwa = st.session_state["sdwa"]
  sdwa = sdwa.loc[sdwa["FISCAL_YEAR"] == 2021]  # for mapping purposes, delete any duplicates
  psa = st.session_state["service_areas"]
except:
  st.error("### Error: Please start on the 'Welcome' page.")
  st.stop()



def main():
  #with st.spinner(text="Loading map..."):
    # Streamlit section
    # Map
    if "markers" not in st.session_state:
      st.session_state["markers"] = []
    if "bounds" not in st.session_state:
      st.session_state["bounds"] = None
    if "psa_gdf" not in st.session_state:
      st.session_state["psa_gdf"] = None

    def change(bounds):
      st.session_state['bounds'] = bounds
      if output["zoom"] < 11:
        with c2:
          st.error("Try zooming in a bit more. There's too much data to show for this big of an area.")
          st.stop()
      # Create a feature from bounds
      feature = {
      "type": "FeatureCollection",
      "features": [
          {
            "type": "Feature",
            "properties": {"Name": "Bounds"},
            "geometry": {
              "coordinates": [
                [
                  [
                    bounds["_southWest"]["lng"],
                    bounds["_northEast"]["lat"]
                  ],
                  [
                    bounds["_southWest"]["lng"],
                    bounds["_southWest"]["lat"]
                  ],
                  [
                    bounds["_northEast"]["lng"],
                    bounds["_southWest"]["lat"]
                  ],
                  [
                    bounds["_northEast"]["lng"],
                    bounds["_northEast"]["lat"]
                  ],
                  [
                    bounds["_southWest"]["lng"],
                    bounds["_northEast"]["lat"]
                  ]
                ]
              ],
              "type": "Polygon"
            }
          }
        ]
      }
      # Get bounds
      bounds = geopandas.GeoDataFrame.from_features(feature)
      x1,y1,x2,y2 = bounds.geometry.total_bounds
      psa_gdf = psa[psa.geometry.intersects(bounds.geometry[0])] # Service areas in the place
      if type(psa_gdf) == list:
        pass
      else:
        psa_gdf = [psa_gdf]
      st.session_state["psa_gdf"] = psa_gdf
      # Get data (to be replaced by a clip?)
      sql = 'select * from "SDWA_PUBLIC_WATER_SYSTEMS_MVIEW" where "FISCAL_YEAR" = \'2021\' and "FAC_LAT" >'+str(y1)+' and "FAC_LAT" <'+str(y2)+' and "FAC_LONG">'+str(x1)+' and "FAC_LONG" <'+str(x2)+''
      data = get_data(sql)
      # save data
      # Process data, make markers for mapping
      markers = [folium.CircleMarker(location=[mark["FAC_LAT"], mark["FAC_LONG"]], fill_color="orange", fill_opacity=1, tooltip=folium.Tooltip(text=mark["FAC_NAME"])) for index,mark in data.iterrows() if mark["FAC_LONG"] is not None]
      st.session_state["markers"] = markers
      st.experimental_rerun()

    m = folium.Map(location=[40.21932319852321, -74.75292012500869], zoom_start=13, min_zoom = 8, max_zoom=15)
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
    for marker in st.session_state["markers"]:
      fg.add_child(marker)

    c1, c2 = st.columns(2)
    
    with c1:
      output = st_folium(m, width=700, height=500, feature_group_to_add=fg, returned_objects=["bounds", "zoom"]) #

    # if bounds change
    if (output["bounds"] and (output["bounds"] != st.session_state["bounds"])):
      st.session_state["bounds"] = output["bounds"]
      change(st.session_state["bounds"])
    
if __name__ == "__main__":
  main()

next = st.button("Next: Environmental Justice")
if next:
    switch_page("environmental justice")
