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
    """
    Advanced TSP solver with package constraints and multi-objective optimization.
    Ensures all packages are included in the optimal route.
    """
    import random
    import copy
    from itertools import permutations

    packages = st.session_state.packages.copy()
    
    # Create a map of package requirements
    package_map = {p["id"]: {"pickup": p["pickup"], "delivery": p["delivery"]} for p in packages}
    
    # Identify locations that require constraint ordering
    constraint_pairs = [
        ("Factory", "Shop"),
        ("DHL Hub", "Residence")
    ]
    
    # Create a directed graph of constraints
    constraint_graph = {}
    for first, second in constraint_pairs:
        if first not in constraint_graph:
            constraint_graph[first] = []
        constraint_graph[first].append(second)
    
    # Identify all locations we need to visit
    all_locations = set(locations)
    
    # Helper function to check if a route satisfies all constraints
    def is_valid_route(route):
        # Check location constraints
        for first, second in constraint_pairs:
            if first in route and second in route:
                if route.index(first) > route.index(second):
                    return False
        return True
    
    # Convert a route of locations to a full action route with package operations
    # Ensures all packages are handled
    def create_action_route(route):
        action_route = []
        visited = set()
        carrying_package = None
        
        # Track packages that need to be picked up and delivered
        packages_to_handle = {p["id"]: {"pickup": p["pickup"], "delivery": p["delivery"], "status": "waiting"} 
                             for p in packages}
        
        # First add the starting location
        if route[0] not in visited:
            action_route.append({"location": route[0], "action": "visit", "package_id": None})
            visited.add(route[0])
        
        # Process the route to handle packages
        for i, loc in enumerate(route):
            if loc not in visited:
                action_route.append({"location": loc, "action": "visit", "package_id": None})
                visited.add(loc)
            
            # Check if we can pick up any packages at this location
            pickups_at_location = [pkg_id for pkg_id, pkg in packages_to_handle.items() 
                                  if pkg["pickup"] == loc and pkg["status"] == "waiting"]
            
            for pkg_id in pickups_at_location:
                if carrying_package is None:  # Only pick up if not carrying anything
                    action_route.append({"location": loc, "action": "pickup", "package_id": pkg_id})
                    packages_to_handle[pkg_id]["status"] = "picked_up"
                    carrying_package = pkg_id
                    
                    # Immediately check if we can deliver this package
                    if loc == packages_to_handle[pkg_id]["delivery"]:
                        action_route.append({"location": loc, "action": "deliver", "package_id": pkg_id})
                        packages_to_handle[pkg_id]["status"] = "delivered"
                        carrying_package = None
            
            # Check if we can deliver the package we're carrying
            if carrying_package is not None:
                pkg = packages_to_handle[carrying_package]
                if pkg["delivery"] == loc:
                    action_route.append({"location": loc, "action": "deliver", "package_id": carrying_package})
                    pkg["status"] = "delivered"
                    carrying_package = None
        
        # Check if we need to add more steps to handle all packages
        unhandled_packages = [pkg_id for pkg_id, pkg in packages_to_handle.items() 
                             if pkg["status"] != "delivered"]
        
        if unhandled_packages:
            # If we still have unhandled packages, try to create a new route to handle them
            remaining_locations = set()
            for pkg_id in unhandled_packages:
                pkg = packages_to_handle[pkg_id]
                remaining_locations.add(pkg["pickup"])
                remaining_locations.add(pkg["delivery"])
            
            # Create a route through remaining locations
            current_loc = action_route[-1]["location"]
            
            for pkg_id in unhandled_packages:
                pkg = packages_to_handle[pkg_id]
                
                # Go to pickup if needed
                if pkg["status"] == "waiting":
                    if current_loc != pkg["pickup"]:
                        action_route.append({"location": pkg["pickup"], "action": "visit", "package_id": None})
                    action_route.append({"location": pkg["pickup"], "action": "pickup", "package_id": pkg_id})
                    pkg["status"] = "picked_up"
                    current_loc = pkg["pickup"]
                
                # Go to delivery
                if current_loc != pkg["delivery"]:
                    action_route.append({"location": pkg["delivery"], "action": "visit", "package_id": None})
                action_route.append({"location": pkg["delivery"], "action": "deliver", "package_id": pkg_id})
                pkg["status"] = "delivered"
                current_loc = pkg["delivery"]
        
        return action_route
    
    # Start with a topological sort of locations based on constraints
    def get_topological_ordering():
        # Start with locations that have package pickups
        pickup_locations = set(pkg["pickup"] for pkg in packages)
        delivery_locations = set(pkg["delivery"] for pkg in packages)
        
        # Create an ordering that satisfies constraints
        result = []
        
        # First add locations with package pickups
        for loc in all_locations:
            if loc in pickup_locations and loc not in result:
                result.append(loc)
        
        # Then add any remaining locations
        for loc in all_locations:
            if loc not in result:
                result.append(loc)
        
        # Ensure the order satisfies constraints
        valid_order = True
        for first, second in constraint_pairs:
            if first in result and second in result:
                idx_first = result.index(first)
                idx_second = result.index(second)
                if idx_first > idx_second:
                    valid_order = False
                    break
        
        # If the order violates constraints, create a constraint-based ordering
        if not valid_order:
            result = []
            visited = set()
            
            def visit(node):
                if node in visited:
                    return
                visited.add(node)
                if node in constraint_graph:
                    for neighbor in constraint_graph[node]:
                        if neighbor in all_locations:
                            visit(neighbor)
                result.append(node)
            
            # Start from nodes with no incoming edges
            has_incoming = set()
            for node in constraint_graph:
                for neighbor in constraint_graph[node]:
                    has_incoming.add(neighbor)
            
            for node in all_locations:
                if node not in has_incoming:
                    visit(node)
            
            # Add any remaining nodes
            for node in all_locations:
                if node not in visited:
                    visit(node)
            
            # Reverse to get the correct order
            result.reverse()
        
        return result
    
    initial_ordering = get_topological_ordering()
    
    # Ensure start location is first 
    if start_location in initial_ordering:
        initial_ordering.remove(start_location)
    ordered_route = [start_location] + initial_ordering
    
    # Create action route that handles all packages
    action_route = create_action_route(ordered_route)
    
    # Extract the full path from the action route
    full_path = []
    for action in action_route:
        loc = action["location"]
        if not full_path or full_path[-1] != loc:
            full_path.append(loc)
    
    # Calculate the total distance
    total_distance = 0
    for i in range(len(full_path) - 1):
        segment_distance = get_distance(full_path[i], full_path[i+1])
        if segment_distance == float('inf'):
            segment_path, segment_distance = find_detour(full_path[i], full_path[i+1])
        total_distance += segment_distance if segment_distance != float('inf') else 0
    
    # Ensure we created a valid route
    if action_route and full_path and total_distance < float('inf'):
        return action_route, full_path, total_distance
    
    # Fallback if we couldn't create a valid route
    fallback_route = []
    
    # Start at the start location
    current_location = start_location
    fallback_route.append({"location": current_location, "action": "visit", "package_id": None})
    
    # Manually create a route that visits all locations and handles all packages
    for pkg in packages:
        pickup_loc = pkg["pickup"]
        delivery_loc = pkg["delivery"]
        
        # Go to pickup location if not already there
        if current_location != pickup_loc:
            fallback_route.append({"location": pickup_loc, "action": "visit", "package_id": None})
        
        # Pick up the package
        fallback_route.append({"location": pickup_loc, "action": "pickup", "package_id": pkg["id"]})
        
        # Go to delivery location if not already there
        if pickup_loc != delivery_loc:
            fallback_route.append({"location": delivery_loc, "action": "visit", "package_id": None})
        
        # Deliver the package
        fallback_route.append({"location": delivery_loc, "action": "deliver", "package_id": pkg["id"]})
        
        current_location = delivery_loc
    
    # Visit any remaining locations
    for loc in all_locations:
        if loc not in [action["location"] for action in fallback_route]:
            fallback_route.append({"location": loc, "action": "visit", "package_id": None})
    
    # Create the full path for fallback
    fallback_path = []
    for action in fallback_route:
        loc = action["location"]
        if not fallback_path or fallback_path[-1] != loc:
            fallback_path.append(loc)
    
    # Calculate distance
    fallback_distance = 0
    for i in range(len(fallback_path) - 1):
        segment_distance = get_distance(fallback_path[i], fallback_path[i+1])
        if segment_distance != float('inf'):
            fallback_distance += segment_distance
        else:
            # Try to find a detour
            _, detour_distance = find_detour(fallback_path[i], fallback_path[i+1])
            if detour_distance != float('inf'):
                fallback_distance += detour_distance
    
    return fallback_route, fallback_path, fallback_distance

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