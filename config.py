# config.py

# Locations with their visual properties (Central Hub removed)
LOCATIONS = {
    "Factory": {"position": (100, 100), "color": "#f87171", "emoji": "🏭"},
    "DHL Hub": {"position": (700, 100), "color": "#fbbf24", "emoji": "🚚"},
    "Shop": {"position": (700, 300), "color": "#60a5fa", "emoji": "🏪"},
    "Residence": {"position": (100, 300), "color": "#a78bfa", "emoji": "🏠"},
}

# Define all possible road segments (no Central Hub)
ROAD_SEGMENTS = [
    ("Factory", "DHL Hub"),
    ("Factory", "Shop"),
    ("Factory", "Residence"),
    ("DHL Hub", "Shop"),
    ("DHL Hub", "Residence"),
    ("Shop", "Residence"),
]

# Simplified graph of distances between locations (no Central Hub)
DISTANCES = {
    ("Factory", "DHL Hub"): 3.0,
    ("Factory", "Shop"): 4.5,
    ("Factory", "Residence"): 2.0,
    ("DHL Hub", "Shop"): 2.0,
    ("DHL Hub", "Residence"): 4.5,
    ("Shop", "Residence"): 3.0,
}

# Game modes with clear descriptions - unchanged
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

# Scoring weights for the unified game mode - unchanged
SCORING_WEIGHTS = {
    "Logistics Challenge": {
        "efficiency": 0.4,
        "delivery": 0.3,
        "constraints": 0.2,
        "time": 0.1
    }
}

# CSS styles for the application (unchanged for now, though Central Hub references could be removed if needed)
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
        color: #6b7280;
    }
    .card {
        background-color: white;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .status-bar {
        background-color: #f0f9ff;
        padding: 10px;
        border-radius: 6px;
        margin-bottom: 20px;
        text-align: center;
    }
    .location-button {
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        padding: 12px;
        width: 100%;
        margin-bottom: 10px;
        font-size: 1.1rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    .location-button:hover {
        background-color: #f3f4f6;
        border-color: #d1d5db;
    }
    .primary-button {
        background-color: #1a56db;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 12px;
        width: 100%;
        margin-bottom: 10px;
        font-size: 1.1rem;
    }
    .primary-button:hover {
        background-color: #1e40af;
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
    .expander-header {
        font-weight: bold;
        color: #1a56db;
    }
</style>
"""

# Centralized constraint checking function - unchanged
def check_constraints(route):
    """
    Check if a route follows the game's constraints.

    Returns True if constraints are met, False otherwise.
    """
    # Factory must come before Shop
    if "Factory" in route and "Shop" in route:
        f_idx = route.index("Factory")
        s_idx = route.index("Shop")
        if f_idx > s_idx:
            return False
            
    # DHL Hub must come before Residence
    if "DHL Hub" in route and "Residence" in route:
        d_idx = route.index("DHL Hub")
        r_idx = route.index("Residence")
        if d_idx > r_idx:
            return False
            
    return True