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
    """Calculate the total distance of a route with detours, returning two values"""
    if len(route) <= 1:
        return None, 0  # Return full_path, distance
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
    """Solve TSP with Nearest Neighbor heuristic, handling packages and detours with backtracking"""
    packages = st.session_state.packages
    unvisited = locations.copy()
    current_location = start_location
    action_route = [{"location": current_location, "action": "visit", "package_id": None}]
    packages_to_handle = {p["id"]: {"pickup": p["pickup"], "delivery": p["delivery"]} for p in packages}
    current_package = None
    total_distance = 0
    max_attempts = len(unvisited) * 2  # Limit backtracking attempts

    attempt = 0
    while unvisited or packages_to_handle and attempt < max_attempts:
        next_loc = None
        min_dist = float('inf')
        # Prioritize package pickups if no package is held
        if not current_package:
            for loc in unvisited:
                if any(pkg["pickup"] == loc and pkg["id"] in packages_to_handle for pkg in packages):
                    _, dist = calculate_segment_path(current_location, loc)
                    if dist < min_dist:
                        min_dist = dist
                        next_loc = loc
            if next_loc:
                pickups = [pid for pid, pkg in packages_to_handle.items() if pkg["pickup"] == next_loc]
                if pickups:
                    pid = pickups[0]
                    action_route.append({"location": next_loc, "action": "pickup", "package_id": pid})
                    current_package = pid
                    unvisited.remove(next_loc)
                    _, segment_dist = calculate_segment_path(current_location, next_loc)
                    total_distance += segment_dist
                    current_location = next_loc
                    continue
        # Prioritize package delivery if holding one
        if current_package:
            delivery_loc = packages_to_handle[current_package]["delivery"]
            if delivery_loc in unvisited or delivery_loc == current_location:
                _, dist = calculate_segment_path(current_location, delivery_loc)
                if dist < min_dist:
                    min_dist = dist
                    next_loc = delivery_loc
            if next_loc:
                action_route.append({"location": next_loc, "action": "deliver", "package_id": current_package})
                del packages_to_handle[current_package]
                current_package = None
                if next_loc in unvisited:
                    unvisited.remove(next_loc)
                _, segment_dist = calculate_segment_path(current_location, next_loc)
                total_distance += segment_dist
                current_location = next_loc
                continue
        # Choose nearest unvisited location
        for loc in unvisited:
            _, dist = calculate_segment_path(current_location, loc)
            if dist < min_dist:
                min_dist = dist
                next_loc = loc
        if next_loc:
            action_route.append({"location": next_loc, "action": "visit", "package_id": None})
            unvisited.remove(next_loc)
            _, segment_dist = calculate_segment_path(current_location, next_loc)
            total_distance += segment_dist
            current_location = next_loc
        else:
            attempt += 1  # Backtrack by trying a different path if stuck
            if attempt >= max_attempts:
                break

    # Return to start
    _, return_dist = calculate_segment_path(current_location, start_location)
    if return_dist != float('inf'):
        action_route.append({"location": start_location, "action": "visit", "package_id": None})
        total_distance += return_dist

    # Validate route
    loc_only_route = [a["location"] for a in action_route]
    if not check_constraints(loc_only_route) or not is_valid_route(action_route) or packages_to_handle:
        return None, None, float('inf')

    full_path, _ = calculate_route_distance(action_route)
    if not full_path:
        return None, None, float('inf')
    return action_route, full_path, total_distance

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