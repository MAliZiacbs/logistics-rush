class ConstraintsManager:
    def __init__(self, active_constraints=None):
        """Initialize with optional list of active constraints"""
        # Default constraints (full set)
        self.default_constraints = {
            "Warehouse": {"before": ["Shop"]},
            "Distribution Center": {"before": ["Home"]},
            "Shop": {"after": ["Warehouse"]},
            "Home": {"after": ["Distribution Center"]}
        }
        
        # Only use constraints specified in active_constraints
        self.active_constraints = {}
        
        if active_constraints:
            for first, second in active_constraints:
                if first in self.default_constraints:
                    before_list = self.default_constraints[first].get("before", [])
                    if second in before_list:
                        if first not in self.active_constraints:
                            self.active_constraints[first] = {"before": []}
                        if "before" not in self.active_constraints[first]:
                            self.active_constraints[first]["before"] = []
                        self.active_constraints[first]["before"].append(second)
                        
                        if second not in self.active_constraints:
                            self.active_constraints[second] = {"after": []}
                        if "after" not in self.active_constraints[second]:
                            self.active_constraints[second]["after"] = []
                        self.active_constraints[second]["after"].append(first)
        
        # Keep track of violations
        self.violations = []
    
    def validate_route(self, route):
        """Check if a route satisfies all constraints
        
        Returns tuple of (is_valid, message, violated_constraint)
        If is_valid is True, no constraint was violated.
        If is_valid is False, a constraint was violated.
        """
        # If no active constraints, always valid
        if not self.active_constraints:
            return True, "Route satisfies all constraints", None
            
        for location, rules in self.active_constraints.items():
            if "before" in rules and location in route:
                for target in rules["before"]:
                    if target in route and route.index(location) > route.index(target):
                        return False, f"{location} must be visited before {target}", (location, target)
                        
            if "after" in rules and location in route:
                for target in rules["after"]:
                    if target in route and route.index(location) < route.index(target):
                        return False, f"{location} must be visited after {target}", (target, location)
        
        return True, "Route satisfies all constraints", None
    
    def validate_move(self, current_route, new_location):
        """Check if adding a new location maintains constraint satisfaction"""
        temp_route = current_route + [new_location]
        return self.validate_route(temp_route)

    def record_violation(self, route, attempted_location, violated_constraint):
        """Record a constraint violation"""
        self.violations.append({
            "route": route.copy(),
            "attempted_location": attempted_location,
            "violated_constraint": violated_constraint
        })
        
    def get_violations(self):
        """Get all recorded violations"""
        return self.violations
        
    def get_active_constraints(self):
        """Get the list of active constraints in (first, second) format"""
        result = []
        for location, rules in self.active_constraints.items():
            if "before" in rules:
                for target in rules["before"]:
                    result.append((location, target))
        return result