import streamlit as st
import random
from config import LOCATIONS

def generate_packages(num_packages=3):
    """Generate random package pickup and delivery locations"""
    locations = [loc for loc in LOCATIONS.keys() if loc != "Central Hub"]
    packages = []
    
    for i in range(num_packages):
        pickup = random.choice(locations)
        # Make sure delivery location is different from pickup
        delivery_options = [loc for loc in locations if loc != pickup]
        delivery = random.choice(delivery_options)
        
        packages.append({
            "id": i + 1,
            "pickup": pickup,
            "delivery": delivery,
            "status": "waiting",  # waiting, picked_up, delivered
            "icon": random.choice(["📦", "📱", "🛒", "🎁", "📚"])
        })
    
    return packages

def get_available_packages_at_location(location):
    """Get packages available for pickup at a location"""
    if not st.session_state.packages:
        return []
        
    return [p for p in st.session_state.packages 
            if p["pickup"] == location and p["status"] == "waiting"]
            
def pickup_package(package_id):
    """Pick up a package by ID (for use in UI)"""
    current_location = st.session_state.current_route[-1] if st.session_state.current_route else None
    if not current_location:
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
    for loc in [l for l in LOCATIONS.keys() if l != "Central Hub"]:
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
    """Add a new random package during gameplay"""
    next_id = max([p["id"] for p in st.session_state.packages], default=0) + 1
    locations = [loc for loc in LOCATIONS.keys() if loc != "Central Hub"]
    
    pickup = random.choice(locations)
    delivery_options = [loc for loc in locations if loc != pickup]
    delivery = random.choice(delivery_options)
    
    new_package = {
        "id": next_id,
        "pickup": pickup,
        "delivery": delivery,
        "status": "waiting",
        "icon": random.choice(["📦", "📱", "🛒", "🎁", "📚"])
    }
    
    st.session_state.packages.append(new_package)
    st.session_state.total_packages += 1
    st.info(f"New package #{next_id} is available for pickup at {pickup}!")
    return new_package

def get_optimal_delivery_order():
    """Determine the optimal order to deliver all packages"""
    from routing import calculate_route_distance
    
    # Get list of packages waiting to be picked up
    waiting_packages = [p for p in st.session_state.packages if p["status"] == "waiting"]
    
    if not waiting_packages:
        return []
        
    current_location = st.session_state.current_route[-1] if st.session_state.current_route else "Central Hub"
    
    # Simple greedy algorithm: pick up closest package, deliver it, repeat
    optimal_order = []
    location = current_location
    
    while waiting_packages:
        # Find closest pickup
        nearest_pickup = min(waiting_packages, 
                             key=lambda p: calculate_route_distance([location, p["pickup"]]))
        
        # Add to optimal order
        optimal_order.append({
            "action": "pickup",
            "package_id": nearest_pickup["id"],
            "location": nearest_pickup["pickup"]
        })
        
        # Add delivery to optimal order
        optimal_order.append({
            "action": "delivery",
            "package_id": nearest_pickup["id"],
            "location": nearest_pickup["delivery"]
        })
        
        # Update current location and remove package from waiting list
        location = nearest_pickup["delivery"]
        waiting_packages = [p for p in waiting_packages if p["id"] != nearest_pickup["id"]]
    
    return optimal_order