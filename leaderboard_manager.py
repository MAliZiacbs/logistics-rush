# leaderboard_manager.py
import json
import uuid
import pandas as pd
from io import StringIO
from datetime import datetime
from azure.storage.blob import ContentSettings
from azure_storage import get_blob_service_client

CONTAINER_NAME = "gamedata"
LEADERBOARD_BLOB_NAME = "leaderboard.csv"

def add_leaderboard_entry(player_info, game_results):
    """Add a new entry to the leaderboard and export it"""
    # Create new leaderboard entry with email included
    entry = {
        "player_id": str(uuid.uuid4()),
        "name": player_info.get("name", "Anonymous"),
        "email": player_info.get("email", ""),
        "company": player_info.get("company", ""),
        "score": game_results.get("score", 0),
        "time": game_results.get("time", 0),
        "efficiency": game_results.get("efficiency", 0),
        "difficulty": game_results.get("difficulty", 1),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "game_id": str(uuid.uuid4())[:8]
    }
    
    # Export to Azure
    export_entry_to_azure(entry)
    
    return entry

def fetch_leaderboard():
    """Fetch leaderboard data from Azure Blob Storage using authenticated access"""
    try:
        # Get authenticated blob service client
        blob_service_client = get_blob_service_client()
        if not blob_service_client:
            print("Failed to get blob service client")
            return []
            
        # Get container client
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        
        # Get blob client
        blob_client = container_client.get_blob_client(LEADERBOARD_BLOB_NAME)
        
        # Download the blob
        try:
            download_stream = blob_client.download_blob()
            csv_data = download_stream.readall().decode('utf-8')
            
            # Parse CSV
            df = pd.read_csv(StringIO(csv_data))
            leaderboard = df.to_dict('records')
            return leaderboard
        except Exception as e:
            print(f"Error downloading leaderboard blob: {e}")
            return []
    
    except Exception as e:
        print(f"Error fetching leaderboard: {e}")
        return []

def export_entry_to_azure(entry):
    """Export a single leaderboard entry to Azure for Databricks to process"""
    try:
        # Get blob service client
        blob_service_client = get_blob_service_client()
        if not blob_service_client:
            print("Failed to get blob service client")
            return False
            
        # Get container client
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        
        # Create a unique filename for this entry
        filename = f"leaderboard/{entry['player_id']}.json"
        
        # Convert entry to JSON string
        json_data = json.dumps(entry)
        
        # Upload to blob storage with content type
        blob_client = container_client.get_blob_client(filename)
        blob_client.upload_blob(
            json_data, 
            overwrite=True,
            content_settings=ContentSettings(content_type="application/json")
        )
        
        print(f"Successfully exported leaderboard entry to Azure: {filename}")
        return True
    except Exception as e:
        print(f"Error exporting leaderboard entry to Azure: {e}")
        return False

def get_leaderboard_csv():
    """Get leaderboard data as CSV string for download"""
    try:
        leaderboard = fetch_leaderboard()
        if not leaderboard:
            # Return empty CSV header if no data
            return "name,email,company,score,time,efficiency,difficulty,timestamp\n"
            
        df = pd.DataFrame(leaderboard)
        return df.to_csv(index=False)
    except Exception as e:
        print(f"Error generating CSV: {e}")
        # Return empty CSV header if error
        return "name,email,company,score,time,efficiency,difficulty,timestamp\n"