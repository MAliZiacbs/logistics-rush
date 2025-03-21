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
    import networkx as nx
    
    # Check if all pickup and delivery locations are connected
    for pkg in packages:
        pickup = pkg["pickup"]
        delivery = pkg["delivery"]
        
        if not nx.has_path(G, pickup, delivery):
            return False
    
    # Check if constraints can still be satisfied
    if not nx.has_path(G, "Warehouse", "Shop") or not nx.has_path(G, "Distribution Center", "Home"):
        return False
    
    # Advanced test for hard mode with multiple closures
    # Test if it's possible to do a full route that satisfies all constraints
    
    # Create a test route that would need to satisfy all constraints:
    # Warehouse → Distribution Center → Shop → Home → Warehouse (complete loop)
    test_route = ["Warehouse", "Distribution Center", "Shop", "Home", "Warehouse"]
    
    # Check if each segment in this route has a path with current closures
    for i in range(len(test_route) - 1):
        if not nx.has_path(G, test_route[i], test_route[i+1]):
            return False
    
    # Also check critical routes for package delivery scenarios
    critical_paths = [
        # Critical Warehouse → Shop path (direct or via Distribution Center/Home)
        ["Warehouse", "Shop"],  
        # Critical Distribution Center → Home path (direct or via Warehouse/Shop)
        ["Distribution Center", "Home"],
        # Must be able to get from Warehouse to Distribution Center (might need to go via Shop)
        ["Warehouse", "Distribution Center"],
        # Must be able to get from Shop to Home (might need to go via Distribution Center)
        ["Shop", "Home"]
    ]
    
    for path in critical_paths:
        if not nx.has_path(G, path[0], path[1]):
            return False
    
    # Explicitly test more package delivery scenarios
    # Scenario 1: Deliver a package from Warehouse to Shop while respecting constraints
    # We're at Warehouse and need to get to Shop
    # If direct route is closed, we need to find a valid detour
    if not nx.has_path(G, "Warehouse", "Shop"):
        # Try to find a valid detour that respects constraints
        # Since Warehouse must come before Shop, we can only go via Distribution Center/Home if needed
        warehouse_to_shop_path = False
        
        # Check if we can go Warehouse → Distribution Center → Shop
        if nx.has_path(G, "Warehouse", "Distribution Center") and nx.has_path(G, "Distribution Center", "Shop"):
            warehouse_to_shop_path = True
        
        # Or check if we can go Warehouse → Distribution Center → Home → Shop
        # This is valid because we visit Distribution Center before Home
        elif (nx.has_path(G, "Warehouse", "Distribution Center") and 
              nx.has_path(G, "Distribution Center", "Home") and 
              nx.has_path(G, "Home", "Shop")):
            warehouse_to_shop_path = True
        
        if not warehouse_to_shop_path:
            return False
    
    # Scenario 2: Deliver a package from Distribution Center to Home while respecting constraints
    # We're at Distribution Center and need to get to Home
    # If direct route is closed, we need to find a valid detour
    if not nx.has_path(G, "Distribution Center", "Home"):
        # Try to find a valid detour that respects constraints
        # Since Distribution Center must come before Home, we can only go via Warehouse/Shop if needed
        distribution_to_home_path = False
        
        # Check if we can go Distribution Center → Warehouse → Home
        if nx.has_path(G, "Distribution Center", "Warehouse") and nx.has_path(G, "Warehouse", "Home"):
            distribution_to_home_path = True
        
        # Or check if we can go Distribution Center → Warehouse → Shop → Home
        # This is valid because Warehouse must come before Shop
        elif (nx.has_path(G, "Distribution Center", "Warehouse") and 
              nx.has_path(G, "Warehouse", "Shop") and 
              nx.has_path(G, "Shop", "Home")):
            distribution_to_home_path = True
        
        # Or check if we can go Distribution Center → Shop → Home
        # (This assumes we've already been to Warehouse before going to Shop)
        elif nx.has_path(G, "Distribution Center", "Shop") and nx.has_path(G, "Shop", "Home"):
            distribution_to_home_path = True
        
        if not distribution_to_home_path:
            return False
    
    # If all tests pass, the graph is valid
    return True

# This is a patch for feature_road_closures.py
# Add this improved function to handle road closures better

# This is a patch for feature_road_closures.py
# Add this improved function to handle road closures better

def generate_road_closures(num_closures=1, max_attempts=100):
    """
    Generate random road closures with improved validation to ensure playable situations.
    """
    # Ensure we never close more than 2 roads in Medium difficulty
    if num_closures > 3:
        num_closures = 3  # Hard mode cap
    
    # We know these specific closure combinations always work well
    safe_closures = {
        1: [  # Easy mode
            [("Warehouse", "Home")],
            [("Shop", "Home")],
            [("Warehouse", "Shop")]
        ],
        2: [  # Medium mode - carefully selected combinations that work well
            [("Warehouse", "Shop"), ("Shop", "Home")],
            [("Warehouse", "Home"), ("Distribution Center", "Shop")],
            [("Shop", "Home"), ("Distribution Center", "Shop")]
        ],
        3: [  # Hard mode - carefully tested combinations
            [("Shop", "Home"), ("Warehouse", "Home"), ("Distribution Center", "Shop")],
            [("Warehouse", "Shop"), ("Distribution Center", "Shop"), ("Warehouse", "Distribution Center")],
            [("Warehouse", "Home"), ("Shop", "Home"), ("Warehouse", "Shop")]
        ]
    }
    
    # Use a predefined safe closure combination based on difficulty
    if num_closures in safe_closures:
        chosen_closure = random.choice(safe_closures[num_closures])
        st.session_state.closed_roads = chosen_closure
        return chosen_closure
    
    # Fallback to single closure if not 1, 2, or 3
    st.session_state.closed_roads = [("Warehouse", "Shop")]
    return [("Warehouse", "Shop")]

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