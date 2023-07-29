# streamlit place picker test
# Pick a place and get ECHO facilities
#https://docs.streamlit.io/library/get-started/create-an-app
import pandas as pd
import json
import urllib.parse
import streamlit as st
from streamlit_extras.switch_page_button import switch_page
from streamlit_folium import st_folium
import geopandas
import folium
import folium.features
from folium.plugins import FastMarkerCluster
import altair as alt

st.set_page_config(layout="wide", page_title="💧 Find Public Water Systems")

previous = st.button("Previous: Welcome")
if previous:
    switch_page("welcome")

st.markdown(""" # Search for Public Water Systems

  The Safe Drinking Water Act (SDWA) regulates the provision of drinking water from sources that serve the public*. The US Environmental Protection Agency (EPA) oversees  state agencies that enforce regulations about what kinds of contaminants are allowable in drinking water and at
  what concentration.
""")
st.caption("*Public water systems = water systems that serve at least 25 people, so not private wells.")
            
st.markdown("""

  ### Drag and zoom the map to center the area you'd like to explore.
            
  The map will automatically select and show the public water systems in the map area. This page and the following pages will show analyses based on this selection. If you wish to change your search area, you can always come back to this page and move the map around.
""")


@st.cache_data
def get_data(query):
  try:
    url= 'https://portal.gss.stonybrook.edu/echoepa/?query='
    data_location = url + urllib.parse.quote_plus(query) + '&pg'
    data = pd.read_csv(data_location, encoding='iso-8859-1', dtype={"REGISTRY_ID": "Int64"})
    return data
  except:
    print("Sorry, can't get data")

# Data Processing
def get_data_from_ids(table, key, list_of_ids):
  ids  = ""
  for i in list_of_ids:
    ids += "'"+i +"',"
  ids = ids[:-1]
  # get data
  sql = 'select * from "'+table+'" where "'+key+'" in ({})'.format(ids)
  data = get_data(sql)
  return data

# Reload, but don't map, PWS
try:
  sdwa = st.session_state["sdwa"]
  sdwa = sdwa.loc[sdwa["FISCAL_YEAR"] == 2021]  # for mapping purposes, delete any duplicates
  psa = st.session_state["service_areas"]
  r = st.session_state["marker_styles"]["r"]
  s = st.session_state["marker_styles"]["s"]
  t = st.session_state["marker_styles"]["t"]
except:
  st.error("### Error: Please start on the 'Welcome' page.")
  st.stop()

style = lambda x: {"fillColor": "red"}

def main():
  if "bounds" not in st.session_state: # bounds for this page
    st.session_state["bounds"] = None

  # Streamlit section
  # Map
  def change(bounds):
    st.session_state['bounds'] = bounds
    if output["zoom"] < 11:
      with c2:
        st.error("### Try zooming in a bit more. There's too much data to show for this big of an area.")
        st.stop()
    # Create a feature from bounds
    feature = {
    "type": "FeatureCollection",
    "features": [
        {
          "type": "Feature",
          "properties": {"Name": "Bounds"},
          "geometry": {
            "coordinates": [
              [
                [
                  bounds["_southWest"]["lng"],
                  bounds["_northEast"]["lat"]
                ],
                [
                  bounds["_southWest"]["lng"],
                  bounds["_southWest"]["lat"]
                ],
                [
                  bounds["_northEast"]["lng"],
                  bounds["_southWest"]["lat"]
                ],
                [
                  bounds["_northEast"]["lng"],
                  bounds["_northEast"]["lat"]
                ],
                [
                  bounds["_southWest"]["lng"],
                  bounds["_northEast"]["lat"]
                ]
              ]
            ],
            "type": "Polygon"
          }
        }
      ]
    }
    # Get bounds
    bounds = geopandas.GeoDataFrame.from_features(feature)
    bounds.set_crs(4326, inplace=True)
    psa_gdf = psa[psa.geometry.intersects(bounds.geometry[0])] # Service areas in the place
    # Clip data to bounds
    data = sdwa[sdwa.geometry.intersects(bounds.geometry[0])]
    # Process data, make markers for mapping
    markers = [folium.CircleMarker(location=[mark.geometry.y, mark.geometry.x], 
      popup=folium.Popup(mark["PWS_NAME"]+'<br><b>Source:</b> '+mark["SOURCE_WATER"]+'<br><b>Size:</b> '+mark["SYSTEM_SIZE"]+'<br><b>Type:</b> '+mark["PWS_TYPE_CODE"]),
      radius=r[mark["SYSTEM_SIZE"]], fill_color=t[mark["PWS_TYPE_CODE"]], stroke=s[mark["SOURCE_WATER"]]) for index,mark in data.iterrows() if not mark.geometry.is_empty]
    # Save data
    st.session_state["these_psa"] = psa_gdf
    st.session_state["these_markers"] = markers
    st.session_state["these_data"] = data
    st.session_state["box"] = bounds
    st.experimental_rerun()

  con1 = st.container()
  con2 = st.container()

  with con1:
    c1, c2 = st.columns(2)

    m = folium.Map(tiles="cartodb positron", location=[40.934, -74.178], zoom_start=12, min_zoom = 8, max_zoom=15)

    fg = folium.FeatureGroup()

    if st.session_state["these_psa"] is None:
      pass
    else:
      fg.add_child(folium.GeoJson(
        st.session_state["these_psa"],
        style_function = lambda x: {"fillOpacity": 0, "fillColor": None, "weight": 2, "color": "black"},
        tooltip=folium.GeoJsonTooltip(fields=['SYS_NAME'], labels=False)
        )
      ) # Styling doesn't work. See: https://github.com/randyzwitch/streamlit-folium/issues/121
    mc = FastMarkerCluster("")
    for marker in st.session_state["these_markers"]:
      mc.add_child(marker)
    fg.add_child(mc)

    with c1:
      output = st_folium(m, width=500, feature_group_to_add=fg, returned_objects=["bounds", "zoom"])

    # if bounds change
    if (output["bounds"] and (output["bounds"] != st.session_state["bounds"])):
      st.session_state["bounds"] = output["bounds"]
      change(st.session_state["bounds"])

    with c2:
      st.markdown("""
        ### Map Legend
        
        Click on circles and hover over blue areas to see more information.

        | Feature | What it means |
        |------|---------------|
        | Colored circle with number | There are several public water systems here, zoom in and/or click to see them |
        | Exploded lines | Several public water systems are listed at these coordinates in EPA's database, learn more about them by clicking the cirles the lines point to |
        | Circle Outline - Solid | Public water system that draws from surface water |
        | Circle Outline - None | Public water system that draws from groundwater |
        | Circle Color - Blue | Community Water Systems |
        | Circle Color - Yellow | Transient Non-Community Water Systems |
        | Circle Color - Green | Non-Transient, Non-Community Water Systems |
        | Circle Size | Public water system  size, from very small to very large |
        | Blue area with outline | Service area boundary for a selected public water system |
      """)

  with con2:
    st.markdown("## Summary of Public Water Systems by Type, Size, and Source")
    st.markdown("""
      Click through the tabs below to see summaries of the selected area's water systems based on different EPA categorizations.
    """)

    def chart_category(selected_category):
      data = st.session_state["these_data"].loc[st.session_state["these_data"]["FISCAL_YEAR"]==2021]
      counts = data.groupby(by=selected_category)[[selected_category]].count().rename(columns={selected_category:"Number of Facilities"})
      counts.sort_values(by="Number of Facilities",ascending=False, inplace=True) # Sort table by selected_category
      #st.dataframe(counts)
      counts = counts.rename_axis(selected_category).reset_index()
      title = alt.TitleParams("Distribution of the area's Public Water Systems by EPA Code '%s'" %selected_category, anchor='middle')
      st.altair_chart(
        alt.Chart(counts, title=title).mark_bar().encode(
          x = alt.X('Number of Facilities', axis=alt.Axis(tickMinStep=1)),
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

next = st.button("Next: Drinking Water Violations")
if next:
    switch_page("drinking water violations")
