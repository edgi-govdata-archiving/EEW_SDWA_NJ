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

previous = st.button("Previous: Safe Drinking Water Act Violations")
if previous:
    switch_page("sdwa violations")

st.markdown("""
# How do SDWA Violations affect Environmental Justice (EJ) in this Place?
Here you can explore socio-economic demographics and pollution exposures recorded for the place you drew a box around
on the previous page. Does this place experience environmental marginalization in terms of high exposures to lead, traffic exhaust,
and so on? Is it socially marginalized in terms of race, income, or age? 

Remember: if you want to explore somewhere else or change the boundaries, you can always go back to the 
"Statewide Violations" page and do so, then return here.

Use the dropdown menu to select an EJ measure. The map will change to show each of the Census block groups in the place and
the recorded value for the measure there. The data come from EPA's EJScreen tool.

*Important: any percentages shown here are shown as decimals. For instance, 80% is shown as .8*

On the map, the darker the shade of the blue, 
the more of the measure - a higher percentage minority population, cancer rate, or number of underground storage tanks, for instance.

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

# Load and join census data
with st.spinner(text="Loading data..."):
  census_data = add_spatial_data(url="https://www2.census.gov/geo/tiger/TIGER2017/BG/tl_2017_34_bg.zip", name="census") #, projection=4269
  ej_data = pd.read_csv("https://github.com/edgi-govdata-archiving/ECHO-SDWA/raw/main/EJSCREEN_2021_StateRankings_NJ.csv") # NJ specific
  ej_data["ID"] = ej_data["ID"].astype(str)
  census_data.set_index("GEOID", inplace=True)
  ej_data.set_index("ID", inplace=True)
  census_data = census_data.join(ej_data)

# Convert st.session_state["last_active_drawing"]
try:
  location = geopandas.GeoDataFrame.from_features([st.session_state["last_active_drawing"]])
except:
  st.error("### Error: Did you forget to start on the 'Statewide Overview' page and/or draw a box on the 'SDWA Violations' page?")
  st.stop()
# Filter to area
bgs = census_data[census_data.geometry.intersects(location.geometry[0]) ] # Block groups in the area around the clicked point
bg_data = bgs
# Set new bounds
x1,y1,x2,y2 = bgs.geometry.total_bounds
bounds = [[y1, x1], [y2, x2]]
# bgs back to features
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
  if "ejvar" not in st.session_state:
    st.session_state["ejvar"] = None
  
  c1 = st.container()
  c2 = st.container()

  with c2:
    # EJ parameters we are working with
    ej_parameters = {
      "MINORPCT",
      "LOWINCPCT",
      "LESSHSPCT",
      "LINGISOPCT",
      "UNDER5PCT",
      "OVER64PCT",
      "PRE1960PCT",
      "UNEMPPCT",
      "VULEOPCT",
      "DISPEO",
      "DSLPM",
      "CANCER",
      "RESP",
      "PTRAF",
      "PWDIS",
      "PNPL",
      "PRMP",
      "PTSDF",
      "OZONE",
      "PM25",
      "UST"
    }

    @st.cache_data
    def get_metadata():
      columns = pd.read_csv("https://raw.githubusercontent.com/edgi-govdata-archiving/ECHO-SDWA/main/2021_EJSCREEEN_columns-explained.csv")
      return columns
    columns = get_metadata()
    columns = columns.loc[columns["GDB Fieldname"].isin(ej_parameters)][["GDB Fieldname", "Description"]]
    columns.set_index("Description", inplace = True)
    ej_dict = columns.to_dict()['GDB Fieldname']

    options = ej_dict.keys() # list of EJScreen variables that will be selected
    st.markdown("# Which EJ measure to explore?")
    ejdesc = st.selectbox(
      "Which EJ measure to explore?",
      options,
      label_visibility = "hidden"
    )
    ejvar = ej_dict[ejdesc]
    st.bar_chart(bg_data.sort_values(by=[ejvar], ascending=False)[[ejvar]])

  with c1:
    with st.spinner(text="Loading interactive map..."):
      m = folium.Map(tiles="cartodb positron")
      m.fit_bounds(bounds)

      def style(feature):
        # choropleth approach
        # set colorscale
        colorscale = branca.colormap.linear.Blues_05.scale(bg_data[ejvar].min(), bg_data[ejvar].max()) # 0 - 1? 
        return "#d3d3d3" if feature["properties"][ejvar] is None else colorscale(feature["properties"][ejvar])

      geo_j = folium.GeoJson(st.session_state["last_active_drawing"])
      geo_j.add_to(m)
      gj = folium.GeoJson(
        bgs,
        style_function = lambda bg: {"fillColor": style(bg), "fillOpacity": .75, "weight": 1},
        popup=folium.GeoJsonPopup(fields=['BLKGRPCE', ejvar])
        ).add_to(m) 
      for marker in st.session_state["markers"]:
        m.add_child(marker)

      out = st_folium(
        m,
        returned_objects=[]
      )

if __name__ == "__main__":
  main()

next = st.button("Next: Lead Service Lines")
if next:
    switch_page("lead service lines")
