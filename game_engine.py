import streamlit as st
import numpy as np
import time

from config import LOCATIONS, SCORING_WEIGHTS, check_constraints
from routing import solve_tsp, get_distance, calculate_route_distance
from feature_road_closures import generate_road_closures, is_road_closed
from feature_packages import generate_packages
from data_management import save_player_data

def start_new_game():
    """Start a new game with all features combined"""
    st.session_state.game_active = True
    st.session_state.start_time = time.time()
    
    st.session_state.current_package = None
    st.session_state.delivered_packages = []
    st.session_state.current_route = []
    st.session_state.optimal_route = None
    st.session_state.optimal_path = None
    
    locations_to_visit = [loc for loc in LOCATIONS.keys() if loc != "Central Hub"]
    start_location = "Factory"

    st.session_state.constraints = {
        "Factory": "Must visit before Shop",
        "Shop": "Must visit after Factory",
        "DHL Hub": "Must visit before Residence",
        "Residence": "Must visit after DHL Hub"
    }
    
    st.session_state.closed_roads = generate_road_closures(num_closures=2)
    st.session_state.packages = generate_packages(num_packages=3)
    st.session_state.total_packages = len(st.session_state.packages)

    # Try to find an optimal route
    optimal_route, optimal_path, optimal_distance = solve_tsp(start_location, locations_to_visit)
    if optimal_route is None:
        st.warning("Optimal route calculation failed. Using fallback route via Central Hub.")
        # Fallback route ensuring all locations are visited
        fallback_route = [
            {"location": start_location, "action": "visit", "package_id": None},
            {"location": "Central Hub", "action": "visit", "package_id": None}
        ]
        for loc in locations_to_visit:
            if loc != start_location:
                fallback_route.append({"location": loc, "action": "visit", "package_id": None})
        fallback_route.append({"location": start_location, "action": "visit", "package_id": None})
        full_path, _, optimal_distance = calculate_route_distance(fallback_route)
        optimal_path = full_path if full_path else [start_location]
        optimal_route = fallback_route

    st.session_state.current_route = [start_location]
    st.session_state.optimal_route = optimal_route
    st.session_state.optimal_path = optimal_path

def process_location_checkin(location):
    """Process a player checking in at a location"""
    if not st.session_state.game_active:
        st.warning("Please start a new game first!")
        return None
        
    if len(st.session_state.current_route) > 0:
        current_location = st.session_state.current_route[-1]
        if is_road_closed(current_location, location):
            st.error(f"❌ Road from {current_location} to {location} is closed! Find another route.")
            return None

    temp_route = st.session_state.current_route + [location]
    if not check_constraints(temp_route):
        if location == "Shop" and "Factory" not in st.session_state.current_route:
            st.error("You must visit Factory before Shop!")
        elif location == "Residence" and "DHL Hub" not in st.session_state.current_route:
            st.error("You must visit DHL Hub before Residence!")
        return None
            
    if st.session_state.current_package and st.session_state.current_package["delivery"] == location:
        st.session_state.current_package["status"] = "delivered"
        st.session_state.delivered_packages.append(st.session_state.current_package)
        st.session_state.current_package = None
        st.success(f"📦 Package delivered successfully to {location}!")
        
    available_pickups = [p for p in st.session_state.packages 
                         if p["pickup"] == location and p["status"] == "waiting"]
    if available_pickups and not st.session_state.current_package:
        st.info(f"📦 There are {len(available_pickups)} packages available for pickup at {location}!")

    st.session_state.current_route.append(location)
    
    main_locations = [loc for loc in LOCATIONS.keys() if loc != "Central Hub"]
    all_locations_visited = all(loc in st.session_state.current_route for loc in main_locations)
    all_packages_delivered = len(st.session_state.delivered_packages) == st.session_state.total_packages
    
    if all_locations_visited and all_packages_delivered:
        if st.session_state.current_route[0] != st.session_state.current_route[-1]:
            if not is_road_closed(st.session_state.current_route[-1], st.session_state.current_route[0]):
                st.session_state.current_route.append(st.session_state.current_route[0])
        return end_game()
            
    return None

def pickup_package(package):
    """Pick up a package at the current location"""
    if not st.session_state.game_active or not package:
        return
    package["status"] = "picked_up"
    st.session_state.current_package = package
    st.success(f"Package #{package['id']} picked up! Deliver to {package['delivery']}.")

def get_game_status():
    """Get current game status including time, progress, etc."""
    if not st.session_state.game_active:
        return None
        
    game_time = time.time() - st.session_state.start_time
    loc_visited = len(set([loc for loc in st.session_state.current_route if loc != "Central Hub"]))
    total_loc = len([loc for loc in LOCATIONS.keys() if loc != "Central Hub"])
    loc_progress = min(100, int((loc_visited / total_loc) * 100))
    pkg_progress = min(100, int((len(st.session_state.delivered_packages) / max(1, st.session_state.total_packages)) * 100))
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

    _, optimal_distance = calculate_route_distance(st.session_state.optimal_route)
    if optimal_distance == float('inf'):
        optimal_distance = 0  # Fallback if no valid optimal route
    player_distance = 0
    for i in range(len(st.session_state.current_route) - 1):
        segment_distance = get_distance(st.session_state.current_route[i], st.session_state.current_route[i+1])
        if segment_distance != float('inf'):
            player_distance += segment_distance

    efficiency = min(100, int((optimal_distance / player_distance) * 100)) if player_distance > 0 and optimal_distance > 0 else 0
    weights = SCORING_WEIGHTS["Logistics Challenge"]
    time_factor = max(0, 100 - (game_time / 3))
    constraints_followed = check_constraints(st.session_state.current_route)
    constraint_factor = 100 if constraints_followed else 0
    delivery_percent = min(100, int((len(st.session_state.delivered_packages) / max(1, st.session_state.total_packages)) * 100))
    
    score_components = {
        "efficiency": efficiency * weights["efficiency"],
        "delivery": delivery_percent * weights["delivery"],
        "constraints": constraint_factor * weights["constraints"],
        "time": time_factor * weights["time"]
    }
    player_score = int(sum(score_components.values()))
    player_score = max(0, min(100, player_score))

    # Calculate optimal score (assuming fastest time and all deliveries)
    optimal_time = optimal_distance * 2  # Arbitrary: 2 seconds per unit distance
    optimal_time_factor = max(0, 100 - (optimal_time / 3))
    optimal_score_components = {
        "efficiency": 100 * weights["efficiency"],
        "delivery": 100 * weights["delivery"],
        "constraints": 100 * weights["constraints"],
        "time": optimal_time_factor * weights["time"]
    }
    optimal_score = int(sum(optimal_score_components.values()))
    optimal_score = max(0, min(100, optimal_score))
    
    improvement_percent = ((optimal_score - player_score) / player_score * 100) if player_score > 0 else 0

    st.session_state.completed_routes = {
        "player": st.session_state.current_route.copy(),
        "optimal": st.session_state.optimal_path.copy() if st.session_state.optimal_path else []
    }
    
    if st.session_state.current_player:
        result_data = {
            "time": game_time,
            "efficiency": efficiency,
            "delivery": delivery_percent,
            "constraints": constraint_factor,
            "score": player_score,
            "route": st.session_state.current_route.copy()
        }
        save_player_data(result_data)
    
    st.session_state.game_active = False

    results = {
        "time": game_time,
        "efficiency": efficiency,
        "score": player_score,
        "optimal_distance": optimal_distance,
        "player_distance": player_distance,
        "score_components": score_components,
        "delivery_percent": delivery_percent,
        "constraints_followed": constraints_followed,
        "optimal_score": optimal_score,
        "improvement_percent": improvement_percent
    }
    st.session_state.game_results = results
    return results

def get_completion_summary():
    """Get a summary of completion status for all game aspects"""
    if not st.session_state.game_active:
        return None
        
    main_locations = [loc for loc in LOCATIONS.keys() if loc != "Central Hub"]
    visited_locations = [loc for loc in main_locations if loc in st.session_state.current_route]
    remaining_locations = [loc for loc in main_locations if loc not in st.session_state.current_route]
    delivered_packages = len(st.session_state.delivered_packages)
    total_packages = st.session_state.total_packages
    remaining_packages = total_packages - delivered_packages
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