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

  ### Use the control on the left-hand side of the map to add a marker and retrieve information about public water systems near it

""")

@st.cache_data
def get_data(query):
  try:
    url= 'https://portal.gss.stonybrook.edu/echoepa/?query='
    data_location = url + urllib.parse.quote_plus(query) + '&pg'
    print(query, data_location)
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
with st.spinner(text="Loading map..."):
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
    if "markers" not in st.session_state:
      st.session_state["markers"] = []
    if "last_active_drawing" not in st.session_state:
      st.session_state["last_active_drawing"] = None
    if "data" not in st.session_state:
      st.session_state["data"] = None
    if "bounds" not in st.session_state:
      st.session_state["bounds"] = None
    if "psa_gdf" not in st.session_state:
      st.session_state["psa_gdf"] = None
    if "last_clicked" not in st.session_state:
      st.session_state["last_clicked"] = None

    m = folium.Map(location=[40.21932319852321, -74.75292012500869], zoom_start=12)
    Draw(
      export=False,
      draw_options={"polyline": False, "circle": False, "marker": False, "circlemarker": True, "polygon": False, "rectangle": False},
      edit_options={"edit": False, "remove": False}
    ).add_to(m)
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
    if st.session_state["bounds"] is not None:
      m.fit_bounds(st.session_state["bounds"])
    if st.session_state["last_active_drawing"] is not None:
      fg.add_child(folium.GeoJson(st.session_state["last_active_drawing"]))

    c1, c2 = st.columns(2)
    with c1:
      output = st_folium(m, width=700, height=500, feature_group_to_add=fg, returned_objects=["last_active_drawing"]) #

    #with c2:
      #st.write(output)

    if ((output["last_active_drawing"]) and (output["last_active_drawing"]["geometry"]["type"] == "Point")):
      st.session_state["last_active_drawing"] = output["last_active_drawing"]
      # Get and map data
      x = output["last_active_drawing"]["geometry"]["coordinates"][1]
      y = output["last_active_drawing"]["geometry"]["coordinates"][0]
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
                    y - .10,
                    x + .05
                  ],
                  [
                    y - .10,
                    x - .05
                  ],
                  [
                    y + .10,
                    x - .05
                  ],
                  [
                    y + .10,
                    x + .05
                  ],
                  [
                    y - .10,
                    x + .05
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
      st.session_state["bounds"] = [[y1, x1], [y2, x2]]
      # Get PSAs
      psa_gdf = psa[psa.geometry.intersects(bounds.geometry[0])] # Service areas in the place
      if type(psa_gdf) == list:
        pass
      else:
        psa_gdf = [psa_gdf]
      st.session_state["psa_gdf"] = psa_gdf
      # Get data
      sql = 'select * from "SDWA_PUBLIC_WATER_SYSTEMS_MVIEW" where "FAC_LAT" >'+str(y1)+' and "FAC_LAT" <'+str(y2)+' and "FAC_LONG">'+str(x1)+' and "FAC_LONG" <'+str(x2)+''
      data = get_data(sql)
      # save data
      # Process data, make markers for mapping
      markers = [folium.CircleMarker(location=[mark["FAC_LAT"], mark["FAC_LONG"]], fill_color="orange", fill_opacity=1, tooltip=folium.Tooltip(text=mark["FAC_NAME"])) for index,mark in data.iterrows() if mark["FAC_LONG"] is not None]
      st.session_state["markers"] = markers
      st.experimental_rerun()

if __name__ == "__main__":
  main()

next = st.button("Next: Environmental Justice")
if next:
    switch_page("environmental justice")
