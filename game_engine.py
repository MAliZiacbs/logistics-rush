import time
import random
import json
from logistics_graph import LogisticsGraph
from package_manager import PackageManager
from constraints_manager import ConstraintsManager
from route_optimizer import RouteOptimizer
from config import DIFFICULTY_CONSTRAINTS, CONSTRAINT_VIOLATION_PENALTY

class LogisticsRushGame:
    def __init__(self, locations, road_segments, distances, difficulty=1):
        """Initialize a new game with the given difficulty"""
        self.difficulty = min(difficulty, 3)  # Cap at 3
        self.start_location = "Warehouse"
        
        # Create the graph
        self.graph = LogisticsGraph(locations, road_segments, distances)
        
        # Create the package manager
        self.package_manager = PackageManager()
        
        # Get constraints based on difficulty
        active_constraints = DIFFICULTY_CONSTRAINTS.get(self.difficulty, [])
        
        # Create the constraints manager with active constraints
        self.constraints = ConstraintsManager(active_constraints)
        
        # Initialize game state
        self.game_active = False
        self.current_location = None
        self.current_route = []
        self.start_time = None
        self.closed_roads = []
        self.optimal_route = None
        self.optimal_distance = 0
        self.optimal_package_operations = []
        
        # Enhanced diagnostics
        self.move_history = []
        self.decision_logs = []
        self.constraint_violations = []
        
        # Track constraint violations for scoring
        self.violated_constraints = set()
    
    def start_game(self):
        """Start a new game with the current difficulty"""
        # Reset game state
        self.game_active = True
        self.current_location = self.start_location
        self.current_route = [self.start_location]
        self.start_time = time.time()
        self.violated_constraints = set()
        
        # Generate packages
        self._generate_packages()
        
        # Close roads based on difficulty
        self.closed_roads = self._generate_road_closures()
        for road in self.closed_roads:
            self.graph.close_road(road[0], road[1])
        
        # Calculate optimal route
        self._calculate_optimal_route()
        
        # Log initial game state
        self.decision_logs.append({
            "timestamp": time.time(),
            "action": "game_start",
            "location": self.current_location,
            "available_moves": self.get_available_moves(),
            "packages": self.package_manager.get_package_info(),
            "closed_roads": self.closed_roads,
            "active_constraints": self.constraints.get_active_constraints()
        })
        
        return {
            "started": True,
            "current_location": self.current_location,
            "available_moves": self.get_available_moves(),
            "packages": self.package_manager.get_package_info(),
            "closed_roads": self.closed_roads,
            "active_constraints": self.constraints.get_active_constraints()
        }
    
    def move_to_location(self, location):
        """Move to a directly connected location"""
        if not self.game_active:
            return {"success": False, "message": "Game not active"}
        
        # Log decision point
        decision_point = {
            "timestamp": time.time(),
            "action": "move_attempt",
            "from": self.current_location,
            "to": location,
            "current_route": self.current_route.copy()
        }
        
        # Check if the location is directly connected
        if not self.graph.is_directly_connected(self.current_location, location):
            decision_point["result"] = "failed"
            decision_point["reason"] = "not_directly_connected"
            self.decision_logs.append(decision_point)
            return {
                "success": False, 
                "message": f"Cannot move directly from {self.current_location} to {location}. Choose a connected location."
            }
        
        # Get the distance for this move
        distance = self.graph.get_edge_weight(self.current_location, location)
        decision_point["distance"] = distance
        
        # Check if this move would violate constraints
        temp_route = self.current_route + [location]
        valid, message, violated_constraint = self.constraints.validate_route(temp_route)
        
        decision_point["constraints_check"] = {
            "valid": valid,
            "message": message,
            "violated_constraint": violated_constraint
        }
        
        # Set up warning message and track violation if needed
        warning_message = ""
        
        if not valid:
            self.constraint_violations.append({
                "timestamp": time.time(),
                "current_route": self.current_route.copy(),
                "attempted_location": location,
                "violation_message": message,
                "violated_constraint": violated_constraint
            })
            
            # Record the violation in the constraints manager
            self.constraints.record_violation(self.current_route, location, violated_constraint)
            
            # Add to set of violated constraints for scoring
            if violated_constraint:
                self.violated_constraints.add(violated_constraint)
            
            decision_point["result"] = "constraint_violation"
            
            # Set warning message
            warning_message = message
        
        # Move is executing regardless of constraints, update route and current location
        self.current_route.append(location)
        self.current_location = location
        
        decision_point["result"] = "success"
        self.decision_logs.append(decision_point)
        
        # Record this move in history
        self.move_history.append({
            "timestamp": time.time(),
            "from": self.current_route[-2],
            "to": location,
            "distance": distance,
            "violated_constraint": None if valid else violated_constraint
        })
        
        # Check for automatic package delivery
        result = {"success": True, "message": f"Moved to {location}"}
        if warning_message:
            result["message"] += f" WARNING: {warning_message}"
            result["constraint_violated"] = True
            result["violated_constraint"] = violated_constraint
        
        if self.package_manager.carrying and self.package_manager.carrying.delivery == location:
            success, deliver_msg = self.package_manager.deliver(location)
            if success:
                result["message"] += f". {deliver_msg}"
        
        # Check if game is complete
        if self._check_game_completion():
            game_results = self.end_game()
            result["game_completed"] = True
            result["results"] = game_results
            
        # Return available moves for the next step
        result["available_moves"] = self.get_available_moves()
        result["packages_here"] = self.package_manager.get_available_pickups(location)
        
        return result
    
    def pickup_package(self, package_id):
        """Pick up a package at the current location"""
        if not self.game_active:
            return {"success": False, "message": "Game not active"}
        
        # Log decision
        decision_point = {
            "timestamp": time.time(),
            "action": "pickup_attempt",
            "location": self.current_location,
            "package_id": package_id
        }
        
        success, message = self.package_manager.pickup(package_id, self.current_location)
        
        decision_point["result"] = "success" if success else "failed"
        decision_point["message"] = message
        self.decision_logs.append(decision_point)
        
        result = {"success": success, "message": message}
        
        # Return available moves for the next step
        result["available_moves"] = self.get_available_moves()
        
        return result
    
    def deliver_package(self):
        """Deliver the currently carried package"""
        if not self.game_active:
            return {"success": False, "message": "Game not active"}
        
        # Log decision
        decision_point = {
            "timestamp": time.time(),
            "action": "delivery_attempt",
            "location": self.current_location
        }
        
        if self.package_manager.carrying:
            decision_point["package_id"] = self.package_manager.carrying.id
            decision_point["package_destination"] = self.package_manager.carrying.delivery
            
        success, message = self.package_manager.deliver(self.current_location)
        
        decision_point["result"] = "success" if success else "failed"
        decision_point["message"] = message
        self.decision_logs.append(decision_point)
        
        result = {"success": success, "message": message}
        
        # Check if game is complete
        if success and self._check_game_completion():
            game_results = self.end_game()
            result["game_completed"] = True
            result["results"] = game_results
            
        # Return available moves for the next step
        result["available_moves"] = self.get_available_moves()
        
        return result
    
    def get_available_moves(self):
        """Get all locations that can be moved to from the current location"""
        if not self.game_active or not self.current_location:
            return []
            
        # Get all connected locations
        connected = self.graph.get_connected_locations(self.current_location)
        
        # All moves are available regardless of constraints
        valid_moves = []
        for location in connected:
            # Get the distance for this move
            distance = self.graph.get_edge_weight(self.current_location, location)
            
            # Check if this would violate a constraint (for warning purposes only)
            temp_route = self.current_route + [location]
            valid, message, violated_constraint = self.constraints.validate_route(temp_route)
            
            valid_moves.append({
                "location": location,
                "distance": distance,
                "has_packages": len(self.package_manager.get_available_pickups(location)) > 0,
                "violates_constraint": not valid,
                "constraint_message": message if not valid else None,
                "violated_constraint": violated_constraint
            })
        
        return valid_moves
    
    def end_game(self):
        """End the game and calculate results"""
        if not self.game_active:
            return {"success": False, "message": "Game not active"}
            
        self.game_active = False
        game_time = time.time() - self.start_time
        
        # Calculate player route distance - direct calculation since we now have explicit movements
        player_distance = self.graph.calculate_route_distance(self.current_route)
        
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
        
        # Apply constraint penalties if constraints were violated
        total_possible_constraints = len(DIFFICULTY_CONSTRAINTS.get(self.difficulty, []))
        if total_possible_constraints > 0:
            # Calculate percentage of constraints violated
            if len(self.violated_constraints) > 0:
                constraints_score = max(0, 100 - (len(self.violated_constraints) * CONSTRAINT_VIOLATION_PENALTY))
            else:
                constraints_score = 100
        else:
            # No constraints in this difficulty level
            constraints_score = 100
        
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
        
        # Generate detailed diagnostics
        diagnostics = {
            "move_history": self.move_history,
            "decision_logs": self.decision_logs,
            "constraint_violations": self.constraint_violations,
            "graph_state": self.graph.get_graph_state(),
            "optimal_route_calculation": {
                "route": self.optimal_route,
                "distance": self.optimal_distance,
                "operations": self.optimal_package_operations
            },
            "violated_constraints": list(self.violated_constraints),
            "active_constraints": self.constraints.get_active_constraints()
        }
        
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
            "closed_roads": self.closed_roads,
            "packages": self.package_manager.get_package_info(),
            "optimal_package_operations": self.optimal_package_operations,
            "violated_constraints": list(self.violated_constraints),
            "constraints_score": constraints_score,
            "active_constraints": self.constraints.get_active_constraints(),
            "enhanced_diagnostics": diagnostics
        }
    
    def get_game_status(self):
        """Get current game status"""
        if not self.game_active:
            return {"active": False}
            
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
            "current_location": self.current_location,
            "locations_visited": unique_locations,
            "total_locations": total_locations,
            "packages_delivered": delivered,
            "total_packages": total_packages,
            "carrying_package": self.package_manager.carrying.id if self.package_manager.carrying else None,
            "progress": combined_progress,
            "available_moves": self.get_available_moves(),
            "violated_constraints": list(self.violated_constraints),
            "active_constraints": self.constraints.get_active_constraints()
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
            ("Home", "Warehouse")
        ]
        pickup, delivery = random.choice(options)
        self.package_manager.add_package(3, pickup, delivery)
    
    def _generate_road_closures(self):
        """Generate road closures based on difficulty"""
        # Number of closures based on difficulty
        num_closures = self.difficulty
        
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
        
        if num_closures in safe_closures:
            # Randomly select one of the predefined closure sets for this difficulty
            return random.choice(safe_closures[num_closures])
        
        # Fallback to the simplest closure if something goes wrong
        return [("Warehouse", "Shop")]
    
    def _calculate_optimal_route(self):
        """Calculate the optimal route that properly accounts for package deliveries"""
        optimizer = RouteOptimizer(self.graph, self.constraints)
        
        # Get a list of all locations
        locations = list(self.graph.locations.keys())
        
        # Find the optimal route with package operations
        route, distance, operations = optimizer.find_optimal_route(
            self.start_location, 
            locations, 
            self.package_manager.packages
        )
        
        # Store the results
        self.optimal_route = route
        self.optimal_distance = distance
        self.optimal_package_operations = operations
    
    def _check_game_completion(self):
        """Check if the game is complete"""
        # Game is complete when:
        # 1. All locations have been visited
        # 2. All packages have been delivered
        all_locations_visited = set(self.graph.locations.keys()).issubset(set(self.current_route))
        all_packages_delivered = self.package_manager.all_packages_delivered()
        
        return all_locations_visited and all_packages_delivered