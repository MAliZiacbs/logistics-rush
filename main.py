# main.py

import streamlit as st
import json
import os
from config import LOCATIONS, GAME_MODES, STYLES, check_constraints
from game_engine import start_new_game, process_location_checkin
from visualization import visualize_map
from visualization_renders import render_action_controls, render_game_info, render_game_results
from data_management import save_player_data, export_player_data, reset_leaderboard, reset_all_data
import route_analysis
import diagnostics

st.set_page_config(page_title="Logistics Rush", page_icon="🚚", layout="wide")
st.markdown(STYLES, unsafe_allow_html=True)

# Initialize session state variables if not already set
if 'players' not in st.session_state:
    if os.path.exists('player_data.json'):
        with open('player_data.json', 'r') as f:
            st.session_state.players = json.load(f) if os.path.getsize('player_data.json') > 0 else {}
    else:
        st.session_state.players = {}

if 'game_active' not in st.session_state:
    st.session_state.game_active = False
if 'current_route' not in st.session_state:
    st.session_state.current_route = []
if 'optimal_route' not in st.session_state:
    st.session_state.optimal_route = []
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'current_player' not in st.session_state:
    st.session_state.current_player = None
if 'game_mode' not in st.session_state:
    st.session_state.game_mode = "Logistics Challenge"
if 'game_results' not in st.session_state:
    st.session_state.game_results = None
if 'leaderboard' not in st.session_state:
    st.session_state.leaderboard = []
if 'constraints' not in st.session_state:
    st.session_state.constraints = {}
if 'completed_routes' not in st.session_state:
    st.session_state.completed_routes = {"player": [], "optimal": []}
if 'closed_roads' not in st.session_state:
    st.session_state.closed_roads = []
if 'packages' not in st.session_state:
    st.session_state.packages = []
if 'current_package' not in st.session_state:
    st.session_state.current_package = None
if 'delivered_packages' not in st.session_state:
    st.session_state.delivered_packages = []
if 'total_packages' not in st.session_state:
    st.session_state.total_packages = 0
if 'num_road_closures' not in st.session_state:
    st.session_state.num_road_closures = 1
if 'all_game_diagnostics' not in st.session_state:
    st.session_state.all_game_diagnostics = []

route_analysis.init_route_tracking()

st.markdown('<h1 class="main-title">🚚 Logistics Rush</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Interactive Supply Chain Challenge</p>', unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Game", "Leaderboard", "Instructions", "Diagnostics"])

with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        if st.session_state.game_active:
            map_fig = visualize_map(player_route=st.session_state.current_route, show_roads=True)
            st.plotly_chart(map_fig, use_container_width=True)
        elif st.session_state.game_results:
            player_route = st.session_state.completed_routes.get("player", [])
            optimal_route = st.session_state.completed_routes.get("optimal", [])
            st.markdown("### Route Comparison")
            player_map = visualize_map(player_route=player_route, show_roads=False, route_type="player")
            optimal_map = visualize_map(optimal_route=optimal_route, show_roads=False, route_type="optimal")
            col_map1, col_map2 = st.columns(2)
            with col_map1:
                st.plotly_chart(player_map, use_container_width=True)
            with col_map2:
                st.plotly_chart(optimal_map, use_container_width=True)
        else:
            map_fig = visualize_map(show_roads=True)
            st.plotly_chart(map_fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        if st.session_state.game_active:
            render_action_controls()
    with col2:
        render_game_info()

with tab2:
    st.subheader("Leaderboard")
    st.write(st.session_state.leaderboard)
    if st.button("Reset Leaderboard"):
        reset_leaderboard()

with tab3:
    st.subheader("Instructions")
    st.markdown(GAME_MODES["Logistics Challenge"]["instructions"])

with tab4:
    st.subheader("Diagnostics")
    diagnostics.render_diagnostics_tab()

if not st.session_state.game_active and not st.session_state.game_results:
    with st.form("registration_form"):
        name = st.text_input("Name*")
        email = st.text_input("Email*")
        company = st.text_input("Company")
        submitted = st.form_submit_button("Start Game")
        if submitted and name and email:
            st.session_state.current_player = {"name": name, "email": email, "company": company}
            start_new_game()
            st.experimental_rerun()
