# routing_optimization.py

import random
import math
import networkx as nx
from config import LOCATIONS, check_constraints

def apply_two_opt(route):
    from routing import calculate_total_distance
    loc_route = route if isinstance(route[0], str) else [r["location"] for r in route]
    improved = True
    best_distance = calculate_total_distance(loc_route)
    best_route = loc_route.copy()
    max_iterations = 100
    iteration = 0
    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        for i in range(1, len(loc_route) - 2):
            for j in range(i + 1, len(loc_route) - 1):
                new_route = loc_route.copy()
                new_route[i:j+1] = list(reversed(new_route[i:j+1]))
                if not check_constraints(new_route):
                    continue
                new_distance = calculate_total_distance(new_route)
                if new_distance < best_distance:
                    best_distance = new_distance
                    best_route = new_route.copy()
                    improved = True
        if improved:
            loc_route = best_route.copy()
    return best_route

def apply_three_opt(route):
    from routing import calculate_total_distance
    loc_route = route if isinstance(route[0], str) else [r["location"] for r in route]
    improved = True
    best_distance = calculate_total_distance(loc_route)
    best_route = loc_route.copy()
    if len(loc_route) < 6:
        return best_route
    iteration_limit = 5
    iterations = 0
    while improved and iterations < iteration_limit:
        improved = False
        iterations += 1
        possible_i = range(1, min(len(loc_route) - 4, 4))
        possible_j = range(2, min(len(loc_route) - 2, 5))
        possible_k = range(3, min(len(loc_route) - 1, 7))
        for i in possible_i:
            for j in possible_j:
                for k in possible_k:
                    if i < j < k:
                        for swap_type in range(4):
                            new_route = loc_route.copy()
                            if swap_type == 0:
                                new_route[i:j+1] = list(reversed(new_route[i:j+1]))
                            elif swap_type == 1:
                                new_route[j:k+1] = list(reversed(new_route[j:k+1]))
                            elif swap_type == 2:
                                new_route[i:k+1] = list(reversed(new_route[i:k+1]))
                            elif swap_type == 3:
                                tmp = new_route[j:k+1] + new_route[i:j]
                                new_route[i:k+1] = tmp
                            if not check_constraints(new_route):
                                continue
                            new_distance = calculate_total_distance(new_route)
                            if new_distance < best_distance:
                                best_distance = new_distance
                                best_route = new_route.copy()
                                improved = True
        if improved:
            loc_route = best_route.copy()
    return best_route

def simulated_annealing(route, max_iterations=1000, initial_temperature=100, cooling_rate=0.95):
    from routing import calculate_total_distance
    loc_route = route if isinstance(route[0], str) else [r["location"] for r in route]
    current_route = loc_route.copy()
    best_route = loc_route.copy()
    current_distance = calculate_total_distance(current_route)
    best_distance = current_distance
    temperature = initial_temperature
    for iteration in range(max_iterations):
        i = random.randint(1, len(current_route) - 2)
        j = random.randint(1, len(current_route) - 2)
        if i != j:
            new_route = current_route.copy()
            new_route[i], new_route[j] = new_route[j], new_route[i]
            if not check_constraints(new_route):
                continue
            new_distance = calculate_total_distance(new_route)
            delta = new_distance - current_distance
            acceptance_probability = math.exp(-delta / temperature) if delta > 0 else 1.0
            if random.random() < acceptance_probability:
                current_route = new_route
                current_distance = new_distance
                if current_distance < best_distance:
                    best_route = current_route.copy()
                    best_distance = current_distance
        temperature *= cooling_rate
        if temperature < 0.1:
            break
    return best_route

def strategic_package_handling(route, packages):
    from routing import calculate_total_distance, get_distance
    if not route or len(route) == 0:
        return route
    loc_route = route if isinstance(route[0], str) else [r["location"] for r in route]
    G = nx.Graph()
    for loc in LOCATIONS.keys():
        G.add_node(loc)
    for loc1, loc2 in [(l1, l2) for l1 in LOCATIONS for l2 in LOCATIONS if l1 != l2]:
        dist = get_distance(loc1, loc2)
        if dist != float('inf'):
            G.add_edge(loc1, loc2, weight=dist)
    location_packages = {loc: [] for loc in LOCATIONS.keys()}
    for pkg in packages:
        if pkg["pickup"] in location_packages:
            location_packages[pkg["pickup"]].append(pkg)
    optimized_route = loc_route.copy()
    if len(optimized_route) <= 1:
        return optimized_route
    improvement_found = True
    max_iterations = 3
    current_iteration = 0
    while improvement_found and current_iteration < max_iterations:
        improvement_found = False
        current_iteration += 1
        for i in range(len(optimized_route) - 1):
            current_loc = optimized_route[i]
            pickups = location_packages.get(current_loc, [])
            if pickups:
                new_route = optimized_route.copy()
                for pkg in pickups:
                    pickup_loc = pkg["pickup"]
                    delivery_loc = pkg["delivery"]
                    if pickup_loc in new_route and delivery_loc in new_route:
                        idx_pickup = new_route.index(pickup_loc)
                        idx_current = i
                        if idx_pickup > idx_current + 1:
                            new_route.pop(idx_pickup)
                            new_route.insert(idx_current+1, pickup_loc)
                            if check_constraints(new_route):
                                if calculate_total_distance(new_route) < calculate_total_distance(optimized_route):
                                    optimized_route = new_route
                                    improvement_found = True
        if improvement_found:
            loc_route = optimized_route.copy()
    return optimized_route
