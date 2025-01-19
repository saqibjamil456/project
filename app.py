from flask import Flask, render_template, url_for, request
import sqlite3

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/aboutus')
def aboutus():
    return render_template('aboutus.html')


# Database path
db_path = r"busrouteup.db"

# Connect to the database
def connect_to_db(db_file):
    return sqlite3.connect(db_file)

# Find direct routes (Stops table)
def find_direct_routes(connection, start, destination):
    query = """
    SELECT DISTINCT BusRoutes.route_name, 
                    (end_stops.stop_order - start_stops.stop_order) AS total_stops
    FROM Stops AS start_stops
    JOIN Stops AS end_stops ON start_stops.route_id = end_stops.route_id
    JOIN BusRoutes ON start_stops.route_id = BusRoutes.route_id
    WHERE start_stops.stop_name = ? AND end_stops.stop_name = ?
    AND end_stops.stop_order > start_stops.stop_order
    ORDER BY total_stops ASC;
    """
    cursor = connection.cursor()
    cursor.execute(query, (start, destination))
    return cursor.fetchall()

# Find routes passing through areas (BusAreas table)
def find_routes_through_areas(connection, start_area, destination_area):
    query = """
    SELECT DISTINCT BusRoutes.route_name
    FROM BusAreas AS start_areas
    JOIN BusAreas AS end_areas ON start_areas.route_id = end_areas.route_id
    JOIN BusRoutes ON start_areas.route_id = BusRoutes.route_id
    WHERE start_areas.area_name = ? AND end_areas.area_name = ?
    AND end_areas.order_in_route > start_areas.order_in_route
    ORDER BY start_areas.order_in_route ASC;
    """
    cursor = connection.cursor()
    cursor.execute(query, (start_area, destination_area))
    return cursor.fetchall()

# Find routes with one transfer point (Connections table)
def find_routes_with_connections(connection, start, destination):
    query = """
    SELECT c.stop_name AS transfer_point, 
           r1.route_name AS first_route, 
           r2.route_name AS second_route
    FROM Connections c
    JOIN Stops AS s1 ON c.route_from = s1.route_id
    JOIN Stops AS s2 ON c.route_to = s2.route_id
    JOIN BusRoutes AS r1 ON c.route_from = r1.route_id
    JOIN BusRoutes AS r2 ON c.route_to = r2.route_id
    WHERE s1.stop_name = ? AND s2.stop_name = ?
    ORDER BY ABS(s2.stop_order - s1.stop_order);
    """
    cursor = connection.cursor()
    cursor.execute(query, (start, destination))
    
    # Eliminate duplicate connections
    connections = cursor.fetchall()
    unique_connections = list(set(connections))  # Remove duplicates using set
    return unique_connections

# Find routes with two transfer points
def find_routes_with_two_transfers(connection, start, destination):
    query = """
    SELECT c1.stop_name AS first_transfer_point, 
           c2.stop_name AS second_transfer_point,
           r1.route_name AS first_route, 
           r2.route_name AS second_route, 
           r3.route_name AS third_route
    FROM Connections c1
    JOIN Connections c2 ON c1.route_to = c2.route_from
    JOIN Stops AS s1 ON c1.route_from = s1.route_id
    JOIN Stops AS s2 ON c2.route_to = s2.route_id
    JOIN BusRoutes AS r1 ON c1.route_from = r1.route_id
    JOIN BusRoutes AS r2 ON c1.route_to = r2.route_id
    JOIN BusRoutes AS r3 ON c2.route_to = r3.route_id
    WHERE s1.stop_name = ? AND s2.stop_name = ?
    ORDER BY ABS(s2.stop_order - s1.stop_order);
    """
    cursor = connection.cursor()
    cursor.execute(query, (start, destination))
    
    # Eliminate duplicate two-transfer connections
    connections = cursor.fetchall()
    unique_connections = list(set(connections))  # Remove duplicates using set
    return unique_connections

@app.route("/search", methods=["GET", "POST"])
def search():
    connection = connect_to_db(db_path)
    
    # Fetch all stops from the database for the dropdown
    stops_query = "SELECT DISTINCT stop_name FROM Stops ORDER BY stop_name;"
    stops_cursor = connection.cursor()
    stops_cursor.execute(stops_query)
    stops = [row[0] for row in stops_cursor.fetchall()]
    
    routes = None
    message = None
    msg = None
    if request.method == "POST":
        start = request.form.get("start")
        destination = request.form.get("destination")
        print(f"Finding routes from '{start}' to '{destination}'...")
        message = f"Finding routes from '{start}' to '{destination}'..."
        
        # Fetch routes
        if start == destination:
            print("Your current location is the same as your destination")
            msg = "Your current location is the same as your destination"
        else:
            direct_routes = find_direct_routes(connection, start, destination)
            area_routes = find_routes_through_areas(connection, start, destination)
            connection_routes = find_routes_with_connections(connection, start, destination)
            two_transfer_routes = find_routes_with_two_transfers(connection, start, destination)
        
            # Deduplicate all route results
            routes = {
                "direct_routes": list(set(direct_routes)),
                "area_routes": list(set(area_routes)),
                "connection_routes": connection_routes,
                "two_transfer_routes": two_transfer_routes
            }
    
    connection.close()
    return render_template("search.html", stops=stops, routes=routes, message=message, msg=msg)

if __name__ == "__main__":
    app.run(debug=True)

