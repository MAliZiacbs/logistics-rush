# game_engine.py

import streamlit as st
import time
import diagnostics
import route_analysis

from config import LOCATIONS, check_constraints
from routing import solve_tsp_improved, calculate_route_distance, is_valid_route
from feature_road_closures import generate_road_closures
from feature_packages import generate_packages
from data_management import save_player_data

def start_new_game():
    """Start a new game session."""
    st.session_state.game_active = True
    st.session_state.start_time = time.time()
    diagnostics.init_diagnostics()
    st.session_state.current_package = None
    st.session_state.delivered_packages = []
    st.session_state.current_route = ["Warehouse"]  # Starting point
    st.session_state.optimal_route = None
    st.session_state.optimal_path = None

    st.session_state.constraints = {
        "Warehouse": "Must visit before Shop",
        "Shop": "Must visit after Warehouse",
        "Distribution Center": "Must visit before Home",
        "Home": "Must visit after Distribution Center"
    }

    # Generate packages
    st.session_state.packages = generate_packages(num_packages=3)
    st.session_state.total_packages = len(st.session_state.packages)

    # Generate road closures based on selected difficulty
    num_closures = st.session_state.get('num_road_closures', 1)
    try:
        closures = generate_road_closures(num_closures=num_closures)
        st.session_state.closed_roads = closures
        diagnostics.log_event("Game Start", f"Applied road closures: {closures}")
    except Exception as e:
        st.warning(f"Using default road closures due to error: {e}")
        st.session_state.closed_roads = [("Warehouse", "Shop")]
        diagnostics.log_error("Road Closure Generation", str(e))

    # Calculate optimal route using improved TSP solver
    start_location = "Warehouse"
    locations = list(LOCATIONS.keys())
    try:
        optimal_route, optimal_path, optimal_distance = solve_tsp_improved(start_location, locations, st.session_state.packages)
        if not is_valid_route(optimal_route):
            diagnostics.log_error("Optimal Route Validation", "Route validation failed, using fallback")
            from routing import nearest_neighbor_route
            optimal_route = nearest_neighbor_route(start_location, locations)
            _, optimal_distance = calculate_route_distance(optimal_route)
        st.session_state.optimal_route = optimal_route
        st.session_state.optimal_path = optimal_route
        st.session_state.optimal_distance = optimal_distance if optimal_distance != float('inf') else 0
        diagnostics.log_optimal_route_data(optimal_route, optimal_route, optimal_distance)
    except Exception as e:
        st.error(f"Route calculation error: {e}")
        diagnostics.log_error("Route Calculation Error", str(e))
        fallback_route = list(LOCATIONS.keys())
        st.session_state.optimal_route = fallback_route
        st.session_state.optimal_path = fallback_route
        st.session_state.optimal_distance = 1000

    route_analysis.init_route_tracking()

def process_location_checkin(location):
    """Process player check-in at a given location."""
    if not st.session_state.game_active:
        st.warning("Please start a new game first!")
        return None

    diagnostics.log_route_change(location, True)
    if st.session_state.current_route:
        current_location = st.session_state.current_route[-1]
        if is_road_closed(current_location, location):
            st.error(f"❌ Road from {current_location} to {location} is closed!")
            diagnostics.log_route_change(location, False)
            return None
    temp_route = st.session_state.current_route + [location]
    if not check_constraints(temp_route):
        st.error("Route constraints violated!")
        diagnostics.log_route_change(location, False)
        return None

    st.session_state.current_route.append(location)
    # Check for delivery
    if st.session_state.current_package and st.session_state.current_package["delivery"] == location:
        pkg_id = st.session_state.current_package["id"]
        st.session_state.current_package["status"] = "delivered"
        st.session_state.delivered_packages.append(st.session_state.current_package)
        diagnostics.log_package_operation("delivery", location, pkg_id)
        st.session_state.current_package = None
        st.success(f"Package #{pkg_id} delivered at {location}!")
    route_analysis.record_delivery(location, st.session_state.current_package["id"] if st.session_state.current_package else None)
    return True
