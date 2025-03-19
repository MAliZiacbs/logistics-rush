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

def find_detour(from_loc, to_loc):
    """Find a detour route when direct path is closed (no Central Hub fallback)"""
    if not is_road_closed(from_loc, to_loc):
        return [from_loc, to_loc], get_distance(from_loc, to_loc)
    # Try all possible intermediate nodes (excluding from_loc and to_loc)
    for via_loc in LOCATIONS:
        if via_loc != from_loc and via_loc != to_loc:
            if not is_road_closed(from_loc, via_loc) and not is_road_closed(via_loc, to_loc):
                detour_distance = get_distance(from_loc, via_loc) + get_distance(via_loc, to_loc)
                if detour_distance != float('inf'):
                    return [from_loc, via_loc, to_loc], detour_distance
    return None, float('inf')

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
    
    # Handle if route is a list of locations or a list of dicts
    if isinstance(route[0], dict):
        loc_route = [r["location"] for r in route]
    else:
        loc_route = route
        
    for i in range(len(loc_route) - 1):
        segment_path, segment_distance = calculate_segment_path(loc_route[i], loc_route[i+1])
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
    """Solve TSP considering packages and constraints, ensuring all locations are visited"""
    packages = st.session_state.packages.copy()
    unvisited = locations.copy()
    
    # First, create a mandatory route that includes all package deliveries
    # This ensures we create a route that can deliver all packages
    required_segments = []
    for pkg in packages:
        required_segments.append((pkg["pickup"], pkg["delivery"]))
    
    # We need to make sure all locations are visited and all packages can be delivered
    # Start building a route from the start location
    current_location = start_location
    action_route = [{"location": current_location, "action": "visit", "package_id": None}]
    
    # Keep track of packages that need to be handled
    packages_to_handle = {p["id"]: {"pickup": p["pickup"], "delivery": p["delivery"]} for p in packages}
    current_package = None
    visited = {start_location}
    
    # First priority: Ensure we visit all locations
    while len(visited) < len(locations) or packages_to_handle:
        next_loc = None
        min_dist = float('inf')
        
        # Handle constraints: Factory must be visited before Shop
        factory_constraint = "Factory" in visited or current_location == "Factory"
        shop_constraint = "Shop" not in unvisited or factory_constraint
        
        # Handle constraints: DHL Hub must be visited before Residence
        dhl_constraint = "DHL Hub" in visited or current_location == "DHL Hub"
        residence_constraint = "Residence" not in unvisited or dhl_constraint
        
        # Priority 1: Pickup packages that can be delivered
        if not current_package:
            for loc in unvisited:
                # Skip Shop if Factory hasn't been visited yet
                if loc == "Shop" and not factory_constraint:
                    continue
                # Skip Residence if DHL Hub hasn't been visited yet
                if loc == "Residence" and not dhl_constraint:
                    continue
                
                # Check if this location has packages for pickup
                has_pickup = any(pkg["pickup"] == loc and pkg["id"] in packages_to_handle for pkg in packages)
                
                if has_pickup:
                    _, dist = calculate_segment_path(current_location, loc)
                    if dist < min_dist:
                        min_dist = dist
                        next_loc = loc
            
            if next_loc:
                # Find a package to pick up
                pickup_pkgs = [pkg for pkg in packages if pkg["pickup"] == next_loc and pkg["id"] in packages_to_handle]
                if pickup_pkgs:
                    pkg = pickup_pkgs[0]
                    action_route.append({"location": next_loc, "action": "pickup", "package_id": pkg["id"]})
                    current_package = pkg["id"]
                    visited.add(next_loc)
                    if next_loc in unvisited:
                        unvisited.remove(next_loc)
                    current_location = next_loc
                    continue
        
        # Priority 2: Deliver current package if holding one
        if current_package:
            delivery_loc = packages_to_handle[current_package]["delivery"]
            
            # Check constraints before delivering
            if (delivery_loc == "Shop" and not factory_constraint) or \
               (delivery_loc == "Residence" and not dhl_constraint):
                # Can't deliver yet due to constraints
                pass
            else:
                _, dist = calculate_segment_path(current_location, delivery_loc)
                if dist < float('inf'):
                    action_route.append({"location": delivery_loc, "action": "deliver", "package_id": current_package})
                    del packages_to_handle[current_package]
                    current_package = None
                    visited.add(delivery_loc)
                    if delivery_loc in unvisited:
                        unvisited.remove(delivery_loc)
                    current_location = delivery_loc
                    continue
        
        # Priority 3: Visit remaining unvisited locations (considering constraints)
        min_dist = float('inf')
        next_loc = None
        
        for loc in unvisited:
            # Skip Shop if Factory hasn't been visited
            if loc == "Shop" and not factory_constraint:
                continue
            # Skip Residence if DHL Hub hasn't been visited
            if loc == "Residence" and not dhl_constraint:
                continue
            
            _, dist = calculate_segment_path(current_location, loc)
            if dist < min_dist:
                min_dist = dist
                next_loc = loc
        
        if next_loc:
            action_route.append({"location": next_loc, "action": "visit", "package_id": None})
            visited.add(next_loc)
            unvisited.remove(next_loc)
            current_location = next_loc
            continue
        
        # If we reach here, we might be stuck due to constraints
        # Try to pick an available location that satisfies constraints
        available_locs = []
        
        for loc in locations:
            if loc not in visited:
                if (loc == "Shop" and not factory_constraint) or \
                   (loc == "Residence" and not dhl_constraint):
                    continue
                available_locs.append(loc)
        
        if available_locs:
            # Find the closest available location
            next_loc = min(available_locs, key=lambda loc: get_distance(current_location, loc))
            _, dist = calculate_segment_path(current_location, next_loc)
            
            if dist < float('inf'):
                action_route.append({"location": next_loc, "action": "visit", "package_id": None})
                visited.add(next_loc)
                if next_loc in unvisited:
                    unvisited.remove(next_loc)
                current_location = next_loc
                continue
        
        # If we still can't find a valid next location, we're really stuck
        # This could happen if road closures make it impossible to satisfy all constraints
        break
    
    # Return to start location if possible
    if current_location != start_location:
        _, return_dist = calculate_segment_path(current_location, start_location)
        if return_dist != float('inf'):
            action_route.append({"location": start_location, "action": "visit", "package_id": None})
    
    # Check if the route is valid and satisfies constraints
    if not check_constraints([a["location"] for a in action_route]):
        return None, None, float('inf')
    
    # Calculate full path and total distance
    full_path, total_distance = calculate_route_distance(action_route)
    
    if full_path is None or total_distance == float('inf'):
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
        # No Central Hub detour; try any accessible location
        nearest = get_nearest_accessible_location(current_location)
        if nearest:
            return nearest, "detour"
    available_pickups = [p for p in packages if p["pickup"] == current_location and p["status"] == "waiting"]
    if available_pickups and not st.session_state.current_package:
        return current_location, "pickup"
    main_locations = list(LOCATIONS.keys())  # No Central Hub
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
    # Default to nearest accessible location if no specific action
    nearest = get_nearest_accessible_location(current_location)
    return nearest if nearest else current_location, "default"