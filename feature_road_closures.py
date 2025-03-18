import streamlit as st
import random
import networkx as nx

from config import LOCATIONS, ROAD_SEGMENTS

def is_road_closed(loc1, loc2):
    """Check if a road between two locations is closed"""
    return (loc1, loc2) in st.session_state.closed_roads or (loc2, loc1) in st.session_state.closed_roads

def generate_road_closures(num_closures=2):
    """Generate random road closures, ensuring the graph remains connected"""
    road_segments = ROAD_SEGMENTS.copy()
    closed_roads = []
    
    # Create a graph to check connectivity
    G = nx.Graph()
    for loc in LOCATIONS:
        G.add_node(loc)
    
    for road in road_segments:
        G.add_edge(road[0], road[1])
    
    # Try to close roads while keeping the graph connected
    random.shuffle(road_segments)
    
    for road in road_segments:
        # Temporarily remove the edge
        G.remove_edge(road[0], road[1])
        
        # Check if the graph is still connected
        if nx.is_connected(G):
            closed_roads.append(road)
            if len(closed_roads) >= num_closures:
                break
        else:
            # If removing this edge disconnects the graph, add it back
            G.add_edge(road[0], road[1])
    
    return closed_roads

def get_road_closure_impact():
    """Calculate the impact of road closures on routing options"""
    if not st.session_state.closed_roads:
        return None
        
    # Create a graph without closed roads
    G = nx.Graph()
    for loc in LOCATIONS:
        G.add_node(loc)
    
    for loc1, loc2 in ROAD_SEGMENTS:
        if not is_road_closed(loc1, loc2):
            G.add_edge(loc1, loc2)
            
    # Calculate impact statistics
    impact = {
        "num_closures": len(st.session_state.closed_roads),
        "closed_roads": st.session_state.closed_roads.copy(),
        "affected_locations": set()
    }
    
    # Find locations affected by closures
    for loc1, loc2 in st.session_state.closed_roads:
        impact["affected_locations"].add(loc1)
        impact["affected_locations"].add(loc2)
    
    impact["affected_locations"] = list(impact["affected_locations"])
    
    # Calculate alternative routes for closed roads
    impact["detours"] = {}
    for loc1, loc2 in st.session_state.closed_roads:
        # Find shortest path through the graph (this will be a detour)
        try:
            path = nx.shortest_path(G, loc1, loc2)
            impact["detours"][(loc1, loc2)] = path
        except nx.NetworkXNoPath:
            impact["detours"][(loc1, loc2)] = None
    
    return impact

def add_random_closure():
    """Add a random road closure during gameplay, ensuring connectivity"""
    if len(st.session_state.closed_roads) >= len(ROAD_SEGMENTS) - (len(LOCATIONS) - 1):
        # Cannot close more roads without disconnecting the graph
        return False
    
    # Find roads that are not already closed
    available_roads = [road for road in ROAD_SEGMENTS if road not in st.session_state.closed_roads and (road[1], road[0]) not in st.session_state.closed_roads]
    
    # Create a graph to check connectivity
    G = nx.Graph()
    for loc in LOCATIONS:
        G.add_node(loc)
    
    for road in ROAD_SEGMENTS:
        if not is_road_closed(road[0], road[1]):
            G.add_edge(road[0], road[1])
    
    # Try roads until we find one that can be closed
    random.shuffle(available_roads)
    for road in available_roads:
        # Temporarily remove the edge
        G.remove_edge(road[0], road[1])
        
        # Check if the graph is still connected
        if nx.is_connected(G):
            st.session_state.closed_roads.append(road)
            st.warning(f"⛔️ ALERT: Road between {road[0]} and {road[1]} is now closed!")
            return True
        else:
            # If removing this edge disconnects the graph, add it back
            G.add_edge(road[0], road[1])
    
    return False

def remove_random_closure():
    """Remove a random road closure during gameplay"""
    if not st.session_state.closed_roads:
        return False
    
    # Randomly select a closure to remove
    closure_index = random.randint(0, len(st.session_state.closed_roads) - 1)
    removed_closure = st.session_state.closed_roads.pop(closure_index)
    st.success(f"✅ Road between {removed_closure[0]} and {removed_closure[1]} has been reopened!")
    return True