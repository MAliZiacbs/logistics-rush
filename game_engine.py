import streamlit as st
import numpy as np
import time

from config import LOCATIONS, SCORING_WEIGHTS, check_constraints
from routing import solve_tsp, get_distance, calculate_route_distance
from feature_road_closures import generate_road_closures, is_road_closed
from feature_packages import generate_packages
from data_management import save_player_data
import route_analysis

def update_difficulty_display(num_actual_closures):
    """Update the displayed difficulty based on the actual number of closures"""
    if num_actual_closures >= 3:
        st.session_state.displayed_difficulty = "Hard"
    elif num_actual_closures >= 2:
        st.session_state.displayed_difficulty = "Medium"
    elif num_actual_closures >= 1:
        st.session_state.displayed_difficulty = "Easy"
    else:
        st.session_state.displayed_difficulty = "No Closures"
    
    # This will be used for display purposes
    st.session_state.actual_num_closures = num_actual_closures

def validate_optimal_route(route, path, packages):
    """
    Validates that the optimal route satisfies all requirements:
    - Handles all packages
    - Satisfies all constraints
    - Forms a valid path with no impossible segments
    
    Returns True if valid, False otherwise
    """
    if not route or not path:
        return False
    
    # Collect all package IDs that are handled in the route
    handled_packages = set()
    carrying = None
    
    for action in route:
        if action["action"] == "pickup":
            if carrying is not None:
                return False  # Can't carry more than one package
            carrying = action["package_id"]
            handled_packages.add(action["package_id"])
        elif action["action"] == "deliver":
            if carrying != action["package_id"]:
                return False  # Can't deliver what we're not carrying
            carrying = None
    
    # All packages should be handled
    if len(handled_packages) != len(packages):
        return False
    
    # Check if path satisfies sequence constraints
    if "Factory" in path and "Shop" in path:
        f_idx = path.index("Factory")
        s_idx = path.index("Shop")
        if f_idx > s_idx:
            return False  # Factory must come before Shop
    
    if "DHL Hub" in path and "Residence" in path:
        d_idx = path.index("DHL Hub")
        r_idx = path.index("Residence")
        if d_idx > r_idx:
            return False  # DHL Hub must come before Residence
    
    # Check if all path segments are valid (no infinite distances)
    for i in range(len(path) - 1):
        _, distance = calculate_segment_path(path[i], path[i+1])
        if distance == float('inf'):
            return False
    
    # If we passed all checks, the route is valid
    return True

def start_new_game():
    """Start a new game with all features combined - with improved error handling"""
    st.session_state.game_active = True
    st.session_state.start_time = time.time()
    
    st.session_state.current_package = None
    st.session_state.delivered_packages = []
    st.session_state.current_route = ["Warehouse"]  # Start at Warehouse
    st.session_state.optimal_route = None
    st.session_state.optimal_path = None
    
    locations_to_visit = list(LOCATIONS.keys())
    start_location = "Warehouse"

    st.session_state.constraints = {
        "Warehouse": "Must visit before Shop",
        "Shop": "Must visit after Warehouse",
        "Distribution Center": "Must visit before Home",
        "Home": "Must visit after Distribution Center"
    }
    
    # First generate packages
    st.session_state.packages = generate_packages(num_packages=3)
    st.session_state.total_packages = len(st.session_state.packages)
    
    # Get the number of road closures based on difficulty (default to 1 if not set)
    num_closures = st.session_state.get('num_road_closures', 1)
    
    try:
        # Generate road closures based on selected difficulty
        st.session_state.closed_roads = generate_road_closures(num_closures=num_closures)
        
        # Update difficulty display based on actual number of closures generated
        update_difficulty_display(len(st.session_state.closed_roads))

        # Display accurate difficulty message
        if len(st.session_state.closed_roads) != num_closures:
            actual_difficulty = st.session_state.displayed_difficulty
            st.info(f"Note: {actual_difficulty} mode with {len(st.session_state.closed_roads)} road closure(s) was applied to ensure a playable game.")
        else:
            if num_closures == 1:
                st.info(f"Easy mode: 1 road closure generated.")
            elif num_closures == 2:
                st.info(f"Medium mode: {len(st.session_state.closed_roads)} road closures generated.")
            else:
                st.info(f"Hard mode: {len(st.session_state.closed_roads)} road closures generated.")
        
        # If no closures were possible, let the player know
        if len(st.session_state.closed_roads) == 0:
            st.warning("No road closures were possible while ensuring all packages could be delivered.")
    except Exception as e:
        # Fallback to a safe configuration if road closure generation fails
        st.warning("Using default road closures to ensure a playable game.")
        st.session_state.closed_roads = [("Warehouse", "Shop")]  # Safe default
        update_difficulty_display(1)  # Set to Easy mode

    try:
        # Try to find an optimal route with the improved algorithm
        optimal_route, optimal_path, optimal_distance = solve_tsp(start_location, locations_to_visit)
        
        # Verify the optimal route is valid and all packages can be delivered
        valid_optimal = validate_optimal_route(optimal_route, optimal_path, st.session_state.packages)
        
        if not valid_optimal:
            st.warning("Optimal route calculation encountered challenges. Using best available solution.")
            
            # If validation fails, try the fallback route
            from routing import fallback_route
            optimal_route, optimal_path, optimal_distance = fallback_route(start_location, locations_to_visit, st.session_state.packages)
    except Exception as e:
        st.error(f"Route calculation error: {e}")
        # Create a minimal valid route as fallback
        optimal_route = [{"location": loc, "action": "visit", "package_id": None} for loc in locations_to_visit]
        optimal_path = locations_to_visit
        optimal_distance = 10  # Arbitrary distance as fallback
    
    st.session_state.optimal_route = optimal_route
    st.session_state.optimal_path = optimal_path if optimal_path else ["Warehouse"]
    st.session_state.optimal_distance = optimal_distance if optimal_distance != float('inf') else 0

def process_location_checkin(location):
    """Process a player checking in at a location"""
    if not st.session_state.game_active:
        st.warning("Please start a new game first!")
        return None
        
    if len(st.session_state.current_route) > 0:
        current_location = st.session_state.current_route[-1]
        if is_road_closed(current_location, location):
            st.error(f"❌ Road from {current_location} to {location} is closed! Find another route.")
            return None

    temp_route = st.session_state.current_route + [location]
    if not check_constraints(temp_route):
        if location == "Shop" and "Warehouse" not in st.session_state.current_route:
            st.error("You must visit Warehouse before Shop!")
        elif location == "Home" and "Distribution Center" not in st.session_state.current_route:
            st.error("You must visit Distribution Center before Home!")
        return None
    
    # First update the route - this is critical for visualization
    st.session_state.current_route.append(location)
            
    if st.session_state.current_package and st.session_state.current_package["delivery"] == location:
        package_id = st.session_state.current_package["id"]
        st.session_state.current_package["status"] = "delivered"
        st.session_state.delivered_packages.append(st.session_state.current_package)
        
        # Record this delivery operation using the route_analysis module
        route_analysis.record_delivery(location, package_id)
        
        st.session_state.current_package = None
        st.success(f"📦 Package delivered successfully to {location}!")
        
    available_pickups = [p for p in st.session_state.packages 
                         if p["pickup"] == location and p["status"] == "waiting"]
    if available_pickups and not st.session_state.current_package:
        st.info(f"📦 There are {len(available_pickups)} packages available for pickup at {location}!")
    
    main_locations = list(LOCATIONS.keys())
    all_locations_visited = all(loc in st.session_state.current_route for loc in main_locations)
    all_packages_delivered = len(st.session_state.delivered_packages) == st.session_state.total_packages
    
    if all_locations_visited and all_packages_delivered:
        if st.session_state.current_route[0] != st.session_state.current_route[-1]:
            if not is_road_closed(st.session_state.current_route[-1], st.session_state.current_route[0]):
                st.session_state.current_route.append(st.session_state.current_route[0])
        return end_game()
            
    return True  # Return True to indicate successful check-in

def pickup_package(package):
    """Pick up a package at the current location"""
    if not st.session_state.game_active or not package:
        return
    package["status"] = "picked_up"
    st.session_state.current_package = package
    
    # Record this pickup operation using the route_analysis module
    current_location = st.session_state.current_route[-1] if st.session_state.current_route else None
    route_analysis.record_pickup(current_location, package["id"])
    
    st.success(f"Package #{package['id']} picked up! Deliver to {package['delivery']}.")

def get_game_status():
    """Get current game status including time, progress, etc."""
    if not st.session_state.game_active:
        return None
        
    game_time = time.time() - st.session_state.start_time
    loc_visited = len(set(st.session_state.current_route))
    total_loc = len(LOCATIONS)
    loc_progress = min(100, int((loc_visited / total_loc) * 100))
    pkg_progress = min(100, int((len(st.session_state.delivered_packages) / max(1, st.session_state.total_packages)) * 100))
    combined_progress = (loc_progress + pkg_progress) // 2
    return {
        "time": game_time,
        "location_progress": loc_progress,
        "package_progress": pkg_progress,
        "combined_progress": combined_progress,
        "progress_text": f"Overall Progress: {combined_progress}%"
    }

def end_game():
    """End the game and calculate results with improved efficiency calculation and route validation"""
    if not st.session_state.game_active:
        return None

    game_time = time.time() - st.session_state.start_time

    # Get the optimal distance using the stored path
    optimal_distance = getattr(st.session_state, 'optimal_distance', 0)
    if optimal_distance == 0 and st.session_state.optimal_route:
        _, optimal_distance = calculate_route_distance(st.session_state.optimal_route)
        if optimal_distance == float('inf'):
            optimal_distance = 0  # Fallback if no valid optimal route
    
    # Calculate player's route distance
    player_distance = 0
    for i in range(len(st.session_state.current_route) - 1):
        segment_distance = get_distance(st.session_state.current_route[i], st.session_state.current_route[i+1])
        if segment_distance != float('inf'):
            player_distance += segment_distance

    # Compare player's route to optimal route
    # If player's distance is better (shorter) than the "optimal", update the optimal
    player_found_better_route = False
    if player_distance < optimal_distance and player_distance > 0:
        # Player found a better route than the calculated "optimal"
        st.success("You found a more efficient route than the algorithm! 🎉")
        
        # Update the optimal path and distance for visualization
        st.session_state.optimal_path = st.session_state.current_route.copy()
        st.session_state.optimal_distance = player_distance
        optimal_distance = player_distance
        player_found_better_route = True
        efficiency = 100  # Perfect efficiency
    else:
        # Calculate efficiency normally
        efficiency = min(100, int((optimal_distance / player_distance) * 100)) if player_distance > 0 and optimal_distance > 0 else 0

    weights = SCORING_WEIGHTS["Logistics Challenge"]
    time_factor = max(0, 100 - (game_time / 3))
    constraints_followed = check_constraints(st.session_state.current_route)
    constraint_factor = 100 if constraints_followed else 0
    delivery_percent = min(100, int((len(st.session_state.delivered_packages) / max(1, st.session_state.total_packages)) * 100))
    
    # Calculate score components with possibly improved efficiency
    score_components = {
        "efficiency": efficiency * weights["efficiency"],
        "delivery": delivery_percent * weights["delivery"],
        "constraints": constraint_factor * weights["constraints"],
        "time": time_factor * weights["time"]
    }
    player_score = int(sum(score_components.values()))
    player_score = max(0, min(100, player_score))

    # Calculate optimal score (assuming fastest time and all deliveries)
    optimal_time = optimal_distance * 2  # Arbitrary: 2 seconds per unit distance
    optimal_time_factor = max(0, 100 - (optimal_time / 3))
    optimal_score_components = {
        "efficiency": 100 * weights["efficiency"],
        "delivery": 100 * weights["delivery"],
        "constraints": 100 * weights["constraints"],
        "time": optimal_time_factor * weights["time"]
    }
    optimal_score = int(sum(optimal_score_components.values()))
    optimal_score = max(0, min(100, optimal_score))
    
    # If player found a better route, their score should be the new optimal
    if player_found_better_route:
        optimal_score = player_score
    
    # Calculate improvement percentage more meaningfully
    if player_score > 0:
        if player_found_better_route or player_score >= optimal_score:
            improvement_percent = 0.0  # No improvement needed
        else:
            improvement_percent = ((optimal_score - player_score) / player_score * 100)

    # Ensure optimal_path is consistent between visualization and text description
    if player_found_better_route:
        # Use player's route as the optimal path
        optimal_path = st.session_state.current_route.copy()
    elif hasattr(st.session_state, 'optimal_route') and st.session_state.optimal_route:
        # Extract locations from the action route in the correct order
        optimal_path = []
        seen_locations = set()
        
        for action in st.session_state.optimal_route:
            location = action["location"]
            # Only add each location once to avoid duplicates in the path
            if location not in seen_locations:
                optimal_path.append(location)
                seen_locations.add(location)
    else:
        # Fallback if optimal_route is not available
        optimal_path = st.session_state.optimal_path if hasattr(st.session_state, 'optimal_path') and st.session_state.optimal_path else []
    
    # NEW: Validate that the optimal path doesn't use closed roads
    if hasattr(st.session_state, 'closed_roads') and st.session_state.closed_roads:
        from feature_road_closures import is_road_closed
        from routing import calculate_segment_path
        
        # Process the optimal route to ensure it respects road closures
        valid_optimal_path = []
        for i in range(len(optimal_path)):
            if i == 0:
                valid_optimal_path.append(optimal_path[i])
                continue
                
            prev_loc = optimal_path[i-1]
            curr_loc = optimal_path[i]
            
            # Check if this segment uses a closed road
            if is_road_closed(prev_loc, curr_loc):
                # Find a detour
                segment_path, _ = calculate_segment_path(prev_loc, curr_loc)
                if segment_path and len(segment_path) > 2:
                    # Add intermediate locations in the detour
                    for loc in segment_path[1:-1]:
                        valid_optimal_path.append(loc)
            
            valid_optimal_path.append(curr_loc)
        
        # Use the validated path
        optimal_path = valid_optimal_path
    
    # Store the consistent path for both visualization and text description
    st.session_state.completed_routes = {
        "player": st.session_state.current_route.copy(),
        "optimal": optimal_path
    }

    # Store optimal_route for package operations in text description
    if player_found_better_route:
        # Convert player's route to action route for package operations
        # This is a simplified representation of the player's actual path
        player_action_route = []
        for i, loc in enumerate(st.session_state.current_route):
            player_action_route.append({"location": loc, "action": "visit", "package_id": None})
        st.session_state.completed_optimal_route = player_action_route
    else:
        st.session_state.completed_optimal_route = st.session_state.optimal_route if hasattr(st.session_state, 'optimal_route') else []
    
    if st.session_state.current_player:
        result_data = {
            "time": game_time,
            "efficiency": efficiency,
            "delivery": delivery_percent,
            "constraints": constraint_factor,
            "score": player_score,
            "route": st.session_state.current_route.copy(),
            "found_better_route": player_found_better_route,
            "num_road_closures": len(st.session_state.closed_roads)
        }
        save_player_data(result_data)
    
    # Finalize the route data for analysis
    route_analysis.finalize_route_data()
    
    st.session_state.game_active = False

    results = {
        "time": game_time,
        "efficiency": efficiency,
        "score": player_score,
        "optimal_distance": optimal_distance,
        "player_distance": player_distance,
        "score_components": score_components,
        "delivery_percent": delivery_percent,
        "constraints_followed": constraints_followed,
        "optimal_score": optimal_score,
        "improvement_percent": improvement_percent,
        "found_better_route": player_found_better_route,
        "difficulty": len(st.session_state.closed_roads)
    }
    st.session_state.game_results = results
    return results

def get_completion_summary():
    """Get a summary of completion status for all game aspects"""
    if not st.session_state.game_active:
        return None
        
    main_locations = list(LOCATIONS.keys())
    visited_locations = [loc for loc in main_locations if loc in st.session_state.current_route]
    remaining_locations = [loc for loc in main_locations if loc not in st.session_state.current_route]
    delivered_packages = len(st.session_state.delivered_packages)
    total_packages = st.session_state.total_packages
    remaining_packages = total_packages - delivered_packages
    constraints_followed = check_constraints(st.session_state.current_route)
    constraint_issues = []
    if not constraints_followed:
        if "Factory" in st.session_state.current_route and "Shop" in st.session_state.current_route:
            f_idx = st.session_state.current_route.index("Factory")
            s_idx = st.session_state.current_route.index("Shop")
            if f_idx > s_idx:
                constraint_issues.append("Shop was visited before Factory")
        if "DHL Hub" in st.session_state.current_route and "Residence" in st.session_state.current_route:
            d_idx = st.session_state.current_route.index("DHL Hub")
            r_idx = st.session_state.current_route.index("Residence")
            if d_idx > r_idx:
                constraint_issues.append("Residence was visited before DHL Hub")
    return {
        "visited_locations": visited_locations,
        "remaining_locations": remaining_locations,
        "delivered_packages": delivered_packages,
        "total_packages": total_packages,
        "remaining_packages": remaining_packages,
        "constraints_followed": constraints_followed,
        "constraint_issues": constraint_issues,
        "num_road_closures": len(st.session_state.closed_roads)
    }