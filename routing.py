import streamlit as st
from itertools import permutations

from config import DISTANCES, LOCATIONS
from feature_road_closures import is_road_closed

def get_distance(loc1, loc2):
    """Get the distance between two locations, accounting for road closures"""
    # Check if road is closed
    if is_road_closed(loc1, loc2):
        return float('inf')
    
    if (loc1, loc2) in DISTANCES:
        return DISTANCES[(loc1, loc2)]
    elif (loc2, loc1) in DISTANCES:
        return DISTANCES[(loc2, loc1)]
    else:
        return float('inf')

def calculate_route_distance(route):
    """Calculate the total distance of a route"""
    if len(route) <= 1:
        return 0
        
    total_distance = 0
    for i in range(len(route) - 1):
        segment_distance = get_distance(route[i], route[i+1])
        if segment_distance == float('inf'):
            return float('inf')  # Route is invalid due to road closure
        total_distance += segment_distance
        
    return total_distance

def is_valid_route(route):
    """Check if a route is valid (no closed roads)"""
    for i in range(len(route) - 1):
        if is_road_closed(route[i], route[i+1]):
            return False
    return True

def check_constraints(route):
    """Check if route follows the constraints for Complex Supply Chain mode"""
    # Factory must come before Shop
    if "Factory" in route and "Shop" in route:
        f_idx = route.index("Factory")
        s_idx = route.index("Shop")
        if f_idx > s_idx:
            return False
            
    # DHL Hub must come before Residence
    if "DHL Hub" in route and "Residence" in route:
        d_idx = route.index("DHL Hub")
        r_idx = route.index("Residence")
        if d_idx > r_idx:
            return False
            
    return True

def solve_tsp(start_location, locations):
    """Solve the Traveling Salesman Problem to find optimal route accounting for road closures"""
    # For complex supply chain mode, ensure constraints are followed
    if st.session_state.game_mode == "Complex Supply Chain":
        if "Factory" in locations and "Shop" in locations:
            factory_idx = locations.index("Factory")
            shop_idx = locations.index("Shop")
            if factory_idx > shop_idx:
                # Swap to ensure Factory comes before Shop
                locations[factory_idx], locations[shop_idx] = locations[shop_idx], locations[factory_idx]
        if "DHL Hub" in locations and "Residence" in locations:
            dhl_idx = locations.index("DHL Hub")
            res_idx = locations.index("Residence")
            if dhl_idx > res_idx:
                # Swap to ensure DHL Hub comes before Residence
                locations[dhl_idx], locations[res_idx] = locations[res_idx], locations[dhl_idx]

    best_route = None
    min_distance = float('inf')

    remaining = [loc for loc in locations if loc != start_location]
    for perm in permutations(remaining):
        route = [start_location] + list(perm)
        distance = 0
        valid_route = True
        
        for i in range(len(route) - 1):
            # If road is closed between these locations, route is invalid
            segment_distance = get_distance(route[i], route[i+1])
            if segment_distance == float('inf'):
                valid_route = False
                break
            distance += segment_distance

        # Add return to start
        return_distance = get_distance(route[-1], route[0])
        if return_distance == float('inf'):
            valid_route = False
        else:
            distance += return_distance

        if valid_route and distance < min_distance:
            min_distance = distance
            best_route = route.copy()
            best_route.append(route[0])  # close the loop

    # If no valid route is found (all routes have closed roads), return None
    if best_route is None:
        return None, float('inf')
    
    return best_route, min_distance

def find_detour(from_loc, to_loc, via_loc="Central Hub"):
    """Find a detour route when direct path is closed"""
    # Check if direct route is possible
    if not is_road_closed(from_loc, to_loc):
        return [from_loc, to_loc], get_distance(from_loc, to_loc)
        
    # Check if detour via specified location is possible
    if is_road_closed(from_loc, via_loc) or is_road_closed(via_loc, to_loc):
        return None, float('inf')
        
    # Calculate detour distance
    detour_distance = get_distance(from_loc, via_loc) + get_distance(via_loc, to_loc)
    detour_route = [from_loc, via_loc, to_loc]
    
    return detour_route, detour_distance

def get_nearest_accessible_location(current_location):
    """Find the nearest location that can be reached from current location"""
    locations = [loc for loc in LOCATIONS.keys() if loc != current_location]
    accessible = []
    
    for loc in locations:
        distance = get_distance(current_location, loc)
        if distance < float('inf'):  # Location is accessible
            accessible.append((loc, distance))
            
    if not accessible:
        return None
        
    # Return nearest accessible location
    accessible.sort(key=lambda x: x[1])
    return accessible[0][0]