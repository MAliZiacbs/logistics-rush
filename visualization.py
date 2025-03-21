import streamlit as st
import plotly.graph_objects as go
import numpy as np
import time

from config import LOCATIONS, GAME_MODES, ROAD_SEGMENTS
from routing import get_distance, suggest_next_location
from feature_road_closures import is_road_closed
from feature_packages import get_available_packages_at_location, get_package_hints
from game_engine import process_location_checkin, pickup_package, get_game_status, get_completion_summary

# This patch fixes the visualization issue where the optimal route shows paths using closed roads

# Add this improved function to visualization.py
def visualize_map(player_route=None, optimal_route=None, constraints=None, show_roads=True, route_type="both"):
    """Create a clean, professional visual map with improved route display and road closure handling."""
    fig = go.Figure()
    
    # Get road closures from session state
    closed_roads = st.session_state.closed_roads if 'closed_roads' in st.session_state else []
    
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
            road_closed = any((loc1, loc2) == closure or (loc2, loc1) == closure for closure in closed_roads)
            
            line_color = "#ff0000" if road_closed else "#555555"
            line_dash = "dot" if road_closed else None
            line_width = 8 if road_closed else 6
            
            fig.add_shape(type="line", x0=LOCATIONS[loc1]["position"][0], 
                          y0=LOCATIONS[loc1]["position"][1], 
                          x1=LOCATIONS[loc2]["position"][0], 
                          y1=LOCATIONS[loc2]["position"][1], 
                          line=dict(color=line_color, width=line_width, dash=line_dash), layer="below")
            
            if not road_closed:
                fig.add_shape(type="line", x0=LOCATIONS[loc1]["position"][0], 
                              y0=LOCATIONS[loc1]["position"][1], 
                              x1=LOCATIONS[loc2]["position"][0], 
                              y1=LOCATIONS[loc2]["position"][1], 
                              line=dict(color="#ffffff", width=1, dash="dash"), layer="below")
                              
            # For closed roads, add a clear visual indicator
            if road_closed:
                mid_x = (LOCATIONS[loc1]["position"][0] + LOCATIONS[loc2]["position"][0]) / 2
                mid_y = (LOCATIONS[loc1]["position"][1] + LOCATIONS[loc2]["position"][1]) / 2
                
                fig.add_annotation(
                    x=mid_x, y=mid_y,
                    text="⛔",
                    showarrow=False,
                    font=dict(size=16),
                    bgcolor="white",
                    borderpad=2,
                    bordercolor="#ff0000",
                    borderwidth=2,
                    opacity=0.9
                )
            else:
                # Add distance labels to roads
                mid_x = (LOCATIONS[loc1]["position"][0] + LOCATIONS[loc2]["position"][0]) / 2
                mid_y = (LOCATIONS[loc1]["position"][1] + LOCATIONS[loc2]["position"][1]) / 2
                distance = get_distance(loc1, loc2)
                
                fig.add_annotation(
                    x=mid_x, y=mid_y,
                    text=f"{int(distance)} cm",
                    showarrow=False,
                    font=dict(size=10, color="#000000"),
                    bgcolor="rgba(255, 255, 255, 0.7)",
                    borderpad=2,
                    borderwidth=1,
                    opacity=0.9
                )

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
                hoverinfo='text', hovertext=f"Step {i+1}: {player_route[i]} → {player_route[i+1]} ({get_distance(player_route[i], player_route[i+1]):.0f} cm)"
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

    # Optimal Route: Fixed to draw showing proper detours around closed roads with better offsets
    if (optimal_route and len(optimal_route) > 1 and (route_type == "both" or route_type == "optimal")):
        # Verify the optimal route includes all required locations
        missing_locations = [loc for loc in LOCATIONS.keys() if loc not in optimal_route]
        if missing_locations:
            # If we're in results view, show a warning
            if not show_roads:
                st.warning(f"Optimal route visualization is missing required locations: {', '.join(missing_locations)}")
        
        # Process the optimal route to respect road closures
        processed_optimal_route = []
        for i in range(len(optimal_route) - 1):
            loc1 = optimal_route[i]
            loc2 = optimal_route[i+1]
            
            # Check if this segment uses a closed road
            is_closed = False
            for closed_road in closed_roads:
                if (loc1 == closed_road[0] and loc2 == closed_road[1]) or (loc1 == closed_road[1] and loc2 == closed_road[0]):
                    is_closed = True
                    break
            
            if not is_closed:
                # Direct route is available
                if i == 0:
                    processed_optimal_route.append(loc1)
                processed_optimal_route.append(loc2)
            else:
                # Need to find a detour
                from routing import calculate_segment_path
                segment_path, _ = calculate_segment_path(loc1, loc2)
                
                if segment_path:
                    # Use the calculated detour path
                    if i == 0:
                        processed_optimal_route.extend(segment_path)
                    else:
                        # Skip the first location to avoid duplication
                        processed_optimal_route.extend(segment_path[1:])
                else:
                    # If no path is found, just add the endpoints
                    if i == 0:
                        processed_optimal_route.append(loc1)
                    processed_optimal_route.append(loc2)
        
        # Use the processed route for visualization
        display_route = processed_optimal_route if processed_optimal_route else optimal_route
        
        # Check if display route includes all locations
        display_locations = set(display_route)
        all_locations = set(LOCATIONS.keys())
        if not all_locations.issubset(display_locations) and not show_roads:
            missing = all_locations - display_locations
            st.warning(f"The optimal route visualization is missing locations: {', '.join(missing)}")
        
        # Track path segments for offset calculation
        path_counts = {}
        
        # Draw each segment of the optimal route in sequence
        for i in range(len(display_route) - 1):
            loc1 = display_route[i]
            loc2 = display_route[i+1]
            
            # Skip if this segment uses a closed road
            is_closed = False
            for road in closed_roads:
                if (loc1 == road[0] and loc2 == road[1]) or (loc1 == road[1] and loc2 == road[0]):
                    is_closed = True
                    break
            if is_closed:
                continue
                
            # Get coordinates
            x0, y0 = LOCATIONS[loc1]["position"]
            x1, y1 = LOCATIONS[loc2]["position"]
            
            # Calculate offset (similar to player route)
            segment = tuple(sorted([loc1, loc2]))
            if segment not in path_counts:
                path_counts[segment] = 0
            path_counts[segment] += 1
            
            offset = -10 * path_counts[segment]  # Negative offset to distinguish from player route
            
            y0_offset = y0 + offset
            y1_offset = y1 + offset
            
            # Add segment line
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
                hovertext=f"Step {i+1}: {loc1} → {loc2} ({get_distance(loc1, loc2):.0f} cm)"
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
            # Change pickup location color to orange instead of green
            has_pickup = any(pkg["pickup"] == location and pkg["status"] == "waiting" for pkg in st.session_state.packages)
            has_delivery = st.session_state.current_package and st.session_state.current_package["delivery"] == location
            if has_pickup:
                highlight_color = "#f97316"  # Changed to orange
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
                                   text=f"{pkg['icon']} #{pkg['id']} to {pkg['delivery']}", showarrow=False, font=dict(size=16), 
                                   bgcolor="rgba(255,255,255,0.8)", bordercolor="#f97316", borderwidth=2, borderpad=3) # Changed from #10B981 to orange

    # Additional annotations
    if show_roads and hasattr(st.session_state, 'closed_roads') and st.session_state.closed_roads:
        num_closures = len(st.session_state.closed_roads)
        
        # Use the display difficulty from session state if available
        difficulty_label = st.session_state.get('displayed_difficulty', 
                       "EASY" if num_closures == 1 else "MEDIUM" if num_closures == 2 else "HARD")
        difficulty_label = difficulty_label.upper()
        
        # Set colors based on the displayed difficulty label
        closure_color = "#f97316" if difficulty_label == "EASY" else "#ef4444" if difficulty_label == "MEDIUM" else "#7f1d1d"
        
        fig.add_annotation(x=150, y=40, 
                           text=f"⛔️ {difficulty_label}: {num_closures} ROAD CLOSURE{'S' if num_closures > 1 else ''}", 
                           showarrow=False, 
                           font=dict(size=12, color=closure_color, weight="bold"), 
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
    
    # Add real distance info
    if show_roads:
        fig.add_annotation(x=650, y=40, 
                          text="DISTANCES SHOWN IN CENTIMETERS", 
                          showarrow=False, 
                          font=dict(size=12, color="#333333", weight="bold"), 
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