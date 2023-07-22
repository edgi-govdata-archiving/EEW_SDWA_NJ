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
from folium.plugins import Draw
import altair as alt

st.set_page_config(layout="wide")

previous = st.button("Previous: Statewide Overview")
if previous:
    switch_page("statewide overview")

st.markdown(""" # Search for Public Water Systems and Find Violations

  Using the buttons on the left-hand side of the map, draw a rectangle around the part of New Jersey that you want to learn more about.
  After you draw the box, the map will show any public water systems within it, and the lower part of the page will give details about any violations of SDWA they may have
  recorded since 2001.

  The next pages will also show data based on the area you have selected. If you wish to change your search area, you can come back to this page and draw a different box.

  ### Select an area on the interactive map below in order to proceed.
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
with st.spinner(text="Loading data..."):
  try:
    sdwa = st.session_state["sdwa"]
    sdwa = sdwa.loc[sdwa["FISCAL_YEAR"] == 2021]  # for mapping purposes, delete any duplicates
  except:
    st.error("### Error: Please start on the 'Welcome' page.")
    st.stop()

# Streamlit section
# Map
def main():
  if "markers" not in st.session_state:
    st.session_state["markers"] = []
  if "last_active_drawing" not in st.session_state:
    st.session_state["last_active_drawing"] = None
  if "data" not in st.session_state:
    st.session_state["data"] = None
  if "bounds" not in st.session_state:
    st.session_state["bounds"] = None

  c1 = st.container()
  c2 = st.container()
  c3 = st.container()

  with c1:

    with st.spinner(text="Loading interactive map..."):
      m = folium.Map(tiles="cartodb positron")

      Draw(
        export=False,
        draw_options={"polyline": False, "circle": False, "marker": False, "circlemarker": False},
        edit_options={"edit": False, "remove": False}
      ).add_to(m)

      if (st.session_state["last_active_drawing"] is not None) and (st.session_state["data"] is not None): # else statement has already ran
        print("IF_1")
        # problem is that st.session_state has been assigned default box (see below) so it's just repeating that
        geo_j = folium.GeoJson(data=st.session_state["last_active_drawing"])
        geo_j.add_to(m)
      else: # default - no box drawn yet
        print("ELSE")
        # draw box
        default_box = json.loads('{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"name": "default box"},"geometry":{"coordinates":[[[-74.28527671505785,41.002662478823],[-74.28527671505785,40.88373661477061],[-74.12408529371498,40.88373661477061],[-74.12408529371498,41.002662478823],[-74.28527671505785,41.002662478823]]],"type":"Polygon"}}]}')
        #st.session_state["last_active_drawing"] = default_box["features"][0]  # This will ensure default loads on other pages, but it will - at least for the first custom box drawn - override the custom box
        # add to map
        geo_j = folium.GeoJson(data=default_box)
        geo_j.add_to(m)
        # set bounds
        bounds = geopandas.GeoDataFrame.from_features(default_box)
        bounds.set_crs(4326, inplace=True)
        x1,y1,x2,y2 = bounds.geometry.total_bounds
        st.session_state["bounds"] = [[y1, x1], [y2, x2]]
        # Get PWS
        these_pws = geopandas.clip(sdwa, bounds.geometry)
        these_pws = list(these_pws["PWSID"].unique())
        data = get_data_from_ids("SDWA_VIOLATIONS_MVIEW", "PWSID", these_pws)
        st.session_state["data"] = data
        markers = [folium.CircleMarker(location=[mark["FAC_LAT"], mark["FAC_LONG"]], 
          popup = folium.Popup(
          mark["FAC_NAME"] + "<br>"
          ), #PWS_NAME
          radius = 6, fill_color="orange") for index,mark in data.iterrows() if mark["FAC_LONG"] is not None]
        st.session_state["markers"] = markers

      for marker in st.session_state["markers"]:
        m.add_child(marker)

      if st.session_state["bounds"]:
        m.fit_bounds(st.session_state["bounds"])

      out = st_folium(
        m,
        returned_objects=["last_active_drawing"]
      )

    # Manipulate data
    try:
      counts = st.session_state["data"].groupby(by="FAC_NAME")[["FAC_NAME"]].count()
      counts.rename(columns={"FAC_NAME": "COUNT"}, inplace=True)
      counts = counts.sort_values(by="COUNT", ascending=False)
      violation_type = st.session_state["data"].groupby(by="HEALTH_BASED")[["HEALTH_BASED"]].count()
      violation_type.index = violation_type.index.str.replace('Y', 'Yes')
      violation_type.index = violation_type.index.str.replace('N', 'No')
      violation_type.rename(columns={"HEALTH_BASED": "COUNT"}, inplace=True)
      violation_type = violation_type.sort_values(by="COUNT", ascending=False)
    except:
      counts = []
      violation_type = []

  with c2:
    st.markdown("""
      # Safe Drinking Water Act (SDWA) Violations by Public Water Systems in Selected Area
                
      There are several types of SDWA violation, ranging from "acute health violations" that may immediately cause illness, to failures to monitor, to failures to notify the public, and more.
      """)
    #st.dataframe(counts) 
    st.altair_chart(
      alt.Chart(counts.reset_index(), title = 'Number of SDWA violations by facility, 2001-present').mark_bar().encode(
        x = alt.X("COUNT", title = "Number of violations"),
        y = alt.Y('FAC_NAME', axis=alt.Axis(labelLimit = 500), title=None).sort('-x') # Sort horizontal bar chart
      ),
    use_container_width=True
    )

  with c3:
    st.markdown("""
                # Health-Based Violations in Selected Area

                Some violations are classified as "health-based," meaning that contaminants or disinfectants have been reported in the water above the maximum allowed amounts and may cause health concerns.

                Other violations are classed as more administrative, such as a failure to test the water, or failure to notify the public when a risk to public health has been found.

                """)
    st.caption("Information about health-based violations is from EPA's [Data Dictionary](https://echo.epa.gov/help/drinking-water-qlik-dashboard-help#vio)")
    #st.dataframe(violation_type)
    st.altair_chart(
      alt.Chart(violation_type.reset_index(), title = 'Number of SDWA health-based violations by facility, 2001-present').mark_bar().encode(
        x = alt.X("COUNT", title = "Number of violations"),
        y = alt.Y('HEALTH_BASED', axis=alt.Axis(labelLimit = 500), title="Health-Based Violation?").sort('-x') # Sort horizontal bar chart
      ),
    use_container_width=True
    )
    st.markdown("""
      :arrow_right: In addition to "health-based violations," how might failures to monitor and report drinking water quality, or failures to notify the public, also factor into health outcomes?
      
      :face_with_monocle: Want to learn more about SDWA, all the terms that are used, and the way the law is implemented? EPA maintains an FAQ page [here](https://echo.epa.gov/help/sdwa-faqs).
    """)
  
  if (
    (out["last_active_drawing"]) and (out["last_active_drawing"] != st.session_state["last_active_drawing"]) 
  ):
    print("IF_2")
    bounds = out["last_active_drawing"]
    bounds = geopandas.GeoDataFrame.from_features([bounds])
    bounds.set_crs(4269, inplace=True)
    if bounds.geometry.area[0] < .07:
      x1,y1,x2,y2 = bounds.geometry.total_bounds
      st.session_state["bounds"] = [[y1, x1], [y2, x2]]

      # Keep this drawing
      st.session_state["last_active_drawing"] = out["last_active_drawing"]

      # Get data
      these_pws = geopandas.clip(sdwa, bounds.geometry)
      these_pws = list(these_pws["PWSID"].unique())
      data = get_data_from_ids("SDWA_VIOLATIONS_MVIEW", "PWSID", these_pws)
      st.session_state["data"] = data
      markers = [folium.CircleMarker(location=[mark["FAC_LAT"], mark["FAC_LONG"]], 
        popup = folium.Popup(
        mark["FAC_NAME"] + "<br>"
        ), #PWS_NAME
        radius = 6, fill_color="orange") for index,mark in data.iterrows() if mark["FAC_LONG"] is not None]
      st.session_state["markers"] = markers
      st.experimental_rerun()
    else:
      with c1:
        st.markdown("### You've drawn a big area! Try drawing a smaller one.")

if __name__ == "__main__":
  main()

next = st.button("Next: Environmental Justice")
if next:
    switch_page("environmental justice")
