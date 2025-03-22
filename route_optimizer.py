from constraints_manager import ConstraintsManager

class RouteOptimizer:
    def __init__(self, logistics_graph):
        """Initialize with a LogisticsGraph instance"""
        self.graph = logistics_graph
        self.constraints = ConstraintsManager()
    
    def find_optimal_route(self, start_location, required_locations, packages):
        """Find a realistic optimal route that properly accounts for package deliveries"""
        # First, let's make sure our starting location is included
        if start_location not in required_locations:
            required_locations = [start_location] + [loc for loc in required_locations if loc != start_location]
        
        # Create a route that prioritizes package operations
        route = [start_location]
        current_location = start_location
        carrying_package = None
        package_operations = []
        
        # Keep track of which packages are handled
        handled_packages = set()
        
        # First pass: handle critical packages that match constraints
        for package in packages:
            # Skip if already handled
            if package.id in handled_packages:
                continue
                
            # Special case: Warehouse → Shop package (constraint)
            if package.pickup == "Warehouse" and package.delivery == "Shop":
                # Only add if we can reach both locations
                path_to_pickup, _ = self.graph.find_shortest_path(current_location, package.pickup)
                if path_to_pickup:
                    path_to_delivery, _ = self.graph.find_shortest_path(package.pickup, package.delivery)
                    
                    if path_to_delivery:
                        # First visit the pickup location if not already there
                        if current_location != package.pickup:
                            route.append(package.pickup)
                            current_location = package.pickup
                            
                        package_operations.append((package.pickup, "pickup", package.id))
                        
                        # Then visit the delivery location
                        route.append(package.delivery)
                        package_operations.append((package.delivery, "delivery", package.id))
                        
                        # Update current location and mark package as handled
                        current_location = package.delivery
                        handled_packages.add(package.id)
            
            # Special case: Distribution Center → Home package (constraint)
            elif package.pickup == "Distribution Center" and package.delivery == "Home":
                # Only add if we can reach both locations
                path_to_pickup, _ = self.graph.find_shortest_path(current_location, package.pickup)
                if path_to_pickup:
                    path_to_delivery, _ = self.graph.find_shortest_path(package.pickup, package.delivery)
                    
                    if path_to_delivery:
                        # First visit the pickup location if not already there
                        if current_location != package.pickup:
                            route.append(package.pickup)
                            current_location = package.pickup
                            
                        package_operations.append((package.pickup, "pickup", package.id))
                        
                        # Then visit the delivery location
                        route.append(package.delivery)
                        package_operations.append((package.delivery, "delivery", package.id))
                        
                        # Update current location and mark package as handled
                        current_location = package.delivery
                        handled_packages.add(package.id)
        
        # Second pass: handle remaining packages
        for package in packages:
            # Skip if already handled
            if package.id in handled_packages:
                continue
                
            # Find path to pickup
            path_to_pickup, _ = self.graph.find_shortest_path(current_location, package.pickup)
            if path_to_pickup:
                # First visit the pickup location if not already there
                if current_location != package.pickup:
                    route.append(package.pickup)
                    current_location = package.pickup
                
                package_operations.append((package.pickup, "pickup", package.id))
                
                # Find path to delivery
                path_to_delivery, _ = self.graph.find_shortest_path(current_location, package.delivery)
                if path_to_delivery:
                    # Visit the delivery location
                    route.append(package.delivery)
                    package_operations.append((package.delivery, "delivery", package.id))
                    
                    # Update current location and mark package as handled
                    current_location = package.delivery
                    handled_packages.add(package.id)
        
        # Third pass: make sure we've visited all required locations
        for location in required_locations:
            if location not in route:
                # Try to find a path to this location
                path, _ = self.graph.find_shortest_path(current_location, location)
                if path:
                    route.append(location)
                    current_location = location
        
        # Finally, check if the route satisfies constraints
        valid, _ = self.constraints.validate_route(route)
        if not valid:
            # If not valid, use the constraint-based route as fallback
            fallback_route = self._create_constraint_satisfied_route(start_location, required_locations)
            
            # Calculate distance for fallback route
            _, fallback_distance = self.graph.find_path_distance(fallback_route)
            return fallback_route, fallback_distance, []
        
        # Calculate the total distance of this route
        _, total_distance = self.graph.find_path_distance(route)
        if total_distance == float('inf'):
            # If path is invalid, use constraint-based route
            fallback_route = self._create_constraint_satisfied_route(start_location, required_locations)
            _, fallback_distance = self.graph.find_path_distance(fallback_route)
            return fallback_route, fallback_distance, []
            
        return route, total_distance, package_operations
    
    def _create_constraint_satisfied_route(self, start, locations):
        """Create a route that satisfies all constraints"""
        route = [start]
        remaining = [loc for loc in locations if loc != start]
        
        # First handle Warehouse and Shop (Warehouse must come before Shop)
        if "Warehouse" not in route and "Warehouse" in remaining:
            route.append("Warehouse")
            remaining.remove("Warehouse")
        
        if "Shop" in remaining:
            # Make sure Warehouse is before Shop
            if "Warehouse" in route:
                route.append("Shop")
                remaining.remove("Shop")
        
        # Then handle Distribution Center and Home (DC must come before Home)
        if "Distribution Center" in remaining:
            route.append("Distribution Center")
            remaining.remove("Distribution Center")
        
        if "Home" in remaining:
            # Make sure Distribution Center is before Home
            if "Distribution Center" in route:
                route.append("Home")
                remaining.remove("Home")
        
        # Add any remaining locations
        route.extend(remaining)
        
        return route
    
    def _apply_two_opt(self, route):
        """Apply 2-opt local search to improve a route"""
        improved = True
        best_route = route.copy()
        
        # Limit iterations to prevent excessive computation
        max_iterations = 10
        iteration = 0
        
        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            
            for i in range(1, len(best_route) - 1):
                for j in range(i + 1, len(best_route)):
                    # Create a new route by reversing the segment between i and j
                    new_route = best_route.copy()
                    new_route[i:j+1] = reversed(new_route[i:j+1])
                    
                    # Check if the new route is valid
                    valid, _ = self.constraints.validate_route(new_route)
                    if not valid:
                        continue
                    
                    # Check if the new route is better
                    _, old_distance = self.graph.find_path_distance(best_route)
                    _, new_distance = self.graph.find_path_distance(new_route)
                    
                    if new_distance < old_distance:
                        best_route = new_route
                        improved = True
        
        return best_route