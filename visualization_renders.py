import streamlit as st

from config import LOCATIONS
from routing import suggest_next_location
from feature_packages import get_available_packages_at_location, get_package_hints
from game_engine import process_location_checkin, pickup_package, get_game_status

def render_action_controls():
    """Render only the Check In and Pickup Package sections below the map"""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Check In")
    col1, col2 = st.columns(2)
    with col1:
        for loc in ["Factory", "Shop"]:
            disabled = (loc == "Shop" and "Factory" not in st.session_state.current_route)
            btn_type = "primary" if st.session_state.current_route and suggest_next_location(st.session_state.current_route[-1], st.session_state.current_route, st.session_state.packages)[0] == loc else "secondary"
            if st.button(f"{LOCATIONS[loc]['emoji']} {loc}", key=f"btn_{loc}", disabled=disabled, type=btn_type, use_container_width=True):
                if process_location_checkin(loc):
                    # Force a rerun to update the map with the new state
                    st.rerun()
    with col2:
        for loc in ["DHL Hub", "Residence"]:
            disabled = (loc == "Residence" and "DHL Hub" not in st.session_state.current_route)
            btn_type = "primary" if st.session_state.current_route and suggest_next_location(st.session_state.current_route[-1], st.session_state.current_route, st.session_state.packages)[0] == loc else "secondary"
            if st.button(f"{LOCATIONS[loc]['emoji']} {loc}", key=f"btn_{loc}", disabled=disabled, type=btn_type, use_container_width=True):
                if process_location_checkin(loc):
                    # Force a rerun to update the map with the new state
                    st.rerun()
    if st.session_state.current_route:
        current_loc = st.session_state.current_route[-1]
        pickups = get_available_packages_at_location(current_loc)
        if pickups and not st.session_state.current_package:
            st.markdown("### Pickup Package")
            for pkg in pickups:
                if st.button(f"{pkg['icon']} Package #{pkg['id']} to {pkg['delivery']}", key=f"pickup_{pkg['id']}", type="primary", use_container_width=True):
                    pickup_package(pkg)
                    # Force a rerun to update the UI
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def render_game_info():
    """Render game status and supplementary info on the right"""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    game_status = get_game_status()
    if game_status:
        st.markdown('<div class="status-bar">', unsafe_allow_html=True)
        st.markdown(f"⏱ **Time:** {game_status['time']:.1f}s | 📦 **Packages:** {len(st.session_state.delivered_packages)}/{st.session_state.total_packages} | 🌐 **Progress:** {game_status['combined_progress']}%")
        st.markdown('</div>', unsafe_allow_html=True)
    with st.expander("Game Info", expanded=True):
        if hasattr(st.session_state, 'closed_roads') and st.session_state.closed_roads:
            st.markdown('<div class="road-closure-alert">⛔️ Road Closure:</div>', unsafe_allow_html=True)
            closures_text = ", ".join([f"{road[0]} ↔️ {road[1]}" for road in st.session_state.closed_roads])
            st.markdown(closures_text)
        st.markdown('<div class="package-info">', unsafe_allow_html=True)
        if st.session_state.current_package:
            pkg = st.session_state.current_package
            st.markdown(f"🚚 **Carrying:** {pkg['icon']} Package #{pkg['id']} to {pkg['delivery']}")
        else:
            st.markdown("🚚 **Carrying:** No package")
        st.markdown(f"📦 **Delivered:** {len(st.session_state.delivered_packages)}/{st.session_state.total_packages}")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="constraints-info">', unsafe_allow_html=True)
        st.markdown("🔄 **Constraints:**")
        st.markdown("• Factory → Shop")
        st.markdown("• DHL Hub → Residence")
        st.markdown("• One package at a time")
        # Add difficulty info
        if hasattr(st.session_state, 'closed_roads'):
            num_closures = len(st.session_state.closed_roads)
            displayed_difficulty = st.session_state.get('displayed_difficulty', 
                                "Easy" if num_closures == 1 else "Medium" if num_closures == 2 else "Hard")
            st.markdown(f"• **Difficulty:** {displayed_difficulty} ({num_closures} closure{'s' if num_closures > 1 else ''})")
            
        st.markdown('</div>', unsafe_allow_html=True)
    if st.session_state.current_route:
        current_loc = st.session_state.current_route[-1]
        next_loc, reason = suggest_next_location(current_loc, st.session_state.current_route, st.session_state.packages)
        st.info(f"Next Suggested Move: {LOCATIONS[next_loc]['emoji']} {next_loc} ({reason})")
    hints = get_package_hints()
    if hints:
        with st.expander("Hints"):
            for hint in hints:
                st.markdown(f"• {hint}")
    if st.session_state.current_route:
        st.markdown("### Your Route")
        st.code(" → ".join(st.session_state.current_route))
    st.markdown('</div>', unsafe_allow_html=True)

def render_game_results():
    """Render the game results UI with improved information display"""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Challenge Complete!")
    results = st.session_state.game_results

    st.markdown(f"""
    <div style="text-align:center;margin-bottom:20px">
        <div style="font-size:3rem;font-weight:bold;color:#1a56db">{results['score']}</div>
        <div style="font-size:1rem;color:#6b7280">SCORE</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Time", f"{results['time']:.1f}s")
        st.metric("Your Distance", f"{results['player_distance']:.1f}")
    with c2:
        st.metric("Efficiency", f"{results['efficiency']}%")
        st.metric("Optimal Distance", f"{results['optimal_distance']:.1f}")

    # Display a special message if player found a better route
    if results.get('found_better_route', False):
        st.success("🏆 Congratulations! You found a more efficient route than the algorithm calculated. Your route is now considered the optimal solution!")

    st.markdown('<div class="score-breakdown">', unsafe_allow_html=True)
    st.markdown("### Score Breakdown")
    components = results['score_components']
    col_score1, col_score2 = st.columns(2)
    with col_score1:
        st.metric("Efficiency Score", f"{components['efficiency']:.1f}")
        st.metric("Delivery Score", f"{components['delivery']:.1f}")
    with col_score2:
        st.metric("Constraint Score", f"{components['constraints']:.1f}")
        st.metric("Time Score", f"{components['time']:.1f}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("### Challenge Results")
    st.metric("Optimal Score", f"{results['optimal_score']}")
    # Show difficulty level based on number of road closures
    if 'difficulty' in results:
        num_closures = results['difficulty']
        displayed_difficulty = st.session_state.get('displayed_difficulty', 
                             "Easy" if num_closures == 1 else "Medium" if num_closures == 2 else "Hard")
        st.markdown(f"**Difficulty Level:** {displayed_difficulty} ({num_closures} road closure{'s' if num_closures > 1 else ''})")
    # Show improvement percentage differently if player found the optimal route
    improvement = results['improvement_percent']
    if results.get('found_better_route', False) or improvement <= 0:
        st.markdown("<div style='color:#10B981'>You achieved the optimal route! 🌟</div>", unsafe_allow_html=True)
    else:
        color = "#EF4444"
        st.markdown(f"<div style='color:{color}'>Optimal Route Improvement: {improvement:.1f}%</div>", unsafe_allow_html=True)

    if st.session_state.delivered_packages:
        st.markdown(f"**Packages Delivered:** {len(st.session_state.delivered_packages)}/{st.session_state.total_packages}")
        for i, pkg in enumerate(st.session_state.delivered_packages):
            st.markdown(f"✅ {pkg['icon']} Package #{pkg['id']}: {pkg['pickup']} → {pkg['delivery']}")
    else:
        st.markdown("**No packages delivered**")
    
    constraints_followed = results.get('constraints_followed', False)
    st.markdown(f"**Sequence Constraints:** {'✅ Met' if constraints_followed else '❌ Not Met'}")
    
    if st.session_state.closed_roads:
        st.markdown("**Road Closure Navigated:**")
        for road in st.session_state.closed_roads:
            st.markdown(f"⛔️ {road[0]} ↔️ {road[1]}")

    st.markdown("### Route Analysis")
    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**Your Route:**")
        route_text = " → ".join(st.session_state.completed_routes["player"])
        st.code(route_text)
    with cc2:
        title = "**Optimal Route:**" if not results.get('found_better_route', False) else "**Optimal Route (Your Solution!):**"
        st.markdown(title)
        if "completed_routes" in st.session_state and "optimal" in st.session_state.completed_routes:
            optimal_path = st.session_state.completed_routes["optimal"]
            if optimal_path and len(optimal_path) > 1:
                # First create the basic location route text 
                route_text = " → ".join(optimal_path)
                
                # Get all packages
                all_packages = st.session_state.packages

                # Create an enhanced version with package operations
                if hasattr(st.session_state, 'completed_optimal_route') and st.session_state.completed_optimal_route:
                    optimal_actions = st.session_state.completed_optimal_route
                    
                    # If player found better route, show their route with simplified package operations
                    if results.get('found_better_route', False):
                        st.code(route_text)
                        st.markdown("**Note:** Your route was more efficient! The game now recognizes your solution as optimal.")
                    else:
                        # Create a map of location to actions
                        location_actions = {}
                        for action in optimal_actions:
                            loc = action["location"]
                            act_type = action["action"]
                            pkg_id = action["package_id"]
                            
                            if loc not in location_actions:
                                location_actions[loc] = []
                            
                            if act_type in ["pickup", "deliver"] and pkg_id is not None:
                                location_actions[loc].append((act_type, pkg_id))
                        
                        # Create enhanced labels for each location (keeping one package at a time limitation)
                        action_labels = []
                        current_package = None
                        for loc in optimal_path:
                            if loc in location_actions and location_actions[loc]:
                                # Add actions to the location label
                                actions = []
                                for act_type, pkg_id in location_actions[loc]:
                                    if act_type == "pickup" and current_package is None:
                                        action_code = "P"
                                        current_package = pkg_id
                                        actions.append(f"{action_code}{pkg_id}")
                                    elif act_type == "deliver" and current_package == pkg_id:
                                        action_code = "D"
                                        current_package = None
                                        actions.append(f"{action_code}{pkg_id}")
                                
                                # Format the location with actions
                                if actions:
                                    label = f"{loc} ({', '.join(actions)})"
                                else:
                                    label = loc
                            else:
                                label = loc
                            
                            action_labels.append(label)
                        
                        # If we successfully created the enhanced labels, use them
                        if action_labels:
                            route_text = " → ".join(action_labels)
                            st.code(route_text)
                        else:
                            st.code(route_text)

                # Verify all packages are represented in one-package-at-a-time mode
                if not results.get('found_better_route', False):
                    package_operations = []
                    for pkg in all_packages:
                        pickup_found = False
                        delivery_found = False
                        
                        # Check if route_text contains all package operations
                        for i in range(len(optimal_actions)):
                            action = optimal_actions[i]
                            if action["package_id"] == pkg["id"]:
                                if action["action"] == "pickup":
                                    pickup_found = True
                                elif action["action"] == "deliver":
                                    delivery_found = True
                        
                        package_operations.append((pkg["id"], pickup_found, delivery_found))
                    
                    # If any packages are missing operations, add debug info
                    missing_operations = [pkg_id for pkg_id, pickup, delivery in package_operations if not (pickup and delivery)]
                    if missing_operations and not st.session_state.get("debug_shown", False):
                        st.warning(f"Note: The optimal route handles all packages one at a time while accounting for road closures.")
                        st.session_state.debug_shown = True
            else:
                st.markdown("*No optimal route available due to road closure constraints.*")
        else:
            st.markdown("*No optimal route information available.*")

    # Add information about route constraints and rules
    with st.expander("Route Planning Logic"):
        st.markdown("""
        **Game Rules & Constraints:**
        
        1. **One package at a time:** Both you and the AI can only carry one package at a time.
        2. **Road closures:** The optimal route accounts for road closures.
        3. **Location constraints:** Factory must be visited before Shop, and DHL Hub before Residence.
        4. **Efficiency:** Route with the shortest total distance while satisfying all constraints.
        
        **Legend:**
        - P1 = Pickup Package #1
        - D1 = Deliver Package #1
        """)
        
        if results.get('found_better_route', False):
            st.success("Your solution outperformed the AI's calculated optimal route!")

    if st.button("Play Again", use_container_width=True):
        st.session_state.game_results = None
        st.session_state.debug_shown = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)