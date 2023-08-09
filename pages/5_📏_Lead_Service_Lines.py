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
import altair as alt
import json
import requests, zipfile, io

st.set_page_config(layout="wide", page_title="📏 Lead Service Lines")

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

  A lead service line is a pipe that goes from the utility's main to a house and is made of lead. On this page, we map out the "Purveyor Service Areas" in the area you have selected. Then, we show how many lead service lines these utilities have reported within their service areas.
  
  There is no known safe amount of lead exposure, so
  lead service lines may pose a risk to residents' well-being. 

  """)

# Load and join lead/service area data
with st.spinner(text="Loading data..."):
  # Convert st.session_state["last_active_drawing"]
  try:
    service_areas = st.session_state["these_psa"]
    location = geopandas.GeoDataFrame.from_features(st.session_state["box"]) # Try loading the active box area
  except:
    st.error("### Error: Please start on the 'Welcome' page.")
    st.stop() 
  # Filter to area
  sas = service_areas[service_areas.geometry.intersects(location.geometry[0])] # Service areas in the place
  # Get lead data
  lead = pd.read_csv("https://raw.githubusercontent.com/edgi-govdata-archiving/ECHO-SDWA/main/nj_leadlines.csv", 
    dtype={"Measurement (service lines)": int}) # This is a CSV created by collating the results from the above link
  lead.rename(columns={"Measurement (service lines)":"Number of lead service lines in area", "size": "System Size"}, inplace=True)
  lead = sas.join(lead.set_index("PWSID"))
  lead.set_index("SYS_NAME", inplace=True)
  # Set bounds
  x1,y1,x2,y2 = location.geometry.total_bounds
  bounds = [[y1, x1], [y2, x2]]
  # Save data for later
  lead_data = lead
  # Back to features
  lead = json.loads(lead.to_json())

# Streamlit section
# Map
def main():
  if "violations_markers" not in st.session_state:
    st.session_state["violations_markers"] = []

  c1 = st.container()
  c2 = st.container()

  if lead_data.empty:
    with c1:
      st.error("### There are no purveyor service areas required to count lead service lines in this area.")
      st.stop()

  with c1:
    st.markdown("""
      ## Map of Purveyor Service Areas in Selected Area
      
      According to the [New Jersey Department of Environmental Protection](https://geo.btaa.org/catalog/00e7ff046ddb4302abe7b49b2ddee07e_13),

      > Public Community Water Purveyors are systems that pipe water for human consumption to at least 15 service connections used year-round, or one that regularly serves at least 25 year-round residents. Public purveyors can be government agencies, private companies, or quasi-government groups. The boundaries mapped are those of the actual water delivery or service area. Franchise areas are not depicted (areas with legal rights for future service once developed). Water sources (wells or surface water intakes) are often located outside the delivery area boundaries.          
      
      The map below shows Purveyor Service Areas colored by the number of lead service lines reported in that area. The darker the shade of blue, the more lead service lines are reported.
    """)
    col1, col2 = st.columns(2)
    with col1:
      with st.spinner(text="Loading interactive map..."):
        colorscale = branca.colormap.linear.Blues_05.scale(lead_data["Number of lead service lines in area"].min(), lead_data["Number of lead service lines in area"].max())
        colorscale.width=500
        m = folium.Map(tiles="cartodb positron")
        m.fit_bounds(bounds)
        def style(feature):
          # choropleth approach
          # set colorscale
          return "#d3d3d3" if feature["properties"]["Number of lead service lines in area"] is None else colorscale(feature["properties"]["Number of lead service lines in area"])

        # Add PSA service areas
        gj = folium.GeoJson(
          lead,
          style_function = lambda sa: {"fillColor": style(sa), "fillOpacity": .75, "weight": 2, "color": "black"},
          popup=folium.GeoJsonPopup(fields=['Utility', "Number of lead service lines in area", "System Size"])
          ).add_to(m)

        out = st_folium(
          m,
          width = 500,
          returned_objects=[]
        )

      with col2:
        st.markdown("""
          ### Color Scale
          Number of lead service lines in area
          """)
        
        st.write(colorscale)
        
        st.markdown("""
          ### Map Legend

          | Feature | What it means |
          |------|---------------|
          | Black outlines | Purveyor Service Area boundaries | 
                    
          ### System Size Definitions
          | Size Classification | Population Range Served |
          |------|---------------|
          | Very Small | 500 or less |
          | Small | 501 - 3,300 |
          | Medium | 3,301 - 10,000 |
          | Large | 10,001 - 100,00 |
          | Very Large | Greater than 100,000 |  
        """)

  with c2:
    st.markdown("""
                # Count of Lead Service Lines in Purveyor Service Areas

                Number of lead service lines reported in the Purveyor Service Areas that overlap with the selected area:
                """)
    counts = lead_data.sort_values(by=["Number of lead service lines in area"], ascending=False)[["Number of lead service lines in area"]]
    counts = counts.rename_axis('System Name') # Rename SYS_NAME to be pretty
    counts = counts.reset_index() # prepare the table for charting
    col3, col4 = st.columns(2)
    with col3:
      st.altair_chart(
        alt.Chart(counts, title = 'Number of Lead Service Lines per Purveyor Service Area in Selected Area').mark_bar().encode(
          x = alt.X("Number of lead service lines in area", title = "Number of lead service lines in system"),
          y = alt.Y('System Name', axis=alt.Axis(labelLimit = 500), title=None).sort('-x') # Sort horizontal bar chart
        ),
      use_container_width=True
      )
    with col4:
      st.dataframe(counts) # show table

  st.caption("""
    Data compiled from [https://www.njwatercheck.com/BenchmarkHub](https://www.njwatercheck.com/BenchmarkHub)
  """)
  
  st.markdown("""
      ### :face_with_monocle: How should we understand these numbers?
      This data is difficult to present in a way that's easy to intuitively grasp, because although the database gives us the *number* of lead service lines, it doesn't help us understand *who is impacted* or *how likely a given tap in that water system is* to have some lead in the water.
      
      A lead service line is a lead water line that goes from the city's main to someone's house. We could present the number of lead lines as a percentage of total lines, but that could be misleading, because we don't know how many people are served by each line. For instance, if you had 2,000 lead lines and served a population of 40,000, the "raw" percentage would be 5%, but that assumes each person has their own service line, lead or otherwise. In reality, it is households/buildings that receive service lines, and these may serve 0 to 100s of people. In theory, those 2,000 lead lines could serve all 40,000 residents - but we just don't have that granular level of information. There may also be inaccuracies or imprecision in the measure of the population served (e.g. do children count? When was the last census? How was the count conducted? Are there populations that are likely to have been left out?)

      :arrow_right: How might this kind of data imprecision intersect with environmental justice? For example, are there demographics that are more likely to have more people in a given household? Is there any way to tell if those same demographics are more or less likely than other parts of the population to have lead service lines?
              
      :arrow_right: In some selected areas, you may see that some Public Water Systems report "0" and others fail to report ("None" in the table). These are not the same! "None" means that the report is missing. We don't know how many lead service lines there are in that area. Notice that these water systems are missing from the graph. What might be a good way to visualize this missing data?
    """)

  # Download Data Button
  st.download_button(
    "Download this page's data",
    lead_data.to_csv(),
    "selected_area_leadlines.csv",
    "text/csv",
    key='download-csv'
  )

if __name__ == "__main__":
  main()

next = st.button("Next: Watershed Pollution")
if next:
    switch_page("watershed pollution")
