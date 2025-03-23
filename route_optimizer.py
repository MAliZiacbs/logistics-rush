from constraints_manager import ConstraintsManager

class RouteOptimizer:
    def __init__(self, logistics_graph):
        """Initialize with a LogisticsGraph instance"""
        self.graph = logistics_graph
        self.constraints = ConstraintsManager()
    
    def find_optimal_route(self, start_location, required_locations, packages):
        """Find the optimal route using only available roads and respecting constraints"""
        # First, let's make sure our starting location is included
        if start_location not in required_locations:
            required_locations = [start_location] + [loc for loc in required_locations if loc != start_location]
        
        # Create a route that prioritizes package operations
        route = [start_location]
        current_location = start_location
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
                # Find the shortest valid path for pickup to delivery
                pickup_path, pickup_distance = self._find_path_respecting_constraints(
                    current_location, package.pickup, route
                )
                
                if pickup_path:
                    delivery_path, delivery_distance = self._find_path_respecting_constraints(
                        package.pickup, package.delivery, route + pickup_path[1:]
                    )
                    
                    if delivery_path:
                        # Add the pickup path (excluding start)
                        if current_location != package.pickup:
                            route.extend(pickup_path[1:])
                            current_location = package.pickup
                            
                        package_operations.append((package.pickup, "pickup", package.id))
                        
                        # Add the delivery path (excluding start)
                        route.extend(delivery_path[1:])
                        package_operations.append((package.delivery, "delivery", package.id))
                        
                        # Update current location and mark package as handled
                        current_location = package.delivery
                        handled_packages.add(package.id)
            
            # Special case: Distribution Center → Home package (constraint)
            elif package.pickup == "Distribution Center" and package.delivery == "Home":
                # Find the shortest valid path for pickup to delivery
                pickup_path, pickup_distance = self._find_path_respecting_constraints(
                    current_location, package.pickup, route
                )
                
                if pickup_path:
                    delivery_path, delivery_distance = self._find_path_respecting_constraints(
                        package.pickup, package.delivery, route + pickup_path[1:]
                    )
                    
                    if delivery_path:
                        # Add the pickup path (excluding start)
                        if current_location != package.pickup:
                            route.extend(pickup_path[1:])
                            current_location = package.pickup
                            
                        package_operations.append((package.pickup, "pickup", package.id))
                        
                        # Add the delivery path (excluding start)
                        route.extend(delivery_path[1:])
                        package_operations.append((package.delivery, "delivery", package.id))
                        
                        # Update current location and mark package as handled
                        current_location = package.delivery
                        handled_packages.add(package.id)
        
        # Second pass: handle remaining packages
        for package in packages:
            # Skip if already handled
            if package.id in handled_packages:
                continue
                
            # Find the shortest valid path for pickup to delivery
            pickup_path, pickup_distance = self._find_path_respecting_constraints(
                current_location, package.pickup, route
            )
            
            if pickup_path:
                # Add the pickup path (excluding start)
                if current_location != package.pickup:
                    route.extend(pickup_path[1:])
                    current_location = package.pickup
                
                package_operations.append((package.pickup, "pickup", package.id))
                
                # Find the shortest valid path for delivery
                delivery_path, delivery_distance = self._find_path_respecting_constraints(
                    current_location, package.delivery, route
                )
                
                if delivery_path:
                    # Add the delivery path (excluding start)
                    route.extend(delivery_path[1:])
                    package_operations.append((package.delivery, "delivery", package.id))
                    
                    # Update current location and mark package as handled
                    current_location = package.delivery
                    handled_packages.add(package.id)
        
        # Third pass: make sure we've visited all required locations
        for location in required_locations:
            if location not in route:
                # Find the shortest valid path to this location
                path, _ = self._find_path_respecting_constraints(
                    current_location, location, route
                )
                
                if path:
                    # Add the path (excluding start)
                    route.extend(path[1:])
                    current_location = location
        
        # Calculate the total distance of this route
        total_distance = self.graph.calculate_route_distance(route)
            
        return route, total_distance, package_operations
    
    def _find_path_respecting_constraints(self, start, end, current_route):
        """Find the shortest path that respects constraints when added to current route"""
        # Get the shortest path
        path, distance = self.graph.find_shortest_path(start, end)
        
        if not path:
            return None, float('inf')
        
        # Check if adding this path would violate constraints
        test_route = current_route.copy()
        # Add each step of the path (excluding start if it's already the last item in route)
        if test_route and test_route[-1] == path[0]:
            test_route.extend(path[1:])
        else:
            test_route.extend(path)
            
        valid, _ = self.constraints.validate_route(test_route)
        
        if valid:
            return path, distance
        
        # If invalid, we need to find an alternative path
        # This could be quite complex - for simplicity, we'll return None
        return None, float('inf')