# streamlit place picker test
# Pick a place and get ECHO facilities
#https://docs.streamlit.io/library/get-started/create-an-app

import streamlit as st
from streamlit_extras.switch_page_button import switch_page
from streamlit_folium import st_folium
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
c4 = st.container()

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
with c3:
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
       
    r = {"Very Small": 6, "Small": 10, "Medium": 16, "Large": 24, "Very Large": 32}

    # Filter data for use on later pages as a default
    default_box = json.loads('{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"name": "default box"},"geometry":{"coordinates":[[[-74.28527671505785,41.002662478823],[-74.28527671505785,40.88373661477061],[-74.12408529371498,40.88373661477061],[-74.12408529371498,41.002662478823],[-74.28527671505785,41.002662478823]]],"type":"Polygon"}}]}')
    # set bounds
    bounds = geopandas.GeoDataFrame.from_features(default_box)
    bounds.set_crs(4326, inplace=True)
    #x1,y1,x2,y2 = bounds.geometry.total_bounds

    ## Convert to circle markers
    sdwa_circles = sdwa.loc[sdwa["FISCAL_YEAR"] == 2021]  # For mapping purposes, remove any duplicates and non-current entries

    markers = [folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], 
      popup=folium.Popup(mark["FAC_NAME"]+'<br><b>Source:</b> '+mark["SOURCE_WATER"]+'<br><b>Size:</b> '+mark["SYSTEM_SIZE"]+'<br><b>Type:</b> '+mark["PWS_TYPE_CODE"]),
      radius=r[mark["SYSTEM_SIZE"]], fill_color=t[mark["PWS_TYPE_CODE"]], stroke=s[mark["SOURCE_WATER"]]) for index,mark in sdwa_circles.iterrows() if not mark.geometry.is_empty]

    local_sdwa_circles = sdwa_circles[sdwa_circles.geometry.intersects(bounds.geometry[0])]
    local_markers = [folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], 
      popup=folium.Popup(mark["FAC_NAME"]+'<br><b>Source:</b> '+mark["SOURCE_WATER"]+'<br><b>Size:</b> '+mark["SYSTEM_SIZE"]+'<br><b>Type:</b> '+mark["PWS_TYPE_CODE"]),
      radius=r[mark["SYSTEM_SIZE"]], fill_color=t[mark["PWS_TYPE_CODE"]], stroke=s[mark["SOURCE_WATER"]]) for index,mark in local_sdwa_circles.iterrows() if not mark.geometry.is_empty]

    # Load purveyor service area (PSA) data
    service_areas = add_spatial_data("https://github.com/edgi-govdata-archiving/ECHO-SDWA/raw/main/Purveyor_Service_Areas_of_New_Jersey.zip", "PSAs") # downloaded from: https://njogis-newjersey.opendata.arcgis.com/datasets/00e7ff046ddb4302abe7b49b2ddee07e/explore?location=40.110098%2C-74.748900%2C9.33
    service_areas.set_index("PWID", inplace=True)

    # Save data
    if "marker_styles" not in st.session_state:
      st.session_state["marker_styles"] = {"r": r, "t": t, "s": s}
    if "sdwa" not in st.session_state: # all SDWA PWS data
      st.session_state["sdwa"] = sdwa
    if "statewide_markers" not in st.session_state: # All markers for PWS
      st.session_state["statewide_markers"] = markers
    if "these_data" not in st.session_state: # local SDWA numbers for charts
      st.session_state["these_data"] = sdwa[sdwa.geometry.intersects(bounds.geometry[0])]
    if "these_markers" not in st.session_state: # *Local* PWS for mapping defaults
      st.session_state["these_markers"] = local_markers
    if "service_areas" not in st.session_state: # All PSAs
      st.session_state["service_areas"] = service_areas
    if "these_psa" not in st.session_state: # Local PSAs for mapping defaults
      st.session_state["these_psa"] = service_areas[service_areas.geometry.intersects(bounds.geometry[0])] # Service areas in the place
    if "box" not in st.session_state: # Default bounds
      st.session_state["box"] = bounds

    next = st.button("Get Started! >")
    if next:
        switch_page("statewide overview")

  with c4:
    st.markdown("""
    ##### This website was created by the [Environmental Enforcement Watch](https://environmentalenforcementwatch.org/) (EEW) project of the [Environmental Data and Governance Initiative](https://envirodatagov.org/) (EDGI).  Please visit our websites to learn more about our work!
                
    This tool was funded by National Science Foundation Awards #2127334 and #2127335.
    """)