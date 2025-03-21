import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
import datetime
import os
import json

# Import our modules
from config import LOCATIONS, GAME_MODES, STYLES, check_constraints
from game_engine import start_new_game, process_location_checkin, get_game_status
from visualization import visualize_map 
from visualization_renders import render_action_controls, render_game_info, render_game_results
from data_management import save_player_data, export_player_data, reset_leaderboard, reset_all_data

# Page configuration
st.set_page_config(page_title="Logistics Rush", page_icon="🚚", layout="wide")

# Apply CSS styles from config
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

if 'optimal_path' not in st.session_state:
    st.session_state.optimal_path = []

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
            # Make sure to use the current route for visualization
            map_fig = visualize_map(
                player_route=st.session_state.current_route,
                constraints=st.session_state.constraints,
                show_roads=True
            )
            st.plotly_chart(map_fig, use_container_width=True)
        elif st.session_state.game_results:
            has_player_route = "completed_routes" in st.session_state and "player" in st.session_state.completed_routes
            has_optimal_route = "completed_routes" in st.session_state and "optimal" in st.session_state.completed_routes
            
            player_route = st.session_state.completed_routes.get("player", []) if has_player_route else []
            optimal_route = st.session_state.completed_routes.get("optimal", []) if has_optimal_route else []
            
            st.markdown("### Route Comparison")
            
            player_map = visualize_map(
                player_route=player_route,
                constraints=st.session_state.constraints,
                show_roads=False,
                route_type="player"
            )
            
            optimal_map = visualize_map(
                optimal_route=optimal_route,
                constraints=st.session_state.constraints,
                show_roads=False,
                route_type="optimal"
            )
            
            map_col1, map_col2 = st.columns(2)
            with map_col1:
                st.plotly_chart(player_map, use_container_width=True)
            with map_col2:
                st.plotly_chart(optimal_map, use_container_width=True)
        else:
            map_fig = visualize_map(show_roads=True)
            st.plotly_chart(map_fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Action Controls below map
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
                
                # Add difficulty selector based on road closures
                difficulty = st.radio("Select Difficulty Level", 
                                    ["Easy (1 road closure)", 
                                     "Medium (2 road closures)", 
                                     "Hard (3 road closures)"],
                                    index=0)
                
                # Extract number of road closures from selection
                if "Easy" in difficulty:
                    num_closures = 1
                elif "Medium" in difficulty:
                    num_closures = 2
                else:
                    num_closures = 3
                
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
                        st.session_state.num_road_closures = num_closures
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
    Logistics Rush is an interactive supply chain optimization game. Navigate between locations to complete package deliveries while navigating road closures.

    ### Basic Gameplay
    1. **Register** with your details and select difficulty level
    2. **Navigate** starting from the Warehouse
    3. **Overcome** road closures (1-3 depending on difficulty)
    4. **Deliver** packages while following constraints
    5. **Complete** to see your score

    ### Difficulty Levels
    - **Easy**: 1 road closure
    - **Medium**: 2 road closures
    - **Hard**: 3 road closures

    ### Rules & Constraints
    - You can only carry one package at a time
    - Warehouse must be visited before Shop
    - Distribution Center must be visited before Home
    - All locations must be visited
    - All packages must be delivered
    
    ### Scoring
    Your score is based on efficiency (40%), package delivery (30%), following constraints (20%), and time (10%).
    
    Try to find a more efficient route than the AI's calculated optimal path to earn a perfect efficiency score!
    """)