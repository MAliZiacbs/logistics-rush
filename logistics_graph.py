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
    
    def close_road(self, loc1, loc2):
        """Close a road between two locations"""
        if self.graph.has_edge(loc1, loc2):
            self.graph.remove_edge(loc1, loc2)
            self.closed_roads.append((loc1, loc2))
            return True
        return False
    
    def is_road_closed(self, loc1, loc2):
        """Check if a road is closed"""
        return not self.graph.has_edge(loc1, loc2)
    
    def find_shortest_path(self, start, end):
        """Find the shortest path between two locations, ensuring no closed roads are used"""
        # If there's no connection at all, return none
        if not nx.has_path(self.graph, start, end):
            return None, float('inf')
        
        try:
            # Get the shortest path using NetworkX
            path = nx.shortest_path(self.graph, start, end, weight='weight')
            
            # Calculate the total distance
            distance = 0
            for i in range(len(path) - 1):
                # Verify that each segment is not a closed road
                if not self.graph.has_edge(path[i], path[i+1]):
                    return None, float('inf')  # This should never happen but added for safety
                distance += self.graph[path[i]][path[i+1]]['weight']
                
            return path, distance
        except nx.NetworkXNoPath:
            return None, float('inf')
    
    def find_path_distance(self, path):
        """Calculate the total distance of a given path"""
        if len(path) <= 1:
            return path, 0
            
        total_distance = 0
        full_path = [path[0]]
        
        for i in range(len(path) - 1):
            segment_path, segment_distance = self.find_shortest_path(path[i], path[i+1])
            
            if segment_path is None:
                return None, float('inf')
                
            # Add intermediate points from detours
            if len(segment_path) > 2:
                full_path.extend(segment_path[1:])
            else:
                full_path.append(path[i+1])
                
            total_distance += segment_distance
            
        return full_path, total_distance
    
    def get_available_moves(self, current_location):
        """Get all locations that can be reached from current location"""
        return list(self.graph.neighbors(current_location))