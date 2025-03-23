import networkx as nx
import copy

class LogisticsGraph:
    def __init__(self, locations, road_segments, distances):
        """Initialize the graph with locations and roads"""
        self.graph = nx.Graph()
        
        # Add all locations as nodes
        for loc in locations:
            self.graph.add_node(loc)
        
        # Add all roads as edges with distances as weights
        for (loc1, loc2) in road_segments:
            weight = distances.get((loc1, loc2), distances.get((loc2, loc1), 300))
            self.graph.add_edge(loc1, loc2, weight=weight)
            
        # Keep a copy of the original data
        self.locations = locations
        self.road_segments = road_segments
        self.distances = distances
        self.closed_roads = []
        
        # Enhanced diagnostics - keep history of graph changes
        self.original_graph = copy.deepcopy(self.graph)
        self.edge_history = []
    
    def close_road(self, loc1, loc2):
        """Close a road between two locations"""
        # Enhanced diagnostics - log before state
        before_state = {
            "has_edge": self.graph.has_edge(loc1, loc2),
            "closed_roads": self.closed_roads.copy()
        }
        
        if self.graph.has_edge(loc1, loc2):
            self.graph.remove_edge(loc1, loc2)
            self.closed_roads.append((loc1, loc2))
            
            # Enhanced diagnostics - log action
            self.edge_history.append({
                "action": "close_road",
                "locations": (loc1, loc2),
                "before": before_state,
                "after": {
                    "has_edge": self.graph.has_edge(loc1, loc2),
                    "closed_roads": self.closed_roads.copy()
                },
                "success": True
            })
            return True
        
        # Enhanced diagnostics - log failed action
        self.edge_history.append({
            "action": "close_road",
            "locations": (loc1, loc2),
            "before": before_state,
            "after": {
                "has_edge": self.graph.has_edge(loc1, loc2),
                "closed_roads": self.closed_roads.copy()
            },
            "success": False,
            "reason": "edge_not_found"
        })
        return False
    
    def is_road_closed(self, loc1, loc2):
        """Check if a road is closed"""
        result = not self.graph.has_edge(loc1, loc2)
        
        # Enhanced diagnostics - log check with detailed state
        self.edge_history.append({
            "action": "check_road_closed",
            "locations": (loc1, loc2),
            "result": result,
            "in_closed_roads_list": (loc1, loc2) in self.closed_roads or (loc2, loc1) in self.closed_roads,
            "graph_has_edge": self.graph.has_edge(loc1, loc2)
        })
        return result
    
    def find_shortest_path(self, start, end):
        """Find the shortest path between two locations, ensuring no closed roads are used"""
        # Enhanced diagnostics - log path request
        path_request = {
            "action": "find_shortest_path",
            "from": start,
            "to": end,
            "graph_state": {
                "nodes": list(self.graph.nodes()),
                "edges": list(self.graph.edges()),
                "closed_roads": self.closed_roads.copy()
            }
        }
        
        # If there's no connection at all, return none
        if not nx.has_path(self.graph, start, end):
            path_request["result"] = {
                "path_found": False,
                "reason": "no_path_exists"
            }
            self.edge_history.append(path_request)
            return None, float('inf')
        
        try:
            # Get the shortest path using NetworkX
            path = nx.shortest_path(self.graph, start, end, weight='weight')
            
            # Calculate the total distance and verify each segment
            distance = 0
            segment_validation = []
            
            for i in range(len(path) - 1):
                # Verify that each segment is not a closed road
                if not self.graph.has_edge(path[i], path[i+1]):
                    segment_validation.append({
                        "segment": (path[i], path[i+1]),
                        "valid": False,
                        "reason": "edge_not_in_graph"
                    })
                    path_request["result"] = {
                        "path_found": False,
                        "reason": f"segment_{path[i]}_{path[i+1]}_not_in_graph",
                        "segments_validation": segment_validation
                    }
                    self.edge_history.append(path_request)
                    return None, float('inf')  # This should never happen but added for safety
                
                segment_validation.append({
                    "segment": (path[i], path[i+1]),
                    "valid": True,
                    "weight": self.graph[path[i]][path[i+1]]['weight']
                })
                distance += self.graph[path[i]][path[i+1]]['weight']
            
            path_request["result"] = {
                "path_found": True,
                "path": path,
                "distance": distance,
                "segments_validation": segment_validation
            }
            self.edge_history.append(path_request)
            return path, distance
            
        except nx.NetworkXNoPath:
            path_request["result"] = {
                "path_found": False,
                "reason": "networkx_no_path"
            }
            self.edge_history.append(path_request)
            return None, float('inf')
    
    def find_path_distance(self, path):
        """Calculate the total distance of a given path"""
        # Enhanced diagnostics
        path_distance_request = {
            "action": "find_path_distance",
            "path": path.copy() if path else None
        }
        
        if len(path) <= 1:
            path_distance_request["result"] = {
                "valid": True,
                "distance": 0,
                "full_path": path,
                "reason": "path_too_short"
            }
            self.edge_history.append(path_distance_request)
            return path, 0
            
        total_distance = 0
        full_path = [path[0]]
        segment_results = []
        
        for i in range(len(path) - 1):
            segment_path, segment_distance = self.find_shortest_path(path[i], path[i+1])
            
            segment_results.append({
                "from": path[i],
                "to": path[i+1],
                "segment_path": segment_path,
                "segment_distance": segment_distance
            })
            
            if segment_path is None:
                path_distance_request["result"] = {
                    "valid": False,
                    "distance": float('inf'),
                    "segment_results": segment_results,
                    "reason": f"no_path_between_{path[i]}_{path[i+1]}"
                }
                self.edge_history.append(path_distance_request)
                return None, float('inf')
                
            # Add intermediate points from detours
            if len(segment_path) > 2:
                full_path.extend(segment_path[1:])
            else:
                full_path.append(path[i+1])
                
            total_distance += segment_distance
        
        path_distance_request["result"] = {
            "valid": True,
            "distance": total_distance,
            "full_path": full_path,
            "segment_results": segment_results
        }
        self.edge_history.append(path_distance_request)
        return full_path, total_distance
    
    def get_available_moves(self, current_location):
        """Get all locations that can be reached from current location"""
        return list(self.graph.neighbors(current_location))
    
    # New methods for diagnostics
    def get_graph_state(self):
        """Get a complete representation of the current graph state"""
        return {
            "nodes": list(self.graph.nodes()),
            "edges": [{
                "from": u, 
                "to": v, 
                "weight": d.get('weight', 0)
            } for u, v, d in self.graph.edges(data=True)],
            "closed_roads": self.closed_roads,
            "connectivity": {
                node: list(self.graph.neighbors(node)) 
                for node in self.graph.nodes()
            }
        }
    
    def get_edge_history(self):
        """Get the history of edge operations"""
        return self.edge_history