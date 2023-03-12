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
def add_spatial_data(url, name, projection=4326):
  """
  Gets external geospatial data
  
  Parameters
  ----------
  url: a zip of shapefile (in the future, extend to geojson)
  name: a string handle for the data files
  projection (optional): an EPSG projection for the spatial dataa

  Returns
  -------
  sd: spatial data reads ]as a geodataframe and projected to a specified projected coordinate system, or defaults to GCS
  
  """

  r = requests.get(url) 
  z = zipfile.ZipFile(io.BytesIO(r.content))
  z.extractall(name)
  sd = geopandas.read_file(""+name+"/")
  sd.to_crs(crs=projection, inplace=True) # transform to input projection, defaults to WGS GCS
  return sd

# Load and join census data

census_data = add_spatial_data(url="https://www2.census.gov/geo/tiger/TIGER2017/BG/tl_2017_34_bg.zip", name="census") #, projection=4269
ej_data = pd.read_csv("https://github.com/edgi-govdata-archiving/ECHO-SDWA/raw/main/EJSCREEN_2021_StateRankings_NJ.csv") # NJ specific
ej_data["ID"] = ej_data["ID"].astype(str)
census_data.set_index("GEOID", inplace=True)
ej_data.set_index("ID", inplace=True)
census_data = census_data.join(ej_data)

# convert st.session_state["last_active_drawing"]
location = geopandas.GeoDataFrame.from_features([st.session_state["last_active_drawing"]])
# filter to area
bgs = census_data[census_data.geometry.intersects(location.geometry[0]) ] #block groups in the area around the clicked point
bg_data = bgs
#st.session_state["bg_data"] = bgs
# set new bounds
x1,y1,x2,y2 = bgs.geometry.total_bounds
#st.session_state["bounds"] = [[y1, x1], [y2, x2]]
bounds = [[y1, x1], [y2, x2]]
#bgs back to features
bgs = json.loads(bgs.to_json())

# Streamlit section
# Map
def main():
  if "bounds" not in st.session_state:
    st.session_state["bounds"] = None # could set initial bounds here
  if "markers" not in st.session_state:
    st.session_state["markers"] = []
  if "last_active_drawing" not in st.session_state:
    st.session_state["last_active_drawing"] = None
  if "bgs" not in st.session_state:
    st.session_state["bgs"] = []
  if "bg_data" not in st.session_state:
    st.session_state["bg_data"] = None
  if "ej_run" not in st.session_state:
    st.session_state["ej_run"] = False
  if "ejvar" not in st.session_state:
    st.session_state["ejvar"] = None
  
  c1, c2, c3 = st.columns(3)

  with c2:
    # EJ variable picking parameters
    options = ["LOWINCPCT", "MINORPCT", "OVER64PCT", "CANCER"] # list of EJScreen variables that will be selected
    st.markdown("# What EJ variable to explore?")
    ejvar = st.selectbox(
      "What EJ variable to explore?",
      options,
      label_visibility = "hidden"
    )

    st.markdown("#### See details on each variable: [metadata]('https://gaftp.epa.gov/EJSCREEN/2021/2021_EJSCREEEN_columns-explained.xlsx')")   
    st.write(bg_data.sort_values(by=[ejvar], ascending=False)[['NAMELSAD',ejvar]])
    st.write(ejvar)

  with c1:
    m = folium.Map()
    #if st.session_state["bounds"]:
    m.fit_bounds(bounds) #st.session_state["bounds"]

    #colorscale = branca.colormap.linear.YlOrRd_09.scale(bg_data[ejvar].min(), bg_data[ejvar].max())
    def style(feature):
      # choropleth approach
      # set colorscale
      colorscale = branca.colormap.linear.YlOrRd_09.scale(bg_data[ejvar].min(), bg_data[ejvar].max())
      return "#d3d3d3" if feature["properties"][ejvar] is None else colorscale(feature["properties"][ejvar])

    fg = folium.FeatureGroup(name="BlockGroups")
    #if st.session_state["bgs"]:
    gj = folium.GeoJson(
      bgs,
      #st.session_state["bgs"],
      style_function = lambda bg: {"fillColor": style(bg), "fillOpacity": .75}, #style(bg)
      popup=folium.GeoJsonPopup(fields=['NAMELSAD', ejvar])
      ).add_to(m) #.add_to(fg)

    # add st.session_state["last_active_drawing"]
    #if st.session_state["last_active_drawing"]:
    geo_j = folium.GeoJson(st.session_state["last_active_drawing"])
    geo_j.add_to(m)
    #add markers
    for marker in st.session_state["markers"]:
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

  with c3:
    st.markdown("# EJ Variables")
    #if st.session_state["bg_data"] is not None:
    st.bar_chart(bg_data.sort_values(by=[ejvar], ascending=False)[[ejvar]])
if __name__ == "__main__":
  main()