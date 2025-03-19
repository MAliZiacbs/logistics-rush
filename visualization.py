import streamlit as st
import plotly.graph_objects as go
import numpy as np
import time

from config import LOCATIONS, GAME_MODES
from routing import get_distance, suggest_next_location
from feature_road_closures import is_road_closed
from feature_packages import get_available_packages_at_location, get_package_hints
from game_engine import process_location_checkin, pickup_package, get_game_status, get_completion_summary

def visualize_map(player_route=None, optimal_route=None, constraints=None, show_roads=True):
    """Create a clean, professional visual map with improved route display.
    
    Parameters:
    - player_route: List of locations visited by the player
    - optimal_route: List of optimal locations to visit
    - constraints: Dictionary of constraints for each location
    - show_roads: Whether to show roads (set to False for result visualization)
    """
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
    
    # Draw road segments only if show_roads is True
    if show_roads:
        for location, details in LOCATIONS.items():
            if location != "Central Hub":
                road_closed = is_road_closed(location, "Central Hub")
                fig.add_shape(type="line", x0=LOCATIONS["Central Hub"]["position"][0], 
                              y0=LOCATIONS["Central Hub"]["position"][1], x1=details["position"][0], 
                              y1=details["position"][1], 
                              line=dict(color="#555555" if not road_closed else "#ff0000", width=8, 
                                        dash="dot" if road_closed else None), layer="below")
                if not road_closed:
                    fig.add_shape(type="line", x0=LOCATIONS["Central Hub"]["position"][0], 
                                  y0=LOCATIONS["Central Hub"]["position"][1], x1=details["position"][0], 
                                  y1=details["position"][1], 
                                  line=dict(color="#ffffff", width=1, dash="dash"), layer="below")
        locations_list = ["Factory", "DHL Hub", "Shop", "Residence", "Factory"]
        for i in range(len(locations_list) - 1):
            loc1, loc2 = locations_list[i], locations_list[i + 1]
            road_closed = is_road_closed(loc1, loc2)
            fig.add_shape(type="line", x0=LOCATIONS[loc1]["position"][0], y0=LOCATIONS[loc1]["position"][1], 
                          x1=LOCATIONS[loc2]["position"][0], y1=LOCATIONS[loc2]["position"][1], 
                          line=dict(color="#555555" if not road_closed else "#ff0000", width=6, 
                                    dash="dot" if road_closed else None), layer="below")
            if not road_closed:
                fig.add_shape(type="line", x0=LOCATIONS[loc1]["position"][0], y0=LOCATIONS[loc1]["position"][1], 
                              x1=LOCATIONS[loc2]["position"][0], y1=LOCATIONS[loc2]["position"][1], 
                              line=dict(color="#ffffff", width=1, dash="dash"), layer="below")
        diagonals = [("Factory", "Shop"), ("DHL Hub", "Residence")]
        for loc1, loc2 in diagonals:
            road_closed = is_road_closed(loc1, loc2)
            fig.add_shape(type="line", x0=LOCATIONS[loc1]["position"][0], y0=LOCATIONS[loc1]["position"][1], 
                          x1=LOCATIONS[loc2]["position"][0], y1=LOCATIONS[loc2]["position"][1], 
                          line=dict(color="#555555" if not road_closed else "#ff0000", width=4, 
                                    dash="dot" if road_closed else None), layer="below")
            if not road_closed:
                fig.add_shape(type="line", x0=LOCATIONS[loc1]["position"][0], y0=LOCATIONS[loc1]["position"][1], 
                              x1=LOCATIONS[loc2]["position"][0], y1=LOCATIONS[loc2]["position"][1], 
                              line=dict(color="#ffffff", width=1, dash="dash"), layer="below")

    # User Route: Solid line with hover info - make it more prominent in results view
    line_width = 6 if not show_roads else 4  # Thicker line when showing results
    if player_route and len(player_route) > 1:
        route_x = [LOCATIONS[loc]["position"][0] for loc in player_route]
        route_y = [LOCATIONS[loc]["position"][1] for loc in player_route]
        hover_text = [f"Step {i+1}: {loc}" for i, loc in enumerate(player_route)]
        fig.add_trace(go.Scatter(
            x=route_x, y=route_y, mode='lines+markers',
            line=dict(color='#e63946', width=line_width), opacity=0.9,
            marker=dict(size=10 if not show_roads else 8, color='#e63946', 
                        line=dict(color='#ffffff', width=2)),
            name='Your Route', hoverinfo='text', hovertext=hover_text
        ))

    # Optimal Route: Curved paths with action-based colors
    # Fix for the index error: Check that optimal_route and optimal_path exist and have compatible lengths
    if (optimal_route and 
        hasattr(st.session_state, 'optimal_path') and 
        st.session_state.optimal_path and 
        len(st.session_state.optimal_path) > 1 and
        hasattr(st.session_state, 'optimal_route') and
        len(st.session_state.optimal_route) >= len(st.session_state.optimal_path) - 1):
        
        # Draw a single optimal path line when showing results
        if not show_roads:
            opt_route_x = [LOCATIONS[loc]["position"][0] for loc in st.session_state.optimal_path]
            opt_route_y = [LOCATIONS[loc]["position"][1] for loc in st.session_state.optimal_path]
            hover_text = [f"Step {chr(65+i)}: {loc}" for i, loc in enumerate(st.session_state.optimal_path)]
            fig.add_trace(go.Scatter(
                x=opt_route_x, y=opt_route_y, mode='lines+markers',
                line=dict(color='#0466c8', width=line_width, dash='dot'), opacity=0.8,
                marker=dict(size=10, symbol='circle-open', color='#0466c8', line=dict(color='#0466c8', width=2)),
                name='Optimal Route', hoverinfo='text', hovertext=hover_text
            ))
        else:
            # Original curved path display for in-game view
            for i in range(len(st.session_state.optimal_path) - 1):
                x0, y0 = LOCATIONS[st.session_state.optimal_path[i]]["position"]
                x1, y1 = LOCATIONS[st.session_state.optimal_path[i+1]]["position"]
                
                # Make sure we don't go out of bounds on optimal_route
                if i < len(st.session_state.optimal_route):
                    action = st.session_state.optimal_route[i]
                    color = '#0466c8' if action["action"] == "visit" else '#10B981' if action["action"] == "pickup" else '#3B82F6'
                    hover_text = f"Step {chr(65+i)}: {action['location']} ({action['action'][0].upper()}{action['package_id'] or ''})"
                else:
                    # Default values if optimal_route is shorter than optimal_path
                    color = '#0466c8'  # Default color
                    hover_text = f"Step {chr(65+i)}: {st.session_state.optimal_path[i]} → {st.session_state.optimal_path[i+1]}"
                    
                mid_x = (x0 + x1) / 2 - 50  # Curve downward for optimal route
                mid_y = (y0 + y1) / 2
                path = f"M {x0},{y0} Q {mid_x},{mid_y} {x1},{y1}"
                
                fig.add_shape(type="path", path=path, line=dict(color=color, width=2, dash='dash'), opacity=0.5)
                # Add hover point for each segment
                fig.add_trace(go.Scatter(
                    x=[(x0 + x1) / 2], y=[(y0 + y1) / 2], mode='markers',
                    marker=dict(size=1, color=color, opacity=0), hoverinfo='text', hovertext=[hover_text],
                    showlegend=False
                ))

    # Central Hub
    central_hub = LOCATIONS["Central Hub"]
    fig.add_shape(type="rect", x0=central_hub["position"][0] - 50, y0=central_hub["position"][1] - 50, 
                  x1=central_hub["position"][0] + 50, y1=central_hub["position"][1] + 50, 
                  fillcolor="#333333", line=dict(color="#ffffff", width=2))
    fig.add_annotation(x=central_hub["position"][0], y=central_hub["position"][1], text="CENTRAL<br>HUB", 
                       showarrow=False, font=dict(size=14, color="#ffffff", family="Arial"))

    # Location markers and package indicators
    for location, details in LOCATIONS.items():
        if location != "Central Hub":
            r = 40
            cx, cy = details["position"]
            hexagon_points = [(cx + r * np.cos((np.pi / 3) * i), cy + r * np.sin((np.pi / 3) * i)) for i in range(6)]
            path = f"M {hexagon_points[0][0]},{hexagon_points[0][1]} " + " ".join(f"L {x},{y}" for x, y in hexagon_points[1:]) + " Z"
            highlight_color = details["color"]
            
            # Only highlight packages in game mode, not results mode
            if show_roads:
                has_pickup = any(pkg["pickup"] == location and pkg["status"] == "waiting" for pkg in st.session_state.packages)
                has_delivery = st.session_state.current_package and st.session_state.current_package["delivery"] == location
                if has_pickup:
                    highlight_color = "#10B981"
                elif has_delivery:
                    highlight_color = "#3B82F6"
            
            if constraints and location in constraints:
                fig.add_shape(type="path", path=path, fillcolor="rgba(0,0,0,0)", 
                              line=dict(color="#6366F1", width=4))
            fig.add_shape(type="path", path=path, fillcolor=highlight_color, 
                          line=dict(color="#ffffff", width=2))
            fig.add_annotation(x=details["position"][0], y=details["position"][1], text=f"{location}", 
                               showarrow=False, font=dict(size=12, color="#ffffff", family="Arial", weight="bold"))
            fig.add_annotation(x=details["position"][0], y=details["position"][1] - 15, text=f"{details['emoji']}", 
                               showarrow=False, font=dict(size=20))
            
            # Only show constraints and packages in game mode, not results mode
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
        fig.add_annotation(x=150, y=40, text="⛔️ ROAD CLOSURES", showarrow=False, 
                           font=dict(size=12, color="#EF4444", weight="bold"), 
                           bgcolor="rgba(255,255,255,0.8)", borderpad=3)
    
    # Show comparison text in results view
    if not show_roads and optimal_route:
        fig.add_annotation(x=400, y=40, text="ROUTE COMPARISON", showarrow=False, 
                           font=dict(size=16, color="#333333", weight="bold"), 
                           bgcolor="rgba(255,255,255,0.8)", borderpad=3)
    
    fig.add_annotation(x=400, y=370, text="LOGISTICS RUSH", showarrow=False, 
                       font=dict(size=24, color="#333333", family="Arial Black"), opacity=0.8)

    # Layout settings
    fig.update_layout(
        height=500, showlegend=True, 
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
                result = process_location_checkin(loc)
                if result:
                    st.rerun()
    with col2:
        for loc in ["DHL Hub", "Residence"]:
            disabled = (loc == "Residence" and "DHL Hub" not in st.session_state.current_route)
            btn_type = "primary" if st.session_state.current_route and suggest_next_location(st.session_state.current_route[-1], st.session_state.current_route, st.session_state.packages)[0] == loc else "secondary"
            if st.button(f"{LOCATIONS[loc]['emoji']} {loc}", key=f"btn_{loc}", disabled=disabled, type=btn_type, use_container_width=True):
                result = process_location_checkin(loc)
                if result:
                    st.rerun()
    btn_type = "primary" if st.session_state.current_route and suggest_next_location(st.session_state.current_route[-1], st.session_state.current_route, st.session_state.packages)[0] == "Central Hub" else "secondary"
    if st.button(f"{LOCATIONS['Central Hub']['emoji']} Central Hub", key="btn_central", type=btn_type, use_container_width=True):
        result = process_location_checkin("Central Hub")
        if result:
            st.rerun()
    if st.session_state.current_route:
        current_loc = st.session_state.current_route[-1]
        pickups = get_available_packages_at_location(current_loc)
        if pickups and not st.session_state.current_package:
            st.markdown("### Pickup Package")
            for pkg in pickups:
                if st.button(f"{pkg['icon']} Package #{pkg['id']} to {pkg['delivery']}", key=f"pickup_{pkg['id']}", type="primary", use_container_width=True):
                    pickup_package(pkg)
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
            st.markdown('<div class="road-closure-alert">⛔️ Road Closures:</div>', unsafe_allow_html=True)
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
        st.markdown("**Road Closures Navigated:**")
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
        if st.session_state.completed_routes["optimal"] and len(st.session_state.completed_routes["optimal"]) > 1:
            optimal_actions = st.session_state.optimal_route
            route_text = " → ".join(st.session_state.completed_routes["optimal"])
            action_labels = []
            for i, loc in enumerate(st.session_state.completed_routes["optimal"]):
                action = next((a for a in optimal_actions if a["location"] == loc), None)
                if action and action["action"] in ["pickup", "deliver"]:
                    label = f"{loc} ({'P' if action['action'] == 'pickup' else 'D'}{action['package_id']})"
                else:
                    label = loc
                action_labels.append(label)
            route_text = " → ".join(action_labels)
            st.code(route_text)
        else:
            st.markdown("*No optimal route available due to road closures.*")

    if st.button("Play Again", use_container_width=True):
        st.session_state.game_results = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)