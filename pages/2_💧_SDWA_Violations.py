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

# Map all SDWA PWS
## Convert to circle markers 
sdwa = st.session_state["sdwa"]
sdwa = sdwa.loc[sdwa["FISCAL_YEAR"] == 2021]  # for mapping purposes, delete any duplicates
markers = [folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], popup=folium.Popup(''+mark["PWS_NAME"]+': '+mark["SOURCE_WATER"]), radius=6, fill_color="orange") for index,mark in sdwa.iterrows() if not mark.geometry.is_empty]

# Streamlit section
# Map
def main():
  if "markers" not in st.session_state:
    st.session_state["markers"] = [] #folium.Marker(location=[40.1, -74.1])
  if "last_active_drawing" not in st.session_state:
    st.session_state["last_active_drawing"] = None
  if "data" not in st.session_state:
    st.session_state["data"] = None
  if "bounds" not in st.session_state:
    st.session_state["bounds"] = None # could set initial bounds here
  if "ej_run" not in st.session_state:
    st.session_state["ej_run"] = False

  c1, c2, c3 = st.columns(3)

  with c1:
    
    m = folium.Map(location=[40,-74], zoom_start=8)
    if st.session_state["bounds"]:
      m.fit_bounds(st.session_state["bounds"])
    fg = folium.FeatureGroup(name="Markers")
    for marker in st.session_state["markers"]:
      fg.add_child(marker)

    Draw(export=True).add_to(m)
    # add st.session_state["last_active_drawing"]
    if st.session_state["last_active_drawing"]:
      geo_j = folium.GeoJson(data=st.session_state["last_active_drawing"])
      fg.add_child(geo_j)

    out = st_folium(
      m,
      key="new",
      feature_group_to_add=fg,
      height=400,
      width=700,
      returned_objects=["last_active_drawing"]
    )
  # Manipulate data
  try:
    counts = st.session_state["data"].groupby(by="PWSID")[["PWSID"]].count()
    counts.rename(columns={"PWSID": "COUNT"}, inplace=True)
    violation_type = st.session_state["data"].groupby(by="HEALTH_BASED")[["HEALTH_BASED"]].count()
    violation_type.rename(columns={"HEALTH_BASED": "COUNT"}, inplace=True)
  except:
    counts = []
    violation_type = []

  with c2:
    st.markdown("# SDWA Violations")
    st.dataframe(counts) 
    st.bar_chart(counts)
  with c3:
    st.markdown("# Violation types")
    st.dataframe(violation_type)
    st.bar_chart(violation_type)

  if ((out["last_active_drawing"]) 
    and (out["last_active_drawing"] != st.session_state["last_active_drawing"]) 
    and (out["last_active_drawing"]["geometry"]["type"] != "Point")
  ):
    st.session_state["last_active_drawing"] = out["last_active_drawing"]
    st.session_state["ej_run"] = False

    bounds = out["last_active_drawing"]
    bounds = geopandas.GeoDataFrame.from_features([bounds])
    bounds.set_crs(4269, inplace=True)
    x1,y1,x2,y2 = bounds.geometry.total_bounds
    st.session_state["bounds"] = [[y1, x1], [y2, x2]]

    these_pws = geopandas.clip(sdwa, bounds.geometry)
    markers = [folium.Marker(location=[mark.geometry.y, mark.geometry.x], popup=f"{mark.FAC_NAME}") for index,mark in these_pws.iterrows() if not mark.geometry.is_empty]
    st.session_state["markers"] = markers

    # Pass to chart constructor
    these_pws = list(these_pws["PWSID"].unique())
    data = get_data_from_ids("SDWA_VIOLATIONS_MVIEW", "PWSID", these_pws)
    st.session_state["data"] = data
    
    


    st.experimental_rerun()

if __name__ == "__main__":
  main()