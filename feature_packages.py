import streamlit as st
import random
from config import LOCATIONS
from feature_road_closures import is_road_closed

def generate_packages(num_packages=3):
    """Generate random package pickup and delivery locations that don't conflict with constraints"""
    locations = [loc for loc in LOCATIONS.keys()]
    packages = []
    
    # Special package that requires Warehouse → Shop route
    warehouse_to_shop = {
        "id": 1,
        "pickup": "Warehouse",
        "delivery": "Shop",
        "status": "waiting",
        "icon": "📦",
        "description": "Warehouse products for Shop"
    }
    packages.append(warehouse_to_shop)
    
    # Special package that requires Distribution Center → Home route
    distribution_to_home = {
        "id": 2,
        "pickup": "Distribution Center",
        "delivery": "Home",
        "status": "waiting",
        "icon": "📬",
        "description": "Home delivery from Distribution Center"
    }
    packages.append(distribution_to_home)
    
    # Add more random packages if requested
    if num_packages > 2:
        icons = ["🛒", "🎁", "📚", "📱", "🧸", "🧳", "🎮", "💻", "🎵", "🧴"]
        
        # Define valid combinations that don't conflict with constraints
        valid_combinations = [
            ("Warehouse", "Distribution Center"),
            ("Warehouse", "Home"),
            ("Distribution Center", "Warehouse"),
            ("Distribution Center", "Shop"),
            ("Shop", "Distribution Center"),
            ("Shop", "Warehouse"),
            ("Shop", "Home"),
            ("Home", "Warehouse"),
            ("Home", "Shop")
        ]
        
        # Add additional random packages
        for i in range(2, num_packages):
            # Pick a random valid combination
            pickup, delivery = random.choice(valid_combinations)
            
            # Create the package
            packages.append({
                "id": i + 1,
                "pickup": pickup,
                "delivery": delivery,
                "status": "waiting",
                "icon": random.choice(icons),
                "description": f"Package from {pickup} to {delivery}"
            })
    
    return packages

def get_available_packages_at_location(location):
    """Get packages available for pickup at a location"""
    if not st.session_state.packages:
        return []
        
    return [p for p in st.session_state.packages 
            if p["pickup"] == location and p["status"] == "waiting"]
            
def pickup_package_by_id(package_id):
    """Pick up a package by ID (for use in UI)"""
    current_location = st.session_state.current_route[-1] if st.session_state.current_route else None
    if not current_location:
        return False
        
    # If already carrying a package, cannot pick up another
    if st.session_state.current_package:
        st.warning("You are already carrying a package. Deliver it first before picking up another.")
        return False
        
    # Find the package with the given ID
    for pkg in st.session_state.packages:
        if pkg["id"] == package_id and pkg["pickup"] == current_location and pkg["status"] == "waiting":
            # Pick up the package
            pkg["status"] = "picked_up"
            st.session_state.current_package = pkg
            return True
            
    return False

def deliver_package():
    """Deliver the currently held package at the current location"""
    current_location = st.session_state.current_route[-1] if st.session_state.current_route else None
    if not current_location or not st.session_state.current_package:
        return False
        
    # Check if at the correct delivery location
    if st.session_state.current_package["delivery"] == current_location:
        st.session_state.current_package["status"] = "delivered"
        st.session_state.delivered_packages.append(st.session_state.current_package)
        package_id = st.session_state.current_package["id"]
        st.session_state.current_package = None
        return package_id
        
    return False

def get_package_statistics():
    """Get statistics about packages and deliveries"""
    if not st.session_state.packages:
        return None
        
    stats = {
        "total": len(st.session_state.packages),
        "waiting": len([p for p in st.session_state.packages if p["status"] == "waiting"]),
        "picked_up": 1 if st.session_state.current_package else 0,
        "delivered": len(st.session_state.delivered_packages),
    }
    
    stats["completion"] = int((stats["delivered"] / stats["total"]) * 100)
    
    # Count packages by location
    stats["by_location"] = {}
    for loc in LOCATIONS.keys():
        stats["by_location"][loc] = {
            "pickups": len([p for p in st.session_state.packages if p["pickup"] == loc and p["status"] == "waiting"]),
            "deliveries": len([p for p in st.session_state.delivered_packages if p["delivery"] == loc])
        }
        
    # Current package details
    if st.session_state.current_package:
        stats["current_package"] = {
            "id": st.session_state.current_package["id"],
            "pickup": st.session_state.current_package["pickup"],
            "delivery": st.session_state.current_package["delivery"],
            "icon": st.session_state.current_package["icon"]
        }
        
    return stats

def add_random_package():
    """Add a new random package during gameplay that doesn't conflict with constraints"""
    next_id = max([p["id"] for p in st.session_state.packages], default=0) + 1
    
    # Define valid combinations that don't conflict with constraints
    valid_combinations = [
        ("Factory", "DHL Hub"),
        ("Factory", "Residence"),
        ("DHL Hub", "Factory"),
        ("DHL Hub", "Shop"),
        ("Shop", "DHL Hub"),
        ("Shop", "Factory"),
        ("Shop", "Residence"),
        ("Residence", "Factory"),
        ("Residence", "Shop")
    ]
    
    # Pick a random valid combination
    pickup, delivery = random.choice(valid_combinations)
    
    # Random icon
    icons = ["🛒", "🎁", "📚", "📱", "🧸", "🧳", "🎮", "💻", "🎵", "🧴"]
    
    # Create the new package
    new_package = {
        "id": next_id,
        "pickup": pickup,
        "delivery": delivery,
        "status": "waiting",
        "icon": random.choice(icons),
        "description": f"Package from {pickup} to {delivery}"
    }
    
    st.session_state.packages.append(new_package)
    st.session_state.total_packages += 1
    st.info(f"New package #{next_id} ({new_package['icon']}) is available for pickup at {pickup}!")
    return new_package

def get_optimal_delivery_order():
    """Determine the optimal order to deliver all packages based on current position"""
    from routing import calculate_route_distance
    
    # Get list of packages waiting to be picked up
    waiting_packages = [p for p in st.session_state.packages if p["status"] == "waiting"]
    
    if not waiting_packages:
        return []
        
    current_location = st.session_state.current_route[-1] if st.session_state.current_route else "Factory"
    
    # Simple one-package-at-a-time greedy algorithm
    optimal_order = []
    location = current_location
    
    # If currently carrying a package, prioritize delivering it first
    if st.session_state.current_package:
        delivery_loc = st.session_state.current_package["delivery"]
        optimal_order.append({
            "action": "delivery",
            "package_id": st.session_state.current_package["id"],
            "location": delivery_loc
        })
        location = delivery_loc
    
    # Now handle remaining packages one at a time
    while waiting_packages:
        # Find closest pickup
        nearest_pickup = min(waiting_packages, 
                             key=lambda p: calculate_route_distance([location, p["pickup"]])[1])
        
        # Add pickup to optimal order
        optimal_order.append({
            "action": "pickup",
            "package_id": nearest_pickup["id"],
            "location": nearest_pickup["pickup"]
        })
        
        # Update location to pickup location
        location = nearest_pickup["pickup"]
        
        # Add delivery immediately after pickup
        optimal_order.append({
            "action": "delivery",
            "package_id": nearest_pickup["id"],
            "location": nearest_pickup["delivery"]
        })
        
        # Update current location and remove package from waiting list
        location = nearest_pickup["delivery"]
        waiting_packages = [p for p in waiting_packages if p["id"] != nearest_pickup["id"]]
    
    return optimal_order

def get_package_route_impact():
    """Analyze how packages affect the optimal route"""
    # Get all unique locations involved in package pickups and deliveries
    package_locations = set()
    for pkg in st.session_state.packages:
        package_locations.add(pkg["pickup"])
        package_locations.add(pkg["delivery"])
    
    # Check if the two required packages force particular route segments
    impact = {
        "forced_segments": [],
        "package_locations": list(package_locations),
        "critical_packages": []
    }
    
    # Factory to Shop package creates a forced segment
    factory_to_shop = next((p for p in st.session_state.packages 
                           if p["pickup"] == "Factory" and p["delivery"] == "Shop"), None)
    if factory_to_shop:
        impact["forced_segments"].append(("Factory", "Shop"))
        impact["critical_packages"].append(factory_to_shop)
    
    # DHL Hub to Residence package creates a forced segment
    dhl_to_residence = next((p for p in st.session_state.packages 
                            if p["pickup"] == "DHL Hub" and p["delivery"] == "Residence"), None)
    if dhl_to_residence:
        impact["forced_segments"].append(("DHL Hub", "Residence"))
        impact["critical_packages"].append(dhl_to_residence)
    
    return impact

def get_package_hints():
    """Generate helpful hints about package delivery strategy"""
    if not st.session_state.packages:
        return []
        
    hints = []
    
    # Check if player is carrying a package
    if st.session_state.current_package:
        pkg = st.session_state.current_package
        hints.append(f"You're carrying a package to {pkg['delivery']}. Head there next.")
        
        # Check if there's a road closure blocking direct delivery
        current_loc = st.session_state.current_route[-1] if st.session_state.current_route else None
        if current_loc and is_road_closed(current_loc, pkg['delivery']):
            hints.append(f"The direct route to {pkg['delivery']} is closed. Find a detour.")
    else:
        # Suggest picking up specific packages based on location
        current_loc = st.session_state.current_route[-1] if st.session_state.current_route else None
        if current_loc:
            packages_here = get_available_packages_at_location(current_loc)
            if packages_here:
                hints.append(f"There are {len(packages_here)} packages to pick up at your current location.")
            
            # Suggest nearest pickup location
            if not packages_here:
                nearest_pickup = None
                min_distance = float('inf')
                
                for pkg in st.session_state.packages:
                    if pkg["status"] == "waiting":
                        from routing import get_distance
                        dist = get_distance(current_loc, pkg["pickup"])
                        if dist < min_distance:
                            min_distance = dist
                            nearest_pickup = pkg["pickup"]
                
                if nearest_pickup:
                    hints.append(f"The nearest package pickup is at {nearest_pickup}.")
    
    # General strategic advice
    if len(st.session_state.delivered_packages) == 0 and len(st.session_state.packages) > 0:
        hints.append("Focus on delivering the Factory→Shop and DHL Hub→Residence packages first to satisfy constraints.")
    
    # Remind about one-package-at-a-time rule
    hints.append("Remember: You can only carry one package at a time. Deliver current package before picking up another.")
    
    # Road closure advice
    if st.session_state.closed_roads:
        closed_road = st.session_state.closed_roads[0]
        hints.append(f"Plan your route carefully to avoid the closed road between {closed_road[0]} and {closed_road[1]}.")
    
    return hints