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

# Load and join lead/service area data
service_areas = add_spatial_data("https://github.com/edgi-govdata-archiving/ECHO-SDWA/raw/main/Purveyor_Service_Areas_of_New_Jersey.zip", "PSAs") # downloaded from: https://njogis-newjersey.opendata.arcgis.com/datasets/00e7ff046ddb4302abe7b49b2ddee07e/explore?location=40.110098%2C-74.748900%2C9.33
location = geopandas.GeoDataFrame.from_features([st.session_state["last_active_drawing"]])
# filter to area
sas = service_areas[service_areas.geometry.intersects(location.geometry[0]) ] #block groups in the area around the clicked point
sas.set_index("PWID", inplace=True)
# get lead data
lead = pd.read_csv("https://raw.githubusercontent.com/edgi-govdata-archiving/ECHO-SDWA/main/nj_leadlines.csv", 
  dtype={"Measurement (service lines)": int}) # This is a CSV created by collating the results from the above link
lead = sas.join(lead.set_index("PWSID"))
# set new bounds
x1,y1,x2,y2 = lead.geometry.total_bounds
bounds = [[y1, x1], [y2, x2]]
# save data for later
lead_data = lead
#back to features
lead = json.loads(lead.to_json())

# Streamlit section
# Map
def main():
  #if "bounds" not in st.session_state:
  #  st.session_state["bounds"] = None # could set initial bounds here
  if "markers" not in st.session_state:
    st.session_state["markers"] = []
  if "last_active_drawing" not in st.session_state:
    st.session_state["last_active_drawing"] = None
  if "bgs" not in st.session_state:
    st.session_state["sas"] = []
  if "bg_data" not in st.session_state:
    st.session_state["sa_data"] = None
  
  c1, c2, c3 = st.columns(3)

  with c1:
    m = folium.Map()
    #if st.session_state["bounds"]:
    m.fit_bounds(bounds) #st.session_state["bounds"]

    #colorscale = branca.colormap.linear.YlOrRd_09.scale(bg_data[ejvar].min(), bg_data[ejvar].max())
    def style(feature):
      # choropleth approach
      # set colorscale
      colorscale = branca.colormap.linear.YlOrRd_09.scale(lead_data["Measurement (service lines)"].min(), lead_data["Measurement (service lines)"].max())
      return "#d3d3d3" if feature["properties"]["Measurement (service lines)"] is None else colorscale(feature["properties"]["Measurement (service lines)"])

    fg = folium.FeatureGroup(name="BlockGroups")
    #if st.session_state["bgs"]:
    gj = folium.GeoJson(
      lead,
      style_function = lambda sa: {"fillColor": style(sa), "fillOpacity": .75},
      popup=folium.GeoJsonPopup(fields=['Utility', "Measurement (service lines)"])
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

  with c2:
    st.markdown("# Lead Service Lines")
    #if st.session_state["bg_data"] is not None:
    st.dataframe(lead_data.sort_values(by=["Measurement (service lines)"], ascending=False)[["Measurement (service lines)"]])

  with c3:
    st.markdown("# Lead Service Lines")
    #if st.session_state["bg_data"] is not None:
    st.bar_chart(lead_data.sort_values(by=["Measurement (service lines)"], ascending=False)[["Measurement (service lines)"]])

if __name__ == "__main__":
  main()


