import streamlit as st
from itertools import permutations

from config import DISTANCES, LOCATIONS, check_constraints
from feature_road_closures import is_road_closed

def get_distance(loc1, loc2):
    """Get the distance between two locations, accounting for road closures"""
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
        segment_distance = get_distance(route[i]["location"], route[i+1]["location"])
        if segment_distance == float('inf'):
            return float('inf')
        total_distance += segment_distance
    return total_distance

def is_valid_route(route):
    """Check if a route is valid (no closed roads)"""
    for i in range(len(route) - 1):
        if is_road_closed(route[i]["location"], route[i+1]["location"]):
            return False
    return True

def solve_tsp(start_location, locations):
    """Solve TSP with package pickups and deliveries"""
    packages = st.session_state.packages
    ordered_locations = locations.copy()
    
    # Ensure constraint ordering
    if "Factory" in ordered_locations and "Shop" in ordered_locations:
        factory_idx = ordered_locations.index("Factory")
        shop_idx = ordered_locations.index("Shop")
        if factory_idx > shop_idx:
            ordered_locations[factory_idx], ordered_locations[shop_idx] = ordered_locations[shop_idx], ordered_locations[factory_idx]
    if "DHL Hub" in ordered_locations and "Residence" in ordered_locations:
        dhl_idx = ordered_locations.index("DHL Hub")
        res_idx = ordered_locations.index("Residence")
        if dhl_idx > res_idx:
            ordered_locations[dhl_idx], ordered_locations[res_idx] = ordered_locations[res_idx], ordered_locations[dhl_idx]

    best_route = None
    min_distance = float('inf')
    remaining = [loc for loc in ordered_locations if loc != start_location]

    # Build action list: visit all locations and handle all packages
    for perm in permutations(remaining):
        base_route = [start_location] + list(perm)
        action_route = []
        packages_to_handle = {p["id"]: {"pickup": p["pickup"], "delivery": p["delivery"]} for p in packages}
        current_package = None

        for loc in base_route:
            # Check for pickups
            pickups = [pid for pid, pkg in packages_to_handle.items() if pkg["pickup"] == loc and pid not in [a["package_id"] for a in action_route if a["action"] == "pickup"]]
            if pickups and not current_package:
                pid = pickups[0]
                action_route.append({"location": loc, "action": "pickup", "package_id": pid})
                current_package = pid
            # Check for deliveries
            if current_package and packages_to_handle[current_package]["delivery"] == loc:
                action_route.append({"location": loc, "action": "deliver", "package_id": current_package})
                del packages_to_handle[current_package]
                current_package = None
            # Add visit if no action
            if not any(a["location"] == loc for a in action_route[-2:]):  # Avoid redundant visits
                action_route.append({"location": loc, "action": "visit", "package_id": None})

        # Return to start
        if not is_road_closed(action_route[-1]["location"], start_location):
            action_route.append({"location": start_location, "action": "visit", "package_id": None})

        # Validate route
        loc_only_route = [a["location"] for a in action_route]
        if check_constraints(loc_only_route) and is_valid_route(action_route) and not packages_to_handle:
            distance = calculate_route_distance(action_route)
            if distance < min_distance:
                min_distance = distance
                best_route = action_route.copy()

    if best_route is None:
        return None, float('inf')
    return best_route, min_distance

# Other functions (get_distance, find_detour, etc.) remain unchanged
def get_distance(loc1, loc2):
    """Get the distance between two locations, accounting for road closures"""
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
        segment_distance = get_distance(route[i]["location"], route[i+1]["location"])
        if segment_distance == float('inf'):
            return float('inf')
        total_distance += segment_distance
    return total_distance

def is_valid_route(route):
    """Check if a route is valid (no closed roads)"""
    for i in range(len(route) - 1):
        if is_road_closed(route[i]["location"], route[i+1]["location"]):
            return False
    return True

def find_detour(from_loc, to_loc, via_loc="Central Hub"):
    """Find a detour route when direct path is closed"""
    if not is_road_closed(from_loc, to_loc):
        return [from_loc, to_loc], get_distance(from_loc, to_loc)
    if is_road_closed(from_loc, via_loc) or is_road_closed(via_loc, to_loc):
        return None, float('inf')
    detour_distance = get_distance(from_loc, via_loc) + get_distance(via_loc, to_loc)
    detour_route = [from_loc, via_loc, to_loc]
    return detour_route, detour_distance

def get_nearest_accessible_location(current_location):
    """Find the nearest location that can be reached from current location"""
    locations = [loc for loc in LOCATIONS.keys() if loc != current_location]
    accessible = []
    for loc in locations:
        distance = get_distance(current_location, loc)
        if distance < float('inf'):
            accessible.append((loc, distance))
    if not accessible:
        return None
    accessible.sort(key=lambda x: x[1])
    return accessible[0][0]

def suggest_next_location(current_location, visited_locations, packages):
    """Suggest the next best location to visit based on current state"""
    if st.session_state.current_package:
        delivery_loc = st.session_state.current_package["delivery"]
        if not is_road_closed(current_location, delivery_loc):
            return delivery_loc, "delivery"
        if not is_road_closed(current_location, "Central Hub") and not is_road_closed("Central Hub", delivery_loc):
            return "Central Hub", "detour"
    available_pickups = [p for p in packages if p["pickup"] == current_location and p["status"] == "waiting"]
    if available_pickups and not st.session_state.current_package:
        return current_location, "pickup"
    main_locations = [loc for loc in LOCATIONS.keys() if loc != "Central Hub"]
    unvisited = [loc for loc in main_locations if loc not in visited_locations]
    if unvisited:
        accessible_unvisited = []
        for loc in unvisited:
            dist = get_distance(current_location, loc)
            if dist < float('inf'):
                accessible_unvisited.append((loc, dist))
        if accessible_unvisited:
            accessible_unvisited.sort(key=lambda x: x[1])
            return accessible_unvisited[0][0], "unvisited"
    return "Central Hub", "default"