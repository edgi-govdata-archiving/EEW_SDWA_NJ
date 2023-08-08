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
from folium.plugins import FastMarkerCluster
import branca
import json
import requests, zipfile, io

st.set_page_config(layout="wide", page_title="⚖️ Environmental Justice")

previous = st.button("Previous: Safe Drinking Water Act Violations")
if previous:
    switch_page("sdwa violations")

st.markdown("""
# How do SDWA Violations relate to Environmental Justice (EJ) in the Selected Area?
Here you can explore socio-economic indicators recorded for the place you drew a box around
on the previous page, to get a sense of whether the SDWA violations, lead service lines, and watershed pollutants have any
correlation with neighborhood-level factors such as race, income, age, or education level. 
""")

st.caption("""
  Remember: if you want to change the boundaries of the selected area, you can always go back to the 
"Statewide Violations" page and do so, then return here.
""")

redraw = st.button("< Return to SDWA Violations to change selected area")
if redraw:
    switch_page("SDWA Violations")

st.markdown("""
  ## Select environmental justice measures

  Use the dropdown menus below to view measures EPA uses to calculate environmental justice.
              
  The maps show each of the census block groups 
  that are at least partly in the selected area, and the recorded value for the selected EJ measure there (using data from EPA's EJScreen tool). 
  The darker the shade of the blue, the more present that measure is in the block group — 
  for example, a higher percentage minority population will appear in a darker blue. Overlaid on the color blocks,
  you can see safe drinking water act violations. (If the violations aren't showing up, try going back to the Drinking Water Violations page and then returning here.)
""")

@st.cache_data
def add_spatial_data(url, name, projection=4326):
  """
  Gets external geospatial data
  
  Parameters
  ----------
  url: a zip of shapefile (in the future, extend to geojson)
  name: a string handle for the data files
  projection (optional): an EPSG projection for the spatial data

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

# EJ parameters we are working with
longest_definition_length = 315
ejdefs = {
  "MINORPCT":   "Percent of individuals in a block group who list their racial status as a race other than white alone and/or list their ethnicity as Hispanic or Latino. That is, all people other than non-Hispanic white-alone individuals. The word 'alone' in this case indicates that the person is of a single race, not multiracial.\n",
  "LOWINCPCT":  "Percent of a block group's population in households where the household income is less than or equal to twice the federal poverty level.\n" + (longest_definition_length-136)*"&nbsp;",
  "LESSHSPCT":  "Percent of people age 25 or older in a block group whose education is short of a high school diploma.\n" + (longest_definition_length-101)*"&nbsp;",
  "LINGISOPCT": "Percent of people in a block group living in limited English speaking households. A household in which all members age 14 years and over speak a non-English language and also speak English less than 'very well' (have difficulty with English) is limited English speaking.\n" + (longest_definition_length-270)*"&nbsp;",
  "UNDER5PCT":  "Percent of people in a block group under the age of 5.\n" + (longest_definition_length-54)*"&nbsp;",
  "OVER64PCT":  "Percent of people in a block group over the age of 64.\n" + (longest_definition_length-54)*"&nbsp;",
  "UNEMPPCT":   "Percent of a block group's population that did not have a job at all during the reporting period, made at least one specific active effort to find a job during the prior 4 weeks, and were available for work (unless temporarily ill).\n" + (longest_definition_length-232)*"&nbsp;",
  "PRE1960PCT": "Percent of housing units built pre-1960, as indicator of potential lead paint exposure\n" + (longest_definition_length-86)*"&nbsp;",
  "DSLPM":      "Diesel particulate matter level in air, µg/m3\n" + (longest_definition_length-45)*"&nbsp;",
  "CANCER":     "Lifetime cancer risk from inhalation of air toxics\n" + (longest_definition_length-50)*"&nbsp;",
  "RESP":       "Ratio of exposure concentration to health-based reference concentration\n" + (longest_definition_length-71)*"&nbsp;",
  "PTRAF":      "Count of vehicles (AADT, avg. annual daily traffic) at major roads within 500 meters, divided by distance in meters (not km)\n" + (longest_definition_length-124)*"&nbsp;",
  "PWDIS":      "RSEI modeled toxic concentrations at stream segments within 500 meters, divided by distance in kilometers (km)\n" + (longest_definition_length-10)*"&nbsp;",
  "PNPL":       "Count of proposed or listed NPL - also known as superfund - sites within 5 km (or nearest one beyond 5 km), each divided by distance in kilometers\n" + (longest_definition_length-146)*"&nbsp;",
  "PRMP":       "Count of RMP (potential chemical accident management plan) facilities within 5 km (or nearest one beyond 5 km), each divided by distance in kilometers\n" + (longest_definition_length-150)*"&nbsp;",
  "PTSDF":      "Count of hazardous waste facilities (TSDFs and LQGs) within 5 km (or nearest beyond 5 km), each divided by distance in kilometers\n" + (longest_definition_length-129)*"&nbsp;",
  "OZONE":      "Annual average of top ten maximum daily 8-hour ozone air concentrations in parts per billion\n" + (longest_definition_length-92)*"&nbsp;",
  "PM25":       "PM2.5 levels in air, µg/m3 annual avg.\n" + (longest_definition_length-38)*"&nbsp;",
  "UST":        "Count of leaking underground storage tanks (multiplied by a factor of 7.7) and the number of underground storage tanks within a 1,500-foot buffered block group\n" + (longest_definition_length-159)*"&nbsp;"
} # definitions of each parameter
ej_parameters = list(ejdefs.keys()) # the parameters themselves
socecon = ej_parameters[0:8] # socioeconomic measures
env = ej_parameters[8:len(ej_parameters)] # environmental/health measures

@st.cache_data
def get_metadata():
  columns = pd.read_csv("https://raw.githubusercontent.com/edgi-govdata-archiving/ECHO-SDWA/main/2021_EJSCREEEN_columns-explained.csv")
  return columns
columns = get_metadata()
columns = columns.loc[columns["GDB Fieldname"].isin(ej_parameters)][["GDB Fieldname", "Description"]]
columns.set_index("Description", inplace = True)
ej_dict = columns.to_dict()['GDB Fieldname']
ej_options = {k:v for k,v in ej_dict.items() if v in socecon} # socioeconomic measures
ej_options = ej_options.keys() # list of EJScreen variables that will be selected (% low income: LOWINCPCT, e.g.)
env_options = {k:v for k,v in ej_dict.items() if v in env} # socioeconomic measures
env_options = env_options.keys() # list of EJScreen variables that will be selected
ej_dict = {v: k for k, v in ej_dict.items()} # to replace "behind the scenes" variable names later

# Load and join census data
with st.spinner(text="Loading data..."):
  census_data = add_spatial_data(url="https://www2.census.gov/geo/tiger/TIGER2017/BG/tl_2017_34_bg.zip", name="census") #, projection=4269
  ej_data = pd.read_csv("https://github.com/edgi-govdata-archiving/ECHO-SDWA/raw/main/EJSCREEN_2021_StateRankings_NJ.csv") # NJ specific
  ej_data["ID"] = ej_data["ID"].astype(str) # set the Census id as a string
  census_data.set_index("GEOID", inplace=True) # set it to the index in the Census data
  ej_data.set_index("ID", inplace=True) # set the Census id to the index in the EJScreen data
  census_data = census_data.join(ej_data) # join based on this shared id
  census_data = census_data[[i for i in ej_parameters] + ["geometry"]] # Filter out unnecessary columns
  census_data[[i for i in ej_parameters]] = round(census_data[[i for i in ej_parameters]] * 100, 2) # Convert decimal values to percentages and then stringify to add % symbol
  census_data[[i for i in ej_parameters]] = census_data[[i for i in ej_parameters]].astype(str) + "%"
  census_data.rename(columns = ej_dict, inplace=True) # replace column names like "MINORPCT" with "% people of color"
  ej_dict = {v: k for k, v in ej_dict.items()} # re-reverse the key/value dictionary mapping for later use

# Convert box
with st.spinner(text="Loading data..."):
  try:
    location = geopandas.GeoDataFrame.from_features(st.session_state["box"]) # Try loading the active box area
  except:
    st.error("### Error: Please start on the 'Welcome' page.")
    st.stop()

# Filter to area
if st.session_state["these_psa"].empty: # If there are no PSA to work with
  bgs = census_data[census_data.geometry.intersects(location.geometry[0])] # Block groups in the area around the clicked point
else: # If there are PSA to work with
  within = census_data.sindex.query(st.session_state["these_psa"].geometry, predicate="intersects")
  bgs = census_data.iloc[list(set(within[1]))] # Block groups in the PSAs

bg_data = bgs
# Set bounds to drawn area
x1,y1,x2,y2 = location.geometry.total_bounds
bounds = [[y1, x1], [y2, x2]]
# bgs back to features
bgs = json.loads(bgs.to_json())

# Streamlit section
# Map
def main():
  if "bgs" not in st.session_state:
    st.session_state["bgs"] = bgs
  if "ejvar" not in st.session_state:
    st.session_state["ejvar"] = None
  if "violations_markers" not in st.session_state:
    st.session_state["violations_markers"] = []
    
  c1 = st.container()

  with c1:
    col1, col2 = st.columns(2)
    map_and_colorbar_widths = 500
    
    with col1:
      st.markdown("**Select a socio-economic measure:**")
      ejdesc = st.selectbox(
        label = "Which socioeconomic measure do you want to explore?",
        options = ej_options,
        label_visibility = "hidden"
      )
      ejvar = ej_dict[ejdesc] # Get the selected variable's behind the scenes name e.g. MINORPCT

      st.markdown("**EPA defines this as:**")
      st.markdown(ejdefs[ejvar]) # Look up the selected variable's definition based on its behind the scenes name

      with st.spinner(text="Loading interactive map..."):
        m = folium.Map(tiles="cartodb positron")
        m.fit_bounds(bounds)
        colorscale = branca.colormap.linear.Greens_05.scale(bg_data[ejdesc].str.strip("%").astype(float).min(), bg_data[ejdesc].str.strip("%").astype(float).max()) # 0 - 1?
        colorscale.width = map_and_colorbar_widths
        st.write(colorscale)
        def style(feature):
          # choropleth approach
          # set colorscale
          return "#d3d3d3" if feature["properties"][ejdesc] is None else colorscale(float(feature["properties"][ejdesc].strip("%")))

        prettier_map_labels = ejdesc + ":&nbsp" # Adds a space between the field name and value
        blockgroups = folium.GeoJson(
          bgs,
          style_function = lambda bg: {"fillColor": style(bg), "fillOpacity": .75, "weight": 1, "color": "white"},
          popup=folium.GeoJsonPopup(fields=[ejdesc], aliases=[prettier_map_labels])
        ).add_to(m)
        if st.session_state["these_psa"].empty:
          pass
        else:
          psas = folium.GeoJson(
            st.session_state["these_psa"],
            style_function = lambda bg: {"fill": None, "weight": 2, "color": "black"},
            tooltip=folium.GeoJsonTooltip(fields=['SYS_NAME', 'AGENCY_URL'])
          ).add_to(m) 
        mc = FastMarkerCluster("", showCoverageOnHover = False, removeOutsideVisibleBounds = True, icon_create_function="""
        function (cluster) {
          return L.divIcon({ html: "<span style='border-radius:50%; border:solid #3388ff 1px;padding:5px 10px 5px 10px; background-color:#3388ff; color:white;'>" + cluster.getChildCount() + "</span>", className: 'mycluster' });
        }
        """)
        for marker in st.session_state["violations_markers"]:
          mc.add_child(marker)
        mc.add_to(m)

        out = st_folium(
          m,
          width = map_and_colorbar_widths,
          returned_objects=[]
        )

    with col2:
      st.markdown("**Select an environmental measure:**")
      envdesc = st.selectbox(
        label = "Which environmental indicator do you want to explore?",
        options = env_options,
        label_visibility = "hidden"
      )
      ejvar = ej_dict[envdesc] # Get the selected variable's behind the scenes name e.g. MINORPCT

      st.markdown("**EPA defines this as:**")
      st.markdown(ejdefs[ejvar]) # Look up the selected variable's definition based on its behind the scenes name

      with st.spinner(text="Loading interactive map..."):
        m = folium.Map(tiles="cartodb positron")
        m.fit_bounds(bounds)
        colorscale = branca.colormap.linear.Blues_05.scale(bg_data[envdesc].str.strip("%").astype(float).min(), bg_data[envdesc].str.strip("%").astype(float).max()) # 0 - 1?
        colorscale.width = map_and_colorbar_widths
        st.write(colorscale)
        def style(feature):
          # choropleth approach
          # set colorscale
          return "#d3d3d3" if feature["properties"][envdesc] is None else colorscale(float(feature["properties"][envdesc].strip("%")))

        prettier_map_labels = envdesc + ":&nbsp" # Adds a space between the field name and value
        blockgroups = folium.GeoJson(
          bgs,
          style_function = lambda bg: {"fillColor": style(bg), "fillOpacity": .75, "weight": 1, "color": "white"},
          popup=folium.GeoJsonPopup(fields=[envdesc], aliases=[prettier_map_labels])
        ).add_to(m)
        if st.session_state["these_psa"].empty:
          pass
        else:
          psas = folium.GeoJson(
            st.session_state["these_psa"],
            style_function = lambda bg: {"fill": None, "weight": 2, "color": "black"},
            tooltip=folium.GeoJsonTooltip(fields=['SYS_NAME', 'AGENCY_URL'])
          ).add_to(m) 
        mc = FastMarkerCluster("", icon_create_function="""
        function (cluster) {
          return L.divIcon({ html: "<span style='border-radius:50%; border:solid #3388ff 1px;padding:5px 10px 5px 10px; background-color:#3388ff; color:white;'>" + cluster.getChildCount() + "</span>", className: 'mycluster' });
        }
        """)
        for marker in st.session_state["violations_markers"]:
          mc.add_child(marker)
        mc.add_to(m)

        out = st_folium(
          m,
          width = map_and_colorbar_widths,
          returned_objects=[]
        )
        
  st.markdown("""
    ### Map Legend

    | Feature | What it means |
    |------|---------------|
    | Circle redness | Number of drinking water violations since 2001 - the darker the shade of red, the more violations |
    | Blue circle with white number | There are multiple facilities with violations in this area |
    | Black outlines | Boundaries of Purveyor Service Areas |    
  """)
      
  st.caption("Source for definitions of environmental justice indicators: [socioeconomic](https://www.epa.gov/ejscreen/overview-socioeconomic-indicators-ejscreen) | [environmental](https://www.epa.gov/ejscreen/overview-environmental-indicators-ejscreen)")
  st.markdown(":arrow_right: What assumptions are built into EPA's choices and definitions of environmental justice indicators?")

  # Download Data Button
  st.download_button(
    "Download this page's data",
    bg_data.to_csv(),
    "selected_area_ej_measures.csv",
    "text/csv",
    key='download-csv'
  )

if __name__ == "__main__":
  main()

next = st.button("Next: Lead Service Lines")
if next:
    switch_page("lead service lines")
