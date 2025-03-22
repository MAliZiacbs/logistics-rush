class ConstraintsManager:
    def __init__(self):
        """Initialize with the fixed game constraints"""
        self.constraints = {
            "Warehouse": {"before": ["Shop"]},
            "Distribution Center": {"before": ["Home"]},
            "Shop": {"after": ["Warehouse"]},
            "Home": {"after": ["Distribution Center"]}
        }
    
    def validate_route(self, route):
        """Check if a route satisfies all constraints"""
        for location, rules in self.constraints.items():
            if "before" in rules and location in route:
                for target in rules["before"]:
                    if target in route and route.index(location) > route.index(target):
                        return False, f"{location} must be visited before {target}"
                        
            if "after" in rules and location in route:
                for target in rules["after"]:
                    if target in route and route.index(location) < route.index(target):
                        return False, f"{location} must be visited after {target}"
        
        return True, "Route satisfies all constraints"
    
    def validate_move(self, current_route, new_location):
        """Check if adding a new location maintains constraint satisfaction"""
        temp_route = current_route + [new_location]
        return self.validate_route(temp_route)