# insights_fetcher.py
import json
from azure_storage import get_blob_service_client

CONTAINER_NAME = "gamedata"
INSIGHTS_BLOB_NAME = "insights.json"

def get_insights():
    """Fetch insights from Azure Blob Storage using authenticated access"""
    try:
        # Get authenticated blob service client
        blob_service_client = get_blob_service_client()
        if not blob_service_client:
            print("Failed to get blob service client")
            return get_default_insights()
            
        # Get container client
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        
        # Get blob client
        blob_client = container_client.get_blob_client(INSIGHTS_BLOB_NAME)
        
        # Download the blob
        try:
            download_stream = blob_client.download_blob()
            insights_data = download_stream.readall()
            
            # Parse JSON
            insights = json.loads(insights_data)
            return insights
        except Exception as e:
            print(f"Error downloading insights blob: {e}")
            return get_default_insights()
    
    except Exception as e:
        print(f"Error fetching insights: {e}")
        return get_default_insights()

def get_default_insights():
    """Return default insights if unable to fetch from Azure"""
    return {
        "best_routes": [
            {"difficulty": 1, "route": "Warehouse → Home → Shop → Distribution Center", "avg_score": 85.5},
            {"difficulty": 2, "route": "Warehouse → Distribution Center → Home → Shop", "avg_score": 78.2},
            {"difficulty": 3, "route": "Warehouse → Distribution Center → Shop → Home", "avg_score": 72.8}
        ],
        "common_violations": [
            {"constraint": "('Warehouse', 'Shop')", "frequency": 5},
            {"constraint": "('Distribution Center', 'Home')", "frequency": 3}
        ],
        "statistics": {
            "total_games": 0,
            "avg_score": 0,
            "avg_efficiency": 0,
            "avg_time": 0
        },
        "last_updated": "2025-03-24 12:00:00"
    }