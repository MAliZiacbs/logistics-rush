# Game constants and configuration

# Locations with their visual properties
LOCATIONS = {
    "Factory": {"position": (100, 100), "color": "#f87171", "emoji": "🏭"},
    "DHL Hub": {"position": (700, 100), "color": "#fbbf24", "emoji": "🚚"},
    "Shop": {"position": (700, 300), "color": "#60a5fa", "emoji": "🏪"},
    "Residence": {"position": (100, 300), "color": "#a78bfa", "emoji": "🏠"},
    "Central Hub": {"position": (400, 200), "color": "#374151", "emoji": "🔄"}
}

# Define all possible road segments
ROAD_SEGMENTS = [
    ("Factory", "DHL Hub"),
    ("Factory", "Shop"),
    ("Factory", "Residence"),
    ("Factory", "Central Hub"),
    ("DHL Hub", "Shop"),
    ("DHL Hub", "Residence"),
    ("DHL Hub", "Central Hub"),
    ("Shop", "Residence"),
    ("Shop", "Central Hub"),
    ("Residence", "Central Hub"),
]

# Simplified graph of distances between locations
DISTANCES = {
    ("Factory", "DHL Hub"): 3.0,
    ("Factory", "Shop"): 4.5,
    ("Factory", "Residence"): 2.0,
    ("Factory", "Central Hub"): 2.0,
    ("DHL Hub", "Shop"): 2.0,
    ("DHL Hub", "Residence"): 4.5,
    ("DHL Hub", "Central Hub"): 2.0,
    ("Shop", "Residence"): 3.0,
    ("Shop", "Central Hub"): 2.0,
    ("Residence", "Central Hub"): 2.0,
}

# Game modes with clear descriptions - now just a single, combined mode
GAME_MODES = {
    "Logistics Challenge": {
        "description": "Master all logistics challenges in one comprehensive experience",
        "instructions": """
        1. Start at the Factory
        2. Navigate through the network with random road closures
        3. Pick up and deliver packages along your route
        4. Follow sequence constraints (Factory before Shop, DHL Hub before Residence)
        5. Complete your mission as efficiently as possible
        
        Your score depends on efficiency (40%), successful deliveries (30%), 
        following constraints (20%), and time (10%).
        """
    }
}

# Scoring weights for the unified game mode
SCORING_WEIGHTS = {
    "Logistics Challenge": {
        "efficiency": 0.4,
        "delivery": 0.3,
        "constraints": 0.2,
        "time": 0.1
    }
}

# CSS styles for the application
STYLES = """
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 1rem;
        color: #1a56db;
    }
    .subtitle {
        text-align: center;
        margin-bottom: 2rem;
        font-size: 1.2rem;
    }
    .card {
        background-color: white;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .location-button {
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        padding: 10px;
        width: 100%;
        margin-bottom: 8px;
        cursor: pointer;
        transition: all 0.2s;
        text-align: center;
    }
    .location-button:hover {
        background-color: #f3f4f6;
        border-color: #d1d5db;
    }
    .progress-bar {
        height: 10px;
        background-color: #e5e7eb;
        border-radius: 5px;
        margin: 10px 0;
    }
    .progress-fill {
        height: 100%;
        border-radius: 5px;
        background-color: #1a56db;
    }
    .package-button {
        background-color: #10B981;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px;
        width: 100%;
        margin-bottom: 8px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .package-button:hover {
        background-color: #059669;
    }
    .road-closure-alert {
        background-color: #EF4444;
        color: white;
        border-radius: 6px;
        padding: 10px;
        margin-bottom: 12px;
        font-weight: bold;
    }
    .package-info {
        background-color: #f3f4f6;
        border-left: 4px solid #10B981;
        padding: 10px;
        margin-bottom: 12px;
        border-radius: 4px;
    }
    .constraints-info {
        background-color: #f3f4f6;
        border-left: 4px solid #6366F1;
        padding: 10px;
        margin-bottom: 12px;
        border-radius: 4px;
    }
    .challenge-summary {
        background-color: #f9fafb;
        border-radius: 6px;
        padding: 15px;
        margin: 15px 0;
    }
    .score-breakdown {
        background-color: #f0f9ff;
        border-radius: 6px;
        padding: 10px;
        margin-top: 10px;
    }
</style>
"""