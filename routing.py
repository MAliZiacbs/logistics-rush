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

def find_detour(from_loc, to_loc, via_loc="Central Hub"):
    """Find a detour route when direct path is closed"""
    if not is_road_closed(from_loc, to_loc):
        return [from_loc, to_loc], get_distance(from_loc, to_loc)
    if is_road_closed(from_loc, via_loc) or is_road_closed(via_loc, to_loc):
        return None, float('inf')
    detour_distance = get_distance(from_loc, via_loc) + get_distance(via_loc, to_loc)
    detour_route = [from_loc, via_loc, to_loc]
    return detour_route, detour_distance

def calculate_segment_path(from_loc, to_loc):
    """Calculate the path and distance between two locations, using detour if needed"""
    direct_distance = get_distance(from_loc, to_loc)
    if direct_distance != float('inf'):
        return [from_loc, to_loc], direct_distance
    detour_route, detour_distance = find_detour(from_loc, to_loc)
    if detour_route:
        return detour_route, detour_distance
    return None, float('inf')

def calculate_route_distance(route):
    """Calculate the total distance of a route with detours"""
    if len(route) <= 1:
        return None, 0
    total_distance = 0
    full_path = []
    for i in range(len(route) - 1):
        segment_path, segment_distance = calculate_segment_path(route[i]["location"], route[i+1]["location"])
        if segment_distance == float('inf'):
            return None, float('inf')
        total_distance += segment_distance
        full_path.extend(segment_path if i == 0 else segment_path[1:])  # Avoid duplicating locations
    return full_path, total_distance

def is_valid_route(route):
    """Check if a route is valid (has a path between all consecutive locations)"""
    for i in range(len(route) - 1):
        segment_path, _ = calculate_segment_path(route[i]["location"], route[i+1]["location"])
        if segment_path is None:
            return False
    return True

def solve_tsp(start_location, locations):
    """Solve TSP with package pickups and deliveries, using detours if needed"""
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
    best_path = None
    min_distance = float('inf')
    remaining = [loc for loc in ordered_locations if loc != start_location]

    # Build action list: visit all locations and handle all packages
    for perm in permutations(remaining):
        base_route = [start_location] + list(perm)
        action_route = []
        packages_to_handle = {p["id"]: {"pickup": p["pickup"], "delivery": p["delivery"]} for p in packages}
        current_package = None

        for loc in base_route:
            pickups = [pid for pid, pkg in packages_to_handle.items() if pkg["pickup"] == loc and pid not in [a["package_id"] for a in action_route if a["action"] == "pickup"]]
            if pickups and not current_package:
                pid = pickups[0]
                action_route.append({"location": loc, "action": "pickup", "package_id": pid})
                current_package = pid
            if current_package and packages_to_handle[current_package]["delivery"] == loc:
                action_route.append({"location": loc, "action": "deliver", "package_id": current_package})
                del packages_to_handle[current_package]
                current_package = None
            if not any(a["location"] == loc for a in action_route[-2:]):  # Avoid redundant visits
                action_route.append({"location": loc, "action": "visit", "package_id": None})

        # Return to start
        _, return_distance = calculate_segment_path(action_route[-1]["location"], start_location)
        if return_distance != float('inf'):
            action_route.append({"location": start_location, "action": "visit", "package_id": None})

        # Validate route
        loc_only_route = [a["location"] for a in action_route]
        if check_constraints(loc_only_route) and is_valid_route(action_route) and not packages_to_handle:
            full_path, distance = calculate_route_distance(action_route)
            if full_path and distance < min_distance:
                min_distance = distance
                best_route = action_route.copy()
                best_path = full_path

    # Fallback: If no route found, try a minimal path through Central Hub
    if best_route is None:
        st.warning(f"No optimal route found with current closures: {st.session_state.closed_roads}")
        fallback_route = [
            {"location": start_location, "action": "visit", "package_id": None},
            {"location": "Central Hub", "action": "visit", "package_id": None},
        ]
        for loc in ordered_locations:
            if loc != start_location:
                fallback_route.append({"location": loc, "action": "visit", "package_id": None})
        fallback_route.append({"location": start_location, "action": "visit", "package_id": None})
        full_path, distance = calculate_route_distance(fallback_route)
        if full_path and distance != float('inf'):
            best_route = fallback_route
            best_path = full_path
            min_distance = distance
        else:
            return None, None, float('inf')

    if best_route is None:
        return None, None, float('inf')
    return best_route, best_path, min_distance

def get_nearest_accessible_location(current_location):
    """Find the nearest location that can be reached from current location"""
    locations = [loc for loc in LOCATIONS.keys() if loc != current_location]
    accessible = []
    for loc in locations:
        _, distance = calculate_segment_path(current_location, loc)
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
        segment_path, _ = calculate_segment_path(current_location, delivery_loc)
        if segment_path:
            return delivery_loc, "delivery"
        segment_path, _ = calculate_segment_path(current_location, "Central Hub")
        if segment_path:
            return "Central Hub", "detour"
    available_pickups = [p for p in packages if p["pickup"] == current_location and p["status"] == "waiting"]
    if available_pickups and not st.session_state.current_package:
        return current_location, "pickup"
    main_locations = [loc for loc in LOCATIONS.keys() if loc != "Central Hub"]
    unvisited = [loc for loc in main_locations if loc not in visited_locations]
    if unvisited:
        accessible_unvisited = []
        for loc in unvisited:
            _, dist = calculate_segment_path(current_location, loc)
            if dist < float('inf'):
                accessible_unvisited.append((loc, dist))
        if accessible_unvisited:
            accessible_unvisited.sort(key=lambda x: x[1])
            return accessible_unvisited[0][0], "unvisited"
    return "Central Hub", "default"