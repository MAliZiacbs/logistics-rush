# route_analysis.py
# Module for tracking and analyzing package operations and routes

import streamlit as st
import time

def init_route_tracking():
    """Initialize route tracking in session state"""
    if 'package_operations' not in st.session_state:
        st.session_state.package_operations = []

def record_pickup(location, package_id):
    """Record a package pickup operation"""
    if 'package_operations' not in st.session_state:
        st.session_state.package_operations = []
        
    st.session_state.package_operations.append({
        "location": location,
        "action": "pickup",
        "package_id": package_id,
        "timestamp": time.time()
    })

def record_delivery(location, package_id):
    """Record a package delivery operation"""
    if 'package_operations' not in st.session_state:
        st.session_state.package_operations = []
        
    st.session_state.package_operations.append({
        "location": location,
        "action": "deliver",
        "package_id": package_id,
        "timestamp": time.time()
    })

def finalize_route_data():
    """Prepare route data for end-game analysis"""
    if 'package_operations' in st.session_state:
        st.session_state.completed_package_operations = st.session_state.package_operations.copy()
    
def create_annotated_route(route, package_operations=None):
    """
    Create a route representation with P1, P2, P3 for pickups and D1, D2, D3 for deliveries
    with improved handling to avoid duplicates and ensure correct sequencing
    """
    if not route:
        return "No route available"
        
    # Map to track package operations at each location
    location_ops = {}
    
    # Process package operations if provided
    if package_operations:
        # Sort operations by timestamp to ensure correct order
        sorted_ops = sorted(package_operations, key=lambda x: x.get('timestamp', 0))
        
        # Process operations in order
        for op in sorted_ops:
            location = op.get("location")
            action = op.get("action")
            pkg_id = op.get("package_id")
            
            if location and action in ["pickup", "deliver"] and pkg_id is not None:
                if location not in location_ops:
                    location_ops[location] = []
                
                # Create a unique operation identifier
                prefix = "P" if action == "pickup" else "D"
                op_identifier = f"{prefix}{pkg_id}"
                
                # Only add if this exact operation hasn't been added already at this location
                # for this specific route visit
                if route.count(location) > 1:
                    # For locations visited multiple times, we need to track which visit this is
                    visit_number = sum(1 for r in route[:route.index(location)+1] if r == location)
                    visit_key = f"{location}_{visit_number}"
                    
                    if visit_key not in location_ops:
                        location_ops[visit_key] = []
                    location_ops[visit_key].append(op_identifier)
                else:
                    # For locations visited only once
                    if location not in location_ops:
                        location_ops[location] = []
                    location_ops[location].append(op_identifier)
    
    # Create the annotated route text
    annotated_route = []
    visit_counts = {}
    
    for i, loc in enumerate(route):
        # Track visit number for locations visited multiple times
        if loc not in visit_counts:
            visit_counts[loc] = 0
        visit_counts[loc] += 1
        
        # Check if we have operations for this location
        ops = []
        if loc in location_ops:
            ops = location_ops[loc]
        elif route.count(loc) > 1:
            # For locations visited multiple times
            visit_key = f"{loc}_{visit_counts[loc]}"
            if visit_key in location_ops:
                ops = location_ops[visit_key]
        
        if ops:
            operations = ", ".join(ops)
            annotated_route.append(f"{loc} ({operations})")
        else:
            annotated_route.append(loc)
            
    return " → ".join(annotated_route)

def reconstruct_package_operations(route, packages):
    """
    Reconstruct package operations from a route and package data
    with improved tracking to ensure each package is handled correctly
    """
    operations = []
    carrying_pkg = None
    handled_packages = set()  # Track packages that have been handled
    
    # Track packages ready for pickup or delivery at each location
    location_packages = {}
    for pkg in packages:
        # Create pickup opportunities
        if pkg["pickup"] not in location_packages:
            location_packages[pkg["pickup"]] = {"pickups": [], "deliveries": []}
        location_packages[pkg["pickup"]]["pickups"].append(pkg["id"])
        
        # Create delivery opportunities
        if pkg["delivery"] not in location_packages:
            location_packages[pkg["delivery"]] = {"pickups": [], "deliveries": []}
        location_packages[pkg["delivery"]]["deliveries"].append(pkg["id"])
    
    for i, location in enumerate(route):
        # First check for deliveries if carrying a package
        if carrying_pkg is not None:
            pkg = next((p for p in packages if p["id"] == carrying_pkg), None)
            if pkg and pkg["delivery"] == location:
                operations.append({
                    "location": location,
                    "action": "deliver",
                    "package_id": carrying_pkg,
                    "timestamp": i  # Use index as a proxy for timestamp in reconstruction
                })
                handled_packages.add(carrying_pkg)
                carrying_pkg = None
        
        # Then check for pickups if not carrying anything
        if carrying_pkg is None and location in location_packages:
            for pkg_id in location_packages[location]["pickups"]:
                # Only pick up packages that haven't been handled and will be delivered
                pkg = next((p for p in packages if p["id"] == pkg_id), None)
                if pkg and pkg_id not in handled_packages and pkg["delivery"] in route[i:]:
                    operations.append({
                        "location": location,
                        "action": "pickup",
                        "package_id": pkg_id,
                        "timestamp": i + 0.5  # Use index + 0.5 to order after deliveries
                    })
                    carrying_pkg = pkg_id
                    break
    
    return operations

def get_route_operations(is_player_route=True):
    """Get package operations for a route (player or optimal)"""
    if is_player_route:
        # For player route, use recorded operations if available
        if hasattr(st.session_state, 'completed_package_operations') and st.session_state.completed_package_operations:
            operations = st.session_state.completed_package_operations
            
            # Sort operations by timestamp to ensure correct order
            operations = sorted(operations, key=lambda x: x.get('timestamp', 0))
            
            # Filter for only pickup and delivery actions
            operations = [op for op in operations if op["action"] in ["pickup", "deliver"]]
            return operations
    
    # For optimal route or if no recorded operations exist
    if "completed_routes" in st.session_state:
        route = st.session_state.completed_routes.get("player" if is_player_route else "optimal", [])
        
        # If we're getting the optimal route and we have completed_optimal_route actions, use those
        if not is_player_route and hasattr(st.session_state, 'completed_optimal_route') and st.session_state.completed_optimal_route:
            # Extract operations from the completed optimal route
            operations = []
            for action in st.session_state.completed_optimal_route:
                if action["action"] in ["pickup", "deliver"] and action["package_id"] is not None:
                    operations.append({
                        "location": action["location"],
                        "action": action["action"],
                        "package_id": action["package_id"],
                        "timestamp": 0  # Dummy timestamp for ordering
                    })
            
            # If we found operations, return them
            if operations:
                return operations
        
        # Otherwise reconstruct operations from route and packages
        packages = st.session_state.packages + st.session_state.delivered_packages if hasattr(st.session_state, 'delivered_packages') else st.session_state.packages
        
        if route:
            return reconstruct_package_operations(route, packages)
    
    return []