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
import branca
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

  ### Draw an area on the interactive map below, or use the default pre-drawn box.
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

# Make the maps' markers
def marker_maker(data):
  """
  data: SDWA violations dataframe
  """
  # Process data for mapping - drop duplicates (multiple violations) to just get one marker per facility. Color marker by violation count.
  context = data[["PWSID", "PWS_NAME", "PWS_TYPE_CODE", "PWS_SIZE", "SOURCE_WATER", "FAC_LAT", "FAC_LONG"]]
  context.set_index("PWSID", inplace = True)
  data = data.groupby(by=["PWSID"])[["PWSID"]].count().rename(columns={"PWSID": "COUNT"}) # Group data
  data = context.join(data).reset_index().drop_duplicates(subset=["PWSID"])
  colorscale = branca.colormap.linear.Reds_05.scale(data["COUNT"].min(), data["COUNT"].max())
  # Map PWS
  markers = [folium.CircleMarker(location=[mark["FAC_LAT"], mark["FAC_LONG"]], 
    popup=folium.Popup(mark["PWS_NAME"]+'<br><b>Violations since 2001:</b> '+str(mark["COUNT"])+'<br><b>Source:</b> '+mark["SOURCE_WATER"]+'<br><b>Size:</b> '+mark["PWS_SIZE"]+'<br><b>Type:</b> '+mark["PWS_TYPE_CODE"]),
    radius=12, fill_color=colorscale(mark["COUNT"])) for index,mark in data.iterrows() if mark["FAC_LONG"] is not None]
  return markers, colorscale

# Reload, but don't map, PWS
with st.spinner(text="Loading data..."):
  try:
    sdwa = st.session_state["sdwa"]
    sdwa = sdwa.loc[sdwa["FISCAL_YEAR"] == 2021]  # for mapping purposes, delete any duplicates
    psa = st.session_state["service_areas"]
    default_box = st.session_state["default_box"]
  except:
    st.error("### Error: Please start on the 'Welcome' page.")
    st.stop()

# Streamlit section
# Map
def main():
  if "last_active_drawing" not in st.session_state:
    st.session_state["last_active_drawing"] = None
  if "violations_data" not in st.session_state:
    st.session_state["violations_data"] = None
  if "violations_markers" not in st.session_state:
    st.session_state["violations_markers"] = []
  if "violations_colorscale" not in st.session_state:
    st.session_state["violations_colorscale"] = []

  c1 = st.container()
  c2 = st.container()

  with c1:
    col1, col2 = st.columns(2) 

    m = folium.Map(tiles="cartodb positron")

    Draw(
      export=False,
      draw_options={"polyline": False, "circle": False, "marker": False, "circlemarker": False},
      edit_options={"edit": False, "remove": False}
    ).add_to(m)

    # Else statement has already ran
    if (st.session_state["last_active_drawing"] is not None) and (st.session_state["violations_data"] is not None): 
      geo_j = folium.GeoJson(data=st.session_state["last_active_drawing"])
      geo_j.add_to(m)

    # Default - no box drawn yet
    else:
      # Add default box to map
      folium.GeoJson(data=default_box).add_to(m)
      # set bounds
      bounds = geopandas.GeoDataFrame.from_features(default_box)
      bounds.set_crs(4326, inplace=True)
      x1,y1,x2,y2 = bounds.geometry.total_bounds
      #st.session_state["bounds"] = [[y1, x1], [y2, x2]]
      # Get PWS
      these_pws = geopandas.clip(sdwa, bounds.geometry)
      these_pws = list(these_pws["PWSID"].unique())
      violations_data = get_data_from_ids("SDWA_VIOLATIONS_MVIEW", "PWSID", these_pws)
      st.session_state["violations_data"] = violations_data
      # Process data, make markers
      st.session_state["violations_markers"], st.session_state["violations_colorscale"] = marker_maker(violations_data) 

    if st.session_state["psa_gdf"].empty:
      pass
    else:
      folium.GeoJson(
        st.session_state["psa_gdf"],
        style_function = lambda sa: {"fillColor": 'grey', "fillOpacity": .25, "weight": 1, "color": "white"},
        popup=folium.GeoJsonPopup(fields=['SYS_NAME', 'AGENCY_URL'])
      ).add_to(m)

    for marker in st.session_state["violations_markers"]:
      m.add_child(marker)

    if st.session_state["bounds"]:
      m.fit_bounds(st.session_state["bounds"])


  with col2:
    st.markdown("""
      ### Map Legend

      | Feature | What it means |
      |------|---------------|
      | Color | Number of violations since 2001 - the darker the shade of red, the more violations |    
    """)
    st.session_state["violations_colorscale"].width = 750
    st.write(st.session_state["violations_colorscale"])

  with c2:
    # Manipulate data
    try:
      counts = st.session_state["violations_data"].groupby(by=["FAC_NAME", "HEALTH_BASED"])[["FAC_NAME"]].count()
      counts.rename(columns={"FAC_NAME": "COUNT"}, inplace=True)
      counts = counts.sort_values(by="FAC_NAME", ascending=False)
      #violation_type = st.session_state["violations_data"].groupby(by="HEALTH_BASED")[["HEALTH_BASED"]].count()
      #violation_type.index = violation_type.index.str.replace('Y', 'Yes')
      #violation_type.index = violation_type.index.str.replace('N', 'No')
      #violation_type.rename(columns={"HEALTH_BASED": "COUNT"}, inplace=True)
      #violation_type = violation_type.sort_values(by="COUNT", ascending=False)
    except:
      counts = []
      #violation_type = []

    st.markdown("""
      # Safe Drinking Water Act (SDWA) Violations by Public Water Systems in Selected Area
                
      There are several types of SDWA violation, ranging from "acute health violations" that may immediately cause illness, to failures to monitor, to failures to notify the public, and more.
      """)
    st.markdown("""
    Some violations are classified as "health-based," meaning that contaminants or disinfectants have been reported in the water above the maximum allowed amounts and may cause health concerns.

    Other violations are classed as more administrative, such as a failure to test the water, or failure to notify the public when a risk to public health has been found.

    """)
    st.caption("Information about health-based violations is from EPA's [Data Dictionary](https://echo.epa.gov/help/drinking-water-qlik-dashboard-help#vio)")
    #st.dataframe(counts) 
    st.altair_chart(
      alt.Chart(counts.reset_index(), title = 'Number of SDWA violations by facility, 2001-present').mark_bar().encode(
        x = alt.X("COUNT", title = "Number of violations"),
        y = alt.Y('FAC_NAME', axis=alt.Axis(labelLimit = 500), title=None).sort('-x'), # Sort horizontal bar chart
        color = 'HEALTH_BASED'
      ),
    use_container_width=True
    )
    st.markdown("""
      :arrow_right: In addition to "health-based violations," how might failures to monitor and report drinking water quality, or failures to notify the public, also factor into health outcomes?
      
      :face_with_monocle: Want to learn more about SDWA, all the terms that are used, and the way the law is implemented? EPA maintains an FAQ page [here](https://echo.epa.gov/help/sdwa-faqs).
    """)

  with col1:
    with st.spinner(text="Loading interactive map..."):
      out = st_folium(
        m,
        width = 750,
        returned_objects=["last_active_drawing"]
      )

  if (
    (out["last_active_drawing"]) and (out["last_active_drawing"] != st.session_state["last_active_drawing"]) 
  ):
    bounds = out["last_active_drawing"]
    bounds = geopandas.GeoDataFrame.from_features([bounds])
    bounds.set_crs(4269, inplace=True)
    if bounds.geometry.area[0] < .07:
      x1,y1,x2,y2 = bounds.geometry.total_bounds
      # Get PSAs
      psa_gdf = psa[psa.geometry.intersects(bounds.geometry[0])] # Service areas in the place
      # Get PWS violations
      these_pws = geopandas.clip(sdwa, bounds.geometry)
      these_pws = list(these_pws["PWSID"].unique())
      violations_data = get_data_from_ids("SDWA_VIOLATIONS_MVIEW", "PWSID", these_pws)
      # Save data
      st.session_state["bounds"] = [[y1, x1], [y2, x2]]
      st.session_state["psa_gdf"] = psa_gdf
      st.session_state["last_active_drawing"] = out["last_active_drawing"]
      st.session_state["violations_data"] = violations_data
      st.session_state["violations_markers"], st.session_state["violations_colorscale"] = marker_maker(violations_data)
      # Refresh
      st.experimental_rerun()
    else:
      with col2:
        st.error("### You've drawn a big area! Try drawing a smaller one.")


if __name__ == "__main__":
  main()

next = st.button("Next: Environmental Justice")
if next:
    switch_page("environmental justice")
