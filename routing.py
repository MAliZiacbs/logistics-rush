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
    Uses a combined approach with graph analysis and genetic algorithm concepts.
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
        
        # Check if we can deliver all packages with this route
        visited = set()
        can_deliver = {}
        
        for loc in route:
            visited.add(loc)
            
            # Check which packages we can pick up at this location
            for pkg_id, pkg in package_map.items():
                if pkg["pickup"] == loc:
                    can_deliver[pkg_id] = False  # Picked up but not delivered
            
            # Check which packages we can deliver at this location
            for pkg_id, pkg in package_map.items():
                if pkg["delivery"] == loc and pkg_id in can_deliver and pkg["pickup"] in visited:
                    can_deliver[pkg_id] = True
        
        # Ensure all packages can be delivered
        return all(can_deliver.values()) if can_deliver else True
    
    # Calculate the cost of a route (distance + package handling)
    def calculate_route_cost(route):
        if not is_valid_route(route):
            return float('inf')
        
        total_distance = 0
        for i in range(len(route) - 1):
            segment_distance = get_distance(route[i], route[i+1])
            if segment_distance == float('inf'):
                return float('inf')
            total_distance += segment_distance
        
        # Add penalty for excessive route length
        length_penalty = 0.1 * max(0, len(route) - len(all_locations) - 2)
        
        return total_distance * (1 + length_penalty)
    
    # Convert a route of locations to a full action route with package operations
    def create_action_route(route):
        action_route = []
        visited = set()
        carrying_package = None
        
        for i, loc in enumerate(route):
            visited.add(loc)
            
            # First, check if we can deliver a package
            if carrying_package:
                pkg = package_map[carrying_package]
                if pkg["delivery"] == loc:
                    action_route.append({"location": loc, "action": "deliver", "package_id": carrying_package})
                    carrying_package = None
                    continue
            
            # If not delivering, check if we can pick up a package
            if not carrying_package:
                for pkg_id, pkg in package_map.items():
                    if pkg["pickup"] == loc and pkg["delivery"] in set(route[i:]):
                        # Only pick up if we'll visit the delivery location later
                        action_route.append({"location": loc, "action": "pickup", "package_id": pkg_id})
                        carrying_package = pkg_id
                        break
            
            # If no package action, just visit
            if (not action_route or action_route[-1]["location"] != loc or 
                action_route[-1]["action"] not in ["pickup", "deliver"]):
                action_route.append({"location": loc, "action": "visit", "package_id": None})
        
        return action_route
    
    # ----- Begin the advanced TSP solution algorithm -----
    
    # Start with a topological sort of locations based on constraints
    def get_topological_ordering():
        # Create a default ordering that respects constraints
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
    
    # Ensure start location is first and try to make a cycle
    if start_location in initial_ordering:
        initial_ordering.remove(start_location)
    ordered_route = [start_location] + initial_ordering
    
    # Try to optimize by swapping locations that don't violate constraints
    def optimize_route(route, max_iterations=100):
        best_route = route.copy()
        best_cost = calculate_route_cost(best_route)
        
        current_route = route.copy()
        current_cost = best_cost
        
        # Simulated annealing parameters
        temperature = 10.0
        cooling_rate = 0.95
        
        for iteration in range(max_iterations):
            # Make a random swap that doesn't violate constraints
            new_route = current_route.copy()
            
            # Try up to 10 times to find a valid swap
            for attempt in range(10):
                # Don't swap the starting position
                i = random.randint(1, len(new_route) - 1)
                j = random.randint(1, len(new_route) - 1)
                
                if i != j:
                    new_route[i], new_route[j] = new_route[j], new_route[i]
                    if is_valid_route(new_route):
                        break
                    else:
                        # Revert invalid swap
                        new_route[i], new_route[j] = new_route[j], new_route[i]
            
            # Calculate the cost of the new route
            new_cost = calculate_route_cost(new_route)
            
            # Decide whether to accept the new route
            if new_cost < current_cost:
                # Always accept better solutions
                current_route = new_route
                current_cost = new_cost
                
                if new_cost < best_cost:
                    best_route = new_route.copy()
                    best_cost = new_cost
            else:
                # Probabilistically accept worse solutions based on temperature
                delta = new_cost - current_cost
                probability = min(1.0, math.exp(-delta / temperature))
                
                if random.random() < probability:
                    current_route = new_route
                    current_cost = new_cost
            
            # Cool down the temperature
            temperature *= cooling_rate
        
        return best_route, best_cost
    
    # Run the optimization
    try:
        import math
        optimized_route, optimized_cost = optimize_route(ordered_route, max_iterations=200)
        
        # Add return to start if beneficial
        if start_location != optimized_route[-1]:
            complete_route = optimized_route + [start_location]
            complete_cost = calculate_route_cost(complete_route)
            
            if complete_cost < float('inf'):
                optimized_route = complete_route
                optimized_cost = complete_cost
        
        # Convert to action route
        action_route = create_action_route(optimized_route)
        
        # Calculate the full path and distance
        full_path = []
        for loc in optimized_route:
            if not full_path or full_path[-1] != loc:
                full_path.append(loc)
                
        route_distance = 0
        for i in range(len(full_path) - 1):
            segment_distance = get_distance(full_path[i], full_path[i+1])
            if segment_distance != float('inf'):
                route_distance += segment_distance
            else:
                # Try to find a detour
                segment_path, segment_distance = find_detour(full_path[i], full_path[i+1])
                if segment_path and segment_distance < float('inf'):
                    # Insert the intermediate points
                    for j, waypoint in enumerate(segment_path[1:-1], 1):
                        full_path.insert(i + j, waypoint)
                    route_distance += segment_distance
                else:
                    return None, None, float('inf')
        
        # Ensure we've created a valid route
        if action_route and full_path and route_distance < float('inf'):
            return action_route, full_path, route_distance
        
    except Exception as e:
        st.error(f"Route optimization error: {str(e)}")
    
    # If we get here, the advanced algorithm failed - fall back to simpler approach
    # This is a simplified version to ensure we return something viable
    fallback_route = []
    
    # Start at the start location
    current_location = start_location
    fallback_route.append({"location": current_location, "action": "visit", "package_id": None})
    visited = {current_location}
    
    # Visit Factory before Shop, DHL Hub before Residence
    for loc_pair in [("Factory", "Shop"), ("DHL Hub", "Residence")]:
        for loc in loc_pair:
            if loc not in visited and loc in all_locations:
                fallback_route.append({"location": loc, "action": "visit", "package_id": None})
                visited.add(loc)
    
    # Visit any remaining locations
    for loc in all_locations:
        if loc not in visited:
            fallback_route.append({"location": loc, "action": "visit", "package_id": None})
            visited.add(loc)
    
    # Return to start if needed
    if fallback_route[0]["location"] != fallback_route[-1]["location"]:
        fallback_route.append({"location": start_location, "action": "visit", "package_id": None})
    
    # Create the full path for fallback
    fallback_path = [action["location"] for action in fallback_route]
    
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