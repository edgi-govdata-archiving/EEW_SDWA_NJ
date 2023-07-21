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
#st.markdown('![EEW logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/eew.jpg?raw=true) ![EDGI logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/edgi.png?raw=true)')

previous = st.button("Previous: Welcome")
if previous:
    switch_page("welcome")

st.markdown("""
  # Exploring Safe Drinking Water in New Jersey
  ## Statewide Overview of Public Water Systems (PWS)
  The Safe Drinking Water Act (SDWA) regulates the provision of drinking water from sources that serve the public*. The US Environmental Protection Agency (EPA) oversees  state agencies that enforce regulations about what kinds of contaminants are allowable in drinking water and at
  what concentration.
""")

st.caption("*Public water systems = water systems that serve at least 25 people, so not private wells.")

def main():

  # Streamlit section
  # Map
  
  #if "last_active_drawing" not in st.session_state:
    #st.session_state["last_active_drawing"] = None

  c1 = st.container()
  c2 = st.container()

  with c1:
    st.markdown("## Locations of New Jersey's Public Water Systems")
    st.markdown("""
    Below, you will find an interactive map of all public water systems in New Jersey. Click on the circles to see more information.
    """)

    @st.cache_data(experimental_allow_widgets=True)
    def make_map():
      m = folium.Map(location = [40.304857, -74.499739], zoom_start = 8, tiles="cartodb positron")

      #add markers
      for marker in st.session_state["statewide_markers"]:
        m.add_child(marker)
      out = st_folium(
        m,
        returned_objects=[]
      )

    col1, col2 = st.columns(2)
    with col1:
      with st.spinner(text="Loading interactive map..."):
        make_map()
    with col2:
      st.markdown("""
      ### Map Legend

      | Feature | What it means |
      |------|---------------|
      | Outline - Solid | PWS that draw from surface water |
      | Outline - Dashed | PWS that draw from groundwater |
      | Color - Blue | Community Water Systems |
      | Color - Yellow | Transient Non-Community Water Systems |
      | Color - Green | Non-Transient, Non-Community Water Systems |
      | Size | PWS size, from very small to very large |    
    """)

    st.markdown("""
      ### :face_with_monocle: Why are there PWS shown outside of New Jersey?
      This is an example of data errors in the EPA database. Sometimes, a facility will be listed with a NJ address
      but its latitude and longitude actually correspond to somewhere out of state.

      :arrow_right: What are some implications of a data error like this? How might a misclassification by state or incorrect location impact the regulation of safe drinking water at a facility?
    """)


  with c2:
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

if __name__ == "__main__":
    main()

next = st.button("Next: Safe Drinking Water Act Violations")
if next:
    switch_page("sdwa violations")
