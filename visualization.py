# visualization.py

import streamlit as st
import plotly.graph_objects as go
import numpy as np
from config import LOCATIONS, ROAD_SEGMENTS
from routing import get_distance, calculate_segment_path

def visualize_map(player_route=None, optimal_route=None, constraints=None, show_roads=True, route_type="both"):
    fig = go.Figure()
    closed_roads = st.session_state.closed_roads if 'closed_roads' in st.session_state else []

    # Background grid
    fig.add_shape(type="rect", x0=0, y0=0, x1=800, y1=400, fillcolor="rgba(220, 240, 230, 0.6)",
                  line=dict(color="#2e8b57", width=3), layer="below")
    for i in range(0, 801, 100):
        fig.add_shape(type="line", x0=i, y0=0, x1=i, y1=400,
                      line=dict(color="rgba(0, 80, 40, 0.1)", width=1), layer="below")
    for i in range(0, 401, 100):
        fig.add_shape(type="line", x0=0, y0=i, x1=800, y1=i,
                      line=dict(color="rgba(0, 80, 40, 0.1)", width=1), layer="below")

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
    # Draw player route if available
    if player_route and len(player_route) > 1 and (route_type == "both" or route_type == "player"):
        for i in range(len(player_route) - 1):
            x0, y0 = LOCATIONS[player_route[i]]["position"]
            x1, y1 = LOCATIONS[player_route[i+1]]["position"]
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0, y1], mode='lines+markers',
                line=dict(color='#e63946', width=4),
                marker=dict(size=10, color='#e63946'),
                name=f'Your Route Step {i+1}',
                hoverinfo='text', hovertext=f"{player_route[i]} → {player_route[i+1]}"
            ))
    if optimal_route and len(optimal_route) > 1 and (route_type == "both" or route_type == "optimal"):
        for i in range(len(optimal_route) - 1):
            x0, y0 = LOCATIONS[optimal_route[i]]["position"]
            x1, y1 = LOCATIONS[optimal_route[i+1]]["position"]
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[y0, y1], mode='lines+markers',
                line=dict(color='#2a9d8f', width=4),
                marker=dict(size=10, color='#2a9d8f'),
                name=f'Optimal Route Step {i+1}',
                hoverinfo='text', hovertext=f"{optimal_route[i]} → {optimal_route[i+1]}"
            ))
    # Draw nodes for all locations
    for loc, props in LOCATIONS.items():
        x, y = props["position"]
        fig.add_trace(go.Scatter(
            x=[x], y=[y],
            mode='markers+text',
            marker=dict(color=props["color"], size=20),
            text=[props["emoji"]],
            textposition="middle center",
            hoverinfo='text',
            name=loc
        ))
    fig.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0))
    return fig
