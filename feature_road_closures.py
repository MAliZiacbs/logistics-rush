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
    
    # NEW: Check if a valid sequence exists that respects all constraints
    # Create a directed graph for constraint checking
    constraint_G = nx.DiGraph()
    for loc in G.nodes():
        constraint_G.add_node(loc)
    
    # Add edges for existing paths in the undirected graph
    for u, v in G.edges():
        constraint_G.add_edge(u, v)
        constraint_G.add_edge(v, u)  # Since G is undirected
    
    # Add constraint edges (these are directed)
    constraint_G.add_edge("Factory", "Shop")
    constraint_G.add_edge("DHL Hub", "Residence")
    
    # Check if the constrained graph has cycles
    try:
        nx.find_cycle(constraint_G)
        # If a cycle is found, the constraints cannot be satisfied
        return False
    except nx.NetworkXNoCycle:
        # No cycle means constraints can be satisfied
        return True

def generate_road_closures(num_closures=1, max_attempts=100):
    """
    Generate random road closures while ensuring:
    1. The graph remains connected
    2. All packages can be delivered
    3. All constraints can be satisfied
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
            # Remove the edge
            test_G.remove_edge(road[0], road[1])
            
            # Check if graph is still connected and all packages can be delivered with constraints satisfied
            if nx.is_connected(test_G) and validate_package_delivery(test_G, packages):
                closed_roads.append(road)
                if len(closed_roads) >= num_closures:
                    break
            else:
                # If removing this edge disconnects the graph or prevents package delivery, add it back
                test_G.add_edge(road[0], road[1])
        
        # If we found enough closures, use them
        if len(closed_roads) == num_closures:
            st.session_state.closed_roads = closed_roads
            return closed_roads
    
    # If we couldn't find the requested number of closures, try with fewer
    if num_closures > 1:
        return generate_road_closures(num_closures - 1, max_attempts)
    else:
        # As a last resort, return no closures
        st.session_state.closed_roads = []
        return []

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