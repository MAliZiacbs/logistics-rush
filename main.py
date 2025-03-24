import streamlit as st
import pandas as pd
import time
import datetime
import os
import json
import networkx as nx
import matplotlib.pyplot as plt
from io import StringIO

# Import our modules
from config import LOCATIONS, ROAD_SEGMENTS, DISTANCES, STYLES, DIFFICULTY_CONSTRAINTS
from logistics_graph import LogisticsGraph
from package_manager import PackageManager
from constraints_manager import ConstraintsManager
from route_optimizer import RouteOptimizer
from game_engine import LogisticsRushGame
from visualization import visualize_map

# Import new Databricks integration modules
import data_exporter
import leaderboard_manager
import insights_fetcher

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
if 'diagnostics_history' not in st.session_state:
    st.session_state.diagnostics_history = []

def draw_graph(graph, closed_roads=None):
    """Draw a NetworkX graph using matplotlib"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Get node positions from LOCATIONS
    pos = {loc: (LOCATIONS[loc]["position"][0]/100, LOCATIONS[loc]["position"][1]/100) for loc in LOCATIONS}
    
    # Draw nodes
    nx.draw_networkx_nodes(graph, pos, node_size=700, node_color='lightblue', ax=ax)
    
    # Draw edges
    nx.draw_networkx_edges(graph, pos, width=2, edge_color='gray', ax=ax)
    
    # Add node labels
    nx.draw_networkx_labels(graph, pos, font_size=10, font_weight='bold', ax=ax)
    
    # Add edge labels (distances)
    edge_labels = {}
    for u, v, data in graph.edges(data=True):
        edge_labels[(u, v)] = data.get('weight', '')
    
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, font_size=8, ax=ax)
    
    # Highlight closed roads
    if closed_roads:
        closed_edges = [(road[0], road[1]) for road in closed_roads]
        nx.draw_networkx_edges(graph, pos, edgelist=closed_edges, width=3, edge_color='red', 
                              style='dashed', ax=ax)
    
    plt.title("Logistics Rush Network Graph")
    plt.axis('off')
    
    # Display the plot in Streamlit
    st.pyplot(fig)

def save_diagnostics(data):
    """Save diagnostic data to session state history with enhanced constraint tracking"""
    if isinstance(data, LogisticsRushGame):
        # Active game - extract data
        diag_data = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "difficulty": data.difficulty,
            "closed_roads": [(road[0], road[1]) for road in data.closed_roads],
            "current_route": data.current_route,
            "optimal_route": data.optimal_route,
            "optimal_distance": data.optimal_distance,
            "packages": [
                {
                    "id": p.id,
                    "pickup": p.pickup,
                    "delivery": p.delivery,
                    "status": p.status
                } for p in data.package_manager.packages
            ],
            "constraint_info": {
                "active_constraints": data.constraints.get_active_constraints(),
                "violated_constraints": list(data.violated_constraints),
                "constraint_violations": data.constraint_violations
            }
        }
    else:
        # Completed game - data is already a dict
        diag_data = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **data
        }
    
    # Add to history
    st.session_state.diagnostics_history.append(diag_data)

def add_diagnostics_tab():
    st.subheader("Game Diagnostics")
    
    # Section for current/recent game
    if st.session_state.game or st.session_state.game_results:
        data = st.session_state.game_results if st.session_state.game_results else st.session_state.game
        
        if data:
            st.markdown("### Current/Recent Game")
            
            # Basic game info
            game_info_col1, game_info_col2 = st.columns(2)
            
            with game_info_col1:
                if hasattr(data, 'difficulty'):
                    # For active game
                    difficulty = "Easy" if data.difficulty == 1 else "Medium" if data.difficulty == 2 else "Hard"
                    st.metric("Difficulty", difficulty)
                    
                    closed_roads_str = ", ".join([f"{road[0]} ↔️ {road[1]}" for road in data.closed_roads])
                    st.text_area("Road Closures", closed_roads_str, height=100, disabled=True)
                    
                    # Show active constraints based on difficulty
                    active_constraints = data.constraints.get_active_constraints()
                    if active_constraints:
                        st.subheader("Active Constraints")
                        for constraint in active_constraints:
                            st.info(f"{constraint[0]} → {constraint[1]}")
                else:
                    # For completed game
                    difficulty = "Easy" if data['difficulty'] == 1 else "Medium" if data['difficulty'] == 2 else "Hard"
                    st.metric("Difficulty", difficulty)
                    
                    closed_roads_str = ", ".join([f"{road[0]} ↔️ {road[1]}" for road in data['closed_roads']])
                    st.text_area("Road Closures", closed_roads_str, height=100, disabled=True)
                    
                    # Show active constraints from completed game
                    if 'active_constraints' in data:
                        st.subheader("Active Constraints")
                        for constraint in data['active_constraints']:
                            st.info(f"{constraint[0]} → {constraint[1]}")
            
            with game_info_col2:
                if hasattr(data, 'package_manager'):
                    # For active game
                    packages_info = "\n".join([
                        f"Package #{p.id}: {p.pickup} → {p.delivery} ({p.status})" 
                        for p in data.package_manager.packages
                    ])
                    st.text_area("Packages", packages_info, height=150, disabled=True)
                    
                    # Show constraint violations
                    if hasattr(data, 'violated_constraints') and data.violated_constraints:
                        st.subheader("Constraint Violations")
                        for constraint in data.violated_constraints:
                            st.error(f"{constraint[0]} → {constraint[1]} (Violated!)")
                elif 'packages' in data:
                    # For completed game
                    packages_info = "\n".join([
                        f"Package #{p['id']}: {p['pickup']} → {p['delivery']} ({p['status']})" 
                        for p in data['packages']
                    ])
                    st.text_area("Packages", packages_info, height=150, disabled=True)
                    
                    # Show constraint violations from completed game
                    if 'violated_constraints' in data and data['violated_constraints']:
                        st.subheader("Constraint Violations")
                        for constraint in data['violated_constraints']:
                            st.error(f"{constraint[0]} → {constraint[1]} (Violated!)")
            
            # Route analysis
            st.markdown("### Route Analysis")
            
            route_col1, route_col2 = st.columns(2)
            
            with route_col1:
                st.markdown("**Player Route:**")
                
                if hasattr(data, 'current_route'):
                    # For active game
                    player_route = data.current_route
                    if player_route:
                        st.code(" → ".join(player_route))
                        
                        # Calculate distance
                        total_distance = data.graph.calculate_route_distance(player_route)
                        st.metric("Current Distance", f"{total_distance:.1f} cm")
                        
                        # Show move history
                        if hasattr(data, 'move_history') and data.move_history:
                            with st.expander("Move History"):
                                for i, move in enumerate(data.move_history):
                                    violation_info = ""
                                    if move.get('violated_constraint'):
                                        violation_info = f" ⚠️ Violated: {move['violated_constraint'][0]} → {move['violated_constraint'][1]}"
                                    st.markdown(f"**Move {i+1}:** {move.get('from', 'Start')} → {move.get('to', 'Unknown')} ({move.get('distance', 0)} cm){violation_info}")
                        
                elif 'player_route' in data:
                    # For completed game
                    player_route = data['player_route']
                    st.code(" → ".join(player_route))
                    st.metric("Total Distance", f"{data['player_distance']:.1f} cm")
                    
                    # Show move history from enhanced diagnostics
                    if 'enhanced_diagnostics' in data and 'move_history' in data['enhanced_diagnostics']:
                        with st.expander("Move History"):
                            for i, move in enumerate(data['enhanced_diagnostics']['move_history']):
                                violation_info = ""
                                if move.get('violated_constraint'):
                                    violation_info = f" ⚠️ Violated: {move['violated_constraint'][0]} → {move['violated_constraint'][1]}"
                                st.markdown(f"**Move {i+1}:** {move.get('from', 'Start')} → {move.get('to', 'Unknown')} ({move.get('distance', 0)} cm){violation_info}")
            
            with route_col2:
                st.markdown("**Optimal Route:**")
                
                if hasattr(data, 'optimal_route'):
                    # For active game
                    optimal_route = data.optimal_route
                    if optimal_route:
                        st.code(" → ".join(optimal_route))
                        st.metric("Optimal Distance", f"{data.optimal_distance:.1f} cm")
                elif 'optimal_route' in data:
                    # For completed game
                    optimal_route = data['optimal_route']
                    st.code(" → ".join(optimal_route))
                    st.metric("Optimal Distance", f"{data['optimal_distance']:.1f} cm")
            
            # Constraints Analysis
            if hasattr(data, 'constraints') or 'active_constraints' in data:
                st.markdown("### Constraints Analysis")
                
                # Get active constraints
                active_constraints = []
                if hasattr(data, 'constraints'):
                    active_constraints = data.constraints.get_active_constraints()
                elif 'active_constraints' in data:
                    active_constraints = data['active_constraints']
                
                # Get violated constraints
                violated_constraints = []
                if hasattr(data, 'violated_constraints'):
                    violated_constraints = list(data.violated_constraints)
                elif 'violated_constraints' in data:
                    violated_constraints = data['violated_constraints']
                
                # Calculate number of constraints based on difficulty
                if hasattr(data, 'difficulty'):
                    difficulty = data.difficulty
                else:
                    difficulty = data.get('difficulty', 1)
                    
                total_constraints = len(DIFFICULTY_CONSTRAINTS.get(difficulty, []))
                
                # Display constraint compliance stats
                st.metric("Constraints Violated", f"{len(violated_constraints)}/{total_constraints}")
                
                if active_constraints:
                    st.subheader("Active Constraints")
                    for constraint in active_constraints:
                        is_violated = constraint in violated_constraints
                        if is_violated:
                            st.markdown(f"❌ **{constraint[0]} → {constraint[1]}** (Violated)")
                        else:
                            st.markdown(f"✅ **{constraint[0]} → {constraint[1]}** (Respected)")
                else:
                    st.info("No active constraints for this difficulty level.")
            
            # Network Graph
            st.markdown("### Network Graph")
            
            # Create a graph visualization
            if hasattr(data, 'graph'):
                # For active game
                g_state = data.graph.get_graph_state()
                
                st.markdown("#### Connectivity Analysis")
                # Display graph state as table
                connectivity_data = []
                for loc, connections in g_state['connectivity'].items():
                    connectivity_data.append({
                        "Location": loc,
                        "Connected To": ", ".join(connections),
                        "Connections Count": len(connections)
                    })
                
                connectivity_df = pd.DataFrame(connectivity_data)
                st.dataframe(connectivity_df, use_container_width=True)
                
                # Draw the actual graph
                st.markdown("#### Visual Network")
                draw_graph(data.graph.graph, data.closed_roads)
                
            elif 'enhanced_diagnostics' in data and 'graph_state' in data['enhanced_diagnostics']:
                # For completed game, visualize based on final state
                g_state = data['enhanced_diagnostics']['graph_state']
                
                st.markdown("#### Connectivity Analysis")
                # Display graph state as table
                connectivity_data = []
                for loc, connections in g_state['connectivity'].items():
                    connectivity_data.append({
                        "Location": loc,
                        "Connected To": ", ".join(connections),
                        "Connections Count": len(connections)
                    })
                
                connectivity_df = pd.DataFrame(connectivity_data)
                st.dataframe(connectivity_df, use_container_width=True)
                
                # Recreate and draw the graph
                g = LogisticsGraph(LOCATIONS, ROAD_SEGMENTS, DISTANCES)
                for road in data['closed_roads']:
                    g.close_road(road[0], road[1])
                    
                st.markdown("#### Visual Network")
                draw_graph(g.graph, data['closed_roads'])
                
            # Option to save diagnostic data
            if st.button("Save Diagnostic Data", type="primary"):
                save_diagnostics(data)
                st.success("Diagnostic data saved!")
    
    # History section
    st.markdown("### Diagnostics History")
    
    # Display saved diagnostic data
    if st.session_state.diagnostics_history:
        for i, diag in enumerate(st.session_state.diagnostics_history):
            with st.expander(f"Game #{i+1} - {diag.get('timestamp', 'Unknown')}"):
                st.json(diag)
    else:
        st.info("No diagnostic history available yet.")
    
    # Clear history button
    if st.session_state.diagnostics_history and st.button("Clear History", type="secondary"):
        st.session_state.diagnostics_history = []
        st.success("Diagnostic history cleared!")
        
# Main UI
st.markdown('<h1 class="main-title">🚚 Logistics Rush</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Interactive Supply Chain Challenge</p>', unsafe_allow_html=True)

# Create tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Game", "Leaderboard", "Instructions", "Diagnostics", "Databricks Insights"])

# Game Tab - NEW THREE COLUMN LAYOUT
with tab1:
    # Create three columns with appropriate width ratios
    control_col, map_col, info_col = st.columns([1, 2, 1])  # Controls, Map, Game Info
    
    with control_col:
        # Left Column: Game Controls
        if st.session_state.game and st.session_state.game.game_active:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Game Controls")
            
            # Current location
            current_location = st.session_state.game.current_location
            st.info(f"Current Location: {current_location}")
            
            # Movement buttons
            available_moves = st.session_state.game.get_available_moves()
            
            if available_moves:
                st.subheader("Available Moves")
                
                for move in available_moves:
                    location = move["location"]
                    distance = move["distance"]
                    has_packages = move["has_packages"]
                    
                    button_label = f"{LOCATIONS[location]['emoji']} {location} ({distance} cm)"
                    if has_packages:
                        button_label += " 📦"
                    
                    # Add warning indicator for constraint violations
                    if move.get("violates_constraint", False):
                        button_label += " ⚠️"
                    
                    if st.button(button_label, key=f"move_{location}", use_container_width=True):
                        # Show warning if this move would violate a constraint
                        if move.get("violates_constraint", False):
                            st.warning(f"⚠️ WARNING: {move['constraint_message']} Your score will be reduced.")
                        
                        # Process the move
                        result = st.session_state.game.move_to_location(location)
                        if result["success"]:
                            if "constraint_violated" in result and result["constraint_violated"]:
                                st.warning(result["message"])
                            if "game_completed" in result and result["game_completed"]:
                                st.session_state.game_results = result["results"]
                                
                                # Add to leaderboard
                                if st.session_state.current_player and st.session_state.game_results:
                                    leaderboard_entry = leaderboard_manager.add_leaderboard_entry(
                                        st.session_state.current_player,
                                        st.session_state.game_results
                                    )
                                    
                                    # Add to session state leaderboard
                                    if 'leaderboard' not in st.session_state:
                                        st.session_state.leaderboard = []
                                    st.session_state.leaderboard.append(leaderboard_entry)
                                
                                st.session_state.game = None
                            st.rerun()
                        else:
                            st.error(result["message"])
            else:
                st.warning("No available moves from this location. You may have reached a dead end!")
            
            # Package Pickup/Delivery Actions
            st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)
            st.subheader("Package Actions")
            
            if st.session_state.game.package_manager.carrying:
                # Show delivery option if at the right location
                carrying = st.session_state.game.package_manager.carrying
                
                if carrying.delivery == current_location:
                    if st.button(f"📦 Deliver Package #{carrying.id} to {carrying.delivery}", 
                              key="deliver_package", 
                              type="primary", 
                              use_container_width=True):
                        result = st.session_state.game.deliver_package()
                        
                        if result["success"]:
                            st.success(result["message"])
                            
                            if "game_completed" in result and result["game_completed"]:
                                st.session_state.game_results = result["results"]
                                
                                # Add to leaderboard
                                if st.session_state.current_player and st.session_state.game_results:
                                    leaderboard_entry = leaderboard_manager.add_leaderboard_entry(
                                        st.session_state.current_player,
                                        st.session_state.game_results
                                    )
                                    
                                    if 'leaderboard' not in st.session_state:
                                        st.session_state.leaderboard = []
                                    st.session_state.leaderboard.append(leaderboard_entry)
                                
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
                    for pkg in available_packages:
                        if st.button(f"📦 Pick up Package #{pkg.id} to {pkg.delivery}", 
                                  key=f"pickup_{pkg.id}", 
                                  type="primary", 
                                  use_container_width=True):
                            result = st.session_state.game.pickup_package(pkg.id)
                            
                            if result["success"]:
                                st.success(result["message"])
                                st.rerun()
                            else:
                                st.error(result["message"])
                else:
                    st.info("No packages to pick up here.")
                    
            # Show active constraints based on difficulty
            st.markdown('<div style="margin-top: 20px;"></div>', unsafe_allow_html=True)
            st.subheader("Active Constraints")
            active_constraints = st.session_state.game.constraints.get_active_constraints()
            if active_constraints:
                for constraint in active_constraints:
                    st.info(f"{constraint[0]} must be visited before {constraint[1]}")
            else:
                st.info("No ordering constraints in this difficulty level.")
                
            # Show constraint violations
            violated_constraints = st.session_state.game.violated_constraints
            if violated_constraints:
                st.subheader("⚠️ Constraint Violations")
                for constraint in violated_constraints:
                    st.markdown(f'<div class="constraint-warning">{constraint[0]} must be visited before {constraint[1]} - Violated!</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        elif not st.session_state.game_results:
            # New Game panel if no active game
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Player Registration")
            
            with st.form("registration_form"):
                name = st.text_input("Name*")
                email = st.text_input("Email*")
                company = st.text_input("Company")
                
                # Add privacy notice
                st.caption("Game results will be used for analytics and leaderboard. Your data is stored securely.")
                
                st.subheader("Game Challenge")
                st.markdown("Master all logistics challenges in one comprehensive experience")
                
                difficulty = st.radio("Select Difficulty Level", 
                                    ["Easy (1 road closure, no constraints)", 
                                     "Medium (2 road closures, 1 constraint)", 
                                     "Hard (3 road closures, 2 constraints)"],
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
                        
                        # Add player info to game for export
                        st.session_state.game.player_info = {
                            "player_name": name,
                            "email": email,
                            "company": company
                        }
                        
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        elif st.session_state.game_results:
            # Show Play Again button in the controls column
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.subheader("Game Complete!")
            
            if st.button("Play Again", type="primary", use_container_width=True):
                st.session_state.game_results = None
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    with map_col:
        # Middle Column: Map Section
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        if st.session_state.game and st.session_state.game.game_active:
            # Show active game map
            current_location = st.session_state.game.current_location
            available_moves = st.session_state.game.get_available_moves()
            
            map_fig = visualize_map(
                current_location=current_location,
                available_moves=available_moves,
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
        
        # Current route display below the map
        if st.session_state.game and st.session_state.game.game_active and st.session_state.game.current_route:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### Your Route")
            st.code(" → ".join(st.session_state.game.current_route))
            
            # Show route distance
            total_distance = 0
            route = st.session_state.game.current_route
            for i in range(len(route) - 1):
                segment_distance = st.session_state.game.graph.get_edge_weight(route[i], route[i+1])
                if segment_distance:
                    total_distance += segment_distance
            
            st.metric("Total Distance", f"{total_distance:.1f} cm")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with info_col:
        # Right Column: Game Info Panel
        if st.session_state.game and st.session_state.game.game_active:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            
            game_status = st.session_state.game.get_game_status()
            
            st.markdown('<div class="status-bar">', unsafe_allow_html=True)
            st.markdown(f"⏱ **Time:** {game_status['time']:.1f}s | 📦 **Packages:** {game_status['packages_delivered']}/{game_status['total_packages']} | 🌐 **Progress:** {game_status['progress']}%")
            st.markdown('</div>', unsafe_allow_html=True)
            
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
            
            # Display all packages status
            packages = st.session_state.game.package_manager.get_package_info()
            st.markdown("### Package Status")
            for pkg in packages:
                icon = "✅" if pkg["status"] == "delivered" else "🚚" if pkg["status"] == "picked_up" else "⏳"
                st.markdown(f"{icon} **Package #{pkg['id']}**: {pkg['pickup']} → {pkg['delivery']} ({pkg['status']})")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Difficulty
            difficulty_names = {1: "Easy", 2: "Medium", 3: "Hard"}
            difficulty = difficulty_names.get(st.session_state.game.difficulty, "Easy")
            st.markdown(f"**Difficulty:** {difficulty} ({len(st.session_state.game.closed_roads)} closure{'s' if len(st.session_state.game.closed_roads) > 1 else ''})")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Results Panel for completed game
        elif st.session_state.game_results:
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
            
            # Results metrics
            st.metric("Time", f"{results['time']:.1f}s")
            st.metric("Your Distance", f"{results['player_distance']:.1f} cm")
            st.metric("Efficiency", f"{results['efficiency']}%")
            st.metric("Optimal Distance", f"{results['optimal_distance']:.1f} cm")
            
            # Display constraint violations if any occurred
            if results.get('active_constraints') and results.get('violated_constraints'):
                violated_count = len(results.get('violated_constraints', []))
                if violated_count > 0:
                    st.warning(f"You violated {violated_count} constraint(s), reducing your score.")
                    
                    with st.expander("Score Breakdown"):
                        st.markdown("### Score Components")
                        st.markdown(f"- **Efficiency (40%)**: {results['efficiency']}%")
                        st.markdown(f"- **Delivery (30%)**: 100%")
                        st.markdown(f"- **Constraints (20%)**: {results['constraints_score']}% (Penalty for {violated_count} violation(s))")
                        
                        # Calculate time score from results
                        time_score = results['score'] - (
                            (results['efficiency'] * 0.4) + 
                            (100 * 0.3) + 
                            (results['constraints_score'] * 0.2)
                        ) / 0.1
                        st.markdown(f"- **Time (10%)**: {int(time_score)}%")
                        
                        for constraint in results.get('violated_constraints', []):
                            st.error(f"Violated: {constraint[0]} must be visited before {constraint[1]}")
            
            # Special message for finding a better route
            if results.get('found_better_route', False):
                st.success("🏆 Congratulations! You found a more efficient route than the algorithm calculated!")
                
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Routes comparison
            st.markdown('<div class="card">', unsafe_allow_html=True)
            route_tabs = st.tabs(["Your Route", "Optimal Route"])
            
            with route_tabs[0]:
                st.markdown("**Your Route:**")
                st.code(" → ".join(results['player_route']))
                
                # Show route segments
                total_distance = 0
                for i in range(len(results['player_route']) - 1):
                    start = results['player_route'][i]
                    end = results['player_route'][i+1]
                    
                    # We can get segment distance from the results
                    segment_distance = results.get('enhanced_diagnostics', {}).get('move_history', [])[i].get('distance', 0)
                    total_distance += segment_distance
                    
                    # Check if this move violated a constraint
                    violated_constraint = results.get('enhanced_diagnostics', {}).get('move_history', [])[i].get('violated_constraint')
                    violation_info = ""
                    if violated_constraint:
                        violation_info = f" ⚠️ Violated constraint: {violated_constraint[0]} → {violated_constraint[1]}"
                    
                    st.markdown(f"**Step {i+1}:** {start} → {end} ({segment_distance} cm){violation_info}")
            
            with route_tabs[1]:
                st.markdown("**Optimal Route:**")
                st.code(" → ".join(results['optimal_route']))
                
                # Show optimal route segments
                st.metric("Optimal Distance", f"{results['optimal_distance']:.1f} cm")
                
                # Show package operations if available
                if 'optimal_package_operations' in results:
                    st.markdown("**Optimal Package Operations:**")
                    for op in results['optimal_package_operations']:
                        location, action, pkg_id = op
                        action_icon = "📦➡️" if action == "pickup" else "📦✅"
                        st.markdown(f"- {action_icon} {action.capitalize()} Package #{pkg_id} at {location}")
            
            st.markdown('</div>', unsafe_allow_html=True)

# Leaderboard Tab
with tab2:
    st.subheader("Leaderboard")
    
    # Add a refresh button
    if st.button("🔄 Refresh Leaderboard Data"):
        # Fetch latest data from Databricks
        st.session_state.leaderboard = leaderboard_manager.fetch_leaderboard()
        st.success("Leaderboard refreshed!")
    
    # Add CSV download button
    csv_data = leaderboard_manager.get_leaderboard_csv()
    st.download_button(
        label="📥 Download Leaderboard as CSV",
        data=csv_data,
        file_name="logistics_rush_leaderboard.csv",
        mime="text/csv",
    )
    
    # Filter controls
    lb_col1, lb_col2 = st.columns(2)
    with lb_col1:
        sort_by = st.selectbox("Sort By", ["Score", "Time", "Efficiency"])
    with lb_col2:
        # Get all companies
        companies = ["All Companies"]
        
        # Initialize leaderboard if it's empty
        if not st.session_state.leaderboard:
            st.session_state.leaderboard = leaderboard_manager.fetch_leaderboard()
            
        for entry in st.session_state.leaderboard:
            if entry.get("company") and entry["company"] not in companies:
                companies.append(entry["company"])
                
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
            
            # Select and rename columns (including email)
            display_df = df[["rank", "name", "email", "company", "time", "efficiency", "score", "timestamp"]]
            display_df.columns = ["Rank", "Player", "Email", "Company", "Time", "Efficiency", "Score", "Date"]
            
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
    4. **Deliver** packages while following constraints (if applicable)
    5. **Complete** to see your score

    ### Difficulty Levels
    - **Easy**: 1 road closure, no ordering constraints
    - **Medium**: 2 road closures, 1 ordering constraint (Warehouse before Shop)
    - **Hard**: 3 road closures, 2 ordering constraints (Warehouse before Shop AND Distribution Center before Home)

    ### Rules
    - You can only carry one package at a time
    - All locations must be visited
    - All packages must be delivered
    - Violating constraints will reduce your score, but you can continue playing

    ### Scoring
    Your score is based on efficiency (40%), package delivery (30%), following constraints (20%), and time (10%).

    Try to find a more efficient route than the AI's calculated optimal path to earn a perfect efficiency score!
    """)

# Diagnostics Tab
with tab4:
    add_diagnostics_tab()

# Databricks Insights Tab
with tab5:
    st.title("Databricks Analytics Insights")
    st.markdown("### Game Performance Analytics")
    
    # Fetch insights
    insights = insights_fetcher.get_insights()
    
    # Show last updated
    st.caption(f"Last updated: {insights['last_updated']}")
    
    # Game Statistics
    stats = insights["statistics"]
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Games", stats["total_games"])
    with col2:
        st.metric("Avg Score", stats["avg_score"])
    with col3:
        st.metric("Avg Efficiency", f"{stats['avg_efficiency']}%")
    with col4:
        st.metric("Avg Time", f"{stats['avg_time']}s")
    
    # Best Routes
    st.markdown("### 🥇 Best Routes by Difficulty")
    
    for route in insights["best_routes"]:
        difficulty = "Easy" if route["difficulty"] == 1 else "Medium" if route["difficulty"] == 2 else "Hard"
        st.markdown(f"**{difficulty}**: {route['route']} (Avg Score: {route['avg_score']:.1f})")
    
    # Common Violations
    if insights["common_violations"]:
        st.markdown("### ⚠️ Most Common Constraint Violations")
        
        for violation in insights["common_violations"]:
            # Clean up constraint string
            constraint = violation["constraint"].replace("'", "").replace("(", "").replace(")", "").split(", ")
            if len(constraint) >= 2:
                st.warning(f"{constraint[0]} → {constraint[1]} (Violated {violation['frequency']} times)")
    
    # Pro Tips
    st.markdown("### 💡 Pro Tips")
    st.info("**Tip 1:** Start by planning your route to minimize backtracking through closed roads.")
    st.info("**Tip 2:** Prioritize package pickup at the Warehouse first to avoid constraint violations.")
    st.info("**Tip 3:** For highest scores, try to match or beat the optimal route distance.")
    
    # Add a placeholder for interactive visualization
    st.markdown("### 📊 Score Distribution")
    
    # Simulated chart data for placeholder
    chart_data = {
        "0-20": 2,
        "21-40": 5,
        "41-60": 12,
        "61-80": 18,
        "81-100": 15
    }
    
    # Display as a bar chart
    st.bar_chart(chart_data)
    
    # Add explanation of Databricks integration
    with st.expander("How is Databricks powering these insights?"):
        st.markdown("""
        This integration demonstrates a modern data analytics pipeline:
        
        1. **Data Collection**: Game results are automatically exported to Azure Blob Storage
        2. **Data Processing**: Azure Databricks reads and processes this data using Delta Lake
        3. **Analytics**: Spark SQL queries analyze patterns and identify optimal strategies
        4. **Insights Generation**: Results are processed into actionable insights
        5. **Insights Delivery**: This tab fetches and displays the latest analytics
        
        The entire pipeline uses Azure's managed services for a scalable, production-ready architecture.
        """)

# Main function
if __name__ == "__main__":
    pass  # Already running in Streamlit