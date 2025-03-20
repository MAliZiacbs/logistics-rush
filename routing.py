import streamlit as st
from itertools import permutations
import random
import networkx as nx
import copy

from config import DISTANCES, LOCATIONS, check_constraints
from feature_road_closures import is_road_closed
from routing_optimization import apply_two_opt, apply_three_opt, strategic_package_handling

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

def mst_approximation(start, locations):
    """Generate a route using minimum spanning tree approximation"""
    # Create a complete graph with distances as weights
    G = nx.Graph()
    all_locs = [start] + [loc for loc in locations if loc != start]
    
    for i, loc1 in enumerate(all_locs):
        for loc2 in all_locs[i+1:]:
            dist = get_distance(loc1, loc2)
            if dist == float('inf'):
                _, dist = find_detour(loc1, loc2)
            if dist != float('inf'):
                G.add_edge(loc1, loc2, weight=dist)
    
    # Check if graph is connected
    if not nx.is_connected(G):
        return None
    
    # Create a minimum spanning tree
    mst = nx.minimum_spanning_tree(G)
    
    # Perform a depth-first traversal of the MST
    dfs_path = list(nx.dfs_preorder_nodes(mst, source=start))
    
    # The path may not include all locations due to road closures
    if set(dfs_path) != set(all_locs):
        return None
    
    return dfs_path

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

def solve_tsp_improved(start_location, locations, packages):
    """
    Advanced TSP solver with package constraints, road closure awareness, 
    multi-objective optimization, and 3-opt improvement.
    """
    # Initialize the graph
    G = nx.Graph()
    for loc in locations:
        G.add_node(loc)
    for loc1 in locations:
        for loc2 in locations:
            if loc1 != loc2:
                dist = get_distance(loc1, loc2)
                if dist != float('inf'):
                    G.add_edge(loc1, loc2, weight=dist)
    
    # Identify critical constraint locations
    constraint_locations = {
        "Factory": {"before": ["Shop"]},
        "DHL Hub": {"before": ["Residence"]},
        "Shop": {"after": ["Factory"]},
        "Residence": {"after": ["DHL Hub"]}
    }
    
    # Try multiple route generation strategies
    route_candidates = []
    
    # Strategy 1: Nearest Neighbor
    nn_route = nearest_neighbor_route(start_location, locations)
    if nn_route and check_constraints(nn_route):
        route_candidates.append((nn_route, "nearest_neighbor"))
    
    # Strategy 2: Insertion
    ins_route = insertion_route(start_location, locations)
    if ins_route and check_constraints(ins_route):
        route_candidates.append((ins_route, "insertion"))
    
    # Strategy 3: MST Approximation
    mst_route = mst_approximation(start_location, locations)
    if mst_route and check_constraints(mst_route):
        route_candidates.append((mst_route, "mst"))
    
    # Strategy 4: Package-aware routing
    # Start with constraint-based ordering and optimize
    constraint_route = []
    remaining = set(locations)
    
    # Add start location
    constraint_route.append(start_location)
    if start_location in remaining:
        remaining.remove(start_location)
    
    # First add Factory (if not start)
    if "Factory" in remaining:
        constraint_route.append("Factory")
        remaining.remove("Factory")
    
    # Then add DHL Hub (if not start)
    if "DHL Hub" in remaining:
        constraint_route.append("DHL Hub")
        remaining.remove("DHL Hub")
    
    # Then add Shop (which must be after Factory)
    if "Shop" in remaining:
        constraint_route.append("Shop")
        remaining.remove("Shop")
    
    # Then add Residence (which must be after DHL Hub)
    if "Residence" in remaining:
        constraint_route.append("Residence")
        remaining.remove("Residence")
    
    # Add any other remaining locations
    for loc in list(remaining):
        constraint_route.append(loc)
    
    # Only add if it satisfies constraints (should always be true by construction)
    if check_constraints(constraint_route):
        route_candidates.append((constraint_route, "constraint_based"))
    
    # Try brute force with constraints for small problems
    max_brute_force_size = 8
    if len(locations) <= max_brute_force_size:
        valid_perms = []
        # Only try a subset of permutations for medium-sized problems
        max_perms = 1000 if len(locations) > 6 else None
        perm_count = 0
        
        for perm in permutations(locations):
            perm_count += 1
            if max_perms is not None and perm_count > max_perms:
                break
                
            # Ensure starts with start_location
            if perm[0] != start_location:
                continue
                
            # Check constraints
            if check_constraints(perm):
                valid_perms.append(perm)
        
        # Find best permutation
        best_perm = None
        best_dist = float('inf')
        
        for perm in valid_perms:
            dist = calculate_total_distance(perm)
            if dist < best_dist:
                best_dist = dist
                best_perm = perm
        
        if best_perm:
            route_candidates.append((list(best_perm), "brute_force"))
    
    # Apply improvement heuristics to each candidate
    improved_candidates = []
    
    for route, strategy in route_candidates:
        # Skip invalid routes
        if not route or len(route) < len(locations):
            continue
            
        # Apply 2-opt improvement
        improved_2opt = apply_two_opt(route)
        if improved_2opt and check_constraints(improved_2opt):
            improved_candidates.append((improved_2opt, f"{strategy}_2opt"))
        
        # Apply 3-opt improvement for better results
        improved_3opt = apply_three_opt(route)
        if improved_3opt and check_constraints(improved_3opt):
            improved_candidates.append((improved_3opt, f"{strategy}_3opt"))
        
        # Apply strategic package handling optimization
        package_optimized = strategic_package_handling(route, packages)
        if package_optimized and check_constraints(package_optimized):
            improved_candidates.append((package_optimized, f"{strategy}_pkg_opt"))
    
    # Find the best route based on distance
    best_route = None
    best_strategy = None
    best_distance = float('inf')
    
    for route, strategy in improved_candidates:
        distance = calculate_total_distance(route)
        if distance < best_distance:
            best_distance = distance
            best_route = route
            best_strategy = strategy
    
    # If we have a valid route, convert it to action route
    if best_route:
        # Create action route with package handling
        action_route = create_action_route(best_route)
        
        # Extract the full path from the action route
        loc_route = []
        for action in action_route:
            loc = action["location"]
            if not loc_route or loc_route[-1] != loc:
                loc_route.append(loc)
        
        # Check if route accounts for road closures
        full_path, total_distance = calculate_route_distance(loc_route)
        
        if full_path:
            return action_route, full_path, total_distance
    
    # If no valid route found, create a fallback route
    return fallback_route(start_location, locations, packages)

def fallback_route(start_location, locations, packages):
    """
    Create a fallback route when the optimal solution can't be found.
    Ensures a valid route that satisfies all constraints.
    """
    # Create a valid location sequence that satisfies constraints
    location_sequence = []
    
    # Start with starting location
    location_sequence.append(start_location)
    
    # Add constraint locations in correct order
    if "Factory" not in location_sequence:
        location_sequence.append("Factory")
    
    if "DHL Hub" not in location_sequence:
        location_sequence.append("DHL Hub")
    
    if "Shop" not in location_sequence:
        location_sequence.append("Shop")
    
    if "Residence" not in location_sequence:
        location_sequence.append("Residence")
    
    # Add back starting location to complete circuit if not already there
    if location_sequence[-1] != start_location:
        location_sequence.append(start_location)
    
    # Create action route by handling packages one at a time
    action_route = []
    for loc in location_sequence:
        action_route.append({
            "location": loc,
            "action": "visit",
            "package_id": None
        })
    
    # Add package operations between appropriate locations
    for pkg in packages:
        pickup_idx = None
        delivery_idx = None
        
        # Find indices of pickup and delivery locations
        for i, action in enumerate(action_route):
            if action["location"] == pkg["pickup"] and action["action"] == "visit":
                if pickup_idx is None:
                    pickup_idx = i
            if action["location"] == pkg["delivery"] and action["action"] == "visit":
                if delivery_idx is None and (pickup_idx is not None):
                    delivery_idx = i
        
        # If both locations found in correct order, add package operations
        if pickup_idx is not None and delivery_idx is not None and pickup_idx < delivery_idx:
            # Insert pickup after visit
            pickup_action = {
                "location": pkg["pickup"],
                "action": "pickup",
                "package_id": pkg["id"]
            }
            action_route.insert(pickup_idx + 1, pickup_action)
            
            # Delivery index is now shifted by 1
            delivery_idx += 1
            
            # Insert delivery after visit
            delivery_action = {
                "location": pkg["delivery"],
                "action": "deliver",
                "package_id": pkg["id"]
            }
            action_route.insert(delivery_idx + 1, delivery_action)
    
    # Calculate path and distance
    route_path = []
    for action in action_route:
        if not route_path or route_path[-1] != action["location"]:
            route_path.append(action["location"])
    
    # Calculate total distance (use arbitrary high value if can't calculate)
    total_distance = 0
    for i in range(len(route_path) - 1):
        try:
            path, dist = calculate_segment_path(route_path[i], route_path[i+1])
            if dist != float('inf'):
                total_distance += dist
            else:
                total_distance += 100  # Arbitrary high value
        except:
            total_distance += 100  # Arbitrary high value
    
    return action_route, route_path, total_distance

def solve_tsp(start_location, locations):
    """
    Wrapper function that calls the improved TSP solver with packages from session state
    """
    # Get packages from session state
    packages = st.session_state.packages if 'packages' in st.session_state else []
    
    # Call the improved implementation
    action_route, route_path, total_distance = solve_tsp_improved(start_location, locations, packages)
    
    return action_route, route_path, total_distance

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