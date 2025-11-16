import math

def get_distance_in_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the distance between two GPS coordinates in kilometers using the Haversine formula.
    """
    R = 6371  # Radius of the Earth in kilometers

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    a = (math.sin(d_lat / 2) * math.sin(d_lat / 2) +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(d_lon / 2) * math.sin(d_lon / 2))
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance
