import streamlit as st
import random
import networkx as nx

from config import LOCATIONS, ROAD_SEGMENTS

def is_road_closed(loc1, loc2):
    """Check if a road between two locations is closed"""
    if 'closed_roads' not in st.session_state:
        return False
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
        # Don't close certain critical roads for the combined game mode
        # Don't close Factory-Central Hub or Shop-Central Hub to ensure constraints can be met
        if (road[0] == "Factory" and road[1] == "Central Hub") or \
           (road[0] == "Central Hub" and road[1] == "Factory") or \
           (road[0] == "Shop" and road[1] == "Central Hub") or \
           (road[0] == "Central Hub" and road[1] == "Shop"):
            continue
            
        # Don't close DHL Hub-Central Hub or Residence-Central Hub
        if (road[0] == "DHL Hub" and road[1] == "Central Hub") or \
           (road[0] == "Central Hub" and road[1] == "DHL Hub") or \
           (road[0] == "Residence" and road[1] == "Central Hub") or \
           (road[0] == "Central Hub" and road[1] == "Residence"):
            continue
        
        # Temporarily remove the edge
        G.remove_edge(road[0], road[1])
        
        # Check if the graph is still connected and if it doesn't break constraints
        if nx.is_connected(G):
            # Confirm the closure doesn't make it impossible to follow constraints
            factory_to_shop = nx.has_path(G, "Factory", "Shop")
            dhl_to_residence = nx.has_path(G, "DHL Hub", "Residence")
            
            if factory_to_shop and dhl_to_residence:
                closed_roads.append(road)
                if len(closed_roads) >= num_closures:
                    break
            else:
                # If closing this road would break constraints, add it back
                G.add_edge(road[0], road[1])
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
    """Add a random road closure during gameplay, ensuring connectivity and constraints"""
    if len(st.session_state.closed_roads) >= len(ROAD_SEGMENTS) - (len(LOCATIONS) - 1):
        # Cannot close more roads without disconnecting the graph
        return False
    
    # Find roads that are not already closed
    available_roads = [road for road in ROAD_SEGMENTS 
                       if road not in st.session_state.closed_roads 
                       and (road[1], road[0]) not in st.session_state.closed_roads]
    
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
        # Skip critical roads for constraints
        if (road[0] == "Factory" and road[1] == "Central Hub") or \
           (road[0] == "Central Hub" and road[1] == "Factory") or \
           (road[0] == "Shop" and road[1] == "Central Hub") or \
           (road[0] == "Central Hub" and road[1] == "Shop") or \
           (road[0] == "DHL Hub" and road[1] == "Central Hub") or \
           (road[0] == "Central Hub" and road[1] == "DHL Hub") or \
           (road[0] == "Residence" and road[1] == "Central Hub") or \
           (road[0] == "Central Hub" and road[1] == "Residence"):
            continue
            
        # Temporarily remove the edge
        G.remove_edge(road[0], road[1])
        
        # Check if the graph is still connected and constraints can be followed
        if nx.is_connected(G):
            # Confirm the closure doesn't make it impossible to follow constraints
            factory_to_shop = nx.has_path(G, "Factory", "Shop")
            dhl_to_residence = nx.has_path(G, "DHL Hub", "Residence")
            
            if factory_to_shop and dhl_to_residence:
                st.session_state.closed_roads.append(road)
                st.warning(f"⛔️ ALERT: Road between {road[0]} and {road[1]} is now closed!")
                return True
            else:
                # If closing this road would break constraints, add it back
                G.add_edge(road[0], road[1])
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

def get_best_detour(from_loc, to_loc):
    """Find the best detour route between two locations when the direct route is closed"""
    if not is_road_closed(from_loc, to_loc):
        return [from_loc, to_loc]  # Direct route possible
    
    # Create a graph without closed roads
    G = nx.Graph()
    for loc in LOCATIONS:
        G.add_node(loc)
    
    for loc1, loc2 in ROAD_SEGMENTS:
        if not is_road_closed(loc1, loc2):
            # Add weight based on distance
            if (loc1, loc2) in st.session_state.DISTANCES:
                weight = st.session_state.DISTANCES[(loc1, loc2)]
            elif (loc2, loc1) in st.session_state.DISTANCES:
                weight = st.session_state.DISTANCES[(loc2, loc1)]
            else:
                weight = 1
            G.add_edge(loc1, loc2, weight=weight)
    
    # Find shortest path
    try:
        path = nx.shortest_path(G, from_loc, to_loc, weight='weight')
        return path
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None  # No path exists