import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import io
import base64
from PIL import Image
import tempfile
import os
import json
from branca.colormap import linear

# Set page configuration
st.set_page_config(
    page_title="Geographic Data Visualizer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Application title and description
st.title("Geographic Data Visualization Tool")
st.markdown("""
    Upload geographic data, visualize it on interactive maps, and export your visualizations.
    Perfect for students, researchers, analysts, and policymakers.
""")

# Initialize session state variables if they don't exist
if 'data' not in st.session_state:
    st.session_state.data = None
if 'geo_data' not in st.session_state:
    st.session_state.geo_data = None
if 'selected_column' not in st.session_state:
    st.session_state.selected_column = None
if 'map_type' not in st.session_state:
    st.session_state.map_type = 'choropleth'
if 'map_obj' not in st.session_state:
    st.session_state.map_obj = None

# Function to load GeoJSON/Shapefile
@st.cache_data
def load_geo_data(region_type):
    if region_type == "world":
        try:
            # Try to load local shapefile first
            world = gpd.read_file("ne_110m_admin_0_countries.shp")
            # Check for common country code columns and standardize
            if 'ISO_A3' in world.columns:
                world['country_code'] = world['ISO_A3']
            elif 'ADM0_A3' in world.columns:
                world['country_code'] = world['ADM0_A3']
            # Add more mappings as needed
            
            st.success("Loaded local Natural Earth data")
            return world
        except Exception as e:
            st.warning(f"Could not load local shapefile: {str(e)}. Trying online source...")
            
            # Fallback to online source
            world_url = "https://raw.githubusercontent.com/datasets/geo-boundaries-world-110m/master/countries.geojson"
            world = gpd.read_file(world_url)
            
            # Inspect the GeoJSON properties to find the correct identifier
            if len(world) > 0:
                sample_props = world.iloc[0]
                if hasattr(sample_props, '__geo_interface__'):
                    st.info(f"Available properties in GeoJSON: {list(sample_props.__geo_interface__['properties'].keys())}")
                
                # Map common country code fields
                if 'iso_a3' in world.columns:
                    world['country_code'] = world['iso_a3']
                elif 'ISO_A3' in world.columns:
                    world['country_code'] = world['ISO_A3']
                elif 'id' in world.columns:
                    world['country_code'] = world['id']
                # If no known country code column exists, add a warning
                else:
                    st.warning("Could not identify a country code column. Map may not display correctly.")
            
            return world
    elif region_type == "us_states":
        try:
            # Try local file first
            states = gpd.read_file("us_states.shp")
            if 'STUSPS' in states.columns:
                states['state_code'] = states['STUSPS']
            return states
        except Exception as e:
            st.warning(f"Could not load local US states file: {str(e)}. Trying online source...")
            
            # Fallback to online source
            us_states_url = "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json"
            states = gpd.read_file(us_states_url)
            
            # Fix field mappings if needed
            if 'id' in states.columns:
                states['state_code'] = states['id']
                
            return states
    else:
        st.error(f"Unknown region type: {region_type}")
        return None

# Function to load sample datasets
@st.cache_data
def load_sample_data(dataset_name):
    if dataset_name == "World Population":
        # Sample world population data
        data = pd.DataFrame({
            'country_code': ['USA', 'CAN', 'MEX', 'BRA', 'ARG', 'GBR', 'FRA', 'DEU', 'ITA', 'ESP', 
                            'RUS', 'CHN', 'IND', 'JPN', 'AUS', 'ZAF', 'EGY', 'NGA', 'KEN', 'SAU'],
            'country_name': ['United States', 'Canada', 'Mexico', 'Brazil', 'Argentina', 'United Kingdom', 
                            'France', 'Germany', 'Italy', 'Spain', 'Russia', 'China', 'India', 'Japan', 
                            'Australia', 'South Africa', 'Egypt', 'Nigeria', 'Kenya', 'Saudi Arabia'],
            'population_millions': [331.0, 38.0, 126.0, 213.0, 45.0, 67.0, 65.0, 83.0, 60.0, 47.0, 
                                   144.0, 1402.0, 1380.0, 126.0, 25.0, 59.0, 102.0, 206.0, 54.0, 35.0],
            'gdp_per_capita': [63544, 46195, 9946, 8717, 9912, 41059, 39257, 45724, 31676, 27057, 
                              10126, 10500, 1901, 40146, 51693, 6001, 3547, 2097, 1816, 20110],
            'latitude': [37.0902, 56.1304, 23.6345, -14.2350, -38.4161, 55.3781, 46.2276, 51.1657, 
                        41.8719, 40.4637, 61.5240, 35.8617, 20.5937, 36.2048, -25.2744, -30.5595, 
                        26.8206, 9.0820, -1.2921, 23.8859],
            'longitude': [-95.7129, -106.3468, -102.5528, -51.9253, -63.6167, -3.4360, 2.2137, 
                         10.4515, 12.5674, -3.7492, 105.3188, 104.1954, 78.9629, 138.2529, 133.7751, 
                         22.9375, 30.8025, 8.6753, 36.8219, 45.0792]
        })
        return data
    elif dataset_name == "US States Data":
        # Sample US states data
        data = pd.DataFrame({
            'state_code': ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 
                          'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
                          'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                          'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                          'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'],
            'state_name': ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 
                         'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 
                         'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 
                         'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 
                         'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 
                         'New Hampshire', 'New Jersey', 'New Mexico', 'New York', 'North Carolina', 
                         'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania', 
                         'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 
                         'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia', 
                         'Wisconsin', 'Wyoming'],
            'population': [5024279, 733391, 7151502, 3011524, 39538223, 5773714, 3605944, 989948, 
                         21538187, 10711908, 1455271, 1839106, 12812508, 6785528, 3190369, 2937880, 
                         4505836, 4657757, 1362359, 6177224, 7029917, 10077331, 5706494, 2961279, 
                         6154913, 1084225, 1961504, 3104614, 1377529, 9288994, 2117522, 20201249, 
                         10439388, 779094, 11799448, 3959353, 4237256, 13002700, 1097379, 5118425, 
                         886667, 6910840, 29145505, 3271616, 643077, 8631393, 7693612, 1793716, 
                         5893718, 576851],
            'median_income': [50536, 75463, 58945, 47062, 75235, 72331, 76348, 64805, 55462, 58756, 
                             80212, 55785, 65886, 56303, 59955, 57422, 50247, 49973, 57918, 84805, 
                             81215, 57144, 71306, 45792, 55461, 57153, 61439, 58646, 76768, 82545, 
                             49754, 72108, 54602, 64577, 56111, 52919, 63426, 61744, 67167, 53199, 
                             58275, 53320, 61874, 71621, 63001, 74222, 74073, 46711, 61747, 64049]
        })
        return data
    else:
        return None

# Function to process uploaded data
def process_uploaded_data(uploaded_file):
    try:
        # Determine file type and read accordingly
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        
        if file_extension == '.csv':
            data = pd.read_csv(uploaded_file)
        elif file_extension in ['.xls', '.xlsx']:
            data = pd.read_excel(uploaded_file)
        elif file_extension == '.json':
            data = pd.read_json(uploaded_file)
        elif file_extension == '.geojson':
            data = gpd.read_file(uploaded_file)
        elif file_extension == '.shp':
            # For shapefile, we need to handle it differently as it requires multiple files
            try:
                data = gpd.read_file(uploaded_file)
            except Exception as shp_error:
                st.error(f"Error processing shapefile: {str(shp_error)}. Make sure all required files (.shx, .dbf, etc.) are included.")
                return None
        else:
            st.error(f"Unsupported file format: {file_extension}")
            return None
            
        return data
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

# Function to create a choropleth map using Folium
def create_choropleth_map(data, geo_data, join_column, value_column, color_scheme='Blues'):
    # Create a base map
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB positron")
    
    # Get property keys from the GeoJSON
    property_keys = []
    if isinstance(geo_data, gpd.GeoDataFrame) and len(geo_data) > 0:
        try:
            # Try to get properties from the first row if it has __geo_interface__
            first_row = geo_data.iloc[0]
            if hasattr(first_row, '__geo_interface__'):
                property_keys = list(first_row.__geo_interface__['properties'].keys())
                st.info(f"Available GeoJSON properties: {property_keys}")
            else:
                # If we can't get __geo_interface__ from a row, try the whole GeoDataFrame
                if hasattr(geo_data, '__geo_interface__'):
                    sample_feature = geo_data.__geo_interface__['features'][0]
                    property_keys = list(sample_feature['properties'].keys())
                    st.info(f"Available GeoJSON properties from GeoDataFrame: {property_keys}")
                else:
                    # Fallback to column names if we can't get properties
                    property_keys = list(geo_data.columns)
                    st.info(f"Using GeoDataFrame columns as properties: {property_keys}")
        except Exception as e:
            st.warning(f"Could not extract GeoJSON properties: {str(e)}")
            property_keys = list(geo_data.columns)
    
    # Find the matching join column in the GeoJSON properties
    geo_join_column = join_column
    if join_column not in property_keys:
        # Try common alternatives
        alternatives = {
            'country_code': ['ISO_A3', 'iso_a3', 'id', 'ISO3', 'ADMIN'],
            'state_code': ['id', 'STATE', 'STUSPS', 'STATEFP', 'name']
        }
        
        for alt_key in alternatives.get(join_column, []):
            if alt_key in property_keys:
                geo_join_column = alt_key
                st.info(f"Using '{geo_join_column}' from GeoJSON instead of '{join_column}'")
                break
    
    # Create a choropleth layer
    try:
        # Make sure geo_data is properly converted to GeoJSON
        geo_json = None
        if hasattr(geo_data, '__geo_interface__'):
            geo_json = geo_data.__geo_interface__
        elif hasattr(geo_data, 'to_json'):
            geo_json = json.loads(geo_data.to_json())
        else:
            st.error("Cannot convert geo_data to GeoJSON format")
            return m
        
        folium.Choropleth(
            geo_data=geo_json,
            name="choropleth",
            data=data,
            columns=[join_column, value_column],
            key_on=f"feature.properties.{geo_join_column}",
            fill_color=color_scheme,
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name=value_column,
            highlight=True
        ).add_to(m)
        
        # Add tooltips
        folium.features.GeoJson(
            geo_json,
            name="Labels",
            style_function=lambda x: {"color": "transparent", "fillColor": "transparent", "weight": 0},
            tooltip=folium.features.GeoJsonTooltip(
                fields=[geo_join_column] if geo_join_column in property_keys else [property_keys[0]],
                aliases=["Region"],
                localize=True,
                sticky=False,
                labels=True,
                style="""
                    background-color: #F0EFEF;
                    border: 2px solid black;
                    border-radius: 3px;
                    box-shadow: 3px;
                """,
                max_width=800,
            ),
        ).add_to(m)
    except Exception as e:
        st.error(f"Error in choropleth creation: {str(e)}")
        # Provide debug info
        st.write("Data sample:", data.head())
        if len(property_keys) > 0:
            st.write("GeoJSON property keys:", property_keys[:5])
        
    # Add layer control
    folium.LayerControl().add_to(m)
    
    return m

# Function to create a point map using Folium
def create_point_map(data, lat_column, lon_column, value_column, color_scheme='Blues'):
    # Create a base map
    m = folium.Map(location=[data[lat_column].mean(), data[lon_column].mean()], 
                  zoom_start=3, tiles="CartoDB positron")
    
    # Create a color scale
    min_val = data[value_column].min()
    max_val = data[value_column].max()
    color_map = linear.YlOrRd_09.scale(min_val, max_val)
    
    # Add a marker for each data point
    marker_cluster = MarkerCluster().add_to(m)
    
    for idx, row in data.iterrows():
        color = color_map(row[value_column])
        folium.CircleMarker(
            location=[row[lat_column], row[lon_column]],
            radius=10,
            popup=f"{row.name}: {row[value_column]}",
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7
        ).add_to(marker_cluster)
    
    # Add a color legend
    color_map.caption = value_column
    color_map.add_to(m)
    
    return m

# Function to get downloadable link for exported map
def get_download_link(map_obj, filename, file_format):
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_format}') as tmp:
        if file_format == 'html':
            map_obj.save(tmp.name)
            with open(tmp.name, 'rb') as f:
                data = f.read()
            b64 = base64.b64encode(data).decode()
            href = f'<a href="data:text/html;base64,{b64}" download="{filename}.html">Download HTML</a>'
            return href
        else:
            # For image formats like PNG, we need to capture the map as an image
            st.warning("Image export is not fully implemented in this demo. Only HTML export is available.")
            return None

# Sidebar for data input and map options
with st.sidebar:
    st.header("Data Input")
    
    # Data source selection
    data_source = st.radio(
        "Select data source",
        ["Upload your own data", "Use sample data"]
    )
    
    if data_source == "Upload your own data":
        uploaded_file = st.file_uploader(
            "Upload your data file",
            type=["csv", "xlsx", "xls", "json", "geojson", "shp"],
            help="Upload a file containing your geographic data"
        )
        
        if uploaded_file is not None:
            st.session_state.data = process_uploaded_data(uploaded_file)
            
            if st.session_state.data is not None:
                st.success(f"Data loaded: {uploaded_file.name}")
                st.write(f"Columns: {', '.join(st.session_state.data.columns)}")
    else:
        # Sample dataset selection
        sample_dataset = st.selectbox(
            "Choose a sample dataset",
            ["World Population", "US States Data"]
        )
        
        if sample_dataset:
            st.session_state.data = load_sample_data(sample_dataset)
            
            if sample_dataset == "World Population":
                st.session_state.geo_data = load_geo_data("world")
                join_column_default = "country_code"
            elif sample_dataset == "US States Data":
                st.session_state.geo_data = load_geo_data("us_states")
                join_column_default = "state_code"
            
    # Map configuration
    st.header("Map Configuration")
    
    if st.session_state.data is not None:
        # Map type selection
        map_type = st.radio(
            "Select map type",
            ["Choropleth Map", "Point Map"],
            help="Choropleth maps shade regions based on data values. Point maps show individual markers."
        )
        st.session_state.map_type = map_type.lower().replace(" ", "_")
        
        # Column selection for mapping
        if st.session_state.map_type == "choropleth_map":
            join_column = st.selectbox(
                "Select region identifier column",
                options=st.session_state.data.columns,
                index=0 if "country_code" in st.session_state.data.columns else 0
            )
            
            # Region type selection
            region_type = st.selectbox(
                "Select region type",
                ["world", "us_states"],
                index=0
            )
            
            # Load GeoJSON data if not already loaded
            if st.session_state.geo_data is None:
                st.session_state.geo_data = load_geo_data(region_type)
        
        elif st.session_state.map_type == "point_map":
            # For point maps, we need latitude and longitude columns
            lat_column = st.selectbox(
                "Select latitude column",
                options=st.session_state.data.columns,
                index=list(st.session_state.data.columns).index("latitude") if "latitude" in st.session_state.data.columns else 0
            )
            
            lon_column = st.selectbox(
                "Select longitude column",
                options=st.session_state.data.columns,
                index=list(st.session_state.data.columns).index("longitude") if "longitude" in st.session_state.data.columns else 0
            )
        
        # Common map settings
        value_column = st.selectbox(
            "Select data column to visualize",
            options=[col for col in st.session_state.data.columns if st.session_state.data[col].dtype in ['int64', 'float64']],
            index=0
        )
        st.session_state.selected_column = value_column
        
        # Color scheme
        color_scheme = st.selectbox(
            "Select color scheme",
            ["Blues", "Greens", "Reds", "Purples", "Oranges", "YlOrRd", "YlGnBu", "RdPu"]
        )
        
        # Map title
        map_title = st.text_input(
            "Map title",
            f"{value_column} by Region"
        )

# Main content area
if st.session_state.data is not None:
    # Display data preview
    st.subheader("Data Preview")
    st.dataframe(st.session_state.data.head())
    
    # Create and display map
    st.subheader("Map Visualization")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Create the map based on selected options
        if st.session_state.map_type == "choropleth_map" and st.session_state.geo_data is not None:
            try:
                # Create choropleth map
                m = create_choropleth_map(
                    data=st.session_state.data,
                    geo_data=st.session_state.geo_data,
                    join_column=join_column,
                    value_column=value_column,
                    color_scheme=color_scheme
                )
                st.session_state.map_obj = m
                
                # Display the map
                st_folium(m, width=800, height=500)
            except Exception as e:
                st.error(f"Error creating choropleth map: {str(e)}")
                
                # Debug information
                st.write("### Debug Information:")
                st.write("Data Sample:")
                st.dataframe(st.session_state.data.head(3))
                
                st.write("GeoJSON Properties Sample:")
                if st.session_state.geo_data is not None and len(st.session_state.geo_data) > 0:
                    try:
                        if hasattr(st.session_state.geo_data, '__geo_interface__'):
                            props = st.session_state.geo_data.__geo_interface__['features'][0]['properties']
                            st.json(props)
                        else:
                            st.write("No __geo_interface__ attribute found. Displaying columns instead.")
                            st.write(st.session_state.geo_data.columns.tolist())
                    except Exception as e:
                        st.error(f"Error accessing GeoJSON properties: {str(e)}")
                        st.write("GeoData columns:", st.session_state.geo_data.columns.tolist())
        
        elif st.session_state.map_type == "point_map":
            try:
                # Create point map
                m = create_point_map(
                    data=st.session_state.data,
                    lat_column=lat_column,
                    lon_column=lon_column,
                    value_column=value_column,
                    color_scheme=color_scheme
                )
                st.session_state.map_obj = m
                
                # Display the map
                st_folium(m, width=800, height=500)
            except Exception as e:
                st.error(f"Error creating point map: {str(e)}")
    
    with col2:
        # Data statistics
        st.subheader("Data Statistics")
        if st.session_state.selected_column:
            stats = st.session_state.data[st.session_state.selected_column].describe()
            st.write(stats)
            
            # Simple histogram
            fig, ax = plt.subplots(figsize=(4, 3))
            ax.hist(st.session_state.data[st.session_state.selected_column], bins=10, color='steelblue')
            ax.set_xlabel(st.session_state.selected_column)
            ax.set_ylabel('Frequency')
            st.pyplot(fig)
    
    # Export options
    st.subheader("Export Visualization")
    col1, col2 = st.columns(2)
    
    with col1:
        export_filename = st.text_input("Filename", "my_geo_visualization")
    
    with col2:
        export_format = st.selectbox("Format", ["html", "png"])
    
    if st.button("Export Map"):
        if st.session_state.map_obj:
            download_link = get_download_link(
                st.session_state.map_obj,
                export_filename,
                export_format
            )
            if download_link:
                st.markdown(download_link, unsafe_allow_html=True)
            else:
                st.error("Failed to generate export.")
else:
    # Display instructions when no data is loaded
    st.info("👈 Please upload data or select a sample dataset from the sidebar to get started.")
    
    # Show sample visualization as a placeholder
    st.subheader("Sample Visualization")
    
    # Create a simple world map
    m = folium.Map(location=[20, 0], zoom_start=2, tiles="CartoDB positron")
    st_folium(m, width=800, height=500)
    
    # Display additional information
    st.subheader("About this tool")
    st.write("""
    This tool helps you create geographic visualizations from your data. You can:
    
    1. Upload your own CSV, Excel, JSON or Shapefile data containing geographic information
    2. Choose between choropleth (region) maps or point maps
    3. Customize colors and visualization settings
    4. Export your maps for presentations or reports
    
    This is ideal for visualizing:
    * Population statistics
    * Economic indicators
    * Environmental data
    * Health statistics
    * Election results
    * Any other data with a geographic component
    """)