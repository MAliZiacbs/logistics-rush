# config.py

# Locations with their visual properties
LOCATIONS = {
    "Warehouse": {"position": (100, 100), "color": "#f87171", "emoji": "🏭"},
    "Distribution Center": {"position": (700, 100), "color": "#fbbf24", "emoji": "🚚"},
    "Shop": {"position": (700, 300), "color": "#60a5fa", "emoji": "🏪"},
    "Home": {"position": (100, 300), "color": "#4ade80", "emoji": "🏠"},
}

# Define all possible road segments
ROAD_SEGMENTS = [
    ("Warehouse", "Distribution Center"),
    ("Warehouse", "Shop"),
    ("Warehouse", "Home"),
    ("Distribution Center", "Shop"),
    ("Distribution Center", "Home"),
    ("Shop", "Home"),
]

# Distances in centimeters (based on real measurements)
DISTANCES = {
    ("Warehouse", "Distribution Center"): 302,
    ("Warehouse", "Shop"): 354,
    ("Warehouse", "Home"): 183,
    ("Distribution Center", "Shop"): 183,
    ("Distribution Center", "Home"): 354,
    ("Shop", "Home"): 302,
}

GAME_MODES = {
    "Logistics Challenge": {
        "description": "Master all logistics challenges in one comprehensive experience",
        "instructions": """
        1. Start at the Warehouse
        2. Navigate through the network with random road closures
        3. Pick up and deliver packages along your route
        4. Follow sequence constraints (Warehouse before Shop, Distribution Center before Home)
        5. Complete your mission as efficiently as possible

        Your score depends on efficiency (40%), successful deliveries (30%),
        following constraints (20%), and time (10%).
        """
    }
}

SCORING_WEIGHTS = {
    "Logistics Challenge": {
        "efficiency": 0.4,
        "delivery": 0.3,
        "constraints": 0.2,
        "time": 0.1
    }
}

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
    /* Additional CSS styles… */
</style>
"""

def check_constraints(route):
    """
    Check if a route follows the game's constraints.
    Warehouse must come before Shop; Distribution Center before Home.
    """
    if "Warehouse" in route and "Shop" in route:
        if route.index("Warehouse") > route.index("Shop"):
            return False
    if "Distribution Center" in route and "Home" in route:
        if route.index("Distribution Center") > route.index("Home"):
            return False
    return True
