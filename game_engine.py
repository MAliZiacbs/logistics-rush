import time
import random
import json
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
        self.optimal_package_operations = []
        
        # Enhanced diagnostics
        self.move_history = []
        self.path_validation_logs = []
        self.optimizer_logs = []
    
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
        
        # Enhanced diagnostics - Verify road closures after initialization
        self._log_road_closure_state("after_initialization")
        
        # Calculate optimal route
        self._calculate_optimal_route()
        
        # Enhanced diagnostics - Verify optimal route feasibility
        self._validate_route_feasibility(self.optimal_route, "optimal_route_validation")
        
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
        
        # Enhanced diagnostics - Log move attempt details
        move_attempt = {
            "timestamp": time.time(),
            "from": current_location,
            "to": location,
            "current_route": self.current_route.copy()
        }
        
        # Check if move is valid (there's a path)
        path, distance = self.graph.find_shortest_path(current_location, location)
        
        # Enhanced diagnostics - Log path details
        move_attempt["calculated_path"] = path
        move_attempt["calculated_distance"] = distance
        
        if path is None:
            move_attempt["result"] = "failed"
            move_attempt["reason"] = "no_valid_path"
            self.move_history.append(move_attempt)
            return {"success": False, "message": f"No valid path to {location}"}
            
        # Extra validation: check each segment of the path
        segment_validation = []
        valid_path = True
        invalid_segment = None
        
        for i in range(len(path) - 1):
            segment = (path[i], path[i+1])
            is_closed = self.graph.is_road_closed(path[i], path[i+1])
            segment_validation.append({
                "segment": segment,
                "is_closed": is_closed
            })
            
            if is_closed:
                valid_path = False
                invalid_segment = segment
                break
        
        move_attempt["segment_validation"] = segment_validation
        
        if not valid_path:
            move_attempt["result"] = "failed"
            move_attempt["reason"] = f"road_segment_closed_{invalid_segment[0]}_to_{invalid_segment[1]}"
            self.move_history.append(move_attempt)
            return {"success": False, "message": f"Road between {invalid_segment[0]} and {invalid_segment[1]} is closed"}
        
        # Check constraints
        valid, message = self.constraints.validate_move(self.current_route, location)
        move_attempt["constraints_valid"] = valid
        move_attempt["constraints_message"] = message
        
        if not valid:
            move_attempt["result"] = "failed"
            move_attempt["reason"] = "constraints_violation"
            self.move_history.append(move_attempt)
            return {"success": False, "message": message}
        
        # Move is valid, update route
        self.current_route.append(location)
        move_attempt["result"] = "success"
        
        # Check for automatic package delivery
        result = {"success": True, "message": f"Moved to {location}"}
        
        if self.package_manager.carrying and self.package_manager.carrying.delivery == location:
            success, deliver_msg = self.package_manager.deliver(location)
            move_attempt["auto_delivery"] = {
                "success": success,
                "message": deliver_msg
            }
            if success:
                result["message"] += f". {deliver_msg}"
        
        self.move_history.append(move_attempt)
        
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
        
        # Enhanced diagnostics - Log pickup attempt
        pickup_attempt = {
            "timestamp": time.time(),
            "action": "pickup",
            "package_id": package_id,
            "location": current_location
        }
        
        success, message = self.package_manager.pickup(package_id, current_location)
        
        pickup_attempt["success"] = success
        pickup_attempt["message"] = message
        self.move_history.append(pickup_attempt)
        
        return {"success": success, "message": message}
    
    def deliver_package(self):
        """Deliver the currently carried package"""
        if not self.game_active:
            return {"success": False, "message": "Game not active"}
            
        current_location = self.current_route[-1]
        
        # Enhanced diagnostics - Log delivery attempt
        delivery_attempt = {
            "timestamp": time.time(),
            "action": "delivery",
            "location": current_location
        }
        
        if self.package_manager.carrying:
            delivery_attempt["package_id"] = self.package_manager.carrying.id
            delivery_attempt["package_destination"] = self.package_manager.carrying.delivery
        
        success, message = self.package_manager.deliver(current_location)
        
        delivery_attempt["success"] = success
        delivery_attempt["message"] = message
        self.move_history.append(delivery_attempt)
        
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
        full_path, player_distance = self.graph.find_path_distance(self.current_route)
        
        # Enhanced diagnostics - Validate final route
        self._validate_route_feasibility(self.current_route, "final_player_route_validation")
        
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
        
        # Enhanced diagnostics for the results
        diagnostic_data = {
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
            "enhanced_diagnostics": {
                "move_history": self.move_history,
                "path_validation_logs": self.path_validation_logs,
                "optimizer_logs": self.optimizer_logs,
                "final_graph_state": self.graph.get_graph_state()
            }
        }
        
        return diagnostic_data
    
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
            ("Home", "Warehouse")
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
        """Calculate the optimal route that properly accounts for package deliveries"""
        optimizer = RouteOptimizer(self.graph)
        
        # Get a list of all locations
        locations = list(self.graph.locations.keys())
        
        # Enhanced diagnostics - Save pre-optimization state
        self.optimizer_logs.append({
            "stage": "pre_optimization",
            "graph_state": self.graph.get_graph_state(),
            "closed_roads": self.closed_roads,
            "start_location": self.start_location,
            "locations": locations,
            "packages": self.package_manager.get_package_info()
        })
        
        # Find the optimal route with package operations
        route, distance, operations, optimization_log = optimizer.find_optimal_route(
            self.start_location, 
            locations, 
            self.package_manager.packages
        )
        
        # Store the optimization log
        self.optimizer_logs.append(optimization_log)
        
        # Store the results
        self.optimal_route = route
        self.optimal_distance = distance
        self.optimal_package_operations = operations
        
        # Enhanced diagnostics - Log post-optimization
        self.optimizer_logs.append({
            "stage": "post_optimization",
            "optimal_route": route,
            "optimal_distance": distance,
            "optimal_operations": operations
        })
    
    def _check_game_completion(self):
        """Check if the game is complete"""
        # Game is complete when:
        # 1. All locations have been visited
        # 2. All packages have been delivered
        all_locations_visited = set(self.graph.locations.keys()).issubset(set(self.current_route))
        all_packages_delivered = self.package_manager.all_packages_delivered()
        
        return all_locations_visited and all_packages_delivered
    
    # New diagnostic methods
    def _log_road_closure_state(self, stage):
        """Log the current state of all roads for diagnostic purposes"""
        road_state = {}
        for road in self.graph.road_segments:
            loc1, loc2 = road
            is_closed = self.graph.is_road_closed(loc1, loc2)
            road_state[f"{loc1}-{loc2}"] = {
                "closed": is_closed,
                "expected_closed": (loc1, loc2) in self.closed_roads or (loc2, loc1) in self.closed_roads
            }
        
        self.path_validation_logs.append({
            "timestamp": time.time(),
            "stage": stage,
            "road_state": road_state
        })
    
    def _validate_route_feasibility(self, route, log_id):
        """Validate if a route is feasible given current road closures"""
        result = {
            "timestamp": time.time(),
            "route": route.copy(),
            "log_id": log_id,
            "segments": []
        }
        
        if not route or len(route) < 2:
            result["feasible"] = True
            result["message"] = "Route too short for validation"
            self.path_validation_logs.append(result)
            return True
        
        overall_feasible = True
        
        for i in range(len(route) - 1):
            start = route[i]
            end = route[i + 1]
            
            # Try to find a path between consecutive locations
            path, distance = self.graph.find_shortest_path(start, end)
            
            segment_result = {
                "from": start,
                "to": end,
                "direct_connection_closed": self.graph.is_road_closed(start, end),
                "path_found": path is not None,
                "path": path,
                "distance": distance
            }
            
            if path is None:
                overall_feasible = False
                segment_result["message"] = f"No path exists between {start} and {end}"
            
            result["segments"].append(segment_result)
        
        result["feasible"] = overall_feasible
        result["message"] = "Route is feasible" if overall_feasible else "Route contains infeasible segments"
        
        self.path_validation_logs.append(result)
        return overall_feasible