import time
import random
from logistics_graph import LogisticsGraph
from package_manager import PackageManager
from constraints_manager import ConstraintsManager
from route_optimizer import RouteOptimizer

class LogisticsRushGame:
    def __init__(self, locations, road_segments, distances, difficulty=1):
        """Initialize a new game with the given difficulty"""
        self.difficulty = min(difficulty, 3)  # Cap at 3
        self.start_location = "Warehouse"
        
        # Create the graph
        self.graph = LogisticsGraph(locations, road_segments, distances)
        
        # Create the package manager
        self.package_manager = PackageManager()
        
        # Create the constraints manager
        self.constraints = ConstraintsManager()
        
        # Initialize game state
        self.game_active = False
        self.current_route = []
        self.start_time = None
        self.closed_roads = []
        self.optimal_route = None
        self.optimal_distance = 0
    
    def start_game(self):
        """Start a new game with the current difficulty"""
        # Reset game state
        self.game_active = True
        self.current_route = [self.start_location]
        self.start_time = time.time()
        
        # Generate packages
        self._generate_packages()
        
        # Close roads based on difficulty
        self.closed_roads = self._generate_road_closures()
        for road in self.closed_roads:
            self.graph.close_road(road[0], road[1])
        
        # Calculate optimal route
        self._calculate_optimal_route()
        
        return {
            "started": True,
            "packages": self.package_manager.get_package_info(),
            "closed_roads": self.closed_roads,
            "start_location": self.start_location
        }
    
    def move_to_location(self, location):
        """Move to a new location if it's valid"""
        if not self.game_active:
            return {"success": False, "message": "Game not active"}
            
        current_location = self.current_route[-1]
        
        # Check if move is valid (there's a path)
        path, distance = self.graph.find_shortest_path(current_location, location)
        if path is None:
            return {"success": False, "message": f"No valid path to {location}"}
            
        # Check constraints
        valid, message = self.constraints.validate_move(self.current_route, location)
        if not valid:
            return {"success": False, "message": message}
        
        # Move is valid, update route
        self.current_route.append(location)
        
        # Check for automatic package delivery
        result = {"success": True, "message": f"Moved to {location}"}
        
        if self.package_manager.carrying and self.package_manager.carrying.delivery == location:
            success, deliver_msg = self.package_manager.deliver(location)
            if success:
                result["message"] += f". {deliver_msg}"
        
        # Check if game is complete
        if self._check_game_completion():
            game_results = self.end_game()
            result["game_completed"] = True
            result["results"] = game_results
            
        return result
    
    def pickup_package(self, package_id):
        """Pick up a package at the current location"""
        if not self.game_active:
            return {"success": False, "message": "Game not active"}
            
        current_location = self.current_route[-1]
        success, message = self.package_manager.pickup(package_id, current_location)
        
        return {"success": success, "message": message}
    
    def deliver_package(self):
        """Deliver the currently carried package"""
        if not self.game_active:
            return {"success": False, "message": "Game not active"}
            
        current_location = self.current_route[-1]
        success, message = self.package_manager.deliver(current_location)
        
        # Check if game is complete
        result = {"success": success, "message": message}
        
        if success and self._check_game_completion():
            game_results = self.end_game()
            result["game_completed"] = True
            result["results"] = game_results
            
        return result
    
    def end_game(self):
        """End the game and calculate results"""
        if not self.game_active:
            return {"success": False, "message": "Game not active"}
            
        self.game_active = False
        game_time = time.time() - self.start_time
        
        # Calculate player route distance
        _, player_distance = self.graph.find_path_distance(self.current_route)
        
        # Ensure player_distance is valid (not infinity)
        if player_distance == float('inf'):
            # Fallback to a simple distance calculation
            player_distance = len(self.current_route) * 300
        
        # Calculate efficiency
        if player_distance <= self.optimal_distance:
            # Player found a better route
            efficiency = 100
            better_route = True
        else:
            # Normal efficiency calculation
            efficiency = min(100, int((self.optimal_distance / player_distance) * 100))
            better_route = False
        
        # Calculate score components
        weights = {"efficiency": 0.4, "delivery": 0.3, "constraints": 0.2, "time": 0.1}
        
        delivery_score = 100  # All packages must be delivered to complete
        constraints_score = 100  # All constraints must be satisfied
        
        # Time factor calculation (based on average expected time)
        expected_time = (len(self.package_manager.packages) * 15) + (len(self.current_route) * 5)
        time_factor = max(0, 100 - ((game_time / expected_time) * 50))  # 50% penalty for 2x expected time
        
        # Final score calculation
        score = (
            efficiency * weights["efficiency"] +
            delivery_score * weights["delivery"] +
            constraints_score * weights["constraints"] +
            time_factor * weights["time"]
        )
        
        score = min(100, max(0, int(score)))
        
        return {
            "time": game_time,
            "player_route": self.current_route,
            "player_distance": player_distance,
            "optimal_route": self.optimal_route,
            "optimal_distance": self.optimal_distance,
            "efficiency": efficiency,
            "found_better_route": better_route,
            "score": score,
            "difficulty": self.difficulty,
            "closed_roads": self.closed_roads
        }
    
    def get_game_status(self):
        """Get current game status"""
        if not self.game_active:
            return {"active": False}
            
        current_location = self.current_route[-1]
        game_time = time.time() - self.start_time
        
        # Calculate progress
        delivered = len(self.package_manager.get_delivered_packages())
        total_packages = len(self.package_manager.packages)
        unique_locations = len(set(self.current_route))
        total_locations = len(self.graph.locations)
        
        # Location progress and package progress
        loc_progress = min(100, int((unique_locations / total_locations) * 100))
        pkg_progress = min(100, int((delivered / total_packages) * 100))
        
        # Combined progress
        combined_progress = (loc_progress + pkg_progress) // 2
        
        return {
            "active": True,
            "time": game_time,
            "current_location": current_location,
            "locations_visited": unique_locations,
            "total_locations": total_locations,
            "packages_delivered": delivered,
            "total_packages": total_packages,
            "carrying_package": self.package_manager.carrying.id if self.package_manager.carrying else None,
            "progress": combined_progress
        }
    
    def _generate_packages(self):
        """Generate the standard packages for the game"""
        # Always include these critical packages for constraints
        self.package_manager.add_package(1, "Warehouse", "Shop")
        self.package_manager.add_package(2, "Distribution Center", "Home")
        
        # Add one more random package
        options = [
            ("Shop", "Distribution Center"),
            ("Distribution Center", "Shop"),
            ("Warehouse", "Home"),
            ("Home", "Shop")
        ]
        pickup, delivery = random.choice(options)
        self.package_manager.add_package(3, pickup, delivery)
    
    def _generate_road_closures(self):
        """Generate road closures based on difficulty"""
        # Predefined safe closures that ensure the game remains solvable
        safe_closures = {
            1: [
                [("Warehouse", "Shop")],
                [("Warehouse", "Home")],
                [("Shop", "Home")]
            ],
            2: [
                [("Warehouse", "Shop"), ("Distribution Center", "Home")],
                [("Warehouse", "Home"), ("Distribution Center", "Shop")],
                [("Shop", "Home"), ("Warehouse", "Distribution Center")]
            ],
            3: [
                [("Warehouse", "Shop"), ("Shop", "Home"), ("Warehouse", "Home")],
                [("Distribution Center", "Shop"), ("Shop", "Home"), ("Distribution Center", "Home")],
                [("Warehouse", "Shop"), ("Warehouse", "Home"), ("Distribution Center", "Home")]
            ]
        }
        
        if self.difficulty in safe_closures:
            # Randomly select one of the predefined closure sets for this difficulty
            return random.choice(safe_closures[self.difficulty])
        
        # Fallback to the simplest closure if something goes wrong
        return [("Warehouse", "Shop")]
    
    def _calculate_optimal_route(self):
        """Calculate the optimal route"""
        optimizer = RouteOptimizer(self.graph)
        
        # Get a list of all locations
        locations = list(self.graph.locations.keys())
        
        # Find the optimal route
        route, distance = optimizer.find_optimal_route(self.start_location, locations)
        
        # Store the results
        self.optimal_route = route
        self.optimal_distance = distance
    
    def _check_game_completion(self):
        """Check if the game is complete"""
        # Game is complete when:
        # 1. All locations have been visited
        # 2. All packages have been delivered
        all_locations_visited = all(loc in self.current_route for loc in self.graph.locations)
        all_packages_delivered = self.package_manager.all_packages_delivered()
        
        return all_locations_visited and all_packages_delivered