import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
import datetime
import os
import json

# Import our modules
from config import LOCATIONS, GAME_MODES, STYLES
from game_engine import start_new_game, process_location_checkin, get_game_status
from visualization import visualize_map, render_action_controls, render_game_info, render_game_results
from data_management import save_player_data, export_player_data, reset_leaderboard, reset_all_data

# Page configuration
st.set_page_config(page_title="Logistics Rush", page_icon="🚚", layout="wide")

# CSS styles
STYLES = """
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 1rem;
        color: #1a56db;
    }
    .subtitle {
        text-align: center;
        margin-bottom: 2rem;
        font-size: 1.2rem;
        color: #6b7280;
    }
    .card {
        background-color: white;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .status-bar {
        background-color: #f0f9ff;
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 20px;
        text-align: center;
    }
    .location-button {
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        padding: 12px;
        width: 100%;
        margin-bottom: 10px;
        font-size: 1.1rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    .location-button:hover {
        background-color: #f3f4f6;
        border-color: #d1d5db;
    }
    .primary-button {
        background-color: #1a56db;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 12px;
        width: 100%;
        margin-bottom: 10px;
        font-size: 1.1rem;
    }
    .primary-button:hover {
        background-color: #1e40af;
    }
    .package-info, .constraints-info, .road-closure-alert {
        background-color: #f3f4f6;
        border-radius: 6px;
        padding: 10px;
        margin-bottom: 12px;
    }
    .expander-header {
        font-weight: bold;
        color: #1a56db;
    }
</style>
"""

# Apply CSS styles
st.markdown(STYLES, unsafe_allow_html=True)

# Initialize session state
if 'players' not in st.session_state:
    try:
        if os.path.exists('player_data.json'):
            with open('player_data.json', 'r') as f:
                if os.path.getsize('player_data.json') > 0:
                    st.session_state.players = json.load(f)
                else:
                    st.session_state.players = {}
        else:
            st.session_state.players = {}
    except:
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

# Main UI
st.markdown('<h1 class="main-title">🚚 Logistics Rush</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Interactive Supply Chain Challenge</p>', unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3 = st.tabs(["Game", "Leaderboard", "Instructions"])

with tab1:
    col1, col2 = st.columns([2, 1])  # Left column for map and actions, right for info
    with col1:
        # Map Section
        st.markdown('<div class="card">', unsafe_allow_html=True)
        if st.session_state.game_active:
            map_fig = visualize_map(
                player_route=st.session_state.current_route,
                constraints=st.session_state.constraints
            )
        elif st.session_state.game_results:
            map_fig = visualize_map(
                player_route=st.session_state.completed_routes["player"],
                optimal_route=st.session_state.completed_routes["optimal"],
                constraints=st.session_state.constraints
            )
        else:
            map_fig = visualize_map()
        st.plotly_chart(map_fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Action Controls (Check In and Pickup Package) below map
        if st.session_state.game_active:
            render_action_controls()

    with col2:
        if not st.session_state.game_active and not st.session_state.game_results:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Player Registration")
            with st.form("registration_form"):
                name = st.text_input("Name*")
                email = st.text_input("Email*")
                company = st.text_input("Company")
                st.subheader("Game Challenge")
                st.markdown(GAME_MODES["Logistics Challenge"]["description"])
                submit = st.form_submit_button("Start Game", type="primary")
                if submit:
                    if not name or not email:
                        st.error("Please enter your name and email")
                    else:
                        st.session_state.current_player = {
                            "name": name,
                            "email": email,
                            "company": company
                        }
                        st.session_state.game_mode = "Logistics Challenge"
                        start_new_game()
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        elif st.session_state.game_active:
            render_game_info()

        elif st.session_state.game_results:
            render_game_results()

with tab2:
    st.subheader("Leaderboard")
    lb_col1, lb_col2 = st.columns(2)
    with lb_col1:
        if st.session_state.game_active:
            st.success("Game has started! Please use the Game tab to play.")
        sort_by = st.selectbox("Sort By", ["Score", "Time", "Efficiency"])
    with lb_col2:
        company_filter = st.selectbox("Company Filter", ["All Companies"] + 
                                      list(set([p.get("company", "Unknown") for p in st.session_state.players.values()])))
    
    if st.session_state.leaderboard:
        filtered_data = st.session_state.leaderboard.copy()
        if company_filter != "All Companies":
            filtered_data = [entry for entry in filtered_data if entry["company"] == company_filter]
        
        if sort_by == "Score":
            filtered_data.sort(key=lambda x: x["score"], reverse=True)
        elif sort_by == "Time":
            filtered_data.sort(key=lambda x: x["time"])
        else:
            filtered_data.sort(key=lambda x: x["efficiency"], reverse=True)
        
        if filtered_data:
            df = pd.DataFrame(filtered_data)
            df["rank"] = range(1, len(df) + 1)
            df["time"] = df["time"].apply(lambda x: f"{x:.1f}s")
            df["efficiency"] = df["efficiency"].apply(lambda x: f"{x}%")
            display_df = df[["rank", "name", "company", "time", "efficiency", "score", "timestamp"]]
            display_df.columns = ["Rank", "Player", "Company", "Time", "Efficiency", "Score", "Date"]
            st.dataframe(display_df, hide_index=True, use_container_width=True)
        else:
            st.info("No matching leaderboard entries found.")
    else:
        st.info("No games have been played yet. Be the first on the leaderboard!")

with tab3:
    st.subheader("How to Play Logistics Rush")
    st.markdown("""
    ### Game Overview
    Logistics Rush is an interactive supply chain optimization game. Navigate a Sphero Bolt+ robot through a physical map to complete deliveries.

    ### Basic Gameplay
    1. **Register** with your details
    2. **Navigate** starting from the Factory
    3. **Overcome** road closures
    4. **Deliver** packages while following constraints
    5. **Complete** to see your score
    """)