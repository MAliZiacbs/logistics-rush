class RouteOptimizer:
    def __init__(self, logistics_graph, constraints_manager=None):
        """Initialize with a LogisticsGraph instance and optional ConstraintsManager"""
        self.graph = logistics_graph
        self.constraints = constraints_manager
    
    def find_optimal_route(self, start_location, required_locations, packages):
        """Find the globally optimal route by evaluating all valid package orderings"""
        # Generate all possible package handling orders
        packages_list = list(packages)
        all_package_orders = self._generate_all_package_orders(packages_list)
        
        best_route = None
        best_distance = float('inf')
        best_operations = None
        
        # Try each possible package order
        for package_order in all_package_orders:
            route, distance, operations = self._evaluate_package_order(
                start_location, required_locations, package_order)
            
            if route and distance < best_distance:
                best_route = route
                best_distance = distance
                best_operations = operations
        
        # If we couldn't find any valid route, return empty results
        if not best_route:
            return [start_location], float('inf'), []
            
        return best_route, best_distance, best_operations

    def _generate_all_package_orders(self, packages):
        """Generate all possible orders for handling packages"""
        # For 3 packages, we have 6 possible orderings (3!)
        if not packages:
            return [[]]
        
        result = []
        for i, pkg in enumerate(packages):
            rest = packages[:i] + packages[i+1:]
            for order in self._generate_all_package_orders(rest):
                result.append([pkg] + order)
        
        return result

    def _evaluate_package_order(self, start_location, required_locations, package_order):
        """Evaluate a specific package handling order"""
        route = [start_location]
        current_location = start_location
        package_operations = []
        total_distance = 0
        
        # Process each package in the given order
        for package in package_order:
            # Find path to pickup
            pickup_path, pickup_distance = self._find_constraint_respecting_path(
                current_location, package.pickup, route, None)
            
            if not pickup_path:
                return None, float('inf'), None  # Invalid order
            
            # Add pickup path (excluding start if it's the same as current)
            if current_location != package.pickup:
                route.extend(pickup_path[1:])
                total_distance += pickup_distance
                current_location = package.pickup
            
            package_operations.append((package.pickup, "pickup", package.id))
            
            # Find path to delivery
            delivery_path, delivery_distance = self._find_constraint_respecting_path(
                current_location, package.delivery, route, package)
            
            if not delivery_path:
                return None, float('inf'), None  # Invalid order
            
            # Add delivery path
            route.extend(delivery_path[1:])
            total_distance += delivery_distance
            current_location = package.delivery
            
            package_operations.append((package.delivery, "delivery", package.id))
        
        # Ensure all required locations are visited
        for location in required_locations:
            if location not in route:
                path, distance = self._find_constraint_respecting_path(
                    current_location, location, route, None)
                
                if path:
                    route.extend(path[1:])
                    total_distance += distance
                    current_location = location
        
        return route, total_distance, package_operations
    
    def _find_constraint_respecting_path(self, start, end, current_route, carrying_package=None):
        """
        Find a path from start to end that respects all constraints.
        
        Uses a modified breadth-first search to find the shortest path that
        satisfies all constraints.
        """
        # If no constraints or start and end are the same, use simple path
        if (not self.constraints or not self.constraints.get_active_constraints()) or start == end:
            path, distance = self.graph.find_shortest_path(start, end)
            return path, distance
        
        # Use breadth-first search to find a constraint-respecting path
        visited = set()
        queue = [(start, [start], 0)]  # (current, path, distance)
        
        while queue:
            current, path, distance = queue.pop(0)
            
            if current == end:
                # Found a path to the destination
                return path, distance
            
            if current in visited:
                continue
                
            visited.add(current)
            
            # Get all neighbors
            for neighbor in self.graph.get_connected_locations(current):
                if neighbor in visited:
                    continue
                    
                # Check if adding this step would violate constraints
                new_path = path + [neighbor]
                test_route = current_route.copy()
                
                # If the start of new_path is the same as the end of test_route,
                # avoid duplicating the location
                if test_route and test_route[-1] == new_path[0]:
                    test_route.extend(new_path[1:])
                else:
                    test_route.extend(new_path[1:])
                
                # Check if this route satisfies constraints
                valid, _, _ = self.constraints.validate_route(test_route)
                
                if valid:
                    # Calculate the new distance
                    edge_distance = self.graph.get_edge_weight(current, neighbor)
                    new_distance = distance + edge_distance
                    
                    # Add to queue, sorted by distance (makes it more like Dijkstra's)
                    queue.append((neighbor, new_path, new_distance))
                    # Sort queue by distance for better efficiency
                    queue.sort(key=lambda x: x[2])
        
        # If we reach here, no valid path was found
        return None, float('inf')