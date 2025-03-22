# visualization_renders.py

import streamlit as st
from config import LOCATIONS
from routing import get_distance
from feature_packages import get_available_packages_at_location
from game_engine import process_location_checkin, deliver_package
import route_analysis

def render_action_controls():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Check In")
    col1, col2 = st.columns(2)
    with col1:
        for loc in ["Warehouse", "Shop"]:
            disabled = (loc == "Shop" and "Warehouse" not in st.session_state.current_route)
            if st.button(f"{LOCATIONS[loc]['emoji']} {loc}", key=f"btn_{loc}", disabled=disabled):
                if process_location_checkin(loc):
                    st.experimental_rerun()
    with col2:
        for loc in ["Distribution Center", "Home"]:
            disabled = (loc == "Home" and "Distribution Center" not in st.session_state.current_route)
            if st.button(f"{LOCATIONS[loc]['emoji']} {loc}", key=f"btn_{loc}", disabled=disabled):
                if process_location_checkin(loc):
                    st.experimental_rerun()
    current_route = st.session_state.current_route
    if current_route:
        current_loc = current_route[-1]
        pickups = get_available_packages_at_location(current_loc)
        if pickups and not st.session_state.current_package:
            st.markdown("### Pickup Package")
            for pkg in pickups:
                if st.button(f"{pkg['icon']} Package #{pkg['id']} to {pkg['delivery']}", key=f"pickup_{pkg['id']}"):
                    from feature_packages import pickup_package_by_id
                    if pickup_package_by_id(pkg['id']):
                        st.experimental_rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def render_game_info():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if st.session_state.game_active:
        st.info("Game in progress...")
        st.markdown("**Current Route:** " + " → ".join(st.session_state.current_route))
    else:
        st.info("Game not active")
    st.markdown('</div>', unsafe_allow_html=True)

def render_game_results():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if st.session_state.game_results:
        results = st.session_state.game_results
        st.subheader("Challenge Complete!")
        st.metric("Score", results.get("score", 0))
        st.metric("Time", f"{results.get('time', 0):.1f}s")
        st.metric("Your Distance", f"{results.get('player_distance', 0):.1f} cm")
        st.metric("Optimal Distance", f"{results.get('optimal_distance', 0):.1f} cm")
    st.markdown('</div>', unsafe_allow_html=True)
