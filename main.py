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
from visualization import visualize_map, render_game_controls, render_game_results
from data_management import save_player_data, export_player_data, reset_leaderboard, reset_all_data

# Page configuration
st.set_page_config(page_title="Logistics Rush", page_icon="🚚", layout="wide")

# Apply CSS styles
st.markdown(STYLES, unsafe_allow_html=True)

# ----------------------------------
# Initialize session state
# ----------------------------------
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

# New session state variables for Road Closures
if 'closed_roads' not in st.session_state:
    st.session_state.closed_roads = []

# New session state variables for Package Delivery
if 'packages' not in st.session_state:
    st.session_state.packages = []

if 'current_package' not in st.session_state:
    st.session_state.current_package = None

if 'delivered_packages' not in st.session_state:
    st.session_state.delivered_packages = []

if 'total_packages' not in st.session_state:
    st.session_state.total_packages = 0

# ----------------------------------
# Main UI
# ----------------------------------
st.markdown('<h1 class="main-title">🚚 Logistics Rush</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Interactive Supply Chain Challenge</p>', unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3 = st.tabs(["Game", "Leaderboard", "Instructions"])

with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        if st.session_state.game_active:
            # Active game: show current route
            map_fig = visualize_map(
                player_route=st.session_state.current_route,
                constraints=st.session_state.constraints
            )
        elif st.session_state.game_results:
            # Game complete: show both routes
            map_fig = visualize_map(
                player_route=st.session_state.completed_routes["player"],
                optimal_route=st.session_state.completed_routes["optimal"],
                constraints=st.session_state.constraints
            )
        else:
            # No game
            map_fig = visualize_map()
        st.plotly_chart(map_fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        if not st.session_state.game_active and not st.session_state.game_results:
            # Registration form
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Player Registration")
            with st.form("registration_form"):
                name = st.text_input("Name*")
                email = st.text_input("Email*")
                company = st.text_input("Company")
                st.subheader("Game Challenge")
                st.markdown(GAME_MODES["Logistics Challenge"]["description"])
                submit = st.form_submit_button("Start Game")
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
            # Active game controls
            render_game_controls()

        elif st.session_state.game_results:
            # Show results
            render_game_results()

with tab2:
    # Leaderboard
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
        else:  # Efficiency
            filtered_data.sort(key=lambda x: x["efficiency"], reverse=True)

        if filtered_data:
            df = pd.DataFrame(filtered_data)
            df["rank"] = range(1, len(df) + 1)
            df["time"] = df["time"].apply(lambda x: f"{x:.1f}s")
            df["efficiency"] = df["efficiency"].apply(lambda x: f"{x}%")
            display_df = df[["rank", "name", "company", "time", "efficiency", "score", "timestamp"]]
            display_df.columns = ["Rank", "Player", "Company", "Time", "Efficiency", "Score", "Date"]
            st.dataframe(
                display_df,
                column_config={
                    "Score": st.column_config.ProgressColumn(
                        "Score", format="%d", min_value=0, max_value=100
                    ),
                    "Date": st.column_config.DatetimeColumn(
                        "Date/Time", format="MM/DD/YYYY, h:mm a"
                    )
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No matching leaderboard entries found.")
    else:
        st.info("No games have been played yet. Be the first on the leaderboard!")

with tab3:
    st.subheader("How to Play Logistics Rush")
    st.markdown("""
    ### Game Overview

    Logistics Rush is an interactive supply chain optimization game that puts you in control of a delivery network.
    Navigate a Sphero Bolt+ robot through a physical map to complete deliveries between key locations.

    ### Physical Setup

    - A 2m x 4m green carpet with marked roads
    - Four delivery locations (Factory, DHL Hub, Shop, Residence)
    - A central hub in the middle
    - A Sphero Bolt+ robot for navigation

    ### Basic Gameplay

    1. **Register** by entering your details
    2. **Navigate** the Sphero robot starting from the Factory
    3. **Overcome** road closures by finding alternative routes
    4. **Pick up and deliver** packages between locations
    5. **Follow** the required sequence constraints
    6. **Complete** your mission to see your performance results

    ### Game Challenge
    """)
    
    st.markdown(f"""
    #### Logistics Challenge
    **Goal:** {GAME_MODES["Logistics Challenge"]["description"]}

    {GAME_MODES["Logistics Challenge"]["instructions"]}
    """)

    st.markdown("""
    ### The Traveling Salesman Problem

    This game demonstrates the classic Traveling Salesman Problem from logistics and computer science.
    The challenge is to find the shortest possible route that visits a set of locations exactly once
    and returns to the starting point.

    ### Admin Tools
    """)
    admin_password = st.text_input("Admin Password", type="password")
    if admin_password == "LogisticsRush2024":
        st.success("Admin access granted")

        # Export player data
        if st.session_state.players:
            player_data = export_player_data()
            if player_data:
                player_df = pd.DataFrame(player_data)
                st.download_button(
                    label="Download Player Data (CSV)",
                    data=player_df.to_csv(index=False),
                    file_name="logistics_rush_players.csv",
                    mime="text/csv"
                )

                st.subheader("Player Analytics")
                st.markdown("#### Company Distribution")
                company_counts = player_df["Company"].value_counts().reset_index()
                company_counts.columns = ["Company", "Count"]
                fig = px.bar(company_counts.head(10), x="Company", y="Count", title="Top 10 Companies")
                st.plotly_chart(fig)
                
                st.markdown("#### Performance Analysis")
                avg_score = player_df["Score"].mean()
                avg_time = player_df["Time"].mean()
                st.metric("Average Score", f"{avg_score:.1f}")
                st.metric("Average Time", f"{avg_time:.1f}s")
                
            else:
                st.info("No player data available yet.")
        else:
            st.info("No player data available yet.")

        st.subheader("Reset Data")
        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button("Reset Leaderboard", use_container_width=True):
                reset_leaderboard()
        with rc2:
            if st.button("Reset All Data", use_container_width=True):
                reset_all_data()