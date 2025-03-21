import streamlit as st

from config import LOCATIONS
from routing import suggest_next_location, get_distance
from feature_packages import get_available_packages_at_location, get_package_hints
from game_engine import process_location_checkin, pickup_package, get_game_status
import route_analysis

def render_action_controls():
    """Render only the Check In and Pickup Package sections below the map"""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Check In")
    col1, col2 = st.columns(2)
    with col1:
        for loc in ["Warehouse", "Shop"]:
            disabled = (loc == "Shop" and "Warehouse" not in st.session_state.current_route)
            btn_type = "primary" if st.session_state.current_route and suggest_next_location(st.session_state.current_route[-1], st.session_state.current_route, st.session_state.packages)[0] == loc else "secondary"
            if st.button(f"{LOCATIONS[loc]['emoji']} {loc}", key=f"btn_{loc}", disabled=disabled, type=btn_type, use_container_width=True):
                if process_location_checkin(loc):
                    # Force a rerun to update the map with the new state
                    st.rerun()
    with col2:
        for loc in ["Distribution Center", "Home"]:
            disabled = (loc == "Home" and "Distribution Center" not in st.session_state.current_route)
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
        st.markdown("• Warehouse → Shop")
        st.markdown("• Distribution Center → Home")
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
        st.metric("Your Distance", f"{results['player_distance']:.1f} cm")
    with c2:
        st.metric("Efficiency", f"{results['efficiency']}%")
        st.metric("Optimal Distance", f"{results['optimal_distance']:.1f} cm")

    # Display a special message if player found a better route
    if results.get('found_better_route', False):
        st.success("🏆 Congratulations! You found a more efficient route than the algorithm calculated. Your route is now considered the optimal solution!")

    # Add expected time based on real distances
    expected_time = results.get('expected_time', 0)
    if expected_time > 0:
        time_ratio = results['time'] / expected_time
        time_message = f"Estimated time for this route: {expected_time:.1f}s"
        if time_ratio < 0.8:
            time_message += f" (You were {(1-time_ratio)*100:.0f}% faster than expected! 🚀)"
        elif time_ratio > 1.2:
            time_message += f" (You took {(time_ratio-1)*100:.0f}% longer than expected)"
        st.info(time_message)

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

    # Display distance table with real measurements, handling infinity values
    st.markdown("### Distance Table (cm)")
    
    distance_data = []
    for loc1 in LOCATIONS:
        row = {"From": loc1}
        for loc2 in LOCATIONS:
            if loc1 != loc2:
                distance = get_distance(loc1, loc2)
                if distance == float('inf'):
                    row[loc2] = "∞"  # Use infinity symbol for closed routes
                else:
                    row[loc2] = f"{int(distance)} cm"
        distance_data.append(row)
    
    # Convert to DataFrame and display
    import pandas as pd
    distance_df = pd.DataFrame(distance_data)
    st.dataframe(distance_df, use_container_width=True)

    st.markdown("### Route Analysis")
    
    cc1, cc2 = st.columns(2)
    
    with cc1:
        st.markdown("**Your Route:**")
        if "completed_routes" in st.session_state and "player" in st.session_state.completed_routes:
            player_route = st.session_state.completed_routes["player"]
            
            # Get player package operations using the new module
            player_package_ops = route_analysis.get_route_operations(is_player_route=True)
            
            # Create and display player route with package operations
            route_text = route_analysis.create_annotated_route(player_route, player_package_ops)
            st.code(route_text)
            
            # Calculate and display the total distance
            if len(player_route) > 1:
                total_distance = 0
                for i in range(len(player_route) - 1):
                    segment_distance = get_distance(player_route[i], player_route[i+1])
                    if segment_distance != float('inf'):
                        total_distance += segment_distance
                st.markdown(f"**Total Distance:** {total_distance:.1f} cm")
        else:
            st.code("No route data available")
            
    with cc2:
        title = "**Optimal Route:**" if not results.get('found_better_route', False) else "**Optimal Route (Your Solution!):**"
        st.markdown(title)
        if "completed_routes" in st.session_state and "optimal" in st.session_state.completed_routes:
            optimal_path = st.session_state.completed_routes["optimal"]
            
            if optimal_path and len(optimal_path) > 1:
                # Get optimal route operations using the new module
                optimal_package_ops = route_analysis.get_route_operations(is_player_route=False)
                
                # Create and display optimal route with package operations
                route_text = route_analysis.create_annotated_route(optimal_path, optimal_package_ops)
                
                # If player found better route, show their route
                if results.get('found_better_route', False):
                    st.code(route_analysis.create_annotated_route(player_route, player_package_ops))
                    st.markdown("**Note:** Your route was more efficient! The game now recognizes your solution as optimal.")
                    # Calculate and display the total distance
                    if len(player_route) > 1:
                        total_distance = 0
                        for i in range(len(player_route) - 1):
                            segment_distance = get_distance(player_route[i], player_route[i+1])
                            if segment_distance != float('inf'):
                                total_distance += segment_distance
                        st.markdown(f"**Total Distance:** {total_distance:.1f} cm")
                else:
                    st.code(route_text)
                    # Calculate and display the total distance
                    if len(optimal_path) > 1:
                        total_distance = 0
                        for i in range(len(optimal_path) - 1):
                            segment_distance = get_distance(optimal_path[i], optimal_path[i+1])
                            if segment_distance != float('inf'):
                                total_distance += segment_distance
                        st.markdown(f"**Total Distance:** {total_distance:.1f} cm")
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
        3. **Location constraints:** Warehouse must be visited before Shop, and Distribution Center before Home.
        4. **Efficiency:** Route with the shortest total distance while satisfying all constraints.
        5. **Real distances:** This game uses real physical distances measured in centimeters.
        
        **Legend:**
        - P1 = Pickup Package #1
        - D1 = Deliver Package #1
        - P2 = Pickup Package #2
        - D2 = Deliver Package #2
        - P3 = Pickup Package #3
        - D3 = Deliver Package #3
        """)
        
        if results.get('found_better_route', False):
            st.success("Your solution outperformed the AI's calculated optimal route!")

    if st.button("Play Again", use_container_width=True):
        st.session_state.game_results = None
        st.session_state.debug_shown = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)