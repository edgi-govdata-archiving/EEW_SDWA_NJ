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

previous = st.button("Previous: Environmental Justice")
if previous:
    switch_page("environmental justice")

st.markdown("""
  # Lead Service Lines by Purveyor Service Area
 """)

st.caption("""
  Remember: if you want to change the boundaries of the selected area, you can always go back to the 
"Statewide Violations" page and do so, then return here.
""")

redraw = st.button("< Return to SDWA Violations to change selected area")
if redraw:
    switch_page("SDWA Violations")

st.markdown("""
  In New Jersey, there are some public water systems that serve
  municipalities as their community drinking water supply. For instance, the City of Vineland has a water utility that provides drinking water to residents
  of the area.

  On this page, we map out the "Purveyor Service Areas" in the area you have selected. Then, we show how many lead service lines these utilities have reported within their service areas.
  
  A lead service line
  is a pipe that goes from the utility's main to a house and is made of lead.
  
  There is no known safe amount of lead exposure, so
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
    st.markdown("""
      # Map of Purveyor Service Areas in Selected Area
    """)

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
    counts = lead_data.sort_values(by=["Measurement (service lines)"], ascending=False)[["Measurement (service lines)"]]
    st.dataframe(counts)
    counts = counts.rename_axis('SYS_NAME').reset_index()
    st.altair_chart(
      alt.Chart(counts, title = 'Number of Lead Service Lines per Public Water System in Selected Area').mark_bar().encode(
        x = alt.X("Measurement (service lines)", title = "Number of lead service lines in system"),
        y = alt.Y('SYS_NAME', axis=alt.Axis(labelLimit = 500), title=None)
      ),
    use_container_width=True
    )

  st.caption("""
    Data compiled from [https://www.njwatercheck.com/BenchmarkHub](https://www.njwatercheck.com/BenchmarkHub)
  """)
  
  st.markdown("""
      ### :face_with_monocle: How can we understand these numbers?
      This data is difficult to present in a way that's easy to intuitively grasp, because although the database gives us the *number* of lead service lines, it doesn't help us understand *who is impacted* or *how likely a given tap in that water system is* to have some lead in the water.
      
      A lead service line is a lead water line that goes from the city's main to someone's house. We could present the number of lead lines as a percentage of total lines, but that could be misleading, because we don't know how many people live in a given unit. For instance, if you had 2,000 lead lines and served a population of 40,000, the "raw" percentage would be 5%, but we don't know how evenly distributed those lead lines are among the population. There may also be inaccuracies or imprecision in the measure of the population served (e.g. do children count? When was the last census? How was the count conducted? Are there populations that are likely to have been left out?)

      :arrow_right: How might this kind of data imprecision intersect with environmental justice? For example, are there demographics that are more likely to have more people in a given household? Is there any way to tell if those same demographics are more or less likely than other parts of the population to have lead service lines?
    """)
if __name__ == "__main__":
  main()

next = st.button("Next: Watershed Pollution")
if next:
    switch_page("watershed pollution")
