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

st.markdown("""
  On this page, you can explore the pollutants that industrial facilities reported releasing into the watershed in 2022 in your selected area.
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
    location = geopandas.GeoDataFrame.from_features([st.session_state["last_active_drawing"]])
    b = location.geometry.total_bounds
  except:
    st.error("### Error: Did you forget to start on the 'Statewide Overview' page and/or draw a box on the 'SDWA Violations' page?")
    st.stop()
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

  # Set new bounds
  watersheds['geometry'] = geopandas.GeoSeries.from_wkb(watersheds['wkb_geometry'])
  watersheds.drop("wkb_geometry", axis=1, inplace=True)
  watersheds = geopandas.GeoDataFrame(watersheds, crs=4269)
  x1,y1,x2,y2 = watersheds.geometry.total_bounds
  bounds = [[y1, x1], [y2, x2]]
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
  if "markers" not in st.session_state:
    st.session_state["markers"] = []
  if "last_active_drawing" not in st.session_state:
    st.session_state["last_active_drawing"] = None
  if "echo" not in st.session_state:
    st.session_state["echo"] = []
  
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
      list(top_pollutants.index),
      label_visibility = "hidden"
    )

  with c3:
    st.markdown("""
      The map below shows the watersheds for the place you selected and the industrial facilities within those watersheds that reported releasing the selected pollutant.""")
    with st.spinner(text="Loading interactive map..."):
      m = folium.Map(tiles = "cartodb positron")
      
      #Set watershed
      geo_j = folium.GeoJson(st.session_state["last_active_drawing"])
      geo_j.add_to(m)
      gj = folium.GeoJson(
        watersheds,
        style_function = lambda sa: {"fillColor": "#C1E2DB", "fillOpacity": .75, "weight": 1},
        popup=folium.GeoJsonPopup(fields=['huc12'])
        ).add_to(m)

      # Set facility markers
      filtered_data = dmr.loc[dmr["PARAMETER_DESC"] == pollutant]
      filtered_data = filtered_data.drop_duplicates(subset="EXTERNAL_PERMIT_NMBR")
      markers = [folium.CircleMarker(location=[mark["FAC_LAT"], mark["FAC_LONG"]], 
      popup=f"{mark.FAC_NAME}",
      radius = 6, fill_color = "orange", weight=1
      ) for index,mark in filtered_data.iterrows() if not pd.isna(mark["FAC_LAT"])]
      for marker in markers:
        m.add_child(marker)

      m.fit_bounds(bounds)

      out = st_folium(
        m,
        returned_objects=[]
      )

      #st.dataframe(top_pollutors.loc[pollutant].sort_values(by="values", ascending=False))
      units = list(top_pollutors.loc[pollutant].reset_index()['STANDARD_UNIT_DESC'].unique()) # the different units this pollutant is measured in
      st.altair_chart(
        alt.Chart(top_pollutors.loc[pollutant].reset_index(), title = 'Amount of '+pollutant+' reported released in 2022 by facilities in selected watersheds').mark_bar().encode(
          x = alt.X("values", title = "Amount of "+pollutant+" measured as "+', '.join(units)),
          y = alt.Y('FAC_NAME', axis=alt.Axis(labelLimit = 500), title=None).sort('-x') # Sort horizontal bar chart
        ),
      use_container_width=True
      )

    st.markdown(":face_with_monocle: What is the impact of these different pollutants? What are the possible impacts at different amounts in drinking water? You can learn more about some pollutants in EPA's [IRIS (Integrated Risk Information System) database](https://iris.epa.gov/AtoZ/?list_type=alpha).")

  with c1:
    st.markdown("""
      ### Most Frequently Reported Pollutants in Watershed(s) in Selected Area
      """)
  
    # st.dataframe(top_pollutants)
    #top_pollutants = 
    st.altair_chart(
      alt.Chart(top_pollutants.rename_axis('Pollutant').reset_index(), title = 'Number of Facilities Reporting Specific Pollutants in Selected Area').mark_bar().encode(
        x = alt.X("# of facilities", title = "Number of facilities reporting pollutant in selected area"),
        y = alt.Y('Pollutant', axis=alt.Axis(labelLimit = 500), title=None).sort('-x')
      ),
     use_container_width=True
    )
    #st.bar_chart(top_pollutants)

if __name__ == "__main__":
  main()