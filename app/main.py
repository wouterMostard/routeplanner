import streamlit as st
import pandas as pd
from pathlib import Path
import pydeck as pdk
import dotenv
import os
from azure.storage.fileshare import ShareFileClient

from constants import COLOR_MAPPING

DATA_FOLDER: Path = Path('./app/data/gtfs')


dotenv.load_dotenv()

conn_string = os.getenv('connection_string')

def load_data(file_name: str):
    if file_name not in os.listdir(DATA_FOLDER):
        service = ShareFileClient.from_connection_string(conn_str=conn_string, share_name='gtfs', file_path=file_name)

        data = service.download_file()
        data.readinto(open(DATA_FOLDER / file_name, 'wb'))

    return pd.read_csv(DATA_FOLDER / file_name)


@st.cache_data
def load_path_data():
    data = load_data('shapes.txt')
    data = data[data.shape_pt_sequence % 20 == 0]
    data.columns = ['shape_id', 'shape_seq', 'lat', 'lon', 'dist_traveled']
    data.set_index('shape_id', inplace=True)

    path_dict = {
        "shape_id": [],
        "path": []
    }

    for shape_id in data.index.unique():
        shape_data = data.loc[shape_id]

        path_dict['shape_id'].append(shape_id)
        path_dict['path'].append(shape_data[['lon', 'lat']].values.tolist())

    return pd.DataFrame(path_dict).set_index('shape_id')

@st.cache_data
def load_path_to_agency_data():
    unique_shape_trips = load_data('trips.txt').drop_duplicates(subset='shape_id').set_index('shape_id')[['route_id']]
    unique_shapes = load_data('shapes.txt').drop_duplicates(subset='shape_id')[['shape_id']].set_index('shape_id')

    shape_routes = unique_shapes.join(unique_shape_trips, how='left')[['route_id']].reset_index().set_index('route_id')

    routes = load_data('routes.txt').drop_duplicates('route_id').set_index('route_id')

    shape_agency = shape_routes.join(routes)[['shape_id', 'agency_id']].reset_index().drop('route_id', axis=1)

    agency = load_data('agency.txt').set_index('agency_id')

    agency_data = shape_agency.join(agency, on='agency_id')[['shape_id', 'agency_id', 'agency_name']].set_index('shape_id')
    agency_data['color'] = [COLOR_MAPPING[idx] for idx in agency_data.agency_id.values]

    return agency_data

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

st.set_page_config(
    page_title="Public route planning using simulated annealing",
    layout="wide"
)


route_data = load_path_data().dropna()
agency_data = load_path_to_agency_data()

plotting_data = route_data.join(agency_data)[['color', 'path']]
plotting_data['color'] = plotting_data['color'].apply(hex_to_rgb)

view_state = pdk.ViewState(latitude=52.4, longitude=4.89, zoom=6)

layer = pdk.Layer(
    type="PathLayer",
    data=plotting_data,
    pickable=True,
    get_color="color",
    width_scale=20,
    width_min_pixels=2,
    get_path="path",
    get_width=5,
)

r = pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip={"text": "{name}"}, map_style="mapbox://styles/mapbox/light-v9")

st.pydeck_chart(r)