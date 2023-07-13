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
# How do SDWA Violations affect Environmental Justice (EJ) in the Selected Area?
Here you can explore socio-economic demographics and pollution exposures recorded for the place you drew a box around
on the previous page. Does this place experience environmental marginalization in terms of high exposures to lead, traffic exhaust,
and so on? Is it socially marginalized in terms of race, income, or age?
""")

st.caption("""
  Remember: if you want to change the boundaries of the selected area, you can always go back to the 
"Statewide Violations" page and do so, then return here.
""")

redraw = st.button("< Return to SDWA Violations to change selected area")
if redraw:
    switch_page("SDWA Violations")

st.markdown("""
## Select an Environmental Justice measure below

Use the dropdown menu below to select an EJ measure to study. The map will change to show each of the Census block groups that are at least partly in the selected area, and
the recorded value for the EJ measure there. The data come from EPA's EJScreen tool.

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
  st.error("### Error: You must start on the 'Statewide Overview' page and draw a box on the 'SDWA Violations' page in order to proceed.")
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
    st.markdown("# Which EJ measure shall we explore?")
    ejdesc = st.selectbox(
      "Which EJ measure shall we explore?",
      options,
      label_visibility = "hidden"
    )
    ejvar = ej_dict[ejdesc]
    ejdefs = {
      "MINORPCT": "The percent of individuals in a block group who list their racial status as a race other than white alone and/or list their ethnicity as Hispanic or Latino. That is, all people other than non-Hispanic white-alone individuals. The word 'alone' in this case indicates that the person is of a single race, not multiracial.",
      "LOWINCPCT": "The percent of a block group's population in households where the household income is less than or equal to twice the federal poverty level.",
      "LESSHSPCT": "Percent of people age 25 or older in a block group whose education is short of a high school diploma.",
      "LINGISOPCT": "Percent of people in a block group living in limited English speaking households. A household in which all members age 14 years and over speak a non-English language and also speak English less than 'very well' (have difficulty with English) is limited English speaking.",
      "UNDER5PCT": 'Percent of people in a block group under the age of 5.',
      "OVER64PCT": 'Percent of people in a block group over the age of 64.',
      "PRE1960PCT": "Percent of housing units built pre-1960, as indicator of potential lead paint exposure",
      "UNEMPPCT": "The percent of a block group's population that did not have a job at all during the reporting period, made at least one specific active effort to find a job during the prior 4 weeks, and were available for work (unless temporarily ill).",
      "VULEOPCT": "Demographic index of block group used by EPA, an average of low income and people of color populations",
      "DISPEO": "Intermediate variable used for calculation of demographic index",
      "DSLPM": "Diesel particulate matter level in air, µg/m3",
      "CANCER": "Lifetime cancer risk from inhalation of air toxics",
      "RESP": "Ratio of exposure concentration to health-based reference concentration",
      "PTRAF": "Count of vehicles (AADT, avg. annual daily traffic) at major roads within 500 meters, divided by distance in meters (not km)",
      "PWDIS": "RSEI modeled toxic concentrations at stream segments within 500 meters, divided by distance in kilometers (km)",
      "PNPL": "Count of proposed or listed NPL - also known as superfund - sites within 5 km (or nearest one beyond 5 km), each divided by distance in kilometers",
      "PRMP": "Count of RMP (potential chemical accident management plan) facilities within 5 km (or nearest one beyond 5 km), each divided by distance in kilometers",
      "PTSDF": "Count of hazardous waste facilities (TSDFs and LQGs) within 5 km (or nearest beyond 5 km), each divided by distance in kilometers",
      "OZONE": "Annual average of top ten maximum daily 8-hour ozone air concentrations in parts per billion",
      "PM25": "PM2.5 levels in air, µg/m3 annual avg.",
      "UST": "Count of leaking underground storage tanks (multiplied by a factor of 7.7) and the number of underground storage tanks within a 1,500-foot buffered block group"
    }
    st.markdown("**EPA defines this as:**")
    st.markdown(ejdefs[ejvar])
    st.bar_chart(bg_data.sort_values(by=[ejvar], ascending=False)[[ejvar]])
    st.caption("Source for definitions of environmental justice indicators: [socioeconomic](https://www.epa.gov/ejscreen/overview-socioeconomic-indicators-ejscreen) | [environmental](https://www.epa.gov/ejscreen/overview-environmental-indicators-ejscreen)")
    st.markdown(":arrow_right: What assumptions are built into EPA's choices and definitions of environmental justice indicators?")

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
