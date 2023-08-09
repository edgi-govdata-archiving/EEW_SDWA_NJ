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

st.set_page_config(layout="wide", page_title="🌍 Statewide Overview")
#st.markdown('![EEW logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/eew.jpg?raw=true) ![EDGI logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/edgi.png?raw=true)')

previous = st.button("Previous: Welcome")
if previous:
    switch_page("welcome")

st.markdown("""
  # Statewide Overview of Public Water Systems
""")

with st.spinner(text="Loading data..."):
  try:
    markers = st.session_state["statewide_markers"]
    psas = st.session_state["service_areas"]
  except:
    st.error("### Error: Please start on the 'Welcome' page.")
    st.stop()

def main():

  # Streamlit section
  # Map

  c1 = st.container()
  c2 = st.container()
  c3 = st.container()

  with c2:
    
    col1, col2 = st.columns(2)

    @st.cache_data(experimental_allow_widgets=True)
    def make_map(shape):
      m = folium.Map(location = [40.304857, -74.499739], zoom_start = 8, zoom_control=False, scrollWheelZoom=False, dragging=False, tiles="cartodb positron")

      if shape == "psas": 
        # Add polygons representing PSAs
        service_areas = folium.GeoJson(
          psas,
          style_function = lambda sa: {"fillColor": None, "fillOpacity": 0, "weight": 2, "color": "black"},
          tooltip=folium.GeoJsonTooltip(fields=['SYS_NAME'], labels=False),
          popup=folium.GeoJsonPopup(fields=['SYS_NAME', 'AGENCY_URL'], aliases=['Water system:', 'Website:'])
          ).add_to(m)

        out = st_folium(
          m,
          width = 500,
          returned_objects=[]
        )
      else:
        # Add markers representing PWS
        for marker in markers:
          m.add_child(marker)
        out = st_folium(
          m,
          width = 500,
          returned_objects=[]
        )

    with col1:
      with st.spinner(text="Loading interactive map..."):
        make_map("pws")
    with col2:   
      st.markdown("""
        ### Water systems by size, type, and water source
                  
        #### Map Legend

        | Feature | What it means |
        |------|---------------|
        | Circle outline - Solid | PWS that draw from surface water |
        | Circle outline - None | PWS that draw from groundwater |
        | Circle color - Blue | Community Water Systems |
        | Circle color - Yellow | Transient Non-Community Water Systems |
        | Circle color - Green | Non-Transient, Non-Community Water Systems |
        | Circle Size | PWS size, from very small to very large | 
        | Black outlines | Purveyor Service Area boundaries |   
      """)

      st.markdown("""
        ### :face_with_monocle: Why are there PWS shown outside of New Jersey?
        This is an example of data errors in the EPA database. Sometimes, a facility will be listed with a NJ address
        but its latitude and longitude actually correspond to somewhere out of state.

        :arrow_right: What are some implications of a data error like this? How might a misclassification by state or incorrect location impact the regulation of safe drinking water at a facility?
                  
        :arrow_right: Notice that some circles are stacked exactly on top of each other (this looks like, e.g., a small yellow circle inside of a larger green circle inside of a larger blue circle). This means that EPA has listed the headquarters locations of these different water sources in exactly the same place, even though they are often different entities. Is this another data error?
      """)

  with c1:
    st.markdown("## Locations of New Jersey's Public Water Systems")
    st.markdown("""
    Below are two interactive maps of all public water systems in New Jersey. Click on the maps to see more information.
    """)

    col3, col4 = st.columns(2)

    with col3:
      with st.spinner(text="Loading interactive map..."):
        make_map("psas")

    with col4:
      st.markdown("""
                  ### Water system service areas

                  Black outlines on the map to the left show the service areas of all public water systems in New Jersey. Click on the map to see more information about the water system.
                  """)


  with c3:
    st.markdown("## Summary of Public Water Systems by Type, Size, and Source")
    st.markdown("""
      Click through the tabs below to see summaries of New Jersey's water systems based on different EPA categorizations.
    """)

    def chart_category(selected_category):
      data = st.session_state["sdwa"].loc[st.session_state["sdwa"]["FISCAL_YEAR"] == 2021] # This ensures we're only summarizing currently operating facilities and not duplicating them
      counts = data.groupby(by=selected_category)[[selected_category]].count().rename(columns={selected_category:"Number of Facilities"})
      counts.sort_values(by="Number of Facilities",ascending=False, inplace=True) # Sort table by selected_category
      #st.dataframe(counts)
      counts = counts.rename_axis(selected_category).reset_index()
      title = alt.TitleParams("Distribution of New Jersey's Public Water Systems by EPA Code '%s'" %selected_category, anchor='middle')
      st.altair_chart(
        alt.Chart(counts, title=title).mark_bar().encode(
          x = alt.X('Number of Facilities'),
          y = alt.Y(selected_category, axis=alt.Axis(labelLimit = 500), title=None).sort('-x') # Sort horizontal bar chart
        ),
      use_container_width=True
      )

    tab1, tab2, tab3 = st.tabs(["Water System Type (who it serves)", "Water Source (ground vs surface)", "Water System Size"])

    with tab1:
      selected_category = "PWS_TYPE_CODE"
      chart_category(selected_category)
      st.markdown("""
        #### Public Water System (PWS) Type Codes

        | Type | What it means |
        |------|---------------|
        | Community Water System | Provides year-round service to the same set of people, e.g. municipal drinking water |
        | Non-Transient, Non-Community Water System | Services e.g. schools, offices, and hospitals that serve a community but not the same people every day |
        | Transient Non-Community Water Systems | Services e.g. gas stations and campgrounds that serve transient populations |

        :arrow_right: Why would the EPA designate water systems in this way? Are they regulated differently?
      """)

    with tab2:
      selected_category = "SOURCE_WATER"
      chart_category(selected_category)
      st.markdown("""
        #### Public Water System Source Types

        | Type | What it means |
        |------|---------------|
        | Groundwater | Water from underground aquifers |
        | Surface water | Freshwater from surface sources such as lakes, rivers, wetlands, etc. |

        :arrow_right: Water arrives into these different sources through different means. How might the two different source types be contaminated? What are the differences in our ability to predict contamination? 

      """)

    with tab3:
      selected_category = "SYSTEM_SIZE"
      chart_category(selected_category)
      st.markdown("""
        #### Size Classifications of Public Water Systems
        
        > Community water systems are further classified as small, medium, or large based on the residential populations that they serve. The size classification of a system will determine the frequency and amount of sampling that is required. Approximately 96% of New Jersey residents are supplied by medium or large community water systems. ([2019 Annual Compliance Report on Public Water Systems, New Jersey Department of Environmental Protection, p. 11](https://www.state.nj.us/dep/watersupply//pdf/violations2019.pdf))

        | Size Classification | Population Range Served |
        |------|---------------|
        | Very Small | 500 or less |
        | Small | 501 - 3,300 |
        | Medium | 3,301 - 10,000 |
        | Large | 10,001 - 100,00 |
        | Very Large | Greater than 100,000 |

      """)
      st.caption("Size classifications can be found in EPA's Drinking Water Dashboard [Data Dictionary](https://echo.epa.gov/help/drinking-water-qlik-dashboard-help#dictionary)")

    next = st.button("Next: Find Public Water Systems")
    if next:
        switch_page("find public water systems")
if __name__ == "__main__":
    main()


