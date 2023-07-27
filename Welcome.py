# streamlit place picker test
# Pick a place and get ECHO facilities
#https://docs.streamlit.io/library/get-started/create-an-app

import streamlit as st
from streamlit_extras.switch_page_button import switch_page
import pandas as pd
import urllib.parse
import geopandas
import folium
import json
import requests, zipfile, io

st.set_page_config(layout="wide")
st.markdown('![EEW logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/eew.jpg?raw=true) ![EDGI logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/edgi.png?raw=true)')

c1 = st.container()
c2 = st.container()
c3 = st.container()

with c1:
  st.markdown("""# Exploring Safe Drinking Water in New Jersey
  This website enables you to explore different aspects of safe drinking water across 
  the state of New Jersey as well as in specific locations within the state.

  The Safe Drinking Water Act (SDWA) regulates the provision of drinking water from sources that serve the public*
  . The US Environmental Protection Agency (EPA) oversees
  state agencies that enforce regulations about what kinds of contaminants are allowable in drinking water and at
  what concentration.
  """)

  st.caption("""*i.e. those that serve at least 25 people, so not private household wells""")

with c2:
  st.markdown("""## What You Can Learn Here
  You can explore imporant questions about SDWA in New Jersey on this website, such as:
  * Where are the state's public water systems?
  * Which ones serve my community?
  * Do they get their water from groundwater sources such as aquifiers or from surface waters such as rivers?
  * Have they been in violation of SDWA regulations? 
  * Are these violations a result of posing risks to health?
  * Who might be most affected by how public water systems manage drinking water? What are the environmental justice implications?
  * Does my community have lead service lines, the kinds of which contributed to Flint, Michigan's drinking water crisis?
  * What kinds of pollutants are permitted to be released in the watershed?
  """)

  next = st.button("Get Started! >")
  if next:
      switch_page("statewide overview")

with c3:
  st.markdown("""## How to Use This Website
  (These instructions will be repeated on each page)

  1. Navigate to the "Statewide Overview" page to see a map of all public water systems in the state of New Jersey, according to the EPA.
  The page may take a minute to load. **You can always come back to this page as you further explore a specific public water system or set of water systems.** You can click on the markers on the map representing each public water system to learn more about it, including its name. You can also use
  the dropdown menu in the middle of the page to learn more about the different kinds of public water systems including:
      * Where they source their water from
      * The size of water systems (very small to very large)
      * The type of water systems (e.g. institutional ones or community/municipal ones)

  2. Next, navigate to "SDWA Violations."
  Using the buttons on the left-hand side of the map, draw a rectangle around the part of New Jersey that you want to learn more about.
  *Important: your box should be fairly small, so that you are focused on a specific community or region, otherwise you'll get an error message.
  If that happens, just draw a smaller box and try again.*
  After you draw the box, the page will load any public water systems within it as well as details about any violations of SDWA they may have
  recorded since 2001.
  **Later, if you wish to expand your search or narrow it, you can come back to this page and draw a different box.**

  3. Moving to the "Environmental Justice" page, you can explore socio-economic indicators recorded for the place you drew a box around
  on the previous page, to get a sense of whether the SDWA violations, lead service lines, and watershed pollutants have any
  correlation with neighborhood-level factors such as race, income, age, or education level. 
  Use the dropdown menu to select an EJ measure. The map will change to show each of the Census block groups in the place and
  the recorded value for the measure there. The data come from EPA's EJScreen tool.

  4. Go to the next page, "Lead Service Lines," where we map out the "Purveyor Service Areas" that fall within the boundaries 
  of the box you previously drew. We show how many lead service lines these utilities have reported within their service areas. 
  A lead service line is a pipe that goes from the utility's main to a house and is made of lead. There is no known safe amount of lead exposure, 
  so lead service lines may pose a risk to residents' well-being. 

  5. On the last page, you can explore what pollutants industrial facilities reported releasing into the watershed between October 2021 and September 2022. 
  We will show you the watersheds for the place you selected and the industrial facilities within those watershed that reported releasing different kinds of pollutants. 
  Use the dropdown menu to select different pollutants and see how much reporting facilities said they discharged into the watershed.
  """)

  st.markdown("""
  ##### This website was created by the [Environmental Enforcement Watch](https://environmentalenforcementwatch.org/) (EEW) project of the [Environmental Data and Governance Initiative](https://envirodatagov.org/) (EDGI).  Please visit our websites to learn more about our work!
  """)

@st.cache_data
def get_data(query):
  try:
    # Get data
    url= 'https://portal.gss.stonybrook.edu/echoepa/?query='
    data_location = url + urllib.parse.quote_plus(query) + '&pg'
    data = pd.read_csv(data_location, encoding='iso-8859-1', dtype={"REGISTRY_ID": "Int64"})
    # Map all SDWA PWS
    sdwa = geopandas.GeoDataFrame(data, crs = 4269, geometry = geopandas.points_from_xy(data["FAC_LONG"], data["FAC_LAT"]))
    return sdwa
  except:
    with c1:
      st.error("### Sorry, there's a problem getting the data.")
      st.stop()
        
# Get service area data
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

# Initial query (NJ PWS)
with st.spinner(text="Loading data..."):
  # Load PWS data
  sql = 'select * from "SDWA_PUBLIC_WATER_SYSTEMS_MVIEW" where "STATE" = \'NJ\'' # About 3500 = 40000 records for multiple FYs #'
  sdwa = get_data(sql)

  # String manipulations to make output more readable
  source_acronym_dict = {
    'GW': 'Groundwater',
    'SW': 'Surface water'
  }
  for key, value in source_acronym_dict.items():
    sdwa['SOURCE_WATER'] = sdwa['SOURCE_WATER'].str.replace(key, value)
  s = {"Groundwater": False, "Surface water": True}

  type_acronym_dict = {
    'NTNCWS': 'Non-Transient, Non-Community Water System',
    'TNCWS': 'Transient Non-Community Water System',
    'CWS': 'Community Water System'
  }
  for key, value in type_acronym_dict.items():
    sdwa['PWS_TYPE_CODE'] = sdwa['PWS_TYPE_CODE'].str.replace(key, value)
  t = {'Non-Transient, Non-Community Water System': "green", 'Transient Non-Community Water System': "yellow", 'Community Water System': "blue"}
     
  r = {"Very Small": 2, "Small": 6, "Medium": 12, "Large": 20, "Very Large": 32}

  # Filter data for use on later pages as a default
  default_box = json.loads('{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"name": "default box"},"geometry":{"coordinates":[[[-74.28527671505785,41.002662478823],[-74.28527671505785,40.88373661477061],[-74.12408529371498,40.88373661477061],[-74.12408529371498,41.002662478823],[-74.28527671505785,41.002662478823]]],"type":"Polygon"}}]}')
  # set bounds
  bounds = geopandas.GeoDataFrame.from_features(default_box)
  bounds.set_crs(4326, inplace=True)
  x1,y1,x2,y2 = bounds.geometry.total_bounds

  ## Convert to circle markers
  sdwa_circles = sdwa.loc[sdwa["FISCAL_YEAR"] == 2021]  # For mapping purposes, remove any duplicates and non-current entries

  markers = [folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], 
    popup=folium.Popup(mark["PWS_NAME"]+'<br><b>Source:</b> '+mark["SOURCE_WATER"]+'<br><b>Size:</b> '+mark["SYSTEM_SIZE"]+'<br><b>Type:</b> '+mark["PWS_TYPE_CODE"]),
    radius=r[mark["SYSTEM_SIZE"]], fill_color=t[mark["PWS_TYPE_CODE"]], stroke=s[mark["SOURCE_WATER"]]) for index,mark in sdwa_circles.iterrows() if not mark.geometry.is_empty]

  local_sdwa_circles = sdwa_circles[sdwa_circles.geometry.intersects(bounds.geometry[0])]
  local_markers = [folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], 
    popup=folium.Popup(mark["PWS_NAME"]+'<br><b>Source:</b> '+mark["SOURCE_WATER"]+'<br><b>Size:</b> '+mark["SYSTEM_SIZE"]+'<br><b>Type:</b> '+mark["PWS_TYPE_CODE"]),
    radius=r[mark["SYSTEM_SIZE"]], fill_color=t[mark["PWS_TYPE_CODE"]], stroke=s[mark["SOURCE_WATER"]]) for index,mark in local_sdwa_circles.iterrows() if not mark.geometry.is_empty]

  # Load purveyor service area (PSA) data
  service_areas = add_spatial_data("https://github.com/edgi-govdata-archiving/ECHO-SDWA/raw/main/Purveyor_Service_Areas_of_New_Jersey.zip", "PSAs") # downloaded from: https://njogis-newjersey.opendata.arcgis.com/datasets/00e7ff046ddb4302abe7b49b2ddee07e/explore?location=40.110098%2C-74.748900%2C9.33
  service_areas.set_index("PWID", inplace=True)

  # Save data
  if "default_box" not in st.session_state: # May not need this in the future depending on the area selection approach
    st.session_state["default_box"] = default_box
  if "sdwa" not in st.session_state: # all SDWA PWS data
    st.session_state["sdwa"] = sdwa
  if "statewide_markers" not in st.session_state: # All markers for PWS
    st.session_state["statewide_markers"] = markers
  #if "data" not in st.session_state: # local SDWA numbers for charts
  #  st.session_state["data"] = sdwa[sdwa.geometry.intersects(bounds.geometry[0])]
  if "markers" not in st.session_state: # *Local* PWS for mapping defaults
    st.session_state["markers"] = local_markers
  if "service_areas" not in st.session_state: # All PSAs
    st.session_state["service_areas"] = service_areas
  if "psa_gdf" not in st.session_state: # Local PSAs for mapping defaults
    st.session_state["psa_gdf"] = service_areas[service_areas.geometry.intersects(bounds.geometry[0])] # Service areas in the place
  if "bounds" not in st.session_state: # Default bounds
    st.session_state["bounds"] = [[y1, x1], [y2, x2]]