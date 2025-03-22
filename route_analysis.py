# route_analysis.py

import streamlit as st
import time

def init_route_tracking():
    if 'package_operations' not in st.session_state:
        st.session_state.package_operations = []

def record_pickup(location, package_id):
    if 'package_operations' not in st.session_state:
        st.session_state.package_operations = []
    st.session_state.package_operations.append({
        "location": location,
        "action": "pickup",
        "package_id": package_id,
        "timestamp": time.time()
    })

def record_delivery(location, package_id):
    if 'package_operations' not in st.session_state:
        st.session_state.package_operations = []
    st.session_state.package_operations.append({
        "location": location,
        "action": "delivery",
        "package_id": package_id,
        "timestamp": time.time()
    })

def finalize_route_data():
    if 'package_operations' in st.session_state:
        st.session_state.completed_package_operations = st.session_state.package_operations.copy()

def create_annotated_route(route, package_operations=None):
    if not route:
        return "No route available"
    location_ops = {}
    if package_operations:
        sorted_ops = sorted(package_operations, key=lambda x: x.get('timestamp', 0))
        for op in sorted_ops:
            location = op.get("location")
            action = op.get("action")
            pkg_id = op.get("package_id")
            if location and action in ["pickup", "deliver"] and pkg_id is not None:
                if location not in location_ops:
                    location_ops[location] = []
                prefix = "P" if action == "pickup" else "D"
                op_identifier = f"{prefix}{pkg_id}"
                location_ops[location].append(op_identifier)
    annotated_route = []
    for loc in route:
        ops = location_ops.get(loc, [])
        if ops:
            annotated_route.append(f"{loc} ({', '.join(ops)})")
        else:
            annotated_route.append(loc)
    return " → ".join(annotated_route)

def reconstruct_package_operations(route, packages):
    operations = []
    carrying_pkg = None
    handled_packages = set()
    location_packages = {}
    for pkg in packages:
        if pkg["pickup"] not in location_packages:
            location_packages[pkg["pickup"]] = {"pickups": [], "deliveries": []}
        location_packages[pkg["pickup"]]["pickups"].append(pkg["id"])
        if pkg["delivery"] not in location_packages:
            location_packages[pkg["delivery"]] = {"pickups": [], "deliveries": []}
        location_packages[pkg["delivery"]]["deliveries"].append(pkg["id"])
    for i, location in enumerate(route):
        if carrying_pkg is not None:
            pkg = next((p for p in packages if p["id"] == carrying_pkg), None)
            if pkg and pkg["delivery"] == location:
                operations.append({
                    "location": location,
                    "action": "deliver",
                    "package_id": carrying_pkg,
                    "timestamp": i
                })
                handled_packages.add(carrying_pkg)
                carrying_pkg = None
        if carrying_pkg is None:
            if location in location_packages and location_packages[location]["pickups"]:
                pkg_id = location_packages[location]["pickups"][0]
                operations.append({
                    "location": location,
                    "action": "pickup",
                    "package_id": pkg_id,
                    "timestamp": i
                })
                carrying_pkg = pkg_id
    return operations
