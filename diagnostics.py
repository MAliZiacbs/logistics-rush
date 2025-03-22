# diagnostics.py

import streamlit as st
import pandas as pd
import json
import time
import os
import datetime
from io import StringIO

def init_diagnostics():
    """Initialize diagnostics tracking in session state"""
    if 'diagnostics' not in st.session_state:
        st.session_state.diagnostics = {}
    
    if 'all_game_diagnostics' not in st.session_state:
        st.session_state.all_game_diagnostics = []
    
    # Start a new diagnostic record for this game
    if st.session_state.game_active and 'current_game_start' not in st.session_state.diagnostics:
        st.session_state.diagnostics = {
            'current_game_start': time.time(),
            'game_id': len(st.session_state.all_game_diagnostics) + 1,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'events': [],
            'route_changes': [],
            'package_operations': [],
            'road_closures': [],
            'errors': [],
            'optimal_route_data': [],
            'distance_calculations': []
        }

def log_event(event_type, details):
    """Log a general event with timestamp"""
    if 'diagnostics' not in st.session_state:
        init_diagnostics()
    
    if 'events' not in st.session_state.diagnostics:
        st.session_state.diagnostics['events'] = []
    
    st.session_state.diagnostics['events'].append({
        'timestamp': time.time(),
        'type': event_type,
        'details': details
    })

def log_route_change(location, success):
    """Log a route change with detailed information"""
    if 'diagnostics' not in st.session_state:
        init_diagnostics()
    
    if 'route_changes' not in st.session_state.diagnostics:
        st.session_state.diagnostics['route_changes'] = []
    
    current_route = st.session_state.current_route.copy() if hasattr(st.session_state, 'current_route') else []
    
    st.session_state.diagnostics['route_changes'].append({
        'timestamp': time.time(),
        'location': location,
        'success': success,
        'previous_route': current_route,
        'new_route': current_route + [location] if success else current_route
    })

def log_package_operation(operation_type, location, package_id, success=True, error=None):
    """Log a package pickup or delivery operation"""
    if 'diagnostics' not in st.session_state:
        init_diagnostics()
    
    if 'package_operations' not in st.session_state.diagnostics:
        st.session_state.diagnostics['package_operations'] = []
    
    package_info = None
    if hasattr(st.session_state, 'packages'):
        for pkg in st.session_state.packages:
            if pkg['id'] == package_id:
                package_info = {
                    'id': pkg['id'],
                    'pickup': pkg['pickup'],
                    'delivery': pkg['delivery'],
                    'status': pkg['status']
                }
                break
    
    st.session_state.diagnostics['package_operations'].append({
        'timestamp': time.time(),
        'operation': operation_type,
        'location': location,
        'package_id': package_id,
        'success': success,
        'package_info': package_info,
        'error': error
    })

def log_road_closures(closure_data):
    """Log road closure information"""
    if 'diagnostics' not in st.session_state:
        init_diagnostics()
    
    st.session_state.diagnostics['road_closures'] = closure_data

def log_error(error_type, details, traceback=None):
    """Log an error that occurred during gameplay"""
    if 'diagnostics' not in st.session_state:
        init_diagnostics()
    
    if 'errors' not in st.session_state.diagnostics:
        st.session_state.diagnostics['errors'] = []
    
    st.session_state.diagnostics['errors'].append({
        'timestamp': time.time(),
        'type': error_type,
        'details': details,
        'traceback': traceback
    })

def log_optimal_route_data(route_data, path_data, distance, route_valid=True):
    """Log optimal route calculation details"""
    if 'diagnostics' not in st.session_state:
        init_diagnostics()
    
    if 'optimal_route_data' not in st.session_state.diagnostics:
        st.session_state.diagnostics['optimal_route_data'] = []
    
    # Extract locations from route_data (which might be a list of dicts)
    route_locations = []
    if route_data:
        if isinstance(route_data[0], dict):
            route_locations = [step['location'] for step in route_data]
        else:
            route_locations = route_data
    
    # Record all relevant details
    st.session_state.diagnostics['optimal_route_data'].append({
        'timestamp': time.time(),
        'route_valid': route_valid,
        'route': route_locations,
        'path': path_data,
        'distance': distance,
        'road_closures': st.session_state.closed_roads if hasattr(st.session_state, 'closed_roads') else []
    })

def log_distance_calculation(from_loc, to_loc, distance, is_direct=True, detour_path=None):
    """Log individual distance calculations for debugging"""
    if 'diagnostics' not in st.session_state:
        init_diagnostics()
    
    if 'distance_calculations' not in st.session_state.diagnostics:
        st.session_state.diagnostics['distance_calculations'] = []
    
    st.session_state.diagnostics['distance_calculations'].append({
        'timestamp': time.time(),
        'from': from_loc,
        'to': to_loc,
        'distance': distance,
        'is_direct': is_direct,
        'detour_path': detour_path
    })

def catch_and_log_exceptions(func):
    """Decorator to catch and log exceptions in functions"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            import traceback
            error_tb = traceback.format_exc()
            log_error(f"Error in {func.__name__}", str(e), error_tb)
            raise
    return wrapper

def finalize_game_diagnostics():
    """Finalize the current game's diagnostics and add to history"""
    if 'diagnostics' not in st.session_state or not st.session_state.diagnostics:
        return
    
    # Add additional summary data
    diagnostics = st.session_state.diagnostics
    diagnostics['game_end'] = time.time()
    diagnostics['duration'] = diagnostics['game_end'] - diagnostics['current_game_start']
    
    # Add player route and score information
    if hasattr(st.session_state, 'current_route'):
        diagnostics['player_route'] = st.session_state.current_route.copy()
    
    if hasattr(st.session_state, 'game_results'):
        diagnostics['game_results'] = st.session_state.game_results.copy()
    
    if hasattr(st.session_state, 'optimal_route'):
        diagnostics['optimal_route'] = st.session_state.optimal_route.copy() 
    
    if hasattr(st.session_state, 'optimal_path'):
        diagnostics['optimal_path'] = st.session_state.optimal_path.copy()
    
    if hasattr(st.session_state, 'packages'):
        diagnostics['packages'] = st.session_state.packages.copy()
    
    if hasattr(st.session_state, 'delivered_packages'):
        diagnostics['delivered_packages'] = st.session_state.delivered_packages.copy()
    
    # Clone and add to history
    st.session_state.all_game_diagnostics.append(diagnostics.copy())
    
    # Save to file
    save_diagnostics_to_file()

def save_diagnostics_to_file():
    """Save all diagnostics to a JSON file"""
    try:
        with open('game_diagnostics.json', 'w') as f:
            json.dump(st.session_state.all_game_diagnostics, f, indent=2)
    except Exception as e:
        st.error(f"Error saving diagnostics: {e}")

def get_diagnostic_report():
    """Generate a diagnostic report for display and download"""
    if not st.session_state.all_game_diagnostics:
        return "No diagnostic data available."
    
    # Create a text report with all game diagnostics
    report = StringIO()
    report.write("=== LOGISTICS RUSH DIAGNOSTICS REPORT ===\n\n")
    report.write(f"Report Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.write(f"Number of Games: {len(st.session_state.all_game_diagnostics)}\n\n")
    
    for idx, game in enumerate(st.session_state.all_game_diagnostics):
        report.write(f"--- GAME #{idx+1} ---\n")
        report.write(f"Timestamp: {game.get('timestamp', 'Unknown')}\n")
        report.write(f"Duration: {game.get('duration', 0):.2f} seconds\n\n")
        
        # Game Configuration
        report.write("GAME CONFIGURATION:\n")
        road_closures = game.get('road_closures', [])
        report.write(f"Road Closures ({len(road_closures)}):\n")
        for closure in road_closures:
            report.write(f"  {closure[0]} ↔️ {closure[1]}\n")
        
        packages = game.get('packages', [])
        report.write(f"\nPackages ({len(packages)}):\n")
        for pkg in packages:
            report.write(f"  #{pkg['id']}: {pkg['pickup']} → {pkg['delivery']}\n")
        
        # Results
        if 'game_results' in game:
            results = game['game_results']
            report.write("\nGAME RESULTS:\n")
            report.write(f"Score: {results.get('score', 0)}\n")
            report.write(f"Efficiency: {results.get('efficiency', 0)}%\n")
            report.write(f"Player Distance: {results.get('player_distance', 0):.1f} cm\n")
            report.write(f"Optimal Distance: {results.get('optimal_distance', 0):.1f} cm\n")
            report.write(f"Found Better Route: {results.get('found_better_route', False)}\n")
        
        # Route Information
        player_route = game.get('player_route', [])
        report.write("\nPLAYER ROUTE:\n")
        report.write(" → ".join(player_route) + "\n")
        
        # Optimal Route Data
        report.write("\nOPTIMAL ROUTE CALCULATIONS:\n")
        for idx, calc in enumerate(game.get('optimal_route_data', [])):
            report.write(f"Calculation #{idx+1}:\n")
            report.write(f"  Valid: {calc.get('route_valid', False)}\n")
            report.write(f"  Distance: {calc.get('distance', 0):.1f} cm\n")
            if 'route' in calc:
                route_str = " → ".join(calc['route']) if calc['route'] else "None"
                report.write(f"  Route: {route_str}\n")
            if 'path' in calc:
                path_str = " → ".join(calc['path']) if calc['path'] else "None"
                report.write(f"  Path: {path_str}\n")
            report.write("\n")
        
        # Package Operations
        report.write("PACKAGE OPERATIONS:\n")
        for op in game.get('package_operations', []):
            report.write(f"  {op.get('operation', 'Unknown')}: Package #{op.get('package_id', 'Unknown')} at {op.get('location', 'Unknown')} - {'Success' if op.get('success', False) else 'Failed'}\n")
        
        # Errors
        errors = game.get('errors', [])
        if errors:
            report.write("\nERRORS:\n")
            for error in errors:
                report.write(f"  {error.get('type', 'Unknown')}: {error.get('details', 'No details')}\n")
        
        report.write("\n" + "="*50 + "\n\n")
    
    return report.getvalue()

def render_diagnostics_tab():
    """Render the diagnostics tab UI"""
    st.subheader("Game Diagnostics")
    
    if not st.session_state.all_game_diagnostics:
        st.info("No diagnostic data is available yet. Play a game to generate diagnostics.")
        return
    
    # Game selector
    if len(st.session_state.all_game_diagnostics) > 1:
        game_options = [f"Game #{i+1} - {game.get('timestamp', 'Unknown')}" 
                        for i, game in enumerate(st.session_state.all_game_diagnostics)]
        selected_game_idx = st.selectbox("Select Game", range(len(game_options)), 
                                        format_func=lambda x: game_options[x])
        selected_game = st.session_state.all_game_diagnostics[selected_game_idx]
    else:
        selected_game = st.session_state.all_game_diagnostics[0]
    
    # Game overview
    st.markdown("### Game Overview")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Time:** {selected_game.get('timestamp', 'Unknown')}")
        st.markdown(f"**Duration:** {selected_game.get('duration', 0):.2f} seconds")
    with col2:
        if 'game_results' in selected_game:
            st.markdown(f"**Score:** {selected_game['game_results'].get('score', 0)}")
            st.markdown(f"**Efficiency:** {selected_game['game_results'].get('efficiency', 0)}%")
    
    # Road Closures
    st.markdown("### Road Closures")
    road_closures = selected_game.get('road_closures', [])
    if road_closures:
        for closure in road_closures:
            st.markdown(f"⛔️ {closure[0]} ↔️ {closure[1]}")
    else:
        st.markdown("No road closures recorded.")
    
    # Routes
    st.markdown("### Routes")
    tab1, tab2 = st.tabs(["Player Route", "Optimal Route"])
    
    with tab1:
        player_route = selected_game.get('player_route', [])
        if player_route:
            route_text = " → ".join(player_route)
            st.code(route_text)
            
            # Calculate distances
            if len(player_route) > 1:
                total_distance = 0
                distance_details = []
                
                for i in range(len(player_route) - 1):
                    from_loc = player_route[i]
                    to_loc = player_route[i+1]
                    
                    # Find distance in calculations log
                    segment_distance = None
                    is_direct = True
                    detour = None
                    
                    for calc in selected_game.get('distance_calculations', []):
                        if calc.get('from') == from_loc and calc.get('to') == to_loc:
                            segment_distance = calc.get('distance')
                            is_direct = calc.get('is_direct', True)
                            detour = calc.get('detour_path')
                            break
                    
                    if segment_distance is None or segment_distance == float('inf'):
                        distance_details.append(f"{from_loc} → {to_loc}: ∞ (No valid path)")
                    else:
                        total_distance += segment_distance
                        route_type = "Direct" if is_direct else f"Detour via {' → '.join(detour) if detour else 'unknown'}"
                        distance_details.append(f"{from_loc} → {to_loc}: {segment_distance:.1f} cm ({route_type})")
                
                st.markdown(f"**Total Distance:** {total_distance:.1f} cm")
                with st.expander("Distance Details"):
                    for detail in distance_details:
                        st.markdown(f"- {detail}")
        else:
            st.markdown("No player route data available.")
    
    with tab2:
        optimal_path = selected_game.get('optimal_path', [])
        if optimal_path:
            path_text = " → ".join(optimal_path)
            st.code(path_text)
            
            # Show distance if available
            if 'game_results' in selected_game:
                st.markdown(f"**Optimal Distance:** {selected_game['game_results'].get('optimal_distance', 0):.1f} cm")
            
            # Show route calculation details
            with st.expander("Optimal Route Calculation Details"):
                for idx, calc in enumerate(selected_game.get('optimal_route_data', [])):
                    st.markdown(f"**Calculation #{idx+1}**")
                    st.markdown(f"Valid: {calc.get('route_valid', False)}")
                    st.markdown(f"Distance: {calc.get('distance', 0):.1f} cm")
                    if 'route' in calc and calc['route']:
                        st.markdown(f"Route: {' → '.join(calc['route'])}")
                    if 'path' in calc and calc['path']:
                        st.markdown(f"Path: {' → '.join(calc['path'])}")
                    st.markdown("---")
        else:
            st.markdown("No optimal route data available.")
    
    # Packages
    st.markdown("### Package Information")
    packages = selected_game.get('packages', [])
    delivered = selected_game.get('delivered_packages', [])
    
    if packages:
        package_data = []
        for pkg in packages:
            pkg_id = pkg['id']
            pickup = pkg['pickup']
            delivery = pkg['delivery']
            
            # Check if delivered
            is_delivered = any(d['id'] == pkg_id for d in delivered)
            status = "Delivered" if is_delivered else pkg['status'].capitalize()
            
            package_data.append({
                "ID": pkg_id,
                "Pickup": pickup,
                "Delivery": delivery,
                "Status": status
            })
        
        package_df = pd.DataFrame(package_data)
        st.dataframe(package_df)
        
        # Package operations
        st.markdown("#### Package Operations Log")
        package_ops = selected_game.get('package_operations', [])
        if package_ops:
            for op in package_ops:
                status = "✅" if op.get('success', False) else "❌"
                op_type = op.get('operation', 'Unknown').capitalize()
                pkg_id = op.get('package_id', 'Unknown')
                location = op.get('location', 'Unknown')
                st.markdown(f"{status} {op_type} Package #{pkg_id} at {location}")
        else:
            st.markdown("No package operations recorded.")
    else:
        st.markdown("No package data available.")
    
    # Errors
    errors = selected_game.get('errors', [])
    if errors:
        st.markdown("### Errors")
        for error in errors:
            error_type = error.get('type', 'Unknown Error')
            details = error.get('details', 'No details available')
            st.error(f"**{error_type}**: {details}")
            if 'traceback' in error and error['traceback']:
                with st.expander("Error Traceback"):
                    st.code(error['traceback'])
    
    # Download button for all diagnostics
    st.markdown("### Download Diagnostics")
    report = get_diagnostic_report()
    
    # Two download options
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download as Text Report",
            data=report,
            file_name="logistics_rush_diagnostics.txt",
            mime="text/plain"
        )
    
    with col2:
        # JSON download option
        json_data = json.dumps(st.session_state.all_game_diagnostics, indent=2)
        st.download_button(
            label="Download as JSON",
            data=json_data,
            file_name="logistics_rush_diagnostics.json",
            mime="application/json"
        )
    
    # Option to clear diagnostics
    if st.button("Clear All Diagnostic Data", type="secondary"):
        st.session_state.all_game_diagnostics = []
        if os.path.exists('game_diagnostics.json'):
            try:
                os.remove('game_diagnostics.json')
                st.success("All diagnostic data has been cleared.")
                st.rerun()
            except Exception as e:
                st.error(f"Error removing diagnostic file: {e}")