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
import altair as alt
import json
import requests, zipfile, io

st.set_page_config(layout="wide", page_title="🐟 Watershed Pollution")

previous = st.button("Previous: Lead Service Lines")
if previous:
    st.switch_page("pages/5_📏_Lead_Service_Lines.py")

st.markdown("""
  # What Pollutants are Allowed to be Released in the Watershed(s) in the Selected Area?""")

st.caption("""
  Remember: if you want to change the boundaries of the selected area, you can always go back to the 
"Find Public Water Systems" page and do so, then return here.
""")

redraw = st.button("< Return to Find Public Water Systems to change selected area")
if redraw:
    st.switch_page("pages/2_💧_Find_Public_Water_Systems.py")

st.markdown("On this page, you can explore the pollutants that industrial facilities reported releasing into the watershed in 2022 in your selected area.")

st.caption("""          
  :face_with_monocle: Where does this data come from? When facilities receive permits to release certain effluents, often they are required to file "discharge monitoring reports"— so this data is from facilities reporting their own discharge. [Wikipedia](https://en.wikipedia.org/wiki/Discharge_Monitoring_Report) has a good introduction to the concept.
            
  :arrow_right: This data only includes the pollutants that are reported by a facility discharging into the water. Pollutants can also end up in the water from the air, from polluters operating below permit-requiring levels, and lots of other ways (can you think of more?) One way to learn more about what is in the water is with EPA's [How's My Waterway tool](https://mywaterway.epa.gov/), which shows the status of local waterways based on monitoring.
""")

import requests
import json

@st.cache_data
def query_paginated_features(service_url, layer_id, where_clause="1=1", out_fields="*", page_size=None, distinct=False):
    """
    Queries an ArcGIS Feature Server layer with pagination.

    Args:
        service_url (str): The base URL of the ArcGIS Feature Service.
        layer_id (int): The ID of the feature layer to query.
        where_clause (str): The SQL WHERE clause for filtering features.
        out_fields (str): Comma-separated list of fields to return, or "*" for all.
        page_size (int, optional): The number of records per page. If None,
                                   it tries to determine maxRecordCount from service.

    Returns:
        list: A list of all features retrieved from the layer.
    """
    all_features = []
    current_offset = 0

    # Get maxRecordCount if page_size is not specified
    if page_size is None:
        service_info_url = f"{service_url}/{layer_id}"
        service_info_params = {"f": "json"}
        service_info_response = requests.get(service_info_url, params=service_info_params).json()
        page_size = service_info_response.get("maxRecordCount", 1000) # Default to 1000 if not found

    while True:
        query_params = {
            "where": where_clause,
            "outFields": out_fields,
            "resultOffset": current_offset,
            "resultRecordCount": page_size,
            "return_distinct_values": distinct,
            "f": "json",
            "returnGeometry": "false" # Set to true if you need geometry
        }
        query_url = f"{service_url}/{layer_id}/query"
        response = requests.get(query_url, params=query_params).json()

        if "features" in response:
            all_features.extend(response["features"])

        if not response.get("exceededTransferLimit"):
            break  # No more pages

        current_offset += page_size

    return all_features

@st.cache_data
def get_dmrs(wids):
  """
  Queries an ArcGIS Feature Server to find HUC12 watersheds intersecting with a given bounding box.

  The script targets the Watershed Boundary Dataset (WBD) map service.

  Args:
      bounds (list): A list of two points [[y1, x1], [y2, x2]] defining the bounding box,
                     where 'y' is latitude and 'x' is longitude.

  Returns:
      dict: A dictionary parsed from the JSON response containing the intersecting features,
            or None if an error occurs.
  """
  # The ArcGIS REST API endpoint for querying the HUC12 layer.
  # Layer '6' corresponds to HUC12 watersheds.
  url = "https://services.arcgis.com/EXyRv0dqed53BmG2/ArcGIS/rest/services/New_Jersey_DMRs_2022/FeatureServer/1/query"

  list_of_ids=""
  for i in wids:
    list_of_ids+=f"'{i}',"
  list_of_ids=list_of_ids[:-1]

  # Define the parameters for the GET request according to the ArcGIS REST API documentation.
  params = {
      'where': f'FAC_DERIVED_WBD in ({list_of_ids})',
      'outFields': '*',  # Return all available attribute fields
      'returnGeometry': 'true', # Include the geometry of the features in the response
      'f': 'geojson' # Specify the response format as JSON
  }

  try:
    # Send the GET request to the server
    response = requests.get(url, params=params)
    # Raise an HTTPError for bad responses (4xx or 5xx)
    response.raise_for_status()
    
    # Parse the JSON response and return it
    return response.json()

  except requests.exceptions.RequestException as e:
    print(f"An error occurred while making the request: {e}")
    return None
  except json.JSONDecodeError:
    print("Failed to decode the JSON response from the server.")
    return None
  
@st.cache_data
def find_intersecting_huc12(bounds):
  """
  Queries an ArcGIS Feature Server to find HUC12 watersheds intersecting with a given bounding box.

  The script targets the Watershed Boundary Dataset (WBD) map service.

  Args:
      bounds (list): A list of two points [[y1, x1], [y2, x2]] defining the bounding box,
                     where 'y' is latitude and 'x' is longitude.

  Returns:
      dict: A dictionary parsed from the JSON response containing the intersecting features,
            or None if an error occurs.
  """
  # The ArcGIS REST API endpoint for querying the HUC12 layer.
  # Layer '6' corresponds to HUC12 watersheds.
  url = "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/6/query"

  # Extract coordinates and determine the min/max values for the envelope.
  # The API expects the format xmin, ymin, xmax, ymax.
  y1, x1 = bounds[0]
  y2, x2 = bounds[1]

  xmin = min(x1, x2)
  ymin = min(y1, y2)
  xmax = max(x1, x2)
  ymax = max(y1, y2)

  # Define the parameters for the GET request according to the ArcGIS REST API documentation.
  params = {
      'geometry': f'{xmin},{ymin},{xmax},{ymax}',
      'geometryType': 'esriGeometryEnvelope',
      'inSR': '4326',  # Input spatial reference: WGS 84 (standard lat/lon)
      'spatialRel': 'esriSpatialRelIntersects', # The spatial relationship to find
      'outFields': '*',  # Return all available attribute fields
      'returnGeometry': 'true', # Include the geometry of the features in the response
      'f': 'geojson' # Specify the response format as JSON
  }

  try:
    # Send the GET request to the server
    response = requests.get(url, params=params)
    # Raise an HTTPError for bad responses (4xx or 5xx)
    response.raise_for_status()
    
    # Parse the JSON response and return it
    return response.json()

  except requests.exceptions.RequestException as e:
    print(f"An error occurred while making the request: {e}")
    return None
  except json.JSONDecodeError:
    print("Failed to decode the JSON response from the server.")
    return None
            
import sqlite3
from pathlib import Path
DB_PATH = Path('nj_sdwa.db')
@st.cache_data
def get_data(wids):
  list_of_ids=""
  for i in wids:
    list_of_ids+=f"'{i}',"
  list_of_ids=list_of_ids[:-1]
  query = f'select * from NJ_DMR_2022 where FAC_DERIVED_WBD in ({list_of_ids})'
  with sqlite3.connect(DB_PATH) as conn:
    data = pd.read_sql_query(query, conn)#, encoding='iso-8859-1', dtype={"REGISTRY_ID": "Int64"})
  return data

@st.cache_data
def lookup(wids):
  list_of_ids=""
  for i in wids:
    list_of_ids+=f"'{i}',"
  list_of_ids=list_of_ids[:-1]
  query = f'select * from lookup where FAC_DERIVED_WBD in ({list_of_ids})'
  with sqlite3.connect(DB_PATH) as conn:
    data = pd.read_sql_query(query, conn)#, encoding='iso-8859-1', dtype={"REGISTRY_ID": "Int64"})
  return data

# Load watershed data based on intersection
with st.spinner(text="Loading data..."):
  # Get bounds of shape
  try:
    location = geopandas.GeoDataFrame.from_features(st.session_state["box"]) # Try loading the active box area
  except:
    st.error("### Error: Please start on the 'Welcome' page.")
    st.stop()
  # Set bounds
  if st.session_state["these_psa"].empty: # If there are no PSA to work with
    location = location
  else: # If there are PSA to work with
    location = st.session_state["these_psa"]
  b = location.geometry.total_bounds
  x1,y1,x2,y2 = location.geometry.total_bounds
  bounds = [[y1, x1], [y2, x2]]
  # Get watershed boundary
  watersheds_features = find_intersecting_huc12(bounds)
  
  
  # Create the GeoDataFrame from the parsed attributes and geometries.
  watersheds = geopandas.GeoDataFrame.from_features(watersheds_features, crs=4326)
  watersheds.to_crs(4326, inplace=True) # Project data

  within = watersheds.sindex.query(location.geometry, predicate="intersects")
  watersheds = watersheds.iloc[list(set(within[1]))]
  # Create GeoDataFrame
  # Convert the Esri JSON features to a format suitable for GeoPandas
  # This involves creating a Shapely geometry object from the geometry dictionary
  #watersheds = geopandas.GeoDataFrame.from_features(watersheds, crs="EPSG:4326")
  #st.write("WATERSHEDS")
  #st.write(watersheds)
  #for i,w in watersheds.iterrows():
  #  if len(str(w["huc12"]))<12:
  #    w["huc12"] = "0"+str(w["huc12"])
  #watersheds['geometry'] = geopandas.GeoSeries.from_wkb(watersheds['wkb_geometry'])
  #watersheds.drop("wkb_geometry", axis=1, inplace=True)
  #watersheds = geopandas.GeoDataFrame(watersheds, crs=4269)
  # Save data for later
  watershed_data = watersheds
  # Get watershed ids
  wids = list(watersheds["huc12"].unique())
  # Convert to features
  watersheds = json.loads(watersheds.to_json())

  # Get discharge data based on watershed ids
  #sql = 'select * from "DMR_FY2022_MVIEW" where "FAC_DERIVED_WBD" in ({})'.format(ids) 
  url = "https://services.arcgis.com/EXyRv0dqed53BmG2/ArcGIS/rest/services/New_Jersey_DMRs_2022/FeatureServer/"

  list_of_ids=""
  for i in wids:
    list_of_ids+=f"'{i}',"
  list_of_ids=list_of_ids[:-1]

  # Get parameters to select from 
  #where = f'FAC_DERIVED_WBD in ({list_of_ids})'
  #chems = query_paginated_features(service_url=url, layer_id=1, out_fields='PARAMETER_DESC', where_clause=where, page_size=2000, distinct=True)
  
  widslist = [str(w) for w in wids]
  chems = lookup(wids)
  #st.dataframe(chems)

 

# Streamlit section
# Map
def main():
  
  c1 = st.container()
  c2 = st.container()
  c3 = st.container()
  


  with c2:
    st.markdown("""
      ### Analyze by pollutant
      Use the dropdown menu to select different pollutants and see how *much* of that pollutant reporting facilities said they discharged.
                """)
    pollutant = st.selectbox(
      "Select a pollutant...",
      list(chems["PARAMETER_DESC"].unique()),
      label_visibility = "hidden"
    )

    # Get DMRs
    where = f'FAC_DERIVED_WBD in ({list_of_ids}) and PARAMETER_DESC = \'{pollutant}\''
    dmr = query_paginated_features(service_url=url, layer_id=1, where_clause=where, page_size=2000, distinct=False)
    dmr = [d["attributes"] for d in dmr]
    dmr = pd.DataFrame(dmr)
    #st.dataframe(dmr)
    
    top_pollutants = chems.groupby(['PARAMETER_DESC'])[["EXTERNAL_PERMIT_NMBR"]].sum()
    top_pollutants = top_pollutants.rename(columns={"EXTERNAL_PERMIT_NMBR": "# of facilities"})
    top_pollutants = top_pollutants.sort_values(by="# of facilities", ascending=False)

    top_pollutors = dmr.groupby(['PARAMETER_DESC', 'FAC_NAME', 'STANDARD_UNIT_DESC'])[["DMR_VALUE_STANDARD_UNITS"]].sum()
    top_pollutors = top_pollutors.rename(columns={"STANDARD_UNIT_DESC": "units", "DMR_VALUE_STANDARD_UNITS": "values"})

  with c1:
    st.markdown("""
      ### Most Frequently Reported Pollutants in Watershed(s) in Selected Area
      """)
  
    st.altair_chart(
      alt.Chart(top_pollutants.rename_axis('Pollutant').reset_index(), title = 'Number of Facilities Reporting Specific Pollutants in Selected Area').mark_bar().encode(
        x = alt.X("# of facilities", title = "Number of facilities reporting pollutant in selected area"),
        y = alt.Y('Pollutant', axis=alt.Axis(labelLimit = 500), title=None).sort('-x')
      ),
     use_container_width=True
    )

  with c3:
    st.markdown("""
      The map below shows the watersheds for the place you selected and the industrial facilities within those watersheds that reported releasing the selected pollutant.""")
    col1, col2 = st.columns(2) 
    with col1:
      with st.spinner(text="Loading interactive map..."):
        m = folium.Map(tiles = "cartodb positron")
        
        #Set watershed
        #st.write(watersheds)
        w = folium.GeoJson(
          watersheds,
          style_function = lambda sa: {"fillColor": "#C1E2DB", "fillOpacity": .75, "weight": 1, "color": "white"}
          ).add_to(m)
        if st.session_state["these_psa"].empty:
          pass
        else:
          psas = folium.GeoJson(
            st.session_state["these_psa"],
            style_function = lambda bg: {"fill": None, "weight": 2, "color": "black"},
            tooltip=folium.GeoJsonTooltip(fields=['SYS_NAME', 'AGENCY_URL'])
          ).add_to(m) 
        # Set facility markers
        filtered_data = dmr.loc[dmr["PARAMETER_DESC"] == pollutant]
        context = filtered_data[["EXTERNAL_PERMIT_NMBR", "FAC_LAT", "FAC_LONG", "FAC_NAME", "FAC_SIC_CODES", "FAC_NAICS_CODES"]]
        context.set_index("EXTERNAL_PERMIT_NMBR", inplace = True)
        filtered_data = filtered_data.groupby(by=["EXTERNAL_PERMIT_NMBR"])[["EXTERNAL_PERMIT_NMBR"]].count().rename(columns={"EXTERNAL_PERMIT_NMBR": "COUNT"}) # Group data
        filtered_data = context.join(filtered_data).reset_index().drop_duplicates(subset=["EXTERNAL_PERMIT_NMBR"])
        filtered_data['quantile'] = pd.qcut(filtered_data["COUNT"], 4, labels=False, duplicates="drop")
        scale = {0: 8,1:12, 2: 16, 3: 24} # First quartile = size 8 circles, etc.
        #st.dataframe(filtered_data)
        markers = [folium.CircleMarker(location=[mark["FAC_LAT"], mark["FAC_LONG"]], 
          popup =folium.Popup(mark["FAC_NAME"] + "<br><b>Reports of "+pollutant+" in 2022: </b>"+str(mark["COUNT"])+"<br><b>Industry codes (NAICS, SICS): </b>"+str(mark["FAC_SIC_CODES"])+"/"+str(mark["FAC_NAICS_CODES"])),
          radius = scale[mark["quantile"]], fill_color = "orange", weight=1
          ) for index,mark in filtered_data.iterrows() if not pd.isna(mark["FAC_LAT"])
        ]
        for marker in markers:
          m.add_child(marker)

        m.fit_bounds(bounds)

        out = st_folium(
          m,
          width = 500,
          returned_objects=[]
        )

    with col2:
      st.markdown("""
      ### Map Legend

      | Feature | What it means |
      |------|---------------|
      | Circle size | Number of reports of the selected pollutant in 2022 - the larger the circle, the more reports this facility has made of releasing this pollutant (note that this does not indicate pollutant quantity—see the chart below for that) |
      | Green features | Watershed boundaries |
      | Black outlines | Purveyor Service Area boundaries |
  
                  
      :thinking: What are the industry codes in the popup (NAICS, SIC)? These numbers can be looked up to get a sense of what that business does. [More information.](https://www.dnb.com/resources/sic-naics-industry-codes.html)
    """)
    units = list(top_pollutors.loc[pollutant].reset_index()['STANDARD_UNIT_DESC'].unique()) # the different units this pollutant is measured in
    st.altair_chart(
      alt.Chart(top_pollutors.loc[pollutant].reset_index(), title = 'Amount of '+pollutant+' reported released in 2022 by facilities in selected watersheds').mark_bar().encode(
        x = alt.X("values", title = "Amount of "+pollutant+" measured as "+', '.join(units)),
        y = alt.Y('FAC_NAME', axis=alt.Axis(labelLimit = 500), title=None).sort('-x') # Sort horizontal bar chart
      ),
    use_container_width=True
    )

  st.markdown(":arrow_right: What is the impact of these different pollutants? What are the possible impacts at different amounts in drinking water? You can learn more about some pollutants in EPA's [IRIS (Integrated Risk Information System) database](https://iris.epa.gov/AtoZ/?list_type=alpha).")

  # Download Data Button
  st.download_button(
    "Download this page's data",
    dmr.to_csv(),
    "selected_area_pollutants.csv",
    "text/csv",
    key='download-csv'
  )
if __name__ == "__main__":
  main()
