# feature_packages.py

import streamlit as st
import random
from config import LOCATIONS
from feature_road_closures import is_road_closed
import diagnostics

def generate_packages(num_packages=3):
    packages = []
    warehouse_to_shop = {
        "id": 1,
        "pickup": "Warehouse",
        "delivery": "Shop",
        "status": "waiting",
        "icon": "📦",
        "description": "Warehouse products for Shop"
    }
    packages.append(warehouse_to_shop)
    distribution_to_home = {
        "id": 2,
        "pickup": "Distribution Center",
        "delivery": "Home",
        "status": "waiting",
        "icon": "📬",
        "description": "Home delivery from Distribution Center"
    }
    packages.append(distribution_to_home)
    if num_packages > 2:
        icons = ["🛒", "🎁", "📚", "📱", "🧸", "🧳", "🎮", "💻", "🎵", "🧴"]
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
        for i in range(2, num_packages):
            pickup, delivery = random.choice(valid_combinations)
            packages.append({
                "id": i + 1,
                "pickup": pickup,
                "delivery": delivery,
                "status": "waiting",
                "icon": random.choice(icons),
                "description": f"Package from {pickup} to {delivery}"
            })
    diagnostics.log_event("Packages Generated", f"Created {len(packages)} packages")
    return packages

def get_available_packages_at_location(location):
    if not st.session_state.packages:
        return []
    return [p for p in st.session_state.packages if p["pickup"] == location and p["status"] == "waiting"]

def pickup_package_by_id(package_id):
    current_location = st.session_state.current_route[-1] if st.session_state.current_route else None
    if not current_location:
        diagnostics.log_error("Package Pickup", "No current location for pickup")
        return False
    if st.session_state.current_package:
        st.warning("You are already carrying a package. Deliver it first before picking up another.")
        diagnostics.log_error("Package Pickup", "Attempted to pick up while carrying another package")
        return False
    for pkg in st.session_state.packages:
        if pkg["id"] == package_id and pkg["pickup"] == current_location and pkg["status"] == "waiting":
            pkg["status"] = "picked_up"
            st.session_state.current_package = pkg
            diagnostics.log_package_operation("pickup", current_location, package_id)
            return True
    diagnostics.log_error("Package Pickup", f"Package {package_id} not found or not available at {current_location}")
    return False

def deliver_package():
    current_location = st.session_state.current_route[-1] if st.session_state.current_route else None
    if not current_location or not st.session_state.current_package:
        diagnostics.log_error("Package Delivery", "No current location or no package to deliver")
        return False
    if st.session_state.current_package["delivery"] == current_location:
        st.session_state.current_package["status"] = "delivered"
        st.session_state.delivered_packages.append(st.session_state.current_package)
        package_id = st.session_state.current_package["id"]
        diagnostics.log_package_operation("delivery", current_location, package_id)
        st.session_state.current_package = None
        return package_id
    diagnostics.log_error("Package Delivery", f"Wrong delivery location: expected {st.session_state.current_package['delivery']}, got {current_location}")
    return False

def get_package_statistics():
    if not st.session_state.packages:
        return None
    stats = {
        "total": len(st.session_state.packages),
        "waiting": len([p for p in st.session_state.packages if p["status"] == "waiting"]),
        "picked_up": 1 if st.session_state.current_package else 0,
        "delivered": len(st.session_state.delivered_packages),
    }
    stats["completion"] = int((stats["delivered"] / stats["total"]) * 100)
    stats["by_location"] = {}
    for loc in LOCATIONS.keys():
        stats["by_location"][loc] = {
            "pickups": len([p for p in st.session_state.packages if p["pickup"] == loc and p["status"] == "waiting"]),
            "deliveries": len([p for p in st.session_state.delivered_packages if p["delivery"] == loc])
        }
    if st.session_state.current_package:
        stats["current_package"] = {
            "id": st.session_state.current_package["id"],
            "pickup": st.session_state.current_package["pickup"],
            "delivery": st.session_state.current_package["delivery"],
            "icon": st.session_state.current_package["icon"]
        }
    return stats

def add_random_package():
    next_id = max([p["id"] for p in st.session_state.packages], default=0) + 1
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
    pickup, delivery = random.choice(valid_combinations)
    icons = ["🛒", "🎁", "📚", "📱", "🧸", "🧳", "🎮", "💻", "🎵", "🧴"]
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
    diagnostics.log_event("Random Package Added", f"Added package #{next_id} from {pickup} to {delivery}")
    st.info(f"New package #{next_id} ({new_package['icon']}) is available for pickup at {pickup}!")
    return new_package

def get_optimal_delivery_order():
    from routing import calculate_route_distance
    waiting_packages = [p for p in st.session_state.packages if p["status"] == "waiting"]
    if not waiting_packages:
        return []
    current_location = st.session_state.current_route[-1] if st.session_state.current_route else "Warehouse"
    optimal_order = []
    location = current_location
    if st.session_state.current_package:
        delivery_loc = st.session_state.current_package["delivery"]
        optimal_order.append({"action": "delivery", "package_id": st.session_state.current_package["id"], "location": delivery_loc})
        location = delivery_loc
    while waiting_packages:
        nearest_pickup = min(waiting_packages, key=lambda p: calculate_route_distance([location, p["pickup"]])[1])
        optimal_order.append({"action": "pickup", "package_id": nearest_pickup["id"], "location": nearest_pickup["pickup"]})
        location = nearest_pickup["pickup"]
        optimal_order.append({"action": "delivery", "package_id": nearest_pickup["id"], "location": nearest_pickup["delivery"]})
        location = nearest_pickup["delivery"]
        waiting_packages = [p for p in waiting_packages if p["id"] != nearest_pickup["id"]]
    return optimal_order

def get_package_route_impact():
    package_locations = set()
    for pkg in st.session_state.packages:
        package_locations.add(pkg["pickup"])
        package_locations.add(pkg["delivery"])
    impact = {
        "forced_segments": [],
        "package_locations": list(package_locations),
        "critical_packages": []
    }
    warehouse_to_shop = next((p for p in st.session_state.packages if p["pickup"] == "Warehouse" and p["delivery"] == "Shop"), None)
    if warehouse_to_shop:
        impact["forced_segments"].append(("Warehouse", "Shop"))
        impact["critical_packages"].append(warehouse_to_shop)
    distribution_to_home = next((p for p in st.session_state.packages if p["pickup"] == "Distribution Center" and p["delivery"] == "Home"), None)
    if distribution_to_home:
        impact["forced_segments"].append(("Distribution Center", "Home"))
        impact["critical_packages"].append(distribution_to_home)
    return impact

def get_package_hints():
    if not st.session_state.packages:
        return []
    hints = []
    if st.session_state.current_package:
        pkg = st.session_state.current_package
        hints.append(f"You're carrying a package to {pkg['delivery']}. Head there next.")
        current_loc = st.session_state.current_route[-1] if st.session_state.current_route else None
        if current_loc and is_road_closed(current_loc, pkg['delivery']):
            hints.append(f"The direct route to {pkg['delivery']} is closed. Find a detour.")
    else:
        current_loc = st.session_state.current_route[-1] if st.session_state.current_route else None
        if current_loc:
            packages_here = get_available_packages_at_location(current_loc)
            if packages_here:
                hints.append(f"There are {len(packages_here)} packages to pick up at your current location.")
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
    if len(st.session_state.delivered_packages) == 0 and len(st.session_state.packages) > 0:
        hints.append("Focus on delivering the Warehouse→Shop and Distribution Center→Home packages first to satisfy constraints.")
    hints.append("Remember: You can only carry one package at a time. Deliver current package before picking up another.")
    if st.session_state.closed_roads:
        closed_road = st.session_state.closed_roads[0]
        hints.append(f"Plan your route carefully to avoid the closed road between {closed_road[0]} and {closed_road[1]}.")
    return hints
