import streamlit as st
from itertools import permutations
import random
import networkx as nx
import copy

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
    """Find a detour route when direct path is closed"""
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
        if i == 0:
            full_path.extend(segment_path)
        else:
            full_path.extend(segment_path[1:])  # Avoid duplicating locations
    return full_path, total_distance

def is_valid_route(route):
    """Check if a route is valid (has a path between all consecutive locations)"""
    for i in range(len(route) - 1):
        segment_path, _ = calculate_segment_path(route[i]["location"], route[i+1]["location"])
        if segment_path is None:
            return False
    return True

def apply_two_opt(route):
    """Apply 2-opt local search to improve a route"""
    loc_route = route if isinstance(route[0], str) else [r["location"] for r in route]
    improved = True
    best_distance = calculate_total_distance(loc_route)
    best_route = loc_route.copy()
    
    while improved:
        improved = False
        for i in range(1, len(loc_route) - 2):
            for j in range(i + 1, len(loc_route) - 1):
                # Skip if this would violate constraints
                new_route = loc_route.copy()
                new_route[i:j+1] = reversed(new_route[i:j+1])
                if not check_constraints(new_route):
                    continue
                
                # Check if this improves the route
                new_distance = calculate_total_distance(new_route)
                if new_distance < best_distance:
                    best_distance = new_distance
                    best_route = new_route.copy()
                    improved = True
        
        if improved:
            loc_route = best_route.copy()
    
    return best_route

def calculate_total_distance(route):
    """Calculate total distance of a route"""
    total = 0
    for i in range(len(route) - 1):
        dist = get_distance(route[i], route[i+1])
        if dist == float('inf'):
            _, dist = find_detour(route[i], route[i+1])
        if dist == float('inf'):
            return float('inf')
        total += dist
    return total

def nearest_neighbor_route(start, locations):
    """Generate a route using the nearest neighbor heuristic"""
    route = [start]
    remaining = [loc for loc in locations if loc != start]
    
    while remaining:
        current = route[-1]
        nearest = None
        min_dist = float('inf')
        
        for loc in remaining:
            dist = get_distance(current, loc)
            if dist == float('inf'):
                _, dist = find_detour(current, loc)
            
            if dist < min_dist:
                min_dist = dist
                nearest = loc
        
        if nearest is None:  # No accessible location
            break
            
        route.append(nearest)
        remaining.remove(nearest)
    
    return route

def insertion_route(start, locations):
    """Generate a route using the insertion heuristic"""
    route = [start]
    remaining = [loc for loc in locations if loc != start]
    
    # Start with the farthest location to form an initial loop
    farthest = None
    max_dist = -1
    for loc in remaining:
        dist = get_distance(start, loc)
        if dist == float('inf'):
            _, dist = find_detour(start, loc)
        
        if dist > max_dist and dist != float('inf'):
            max_dist = dist
            farthest = loc
    
    if farthest:
        route.append(farthest)
        remaining.remove(farthest)
        route.append(start)  # Complete the loop
    
    # Insert remaining locations
    while remaining:
        best_loc = None
        best_pos = 0
        best_increase = float('inf')
        
        for loc in remaining:
            for i in range(1, len(route)):
                prev = route[i-1]
                next = route[i]
                
                # Calculate increase in distance
                current_dist = get_distance(prev, next)
                if current_dist == float('inf'):
                    _, current_dist = find_detour(prev, next)
                
                dist1 = get_distance(prev, loc)
                if dist1 == float('inf'):
                    _, dist1 = find_detour(prev, loc)
                
                dist2 = get_distance(loc, next)
                if dist2 == float('inf'):
                    _, dist2 = find_detour(loc, next)
                
                if current_dist == float('inf') or dist1 == float('inf') or dist2 == float('inf'):
                    continue
                
                increase = dist1 + dist2 - current_dist
                
                if increase < best_increase:
                    best_increase = increase
                    best_loc = loc
                    best_pos = i
        
        if best_loc is None:  # No valid insertion found
            break
            
        route.insert(best_pos, best_loc)
        remaining.remove(best_loc)
    
    return route

def create_action_route(route):
    """Convert a location route to an action route that handles packages one at a time"""
    action_route = []
    visited = set()
    carrying_package = None
    packages = st.session_state.packages.copy()
    
    # Track packages that need to be picked up and delivered
    packages_to_handle = {p["id"]: {"pickup": p["pickup"], "delivery": p["delivery"], "status": "waiting"} 
                         for p in packages}
    
    # First add the starting location
    if route[0] not in visited:
        action_route.append({"location": route[0], "action": "visit", "package_id": None})
        visited.add(route[0])
    
    # Process the route - ONE PACKAGE AT A TIME
    for i, loc in enumerate(route):
        if loc not in visited and i > 0:  # Skip first location as we already added it
            action_route.append({"location": loc, "action": "visit", "package_id": None})
            visited.add(loc)
        
        # Always deliver before pickup if possible
        if carrying_package is not None:
            pkg = packages_to_handle[carrying_package]
            if pkg["delivery"] == loc:
                action_route.append({"location": loc, "action": "deliver", "package_id": carrying_package})
                pkg["status"] = "delivered"
                carrying_package = None
        
        # Only then check for pickups - just ONE at a time
        if carrying_package is None:  # Only pick up if not carrying anything
            pickups_at_location = [pkg_id for pkg_id, pkg in packages_to_handle.items() 
                                  if pkg["pickup"] == loc and pkg["status"] == "waiting"]
            
            if pickups_at_location:
                pkg_id = pickups_at_location[0]  # Just the first available package
                action_route.append({"location": loc, "action": "pickup", "package_id": pkg_id})
                packages_to_handle[pkg_id]["status"] = "picked_up"
                carrying_package = pkg_id
    
    # Check if we need to add more steps to handle all packages
    unhandled_packages = [pkg_id for pkg_id, pkg in packages_to_handle.items() 
                         if pkg["status"] != "delivered"]
    
    if unhandled_packages:
        # Process each unhandled package one by one
        current_loc = action_route[-1]["location"]
        for pkg_id in unhandled_packages:
            pkg = packages_to_handle[pkg_id]
            
            # Go to pickup if needed
            if pkg["status"] == "waiting":
                if current_loc != pkg["pickup"]:
                    # Generate path to pickup location
                    path, _ = calculate_segment_path(current_loc, pkg["pickup"])
                    if path:
                        # Add intermediate locations if needed (for detours)
                        for intermediate_loc in path[1:-1]:  # Skip first and last
                            action_route.append({"location": intermediate_loc, "action": "visit", "package_id": None})
                        
                        action_route.append({"location": pkg["pickup"], "action": "visit", "package_id": None})
                    
                action_route.append({"location": pkg["pickup"], "action": "pickup", "package_id": pkg_id})
                pkg["status"] = "picked_up"
                current_loc = pkg["pickup"]
                
                # Always deliver immediately after pickup before processing next package
                if current_loc != pkg["delivery"]:
                    # Generate path to delivery location
                    path, _ = calculate_segment_path(current_loc, pkg["delivery"])
                    if path:
                        # Add intermediate locations if needed (for detours)
                        for intermediate_loc in path[1:-1]:  # Skip first and last
                            action_route.append({"location": intermediate_loc, "action": "visit", "package_id": None})
                        
                        action_route.append({"location": pkg["delivery"], "action": "visit", "package_id": None})
                
                action_route.append({"location": pkg["delivery"], "action": "deliver", "package_id": pkg_id})
                pkg["status"] = "delivered"
                current_loc = pkg["delivery"]
    
    return action_route

def solve_tsp(start_location, locations):
    """
    Advanced TSP solver with package constraints, road closure awareness, and 
    multi-objective optimization. Ensures all packages are handled one at a time.
    """
    packages = st.session_state.packages.copy()
    closed_roads = st.session_state.closed_roads if 'closed_roads' in st.session_state else []
    
    # Identify locations with packages
    package_locations = set()
    critical_locations = set()
    for p in packages:
        package_locations.add(p["pickup"])
        package_locations.add(p["delivery"])
        # These are critical constraint locations
        if (p["pickup"] == "Factory" and p["delivery"] == "Shop") or \
           (p["pickup"] == "DHL Hub" and p["delivery"] == "Residence"):
            critical_locations.add(p["pickup"])
            critical_locations.add(p["delivery"])
    
    # Identify all locations we need to visit
    all_locations = set(locations)
    
    # Try multiple route generation strategies
    best_action_route = None
    best_full_path = None
    best_distance = float('inf')
    
    strategies = [
        nearest_neighbor_route,
        insertion_route
    ]
    
    for strategy_func in strategies:
        base_route = strategy_func(start_location, list(all_locations))
        
        # Skip if route doesn't satisfy constraints
        if not check_constraints(base_route):
            continue
        
        # Apply 2-opt optimization if the route has more than 3 locations
        if len(base_route) > 3:
            base_route = apply_two_opt(base_route)
        
        # Create action route with package handling
        action_route = create_action_route(base_route)
        
        # Extract the full path from the action route
        loc_route = []
        for action in action_route:
            loc = action["location"]
            if not loc_route or loc_route[-1] != loc:
                loc_route.append(loc)
        
        # Check if route accounts for road closures
        full_path, total_distance = calculate_route_distance(loc_route)
        
        if full_path and total_distance < best_distance:
            best_action_route = action_route
            best_full_path = full_path
            best_distance = total_distance
    
    # If we couldn't find a good route, try a more aggressive approach
    if best_action_route is None or best_distance == float('inf'):
        # First prioritize picking up packages from Factory and DHL Hub
        priority_pickups = ["Factory", "DHL Hub"]
        other_locs = [loc for loc in all_locations if loc not in priority_pickups]
        
        for priority in priority_pickups:
            if priority in all_locations:
                # Try routes starting with priority locations
                for second_loc in other_locs:
                    route = [start_location, priority, second_loc]
                    for remaining_loc in [l for l in all_locations if l not in route]:
                        route.append(remaining_loc)
                    
                    if check_constraints(route):
                        action_route = create_action_route(route)
                        loc_route = []
                        for action in action_route:
                            loc = action["location"]
                            if not loc_route or loc_route[-1] != loc:
                                loc_route.append(loc)
                        
                        full_path, total_distance = calculate_route_distance(loc_route)
                        if full_path and total_distance < best_distance:
                            best_action_route = action_route
                            best_full_path = full_path
                            best_distance = total_distance
    
    # Last resort: try all permutations of locations
    if (best_action_route is None or best_distance == float('inf')) and len(all_locations) <= 6:
        # Create a directed graph to represent the constraints
        G = nx.DiGraph()
        for loc in all_locations:
            G.add_node(loc)
        
        # Add constraint edges
        if "Factory" in all_locations and "Shop" in all_locations:
            G.add_edge("Factory", "Shop")
        if "DHL Hub" in all_locations and "Residence" in all_locations:
            G.add_edge("DHL Hub", "Residence")
        
        # Get all valid topological orderings
        try:
            # Get all possible topological sorts
            all_topo_sorts = list(nx.all_topological_sorts(G))
            
            # Add start location if not already included
            valid_routes = []
            for topo_sort in all_topo_sorts:
                if start_location not in topo_sort:
                    route = [start_location] + list(topo_sort)
                else:
                    # Ensure start_location is first
                    route = list(topo_sort)
                    route.remove(start_location)
                    route = [start_location] + route
                
                valid_routes.append(route)
            
            # Evaluate each valid route
            for route in valid_routes:
                action_route = create_action_route(route)
                loc_route = []
                for action in action_route:
                    loc = action["location"]
                    if not loc_route or loc_route[-1] != loc:
                        loc_route.append(loc)
                
                full_path, total_distance = calculate_route_distance(loc_route)
                if full_path and total_distance < best_distance:
                    best_action_route = action_route
                    best_full_path = full_path
                    best_distance = total_distance
        except nx.NetworkXUnfeasible:
            # No valid topological sort, constraints cannot be satisfied
            pass
    
    # If we still don't have a valid route, create a simple fallback
    if best_action_route is None:
        # Sort locations to honor constraints
        ordered_locs = []
        if "Factory" in all_locations:
            ordered_locs.append("Factory")
        if "DHL Hub" in all_locations:
            ordered_locs.append("DHL Hub")
        if "Shop" in all_locations:
            ordered_locs.append("Shop")
        if "Residence" in all_locations:
            ordered_locs.append("Residence")
        
        # Add any missing locations
        for loc in all_locations:
            if loc not in ordered_locs:
                ordered_locs.append(loc)
        
        # Start with the specified start location
        if start_location not in ordered_locs:
            route = [start_location] + ordered_locs
        else:
            route = ordered_locs
            # Ensure start location is first
            route.remove(start_location)
            route = [start_location] + route
        
        action_route = create_action_route(route)
        loc_route = []
        for action in action_route:
            loc = action["location"]
            if not loc_route or loc_route[-1] != loc:
                loc_route.append(loc)
        
        full_path, total_distance = calculate_route_distance(loc_route)
        
        # Even if segments have infinite distance, we still need to return something
        if full_path:
            best_action_route = action_route
            best_full_path = full_path
            best_distance = total_distance if total_distance != float('inf') else sum(DISTANCES.values())
    
    # Ensure we return something valid
    if best_action_route and best_full_path and best_distance < float('inf'):
        return best_action_route, best_full_path, best_distance
    else:
        # Last resort fallback - just visit all locations in any order that satisfies constraints
        base_route = list(all_locations)
        if start_location in base_route:
            base_route.remove(start_location)
        base_route = [start_location] + base_route
        
        # Reorder to satisfy constraints
        if "Factory" in base_route and "Shop" in base_route:
            f_idx = base_route.index("Factory")
            s_idx = base_route.index("Shop")
            if f_idx > s_idx:
                base_route.remove("Factory")
                insert_idx = base_route.index("Shop")
                base_route.insert(insert_idx, "Factory")
        
        if "DHL Hub" in base_route and "Residence" in base_route:
            d_idx = base_route.index("DHL Hub")
            r_idx = base_route.index("Residence")
            if d_idx > r_idx:
                base_route.remove("DHL Hub")
                insert_idx = base_route.index("Residence")
                base_route.insert(insert_idx, "DHL Hub")
        
        action_route = create_action_route(base_route)
        # Just use the base route as the path
        return action_route, base_route, 1000  # Arbitrary high distance

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
        # Try any accessible location
        nearest = get_nearest_accessible_location(current_location)
        if nearest:
            return nearest, "detour"
    available_pickups = [p for p in packages if p["pickup"] == current_location and p["status"] == "waiting"]
    if available_pickups and not st.session_state.current_package:
        return current_location, "pickup"
    main_locations = list(LOCATIONS.keys())
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