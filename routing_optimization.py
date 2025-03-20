import random
import math
import networkx as nx
from config import LOCATIONS, check_constraints

# This module requires functions from routing.py, but we import them locally where needed
# to avoid circular import issues

def apply_two_opt(route):
    """Apply 2-opt local search to improve a route"""
    # Handle circular imports
    from routing import calculate_total_distance
    
    loc_route = route if isinstance(route[0], str) else [r["location"] for r in route]
    improved = True
    best_distance = calculate_total_distance(loc_route)
    best_route = loc_route.copy()
    
    # Limit iterations to prevent excessive computation
    max_iterations = 100
    iteration = 0
    
    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        
        for i in range(1, len(loc_route) - 2):
            for j in range(i + 1, len(loc_route) - 1):
                # Skip if this would violate constraints
                new_route = loc_route.copy()
                new_route[i:j+1] = reversed(new_route[i:j+1])
                if not check_constraints(new_route):
                    continue
                
                # Check if this improves the route
                new_distance = calculate_total_distance(new_route)
                if new_distance < best_distance:
                    best_distance = new_distance
                    best_route = new_route.copy()
                    improved = True
        
        if improved:
            loc_route = best_route.copy()
    
    return best_route

def apply_three_opt(route):
    """Apply 3-opt local search to improve a route (more powerful than 2-opt)"""
    # Handle circular imports
    from routing import calculate_total_distance
    
    loc_route = route if isinstance(route[0], str) else [r["location"] for r in route]
    improved = True
    best_distance = calculate_total_distance(loc_route)
    best_route = loc_route.copy()
    
    # Only attempt 3-opt if route is long enough
    if len(loc_route) < 6:
        return best_route
    
    # Limited number of iterations to prevent excessive computation
    iteration_limit = 5
    iterations = 0
    
    while improved and iterations < iteration_limit:
        improved = False
        iterations += 1
        
        # Try all possible 3-opt moves (limited to reasonable subset for performance)
        possible_i = range(1, min(len(loc_route) - 4, 4))
        possible_j = range(2, min(len(loc_route) - 2, 5))
        possible_k = range(3, min(len(loc_route) - 1, 7))
        
        for i in possible_i:
            for j in possible_j:
                for k in possible_k:
                    if i < j < k:  # Ensure proper ordering
                        # Generate all possible reconnection patterns
                        for swap_type in range(4):  # Limit to 4 common reconnection patterns
                            new_route = loc_route.copy()
                            
                            # Apply the 3-opt move based on swap type
                            if swap_type == 0:
                                # Reverse segment i-j
                                new_route[i:j+1] = reversed(new_route[i:j+1])
                            elif swap_type == 1:
                                # Reverse segment j-k
                                new_route[j:k+1] = reversed(new_route[j:k+1])
                            elif swap_type == 2:
                                # Reverse segment i-k
                                new_route[i:k+1] = reversed(new_route[i:k+1])
                            elif swap_type == 3:
                                # More complex exchange
                                tmp = new_route[j:k+1] + new_route[i:j]
                                new_route[i:k+1] = tmp
                            
                            # Skip if this would violate constraints
                            if not check_constraints(new_route):
                                continue
                            
                            # Check if this improves the route
                            new_distance = calculate_total_distance(new_route)
                            if new_distance < best_distance:
                                best_distance = new_distance
                                best_route = new_route.copy()
                                improved = True
        
        if improved:
            loc_route = best_route.copy()
    
    return best_route

def simulated_annealing(route, max_iterations=1000, initial_temperature=100, cooling_rate=0.95):
    """
    Apply simulated annealing to improve a route.
    This can escape local optima better than 2-opt or 3-opt alone.
    """
    # Handle circular imports
    from routing import calculate_total_distance
    
    loc_route = route if isinstance(route[0], str) else [r["location"] for r in route]
    current_route = loc_route.copy()
    best_route = loc_route.copy()
    current_distance = calculate_total_distance(current_route)
    best_distance = current_distance
    
    temperature = initial_temperature
    
    for iteration in range(max_iterations):
        # Generate a neighbor by swapping two random locations
        # (respecting the constraint that the first location remains fixed)
        i = random.randint(1, len(current_route) - 2)
        j = random.randint(1, len(current_route) - 2)
        
        if i != j:
            new_route = current_route.copy()
            new_route[i], new_route[j] = new_route[j], new_route[i]
            
            # Skip if this would violate constraints
            if not check_constraints(new_route):
                continue
            
            new_distance = calculate_total_distance(new_route)
            
            # Calculate acceptance probability
            delta = new_distance - current_distance
            acceptance_probability = math.exp(-delta / temperature) if delta > 0 else 1.0
            
            # Accept new solution based on probability
            if random.random() < acceptance_probability:
                current_route = new_route
                current_distance = new_distance
                
                # Update best solution if this is better
                if current_distance < best_distance:
                    best_route = current_route.copy()
                    best_distance = current_distance
        
        # Cool down the temperature
        temperature *= cooling_rate
        
        # Stop if temperature is too low (system has "frozen")
        if temperature < 0.1:
            break
    
    return best_route

def strategic_package_handling(route, packages):
    """Optimize the route specifically for package handling opportunities"""
    # Handle circular imports
    from routing import calculate_total_distance, get_distance
    
    # Make sure route is not empty
    if not route or len(route) == 0:
        return route
    
    loc_route = route if isinstance(route[0], str) else [r["location"] for r in route]
    
    # Create a graph to find optimal paths between locations
    G = nx.Graph()
    for loc in LOCATIONS.keys():
        G.add_node(loc)
    for loc1, loc2 in [(loc1, loc2) for loc1 in LOCATIONS for loc2 in LOCATIONS if loc1 != loc2]:
        dist = get_distance(loc1, loc2)
        if dist != float('inf'):
            G.add_edge(loc1, loc2, weight=dist)
    
    # Create a map of which packages are available at each location
    location_packages = {}
    for loc in LOCATIONS.keys():
        location_packages[loc] = []
    
    for pkg in packages:
        if pkg["pickup"] in location_packages:
            location_packages[pkg["pickup"]].append(pkg)
    
    # Try to optimize the route by looking at package-handling opportunities
    optimized_route = loc_route.copy()
    
    # If the route is too short, no optimization is needed
    if len(optimized_route) <= 1:
        return optimized_route
        
    improvement_found = True
    
    # Limit optimization iterations
    max_iterations = 3
    current_iteration = 0
    
    while improvement_found and current_iteration < max_iterations:
        improvement_found = False
        current_iteration += 1
        
        # Look for opportunities to optimize each package pickup-delivery pair
        for i in range(len(optimized_route) - 1):  # This should be safe now
            current_loc = optimized_route[i]
            
            # Check if there are packages at this location
            packages_here = location_packages.get(current_loc, [])
            
            for pkg in packages_here:
                delivery_loc = pkg["delivery"]
                
                # Look ahead to see if this delivery location is in our route
                try:
                    delivery_idx = optimized_route.index(delivery_loc, i + 1)
                    
                    # If it's not the next location and there are intermediate locations,
                    # see if we can optimize
                    if delivery_idx > i + 1:
                        # Calculate the shortest path from current to delivery
                        try:
                            shortest_path = nx.shortest_path(G, current_loc, delivery_loc, weight='weight')
                            
                            # If the shortest path is different from our current sequence,
                            # consider replacing the segment
                            current_path = optimized_route[i:delivery_idx+1]
                            
                            if len(shortest_path) < len(current_path):
                                # Calculate distances to compare
                                current_dist = calculate_total_distance(current_path)
                                new_dist = calculate_total_distance(shortest_path)
                                
                                if new_dist < current_dist:
                                    # Ensure the new path doesn't violate constraints
                                    test_route = optimized_route.copy()
                                    test_route[i:delivery_idx+1] = shortest_path
                                    
                                    if check_constraints(test_route):
                                        optimized_route[i:delivery_idx+1] = shortest_path
                                        improvement_found = True
                        except nx.NetworkXNoPath:
                            pass  # No path exists, skip optimization
                except ValueError:
                    pass  # Delivery location not found in route after current position
    
    return optimized_route

def exploit_triangular_patterns(route, closed_roads):
    """
    Look for special cases where the AI can find shortcuts through triangular patterns
    that a human player might overlook.
    """
    # Handle circular imports
    from routing import calculate_total_distance, get_distance, find_detour, is_road_closed
    
    loc_route = route if isinstance(route[0], str) else [r["location"] for r in route]
    
    # Find triangular patterns in the graph
    triangular_patterns = []
    
    # Get all combinations of 3 locations
    for i, loc1 in enumerate(LOCATIONS.keys()):
        for j, loc2 in enumerate(LOCATIONS.keys()):
            for k, loc3 in enumerate(LOCATIONS.keys()):
                if i < j < k:  # Avoid duplicates
                    # Check if these form a triangle in the graph
                    edges = [
                        (loc1, loc2),
                        (loc2, loc3),
                        (loc3, loc1)
                    ]
                    
                    # Count available edges
                    available_edges = sum(1 for edge in edges if not is_road_closed(edge[0], edge[1]))
                    
                    # If exactly one edge is closed, we have a triangular pattern
                    if available_edges == 2:
                        triangular_patterns.append((loc1, loc2, loc3))
    
    # Try to exploit these patterns in the route
    improved_route = loc_route.copy()
    improvement_found = False
    
    for pattern in triangular_patterns:
        # Look for these locations in the route
        indices = []
        for loc in pattern:
            try:
                idx = improved_route.index(loc)
                indices.append((idx, loc))
            except ValueError:
                pass
        
        # If we have all three locations, try to optimize their order
        if len(indices) == 3:
            indices.sort()  # Sort by index
            
            # Get the locations in their current order
            current_order = [loc for _, loc in indices]
            
            # Try all possible permutations of these locations
            for perm in [(current_order[0], current_order[1], current_order[2]),
                         (current_order[0], current_order[2], current_order[1])]:
                # Skip if this would violate constraints
                test_route = improved_route.copy()
                for i, loc in zip([idx for idx, _ in indices], perm):
                    test_route[i] = loc
                
                if not check_constraints(test_route):
                    continue
                
                # Calculate distances
                current_distance = calculate_total_distance(improved_route)
                new_distance = calculate_total_distance(test_route)
                
                if new_distance < current_distance:
                    improved_route = test_route
                    improvement_found = True
    
    if improvement_found:
        return improved_route
    else:
        return loc_route

def genetic_algorithm(start, locations, population_size=50, generations=100, mutation_rate=0.1):
    """
    Apply a genetic algorithm to find an optimal route.
    More likely to find good solutions for complex problems.
    """
    # Handle circular imports
    from routing import calculate_total_distance
    
    # Initialize population with random permutations
    population = []
    for _ in range(population_size):
        route = [start] + random.sample([loc for loc in locations if loc != start], len(locations) - 1)
        if check_constraints(route):
            population.append(route)
    
    # If we couldn't create a valid initial population, return None
    if not population:
        return None
    
    for generation in range(generations):
        # Calculate fitness for each route
        fitness = []
        for route in population:
            distance = calculate_total_distance(route)
            # Higher fitness for shorter distances
            fitness.append(1.0 / distance if distance > 0 else float('inf'))
        
        # Create next generation
        next_population = []
        
        # Elitism: keep the best route
        best_idx = fitness.index(max(fitness))
        next_population.append(population[best_idx])
        
        # Create the rest of the next generation
        while len(next_population) < population_size:
            # Tournament selection
            parent1 = random.choices(population, weights=fitness, k=1)[0]
            parent2 = random.choices(population, weights=fitness, k=1)[0]
            
            # Ordered crossover
            child = ordered_crossover(parent1, parent2)
            
            # Mutation
            if random.random() < mutation_rate:
                child = mutate(child)
            
            # Only add valid routes
            if check_constraints(child):
                next_population.append(child)
        
        population = next_population
    
    # Return the best route from the final population
    best_route = min(population, key=calculate_total_distance)
    return best_route

def ordered_crossover(parent1, parent2):
    """Ordered crossover for genetic algorithm"""
    size = len(parent1)
    child = [None] * size
    
    # Always keep the starting location
    child[0] = parent1[0]
    
    # Choose random segment from parent1
    start, end = sorted(random.sample(range(1, size - 1), 2))
    for i in range(start, end + 1):
        child[i] = parent1[i]
    
    # Fill remaining positions with locations from parent2 in order
    j = 1
    for i in range(1, size):
        if child[i] is None:
            while parent2[j] in child:
                j += 1
                if j >= size:
                    j = 1
            child[i] = parent2[j]
            j += 1
            if j >= size:
                j = 1
    
    return child

def mutate(route):
    """Mutation operation for genetic algorithm"""
    # Don't change the starting location
    i, j = random.sample(range(1, len(route)), 2)
    route[i], route[j] = route[j], route[i]
    return route