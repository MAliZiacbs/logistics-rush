# routing.py

import streamlit as st
import networkx as nx
import diagnostics
from config import DISTANCES, LOCATIONS, check_constraints
from feature_road_closures import is_road_closed
from routing_optimization import apply_two_opt, apply_three_opt, strategic_package_handling

def get_distance(loc1, loc2):
    if is_road_closed(loc1, loc2):
        distance = float('inf')
        diagnostics.log_distance_calculation(loc1, loc2, distance)
        return distance
    if (loc1, loc2) in DISTANCES:
        distance = DISTANCES[(loc1, loc2)]
        diagnostics.log_distance_calculation(loc1, loc2, distance)
        return distance
    elif (loc2, loc1) in DISTANCES:
        distance = DISTANCES[(loc2, loc1)]
        diagnostics.log_distance_calculation(loc1, loc2, distance)
        return distance
    else:
        distance = float('inf')
        diagnostics.log_distance_calculation(loc1, loc2, distance)
        return distance

def find_detour(from_loc, to_loc):
    """Find shortest detour using Dijkstra's algorithm."""
    G = nx.Graph()
    for loc in LOCATIONS:
        G.add_node(loc)
    from config import ROAD_SEGMENTS
    for loc1, loc2 in ROAD_SEGMENTS:
        if not is_road_closed(loc1, loc2):
            d = get_distance(loc1, loc2)
            if d != float('inf'):
                G.add_edge(loc1, loc2, weight=d)
    try:
        path = nx.shortest_path(G, source=from_loc, target=to_loc, weight='weight')
        distance = nx.shortest_path_length(G, source=from_loc, target=to_loc, weight='weight')
        return path, distance
    except nx.NetworkXNoPath:
        return None, float('inf')

def calculate_segment_path(from_loc, to_loc):
    direct_distance = get_distance(from_loc, to_loc)
    if direct_distance != float('inf'):
        return [from_loc, to_loc], direct_distance
    detour_route, detour_distance = find_detour(from_loc, to_loc)
    if detour_route:
        diagnostics.log_distance_calculation(from_loc, to_loc, detour_distance, False, detour_route)
        return detour_route, detour_distance
    return None, float('inf')

@diagnostics.catch_and_log_exceptions
def calculate_route_distance(route):
    if len(route) <= 1:
        return None, 0
    total_distance = 0
    full_path = []
    loc_route = [r["location"] for r in route] if isinstance(route[0], dict) else route
    for i in range(len(loc_route) - 1):
        if is_road_closed(loc_route[i], loc_route[i+1]):
            segment_path, segment_distance = find_detour(loc_route[i], loc_route[i+1])
        else:
            segment_path, segment_distance = calculate_segment_path(loc_route[i], loc_route[i+1])
        if segment_distance == float('inf'):
            diagnostics.log_error("Route Distance", f"No path found between {loc_route[i]} and {loc_route[i+1]}")
            return None, float('inf')
        total_distance += segment_distance
        if i == 0:
            full_path.extend(segment_path)
        else:
            full_path.extend(segment_path[1:])
    return full_path, total_distance

def is_valid_route(route):
    for i in range(len(route) - 1):
        segment_path, _ = calculate_segment_path(route[i], route[i+1])
        if segment_path is None:
            return False
    return True

def calculate_total_distance(route):
    total = 0
    for i in range(len(route) - 1):
        dist = get_distance(route[i], route[i+1])
        if dist == float('inf'):
            _, dist = find_detour(route[i], route[i+1])
        if dist == float('inf'):
            return float('inf')
        total += dist
    return total

def nearest_neighbor_route(start, locations):
    route = [start]
    remaining = [loc for loc in locations if loc != start]
    while remaining:
        current = route[-1]
        nearest = None
        min_dist = float('inf')
        for loc in remaining:
            dist = get_distance(current, loc)
            if dist == float('inf'):
                _, dist = find_detour(current, loc)
            if dist < min_dist:
                min_dist = dist
                nearest = loc
        if nearest is None:
            break
        route.append(nearest)
        remaining.remove(nearest)
    return route

def insertion_route(start, locations):
    route = [start]
    remaining = [loc for loc in locations if loc != start]
    farthest = None
    max_dist = -1
    for loc in remaining:
        dist = get_distance(start, loc)
        if dist == float('inf'):
            _, dist = find_detour(start, loc)
        if dist > max_dist and dist != float('inf'):
            max_dist = dist
            farthest = loc
    if farthest:
        route.append(farthest)
        remaining.remove(farthest)
        route.append(start)
    while remaining:
        best_loc = None
        best_pos = 0
        best_increase = float('inf')
        for loc in remaining:
            for i in range(1, len(route)):
                prev = route[i-1]
                next = route[i]
                current_dist = get_distance(prev, next)
                if current_dist == float('inf'):
                    _, current_dist = find_detour(prev, next)
                dist1 = get_distance(prev, loc)
                if dist1 == float('inf'):
                    _, dist1 = find_detour(prev, loc)
                dist2 = get_distance(loc, next)
                if dist2 == float('inf'):
                    _, dist2 = find_detour(loc, next)
                if current_dist == float('inf') or dist1 == float('inf') or dist2 == float('inf'):
                    continue
                increase = dist1 + dist2 - current_dist
                if increase < best_increase:
                    best_increase = increase
                    best_loc = loc
                    best_pos = i
        if best_loc is None:
            break
        route.insert(best_pos, best_loc)
        remaining.remove(best_loc)
    return route

def mst_approximation(start, locations):
    G = nx.Graph()
    all_locs = [start] + [loc for loc in locations if loc != start]
    for i, loc1 in enumerate(all_locs):
        for loc2 in all_locs[i+1:]:
            dist = get_distance(loc1, loc2)
            if dist == float('inf'):
                _, dist = find_detour(loc1, loc2)
            if dist != float('inf'):
                G.add_edge(loc1, loc2, weight=dist)
    if not nx.is_connected(G):
        return None
    mst = nx.minimum_spanning_tree(G)
    dfs_path = list(nx.dfs_preorder_nodes(mst, source=start))
    if set(dfs_path) != set(all_locs):
        return None
    return dfs_path

@diagnostics.catch_and_log_exceptions
def solve_tsp_improved(start_location, locations, packages):
    # Build graph for distances
    G = nx.Graph()
    for loc in locations:
        G.add_node(loc)
    for loc1 in locations:
        for loc2 in locations:
            if loc1 != loc2:
                dist = get_distance(loc1, loc2)
                if dist != float('inf'):
                    G.add_edge(loc1, loc2, weight=dist)
    diagnostics.log_event("Route Generation", "Trying nearest neighbor strategy")
    route_candidates = []
    nn_route = nearest_neighbor_route(start_location, locations)
    if nn_route and check_constraints(nn_route):
        route_candidates.append((nn_route, "nearest_neighbor"))
        diagnostics.log_event("Route Generation", "Valid nearest neighbor route found")
    diagnostics.log_event("Route Generation", "Trying insertion strategy")
    ins_route = insertion_route(start_location, locations)
    if ins_route and check_constraints(ins_route):
        route_candidates.append((ins_route, "insertion"))
        diagnostics.log_event("Route Generation", "Valid insertion route found")
    diagnostics.log_event("Route Generation", "Trying MST approximation strategy")
    mst_route = mst_approximation(start_location, locations)
    if mst_route and check_constraints(mst_route):
        route_candidates.append((mst_route, "mst"))
        diagnostics.log_event("Route Generation", "Valid MST route found")
    # Constraint-based ordering
    constraint_route = [start_location]
    for loc in ["Warehouse", "Distribution Center", "Shop", "Home"]:
        if loc not in constraint_route:
            constraint_route.append(loc)
    if check_constraints(constraint_route):
        route_candidates.append((constraint_route, "constraint_based"))
        diagnostics.log_event("Route Generation", "Valid constraint-based route found")
    max_brute_force_size = 8
    if len(locations) <= max_brute_force_size:
        diagnostics.log_event("Route Generation", "Trying brute force for small problem")
        valid_perms = []
        from itertools import permutations
        max_perms = 1000 if len(locations) > 6 else None
        perm_count = 0
        for perm in permutations(locations):
            perm_count += 1
            if max_perms is not None and perm_count > max_perms:
                diagnostics.log_event("Route Generation", f"Brute force search stopped after {max_perms} permutations")
                break
            if perm[0] != start_location:
                continue
            if check_constraints(list(perm)):
                valid_perms.append(perm)
        best_perm = None
        best_dist = float('inf')
        for perm in valid_perms:
            dist = calculate_total_distance(list(perm))
            if dist < best_dist:
                best_dist = dist
                best_perm = perm
        if best_perm:
            route_candidates.append((list(best_perm), "brute_force"))
            diagnostics.log_event("Route Generation", f"Valid brute force route found with distance {best_dist}")
    best_candidate = None
    best_distance = float('inf')
    for candidate, method in route_candidates:
        _, dist = calculate_route_distance(candidate)
        if dist < best_distance:
            best_distance = dist
            best_candidate = candidate
    if best_candidate is None:
        diagnostics.log_error("TSP Solver", "No valid route found, using fallback")
        best_candidate = nearest_neighbor_route(start_location, locations)
        best_distance = calculate_total_distance(best_candidate)
    diagnostics.log_optimal_route_data(best_candidate, best_candidate, best_distance)
    return best_candidate, best_candidate, best_distance
