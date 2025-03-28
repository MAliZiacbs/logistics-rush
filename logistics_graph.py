import networkx as nx

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
        self.original_graph = nx.Graph(self.graph)
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
        return not self.graph.has_edge(loc1, loc2)
    
    def is_directly_connected(self, loc1, loc2):
        """Check if two locations are directly connected by a road"""
        return self.graph.has_edge(loc1, loc2)
    
    def get_connected_locations(self, location):
        """Get all locations that are directly connected to this location"""
        return list(self.graph.neighbors(location))
    
    def get_edge_weight(self, loc1, loc2):
        """Get the distance between two directly connected locations"""
        if self.graph.has_edge(loc1, loc2):
            return self.graph[loc1][loc2]['weight']
        return None
    
    def find_shortest_path(self, start, end):
        """Find the shortest path between two locations using only open roads"""
        # If there's no connection at all, return none
        if not nx.has_path(self.graph, start, end):
            return None, float('inf')
        
        try:
            # Get the shortest path using NetworkX
            path = nx.shortest_path(self.graph, start, end, weight='weight')
            
            # Calculate the total distance
            distance = 0
            for i in range(len(path) - 1):
                distance += self.graph[path[i]][path[i+1]]['weight']
                
            return path, distance
        except nx.NetworkXNoPath:
            return None, float('inf')
    
    def calculate_route_distance(self, route):
        """Calculate the total distance of a given route"""
        if len(route) <= 1:
            return 0
            
        total_distance = 0
        for i in range(len(route) - 1):
            if not self.graph.has_edge(route[i], route[i+1]):
                return float('inf')  # Invalid route - has a non-existent edge
            total_distance += self.graph[route[i]][route[i+1]]['weight']
            
        return total_distance
    
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