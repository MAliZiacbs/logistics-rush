# data_management.py

import streamlit as st
import json
import os
import datetime

def save_player_data(result_data):
    if not st.session_state.current_player:
        return
    player = st.session_state.current_player
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    leaderboard_entry = {
        "name": player["name"],
        "company": player["company"],
        "mode": st.session_state.game_mode,
        "time": result_data["time"],
        "efficiency": result_data["efficiency"],
        "score": result_data["score"],
        "timestamp": timestamp
    }
    if "delivery" in result_data:
        leaderboard_entry["delivery"] = result_data["delivery"]
    if "constraints" in result_data:
        leaderboard_entry["constraints"] = result_data["constraints"]
    st.session_state.leaderboard.append(leaderboard_entry)
    st.session_state.leaderboard.sort(key=lambda x: x["score"], reverse=True)
    if player["email"] not in st.session_state.players:
        st.session_state.players[player["email"]] = {
            "name": player["name"],
            "email": player["email"],
            "company": player["company"],
            "games": []
        }
    game_record = {
        "timestamp": timestamp,
        "mode": st.session_state.game_mode,
        "time": result_data["time"],
        "efficiency": result_data["efficiency"],
        "score": result_data["score"],
        "route": result_data["route"]
    }
    if "delivery" in result_data:
        game_record["delivery"] = result_data["delivery"]
    if "constraints" in result_data:
        game_record["constraints"] = result_data["constraints"]
    st.session_state.players[player["email"]]["games"].append(game_record)
    try:
        with open('player_data.json', 'w') as f:
            json.dump(st.session_state.players, f)
    except Exception as e:
        st.error(f"Error saving player data: {e}")

def export_player_data():
    if not st.session_state.players:
        return None
    rows = []
    for email, player in st.session_state.players.items():
        for game in player.get("games", []):
            entry = {
                "Name": player["name"],
                "Email": player["email"],
                "Company": player["company"],
                "Game Mode": game.get("mode", ""),
                "Time": game.get("time", 0),
                "Efficiency": game.get("efficiency", 0),
                "Score": game.get("score", 0),
                "Timestamp": game.get("timestamp", ""),
                "Route": " → ".join(game.get("route", []))
            }
            if game.get("mode") == "Logistics Challenge":
                entry["Delivery Success"] = game.get("delivery", 0)
                entry["Constraints Met"] = "Yes" if game.get("constraints", 0) > 0 else "No"
            rows.append(entry)
    return rows

def reset_leaderboard():
    st.session_state.leaderboard = []
    st.success("Leaderboard has been reset!")

def reset_all_data():
    if st.checkbox("I understand this will delete ALL player data"):
        st.session_state.players = {}
        st.session_state.leaderboard = []
        if os.path.exists("player_data.json"):
            try:
                os.remove("player_data.json")
            except Exception as e:
                st.error(f"Error removing data file: {e}")
        st.success("All data has been reset!")
