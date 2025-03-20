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

def validate_package_delivery(G, packages):
    """
    Validate if all packages can be delivered with the given graph
    Returns True if all packages can be delivered, False otherwise
    """
    # Check if all pickup and delivery locations are connected
    for pkg in packages:
        pickup = pkg["pickup"]
        delivery = pkg["delivery"]
        
        if not nx.has_path(G, pickup, delivery):
            return False
    
    # Check if constraints can still be satisfied
    if not nx.has_path(G, "Factory", "Shop") or not nx.has_path(G, "DHL Hub", "Residence"):
        return False
    
    # Simplified validation that prevents deadlocks:
    # Ensure that we can go from Factory to DHL Hub while respecting the Factory→Shop constraint
    # This prevents the specific deadlock situation observed
    
    # Case 1: Check if we can go from Factory to DHL Hub without going through Shop
    test_G = G.copy()
    if "Shop" in test_G.nodes():
        test_G.remove_node("Shop")
    
    if not nx.has_path(test_G, "Factory", "DHL Hub"):
        # If we can't go from Factory to DHL Hub without Shop, and
        # we know the constraint is Factory before Shop, check if we can
        # go Factory→Shop→DHL Hub
        if not nx.has_path(G, "Shop", "DHL Hub"):
            return False
    
    # Case 2: Check if we can go from DHL Hub to Shop without going through Residence
    test_G = G.copy()
    if "Residence" in test_G.nodes():
        test_G.remove_node("Residence")
    
    if not nx.has_path(test_G, "DHL Hub", "Shop"):
        # If we can't go from DHL Hub to Shop without Residence, and
        # we know the constraint is DHL Hub before Residence, check if we can
        # go DHL Hub→Residence→Shop
        if not nx.has_path(G, "Residence", "Shop"):
            return False
    
    return True

def generate_road_closures(num_closures=1, max_attempts=100):
    """
    Generate random road closures while ensuring:
    1. The graph remains connected
    2. All packages can be delivered
    3. All constraints can be satisfied
    
    Falls back to preset safe closures if needed, with shuffling for variety.
    """
    # Initialize the original graph
    G = nx.Graph()
    for loc in LOCATIONS:
        G.add_node(loc)
    for road in ROAD_SEGMENTS:
        G.add_edge(road[0], road[1])
    
    # Get packages from session state
    packages = st.session_state.packages if 'packages' in st.session_state else []
    
    # Ensure num_closures doesn't exceed possible closures while keeping graph connected
    max_possible_closures = len(ROAD_SEGMENTS) - (len(LOCATIONS) - 1)
    num_closures = min(num_closures, max_possible_closures)
    
    # Try multiple times to find valid closures
    for attempt in range(max_attempts):
        # Copy the original graph
        test_G = G.copy()
        
        # Select random edges to close
        all_roads = list(ROAD_SEGMENTS)
        random.shuffle(all_roads)
        closed_roads = []
        
        for road in all_roads:
            # Skip if already have enough closures
            if len(closed_roads) >= num_closures:
                break
                
            # Remove the edge
            test_G.remove_edge(road[0], road[1])
            
            # Check if graph is still connected and all packages can be delivered
            if nx.is_connected(test_G) and validate_package_delivery(test_G, packages):
                closed_roads.append(road)
            else:
                # If removing this edge causes issues, add it back
                test_G.add_edge(road[0], road[1])
        
        # If we found enough closures, use them
        if len(closed_roads) == num_closures:
            st.session_state.closed_roads = closed_roads
            return closed_roads
    
    # If we couldn't find the requested number of closures, use preset safe closures
    # Define a larger set of potentially safe closures
    all_safe_closures = [
        ("Factory", "Residence"),
        ("Factory", "DHL Hub"),
        ("Shop", "Residence"),
        ("DHL Hub", "Shop"),
        ("Shop", "Factory"),
        ("Residence", "Factory")
    ]
    
    # Shuffle these for variety
    random.shuffle(all_safe_closures)
    
    # Filter to make sure these roads actually exist in our model
    valid_safe_closures = [road for road in all_safe_closures if road in ROAD_SEGMENTS 
                        or (road[1], road[0]) in ROAD_SEGMENTS]
    
    # Create a graph to validate these safe closures in combination
    valid_and_tested_closures = []
    
    # Start with an empty set of closures and add them one by one if they're valid
    for safe_road in valid_safe_closures:
        if len(valid_and_tested_closures) >= num_closures:
            break
            
        # Normalize the road direction to match ROAD_SEGMENTS
        normalized_road = safe_road
        if safe_road not in ROAD_SEGMENTS and (safe_road[1], safe_road[0]) in ROAD_SEGMENTS:
            normalized_road = (safe_road[1], safe_road[0])
            
        # Test adding this closure
        test_G = G.copy()
        for road in valid_and_tested_closures:
            test_G.remove_edge(road[0], road[1])
        
        test_G.remove_edge(normalized_road[0], normalized_road[1])
        
        # Validate the combined closures
        if nx.is_connected(test_G) and validate_package_delivery(test_G, packages):
            valid_and_tested_closures.append(normalized_road)
    
    # If we still don't have enough, create guaranteed safe combinations
    if len(valid_and_tested_closures) < num_closures:
        if num_closures >= 3:  # Hard mode
            # Define several combinations that we know work for Hard mode
            hard_mode_combinations = [
                [("Factory", "Residence"), ("Factory", "Shop"), ("DHL Hub", "Residence")],
                [("Factory", "DHL Hub"), ("Shop", "Residence"), ("Factory", "Residence")],
                [("Factory", "Residence"), ("DHL Hub", "Shop"), ("Factory", "Shop")]
            ]
            # Pick a random combination and use it
            chosen_combo = random.choice(hard_mode_combinations)
            # Filter for valid roads again just to be safe
            valid_combo = [road for road in chosen_combo if road in ROAD_SEGMENTS 
                         or (road[1], road[0]) in ROAD_SEGMENTS]
            # Normalize the roads
            normalized_combo = []
            for road in valid_combo:
                if road in ROAD_SEGMENTS:
                    normalized_combo.append(road)
                elif (road[1], road[0]) in ROAD_SEGMENTS:
                    normalized_combo.append((road[1], road[0]))
            
            valid_and_tested_closures = normalized_combo[:num_closures]
            
        elif num_closures >= 2:  # Medium mode
            # Define several combinations that we know work for Medium mode
            medium_mode_combinations = [
                [("Factory", "Residence"), ("Factory", "Shop")],
                [("Factory", "DHL Hub"), ("Shop", "Residence")],
                [("Factory", "Residence"), ("DHL Hub", "Shop")]
            ]
            # Pick a random combination and use it
            chosen_combo = random.choice(medium_mode_combinations)
            # Filter for valid roads again just to be safe
            valid_combo = [road for road in chosen_combo if road in ROAD_SEGMENTS 
                         or (road[1], road[0]) in ROAD_SEGMENTS]
            # Normalize the roads
            normalized_combo = []
            for road in valid_combo:
                if road in ROAD_SEGMENTS:
                    normalized_combo.append(road)
                elif (road[1], road[0]) in ROAD_SEGMENTS:
                    normalized_combo.append((road[1], road[0]))
            
            valid_and_tested_closures = normalized_combo[:num_closures]
            
        else:  # Easy mode - just one closure
            easy_closures = [
                ("Factory", "Residence"),
                ("Factory", "DHL Hub"),
                ("Shop", "Residence")
            ]
            random.shuffle(easy_closures)
            for road in easy_closures:
                if road in ROAD_SEGMENTS:
                    valid_and_tested_closures = [road]
                    break
                elif (road[1], road[0]) in ROAD_SEGMENTS:
                    valid_and_tested_closures = [(road[1], road[0])]
                    break
    
    # Make sure we return exactly the number of closures requested
    result = valid_and_tested_closures[:num_closures]
    
    # If we still don't have enough, duplicate some (better than having too few)
    if len(result) < num_closures and len(result) > 0:
        while len(result) < num_closures:
            result.append(result[0])  # Duplicate the first closure as a last resort
    
    st.session_state.closed_roads = result
    return result

def get_road_closure_impact():
    """Calculate the impact of road closures on routing options"""
    if not st.session_state.closed_roads:
        return None
        
    G = nx.Graph()
    for loc in LOCATIONS:
        G.add_node(loc)
    for loc1, loc2 in ROAD_SEGMENTS:
        if not is_road_closed(loc1, loc2):
            G.add_edge(loc1, loc2)
            
    impact = {
        "num_closures": len(st.session_state.closed_roads),
        "closed_roads": st.session_state.closed_roads.copy(),
        "affected_locations": set()
    }
    
    for loc1, loc2 in st.session_state.closed_roads:
        impact["affected_locations"].add(loc1)
        impact["affected_locations"].add(loc2)
    
    impact["affected_locations"] = list(impact["affected_locations"])
    
    impact["detours"] = {}
    for loc1, loc2 in st.session_state.closed_roads:
        try:
            path = nx.shortest_path(G, loc1, loc2)
            impact["detours"][(loc1, loc2)] = path
        except nx.NetworkXNoPath:
            impact["detours"][(loc1, loc2)] = None
    
    return impact

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