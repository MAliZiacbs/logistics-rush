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

# Game modes with clear descriptions
GAME_MODES = {
    "Speed Run": {
        "description": "Visit all locations as quickly as possible",
        "instructions": """
        1. Start at the highlighted location
        2. Visit all 4 locations in any order
        3. Move the Sphero as quickly as possible
        4. Check in at each location using the buttons
       
        Your score depends 70% on time and 30% on route efficiency.
        """
    },
    "Efficiency Challenge": {
        "description": "Find the shortest possible route",
        "instructions": """
        1. Start at the highlighted location
        2. Plan your route carefully to minimize distance
        3. Visit all 4 locations in the optimal order
        4. Check in at each location using the buttons
       
        Your score depends 80% on route efficiency and 20% on time.
        """
    },
    "Complex Supply Chain": {
        "description": "Follow specific order constraints",
        "instructions": """
        1. Start at the Factory
        2. Follow these rules:
           - Visit Factory BEFORE Shop
           - Visit DHL Hub BEFORE Residence
        3. Visit all 4 locations while following these rules
        4. Check in at each location using the buttons
       
        Your score depends 40% on efficiency, 40% on following constraints, and 20% on time.
        """
    },
    "Road Closure Challenge": {
        "description": "Navigate with closed roads and obstructions",
        "instructions": """
        1. Start at the highlighted location
        2. Road closures will randomly appear, blocking certain routes
        3. Find alternative paths to reach all locations
        4. Check in at each location using the buttons
        
        Your score depends 50% on efficiency and 50% on time.
        """
    },
    "Package Delivery": {
        "description": "Pick up and deliver packages between locations",
        "instructions": """
        1. Start at the highlighted location
        2. Pick up packages by pressing the "Pick Up Package" button
        3. Deliver each package to its designated destination
        4. Complete all package deliveries as efficiently as possible
        
        Your score depends 40% on efficiency, 40% on successful deliveries, and 20% on time.
        """
    }
}

# Scoring weights for different game modes
SCORING_WEIGHTS = {
    "Speed Run": {
        "efficiency": 0.3,
        "time": 0.7
    },
    "Efficiency Challenge": {
        "efficiency": 0.8,
        "time": 0.2
    },
    "Complex Supply Chain": {
        "efficiency": 0.4,
        "constraints": 0.4,
        "time": 0.2
    },
    "Road Closure Challenge": {
        "efficiency": 0.5,
        "time": 0.5
    },
    "Package Delivery": {
        "efficiency": 0.4,
        "delivery": 0.4,
        "time": 0.2
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
</style>
"""