# feature_road_closures.py

import streamlit as st
import random
import networkx as nx
from config import LOCATIONS, ROAD_SEGMENTS, DISTANCES
import diagnostics

def is_road_closed(loc1, loc2):
    if 'closed_roads' not in st.session_state:
        return False
    return (loc1, loc2) in st.session_state.closed_roads or (loc2, loc1) in st.session_state.closed_roads

def validate_package_delivery(G, packages):
    from routing import calculate_segment_path
    for pkg in packages:
        pickup = pkg["pickup"]
        delivery = pkg["delivery"]
        segment_path, segment_distance = calculate_segment_path(pickup, delivery)
        if segment_path is None or segment_distance == float('inf'):
            diagnostics.log_error("Package Delivery Validation", f"No path for package from {pickup} to {delivery}")
            return False
    # Ensure critical routes exist:
    w_to_s, _ = calculate_segment_path("Warehouse", "Shop")
    dc_to_h, _ = calculate_segment_path("Distribution Center", "Home")
    if w_to_s is None or dc_to_h is None:
        diagnostics.log_error("Constraint Validation", "No valid paths for constraint requirements")
        return False
    return True

def generate_road_closures(num_closures=1, max_attempts=100):
    diagnostics.log_event("Road Closure Generation", f"Generating {num_closures} closures")
    num_closures = min(num_closures, 3)
    # Define safe closures that preserve critical segments
    safe_closures = {
        1: [
            [("Warehouse", "Home")],
            [("Distribution Center", "Shop")]
        ],
        2: [
            [("Warehouse", "Home"), ("Distribution Center", "Shop")]
        ],
        3: [
            [("Warehouse", "Home"), ("Distribution Center", "Shop"), ("Shop", "Home")]
        ]
    }
    packages = st.session_state.packages if 'packages' in st.session_state else []
    G = nx.Graph()
    for loc in LOCATIONS:
        G.add_node(loc)
    for loc1, loc2 in ROAD_SEGMENTS:
        G.add_edge(loc1, loc2)
    if num_closures in safe_closures:
        safe_options = safe_closures[num_closures].copy()
        random.shuffle(safe_options)
        for chosen in safe_options:
            test_G = G.copy()
            for road in chosen:
                if test_G.has_edge(road[0], road[1]):
                    test_G.remove_edge(road[0], road[1])
            if validate_package_delivery(test_G, packages):
                st.session_state.closed_roads = chosen
                diagnostics.log_road_closures(chosen)
                diagnostics.log_event("Road Closure Generation", f"Using safe closure set: {chosen}")
                return chosen
    all_segments = list(ROAD_SEGMENTS)
    for attempt in range(max_attempts):
        random.shuffle(all_segments)
        candidate = all_segments[:num_closures]
        test_G = G.copy()
        for road in candidate:
            if test_G.has_edge(road[0], road[1]):
                test_G.remove_edge(road[0], road[1])
        if nx.is_connected(test_G) and validate_package_delivery(test_G, packages):
            st.session_state.closed_roads = candidate
            diagnostics.log_road_closures(candidate)
            diagnostics.log_event("Road Closure Generation", f"Found valid closures after {attempt+1} attempts: {candidate}")
            return candidate
    # Fallback: try with fewer closures
    for reduced in range(num_closures-1, 0, -1):
        diagnostics.log_event("Road Closure Generation", f"Reducing to {reduced} closures")
        for attempt in range(max_attempts):
            random.shuffle(all_segments)
            candidate = all_segments[:reduced]
            test_G = G.copy()
            for road in candidate:
                if test_G.has_edge(road[0], road[1]):
                    test_G.remove_edge(road[0], road[1])
            if nx.is_connected(test_G) and validate_package_delivery(test_G, packages):
                st.session_state.closed_roads = candidate
                diagnostics.log_road_closures(candidate)
                diagnostics.log_event("Road Closure Generation", f"Found valid closures after reduction: {candidate}")
                return candidate
    diagnostics.log_event("Road Closure Generation", "No valid closures found; using no closures")
    st.session_state.closed_roads = []
    return []
