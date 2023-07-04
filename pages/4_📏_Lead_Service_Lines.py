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

previous = st.button("Previous: Environmental Justice")
if previous:
    switch_page("environmental justice")

st.markdown("""
  # Lead Service Lines by Purveyor Service Area
  In New Jersey, there are some public water systems that serve
  municipalities as their community drinking water supply.

  For instance, the City of Vineland has a water utility that provides drinking water to residents
  of the area.

  On this page, we map out of the "Purveyor Service Areas" that fall within the boundaries of the box you previously drew. 

  Then, we show how many lead service lines these utilities have reported within their service areas. A lead service line
  is a pipe that goes from the utility's main to a house and is made of lead. There is no known safe amount of lead exposure, so
  lead service lines may pose a risk to residents' well-being. 

  The darker the shade of blue, the more lead lines are reported in the area.
""")

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
with st.spinner(text="Loading data..."):
  service_areas = add_spatial_data("https://github.com/edgi-govdata-archiving/ECHO-SDWA/raw/main/Purveyor_Service_Areas_of_New_Jersey.zip", "PSAs") # downloaded from: https://njogis-newjersey.opendata.arcgis.com/datasets/00e7ff046ddb4302abe7b49b2ddee07e/explore?location=40.110098%2C-74.748900%2C9.33
  try:
    location = geopandas.GeoDataFrame.from_features([st.session_state["last_active_drawing"]])
  except:
    st.error("### Error: Did you forget to start on the 'Statewide Overview' page and/or draw a box on the 'SDWA Violations' page?")
    st.stop()
  # Filter to area
  sas = service_areas[service_areas.geometry.intersects(location.geometry[0]) ] # Service areas in the place
  sas.set_index("PWID", inplace=True)
  # Get lead data
  lead = pd.read_csv("https://raw.githubusercontent.com/edgi-govdata-archiving/ECHO-SDWA/main/nj_leadlines.csv", 
    dtype={"Measurement (service lines)": int}) # This is a CSV created by collating the results from the above link
  lead = sas.join(lead.set_index("PWSID"))
  lead.set_index("SYS_NAME", inplace=True)
  # Set new bounds
  x1,y1,x2,y2 = lead.geometry.total_bounds
  bounds = [[y1, x1], [y2, x2]]
  # Save data for later
  lead_data = lead
  # Back to features
  lead = json.loads(lead.to_json())

# Streamlit section
# Map
def main():  
  c1 = st.container()
  c2 = st.container()

  with c1:
    with st.spinner(text="Loading interactive map..."):
      m = folium.Map(tiles="cartodb positron")
      m.fit_bounds(bounds)

      def style(feature):
        # choropleth approach
        # set colorscale
        colorscale = branca.colormap.linear.Blues_05.scale(lead_data["Measurement (service lines)"].min(), lead_data["Measurement (service lines)"].max())
        return "#d3d3d3" if feature["properties"]["Measurement (service lines)"] is None else colorscale(feature["properties"]["Measurement (service lines)"])

      fg = folium.FeatureGroup()
      geo_j = folium.GeoJson(st.session_state["last_active_drawing"])
      geo_j.add_to(m)
      gj = folium.GeoJson(
        lead,
        style_function = lambda sa: {"fillColor": style(sa), "fillOpacity": .75, "weight": 1},
        popup=folium.GeoJsonPopup(fields=['Utility', "Measurement (service lines)"])
        ).add_to(m) #.add_to(fg)
      for marker in st.session_state["markers"]:
        m.add_child(marker)

      out = st_folium(
        m,
        key="new",
        height=400,
        width=700,
        returned_objects=[]
      )

  with c2:
    st.markdown("# Count of Lead Service Lines")
    st.bar_chart(lead_data.sort_values(by=["Measurement (service lines)"], ascending=False)[["Measurement (service lines)"]])

  st.markdown("""
    ### Where do these data come from?
    They were compiled from [https://www.njwatercheck.com/BenchmarkHub](https://www.njwatercheck.com/BenchmarkHub)
  """)
if __name__ == "__main__":
  main()

next = st.button("Next: Watershed Pollution")
if next:
    switch_page("watershed pollution")
