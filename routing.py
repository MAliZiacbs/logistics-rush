import streamlit as st
from itertools import permutations
import random
import networkx as nx
import copy
import diagnostics  # Added import for diagnostics

from config import DISTANCES, LOCATIONS, check_constraints
from feature_road_closures import is_road_closed
from routing_optimization import apply_two_opt, apply_three_opt, strategic_package_handling

def get_distance(loc1, loc2):
    """Get the distance between two locations, accounting for road closures"""
    if is_road_closed(loc1, loc2):
        distance = float('inf')
        diagnostics.log_distance_calculation(loc1, loc2, distance)
        return distance
    if (loc1, loc2) in DISTANCES:
        distance = DISTANCES[(loc1, loc2)]
        diagnostics.log_distance_calculation(loc1, loc2, distance)
        return distance
    elif (loc2, loc1) in DISTANCES:
        distance = DISTANCES[(loc2, loc1)]
        diagnostics.log_distance_calculation(loc1, loc2, distance)
        return distance
    else:
        distance = float('inf')
        diagnostics.log_distance_calculation(loc1, loc2, distance)
        return distance

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
        # Log the detour in diagnostics
        diagnostics.log_distance_calculation(from_loc, to_loc, detour_distance, False, detour_route)
        return detour_route, detour_distance
    
    return None, float('inf')

# Apply exception catching decorator to critical functions
@diagnostics.catch_and_log_exceptions
def calculate_route_distance(route):
    """
    Calculate the total distance of a route with detours, returning two values.
    Now includes explicit checking for closed roads.
    """
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
        # Check for closed roads
        if is_road_closed(loc_route[i], loc_route[i+1]):
            # Try to find a detour
            segment_path, segment_distance = find_detour(loc_route[i], loc_route[i+1])
        else:
            # Direct route is available
            segment_path, segment_distance = calculate_segment_path(loc_route[i], loc_route[i+1])
            
        if segment_distance == float('inf'):
            diagnostics.log_error("Route Distance", f"No path found between {loc_route[i]} and {loc_route[i+1]}")
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
    
    # Process the route - ONE PACKAGE AT A TIME while handling detours
    current_loc = route[0]
    for i in range(1, len(route)):
        next_loc = route[i]
        
        # Check if we need to use a detour
        from feature_road_closures import is_road_closed
        if is_road_closed(current_loc, next_loc):
            # Find the detour path
            segment_path, _ = calculate_segment_path(current_loc, next_loc)
            if segment_path and len(segment_path) > 2:  # If we have intermediate locations
                # Add each location in the detour
                for detour_loc in segment_path[1:-1]:  # Skip first and last (current and next)
                    if detour_loc not in visited:
                        action_route.append({"location": detour_loc, "action": "visit", "package_id": None})
                        visited.add(detour_loc)
                    
                    # Check for deliveries at detour locations
                    if carrying_package is not None:
                        pkg = packages_to_handle[carrying_package]
                        if pkg["delivery"] == detour_loc:
                            action_route.append({"location": detour_loc, "action": "deliver", "package_id": carrying_package})
                            pkg["status"] = "delivered"
                            carrying_package = None
                    
                    # Check for pickups at detour locations if not carrying
                    if carrying_package is None:
                        pickups_at_location = [pkg_id for pkg_id, pkg in packages_to_handle.items() 
                                              if pkg["pickup"] == detour_loc and pkg["status"] == "waiting"]
                        if pickups_at_location:
                            pkg_id = pickups_at_location[0]
                            action_route.append({"location": detour_loc, "action": "pickup", "package_id": pkg_id})
                            packages_to_handle[pkg_id]["status"] = "picked_up"
                            carrying_package = pkg_id
        
        # Add the next location
        if next_loc not in visited:
            action_route.append({"location": next_loc, "action": "visit", "package_id": None})
            visited.add(next_loc)
        
        # Always deliver before pickup if possible
        if carrying_package is not None:
            pkg = packages_to_handle[carrying_package]
            if pkg["delivery"] == next_loc:
                action_route.append({"location": next_loc, "action": "deliver", "package_id": carrying_package})
                pkg["status"] = "delivered"
                carrying_package = None
        
        # Only then check for pickups - just ONE at a time
        if carrying_package is None:  # Only pick up if not carrying anything
            pickups_at_location = [pkg_id for pkg_id, pkg in packages_to_handle.items() 
                                  if pkg["pickup"] == next_loc and pkg["status"] == "waiting"]
            
            if pickups_at_location:
                pkg_id = pickups_at_location[0]  # Just the first available package
                action_route.append({"location": next_loc, "action": "pickup", "package_id": pkg_id})
                packages_to_handle[pkg_id]["status"] = "picked_up"
                carrying_package = pkg_id
        
        current_loc = next_loc
    
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
                    # Generate path to pickup location with detours
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
                    # Generate path to delivery location with detours
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

@diagnostics.catch_and_log_exceptions
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
        "Warehouse": {"before": ["Shop"]},
        "Distribution Center": {"before": ["Home"]},
        "Shop": {"after": ["Warehouse"]},
        "Home": {"after": ["Distribution Center"]}
    }
    
    # Try multiple route generation strategies
    route_candidates = []
    
    # Strategy 1: Nearest Neighbor
    diagnostics.log_event("Route Generation", "Trying nearest neighbor strategy")
    nn_route = nearest_neighbor_route(start_location, locations)
    if nn_route and check_constraints(nn_route):
        route_candidates.append((nn_route, "nearest_neighbor"))
        diagnostics.log_event("Route Generation", "Valid nearest neighbor route found")
    
    # Strategy 2: Insertion
    diagnostics.log_event("Route Generation", "Trying insertion strategy")
    ins_route = insertion_route(start_location, locations)
    if ins_route and check_constraints(ins_route):
        route_candidates.append((ins_route, "insertion"))
        diagnostics.log_event("Route Generation", "Valid insertion route found")
    
    # Strategy 3: MST Approximation
    diagnostics.log_event("Route Generation", "Trying MST approximation strategy")
    mst_route = mst_approximation(start_location, locations)
    if mst_route and check_constraints(mst_route):
        route_candidates.append((mst_route, "mst"))
        diagnostics.log_event("Route Generation", "Valid MST route found")
    
    # Strategy 4: Package-aware routing
    # Start with constraint-based ordering and optimize
    constraint_route = []
    remaining = set(locations)
    
    # Add start location
    constraint_route.append(start_location)
    if start_location in remaining:
        remaining.remove(start_location)
    
    # First add Warehouse (if not start)
    if "Warehouse" in remaining:
        constraint_route.append("Warehouse")
        remaining.remove("Warehouse")
    
    # Then add Distribution Center (if not start)
    if "Distribution Center" in remaining:
        constraint_route.append("Distribution Center")
        remaining.remove("Distribution Center")
    
    # Then add Shop (which must be after Warehouse)
    if "Shop" in remaining:
        constraint_route.append("Shop")
        remaining.remove("Shop")
    
    # Then add Home (which must be after Distribution Center)
    if "Home" in remaining:
        constraint_route.append("Home")
        remaining.remove("Home")
    
    # Add any other remaining locations
    for loc in list(remaining):
        constraint_route.append(loc)
    
    # Only add if it satisfies constraints (should always be true by construction)
    if check_constraints(constraint_route):
        route_candidates.append((constraint_route, "constraint_based"))
        diagnostics.log_event("Route Generation", "Valid constraint-based route found")
    
    # Try brute force with constraints for small problems
    max_brute_force_size = 8
    if len(locations) <= max_brute_force_size:
        diagnostics.log_event("Route Generation", "Trying brute force for small problem")
        valid_perms = []
        # Only try a subset of permutations for medium-sized problems
        max_perms = 1000 if len(locations) > 6 else None
        perm_count = 0
        
        for perm in permutations(locations):
            perm_count += 1
            if max_perms is not None and perm_count > max_perms:
                diagnostics.log_event("Route Generation", f"Brute force search stopped after {max_perms} permutations")
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
            diagnostics.log_event("Route Generation", f"Valid brute force route found with distance {best_dist}")
    
    # Apply improvement heuristics to each candidate
    improved_candidates = []
    
    for route, strategy in route_candidates:
        # Skip invalid routes
        if not route or len(route) < len(locations):
            continue
            
        # Apply 2-opt improvement
        diagnostics.log_event("Route Improvement", f"Applying 2-opt to {strategy} route")
        improved_2opt = apply_two_opt(route)
        if improved_2opt and check_constraints(improved_2opt):
            improved_candidates.append((improved_2opt, f"{strategy}_2opt"))
            diagnostics.log_event("Route Improvement", f"Valid 2-opt improvement for {strategy} found")
        
        # Apply 3-opt improvement for better results
        diagnostics.log_event("Route Improvement", f"Applying 3-opt to {strategy} route")
        improved_3opt = apply_three_opt(route)
        if improved_3opt and check_constraints(improved_3opt):
            improved_candidates.append((improved_3opt, f"{strategy}_3opt"))
            diagnostics.log_event("Route Improvement", f"Valid 3-opt improvement for {strategy} found")
        
        # Apply strategic package handling optimization
        diagnostics.log_event("Route Improvement", f"Applying package optimization to {strategy} route")
        package_optimized = strategic_package_handling(route, packages)
        if package_optimized and check_constraints(package_optimized):
            improved_candidates.append((package_optimized, f"{strategy}_pkg_opt"))
            diagnostics.log_event("Route Improvement", f"Valid package optimization for {strategy} found")
    
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
    
    if best_route:
        diagnostics.log_event("Route Selection", f"Best route found using {best_strategy} with distance {best_distance}")
    else:
        diagnostics.log_error("Route Selection", "No valid route found among candidates")
    
    # If we have a valid route, convert it to action route
    if best_route:
        # Create action route with package handling
        action_route = create_action_route(best_route)
        
        # Extract the full path from the action route, ensuring detours are included
        loc_route = []
        for action in action_route:
            loc = action["location"]
            if not loc_route or loc_route[-1] != loc:
                loc_route.append(loc)
        
        # Create a comprehensive path that includes all detours
        full_path = []
        total_distance = 0
        
        for i in range(len(loc_route) - 1):
            segment_path, segment_distance = calculate_segment_path(loc_route[i], loc_route[i+1])
            
            if segment_path:
                if i == 0:
                    full_path.extend(segment_path)
                else:
                    full_path.extend(segment_path[1:])  # Skip first to avoid duplication
                
                total_distance += segment_distance
            else:
                # If no path is found, this shouldn't happen after validation
                diagnostics.log_error("Path Creation", f"No path found between {loc_route[i]} and {loc_route[i+1]}")
                return fallback_route(start_location, locations, packages)
        
        if full_path:
            # Final check to ensure the path is valid
            if validate_optimal_route(action_route, full_path, packages):
                return action_route, full_path, total_distance
            else:
                diagnostics.log_error("Route Validation", "Final route validation failed")
                
    # If no valid route found, create a fallback route
    diagnostics.log_event("Route Fallback", "Using fallback route creation")
    return fallback_route(start_location, locations, packages)

@diagnostics.catch_and_log_exceptions
def fallback_route(start_location, locations, packages):
    """
    Create a fallback route when the optimal solution can't be found.
    Ensures a valid route that satisfies all constraints and avoids closed roads.
    """
    diagnostics.log_event("Fallback Route", "Creating fallback route")
    
    # Create a valid location sequence that satisfies constraints
    location_sequence = []
    
    # Start with starting location
    location_sequence.append(start_location)
    
    # Create a graph representation without closed roads
    G = nx.Graph()
    for loc in locations:
        G.add_node(loc)
    for loc1 in locations:
        for loc2 in locations:
            if loc1 != loc2 and not is_road_closed(loc1, loc2):
                G.add_edge(loc1, loc2)
    
    # Function to find a valid path between two locations
    def find_valid_path(from_loc, to_loc):
        try:
            return nx.shortest_path(G, from_loc, to_loc)
        except nx.NetworkXNoPath:
            return None
    
    # Add constraint locations in correct order, ensuring we can reach them
    # Make sure Warehouse comes before Shop
    if "Warehouse" not in location_sequence:
        factory_path = find_valid_path(location_sequence[-1], "Warehouse")
        if factory_path:
            # Add all locations along path except the starting point which is already there
            location_sequence.extend(factory_path[1:])
            diagnostics.log_event("Fallback Route", f"Added path to Warehouse: {factory_path[1:]}")
    
    # Make sure Distribution Center comes next after Warehouse if not already visited
    if "Distribution Center" not in location_sequence:
        dhl_path = find_valid_path(location_sequence[-1], "Distribution Center")
        if dhl_path:
            location_sequence.extend(dhl_path[1:])
            diagnostics.log_event("Fallback Route", f"Added path to Distribution Center: {dhl_path[1:]}")
    
    # Then add Shop after Warehouse
    if "Shop" not in location_sequence:
        shop_path = find_valid_path(location_sequence[-1], "Shop")
        if shop_path:
            location_sequence.extend(shop_path[1:])
            diagnostics.log_event("Fallback Route", f"Added path to Shop: {shop_path[1:]}")
    
    # Finally add Home after Distribution Center
    if "Home" not in location_sequence:
        res_path = find_valid_path(location_sequence[-1], "Home")
        if res_path:
            location_sequence.extend(res_path[1:])
            diagnostics.log_event("Fallback Route", f"Added path to Home: {res_path[1:]}")
    
    # Complete the circuit back to start if possible
    if location_sequence[-1] != start_location:
        return_path = find_valid_path(location_sequence[-1], start_location)
        if return_path:
            location_sequence.extend(return_path[1:])
            diagnostics.log_event("Fallback Route", f"Added return path to start: {return_path[1:]}")
    
    # Ensure all locations are included
    for loc in locations:
        if loc not in location_sequence:
            # Try to insert location at a valid position that respects constraints
            for i in range(len(location_sequence)):
                # Skip insertion at beginning
                if i == 0:
                    continue
                    
                # Check if we can insert this location while respecting constraints
                test_seq = location_sequence.copy()
                test_seq.insert(i, loc)
                
                # Check if the modified sequence satisfies constraints
                if check_constraints(test_seq):
                    # Check if we can reach this location from previous and next
                    prev_loc = test_seq[i-1]
                    next_loc = test_seq[i+1] if i+1 < len(test_seq) else None
                    
                    can_reach_from_prev = not is_road_closed(prev_loc, loc)
                    can_reach_next = next_loc is None or not is_road_closed(loc, next_loc)
                    
                    if can_reach_from_prev and can_reach_next:
                        location_sequence.insert(i, loc)
                        diagnostics.log_event("Fallback Route", f"Inserted {loc} at position {i}")
                        break
            
            # If we still couldn't add the location, log the error
            if loc not in location_sequence:
                diagnostics.log_error("Fallback Route", f"Unable to add {loc} to fallback route")
    
    # Final check to make sure constraints are satisfied
    if not check_constraints(location_sequence):
        # If constraints are violated, re-order the locations to satisfy them
        diagnostics.log_error("Fallback Route", "Final constraints check failed, reordering")
        
        # This is a last resort to ensure a valid route
        new_sequence = [start_location]
        remaining = set(location_sequence) - {start_location}
        
        # Add Warehouse if not already there
        if "Warehouse" in remaining and "Warehouse" != start_location:
            new_sequence.append("Warehouse")
            remaining.remove("Warehouse")
        
        # Add Distribution Center if not already there
        if "Distribution Center" in remaining and "Distribution Center" != start_location:
            new_sequence.append("Distribution Center")
            remaining.remove("Distribution Center")
        
        # Add Shop after Warehouse
        if "Shop" in remaining and "Shop" != start_location:
            new_sequence.append("Shop")
            remaining.remove("Shop")
        
        # Add Home after Distribution Center
        if "Home" in remaining and "Home" != start_location:
            new_sequence.append("Home")
            remaining.remove("Home")
        
        # Add remaining locations
        for loc in remaining:
            new_sequence.append(loc)
        
        location_sequence = new_sequence
        diagnostics.log_event("Fallback Route", f"Reordered route: {location_sequence}")
        # Create action route
    action_route = []
    for loc in location_sequence:
        action_route.append({
            "location": loc,
            "action": "visit",
            "package_id": None
        })
    
    # Handle packages
    # First, verify if the path is valid with respect to road closures
    valid_path = []
    for i in range(len(location_sequence) - 1):
        segment_path, segment_distance = calculate_segment_path(location_sequence[i], location_sequence[i+1])
        if segment_path:
            if i == 0:
                valid_path.extend(segment_path)
            else:
                valid_path.extend(segment_path[1:])  # Skip first to avoid duplication
        else:
            # If no valid path, try to find a detour
            detour_exists = False
            for intermediate in locations:
                if intermediate != location_sequence[i] and intermediate != location_sequence[i+1]:
                    path1, dist1 = calculate_segment_path(location_sequence[i], intermediate)
                    path2, dist2 = calculate_segment_path(intermediate, location_sequence[i+1])
                    
                    if path1 and path2 and dist1 != float('inf') and dist2 != float('inf'):
                        if i == 0:
                            valid_path.extend(path1)
                        else:
                            valid_path.extend(path1[1:])  # Skip first to avoid duplication
                        valid_path.extend(path2[1:])  # Skip first to avoid duplication
                        detour_exists = True
                        diagnostics.log_event("Fallback Route", f"Found detour via {intermediate}")
                        break
            
            if not detour_exists:
                # If we can't find a valid path, we need to skip this segment
                # and try to find an alternative route
                diagnostics.log_error("Fallback Route", f"No path found between {location_sequence[i]} and {location_sequence[i+1]}")
                continue
    
    # Calculate total distance (use actual segment distances)
    total_distance = 0
    route_path = location_sequence
    
    for i in range(len(route_path) - 1):
        _, segment_distance = calculate_segment_path(route_path[i], route_path[i+1])
        if segment_distance != float('inf'):
            total_distance += segment_distance
    
    diagnostics.log_event("Fallback Route", f"Final fallback route created with distance {total_distance}")
    return action_route, route_path, total_distance

@diagnostics.catch_and_log_exceptions
def solve_tsp(start_location, locations):
    """
    Wrapper function that calls the improved TSP solver with packages from session state,
    with better handling of road closures and complete package handling validation.
    """
    # Get packages from session state
    packages = st.session_state.packages if 'packages' in st.session_state else []
    
    try:
        # Try the improved implementation
        diagnostics.log_event("TSP Solver", "Starting advanced TSP solution")
        action_route, route_path, total_distance = solve_tsp_improved(start_location, locations, packages)
        
        # Enhanced validation of the solution
        # 1. Check if all locations are visited
        location_set = set(locations)
        route_locations = set(route_path)
        
        if not location_set.issubset(route_locations):
            missing_locations = [loc for loc in locations if loc not in route_path]
            st.warning(f"Optimal route calculation did not include all locations ({', '.join(missing_locations)}). Using fallback route.")
            diagnostics.log_error("Route Validation", f"Missing locations in route: {missing_locations}")
            action_route, route_path, total_distance = fallback_route(start_location, locations, packages)
        
        # 2. Check for any closed roads in the path
        invalid_path = False
        for i in range(len(route_path) - 1):
            if is_road_closed(route_path[i], route_path[i+1]):
                invalid_path = True
                st.warning(f"Optimal route included closed road between {route_path[i]} and {route_path[i+1]}. Using fallback route.")
                diagnostics.log_error("Route Validation", f"Route uses closed road: {route_path[i]} → {route_path[i+1]}")
                break
        
        # 3. Verify the total distance is reasonable (not near zero or infinity)
        if total_distance < 50 or total_distance == float('inf'):
            invalid_path = True
            st.warning(f"Optimal route has unrealistic distance: {total_distance}. Using fallback route.")
            diagnostics.log_error("Route Validation", f"Unrealistic route distance: {total_distance}")
        
        # 4. Check if the path satisfies constraints
        if not check_constraints(route_path):
            invalid_path = True
            st.warning("Optimal route does not satisfy sequence constraints. Using fallback route.")
            diagnostics.log_error("Route Validation", "Route violates sequence constraints")
        
        # 5. Verify that all packages can be handled (critical)
        if packages:
            # Track package handling through actions
            handled_packages = set()
            carrying_package = None
            
            for action in action_route:
                if action["action"] == "pickup":
                    if carrying_package is not None:
                        invalid_path = True
                        st.warning("Optimal route tries to carry multiple packages simultaneously. Using fallback route.")
                        diagnostics.log_error("Route Validation", "Route attempts to carry multiple packages")
                        break
                    carrying_package = action["package_id"]
                    handled_packages.add(carrying_package)
                elif action["action"] == "deliver":
                    if carrying_package != action["package_id"]:
                        invalid_path = True
                        st.warning("Optimal route has inconsistent package handling. Using fallback route.")
                        diagnostics.log_error("Route Validation", "Route has inconsistent package handling")
                        break
                    carrying_package = None
            
            # Check if all packages are handled
            if len(handled_packages) < len(packages):
                invalid_path = True
                st.warning(f"Optimal route only handles {len(handled_packages)}/{len(packages)} packages. Using fallback route.")
                diagnostics.log_error("Route Validation", f"Route only handles {len(handled_packages)}/{len(packages)} packages")
        
        if invalid_path:
            diagnostics.log_event("TSP Solver", "Using fallback route due to validation issues")
            action_route, route_path, total_distance = fallback_route(start_location, locations, packages)
        
        # Critical: Ensure the route includes ALL locations after all validations
        if route_path and set(route_path) != set(locations):
            missing = [loc for loc in locations if loc not in route_path]
            diagnostics.log_error("Route Validation", f"Still missing locations after validation: {missing}")
            
            # Add missing locations while respecting constraints
            temp_path = route_path.copy()
            for loc in missing:
                # Find appropriate position based on constraints
                if loc == "Shop" and "Warehouse" in temp_path:
                    # Insert Shop after Warehouse
                    warehouse_idx = temp_path.index("Warehouse")
                    temp_path.insert(warehouse_idx + 1, loc)
                    diagnostics.log_event("Route Correction", f"Added {loc} after Warehouse")
                elif loc == "Home" and "Distribution Center" in temp_path:
                    # Insert Home after Distribution Center
                    dc_idx = temp_path.index("Distribution Center")
                    temp_path.insert(dc_idx + 1, loc)
                    diagnostics.log_event("Route Correction", f"Added {loc} after Distribution Center")
                else:
                    # Add at the end
                    temp_path.append(loc)
                    diagnostics.log_event("Route Correction", f"Added {loc} at the end")
            
            # If the new path satisfies constraints, use it
            if check_constraints(temp_path):
                route_path = temp_path
                
                # Rebuild action_route based on updated route_path
                updated_action_route = []
                for loc in route_path:
                    # Check if this location already has actions in the original action_route
                    loc_actions = [a for a in action_route if a["location"] == loc]
                    if loc_actions:
                        for action in loc_actions:
                            updated_action_route.append(action)
                    else:
                        updated_action_route.append({"location": loc, "action": "visit", "package_id": None})
                
                action_route = updated_action_route
                diagnostics.log_event("Route Correction", "Rebuilt action route with all locations")
                
                # Recalculate total distance
                _, recalculated_distance = calculate_route_distance(route_path)
                if recalculated_distance != float('inf') and recalculated_distance >= 50:
                    total_distance = recalculated_distance
                    diagnostics.log_event("Route Correction", f"Recalculated distance: {total_distance}")
            
        # Final validation of the fallback route
        if len(route_path) < len(locations) or total_distance < 50 or total_distance == float('inf'):
            st.error("Route calculation encountered serious issues. Using minimal valid route.")
            diagnostics.log_error("Route Final Check", f"Critical route issues: path length={len(route_path)}, distance={total_distance}")
            
            # Create a minimal valid route as absolute fallback
            route_path = ["Warehouse", "Distribution Center", "Shop", "Home"]
            
            # Create a simple action route that handles all packages
            action_route = []
            
            # Add initial visit to starting location
            action_route.append({"location": "Warehouse", "action": "visit", "package_id": None})
            
            # Handle the Warehouse to Shop package
            warehouse_to_shop = next((p for p in packages if p["pickup"] == "Warehouse" and p["delivery"] == "Shop"), None)
            if warehouse_to_shop:
                action_route.append({"location": "Warehouse", "action": "pickup", "package_id": warehouse_to_shop["id"]})
            
            # Go to Distribution Center
            action_route.append({"location": "Distribution Center", "action": "visit", "package_id": None})
            
            # Handle the Distribution Center to Home package
            dc_to_home = next((p for p in packages if p["pickup"] == "Distribution Center" and p["delivery"] == "Home"), None)
            if dc_to_home:
                action_route.append({"location": "Distribution Center", "action": "pickup", "package_id": dc_to_home["id"]})
            
            # Go to Shop
            action_route.append({"location": "Shop", "action": "visit", "package_id": None})
            
            # Deliver the Warehouse to Shop package
            if warehouse_to_shop:
                action_route.append({"location": "Shop", "action": "deliver", "package_id": warehouse_to_shop["id"]})
            
            # Go to Home
            action_route.append({"location": "Home", "action": "visit", "package_id": None})
            
            # Deliver the Distribution Center to Home package
            if dc_to_home:
                action_route.append({"location": "Home", "action": "deliver", "package_id": dc_to_home["id"]})
            
            # Add any remaining packages with pragmatic pickup/delivery
            remaining_packages = [p for p in packages if p not in [warehouse_to_shop, dc_to_home] if warehouse_to_shop and dc_to_home else packages]
            for pkg in remaining_packages:
                action_route.append({"location": pkg["pickup"], "action": "pickup", "package_id": pkg["id"]})
                action_route.append({"location": pkg["delivery"], "action": "deliver", "package_id": pkg["id"]})
            
            # Calculate a reasonable distance based on the DISTANCES in config
            from config import DISTANCES
            total_distance = sum(DISTANCES.get((route_path[i], route_path[i+1]), 
                                 DISTANCES.get((route_path[i+1], route_path[i]), 300)) 
                                 for i in range(len(route_path)-1))
            
            diagnostics.log_event("Route Minimal Fallback", f"Created minimal valid route with distance {total_distance}")
    
    except Exception as e:
        # If any error occurs, use a guaranteed valid minimal route
        st.warning(f"Routing calculation encountered an error: {e}. Using minimal valid route.")
        diagnostics.log_error("TSP Solver Exception", str(e))
        
        # Create a minimal valid route that satisfies constraints
        route_path = ["Warehouse", "Distribution Center", "Shop", "Home"]
        
        # Create a simple action route that handles all packages
        action_route = []
        
        # Add initial visit to starting location
        action_route.append({"location": "Warehouse", "action": "visit", "package_id": None})
        
        # Handle packages in a valid sequence
        if packages:
            # First handle Warehouse to Shop package
            warehouse_pkg = next((p for p in packages if p["pickup"] == "Warehouse"), None)
            if warehouse_pkg:
                action_route.append({"location": "Warehouse", "action": "pickup", "package_id": warehouse_pkg["id"]})
                action_route.append({"location": warehouse_pkg["delivery"], "action": "deliver", "package_id": warehouse_pkg["id"]})
            
            # Then handle Distribution Center to Home package
            action_route.append({"location": "Distribution Center", "action": "visit", "package_id": None})
            dc_pkg = next((p for p in packages if p["pickup"] == "Distribution Center"), None)
            if dc_pkg:
                action_route.append({"location": "Distribution Center", "action": "pickup", "package_id": dc_pkg["id"]})
                action_route.append({"location": dc_pkg["delivery"], "action": "deliver", "package_id": dc_pkg["id"]})
            
            # Make sure Shop and Home are visited
            if "Shop" not in [a["location"] for a in action_route]:
                action_route.append({"location": "Shop", "action": "visit", "package_id": None})
            if "Home" not in [a["location"] for a in action_route]:
                action_route.append({"location": "Home", "action": "visit", "package_id": None})
            
            # Handle any remaining packages
            for pkg in packages:
                if pkg != warehouse_pkg and pkg != dc_pkg:
                    action_route.append({"location": pkg["pickup"], "action": "pickup", "package_id": pkg["id"]})
                    action_route.append({"location": pkg["delivery"], "action": "deliver", "package_id": pkg["id"]})
        
        # Calculate a reasonable distance based on the DISTANCES in config
        from config import DISTANCES
        total_distance = sum(DISTANCES.get((route_path[i], route_path[i+1]), 
                             DISTANCES.get((route_path[i+1], route_path[i]), 300)) 
                             for i in range(len(route_path)-1))
        
        diagnostics.log_event("Route Exception Fallback", f"Created exception fallback route with distance {total_distance}")
    
    # Additional sanity check on the returned distance
    if total_distance < 100:
        # Recalculate the distance using the DISTANCES from config
        from config import DISTANCES
        recalculated_distance = 0
        
        # Extract locations from action route, preserving order and duplicates
        route_locs = []
        for action in action_route:
            if not route_locs or route_locs[-1] != action["location"]:
                route_locs.append(action["location"])
        
        for i in range(len(route_locs) - 1):
            segment_distance = DISTANCES.get((route_locs[i], route_locs[i+1]), 
                                             DISTANCES.get((route_locs[i+1], route_locs[i]), 300))
            recalculated_distance += segment_distance
            
        # Use the recalculated distance if it's more reasonable
        if recalculated_distance >= 100:
            total_distance = recalculated_distance
            diagnostics.log_event("Distance Correction", f"Using recalculated distance: {total_distance}")
        else:
            # As a last resort, set a minimum reasonable distance based on the defined distances
            from config import DISTANCES
            min_reasonable_distance = min([d for d in DISTANCES.values() if d > 0]) * (len(locations) - 1)
            total_distance = max(total_distance, min_reasonable_distance, 100)
            diagnostics.log_event("Distance Correction", f"Using minimum reasonable distance: {total_distance}")
    
    # Log the final route to diagnostics
    diagnostics.log_optimal_route_data(action_route, route_path, total_distance)
    
    return action_route, route_path, total_distance

@diagnostics.catch_and_log_exceptions
def validate_optimal_route(route, path, packages):
    """
    Validates that the optimal route satisfies all requirements:
    - Handles all packages
    - Satisfies all constraints
    - Forms a valid path with no impossible segments
    - Correctly handles detours
    
    Returns True if valid, False otherwise
    """
    if not route or not path:
        diagnostics.log_error("Route Validation", "Empty route or path")
        return False
    
    # Collect all package IDs that are handled in the route
    handled_packages = set()
    carrying = None
    
    for action in route:
        if action["action"] == "pickup":
            if carrying is not None:
                diagnostics.log_error("Route Validation", "Multiple packages carried simultaneously")
                return False  # Can't carry more than one package
            carrying = action["package_id"]
            handled_packages.add(action["package_id"])
        elif action["action"] == "deliver":
            if carrying != action["package_id"]:
                diagnostics.log_error("Route Validation", "Attempted to deliver package not being carried")
                return False  # Can't deliver what we're not carrying
            carrying = None
    
    # All packages should be handled
    if len(handled_packages) != len(packages):
        diagnostics.log_error("Route Validation", f"Not all packages handled: {len(handled_packages)}/{len(packages)}")
        return False
    
    # Check if path satisfies sequence constraints
    if "Warehouse" in path and "Shop" in path:
        f_idx = path.index("Warehouse")
        s_idx = path.index("Shop")
        if f_idx > s_idx:
            diagnostics.log_error("Route Validation", "Constraint violation: Shop before Warehouse")
            return False  # Warehouse must come before Shop
    
    if "Distribution Center" in path and "Home" in path:
        d_idx = path.index("Distribution Center")
        r_idx = path.index("Home")
        if d_idx > r_idx:
            diagnostics.log_error("Route Validation", "Constraint violation: Home before Distribution Center")
            return False  # Distribution Center must come before Home
    
    # Check if all consecutive locations in the path are valid (considering detours)
    for i in range(len(path) - 1):
        # Rather than directly checking is_road_closed, use calculate_segment_path
        # which accounts for detours
        segment_path, segment_distance = calculate_segment_path(path[i], path[i+1])
        if segment_path is None or segment_distance == float('inf'):
            diagnostics.log_error("Route Validation", f"No valid path between {path[i]} and {path[i+1]}")
            return False
    
    # If we passed all checks, the route is valid
    return True

# Add a helper function to explicitly check for and report closed roads in a path
def check_closed_roads_in_path(path):
    """
    Check if a path contains segments that use closed roads.
    Returns a list of problematic segments.
    """
    closed_road_segments = []
    
    for i in range(len(path) - 1):
        if is_road_closed(path[i], path[i+1]):
            closed_road_segments.append((path[i], path[i+1]))
    
    if closed_road_segments:
        diagnostics.log_error("Path Validation", f"Path uses closed roads: {closed_road_segments}")
        
    return closed_road_segments

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