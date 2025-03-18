import streamlit as st
import numpy as np
import time

from config import LOCATIONS, SCORING_WEIGHTS, check_constraints  # Updated import
from routing import solve_tsp, get_distance
from feature_road_closures import generate_road_closures, is_road_closed
from feature_packages import generate_packages
from data_management import save_player_data

def start_new_game():
    """Start a new game with all features combined"""
    st.session_state.game_active = True
    st.session_state.start_time = time.time()
    
    # Reset any previous game state
    st.session_state.current_package = None
    st.session_state.delivered_packages = []
    
    # Locations to visit
    locations_to_visit = [loc for loc in LOCATIONS.keys() if loc != "Central Hub"]

    # Starting location is always Factory in the combined mode
    start_location = "Factory"

    # Set constraints for all games
    st.session_state.constraints = {
        "Factory": "Must visit before Shop",
        "Shop": "Must visit after Factory",
        "DHL Hub": "Must visit before Residence",
        "Residence": "Must visit after DHL Hub"
    }
    
    # Generate road closures for all games
    st.session_state.closed_roads = generate_road_closures(num_closures=2)
    
    # Generate packages for all games
    st.session_state.packages = generate_packages(num_packages=3)
    st.session_state.total_packages = len(st.session_state.packages)

    # Solve TSP with all constraints in mind
    optimal_route, optimal_distance = solve_tsp(start_location, locations_to_visit)
    
    # If no valid route is found (due to road closures), try to find a route through Central Hub
    if optimal_route is None:
        st.warning("Road closures make direct routes impossible! Try routing through Central Hub.")
        # Add Central Hub as a mandatory waypoint for the route
        expanded_locations = locations_to_visit + ["Central Hub"]
        optimal_route, optimal_distance = solve_tsp(start_location, expanded_locations)

    # Initialize route
    st.session_state.current_route = [start_location]
    st.session_state.optimal_route = optimal_route if optimal_route else [start_location]

def process_location_checkin(location):
    """Process a player checking in at a location"""
    if not st.session_state.game_active:
        st.warning("Please start a new game first!")
        return None
        
    # Check if the move is valid (no closed roads)
    if len(st.session_state.current_route) > 0:
        current_location = st.session_state.current_route[-1]
        if is_road_closed(current_location, location):
            st.error(f"❌ Road from {current_location} to {location} is closed! Find another route.")
            return None

    # Constraints check using centralized function
    temp_route = st.session_state.current_route + [location]
    if not check_constraints(temp_route):
        if location == "Shop" and "Factory" not in st.session_state.current_route:
            st.error("You must visit Factory before Shop!")
        elif location == "Residence" and "DHL Hub" not in st.session_state.current_route:
            st.error("You must visit DHL Hub before Residence!")
        return None
            
    # Package Delivery mode checks
    if st.session_state.current_package and st.session_state.current_package["delivery"] == location:
        # Package delivered successfully
        st.session_state.current_package["status"] = "delivered"
        st.session_state.delivered_packages.append(st.session_state.current_package)
        st.session_state.current_package = None
        st.success(f"📦 Package delivered successfully to {location}!")
        
    # Check for available pickups at this location
    available_pickups = [p for p in st.session_state.packages 
                         if p["pickup"] == location and p["status"] == "waiting"]
    if available_pickups and not st.session_state.current_package:
        # Player is at a pickup location with packages waiting
        st.info(f"📦 There are {len(available_pickups)} packages available for pickup at {location}!")

    # Add location to route
    st.session_state.current_route.append(location)
    
    # Check win condition - need to visit all locations AND deliver all packages
    main_locations = [loc for loc in LOCATIONS.keys() if loc != "Central Hub"]
    all_locations_visited = all(loc in st.session_state.current_route for loc in main_locations)
    all_packages_delivered = len(st.session_state.delivered_packages) == st.session_state.total_packages
    
    # Game is complete when both conditions are met
    if all_locations_visited and all_packages_delivered:
        if st.session_state.current_route[0] != st.session_state.current_route[-1]:
            # Add return to starting point if needed and possible
            if not is_road_closed(st.session_state.current_route[-1], st.session_state.current_route[0]):
                st.session_state.current_route.append(st.session_state.current_route[0])
        return end_game()
            
    return None

def pickup_package(package):
    """Pick up a package at the current location"""
    if not st.session_state.game_active or not package:
        return
    
    # Mark package as picked up and set as current package
    package["status"] = "picked_up"
    st.session_state.current_package = package
    st.success(f"Package #{package['id']} picked up! Deliver to {package['delivery']}.")

def get_game_status():
    """Get current game status including time, progress, etc."""
    if not st.session_state.game_active:
        return None
        
    game_time = time.time() - st.session_state.start_time
    
    # Calculate both locations progress and package delivery progress
    loc_visited = len(set([loc for loc in st.session_state.current_route 
                          if loc != "Central Hub"]))
    total_loc = len([loc for loc in LOCATIONS.keys() if loc != "Central Hub"])
    loc_progress = min(100, int((loc_visited / total_loc) * 100))
    
    pkg_progress = min(100, int((len(st.session_state.delivered_packages) / 
                              max(1, st.session_state.total_packages)) * 100))
    
    # Combined progress (average of both)
    combined_progress = (loc_progress + pkg_progress) // 2
    
    return {
        "time": game_time,
        "location_progress": loc_progress,
        "package_progress": pkg_progress,
        "combined_progress": combined_progress,
        "progress_text": f"Overall Progress: {combined_progress}%"
    }

def end_game():
    """End the game and calculate results"""
    if not st.session_state.game_active:
        return None

    game_time = time.time() - st.session_state.start_time

    # Distances
    optimal_distance = 0
    if st.session_state.optimal_route and len(st.session_state.optimal_route) > 1:
        for i in range(len(st.session_state.optimal_route) - 1):
            segment_distance = get_distance(st.session_state.optimal_route[i], st.session_state.optimal_route[i+1])
            if segment_distance != float('inf'):  # Skip closed roads in calculation
                optimal_distance += segment_distance

    player_distance = 0
    for i in range(len(st.session_state.current_route) - 1):
        segment_distance = get_distance(st.session_state.current_route[i], st.session_state.current_route[i+1])
        if segment_distance != float('inf'):  # Skip closed roads in calculation
            player_distance += segment_distance

    # Avoid division by zero
    if player_distance > 0 and optimal_distance > 0:
        efficiency = min(100, int((optimal_distance / player_distance) * 100))
    else:
        efficiency = 0

    # Combined scoring for the unified game mode
    weights = SCORING_WEIGHTS["Logistics Challenge"]
    
    # Base score components
    time_factor = max(0, 100 - (game_time / 3))  # More lenient time factor for combined mode
    
    # Calculate constraint adherence using centralized function
    constraints_followed = check_constraints(st.session_state.current_route)
    constraint_factor = 100 if constraints_followed else 0
    
    # Calculate delivery success rate
    delivery_percent = min(100, int((len(st.session_state.delivered_packages) / 
                                   max(1, st.session_state.total_packages)) * 100))
    
    # Score components for detailed breakdown
    score_components = {
        "efficiency": efficiency * weights["efficiency"],
        "delivery": delivery_percent * weights["delivery"],
        "constraints": constraint_factor * weights["constraints"],
        "time": time_factor * weights["time"]
    }
    
    # Calculate final score
    score = int(sum(score_components.values()))
    score = max(0, min(100, score))  # Ensure score is between 0-100

    # Save completion data
    st.session_state.completed_routes = {
        "player": st.session_state.current_route.copy(),
        "optimal": st.session_state.optimal_route.copy()
    }
    
    # Save player data
    if st.session_state.current_player:
        result_data = {
            "time": game_time,
            "efficiency": efficiency,
            "delivery": delivery_percent,
            "constraints": constraint_factor,
            "score": score,
            "route": st.session_state.current_route.copy()
        }
        save_player_data(result_data)
    
    st.session_state.game_active = False

    # Return results
    results = {
        "time": game_time,
        "efficiency": efficiency,
        "score": score,
        "optimal_distance": optimal_distance,
        "player_distance": player_distance,
        "score_components": score_components,
        "delivery_percent": delivery_percent,
        "constraints_followed": constraints_followed
    }
    
    # Store results
    st.session_state.game_results = results
    
    return results

def get_completion_summary():
    """Get a summary of completion status for all game aspects"""
    if not st.session_state.game_active:
        return None
        
    # Location visits
    main_locations = [loc for loc in LOCATIONS.keys() if loc != "Central Hub"]
    visited_locations = [loc for loc in main_locations if loc in st.session_state.current_route]
    remaining_locations = [loc for loc in main_locations if loc not in st.session_state.current_route]
    
    # Package deliveries
    delivered_packages = len(st.session_state.delivered_packages)
    total_packages = st.session_state.total_packages
    remaining_packages = total_packages - delivered_packages
    
    # Constraint check using centralized function
    constraints_followed = check_constraints(st.session_state.current_route)
    constraint_issues = []
    
    if not constraints_followed:
        if "Factory" in st.session_state.current_route and "Shop" in st.session_state.current_route:
            f_idx = st.session_state.current_route.index("Factory")
            s_idx = st.session_state.current_route.index("Shop")
            if f_idx > s_idx:
                constraint_issues.append("Shop was visited before Factory")
        if "DHL Hub" in st.session_state.current_route and "Residence" in st.session_state.current_route:
            d_idx = st.session_state.current_route.index("DHL Hub")
            r_idx = st.session_state.current_route.index("Residence")
            if d_idx > r_idx:
                constraint_issues.append("Residence was visited before DHL Hub")
    
    return {
        "visited_locations": visited_locations,
        "remaining_locations": remaining_locations,
        "delivered_packages": delivered_packages,
        "total_packages": total_packages,
        "remaining_packages": remaining_packages,
        "constraints_followed": constraints_followed,
        "constraint_issues": constraint_issues
    }