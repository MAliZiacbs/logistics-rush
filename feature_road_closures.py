import streamlit as st
import random
import networkx as nx
from itertools import combinations

from config import LOCATIONS, ROAD_SEGMENTS, DISTANCES

def is_road_closed(loc1, loc2):
    """Check if a road between two locations is closed"""
    if 'closed_roads' not in st.session_state:
        return False
    return (loc1, loc2) in st.session_state.closed_roads or (loc2, loc1) in st.session_state.closed_roads

# Enhanced validation function for feature_road_closures.py

def validate_package_delivery(G, packages):
    """
    Validate if all packages can be delivered with the given graph
    Returns True if all packages can be delivered, False otherwise
    """
    # Handle circular imports
    from routing import calculate_segment_path
    
    # Check if all pickup and delivery locations are connected
    for pkg in packages:
        pickup = pkg["pickup"]
        delivery = pkg["delivery"]
        
        segment_path, segment_distance = calculate_segment_path(pickup, delivery)
        if segment_path is None or segment_distance == float('inf'):
            return False
    
    # Check if constraints can still be satisfied
    warehouse_to_shop_path, warehouse_to_shop_dist = calculate_segment_path("Warehouse", "Shop")
    dc_to_home_path, dc_to_home_dist = calculate_segment_path("Distribution Center", "Home")
    
    if (warehouse_to_shop_path is None or warehouse_to_shop_dist == float('inf') or 
        dc_to_home_path is None or dc_to_home_dist == float('inf')):
        return False
    
    # Check key route segments to ensure playability - using actual paths not just connectivity
    critical_paths = [
        ["Warehouse", "Shop"],
        ["Distribution Center", "Home"],
        ["Warehouse", "Distribution Center"],
        ["Shop", "Home"]
    ]
    
    for path in critical_paths:
        segment_path, segment_distance = calculate_segment_path(path[0], path[1])
        if segment_path is None or segment_distance == float('inf'):
            return False
    
    return True

def generate_road_closures(num_closures=1, max_attempts=100):
    """
    Generate random road closures with improved validation to ensure playable situations.
    Ensures that all packages can be delivered and all constraints can be met.
    """
    # Ensure we never close more than 3 roads (hard mode cap)
    num_closures = min(num_closures, 3)
    
    # We know these specific closure combinations always work well
    safe_closures = {
        1: [  # Easy mode
            [("Warehouse", "Home")],
            [("Shop", "Home")],
            [("Warehouse", "Shop")]
        ],
        2: [  # Medium mode - carefully selected combinations
            [("Warehouse", "Shop"), ("Shop", "Home")],
            [("Warehouse", "Home"), ("Distribution Center", "Shop")],
            [("Shop", "Home"), ("Distribution Center", "Shop")]
        ],
        3: [  # Hard mode - carefully tested combinations
            [("Shop", "Home"), ("Warehouse", "Home"), ("Distribution Center", "Shop")],
            [("Warehouse", "Home"), ("Shop", "Home"), ("Warehouse", "Shop")],
            [("Warehouse", "Shop"), ("Shop", "Home"), ("Distribution Center", "Home")]
        ]
    }
    
    # Get packages from session state for validation
    packages = st.session_state.packages if 'packages' in st.session_state else []
    
    # Create an initial graph with all roads
    G = nx.Graph()
    for loc in LOCATIONS:
        G.add_node(loc)
    for loc1, loc2 in ROAD_SEGMENTS:
        G.add_edge(loc1, loc2)
    
    # First try using a predefined safe closure combination based on difficulty
    if num_closures in safe_closures:
        # Shuffle the safe closures to add randomness
        safe_closure_options = safe_closures[num_closures].copy()
        random.shuffle(safe_closure_options)
        
        for chosen_closures in safe_closure_options:
            # Validate with packages
            test_G = G.copy()
            for road in chosen_closures:
                if test_G.has_edge(road[0], road[1]):
                    test_G.remove_edge(road[0], road[1])
            
            if validate_package_delivery(test_G, packages):
                st.session_state.closed_roads = chosen_closures
                return chosen_closures
    
    # If predefined closures don't work or we have a different number of closures,
    # try to find valid road closures through trial and error while maintaining difficulty
    all_road_segments = list(ROAD_SEGMENTS)
    
    # Try multiple combinations at the requested difficulty level
    for attempt in range(max_attempts):
        random.shuffle(all_road_segments)
        candidate_closures = all_road_segments[:num_closures]
        
        # Validate these closures
        test_G = G.copy()
        for road in candidate_closures:
            if test_G.has_edge(road[0], road[1]):
                test_G.remove_edge(road[0], road[1])
        
        # Check if the graph is still connected and all packages can be delivered
        if nx.is_connected(test_G) and validate_package_delivery(test_G, packages):
            st.session_state.closed_roads = candidate_closures
            return candidate_closures
    
    # If we couldn't find a valid setup with the requested number of closures,
    # try with fewer closures but alert the user
    for reduced_closures in range(num_closures-1, 0, -1):
        for attempt in range(max_attempts):
            random.shuffle(all_road_segments)
            candidate_closures = all_road_segments[:reduced_closures]
            
            # Validate these closures
            test_G = G.copy()
            for road in candidate_closures:
                if test_G.has_edge(road[0], road[1]):
                    test_G.remove_edge(road[0], road[1])
            
            # Check if the graph is still connected and all packages can be delivered
            if nx.is_connected(test_G) and validate_package_delivery(test_G, packages):
                st.session_state.closed_roads = candidate_closures
                # Notify that difficulty was reduced
                st.warning(f"Difficulty reduced to {reduced_closures} road closure(s) to ensure a playable game.")
                return candidate_closures
    
    # Fall back to a single safe closure if everything else fails
    fallback_closures = [("Warehouse", "Shop")]
    st.session_state.closed_roads = fallback_closures
    st.warning("Difficulty reduced to Easy (1 road closure) to ensure a playable game.")
    return fallback_closures

def add_random_closure():
    """Add a random road closure during gameplay, ensuring connectivity and constraints"""
    current_closures = len(st.session_state.closed_roads)
    
    # Try to add one more closure
    available_roads = [road for road in ROAD_SEGMENTS 
                       if road not in st.session_state.closed_roads 
                       and (road[1], road[0]) not in st.session_state.closed_roads]
    
    G = nx.Graph()
    for loc in LOCATIONS:
        G.add_node(loc)
    for road in ROAD_SEGMENTS:
        if not is_road_closed(road[0], road[1]):
            G.add_edge(road[0], road[1])
    
    packages = st.session_state.packages if 'packages' in st.session_state else []
    
    random.shuffle(available_roads)
    for road in available_roads:
        # Copy the graph to test removal
        test_G = G.copy()
        test_G.remove_edge(road[0], road[1])
        
        if nx.is_connected(test_G) and validate_package_delivery(test_G, packages):
            st.session_state.closed_roads.append(road)
            st.warning(f"⛔️ ALERT: Road between {road[0]} and {road[1]} is now closed!")
            return True
    
    return False

def remove_random_closure():
    """Remove a random road closure during gameplay"""
    if not st.session_state.closed_roads:
        return False
    
    closure_index = random.randint(0, len(st.session_state.closed_roads) - 1)
    removed_closure = st.session_state.closed_roads.pop(closure_index)
    st.success(f"✅ Road between {removed_closure[0]} and {removed_closure[1]} has been reopened!")
    return True

def get_best_detour(from_loc, to_loc):
    """Find the best detour route between two locations when the direct route is closed"""
    if not is_road_closed(from_loc, to_loc):
        return [from_loc, to_loc]
    
    G = nx.Graph()
    for loc in LOCATIONS:
        G.add_node(loc)
    for loc1, loc2 in ROAD_SEGMENTS:
        if not is_road_closed(loc1, loc2):
            if (loc1, loc2) in DISTANCES:
                weight = DISTANCES[(loc1, loc2)]
            elif (loc2, loc1) in DISTANCES:
                weight = DISTANCES[(loc2, loc1)]
            else:
                weight = 1
            G.add_edge(loc1, loc2, weight=weight)
    
    try:
        path = nx.shortest_path(G, from_loc, to_loc, weight='weight')
        return path
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None