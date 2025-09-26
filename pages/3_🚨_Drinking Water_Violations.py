import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import geopandas
import folium
from folium.plugins import FastMarkerCluster
import branca
import altair as alt
import sqlite3
from pathlib import Path

st.set_page_config(layout="wide", page_title="🚨 Drinking Water Violations")

previous = st.button("Previous: Find Public Water Systems")
if previous:
    st.switch_page("pages/2_💧_Find_Public_Water_Systems.py")

st.markdown(""" # Violations of the Safe Drinking Water Act (SDWA)

  Details about any violations of SDWA in the selected area that may have been recorded since 2001.
""")


DB_PATH = Path('nj_sdwa.db')
@st.cache_data
def get_data(ids):
  try:
    list_of_ids = ""
    for i in ids:
      list_of_ids += f"'{i}',"
    list_of_ids = list_of_ids[:-1] # remove trailing comma
    data = None
    query = f'select * from NJ_SDWA_VIOLATIONS where PWSID in ({list_of_ids})'
    with sqlite3.connect(DB_PATH) as conn:
      data = pd.read_sql_query(query, conn)
    return data
  except:
    print("Sorry, can't get data")

# Make the maps' markers
def marker_maker(data, facs_without_violations):
  """
  data: SDWA violations dataframe
  """
  # Process data for mapping - drop duplicates (multiple violations) to just get one marker per facility. Color marker by violation count.
  context = data[["PWSID", "FAC_NAME", "PWS_TYPE_CODE", "SYSTEM_SIZE", "PRIMARY_SOURCE_CODE", "FAC_LAT", "FAC_LONG"]]
  context.set_index("PWSID", inplace = True)
  data = data.groupby(by=["PWSID"])[["PWSID"]].count().rename(columns={"PWSID": "VIOLATIONS_COUNT"}) # Group data
  data = context.join(data).reset_index().drop_duplicates(subset=["PWSID"])
  data.loc[data["PWSID"].isin(facs_without_violations), "VIOLATIONS_COUNT"] = 0  # Find facs_without_violations and set count to 0
  colorscale = branca.colormap.linear.Reds_05.scale(data["VIOLATIONS_COUNT"].min(), data["VIOLATIONS_COUNT"].max())
  # remove unmappable points
  to_map = data.loc[~data["FAC_LONG"].isna()]
  # Map PWS
  markers = [folium.CircleMarker(location=[mark["FAC_LAT"], mark["FAC_LONG"]], 
    popup=folium.Popup(mark["FAC_NAME"]+'<br><b>Violations since 2001:</b> '+
      str(mark["VIOLATIONS_COUNT"])+'<br><b>Source:</b> '+mark["PRIMARY_SOURCE_CODE"]+'<br><b>Size:</b> '+
      mark["SYSTEM_SIZE"]+'<br><b>Type:</b> '+mark["PWS_TYPE_CODE"]
    ),
    radius=12, 
    fill_color=colorscale(mark["VIOLATIONS_COUNT"]),
    fill_opacity=1,
    weight=1,
    stroke="white") for index, mark in to_map.iterrows() if (mark["FAC_LONG"] is not None) & (mark["FAC_LAT"] is not None)]
  return markers, colorscale, data

# Reload, but don't map, PWS
with st.spinner(text="Loading data..."):
  try:
    sdwa = st.session_state["sdwa"]
    psa = st.session_state["these_psa"]
    box = st.session_state["box"]
  except:
    st.error("### Error: Please start on the 'Welcome' page.")
    st.stop()

# Streamlit section
# Map
def main():
  if "violations_data" not in st.session_state:
    # Set bounds
    bounds = geopandas.GeoDataFrame.from_features(box)
    bounds.set_crs(4326, inplace=True)
    #x1,y1,x2,y2 = bounds.geometry.total_bounds
    # Get PWS
    these_pws = geopandas.clip(sdwa, bounds.geometry)
    these_pws = list(these_pws["PWSID"].unique())
    # Get PSA ids
    psa_ids = list(st.session_state["these_psa"].index.unique())
    these_pws = these_pws + psa_ids
    st.session_state["violations_data"] = get_data(these_pws)#None
  if "violations_markers" not in st.session_state:
    st.session_state["violations_markers"] = []
  if "violations_colorscale" not in st.session_state:
    st.session_state["violations_colorscale"] = []

  c1 = st.container()
  c2 = st.container()

  with c1:
    col1, col2 = st.columns(2) 

    m = folium.Map(tiles="cartodb positron")

    # Set bounds
    bounds = geopandas.GeoDataFrame.from_features(box)
    bounds.set_crs(4326, inplace=True)
    x1,y1,x2,y2 = bounds.geometry.total_bounds
    # Get PWS
    these_pws = geopandas.clip(sdwa, bounds.geometry)
    these_pws = list(these_pws["PWSID"].unique())
    # Get PSA ids
    psa_ids = list(st.session_state["these_psa"].index.unique())
    these_pws = these_pws + psa_ids
    # Get violations data for PWS and PSA/PWS
    violations_data = get_data(these_pws)
    # Make sure that facilities with no violations still get markers
    if violations_data is not None:
      ## Facilities with violations
      facs_with_violations = list(violations_data["PWSID"].unique())
      ## Facilities without violations
      facs_without_violations = list(set(these_pws) - set(facs_with_violations))
      ## Add faciliities without violations information
      facs_without_violations = sdwa[sdwa["PWSID"].isin(facs_without_violations)]
      ## Fill in missing information from violations table
      facs_without_violations["PWS_SIZE"] = "N/A"
      facs_without_violations["IS_HEALTH_BASED_IND"] = "N" # Really should be N/A but then chart won't show correctly
      #facs_without_violations["PWS_TYPE_CODE"] = "N/A"
      #facs_without_violations["PWS_NAME"] = "N/A"
      violations_data = pd.concat([violations_data, facs_without_violations])
      # Process data, make markers, save data
      st.session_state["violations_markers"], st.session_state["violations_colorscale"], violations_counts = marker_maker(violations_data, list(facs_without_violations["PWSID"].unique()))
      st.session_state["violations_data"] = violations_data
      # Re-save bounds
      bounds = [[y1, x1], [y2, x2]]
    else:
      st.error("### There are no public water systems in this area.")
      st.stop()

    if st.session_state["these_psa"].empty:
      pass
    else:
      # Join violations counts to these_psa
      map_psa = st.session_state["these_psa"].merge(violations_counts, left_on="PWID", right_on="PWSID")
      folium.GeoJson(
        map_psa,
        style_function = lambda sa: {"fillOpacity": 0, "weight": 2, "color": "black"},
        popup=folium.GeoJsonPopup(fields=['SYS_NAME', 'AGENCY_URL', "VIOLATIONS_COUNT"])
      ).add_to(m)

    mc = FastMarkerCluster("", showCoverageOnHover = False, removeOutsideVisibleBounds = True, icon_create_function="""
        function (cluster) {
          return L.divIcon({ html: "<span style='border-radius:50%; border:solid #3388ff 1px;padding:5px 10px 5px 10px; background-color:#3388ff; color:white;'>" + cluster.getChildCount() + "</span>", className: 'mycluster' });
        }
        """)
    for marker in st.session_state["violations_markers"]:
      mc.add_child(marker)
    mc.add_to(m)

    m.fit_bounds(bounds)
    m.add_child(st.session_state["violations_colorscale"])

  with col1:
    with st.spinner(text="Loading interactive map..."):
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
      | Circle color | Number of drinking water violations since 2001 |
      | Blue circle with white text | There are multiple facilities with violations in this area, try zooming in |
      | Black outlines | Purveyor Service Area boundaries |
      | Shades of red | Number of drinking water violations: the darker the shade of red, the more violations at the facility
    """)
    #st.session_state["violations_colorscale"].width = 450
    #st.html(st.session_state["violations_colorscale"])

  with c2:
    # Manipulate data
    try:
      counts = st.session_state["violations_data"].groupby(by=["FAC_NAME", "IS_HEALTH_BASED_IND", "PWS_TYPE_CODE"])[["FAC_NAME"]].count()
      counts.rename(columns={"FAC_NAME": "VIOLATIONS_COUNT"}, inplace=True)
      counts.loc[counts.index.isin(list(facs_without_violations["FAC_NAME"].unique()),level='FAC_NAME'), "VIOLATIONS_COUNT"] = 0 # Reset facilities with no recorded violations to 0 count
      counts = counts.sort_values(by="FAC_NAME", ascending=False)
    except:
      counts = []

    st.markdown("""
      # Safe Drinking Water Act Violations by Public Water Systems in Selected Area
                
      There are several types of SDWA violation, ranging from "acute health violations" that may immediately cause illness, to failures to monitor, to failures to notify the public, and more.
      """)
    st.markdown("""
    Some violations are classified as "health-based," meaning that contaminants or disinfectants have been reported in the water above the maximum allowed amounts and may cause health concerns.

    Other violations are classed as more administrative, such as a failure to test the water, or failure to notify the public when a risk to public health has been found.

    """)
    st.caption("Information about health-based violations is from EPA's [Data Dictionary](https://echo.epa.gov/help/drinking-water-qlik-dashboard-help#vio)")
   
    # Emphasize CWS in chart in bold
    counts.reset_index(inplace=True)
    cws = list(counts[counts["PWS_TYPE_CODE"]=="CWS"]["FAC_NAME"].unique()) # CWS
    condition_str = ''
    for c in cws:
      condition_str += f'datum.value=="{c}" | '
    condition_str = condition_str[:-2]

    title = alt.Title(
        text='Number of SDWA violations by facility, 2001-present',
        subtitle="Community Water Systems (CWS) indicated in *bold*"
    )
    
    st.altair_chart(
      alt.Chart(counts, title = title).mark_bar().encode(
        x = alt.X("VIOLATIONS_COUNT", title = "Number of violations"),
        y = alt.Y('FAC_NAME', axis=alt.Axis(
          labelLimit = 500,
          labelFontWeight=alt.condition(
            condition_str,
            #'datum.value=="KEYSTONE APT LLC-WELL HOUSE #1" | datum.value== "NJ AMERICAN WATER RARITAN-MILLSTONE WATER"',
            #'datum.value in {cws}',
            #alt.datum.FAC_NAME in cws,
            #alt.FieldOneOfPredicate('datum.value',["KEYSTONE APT LLC-WELL HOUSE #1"]),
            alt.value('bold'),  # If true, set font weight to bold
            alt.value('normal') # If false, set font weight to normal
          )
          ), title=None
          ).sort('-x'), # Sort horizontal bar chart
        color = 'IS_HEALTH_BASED_IND'
      ),
    use_container_width=True
    )
    st.markdown("""
      :arrow_right: In addition to "health-based violations," how might failures to monitor and report drinking water quality, or failures to notify the public, also factor into health outcomes?
      
      :thinking: Want to learn more about SDWA, all the terms that are used, and the way the law is implemented? EPA maintains an FAQ page [here](https://echo.epa.gov/help/sdwa-faqs).
    """)

  # Download Data Button
  st.download_button(
    "Download this page's data",
    st.session_state["violations_data"].to_csv(),
    "selected_public_water_systems_violations.csv",
    "text/csv",
    key='download-csv'
  )

if __name__ == "__main__":
  main()

next = st.button("Next: Environmental Justice")
if next:
    st.switch_page("pages/4_⚖️_Environmental_Justice.py")
