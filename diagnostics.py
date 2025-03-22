# diagnostics.py

import streamlit as st
import json
import time
import os
import datetime
from io import StringIO

def init_diagnostics():
    if 'diagnostics' not in st.session_state:
        st.session_state.diagnostics = {}
    if 'all_game_diagnostics' not in st.session_state:
        st.session_state.all_game_diagnostics = []
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
    if 'diagnostics' not in st.session_state:
        init_diagnostics()
    if 'route_changes' not in st.session_state.diagnostics:
        st.session_state.diagnostics['route_changes'] = []
    current_route = st.session_state.current_route.copy() if 'current_route' in st.session_state else []
    st.session_state.diagnostics['route_changes'].append({
        'timestamp': time.time(),
        'location': location,
        'success': success,
        'previous_route': current_route,
        'new_route': current_route + [location] if success else current_route
    })

def log_package_operation(operation_type, location, package_id, success=True, error=None):
    if 'diagnostics' not in st.session_state:
        init_diagnostics()
    if 'package_operations' not in st.session_state.diagnostics:
        st.session_state.diagnostics['package_operations'] = []
    package_info = None
    if 'packages' in st.session_state:
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
    if 'diagnostics' not in st.session_state:
        init_diagnostics()
    st.session_state.diagnostics['road_closures'] = closure_data

def log_error(error_type, details, traceback=None):
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
    if 'diagnostics' not in st.session_state:
        init_diagnostics()
    if 'optimal_route_data' not in st.session_state.diagnostics:
        st.session_state.diagnostics['optimal_route_data'] = []
    route_locations = []
    if route_data:
        if isinstance(route_data[0], dict):
            route_locations = [step['location'] for step in route_data]
        else:
            route_locations = route_data
    st.session_state.diagnostics['optimal_route_data'].append({
        'timestamp': time.time(),
        'route_valid': route_valid,
        'route': route_locations,
        'path': path_data,
        'distance': distance,
        'road_closures': st.session_state.closed_roads if 'closed_roads' in st.session_state else []
    })

def log_distance_calculation(from_loc, to_loc, distance, is_direct=True, detour_path=None):
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
    if 'diagnostics' not in st.session_state or not st.session_state.diagnostics:
        return
    diagnostics_record = st.session_state.diagnostics
    diagnostics_record['game_end'] = time.time()
    diagnostics_record['duration'] = diagnostics_record['game_end'] - diagnostics_record['current_game_start']
    if 'current_route' in st.session_state:
        diagnostics_record['player_route'] = st.session_state.current_route.copy()
    if 'game_results' in st.session_state:
        diagnostics_record['game_results'] = st.session_state.game_results.copy()
    if 'optimal_route' in st.session_state:
        diagnostics_record['optimal_route'] = st.session_state.optimal_route.copy()
    if 'optimal_path' in st.session_state:
        diagnostics_record['optimal_path'] = st.session_state.optimal_path.copy()
    if 'packages' in st.session_state:
        diagnostics_record['packages'] = st.session_state.packages.copy()
    if 'delivered_packages' in st.session_state:
        diagnostics_record['delivered_packages'] = st.session_state.delivered_packages.copy()
    st.session_state.all_game_diagnostics.append(diagnostics_record.copy())
    save_diagnostics_to_file()

def save_diagnostics_to_file():
    try:
        with open('game_diagnostics.json', 'w') as f:
            json.dump(st.session_state.all_game_diagnostics, f, indent=2)
    except Exception as e:
        st.error(f"Error saving diagnostics: {e}")

def get_diagnostic_report():
    if not st.session_state.all_game_diagnostics:
        return "No diagnostic data available."
    report = StringIO()
    report.write("=== LOGISTICS RUSH DIAGNOSTICS REPORT ===\n\n")
    report.write(f"Report Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.write(f"Number of Games: {len(st.session_state.all_game_diagnostics)}\n\n")
    for idx, game in enumerate(st.session_state.all_game_diagnostics):
        report.write(f"--- GAME #{idx+1} ---\n")
        report.write(f"Timestamp: {game.get('timestamp', 'Unknown')}\n")
        report.write(f"Duration: {game.get('duration', 0):.2f} seconds\n\n")
        report.write("GAME CONFIGURATION:\n")
        road_closures = game.get('road_closures', [])
        report.write(f"Road Closures ({len(road_closures)}):\n")
        for closure in road_closures:
            report.write(f"  {closure[0]} ↔️ {closure[1]}\n")
        packages = game.get('packages', [])
        report.write(f"\nPackages ({len(packages)}):\n")
        for pkg in packages:
            report.write(f"  #{pkg['id']}: {pkg['pickup']} → {pkg['delivery']}\n")
        if 'game_results' in game:
            results = game['game_results']
            report.write("\nGAME RESULTS:\n")
            report.write(f"Score: {results.get('score', 0)}\n")
            report.write(f"Efficiency: {results.get('efficiency', 0)}%\n")
            report.write(f"Player Distance: {results.get('player_distance', 0):.1f} cm\n")
            report.write(f"Optimal Distance: {results.get('optimal_distance', 0):.1f} cm\n")
            report.write(f"Found Better Route: {results.get('found_better_route', False)}\n")
        player_route = game.get('player_route', [])
        report.write("\nPLAYER ROUTE:\n")
        report.write(" → ".join(player_route) + "\n")
        report.write("\n---\n\n")
    return report.getvalue()

def render_diagnostics_tab():
    st.subheader("Game Diagnostics")
    if not st.session_state.all_game_diagnostics:
        st.info("No diagnostic data available. Play a game to generate diagnostics.")
        return
    if len(st.session_state.all_game_diagnostics) > 1:
        game_options = [f"Game #{i+1} - {game.get('timestamp', 'Unknown')}" for i, game in enumerate(st.session_state.all_game_diagnostics)]
        selected_game_idx = st.selectbox("Select Game", range(len(game_options)), format_func=lambda x: game_options[x])
        selected_game = st.session_state.all_game_diagnostics[selected_game_idx]
    else:
        selected_game = st.session_state.all_game_diagnostics[0]
    st.markdown("### Game Overview")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Time:** {selected_game.get('timestamp', 'Unknown')}")
        st.markdown(f"**Duration:** {selected_game.get('duration', 0):.2f} seconds")
    with col2:
        if 'game_results' in selected_game:
            st.markdown(f"**Score:** {selected_game['game_results'].get('score', 0)}")
            st.markdown(f"**Efficiency:** {selected_game['game_results'].get('efficiency', 0)}%")
    st.markdown("### Road Closures")
    road_closures = selected_game.get('road_closures', [])
    if road_closures:
        for closure in road_closures:
            st.markdown(f"⛔️ {closure[0]} ↔️ {closure[1]}")
    else:
        st.markdown("No road closures recorded.")
    st.markdown("### Player Route")
    player_route = selected_game.get('player_route', [])
    st.code(" → ".join(player_route))
    st.markdown("### Download Diagnostics")
    report = get_diagnostic_report()
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(label="Download as Text Report", data=report, file_name="logistics_rush_diagnostics.txt", mime="text/plain")
    with col2:
        json_data = json.dumps(st.session_state.all_game_diagnostics, indent=2)
        st.download_button(label="Download as JSON", data=json_data, file_name="logistics_rush_diagnostics.json", mime="application/json")
    if st.button("Clear All Diagnostic Data"):
        st.session_state.all_game_diagnostics = []
        if os.path.exists('game_diagnostics.json'):
            try:
                os.remove('game_diagnostics.json')
                st.success("All diagnostic data has been cleared.")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error removing diagnostic file: {e}")
