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

# Load watershed data based on intersection
# get bbox of drawn shape. or, centroid
location = geopandas.GeoDataFrame.from_features([st.session_state["last_active_drawing"]])
point = location.geometry.centroid # Cheating
# Get watershed boundary
sql = 'SELECT * FROM "wbdhu12" WHERE ST_WITHIN(ST_GeomFromText(\''+str(point[0])+'\', 4269), "wbdhu12"."wkb_geometry");' 
watershed = get_data(sql)
if len(str(watershed["huc12"][0]))<12:
  w = "0"+str(watershed["huc12"][0])
else:
  w = watershed["huc12"][0]

# set new bounds
watershed['geometry'] = geopandas.GeoSeries.from_wkb(watershed['wkb_geometry'])
watershed.drop("wkb_geometry", axis=1, inplace=True)
watershed = geopandas.GeoDataFrame(watershed, crs=4269)
x1,y1,x2,y2 = watershed.geometry.total_bounds
bounds = [[y1, x1], [y2, x2]]
# save data for later
watershed_data = watershed
# to features
watershed = json.loads(watershed.to_json())

# Get ECHO facilities within watershed
sql = 'SELECT "ECHO_EXPORTER".* FROM "ECHO_EXPORTER","wbdhu12" WHERE ST_WITHIN("ECHO_EXPORTER"."wkb_geometry", "wbdhu12"."wkb_geometry") AND "wbdhu12"."huc12" = \''+w+'\' AND "ECHO_EXPORTER"."NPDES_FLAG" = \'Y\';'
echo = get_data(sql)
echo['geometry'] = geopandas.GeoSeries.from_wkb(echo['wkb_geometry'])
echo.drop("wkb_geometry", axis=1, inplace=True)
echo = geopandas.GeoDataFrame(echo, crs=4269)
echo.set_index("REGISTRY_ID", inplace=True)
markers = [folium.Marker(location=[mark.geometry.y, mark.geometry.x], popup=f"{mark.FAC_NAME}") for index,mark in echo.iterrows() if not mark.geometry.is_empty]

# Get discharge data based on watershed id
sql = 'select * from "DMR_FY2022_MVIEW" where "FAC_DERIVED_WBD" = \''+w+'\'' 
dmr = get_data(sql)
#st.write(dmr)

top_pollutants = dmr.groupby(['PARAMETER_DESC'])[["FAC_NAME"]].nunique()
top_pollutants = top_pollutants.rename(columns={"FAC_NAME": "# of facilities"})
top_pollutants.sort_values(by="# of facilities", ascending=False)

top_pollutors = dmr.groupby(['PARAMETER_DESC', 'FAC_NAME', 'STANDARD_UNIT_DESC'])[["DMR_VALUE_STANDARD_UNITS"]].sum()
top_pollutors = top_pollutors.rename(columns={"STANDARD_UNIT_DESC": "units", "DMR_VALUE_STANDARD_UNITS": "values"})

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
  if "w" not in st.session_state:
    st.session_state["w"] = None
  
  c1, c2, c3 = st.columns(3)

  with c1:
    m = folium.Map()
    #if st.session_state["bounds"]:
    m.fit_bounds(bounds) #st.session_state["bounds"]

    fg = folium.FeatureGroup(name="BlockGroups")
    #if st.session_state["bgs"]:
    gj = folium.GeoJson(
      watershed,
      style_function = lambda sa: {"fillColor": "blue", "fillOpacity": .75},
      popup=folium.GeoJsonPopup(fields=['huc12'])
      ).add_to(m) #.add_to(fg)

    # add st.session_state["last_active_drawing"]
    #if st.session_state["last_active_drawing"]:
    geo_j = folium.GeoJson(st.session_state["last_active_drawing"])
    geo_j.add_to(m)
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
    st.markdown("# Top Pollutants")
    #if st.session_state["bg_data"] is not None:
    st.dataframe(top_pollutants)
    st.bar_chart(top_pollutants)

  with c3:
    st.markdown("# Top Pollutors")
    pollutant = st.selectbox(
      "What pollutant?",
      list(top_pollutants.index),
      label_visibility = "hidden"
    )
    st.dataframe(top_pollutors.loc[pollutant].sort_values(by="values", ascending=False))
    st.bar_chart(top_pollutors.loc[pollutant].sort_values(by="values", ascending=False).reset_index().set_index("FAC_NAME")[["values"]])

if __name__ == "__main__":
  main()