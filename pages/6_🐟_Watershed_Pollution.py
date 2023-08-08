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

st.set_page_config(layout="wide", page_title="🐟 Watershed Pollution")

previous = st.button("Previous: Lead Service Lines")
if previous:
    switch_page("lead service lines")

st.markdown("""
  # What Pollutants are Allowed to be Released in the Watershed(s) in the Selected Area?""")

st.caption("""
  Remember: if you want to change the boundaries of the selected area, you can always go back to the 
"Statewide Violations" page and do so, then return here.
""")

redraw = st.button("< Return to SDWA Violations to change selected area")
if redraw:
    switch_page("SDWA Violations")

st.markdown("On this page, you can explore the pollutants that industrial facilities reported releasing into the watershed in 2022 in your selected area.")

st.caption("""          
  :face_with_monocle: Where does this data come from? When facilities receive permits to release certain effluents, often they are required to file "discharge monitoring reports"— so this data is from facilities reporting their own discharge. [Wikipedia](https://en.wikipedia.org/wiki/Discharge_Monitoring_Report) has a good introduction to the concept.
            
  :arrow_right: This data only includes the pollutants that are reported by a facility discharging into the water. Pollutants can also end up in the water from the air, from polluters operating below permit-requiring levels, and lots of other ways (can you think of more?) One way to learn more about what is in the water is with EPA's [How's My Waterway tool](https://mywaterway.epa.gov/), which shows the status of local waterways based on monitoring.
""")
            
@st.cache_data
def get_data(query):
  try:
    url= 'https://portal.gss.stonybrook.edu/echoepa/?query='
    data_location = url + urllib.parse.quote_plus(query) + '&pg'
    data = pd.read_csv(data_location, encoding='iso-8859-1', dtype={"REGISTRY_ID": "Int64", "huc12": str})
    return data
  except:
    print("Sorry, can't get data")

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
  sql = """
  SELECT * FROM "wbdhu12" WHERE ST_INTERSECTS(ST_GeomFromText('POLYGON(({} {}, {} {}, {} {}, {} {}, {} {}))', 4269), "wbdhu12"."wkb_geometry");
  """.format(b[0], b[1], 
    b[0], b[3], 
    b[2], b[3], 
    b[2], b[1], 
    b[0], b[1])
  watersheds = get_data(sql)
  for i,w in watersheds.iterrows():
    if len(str(w["huc12"]))<12:
      w["huc12"] = "0"+str(w["huc12"])
  watersheds['geometry'] = geopandas.GeoSeries.from_wkb(watersheds['wkb_geometry'])
  watersheds.drop("wkb_geometry", axis=1, inplace=True)
  watersheds = geopandas.GeoDataFrame(watersheds, crs=4269)
  # Save data for later
  watershed_data = watersheds
  # Get watershed ids
  w = list(watersheds["huc12"].unique())
  ids  = ""
  for i in w:
    ids += "'"+str(i)+"',"
  ids = ids[:-1] 
  # Convert to features
  watersheds = json.loads(watersheds.to_json())

  # Get ECHO facilities within watersheds
  sql = """
  SELECT "ECHO_EXPORTER".* FROM "ECHO_EXPORTER","wbdhu12" WHERE 
  ST_WITHIN("ECHO_EXPORTER"."wkb_geometry", "wbdhu12"."wkb_geometry") AND "wbdhu12"."huc12" in ({})  AND "ECHO_EXPORTER"."NPDES_FLAG" = \'Y\';
  """.format(ids)
  echo = get_data(sql)
  echo['geometry'] = geopandas.GeoSeries.from_wkb(echo['wkb_geometry'])
  echo.drop("wkb_geometry", axis=1, inplace=True)
  echo = geopandas.GeoDataFrame(echo, crs=4269)
  echo.set_index("REGISTRY_ID", inplace=True)

  # Get discharge data based on watershed ids
  sql = 'select * from "DMR_FY2022_MVIEW" where "FAC_DERIVED_WBD" in ({})'.format(ids) 
  dmr = get_data(sql)

  top_pollutants = dmr.groupby(['PARAMETER_DESC'])[["FAC_NAME"]].nunique()
  top_pollutants = top_pollutants.rename(columns={"FAC_NAME": "# of facilities"})
  top_pollutants = top_pollutants.sort_values(by="# of facilities", ascending=False)

  top_pollutors = dmr.groupby(['PARAMETER_DESC', 'FAC_NAME', 'STANDARD_UNIT_DESC'])[["DMR_VALUE_STANDARD_UNITS"]].sum()
  top_pollutors = top_pollutors.rename(columns={"STANDARD_UNIT_DESC": "units", "DMR_VALUE_STANDARD_UNITS": "values"})

# Streamlit section
# Map
def main():
  
  c1 = st.container()
  c2 = st.container()
  c3 = st.container()
  
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

  with c2:
    st.markdown("""
      ### Analyze by pollutant
      Use the dropdown menu to select different pollutants and see how *much* of that pollutant reporting facilities said they discharged.
                """)
    pollutant = st.selectbox(
      "Select a pollutant...",
      list(top_pollutants.index),
      label_visibility = "hidden"
    )

  with c3:
    st.markdown("""
      The map below shows the watersheds for the place you selected and the industrial facilities within those watersheds that reported releasing the selected pollutant.""")
    col1, col2 = st.columns(2) 
    with col1:
      with st.spinner(text="Loading interactive map..."):
        m = folium.Map(tiles = "cartodb positron")
        
        #Set watershed
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
  
                  
      :face_with_monocle: What are the industry codes in the popup (NAICS, SIC)? These numbers can be looked up to get a sense of what that business does. [More information.](https://www.dnb.com/resources/sic-naics-industry-codes.html)
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
