import streamlit as st
import json
import os
import datetime

def save_player_data(result_data):
    """Save player game data to session state and JSON file"""
    if not st.session_state.current_player:
        return
        
    player = st.session_state.current_player
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Add to leaderboard
    st.session_state.leaderboard.append({
        "name": player["name"],
        "company": player["company"],
        "mode": st.session_state.game_mode,
        "time": result_data["time"],
        "efficiency": result_data["efficiency"],
        "score": result_data["score"],
        "timestamp": timestamp
    })
    
    # Sort leaderboard by score (highest first)
    st.session_state.leaderboard.sort(key=lambda x: x["score"], reverse=True)

    # Add to player profile
    if player["email"] not in st.session_state.players:
        st.session_state.players[player["email"]] = {
            "name": player["name"],
            "email": player["email"],
            "company": player["company"],
            "games": []
        }
    
    # Add the game data to player profile
    st.session_state.players[player["email"]]["games"].append({
        "timestamp": timestamp,
        "mode": st.session_state.game_mode,
        "time": result_data["time"],
        "efficiency": result_data["efficiency"],
        "score": result_data["score"],
        "route": result_data["route"]
    })
    
    # Save to file
    try:
        with open('player_data.json', 'w') as f:
            json.dump(st.session_state.players, f)
    except Exception as e:
        st.error(f"Error saving player data: {e}")

def load_player_data():
    """Load player data from file or initialize if not exists"""
    try:
        if os.path.exists('player_data.json'):
            with open('player_data.json', 'r') as f:
                if os.path.getsize('player_data.json') > 0:
                    st.session_state.players = json.load(f)
                else:
                    st.session_state.players = {}
        else:
            st.session_state.players = {}
    except Exception as e:
        st.error(f"Error loading player data: {e}")
        st.session_state.players = {}
    
    # Initialize leaderboard from player data if needed
    if 'leaderboard' not in st.session_state or not st.session_state.leaderboard:
        st.session_state.leaderboard = []
        for email, player in st.session_state.players.items():
            for game in player.get("games", []):
                st.session_state.leaderboard.append({
                    "name": player["name"],
                    "company": player["company"],
                    "mode": game.get("mode", "Unknown"),
                    "time": game.get("time", 0),
                    "efficiency": game.get("efficiency", 0),
                    "score": game.get("score", 0),
                    "timestamp": game.get("timestamp", "")
                })
        # Sort by score
        st.session_state.leaderboard.sort(key=lambda x: x["score"], reverse=True)

def export_player_data():
    """Export player data for download"""
    if not st.session_state.players:
        return None
        
    rows = []
    for email, player in st.session_state.players.items():
        for game in player.get("games", []):
            rows.append({
                "Name": player["name"],
                "Email": player["email"],
                "Company": player["company"],
                "Game Mode": game.get("mode", ""),
                "Time": game.get("time", 0),
                "Efficiency": game.get("efficiency", 0),
                "Score": game.get("score", 0),
                "Timestamp": game.get("timestamp", ""),
                "Route": " → ".join(game.get("route", []))
            })
    
    return rows

def get_player_statistics():
    """Get aggregated statistics about players and their performance"""
    if not st.session_state.players:
        return None
        
    stats = {
        "total_players": len(st.session_state.players),
        "total_games": sum(len(player.get("games", [])) for player in st.session_state.players.values()),
        "mode_counts": {},
        "company_counts": {},
        "average_scores": {},
        "best_players": {}
    }
    
    # Collect all games
    all_games = []
    for email, player in st.session_state.players.items():
        for game in player.get("games", []):
            game_copy = game.copy()
            game_copy["player_name"] = player["name"]
            game_copy["company"] = player["company"]
            all_games.append(game_copy)
    
    # Get mode counts
    for game in all_games:
        mode = game.get("mode", "Unknown")
        if mode not in stats["mode_counts"]:
            stats["mode_counts"][mode] = 0
        stats["mode_counts"][mode] += 1
        
    # Get company counts
    for player in st.session_state.players.values():
        company = player.get("company", "Unknown")
        if company not in stats["company_counts"]:
            stats["company_counts"][company] = 0
        stats["company_counts"][company] += 1
        
    # Calculate average scores per mode
    for mode in stats["mode_counts"].keys():
        mode_games = [g for g in all_games if g.get("mode") == mode]
        if mode_games:
            stats["average_scores"][mode] = sum(g.get("score", 0) for g in mode_games) / len(mode_games)
        
    # Find best players per mode
    for mode in stats["mode_counts"].keys():
        mode_games = [g for g in all_games if g.get("mode") == mode]
        if mode_games:
            best_game = max(mode_games, key=lambda g: g.get("score", 0))
            stats["best_players"][mode] = {
                "name": best_game["player_name"],
                "company": best_game.get("company", ""),
                "score": best_game.get("score", 0),
                "time": best_game.get("time", 0)
            }
    
    return stats

def reset_leaderboard():
    """Reset the leaderboard data"""
    st.session_state.leaderboard = []
    st.success("Leaderboard has been reset!")

def reset_all_data():
    """Reset all player data and leaderboard"""
    if st.checkbox("I understand this will delete ALL player data"):
        st.session_state.players = {}
        st.session_state.leaderboard = []
        if os.path.exists("player_data.json"):
            try:
                os.remove("player_data.json")
            except Exception as e:
                st.error(f"Error removing data file: {e}")
        st.success("All data has been reset!")