import streamlit as st
import pandas as pd
import time
import datetime
import os
import json

# Import our new modules
from config import LOCATIONS, ROAD_SEGMENTS, DISTANCES, STYLES
from logistics_graph import LogisticsGraph
from package_manager import PackageManager
from constraints_manager import ConstraintsManager
from route_optimizer import RouteOptimizer
from game_engine import LogisticsRushGame
from visualization import visualize_map

# Page configuration
st.set_page_config(page_title="Logistics Rush", page_icon="🚚", layout="wide")

# Apply CSS styles
st.markdown(STYLES, unsafe_allow_html=True)

# Initialize session state
if 'game' not in st.session_state:
    st.session_state.game = None
if 'game_results' not in st.session_state:
    st.session_state.game_results = None
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
if 'current_player' not in st.session_state:
    st.session_state.current_player = None
if 'leaderboard' not in st.session_state:
    st.session_state.leaderboard = []

# Main UI
st.markdown('<h1 class="main-title">🚚 Logistics Rush</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Interactive Supply Chain Challenge</p>', unsafe_allow_html=True)

# Create tabs
tab1, tab2, tab3 = st.tabs(["Game", "Leaderboard", "Instructions"])

# Game Tab
with tab1:
    col1, col2 = st.columns([2, 1])  # Left column for map, right for controls/info
    
    with col1:
        # Map Section
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        if st.session_state.game and st.session_state.game.game_active:
            # Show active game map
            map_fig = visualize_map(
                route=st.session_state.game.current_route,
                closed_roads=st.session_state.game.closed_roads,
                locations=LOCATIONS
            )
            st.plotly_chart(map_fig, use_container_width=True)
            
        elif st.session_state.game_results:
            # Show comparison map with player and optimal routes
            map_fig = visualize_map(
                route=st.session_state.game_results["player_route"],
                optimal_route=st.session_state.game_results["optimal_route"],
                closed_roads=st.session_state.game_results["closed_roads"],
                locations=LOCATIONS,
                show_both=True
            )
            st.plotly_chart(map_fig, use_container_width=True)
            
        else:
            # Show blank map
            map_fig = visualize_map(locations=LOCATIONS)
            st.plotly_chart(map_fig, use_container_width=True)
            
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Action controls for active game
        if st.session_state.game and st.session_state.game.game_active:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Actions")
            
            # Current location
            current_location = st.session_state.game.current_route[-1]
            st.info(f"Current Location: {current_location}")
            
            # Movement buttons - 2 columns
            st.subheader("Check In")
            move_col1, move_col2 = st.columns(2)
            
            # List of all locations excluding current
            locations = [loc for loc in LOCATIONS.keys() if loc != current_location]
            
            # First column of locations
            with move_col1:
                for i in range(0, len(locations), 2):
                    if i < len(locations):
                        loc = locations[i]
                        
                        # Check if move is valid
                        path, _ = st.session_state.game.graph.find_shortest_path(current_location, loc)
                        valid_path = path is not None
                        
                        # Check constraints
                        valid_constraints, _ = st.session_state.game.constraints.validate_move(
                            st.session_state.game.current_route, loc
                        )
                        
                        # Button disabled if path is invalid or constraints violated
                        disabled = not (valid_path and valid_constraints)
                        
                        # Create button
                        if st.button(f"{LOCATIONS[loc]['emoji']} {loc}", 
                                   key=f"btn_{loc}", 
                                   disabled=disabled, 
                                   use_container_width=True):
                            result = st.session_state.game.move_to_location(loc)
                            
                            if result["success"]:
                                if "game_completed" in result and result["game_completed"]:
                                    st.session_state.game_results = result["results"]
                                    st.session_state.game = None
                                st.rerun()
                            else:
                                st.error(result["message"])
            
            # Second column of locations
            with move_col2:
                for i in range(1, len(locations), 2):
                    if i < len(locations):
                        loc = locations[i]
                        
                        # Check if move is valid
                        path, _ = st.session_state.game.graph.find_shortest_path(current_location, loc)
                        valid_path = path is not None
                        
                        # Check constraints
                        valid_constraints, _ = st.session_state.game.constraints.validate_move(
                            st.session_state.game.current_route, loc
                        )
                        
                        # Button disabled if path is invalid or constraints violated
                        disabled = not (valid_path and valid_constraints)
                        
                        # Create button
                        if st.button(f"{LOCATIONS[loc]['emoji']} {loc}", 
                                   key=f"btn_{loc}", 
                                   disabled=disabled, 
                                   use_container_width=True):
                            result = st.session_state.game.move_to_location(loc)
                            
                            if result["success"]:
                                if "game_completed" in result and result["game_completed"]:
                                    st.session_state.game_results = result["results"]
                                    st.session_state.game = None
                                st.rerun()
                            else:
                                st.error(result["message"])
            
            # Package Pickup/Delivery Actions
            if st.session_state.game.package_manager.carrying:
                # Show delivery option if at the right location
                carrying = st.session_state.game.package_manager.carrying
                
                if carrying.delivery == current_location:
                    st.subheader("Deliver Package")
                    if st.button(f"Deliver Package #{carrying.id} to {carrying.delivery}", 
                                key="deliver_package", 
                                type="primary", 
                                use_container_width=True):
                        result = st.session_state.game.deliver_package()
                        
                        if result["success"]:
                            st.success(result["message"])
                            
                            if "game_completed" in result and result["game_completed"]:
                                st.session_state.game_results = result["results"]
                                st.session_state.game = None
                                
                            st.rerun()
                        else:
                            st.error(result["message"])
                else:
                    st.info(f"Carrying Package #{carrying.id} to {carrying.delivery}")
            else:
                # Show pickup options
                available_packages = st.session_state.game.package_manager.get_available_pickups(current_location)
                
                if available_packages:
                    st.subheader("Pickup Package")
                    
                    for pkg in available_packages:
                        if st.button(f"📦 Package #{pkg.id} to {pkg.delivery}", 
                                    key=f"pickup_{pkg.id}", 
                                    type="primary", 
                                    use_container_width=True):
                            result = st.session_state.game.pickup_package(pkg.id)
                            
                            if result["success"]:
                                st.success(result["message"])
                                st.rerun()
                            else:
                                st.error(result["message"])
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        if st.session_state.game is None and st.session_state.game_results is None:
            # Player Registration Form
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Player Registration")
            
            with st.form("registration_form"):
                name = st.text_input("Name*")
                email = st.text_input("Email*")
                company = st.text_input("Company")
                
                st.subheader("Game Challenge")
                st.markdown("Master all logistics challenges in one comprehensive experience")
                
                difficulty = st.radio("Select Difficulty Level", 
                                    ["Easy (1 road closure)", 
                                     "Medium (2 road closures)", 
                                     "Hard (3 road closures)"],
                                    index=0)
                
                # Extract number from difficulty
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
                        # Create and start a new game
                        st.session_state.game = LogisticsRushGame(
                            LOCATIONS, ROAD_SEGMENTS, DISTANCES, difficulty=num_closures
                        )
                        game_info = st.session_state.game.start_game()
                        
                        # Store player info
                        st.session_state.current_player = {
                            "name": name,
                            "email": email,
                            "company": company
                        }
                        
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif st.session_state.game and st.session_state.game.game_active:
            # Game Info Panel
            st.markdown('<div class="card">', unsafe_allow_html=True)
            
            game_status = st.session_state.game.get_game_status()
            
            st.markdown('<div class="status-bar">', unsafe_allow_html=True)
            st.markdown(f"⏱ **Time:** {game_status['time']:.1f}s | 📦 **Packages:** {game_status['packages_delivered']}/{game_status['total_packages']} | 🌐 **Progress:** {game_status['progress']}%")
            st.markdown('</div>', unsafe_allow_html=True)
            
            with st.expander("Game Info", expanded=True):
                # Road closures
                if st.session_state.game.closed_roads:
                    st.markdown('<div class="road-closure-alert">⛔️ Road Closures:</div>', unsafe_allow_html=True)
                    closures_text = ", ".join([f"{road[0]} ↔️ {road[1]}" for road in st.session_state.game.closed_roads])
                    st.markdown(closures_text)
                
                # Package info
                st.markdown('<div class="package-info">', unsafe_allow_html=True)
                if game_status['carrying_package']:
                    carrying = st.session_state.game.package_manager.carrying
                    st.markdown(f"🚚 **Carrying:** 📦 Package #{carrying.id} to {carrying.delivery}")
                else:
                    st.markdown("🚚 **Carrying:** No package")
                
                st.markdown(f"📦 **Delivered:** {game_status['packages_delivered']}/{game_status['total_packages']}")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Constraints info
                st.markdown('<div class="constraints-info">', unsafe_allow_html=True)
                st.markdown("🔄 **Constraints:**")
                st.markdown("• Warehouse → Shop")
                st.markdown("• Distribution Center → Home")
                st.markdown("• One package at a time")
                
                # Difficulty
                difficulty = "Easy" if len(st.session_state.game.closed_roads) == 1 else "Medium" if len(st.session_state.game.closed_roads) == 2 else "Hard"
                st.markdown(f"• **Difficulty:** {difficulty} ({len(st.session_state.game.closed_roads)} closure{'s' if len(st.session_state.game.closed_roads) > 1 else ''})")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Current route
            if st.session_state.game.current_route:
                st.markdown("### Your Route")
                st.code(" → ".join(st.session_state.game.current_route))
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif st.session_state.game_results:
            # Game Results Panel
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Challenge Complete!")
            
            results = st.session_state.game_results
            
            # Score display
            st.markdown(f"""
            <div style="text-align:center;margin-bottom:20px">
                <div style="font-size:3rem;font-weight:bold;color:#1a56db">{results['score']}</div>
                <div style="font-size:1rem;color:#6b7280">SCORE</div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Time", f"{results['time']:.1f}s")
                st.metric("Your Distance", f"{results['player_distance']:.1f} cm")
            with c2:
                st.metric("Efficiency", f"{results['efficiency']}%")
                st.metric("Optimal Distance", f"{results['optimal_distance']:.1f} cm")
            
            # Special message for finding a better route
            if results.get('found_better_route', False):
                st.success("🏆 Congratulations! You found a more efficient route than the algorithm calculated!")
            
            st.markdown("### Routes")
            
            player_col, optimal_col = st.columns(2)
            
            with player_col:
                st.markdown("**Your Route:**")
                st.code(" → ".join(results['player_route']))
            
            with optimal_col:
                st.markdown("**Optimal Route:**")
                st.code(" → ".join(results['optimal_route']))
            
            # Save to leaderboard if player info exists
            if st.session_state.current_player:
                player = st.session_state.current_player
                
                leaderboard_entry = {
                    "name": player["name"],
                    "email": player.get("email", ""),
                    "company": player.get("company", ""),
                    "score": results["score"],
                    "efficiency": results["efficiency"],
                    "time": results["time"],
                    "difficulty": results["difficulty"],
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                st.session_state.leaderboard.append(leaderboard_entry)
                
                # Sort leaderboard by score
                st.session_state.leaderboard.sort(key=lambda x: x["score"], reverse=True)
                
                # Save to players data
                if player["email"] not in st.session_state.players:
                    st.session_state.players[player["email"]] = {
                        "name": player["name"],
                        "email": player["email"],
                        "company": player.get("company", ""),
                        "games": []
                    }
                
                # Add game to player history
                st.session_state.players[player["email"]]["games"].append({
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "score": results["score"],
                    "efficiency": results["efficiency"],
                    "time": results["time"],
                    "difficulty": results["difficulty"],
                    "player_route": results["player_route"],
                    "player_distance": results["player_distance"],
                    "optimal_distance": results["optimal_distance"]
                })
                
                # Save to file
                try:
                    with open('player_data.json', 'w') as f:
                        json.dump(st.session_state.players, f)
                except Exception as e:
                    st.error(f"Error saving player data: {e}")
            
            # Play again button
            if st.button("Play Again", type="primary", use_container_width=True):
                st.session_state.game_results = None
                st.rerun()
                
            st.markdown('</div>', unsafe_allow_html=True)

# Leaderboard Tab
with tab2:
    st.subheader("Leaderboard")
    
    # Filter controls
    lb_col1, lb_col2 = st.columns(2)
    with lb_col1:
        sort_by = st.selectbox("Sort By", ["Score", "Time", "Efficiency"])
    with lb_col2:
        # Get all companies
        companies = ["All Companies"]
        for player in st.session_state.players.values():
            if player.get("company") and player["company"] not in companies:
                companies.append(player["company"])
                
        company_filter = st.selectbox("Company Filter", companies)
    
    # Display leaderboard
    if st.session_state.leaderboard:
        # Apply filters
        filtered_data = st.session_state.leaderboard.copy()
        
        if company_filter != "All Companies":
            filtered_data = [entry for entry in filtered_data if entry.get("company") == company_filter]
        
        # Sort data
        if sort_by == "Score":
            filtered_data.sort(key=lambda x: x["score"], reverse=True)
        elif sort_by == "Time":
            filtered_data.sort(key=lambda x: x["time"])
        else:  # Efficiency
            filtered_data.sort(key=lambda x: x["efficiency"], reverse=True)
        
        # Create a dataframe for display
        if filtered_data:
            df = pd.DataFrame(filtered_data)
            df["rank"] = range(1, len(df) + 1)
            df["time"] = df["time"].apply(lambda x: f"{x:.1f}s")
            df["efficiency"] = df["efficiency"].apply(lambda x: f"{x}%")
            
            # Select and rename columns
            display_df = df[["rank", "name", "company", "time", "efficiency", "score", "timestamp"]]
            display_df.columns = ["Rank", "Player", "Company", "Time", "Efficiency", "Score", "Date"]
            
            st.dataframe(display_df, hide_index=True, use_container_width=True)
        else:
            st.info("No matching leaderboard entries found.")
    else:
        st.info("No games have been played yet. Be the first on the leaderboard!")

# Instructions Tab
with tab3:
    st.subheader("How to Play Logistics Rush")
    st.markdown("""
    ### Game Overview
    Logistics Rush is an interactive supply chain optimization game. Navigate between locations to complete package deliveries while handling road closures.

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

# Main function
if __name__ == "__main__":
    pass  # Already running in Streamlit