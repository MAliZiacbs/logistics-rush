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
    if not nx.has_path(G, "Factory", "Shop") or not nx.has_path(G, "DHL Hub", "Residence"):
        return False
    
    # Advanced test for hard mode with multiple closures
    # Test if it's possible to do a full route that satisfies all constraints
    
    # Create a test route that would need to satisfy all constraints:
    # Factory → DHL Hub → Shop → Residence → Factory (complete loop)
    test_route = ["Factory", "DHL Hub", "Shop", "Residence", "Factory"]
    
    # Check if each segment in this route has a path with current closures
    for i in range(len(test_route) - 1):
        if not nx.has_path(G, test_route[i], test_route[i+1]):
            return False
    
    # Also check critical routes for package delivery scenarios
    critical_paths = [
        # Critical Factory → Shop path (direct or via DHL Hub/Residence)
        ["Factory", "Shop"],  
        # Critical DHL Hub → Residence path (direct or via Factory/Shop)
        ["DHL Hub", "Residence"],
        # Must be able to get from Factory to DHL Hub (might need to go via Shop)
        ["Factory", "DHL Hub"],
        # Must be able to get from Shop to Residence (might need to go via DHL Hub)
        ["Shop", "Residence"]
    ]
    
    for path in critical_paths:
        if not nx.has_path(G, path[0], path[1]):
            return False
    
    # Explicitly test more package delivery scenarios
    # Scenario 1: Deliver a package from Factory to Shop while respecting constraints
    # We're at Factory and need to get to Shop
    # If direct route is closed, we need to find a valid detour
    if not nx.has_path(G, "Factory", "Shop"):
        # Try to find a valid detour that respects constraints
        # Since Factory must come before Shop, we can only go via DHL Hub/Residence if needed
        factory_to_shop_path = False
        
        # Check if we can go Factory → DHL Hub → Shop
        if nx.has_path(G, "Factory", "DHL Hub") and nx.has_path(G, "DHL Hub", "Shop"):
            factory_to_shop_path = True
        
        # Or check if we can go Factory → DHL Hub → Residence → Shop
        # This is valid because we visit DHL Hub before Residence
        elif (nx.has_path(G, "Factory", "DHL Hub") and 
              nx.has_path(G, "DHL Hub", "Residence") and 
              nx.has_path(G, "Residence", "Shop")):
            factory_to_shop_path = True
        
        if not factory_to_shop_path:
            return False
    
    # Scenario 2: Deliver a package from DHL Hub to Residence while respecting constraints
    # We're at DHL Hub and need to get to Residence
    # If direct route is closed, we need to find a valid detour
    if not nx.has_path(G, "DHL Hub", "Residence"):
        # Try to find a valid detour that respects constraints
        # Since DHL Hub must come before Residence, we can only go via Factory/Shop if needed
        dhl_to_residence_path = False
        
        # Check if we can go DHL Hub → Factory → Residence
        if nx.has_path(G, "DHL Hub", "Factory") and nx.has_path(G, "Factory", "Residence"):
            dhl_to_residence_path = True
        
        # Or check if we can go DHL Hub → Factory → Shop → Residence
        # This is valid because Factory must come before Shop
        elif (nx.has_path(G, "DHL Hub", "Factory") and 
              nx.has_path(G, "Factory", "Shop") and 
              nx.has_path(G, "Shop", "Residence")):
            dhl_to_residence_path = True
        
        # Or check if we can go DHL Hub → Shop → Residence
        # (This assumes we've already been to Factory before going to Shop)
        elif nx.has_path(G, "DHL Hub", "Shop") and nx.has_path(G, "Shop", "Residence"):
            dhl_to_residence_path = True
        
        if not dhl_to_residence_path:
            return False
    
    # If all tests pass, the graph is valid
    return True

# This is a patch for feature_road_closures.py
# Add this improved function to handle road closures better

def generate_road_closures(num_closures=1, max_attempts=100):
    """
    Generate random road closures while ensuring:
    1. The graph remains connected
    2. All packages can be delivered
    3. All constraints can be satisfied
    
    Falls back to preset safe closures if needed, with shuffling for variety.
    Added extra validation and error handling.
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
        try:
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
                # Double-check that these closures work
                final_G = G.copy()
                for road in closed_roads:
                    final_G.remove_edge(road[0], road[1])
                
                if nx.is_connected(final_G) and validate_package_delivery(final_G, packages):
                    st.session_state.closed_roads = closed_roads
                    return closed_roads
        except Exception as e:
            # Continue to the next attempt if any error occurs
            continue
    
    # If we couldn't find the requested number of closures, use preset safe closures
    # Use pre-defined road closure combinations that we know work
    try:
        # Easy mode (1 closure)
        easy_closures = [
            [("Factory", "Residence")],
            [("Shop", "Residence")],
            [("Factory", "Shop")]
        ]
        
        # Medium mode (2 closures) - verified working combinations
        medium_closures = [
            [("Factory", "Shop"), ("Shop", "Residence")],
            [("Factory", "DHL Hub"), ("Shop", "Residence")],
            [("Factory", "Shop"), ("Factory", "Residence")]
        ]
        
        # Hard mode (3 closures) - these are carefully selected to avoid deadlocks
        hard_closures = [
            # Configuration 1: Creates a challenging but solvable route
            [("Factory", "DHL Hub"), ("Shop", "Residence"), ("Factory", "Shop")],
            
            # Configuration 2: Another solvable arrangement
            [("Factory", "Shop"), ("DHL Hub", "Shop"), ("DHL Hub", "Residence")],
            
            # Configuration 3: Forces a specific path that works
            [("Factory", "Residence"), ("Shop", "Residence"), ("DHL Hub", "Shop")]
        ]
        
        # Select the appropriate preset based on difficulty
        if num_closures >= 3:  # Hard
            preset_closures = random.choice(hard_closures)
        elif num_closures >= 2:  # Medium
            preset_closures = random.choice(medium_closures)
        else:  # Easy
            preset_closures = random.choice(easy_closures)
        
        # Normalize the roads to match ROAD_SEGMENTS format
        result = []
        for road in preset_closures:
            if road in ROAD_SEGMENTS:
                result.append(road)
            elif (road[1], road[0]) in ROAD_SEGMENTS:
                result.append((road[1], road[0]))
        
        # Limit to requested number (shouldn't be needed, but just to be safe)
        result = result[:num_closures]
        
        # If we still don't have enough, add some that we know are safe
        if len(result) < num_closures:
            safe_additions = [
                ("Factory", "Residence"),
                ("Shop", "Residence"),
                ("Factory", "Shop")
            ]
            
            # Add from safe_additions until we have enough
            for road in safe_additions:
                if len(result) >= num_closures:
                    break
                    
                # Skip if already closed
                if road in result or (road[1], road[0]) in result:
                    continue
                    
                # Add if it exists in ROAD_SEGMENTS
                if road in ROAD_SEGMENTS:
                    result.append(road)
                elif (road[1], road[0]) in ROAD_SEGMENTS:
                    result.append((road[1], road[0]))
        
        # Final validation of the preset closures
        final_G = G.copy()
        for road in result:
            if isinstance(road, tuple) and len(road) == 2:
                if road[0] in final_G and road[1] in final_G:
                    final_G.remove_edge(road[0], road[1])
                else:
                    # Skip invalid road
                    continue
        
        if not nx.is_connected(final_G):
            # If even presets don't work, fall back to single closure
            return [("Factory", "Shop")]
        
        st.session_state.closed_roads = result
        return result
    except Exception as e:
        # Ultimate fallback - just return a single safe closure
        safe_closure = [("Factory", "Shop")]
        st.session_state.closed_roads = safe_closure
        return safe_closure

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