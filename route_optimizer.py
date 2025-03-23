from constraints_manager import ConstraintsManager

class RouteOptimizer:
    def __init__(self, logistics_graph):
        """Initialize with a LogisticsGraph instance"""
        self.graph = logistics_graph
        self.constraints = ConstraintsManager()
    
    def find_optimal_route(self, start_location, required_locations, packages):
        """Find a realistic optimal route that properly accounts for package deliveries"""
        # Enhanced diagnostics
        optimization_log = {
            "start_location": start_location,
            "required_locations": required_locations.copy(),
            "packages": [{
                "id": p.id, 
                "pickup": p.pickup, 
                "delivery": p.delivery, 
                "status": p.status
            } for p in packages],
            "closed_roads": self.graph.closed_roads.copy(),
            "stages": []
        }
        
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
        
        optimization_log["stages"].append({
            "stage": "initialization",
            "route_so_far": route.copy(),
            "current_location": current_location,
            "handled_packages": list(handled_packages)
        })
        
        # First pass: handle critical packages that match constraints
        for package in packages:
            # Skip if already handled
            if package.id in handled_packages:
                continue
                
            # Enhanced diagnostics for this package
            package_log = {
                "stage": "critical_package_handling",
                "package_id": package.id,
                "pickup": package.pickup,
                "delivery": package.delivery,
                "steps": []
            }
            
            # Special case: Warehouse → Shop package (constraint)
            if package.pickup == "Warehouse" and package.delivery == "Shop":
                package_log["package_type"] = "warehouse_to_shop"
                
                # Only add if we can reach both locations
                path_to_pickup, pickup_distance = self.graph.find_shortest_path(current_location, package.pickup)
                
                package_log["steps"].append({
                    "action": "check_path_to_pickup",
                    "from": current_location,
                    "to": package.pickup,
                    "path_found": path_to_pickup is not None,
                    "path": path_to_pickup,
                    "distance": pickup_distance
                })
                
                if path_to_pickup:
                    path_to_delivery, delivery_distance = self.graph.find_shortest_path(package.pickup, package.delivery)
                    
                    package_log["steps"].append({
                        "action": "check_path_to_delivery",
                        "from": package.pickup,
                        "to": package.delivery,
                        "path_found": path_to_delivery is not None,
                        "path": path_to_delivery,
                        "distance": delivery_distance
                    })
                    
                    if path_to_delivery:
                        # First visit the pickup location if not already there
                        if current_location != package.pickup:
                            route.append(package.pickup)
                            package_log["steps"].append({
                                "action": "add_to_route",
                                "location": package.pickup,
                                "reason": "pickup"
                            })
                            current_location = package.pickup
                            
                        package_operations.append((package.pickup, "pickup", package.id))
                        
                        # Then visit the delivery location
                        route.append(package.delivery)
                        package_log["steps"].append({
                            "action": "add_to_route",
                            "location": package.delivery,
                            "reason": "delivery"
                        })
                        package_operations.append((package.delivery, "delivery", package.id))
                        
                        # Update current location and mark package as handled
                        current_location = package.delivery
                        handled_packages.add(package.id)
                        package_log["handled"] = True
                    else:
                        package_log["handled"] = False
                        package_log["reason"] = "no_path_to_delivery"
                else:
                    package_log["handled"] = False
                    package_log["reason"] = "no_path_to_pickup"
            
            # Special case: Distribution Center → Home package (constraint)
            elif package.pickup == "Distribution Center" and package.delivery == "Home":
                package_log["package_type"] = "distribution_to_home"
                
                # Only add if we can reach both locations
                path_to_pickup, pickup_distance = self.graph.find_shortest_path(current_location, package.pickup)
                
                package_log["steps"].append({
                    "action": "check_path_to_pickup",
                    "from": current_location,
                    "to": package.pickup,
                    "path_found": path_to_pickup is not None,
                    "path": path_to_pickup,
                    "distance": pickup_distance
                })
                
                if path_to_pickup:
                    path_to_delivery, delivery_distance = self.graph.find_shortest_path(package.pickup, package.delivery)
                    
                    package_log["steps"].append({
                        "action": "check_path_to_delivery",
                        "from": package.pickup,
                        "to": package.delivery,
                        "path_found": path_to_delivery is not None,
                        "path": path_to_delivery,
                        "distance": delivery_distance
                    })
                    
                    if path_to_delivery:
                        # First visit the pickup location if not already there
                        if current_location != package.pickup:
                            route.append(package.pickup)
                            package_log["steps"].append({
                                "action": "add_to_route",
                                "location": package.pickup,
                                "reason": "pickup"
                            })
                            current_location = package.pickup
                            
                        package_operations.append((package.pickup, "pickup", package.id))
                        
                        # Then visit the delivery location
                        route.append(package.delivery)
                        package_log["steps"].append({
                            "action": "add_to_route",
                            "location": package.delivery,
                            "reason": "delivery"
                        })
                        package_operations.append((package.delivery, "delivery", package.id))
                        
                        # Update current location and mark package as handled
                        current_location = package.delivery
                        handled_packages.add(package.id)
                        package_log["handled"] = True
                    else:
                        package_log["handled"] = False
                        package_log["reason"] = "no_path_to_delivery"
                else:
                    package_log["handled"] = False
                    package_log["reason"] = "no_path_to_pickup"
            
            # Add package log to optimization log
            optimization_log["stages"].append(package_log)
        
        # Update optimization log after critical packages
        optimization_log["stages"].append({
            "stage": "after_critical_packages",
            "route_so_far": route.copy(),
            "current_location": current_location,
            "handled_packages": list(handled_packages),
            "operations_so_far": package_operations.copy()
        })
        
        # Second pass: handle remaining packages
        for package in packages:
            # Skip if already handled
            if package.id in handled_packages:
                continue
                
            # Enhanced diagnostics for this package
            package_log = {
                "stage": "regular_package_handling",
                "package_id": package.id,
                "pickup": package.pickup,
                "delivery": package.delivery,
                "steps": []
            }
            
            # Find path to pickup
            path_to_pickup, pickup_distance = self.graph.find_shortest_path(current_location, package.pickup)
            
            package_log["steps"].append({
                "action": "check_path_to_pickup",
                "from": current_location,
                "to": package.pickup,
                "path_found": path_to_pickup is not None,
                "path": path_to_pickup,
                "distance": pickup_distance
            })
            
            if path_to_pickup:
                # First visit the pickup location if not already there
                if current_location != package.pickup:
                    route.append(package.pickup)
                    package_log["steps"].append({
                        "action": "add_to_route",
                        "location": package.pickup,
                        "reason": "pickup"
                    })
                    current_location = package.pickup
                
                package_operations.append((package.pickup, "pickup", package.id))
                
                # Find path to delivery
                path_to_delivery, delivery_distance = self.graph.find_shortest_path(current_location, package.delivery)
                
                package_log["steps"].append({
                    "action": "check_path_to_delivery",
                    "from": current_location,
                    "to": package.delivery,
                    "path_found": path_to_delivery is not None,
                    "path": path_to_delivery,
                    "distance": delivery_distance
                })
                
                if path_to_delivery:
                    # Visit the delivery location
                    route.append(package.delivery)
                    package_log["steps"].append({
                        "action": "add_to_route",
                        "location": package.delivery,
                        "reason": "delivery"
                    })
                    package_operations.append((package.delivery, "delivery", package.id))
                    
                    # Update current location and mark package as handled
                    current_location = package.delivery
                    handled_packages.add(package.id)
                    package_log["handled"] = True
                else:
                    package_log["handled"] = False
                    package_log["reason"] = "no_path_to_delivery"
            else:
                package_log["handled"] = False
                package_log["reason"] = "no_path_to_pickup"
            
            # Add package log to optimization log
            optimization_log["stages"].append(package_log)
        
        # Update optimization log after all packages
        optimization_log["stages"].append({
            "stage": "after_all_packages",
            "route_so_far": route.copy(),
            "current_location": current_location,
            "handled_packages": list(handled_packages),
            "operations_so_far": package_operations.copy()
        })
        
        # Third pass: make sure we've visited all required locations
        for location in required_locations:
            if location not in route:
                # Enhanced diagnostics for location visit
                location_log = {
                    "stage": "visit_required_location",
                    "location": location,
                    "steps": []
                }
                
                # Try to find a path to this location
                path, distance = self.graph.find_shortest_path(current_location, location)
                
                location_log["steps"].append({
                    "action": "check_path",
                    "from": current_location,
                    "to": location,
                    "path_found": path is not None,
                    "path": path,
                    "distance": distance
                })
                
                if path:
                    route.append(location)
                    location_log["steps"].append({
                        "action": "add_to_route",
                        "location": location,
                        "reason": "required_location"
                    })
                    current_location = location
                    location_log["visited"] = True
                else:
                    location_log["visited"] = False
                    location_log["reason"] = "no_path_available"
                
                # Add location log to optimization log
                optimization_log["stages"].append(location_log)
        
        # Update optimization log after visiting all locations
        optimization_log["stages"].append({
            "stage": "after_all_locations",
            "route_so_far": route.copy()
        })
        
        # Finally, check if the route satisfies constraints
        valid, message = self.constraints.validate_route(route)
        
        # Enhanced diagnostics for route validation
        constraint_validation = {
            "stage": "constraint_validation",
            "route": route.copy(),
            "valid": valid,
            "message": message
        }
        
        optimization_log["stages"].append(constraint_validation)
        
        if not valid:
            # If not valid, use the constraint-based route as fallback
            fallback_route = self._create_constraint_satisfied_route(start_location, required_locations)
            
            # Enhanced diagnostics for fallback
            fallback_log = {
                "stage": "fallback_route",
                "reason": "constraint_violation",
                "fallback_route": fallback_route
            }
            
            optimization_log["stages"].append(fallback_log)
            
            # Calculate distance for fallback route
            _, fallback_distance = self.graph.find_path_distance(fallback_route)
            
            # Final optimization log
            optimization_log["final_route"] = fallback_route
            optimization_log["final_distance"] = fallback_distance
            optimization_log["used_fallback"] = True
            optimization_log["operations"] = []
            
            return fallback_route, fallback_distance, [], optimization_log
        
        # Calculate the total distance of this route
        _, total_distance = self.graph.find_path_distance(route)
        
        # Enhanced diagnostics for path distance calculation
        distance_log = {
            "stage": "calculate_path_distance",
            "route": route.copy(),
            "distance": total_distance
        }
        
        optimization_log["stages"].append(distance_log)
        
        if total_distance == float('inf'):
            # If path is invalid, use constraint-based route
            fallback_route = self._create_constraint_satisfied_route(start_location, required_locations)
            
            # Enhanced diagnostics for fallback
            fallback_log = {
                "stage": "fallback_route",
                "reason": "infinite_distance",
                "fallback_route": fallback_route
            }
            
            optimization_log["stages"].append(fallback_log)
            
            _, fallback_distance = self.graph.find_path_distance(fallback_route)
            
            # Final optimization log
            optimization_log["final_route"] = fallback_route
            optimization_log["final_distance"] = fallback_distance
            optimization_log["used_fallback"] = True
            optimization_log["operations"] = []
            
            return fallback_route, fallback_distance, [], optimization_log
        
        # Final optimization log
        optimization_log["final_route"] = route
        optimization_log["final_distance"] = total_distance
        optimization_log["used_fallback"] = False
        optimization_log["operations"] = package_operations
        
        return route, total_distance, package_operations, optimization_log
    
    def _create_constraint_satisfied_route(self, start, locations):
        """Create a route that satisfies all constraints"""
        # Enhanced diagnostics
        constraint_route_log = {
            "start_location": start,
            "required_locations": locations.copy(),
            "steps": []
        }
        
        route = [start]
        remaining = [loc for loc in locations if loc != start]
        
        constraint_route_log["steps"].append({
            "action": "initialization",
            "route_so_far": route.copy(),
            "remaining": remaining.copy()
        })
        
        # First handle Warehouse and Shop (Warehouse must come before Shop)
        if "Warehouse" not in route and "Warehouse" in remaining:
            route.append("Warehouse")
            remaining.remove("Warehouse")
            
            constraint_route_log["steps"].append({
                "action": "add_to_route",
                "location": "Warehouse",
                "reason": "ensure_warehouse_first"
            })
        
        if "Shop" in remaining:
            # Make sure Warehouse is before Shop
            if "Warehouse" in route:
                route.append("Shop")
                remaining.remove("Shop")
                
                constraint_route_log["steps"].append({
                    "action": "add_to_route",
                    "location": "Shop",
                    "reason": "warehouse_before_shop"
                })
        
        # Then handle Distribution Center and Home (DC must come before Home)
        if "Distribution Center" in remaining:
            route.append("Distribution Center")
            remaining.remove("Distribution Center")
            
            constraint_route_log["steps"].append({
                "action": "add_to_route",
                "location": "Distribution Center",
                "reason": "ensure_dc_before_home"
            })
        
        if "Home" in remaining:
            # Make sure Distribution Center is before Home
            if "Distribution Center" in route:
                route.append("Home")
                remaining.remove("Home")
                
                constraint_route_log["steps"].append({
                    "action": "add_to_route",
                    "location": "Home",
                    "reason": "dc_before_home"
                })
        
        # Add any remaining locations
        if remaining:
            constraint_route_log["steps"].append({
                "action": "add_remaining",
                "locations": remaining.copy()
            })
            route.extend(remaining)
        
        # Validate the final constraint route
        path_exists = True
        for i in range(len(route) - 1):
            path, _ = self.graph.find_shortest_path(route[i], route[i+1])
            if path is None:
                path_exists = False
                break
        
        constraint_route_log["path_exists_for_all_segments"] = path_exists
        constraint_route_log["final_route"] = route
        
        return route
    
    def _apply_two_opt(self, route):
        """Apply 2-opt local search to improve a route"""
        # Enhanced diagnostics
        two_opt_log = {
            "initial_route": route.copy(),
            "iterations": []
        }
        
        improved = True
        best_route = route.copy()
        
        # Limit iterations to prevent excessive computation
        max_iterations = 10
        iteration = 0
        
        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            
            iteration_log = {
                "iteration": iteration,
                "improvements": []
            }
            
            for i in range(1, len(best_route) - 1):
                for j in range(i + 1, len(best_route)):
                    # Create a new route by reversing the segment between i and j
                    new_route = best_route.copy()
                    new_route[i:j+1] = reversed(new_route[i:j+1])
                    
                    # Check if the new route is valid
                    valid, message = self.constraints.validate_route(new_route)
                    
                    improvement_log = {
                        "i": i,
                        "j": j,
                        "new_route": new_route.copy(),
                        "constraints_valid": valid,
                        "constraints_message": message
                    }
                    
                    if not valid:
                        improvement_log["improved"] = False
                        improvement_log["reason"] = "constraints_violated"
                        iteration_log["improvements"].append(improvement_log)
                        continue
                    
                    # Check if the new route is better
                    _, old_distance = self.graph.find_path_distance(best_route)
                    _, new_distance = self.graph.find_path_distance(new_route)
                    
                    improvement_log["old_distance"] = old_distance
                    improvement_log["new_distance"] = new_distance
                    
                    if new_distance < old_distance:
                        best_route = new_route
                        improved = True
                        improvement_log["improved"] = True
                    else:
                        improvement_log["improved"] = False
                        improvement_log["reason"] = "no_improvement_in_distance"
                    
                    iteration_log["improvements"].append(improvement_log)
            
            iteration_log["improved_this_iteration"] = improved
            iteration_log["current_best_route"] = best_route.copy()
            two_opt_log["iterations"].append(iteration_log)
        
        two_opt_log["final_route"] = best_route
        two_opt_log["total_iterations"] = iteration
        two_opt_log["reached_max_iterations"] = iteration >= max_iterations
        
        return best_route