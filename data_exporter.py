# data_exporter.py
import json
import os
import uuid
from datetime import datetime
import streamlit as st
from azure.storage.blob import ContentSettings
from azure_storage import get_blob_service_client

CONTAINER_NAME = "gamedata"

def export_game_results(game_results):
    """Export game results to Azure Blob Storage"""
    # Always save locally as fallback (for local development)
    try:
        local_export(game_results)
    except:
        pass  # Ignore local export failures in cloud
    
    # Try to export to Azure
    try:
        blob_service_client = get_blob_service_client()
        if not blob_service_client:
            print("Failed to get blob service client")
            return False
            
        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        player_name = game_results.get("player_name", "anonymous")
        filename = f"{timestamp}_{player_name}_{str(uuid.uuid4())[:8]}.json"
            
        # Get container client
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        
        # Convert results to JSON string
        json_data = json.dumps(game_results)
        
        # Upload to blob storage with content type
        blob_client = container_client.get_blob_client(filename)
        blob_client.upload_blob(
            json_data, 
            content_settings=ContentSettings(content_type="application/json")
        )
        
        print(f"Successfully exported game results to Azure: {filename}")
        return True
    except Exception as e:
        print(f"Error exporting to Azure: {e}")
        return False

def local_export(game_results):
    """Export game results locally as backup (for local development)"""
    # Only used during local development
    # Create exports directory if it doesn't exist
    if not os.path.exists("exports"):
        os.makedirs("exports")
        
    # Create unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    player_name = game_results.get("player_name", "anonymous")
    filename = f"exports/{timestamp}_{player_name}.json"
    
    # Write to file
    with open(filename, 'w') as f:
        json.dump(game_results, f)
    
    print(f"Exported game results locally to: {filename}")