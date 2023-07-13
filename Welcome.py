# streamlit place picker test
# Pick a place and get ECHO facilities
#https://docs.streamlit.io/library/get-started/create-an-app

import streamlit as st
from streamlit_extras.switch_page_button import switch_page

st.set_page_config(layout="wide")
st.markdown('![EEW logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/eew.jpg?raw=true) ![EDGI logo](https://github.com/edgi-govdata-archiving/EEW-Image-Assets/blob/main/Jupyter%20instructions/edgi.png?raw=true)')

st.markdown("""# Exploring Safe Drinking Water in New Jersey
This website enables you to explore different aspects of safe drinking water across 
the state of New Jersey as well as in specific locations within the state.

The Safe Drinking Water Act (SDWA) regulates the provision of drinking water from sources that serve the public*
. The US Environmental Protection Agency (EPA) oversees
state agencies that enforce regulations about what kinds of contaminants are allowable in drinking water and at
what concentration.
""")

st.caption("""*i.e. those that serve at least 25 people, so not private household wells""")

st.markdown("""## What You Can Learn Here
You can explore imporant questions about SDWA in New Jersey on this website, such as:
* Where are the state's public water systems?
* Which ones serve my community?
* Do they get their water from groundwater sources such as aquifiers or from surface waters such as rivers?
* Have they been in violation of SDWA regulations? 
* Are these violations a result of posing risks to health?
* Who might be most affected by how public water systems manage drinking water? What are the environmental justice implications?
* Does my community have lead service lines, the kinds of which contributed to Flint, Michigan's drinking water crisis?
* What kinds of pollutants are permitted to be released in the watershed?
""")

next = st.button("Get Started! >")
if next:
    switch_page("statewide overview")

st.markdown("""## How to Use This Website
(These instructions will be repeated on each page)

1. Navigate to the "Statewide Overview" page to see a map of all public water systems in the state of New Jersey, according to the EPA.
The page may take a minute to load. **You can always come back to this page as you further explore a specific public water system or set of water systems.** You can click on the markers on the map representing each public water system to learn more about it, including its name. You can also use
the dropdown menu in the middle of the page to learn more about the different kinds of public water systems including:
    * Where they source their water from
    * The size of water systems (very small to very large)
    * The type of water systems (e.g. institutional ones or community/municipal ones)

2. Next, navigate to "SDWA Violations."
Using the buttons on the left-hand side of the map, draw a rectangle around the part of New Jersey that you want to learn more about.
*Important: your box should be fairly small, so that you are focused on a specific community or region, otherwise you'll get an error message.
If that happens, just draw a smaller box and try again.*
After you draw the box, the page will load any public water systems within it as well as details about any violations of SDWA they may have
recorded since 2001.
**Later, if you wish to expand your search or narrow it, you can come back to this page and draw a different box.**

3. Moving to the "Environmental Justice" page, you can explore socio-economic indicators recorded for the place you drew a box around
on the previous page, to get a sense of whether the SDWA violations, lead service lines, and watershed pollutants have any
correlation with neighborhood-level factors such as race, income, age, or education level. 
Use the dropdown menu to select an EJ measure. The map will change to show each of the Census block groups in the place and
the recorded value for the measure there. The data come from EPA's EJScreen tool.

4. Go to the next page, "Lead Service Lines," where we map out the "Purveyor Service Areas" that fall within the boundaries 
of the box you previously drew. We show how many lead service lines these utilities have reported within their service areas. 
A lead service line is a pipe that goes from the utility's main to a house and is made of lead. There is no known safe amount of lead exposure, 
so lead service lines may pose a risk to residents' well-being. 

5. On the last page, you can explore what pollutants industrial facilities reported releasing into the watershed between October 2021 and September 2022. 
We will show you the watersheds for the place you selected and the industrial facilities within those watershed that reported releasing different kinds of pollutants. 
Use the dropdown menu to select different pollutants and see how much reporting facilities said they discharged into the watershed.
""")

st.markdown("""
##### This website was created by the [Environmental Enforcement Watch](https://environmentalenforcementwatch.org/) (EEW) project of the [Environmental Data and Governance Initiative](https://envirodatagov.org/) (EDGI).  Please visit our websites to learn more about our work!
""")
