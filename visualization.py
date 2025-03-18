import streamlit as st
import plotly.graph_objects as go
import numpy as np
import time

from config import LOCATIONS, GAME_MODES
from routing import get_distance 
from feature_road_closures import is_road_closed
from feature_packages import get_available_packages_at_location, get_package_hints
from game_engine import process_location_checkin, pickup_package, get_game_status, get_completion_summary

def visualize_map(player_route=None, optimal_route=None, constraints=None):
    """Create a clean, professional visual map with slight offset for overlapping routes."""
    fig = go.Figure()
   
    # Clean background with subtle gradient
    fig.add_shape(
        type="rect",
        x0=0, y0=0, x1=800, y1=400,
        fillcolor="rgba(220, 240, 230, 0.6)",
        line=dict(color="#2e8b57", width=3),
        layer="below"
    )
   
    # Add thin grid lines
    for i in range(0, 801, 100):
        fig.add_shape(
            type="line",
            x0=i, y0=0, x1=i, y1=400,
            line=dict(color="rgba(0, 80, 40, 0.1)", width=1),
            layer="below"
        )
    for i in range(0, 401, 100):
        fig.add_shape(
            type="line",
            x0=0, y0=i, x1=800, y1=i,
            line=dict(color="rgba(0, 80, 40, 0.1)", width=1),
            layer="below"
        )
   
    # Main roads from central hub
    for location, details in LOCATIONS.items():
        if location != "Central Hub":
            # Check if road is closed
            road_closed = is_road_closed(location, "Central Hub")
            
            fig.add_shape(
                type="line",
                x0=LOCATIONS["Central Hub"]["position"][0],
                y0=LOCATIONS["Central Hub"]["position"][1],
                x1=details["position"][0],
                y1=details["position"][1],
                line=dict(color="#555555" if not road_closed else "#ff0000", 
                         width=8,
                         dash="dot" if road_closed else None),
                layer="below"
            )
            # White dashed line on top (not shown if road is closed)
            if not road_closed:
                fig.add_shape(
                    type="line",
                    x0=LOCATIONS["Central Hub"]["position"][0],
                    y0=LOCATIONS["Central Hub"]["position"][1],
                    x1=details["position"][0],
                    y1=details["position"][1],
                    line=dict(color="#ffffff", width=1, dash="dash"),
                    layer="below"
                )
   
    # Outer ring roads (Factory->DHL->Shop->Residence->Factory)
    locations_list = ["Factory", "DHL Hub", "Shop", "Residence", "Factory"]
    for i in range(len(locations_list) - 1):
        loc1 = locations_list[i]
        loc2 = locations_list[i + 1]
        
        # Check if road is closed
        road_closed = is_road_closed(loc1, loc2)
        
        fig.add_shape(
            type="line",
            x0=LOCATIONS[loc1]["position"][0],
            y0=LOCATIONS[loc1]["position"][1],
            x1=LOCATIONS[loc2]["position"][0],
            y1=LOCATIONS[loc2]["position"][1],
            line=dict(color="#555555" if not road_closed else "#ff0000", 
                     width=6,
                     dash="dot" if road_closed else None),
            layer="below"
        )
        
        # White dashed line on top (not shown if road is closed)
        if not road_closed:
            fig.add_shape(
                type="line",
                x0=LOCATIONS[loc1]["position"][0],
                y0=LOCATIONS[loc1]["position"][1],
                x1=LOCATIONS[loc2]["position"][0],
                y1=LOCATIONS[loc2]["position"][1],
                line=dict(color="#ffffff", width=1, dash="dash"),
                layer="below"
            )
   
    # Diagonal cross roads
    diagonals = [("Factory", "Shop"), ("DHL Hub", "Residence")]
    for loc1, loc2 in diagonals:
        # Check if road is closed
        road_closed = is_road_closed(loc1, loc2)
        
        fig.add_shape(
            type="line",
            x0=LOCATIONS[loc1]["position"][0],
            y0=LOCATIONS[loc1]["position"][1],
            x1=LOCATIONS[loc2]["position"][0],
            y1=LOCATIONS[loc2]["position"][1],
            line=dict(color="#555555" if not road_closed else "#ff0000", 
                     width=4,
                     dash="dot" if road_closed else None),
            layer="below"
        )
        
        # White dashed line on top (not shown if road is closed)
        if not road_closed:
            fig.add_shape(
                type="line",
                x0=LOCATIONS[loc1]["position"][0],
                y0=LOCATIONS[loc1]["position"][1],
                x1=LOCATIONS[loc2]["position"][0],
                y1=LOCATIONS[loc2]["position"][1],
                line=dict(color="#ffffff", width=1, dash="dash"),
                layer="below"
            )
   
    # --- Optimal route (draw first so it's behind player route) ---
    if optimal_route and len(optimal_route) > 1:
        route_x = []
        route_y = []
        for location in optimal_route:
            route_x.append(LOCATIONS[location]["position"][0])
            route_y.append(LOCATIONS[location]["position"][1])
        # Wider background line
        fig.add_trace(go.Scatter(
            x=route_x,
            y=route_y,
            mode='lines',
            line=dict(color='#0466c8', width=5),
            opacity=0.3,
            showlegend=False
        ))
        # Main dashed line
        fig.add_trace(go.Scatter(
            x=route_x,
            y=route_y,
            mode='lines+markers',
            line=dict(color='#0466c8', width=3, dash='dash'),
            marker=dict(
                size=7,
                color='#0466c8',
                symbol='circle',
                line=dict(color='#ffffff', width=1)
            ),
            name='Optimal Route'
        ))
        # Letter indicators (A, B, C, D...)
        for i in range(len(optimal_route)):
            letter = chr(65 + i)
            fig.add_annotation(
                x=LOCATIONS[optimal_route[i]]["position"][0] - 30,
                y=LOCATIONS[optimal_route[i]]["position"][1] - 30,
                text=letter,
                showarrow=False,
                font=dict(size=12, color="#ffffff"),
                bgcolor="#0466c8",
                borderpad=3,
                opacity=0.9
            )
   
    # Central Hub (rectangle)
    central_hub = LOCATIONS["Central Hub"]
    fig.add_shape(
        type="rect",
        x0=central_hub["position"][0] - 50,
        y0=central_hub["position"][1] - 50,
        x1=central_hub["position"][0] + 50,
        y1=central_hub["position"][1] + 50,
        fillcolor="#333333",
        line=dict(color="#ffffff", width=2)
    )
    fig.add_annotation(
        x=central_hub["position"][0],
        y=central_hub["position"][1],
        text="CENTRAL<br>HUB",
        showarrow=False,
        font=dict(size=14, color="#ffffff", family="Arial")
    )
   
    # Draw each location as a hexagon
    for location, details in LOCATIONS.items():
        if location != "Central Hub":
            r = 40
            cx, cy = details["position"]
            hexagon_points = []
            for i in range(6):
                angle = (np.pi / 3) * i
                x = cx + r * np.cos(angle)
                y = cy + r * np.sin(angle)
                hexagon_points.append((x, y))
            path = f"M {hexagon_points[0][0]},{hexagon_points[0][1]} "
            for x, y in hexagon_points[1:]:
                path += f"L {x},{y} "
            path += "Z"
            
            # If we're in package delivery mode, highlight package locations
            highlight_color = details["color"]
            
            # Check if this location has packages for pickup
            has_pickup = any(pkg["pickup"] == location and pkg["status"] == "waiting" 
                            for pkg in st.session_state.packages)
            # Check if this location is a delivery destination for carried packages
            has_delivery = st.session_state.current_package and st.session_state.current_package["delivery"] == location
            
            # Use a different color if it's a pickup or delivery location
            if has_pickup:
                highlight_color = "#10B981"  # Green for pickup
            elif has_delivery:
                highlight_color = "#3B82F6"  # Blue for delivery
            
            # Check for constraint highlighting
            if constraints and location in constraints:
                # Add a slight border effect for constrained locations
                fig.add_shape(
                    type="path",
                    path=path,
                    fillcolor="rgba(0,0,0,0)",
                    line=dict(color="#6366F1", width=4)
                )
            
            fig.add_shape(
                type="path",
                path=path,
                fillcolor=highlight_color,
                line=dict(color="#ffffff", width=2)
            )
            # Name
            fig.add_annotation(
                x=details["position"][0],
                y=details["position"][1],
                text=f"{location}",
                showarrow=False,
                font=dict(size=12, color="#ffffff", family="Arial", weight="bold")
            )
            # Emoji above name
            fig.add_annotation(
                x=details["position"][0],
                y=details["position"][1] - 15,
                text=f"{details['emoji']}",
                showarrow=False,
                font=dict(size=20)
            )
            # Constraints if applicable
            if constraints and location in constraints:
                fig.add_annotation(
                    x=details["position"][0],
                    y=details["position"][1] + 55,
                    text=constraints[location],
                    showarrow=False,
                    font=dict(size=10, color="#333333"),
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="#6366F1",
                    borderwidth=1,
                    borderpad=3
                )
            
            # Package indicators
            pending_packages = [p for p in st.session_state.packages if p["pickup"] == location and p["status"] == "waiting"]
            if pending_packages:
                # Display package emoji above location
                for i, pkg in enumerate(pending_packages[:3]):  # Limit to 3 visible packages
                    fig.add_annotation(
                        x=details["position"][0],
                        y=details["position"][1] - 50 - (i * 20),
                        text=f"{pkg['icon']} #{pkg['id']}",
                        showarrow=False,
                        font=dict(size=16),
                        bgcolor="rgba(255,255,255,0.8)",
                        bordercolor="#10B981",
                        borderwidth=2,
                        borderpad=3
                    )
   
    # --- Player route with slight offset if there's also an optimal route ---
    offset_x = 0
    offset_y = 0
    # If we do have both routes, offset the player route by a small amount
    if player_route and optimal_route:
        offset_x = 5
        offset_y = -5

    if player_route and len(player_route) > 1:
        route_x = []
        route_y = []
        for location in player_route:
            # Apply offset to avoid direct overlap
            route_x.append(LOCATIONS[location]["position"][0] + offset_x)
            route_y.append(LOCATIONS[location]["position"][1] + offset_y)
        # Slightly wider background
        fig.add_trace(go.Scatter(
            x=route_x,
            y=route_y,
            mode='lines',
            line=dict(color='#e63946', width=6),
            opacity=0.2,
            showlegend=False
        ))
        # Main player route
        fig.add_trace(go.Scatter(
            x=route_x,
            y=route_y,
            mode='lines+markers',
            line=dict(color='#e63946', width=3),
            marker=dict(
                size=8,
                color='#e63946',
                line=dict(color='#ffffff', width=1)
            ),
            name='Your Route'
        ))
        # Numbered indicators
        for i, loc in enumerate(player_route):
            fig.add_annotation(
                x=LOCATIONS[loc]["position"][0] + offset_x + 30,
                y=LOCATIONS[loc]["position"][1] + offset_y + 30,
                text=str(i+1),
                showarrow=False,
                font=dict(size=12, color="#ffffff"),
                bgcolor="#e63946",
                borderpad=3,
                opacity=0.9
            )
   
    # Explanation text for route indicators
    if player_route and optimal_route:
        fig.add_annotation(
            x=650,
            y=40,
            text="Your Route: 1→2→3→...",
            showarrow=False,
            font=dict(size=10, color="#e63946"),
            bgcolor="rgba(255,255,255,0.8)",
            borderpad=3
        )
        fig.add_annotation(
            x=650,
            y=70,
            text="Optimal Route: A→B→C→...",
            showarrow=False,
            font=dict(size=10, color="#0466c8"),
            bgcolor="rgba(255,255,255,0.8)",
            borderpad=3
        )
        
    # Add road closure indicators
    if st.session_state.closed_roads:
        fig.add_annotation(
            x=150,
            y=40,
            text="⛔️ ROAD CLOSURES",
            showarrow=False,
            font=dict(size=12, color="#EF4444", weight="bold"),
            bgcolor="rgba(255,255,255,0.8)",
            borderpad=3
        )
   
    # Minimal title
    fig.add_annotation(
        x=400,
        y=370,
        text="LOGISTICS RUSH",
        showarrow=False,
        font=dict(size=24, color="#333333", family="Arial Black"),
        opacity=0.8
    )
   
    # Layout
    fig.update_layout(
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="#cccccc",
            borderwidth=1
        ),
        xaxis=dict(
            range=[-50, 850],
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        yaxis=dict(
            range=[-50, 450],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor="x",
            scaleratio=1
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
   
    return fig

def render_game_controls():
    """Render the game controls UI for active games"""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"### Logistics Challenge")
    
    # Show all game elements at once in the integrated mode
    
    # Road closure warning
    if st.session_state.closed_roads:
        st.markdown('<div class="road-closure-alert">⛔️ ALERT: Road Closures In Effect!</div>', unsafe_allow_html=True)
        closures_text = ", ".join([f"{road[0]} ↔️ {road[1]}" for road in st.session_state.closed_roads])
        st.markdown(f"**Closed roads:** {closures_text}")
    
    # Package delivery info
    st.markdown('<div class="package-info">', unsafe_allow_html=True)
    st.markdown(f"**📊 Package Status:** {len(st.session_state.delivered_packages)}/{st.session_state.total_packages} Delivered")
    
    if st.session_state.current_package:
        pkg = st.session_state.current_package
        st.markdown(f"**🚚 Carrying:** {pkg['icon']} Package #{pkg['id']} to {pkg['delivery']}")
    else:
        st.markdown("**🚚 Carrying:** No package")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Sequence constraints info
    st.markdown('<div class="constraints-info">', unsafe_allow_html=True)
    st.markdown("**🔄 Sequence Constraints:**")
    st.markdown("• Factory must be visited before Shop")
    st.markdown("• DHL Hub must be visited before Residence")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Game status and objectives
    completion = get_completion_summary()
    if completion:
        # Progress bars for each objective
        st.markdown("### Current Status")
        game_status = get_game_status()
        if game_status:
            st.metric("Time", f"{game_status['time']:.1f} seconds")
            
            # Location visits progress
            loc_visited = len(set([loc for loc in st.session_state.current_route if loc != "Central Hub"]))
            total_loc = len([loc for loc in LOCATIONS.keys() if loc != "Central Hub"])
            loc_progress = min(100, int((loc_visited / total_loc) * 100))
            
            st.markdown(f"Location Visits: {loc_visited}/{total_loc} ({loc_progress}%)")
            st.markdown(
                f"""<div class="progress-bar"><div class="progress-fill" style="width:{loc_progress}%"></div></div>""",
                unsafe_allow_html=True
            )
            
            # Package delivery progress
            pkg_progress = min(100, int((len(st.session_state.delivered_packages) / 
                                      max(1, st.session_state.total_packages)) * 100))
            
            st.markdown(f"Package Deliveries: {len(st.session_state.delivered_packages)}/{st.session_state.total_packages} ({pkg_progress}%)")
            st.markdown(
                f"""<div class="progress-bar"><div class="progress-fill" style="width:{pkg_progress}%"></div></div>""",
                unsafe_allow_html=True
            )
            
            # Constraints status
            constraint_status = "✅ Met" if completion["constraints_followed"] else "❌ Not Met"
            st.markdown(f"Constraints: {constraint_status}")
            
            if not completion["constraints_followed"]:
                for issue in completion["constraint_issues"]:
                    st.warning(issue)

    # Game hints
    hints = get_package_hints()
    if hints:
        with st.expander("Need a hint?"):
            for hint in hints:
                st.markdown(f"• {hint}")

    # Location check-in buttons
    st.markdown("### Check-in at Location")
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button(f"{LOCATIONS['Factory']['emoji']} Factory", key="factory_btn", use_container_width=True):
            results = process_location_checkin("Factory")
            if results:
                st.rerun()
        if st.button(f"{LOCATIONS['Shop']['emoji']} Shop", key="shop_btn", use_container_width=True):
            results = process_location_checkin("Shop")
            if results:
                st.rerun()
    with btn_col2:
        if st.button(f"{LOCATIONS['DHL Hub']['emoji']} DHL Hub", key="dhl_btn", use_container_width=True):
            results = process_location_checkin("DHL Hub")
            if results:
                st.rerun()
        if st.button(f"{LOCATIONS['Residence']['emoji']} Residence", key="res_btn", use_container_width=True):
            results = process_location_checkin("Residence")
            if results:
                st.rerun()
    
    # Central Hub button - highlight as a detour option
    st.button(f"{LOCATIONS['Central Hub']['emoji']} Central Hub", key="central_hub_btn", use_container_width=True,
              help="Use the Central Hub to bypass road closures", 
              on_click=lambda: process_location_checkin("Central Hub"))
    
    # Package pickup button (only shown when at a location with packages)
    if st.session_state.current_route:
        current_location = st.session_state.current_route[-1]
        available_pickups = get_available_packages_at_location(current_location)
        
        if available_pickups and not st.session_state.current_package:
            st.markdown("### Package Actions")
            # Allow player to pick up a package
            pickup_options = {f"{pkg['icon']} Package #{pkg['id']} to {pkg['delivery']}": pkg 
                              for pkg in available_pickups}
            
            selected_package_str = st.selectbox(
                "Select a package to pick up:",
                options=list(pickup_options.keys())
            )
            
            if st.button("📦 Pick Up Package", key="pickup_btn", 
                         use_container_width=True, type="primary", 
                         help="Pick up the selected package"):
                selected_package = pickup_options[selected_package_str]
                pickup_package(selected_package)
                st.rerun()

    # Show current route
    if st.session_state.current_route:
        st.markdown("### Your Route")
        route_text = " → ".join(st.session_state.current_route)
        st.code(route_text)
    st.markdown('</div>', unsafe_allow_html=True)

def render_game_results():
    """Render the game results UI"""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Challenge Complete!")
    results = st.session_state.game_results

    # Score
    st.markdown(f"""
    <div style="text-align:center;margin-bottom:20px">
        <div style="font-size:3rem;font-weight:bold;color:#1a56db">{results['score']}</div>
        <div style="font-size:1rem;color:#6b7280">SCORE</div>
    </div>
    """, unsafe_allow_html=True)

    # Metrics
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Time", f"{results['time']:.1f}s")
        st.metric("Your Distance", f"{results['player_distance']:.1f}")
    with c2:
        st.metric("Efficiency", f"{results['efficiency']}%")
        st.metric("Optimal Distance", f"{results['optimal_distance']:.1f}")

    # Detailed score breakdown
    st.markdown('<div class="score-breakdown">', unsafe_allow_html=True)
    st.markdown("### Score Breakdown")
    components = results["score_components"]
    
    col_score1, col_score2 = st.columns(2)
    with col_score1:
        st.metric("Efficiency Score", f"{components['efficiency']:.1f}")
        st.metric("Delivery Score", f"{components['delivery']:.1f}")
    with col_score2:
        st.metric("Constraint Score", f"{components['constraints']:.1f}")
        st.metric("Time Score", f"{components['time']:.1f}")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Challenge results
    st.markdown("### Challenge Results")
    
    # Package delivery summary
    if st.session_state.delivered_packages:
        st.markdown(f"**Packages Delivered:** {len(st.session_state.delivered_packages)}/{st.session_state.total_packages}")
        for i, pkg in enumerate(st.session_state.delivered_packages):
            st.markdown(f"✅ {pkg['icon']} Package #{pkg['id']}: {pkg['pickup']} → {pkg['delivery']}")
    else:
        st.markdown("**No packages delivered**")
    
    # Constraint status
    constraints_followed = results.get('constraints_followed', False)
    st.markdown(f"**Sequence Constraints:** {'✅ Met' if constraints_followed else '❌ Not Met'}")
    
    # Road closure summary
    if st.session_state.closed_roads:
        st.markdown("**Road Closures Navigated:**")
        for road in st.session_state.closed_roads:
            st.markdown(f"⛔️ {road[0]} ↔️ {road[1]}")

    # Route comparison
    st.markdown("### Route Analysis")
    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown("**Your Route:**")
        route_text = " → ".join(st.session_state.completed_routes["player"])
        st.code(route_text)
    with cc2:
        st.markdown("**Optimal Route:**")
        if st.session_state.completed_routes["optimal"] and len(st.session_state.completed_routes["optimal"]) > 1:
            route_text = " → ".join(st.session_state.completed_routes["optimal"])
            st.code(route_text)
        else:
            st.markdown("*No optimal route available due to road closures.*")

    # Play again button
    if st.button("Play Again", use_container_width=True):
        st.session_state.game_results = None
        st.rerun()
        
    st.markdown('</div>', unsafe_allow_html=True)