import streamlit as st
import plotly.graph_objects as go
import numpy as np
import time

from config import LOCATIONS, GAME_MODES, ROAD_SEGMENTS
from routing import get_distance, suggest_next_location
from feature_road_closures import is_road_closed
from feature_packages import get_available_packages_at_location, get_package_hints
from game_engine import process_location_checkin, pickup_package, get_game_status, get_completion_summary

def visualize_map(player_route=None, optimal_route=None, constraints=None, show_roads=True, route_type="both"):
    """Create a clean, professional visual map with improved route display."""
    fig = go.Figure()
    
    # Background grid and styling
    fig.add_shape(type="rect", x0=0, y0=0, x1=800, y1=400, fillcolor="rgba(220, 240, 230, 0.6)", 
                  line=dict(color="#2e8b57", width=3), layer="below")
    for i in range(0, 801, 100):
        fig.add_shape(type="line", x0=i, y0=0, x1=i, y1=400, 
                      line=dict(color="rgba(0, 80, 40, 0.1)", width=1), layer="below")
    for i in range(0, 401, 100):
        fig.add_shape(type="line", x0=0, y0=i, x1=800, y1=i, 
                      line=dict(color="rgba(0, 80, 40, 0.1)", width=1), layer="below")
    
    # Draw road segments if show_roads is True
    if show_roads:
        for loc1, loc2 in ROAD_SEGMENTS:
            road_closed = is_road_closed(loc1, loc2)
            fig.add_shape(type="line", x0=LOCATIONS[loc1]["position"][0], 
                          y0=LOCATIONS[loc1]["position"][1], 
                          x1=LOCATIONS[loc2]["position"][0], 
                          y1=LOCATIONS[loc2]["position"][1], 
                          line=dict(color="#555555" if not road_closed else "#ff0000", width=6, 
                                    dash="dot" if road_closed else None), layer="below")
            if not road_closed:
                fig.add_shape(type="line", x0=LOCATIONS[loc1]["position"][0], 
                              y0=LOCATIONS[loc1]["position"][1], 
                              x1=LOCATIONS[loc2]["position"][0], 
                              y1=LOCATIONS[loc2]["position"][1], 
                              line=dict(color="#ffffff", width=1, dash="dash"), layer="below")

    # Track repeated traversals to offset lines
    def get_offset(route, start_idx, end_idx):
        """Calculate an offset for repeated traversals to visually separate them."""
        path = tuple(sorted([route[start_idx], route[end_idx]]))  # Sort to treat A→B and B→A as same path
        count = sum(1 for i in range(len(route) - 1) if tuple(sorted([route[i], route[i+1]])) == path and i < start_idx)
        # Alternate direction: up for odd counts, down for even counts
        direction = 1 if count % 2 == 0 else -1
        return direction * (count // 2 + 1) * 20  # 20 units per repeat, alternating direction

    # User Route: Separate lines for each traversal with numbered sequence
    line_width = 4 if not show_roads else 2
    if player_route and len(player_route) > 1 and (route_type == "both" or route_type == "player"):
        for i in range(len(player_route) - 1):
            x0, y0 = LOCATIONS[player_route[i]]["position"]
            x1, y1 = LOCATIONS[player_route[i+1]]["position"]
            # Apply offset for repeated traversals
            offset = get_offset(player_route, i, i+1)
            y0_offset = y0 + offset
            y1_offset = y1 + offset
            # Add separate line segment
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0_offset, y1_offset], mode='lines+markers',
                line=dict(color='#e63946', width=line_width),
                marker=dict(size=10 if not show_roads else 8, color='#e63946', 
                            line=dict(color='#ffffff', width=2)),
                name=f'Your Route Step {i+1}' if i == 0 else None,
                showlegend=(i == 0),
                hoverinfo='text', hovertext=f"Step {i+1}: {player_route[i]} → {player_route[i+1]}"
            ))
            # Add arrow
            dx, dy = x1 - x0, y1_offset - y0_offset
            length = np.sqrt(dx**2 + dy**2)
            if length > 0:  # Avoid division by zero
                dx, dy = dx / length, dy / length
                arrow_x = x1 - dx * 15
                arrow_y = y1_offset - dy * 15
                ref_x = x1 - dx * 25
                ref_y = y1_offset - dy * 25
                fig.add_annotation(
                    x=arrow_x, y=arrow_y,
                    ax=ref_x, ay=ref_y,
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True, arrowhead=3, arrowsize=1, arrowwidth=1.5,
                    arrowcolor="#e63946"
                )
            # Add sequence number at midpoint with slight horizontal offset
            mid_x = (x0 + x1) / 2 + (5 if dx > 0 else -5)
            mid_y = (y0_offset + y1_offset) / 2
            fig.add_annotation(
                x=mid_x, y=mid_y,
                text=f"{i+1}",
                showarrow=False,
                font=dict(size=10, color="white"),
                bgcolor="#e63946",
                bordercolor="#e63946",
                borderpad=2,
                borderwidth=1,
                opacity=0.8
            )

    # Optimal Route: Fixed to draw as a sequential path
    if (optimal_route and len(optimal_route) > 1 and (route_type == "both" or route_type == "optimal")):
        # Draw each segment of the optimal route in sequence
        for i in range(len(optimal_route) - 1):
            loc1 = optimal_route[i]
            loc2 = optimal_route[i+1]
            x0, y0 = LOCATIONS[loc1]["position"]
            x1, y1 = LOCATIONS[loc2]["position"]
            
            # Apply consistent offset for optimal route
            y0_offset = y0 - 8
            y1_offset = y1 - 8
            
            # Add sequential line segment
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0_offset, y1_offset], 
                mode='lines+markers',
                line=dict(color='#0466c8', width=line_width, 
                         dash='dot' if route_type == "both" else None),
                marker=dict(size=10, symbol='circle-open' if route_type == "both" else "circle", 
                           color='#0466c8', line=dict(color='#0466c8', width=2)),
                name=f'Optimal Route Step {i+1}' if i == 0 else None,
                showlegend=(i == 0),
                hoverinfo='text', 
                hovertext=f"Step {i+1}: {loc1} → {loc2}"
            ))
            
            # Add arrow
            dx = x1 - x0
            dy = y1_offset - y0_offset
            length = np.sqrt(dx**2 + dy**2)
            
            if length > 0:
                dx, dy = dx / length, dy / length
                arrow_x = x1 - dx * 15
                arrow_y = y1_offset - dy * 15
                ref_x = x1 - dx * 25
                ref_y = y1_offset - dy * 25
                
                fig.add_annotation(
                    x=arrow_x, y=arrow_y,
                    ax=ref_x, ay=ref_y,
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True, arrowhead=3, arrowsize=1, arrowwidth=1.5,
                    arrowcolor="#0466c8"
                )
            
            # Add sequence number
            mid_x = (x0 + x1) / 2 + (5 if dx > 0 else -5)
            mid_y = (y0_offset + y1_offset) / 2
            
            fig.add_annotation(
                x=mid_x, y=mid_y,
                text=f"{i+1}",
                showarrow=False,
                font=dict(size=10, color="white"),
                bgcolor="#0466c8",
                bordercolor="#0466c8",
                borderpad=2,
                borderwidth=1,
                opacity=0.8
            )

    # Location markers and package indicators
    for location, details in LOCATIONS.items():
        r = 40
        cx, cy = details["position"]
        hexagon_points = [(cx + r * np.cos((np.pi / 3) * i), cy + r * np.sin((np.pi / 3) * i)) for i in range(6)]
        path = f"M {hexagon_points[0][0]},{hexagon_points[0][1]} " + " ".join(f"L {x},{y}" for x, y in hexagon_points[1:]) + " Z"
        highlight_color = details["color"]
        
        if show_roads:
            has_pickup = any(pkg["pickup"] == location and pkg["status"] == "waiting" for pkg in st.session_state.packages)
            has_delivery = st.session_state.current_package and st.session_state.current_package["delivery"] == location
            if has_pickup:
                highlight_color = "#10B981"
            elif has_delivery:
                highlight_color = "#3B82F6"
        
        if constraints and location in constraints and show_roads:
            fig.add_shape(type="path", path=path, fillcolor="rgba(0,0,0,0)", 
                          line=dict(color="#6366F1", width=4))
        
        fig.add_shape(type="path", path=path, fillcolor=highlight_color, 
                      line=dict(color="#ffffff", width=2))
        fig.add_annotation(x=details["position"][0], y=details["position"][1], text=f"{location}", 
                           showarrow=False, font=dict(size=12, color="#ffffff", family="Arial", weight="bold"))
        fig.add_annotation(x=details["position"][0], y=details["position"][1] - 15, text=f"{details['emoji']}", 
                           showarrow=False, font=dict(size=20))
        
        # Add dotted black square around the current location during gameplay
        if show_roads and player_route and location == player_route[-1]:
            square_size = 50  # Slightly larger than the hexagon
            fig.add_shape(type="rect",
                          x0=cx - square_size, y0=cy - square_size,
                          x1=cx + square_size, y1=cy + square_size,
                          line=dict(color="black", width=2, dash="dot"),
                          fillcolor="rgba(0,0,0,0)")
        
        if show_roads:
            if constraints and location in constraints:
                fig.add_annotation(x=details["position"][0], y=details["position"][1] + 55, 
                                   text=constraints[location], showarrow=False, 
                                   font=dict(size=10, color="#333333"), bgcolor="rgba(255,255,255,0.8)", 
                                   bordercolor="#6366F1", borderwidth=1, borderpad=3)
            pending_packages = [p for p in st.session_state.packages if p["pickup"] == location and p["status"] == "waiting"]
            for i, pkg in enumerate(pending_packages[:3]):
                fig.add_annotation(x=details["position"][0], y=details["position"][1] - 50 - (i * 20), 
                                   text=f"{pkg['icon']} #{pkg['id']}", showarrow=False, font=dict(size=16), 
                                   bgcolor="rgba(255,255,255,0.8)", bordercolor="#10B981", borderwidth=2, borderpad=3)

    # Additional annotations
    if show_roads and st.session_state.closed_roads:
        fig.add_annotation(x=150, y=40, text="⛔️ ROAD CLOSURE", showarrow=False, 
                           font=dict(size=12, color="#EF4444", weight="bold"), 
                           bgcolor="rgba(255,255,255,0.8)", borderpad=3)
    
    if not show_roads:
        if route_type == "player":
            fig.add_annotation(x=400, y=40, text="YOUR ROUTE", showarrow=False, 
                               font=dict(size=16, color="#e63946", weight="bold"), 
                               bgcolor="rgba(255,255,255,0.8)", borderpad=3)
        elif route_type == "optimal":
            fig.add_annotation(x=400, y=40, text="OPTIMAL ROUTE", showarrow=False, 
                               font=dict(size=16, color="#0466c8", weight="bold"), 
                               bgcolor="rgba(255,255,255,0.8)", borderpad=3)
        elif route_type == "both":
            fig.add_annotation(x=400, y=40, text="ROUTE COMPARISON", showarrow=False, 
                               font=dict(size=16, color="#333333", weight="bold"), 
                               bgcolor="rgba(255,255,255,0.8)", borderpad=3)
    
    fig.add_annotation(x=400, y=370, text="LOGISTICS RUSH", showarrow=False, 
                       font=dict(size=24, color="#333333", family="Arial Black"), opacity=0.8)

    # Layout settings
    fig.update_layout(
        height=400 if not show_roads else 500,
        showlegend=True, 
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, 
                    bgcolor="rgba(255,255,255,0.8)", bordercolor="#cccccc", borderwidth=1),
        xaxis=dict(range=[-50, 850], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[-50, 450], showgrid=False, zeroline=False, showticklabels=False, 
                   scaleanchor="x", scaleratio=1),
        margin=dict(l=0, r=0, t=30, b=0), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)"
    )
    return fig

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
        if st.session_state.closed_roads:
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
    """Render the game results UI with improvement percent"""
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
    improvement = results['improvement_percent']
    color = "#10B981" if improvement < 0 else "#EF4444"
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
        st.markdown("**Optimal Route:**")
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
                    
                    # Create enhanced labels for each location
                    action_labels = []
                    for loc in optimal_path:
                        if loc in location_actions and location_actions[loc]:
                            # Add actions to the location label
                            actions = []
                            for act_type, pkg_id in location_actions[loc]:
                                action_code = "P" if act_type == "pickup" else "D"
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
                
                # Verify all packages are represented
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
                    st.warning(f"Note: The optimal route may not show all package operations. Missing operations for packages: {missing_operations}")
                    st.session_state.debug_shown = True
                
                st.code(route_text)
            else:
                st.markdown("*No optimal route available due to road closure.*")
        else:
            st.markdown("*No optimal route information available.*")

    if st.button("Play Again", use_container_width=True):
        st.session_state.game_results = None
        st.session_state.debug_shown = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)