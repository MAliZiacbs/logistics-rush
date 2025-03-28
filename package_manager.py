class Package:
    def __init__(self, id, pickup, delivery):
        self.id = id
        self.pickup = pickup
        self.delivery = delivery
        self.status = "waiting"  # waiting, picked_up, or delivered

class PackageManager:
    def __init__(self, packages=None):
        """Initialize with optional list of packages"""
        self.packages = []
        self.carrying = None
        
        if packages:
            for pkg in packages:
                self.add_package(pkg['id'], pkg['pickup'], pkg['delivery'])
    
    def add_package(self, id, pickup, delivery):
        """Add a new package to the system"""
        package = Package(id, pickup, delivery)
        self.packages.append(package)
        return package
    
    def pickup(self, package_id, current_location):
        """Pick up a package at the current location"""
        # Can't pickup if already carrying
        if self.carrying is not None:
            return False, "Already carrying a package"
        
        # Find the package
        package = next((p for p in self.packages if p.id == package_id), None)
        if not package:
            return False, f"Package #{package_id} not found"
            
        # Check if package is available for pickup
        if package.status != "waiting" or package.pickup != current_location:
            return False, f"Package #{package_id} not available for pickup here"
            
        # Pick up the package
        package.status = "picked_up"
        self.carrying = package
        return True, f"Picked up package #{package_id}"
    
    def deliver(self, current_location):
        """Deliver the currently carried package"""
        # Can't deliver if not carrying
        if self.carrying is None:
            return False, "Not carrying any package"
            
        # Check if at correct delivery location
        if self.carrying.delivery != current_location:
            return False, f"Wrong location. This package goes to {self.carrying.delivery}"
            
        # Deliver the package
        package_id = self.carrying.id
        self.carrying.status = "delivered"
        self.carrying = None
        return True, f"Successfully delivered package #{package_id}"
    
    def get_available_pickups(self, location):
        """Get packages available for pickup at a location"""
        return [p for p in self.packages if p.pickup == location and p.status == "waiting"]
    
    def get_delivered_packages(self):
        """Get all delivered packages"""
        return [p for p in self.packages if p.status == "delivered"]
    
    def all_packages_delivered(self):
        """Check if all packages have been delivered"""
        return all(p.status == "delivered" for p in self.packages)
    
    def get_package_info(self):
        """Get information about all packages"""
        info = []
        for p in self.packages:
            info.append({
                "id": p.id,
                "pickup": p.pickup,
                "delivery": p.delivery,
                "status": p.status
            })
        return info