import plotly.graph_objects as go
import numpy as np

def visualize_map(current_location=None, available_moves=None, route=None, closed_roads=None, locations=None, optimal_route=None, show_both=False):
    """
    Create a map visualization with enhanced features.
    
    Args:
        current_location: The player's current location
        available_moves: List of available moves from current location
        route: The player's route as a list of location names
        closed_roads: List of tuples of closed roads [(loc1, loc2), ...]
        locations: Dictionary of location data including positions
        optimal_route: The optimal route to display
        show_both: Whether to show both player and optimal routes
    """
    if locations is None:
        # Use default locations from your config
        from config import LOCATIONS as locations
    
    if closed_roads is None:
        closed_roads = []
    
    fig = go.Figure()
    
    # Draw background grid
    fig.add_shape(type="rect", x0=0, y0=0, x1=800, y1=400, fillcolor="rgba(220, 240, 230, 0.6)", 
                  line=dict(color="#2e8b57", width=3), layer="below")
    
    # Draw grid lines
    for i in range(0, 801, 100):
        fig.add_shape(type="line", x0=i, y0=0, x1=i, y1=400, 
                      line=dict(color="rgba(0, 80, 40, 0.1)", width=1), layer="below")
    for i in range(0, 401, 100):
        fig.add_shape(type="line", x0=0, y0=i, x1=800, y1=i, 
                      line=dict(color="rgba(0, 80, 40, 0.1)", width=1), layer="below")
    
    # Draw roads (all possible connections)
    from config import ROAD_SEGMENTS, DISTANCES
    
    for loc1, loc2 in ROAD_SEGMENTS:
        # Check if this road is closed
        is_closed = any((loc1, loc2) == road or (loc2, loc1) == road for road in closed_roads)
        
        # Set road style based on status
        line_color = "#ff0000" if is_closed else "#555555"
        line_dash = "dot" if is_closed else None
        line_width = 8 if is_closed else 6
        
        # Draw the road
        pos1 = locations[loc1]["position"]
        pos2 = locations[loc2]["position"]
        
        fig.add_shape(type="line", x0=pos1[0], y0=pos1[1], x1=pos2[0], y1=pos2[1], 
                      line=dict(color=line_color, width=line_width, dash=line_dash), layer="below")
        
        # Add center line to non-closed roads
        if not is_closed:
            fig.add_shape(type="line", x0=pos1[0], y0=pos1[1], x1=pos2[0], y1=pos2[1], 
                          line=dict(color="#ffffff", width=1, dash="dash"), layer="below")
        
        # Add distance label
        mid_x = (pos1[0] + pos2[0]) / 2
        mid_y = (pos1[1] + pos2[1]) / 2
        
        # Get the distance for this segment
        distance = DISTANCES.get((loc1, loc2), DISTANCES.get((loc2, loc1), 300))
        
        # For closed roads, add a clear marker
        if is_closed:
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
    
    # Highlight available moves if provided
    if current_location and available_moves:
        current_pos = locations[current_location]["position"]
        
        for move in available_moves:
            move_loc = move["location"]
            move_pos = locations[move_loc]["position"]
            
            # Draw a highlighted path for available moves
            fig.add_trace(go.Scatter(
                x=[current_pos[0], move_pos[0]], 
                y=[current_pos[1], move_pos[1]], 
                mode='lines',
                line=dict(color='#4CAF50', width=8, dash='solid'),
                opacity=0.6,
                hoverinfo='text', 
                hovertext=f"Move to {move_loc} ({move['distance']} cm)"
            ))
    
    # Draw player route
    if route and len(route) > 1:
        for i in range(len(route) - 1):
            pos1 = locations[route[i]]["position"]
            pos2 = locations[route[i+1]]["position"]
            
            # Draw route segment
            fig.add_trace(go.Scatter(
                x=[pos1[0], pos2[0]], 
                y=[pos1[1], pos2[1]], 
                mode='lines+markers',
                line=dict(color='#e63946', width=4),
                marker=dict(size=10, color='#e63946', line=dict(color='#ffffff', width=2)),
                name=f'Your Route Step {i+1}' if i == 0 else None,
                showlegend=(i == 0),
                hoverinfo='text', 
                hovertext=f"Step {i+1}: {route[i]} → {route[i+1]}"
            ))
            
            # Add direction arrow
            dx, dy = pos2[0] - pos1[0], pos2[1] - pos1[1]
            length = np.sqrt(dx**2 + dy**2)
            
            if length > 0:
                dx, dy = dx / length, dy / length
                arrow_x = pos2[0] - dx * 15
                arrow_y = pos2[1] - dy * 15
                ref_x = pos2[0] - dx * 25
                ref_y = pos2[1] - dy * 25
                
                fig.add_annotation(
                    x=arrow_x, y=arrow_y,
                    ax=ref_x, ay=ref_y,
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True, arrowhead=3, arrowsize=1, arrowwidth=1.5,
                    arrowcolor="#e63946"
                )
            
            # Add step number
            mid_x = (pos1[0] + pos2[0]) / 2 + (5 if dx > 0 else -5)
            mid_y = (pos1[1] + pos2[1]) / 2
            
            fig.add_annotation(
                x=mid_x, y=mid_y,
                text=f"{i+1}",
                showarrow=False,
                font=dict(size=10, color="white"),
                bgcolor="#e63946",
                borderpad=2,
                borderwidth=1,
                opacity=0.8
            )
    
    # Draw optimal route if requested
    if optimal_route and len(optimal_route) > 1 and (show_both or not route):
        for i in range(len(optimal_route) - 1):
            # continuing visualization.py
            pos1 = locations[optimal_route[i]]["position"]
            pos2 = locations[optimal_route[i+1]]["position"]
            
            # Draw optimal route segment with different style
            fig.add_trace(go.Scatter(
                x=[pos1[0], pos2[0]], 
                y=[pos1[1], pos2[1]], 
                mode='lines+markers',
                line=dict(color='#0466c8', width=3, dash='dot'),
                marker=dict(size=8, symbol='circle-open', color='#0466c8', 
                           line=dict(color='#0466c8', width=2)),
                name=f'Optimal Route Step {i+1}' if i == 0 else None,
                showlegend=(i == 0),
                hoverinfo='text', 
                hovertext=f"Optimal Step {i+1}: {optimal_route[i]} → {optimal_route[i+1]}"
            ))
            
            # Add direction arrow for optimal route
            dx, dy = pos2[0] - pos1[0], pos2[1] - pos1[1]
            length = np.sqrt(dx**2 + dy**2)
            
            if length > 0:
                dx, dy = dx / length, dy / length
                arrow_x = pos2[0] - dx * 15
                arrow_y = pos2[1] - dy * 15
                
                fig.add_annotation(
                    x=arrow_x, y=arrow_y,
                    text="▶",
                    showarrow=False,
                    font=dict(size=10, color="#0466c8"),
                    opacity=0.8
                )
    
    # Draw location markers
    for location, details in locations.items():
        pos = details["position"]
        color = details["color"]
        emoji = details["emoji"]
        
        # Create a hexagon for each location
        r = 40  # hexagon radius
        hexagon_points = [(pos[0] + r * np.cos((np.pi / 3) * i), 
                          pos[1] + r * np.sin((np.pi / 3) * i)) 
                          for i in range(6)]
        
        path = f"M {hexagon_points[0][0]},{hexagon_points[0][1]} " + \
               " ".join(f"L {x},{y}" for x, y in hexagon_points[1:]) + " Z"
        
        # Highlight current location if provided
        is_current = current_location and location == current_location
        border_color = "#000000" if is_current else "#ffffff"
        border_width = 3 if is_current else 2
        
        # Draw the hexagon
        fig.add_shape(
            type="path", 
            path=path, 
            fillcolor=color, 
            line=dict(color=border_color, width=border_width)
        )
        
        # Add location name
        fig.add_annotation(
            x=pos[0], y=pos[1], 
            text=f"{location}", 
            showarrow=False, 
            font=dict(size=12, color="#ffffff", family="Arial", weight="bold")
        )
        
        # Add location emoji
        fig.add_annotation(
            x=pos[0], y=pos[1] - 15, 
            text=f"{emoji}", 
            showarrow=False, 
            font=dict(size=20)
        )
    
    # Add title and difficulty info
    if closed_roads:
        difficulty = "Easy" if len(closed_roads) == 1 else "Medium" if len(closed_roads) == 2 else "Hard"
        fig.add_annotation(
            x=150, y=40, 
            text=f"⛔️ {difficulty.upper()}: {len(closed_roads)} ROAD CLOSURE{'S' if len(closed_roads) > 1 else ''}", 
            showarrow=False, 
            font=dict(size=12, color="#e63946", weight="bold"), 
            bgcolor="rgba(255,255,255,0.8)", 
            borderpad=3
        )
    
    # Add distances info
    fig.add_annotation(
        x=650, y=40, 
        text="DISTANCES SHOWN IN CENTIMETERS", 
        showarrow=False, 
        font=dict(size=12, color="#333333", weight="bold"), 
        bgcolor="rgba(255,255,255,0.8)", 
        borderpad=3
    )
    
    # Add game title
    fig.add_annotation(
        x=400, y=370, 
        text="LOGISTICS RUSH", 
        showarrow=False, 
        font=dict(size=24, color="#333333", family="Arial Black"), 
        opacity=0.8
    )
    
    # Set layout properties
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