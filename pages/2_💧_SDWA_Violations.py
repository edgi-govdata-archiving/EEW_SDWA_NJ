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
st.markdown(""" # Search for Public Water Systems and Find Violations
Using the buttons on the left-hand side of the map, draw a rectangle around the part of New Jersey that you want to learn more about.

*Important: your box should be fairly small, so that you are focused on a specific community or region, otherwise you'll get an error message.
If that happens, just draw a smaller box and try again.*

After you draw the box, the page will load any public water systems within it as well as details about any violations of SDWA they may have
recorded since 2001.

Later, if you wish to expand your search or narrow it, you can come back to this page and draw a different box.
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
try:
  sdwa = st.session_state["sdwa"]
  sdwa = sdwa.loc[sdwa["FISCAL_YEAR"] == 2021]  # for mapping purposes, delete any duplicates
except:
  st.error("### Error: Did you forget to start on the 'Statewide Overview' page?")
  st.stop()

# Streamlit section
# Map
def main():
  if "markers" not in st.session_state:
    st.session_state["markers"] = []
  if "last_active_drawing" not in st.session_state:
    st.session_state["last_active_drawing"] = None
  if "data" not in st.session_state:
    st.session_state["data"] = None
  if "bounds" not in st.session_state:
    st.session_state["bounds"] = None

  c1, c2, c3 = st.columns(3)

  with c1:
    
    m = folium.Map(location = [40.1538589,-74.2826471], zoom_start = 10, tiles="cartodb positron")
    if st.session_state["bounds"]:
      m.fit_bounds(st.session_state["bounds"])
    fg = folium.FeatureGroup()

    Draw(
      export=False,
      draw_options={"polyline": False, "circle": False, "marker": False, "circlemarker": False},
      edit_options=None
    ).add_to(m)

    if st.session_state["last_active_drawing"]:
      geo_j = folium.GeoJson(data=st.session_state["last_active_drawing"])
      fg.add_child(geo_j)
    for marker in st.session_state["markers"]:
      fg.add_child(marker)

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
    counts = st.session_state["data"].groupby(by="FAC_NAME")[["FAC_NAME"]].count()
    counts.rename(columns={"FAC_NAME": "COUNT"}, inplace=True)
    counts = counts.sort_values(by="COUNT", ascending=False)
    violation_type = st.session_state["data"].groupby(by="HEALTH_BASED")[["HEALTH_BASED"]].count()
    violation_type.rename(columns={"HEALTH_BASED": "COUNT"}, inplace=True)
    violation_type = violation_type.sort_values(by="COUNT", ascending=False)
  except:
    counts = []
    violation_type = []

  with c2:
    st.markdown("# SDWA Violations by PWS")
    st.dataframe(counts) 
    st.bar_chart(counts)
  with c3:
    st.markdown("# Health-Based Violations")
    st.dataframe(violation_type)
    st.bar_chart(violation_type)
  
  if ((out["last_active_drawing"]) 
    and (out["last_active_drawing"] != st.session_state["last_active_drawing"]) 
    and (out["last_active_drawing"]["geometry"]["type"] != "Point")
  ):
    st.session_state["last_active_drawing"] = out["last_active_drawing"]
    bounds = out["last_active_drawing"]
    bounds = geopandas.GeoDataFrame.from_features([bounds])
    bounds.set_crs(4269, inplace=True)
    if bounds.geometry.area[0] < .07:
      x1,y1,x2,y2 = bounds.geometry.total_bounds
      st.session_state["bounds"] = [[y1, x1], [y2, x2]]

      # Get data
      these_pws = geopandas.clip(sdwa, bounds.geometry)
      these_pws = list(these_pws["PWSID"].unique())
      data = get_data_from_ids("SDWA_VIOLATIONS_MVIEW", "PWSID", these_pws)
      st.session_state["data"] = data
      markers = [folium.CircleMarker(location=[mark["FAC_LAT"], mark["FAC_LONG"]], 
        popup = folium.Popup(
        mark["FAC_NAME"] + "<br>"
        ), #PWS_NAME
        radius = 6, fill_color="orange") for index,mark in data.iterrows() if mark["FAC_LONG"] is not None]
      st.session_state["markers"] = markers
      st.experimental_rerun()
    else:
      with c1:
        st.markdown("### You've drawn a big area! Try drawing a smaller one.")
      st.session_state["last_active_drawing"] = None
      out["last_active_drawing"] = None

    

if __name__ == "__main__":
  main()