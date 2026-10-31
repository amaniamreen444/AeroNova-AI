import os
import requests
from datetime import datetime
from dotenv import load_dotenv

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

from database import get_db_connection


load_dotenv()


RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

RAPIDAPI_HOST = os.getenv(
    "RAPIDAPI_HOST",
    "google-flights2.p.rapidapi.com"
)


flights_bp = Blueprint(
    "flights",
    __name__
)


# =====================================================
# RAPIDAPI FLIGHT SEARCH
# =====================================================

def search_live_flights(
    origin,
    destination,
    departure_date,
    travel_class="ECONOMY",
    adults=1,
    currency="INR",
    search_type="best"
):

    url = (
        f"https://{RAPIDAPI_HOST}"
        "/api/v1/searchFlights"
    )

    querystring = {
        "departure_id": origin.upper(),
        "arrival_id": destination.upper(),
        "outbound_date": departure_date,
        "travel_class": travel_class,
        "adults": adults,
        "show_hidden": "1",
        "currency": currency,
        "language_code": "en-US",
        "country_code": "IN",
       "search_type": search_type,
    }

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            params=querystring,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:

        print("RAPIDAPI ERROR:", error)

        return None


# =====================================================
# HELPER FUNCTIONS FOR API DATA
# =====================================================

def get_value(data, *keys, default=""):

    """
    Safely searches for the first available key.
    """

    if not isinstance(data, dict):
        return default

    for key in keys:

        value = data.get(key)

        if value not in [None, ""]:

            return value

    return default


def get_airport_data(airport):

    """
    Handles different airport formats returned by the API.
    """

    if not isinstance(airport, dict):
        return {
            "code": "",
            "name": "",
            "time": ""
        }

    code = get_value(
        airport,
        "airport_code",
        "code",
        "id",
        default=""
    )

    name = get_value(
        airport,
        "airport_name",
        "name",
        "airport",
        default=""
    )

    time = get_value(
        airport,
        "time",
        "datetime",
        "date_time",
        default=""
    )

    return {
        "code": code,
        "name": name,
        "time": time
    }


# =====================================================
# CONVERT API FLIGHTS TO WEBSITE FORMAT
# =====================================================

def format_live_flights(api_result):

    flights = []

    if not api_result:
        return flights

    data = api_result.get("data", {})

    if not isinstance(data, dict):
        return flights

    itineraries = data.get("itineraries", {})

    if not isinstance(itineraries, dict):
        return flights

    top_flights = itineraries.get("topFlights", [])
    other_flights = itineraries.get("otherFlights", [])

    all_flights = top_flights + other_flights

    print("TOTAL API ITINERARIES:", len(all_flights))

    for itinerary in all_flights:

        if not isinstance(itinerary, dict):
            continue

        # Many API results store actual flight segments
        # inside an inner "flights" list.
        segments = itinerary.get("flights", [])

        if not isinstance(segments, list):
            segments = []

        first_segment = segments[0] if segments else itinerary
        last_segment = segments[-1] if segments else itinerary

        if not isinstance(first_segment, dict):
            first_segment = {}

        if not isinstance(last_segment, dict):
            last_segment = {}

        departure_airport = get_airport_data(
            first_segment.get("departure_airport", {})
        )

        arrival_airport = get_airport_data(
            last_segment.get("arrival_airport", {})
        )

        # Some API responses use departure/arrival directly
        # in the itinerary instead of inside segments.
        if not departure_airport["code"]:

            departure_airport = get_airport_data(
                itinerary.get("departure_airport", {})
            )

        if not arrival_airport["code"]:

            arrival_airport = get_airport_data(
                itinerary.get("arrival_airport", {})
            )

        airline = get_value(
            first_segment,
            "airline",
            "airline_name",
            "carrier",
            default=""
        )

        if not airline:

            airline = get_value(
                itinerary,
                "airline",
                "airline_name",
                "carrier",
                default="Unknown Airline"
            )

        flight_number = get_value(
            first_segment,
            "flight_number",
            "flightNumber",
            "number",
            default=""
        )

        if not flight_number:

            flight_number = get_value(
                itinerary,
                "flight_number",
                "flightNumber",
                default="N/A"
            )

        price = get_value(
            itinerary,
            "price",
            "total_price",
            "amount",
            default=0
        )

        if isinstance(price, dict):

            price = get_value(
                price,
                "value",
                "amount",
                "price",
                default=0
            )

        try:

            price = float(price)

        except (ValueError, TypeError):

            price = 0

        formatted_flight = {
            "id": None,
            "airline": airline,
            "flight_number": flight_number,
            "origin": departure_airport["code"],
            "destination": arrival_airport["code"],
            "departure_time": departure_airport["time"],
            "arrival_time": arrival_airport["time"],
            "available_seats": "N/A",
            "price": price,
            "is_live": True
        }

        flights.append(formatted_flight)

    print("TOTAL FLIGHTS FOUND:", len(flights))

    return flights


# =====================================================
# SEARCH ROUTE
# =====================================================

@flights_bp.route("/flights")
@flights_bp.route("/search")
def search():

    origin = request.args.get(
        "origin",
        ""
    ).strip()

    destination = request.args.get(
        "destination",
        ""
    ).strip()

    departure_date = request.args.get(
        "departure_date",
        ""
    ).strip()

    passengers = request.args.get(
        "passengers",
        1,
        type=int
    )

    if not origin and not destination:

        return render_template(
            "search_results.html",
            flights=[],
            origin="",
            destination="",
            departure_date="",
            passengers=1
        )

    origin_code = get_airport_code(origin)

    destination_code = get_airport_code(destination)

    print("SEARCH STARTED")
    print("Origin:", origin)
    print("Destination:", destination)
    print("Departure Date:", departure_date)
    print("Passengers:", passengers)
    print("Origin code:", origin_code)
    print("Destination code:", destination_code)

    if not origin_code or not destination_code:

        flash(
            "Airport not found. Please enter a supported city or airport code.",
            "danger"
        )

        return render_template(
            "search_results.html",
            flights=[],
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            passengers=passengers
        )

    api_result = search_live_flights(
        origin=origin_code,
        destination=destination_code,
        departure_date=departure_date,
        adults=passengers
    )

    flights = format_live_flights(api_result)

    if not flights:

        flash(
            "No live flights found for this route and date.",
            "warning"
        )

    return render_template(
        "search_results.html",
        flights=flights,
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        passengers=passengers
    )


# =====================================================
# CITY TO AIRPORT CODE
# =====================================================

def get_airport_code(location):

    airport_codes = {

        "kochi": "COK",
        "cochin": "COK",

        "delhi": "DEL",
        "new delhi": "DEL",

        "mumbai": "BOM",

        "goa": "GOI",

        "bengaluru": "BLR",
        "bangalore": "BLR",

        "chennai": "MAA",

        "hyderabad": "HYD",

        "kolkata": "CCU",

        "doha": "DOH",
        "qatar": "DOH",

        "dubai": "DXB",

        "london": "LHR",

        "paris": "CDG"

    }

    location = location.lower().strip()

    if len(location) == 3:

        return location.upper()

    return airport_codes.get(location)


# =====================================================
# DATABASE FLIGHT DETAILS
# =====================================================

@flights_bp.route("/flight/<int:flight_id>")
def flight_details(flight_id):

    passengers = request.args.get(
        "passengers",
        1,
        type=int
    )

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT *
        FROM flights
        WHERE id = %s
        """,
        (flight_id,)
    )

    flight = cursor.fetchone()

    cursor.close()
    connection.close()

    if not flight:

        return redirect(
            url_for("flights.search")
        )

    return render_template(
        "flight_details.html",
        flight=flight,
        passengers=passengers
    )


# =====================================================
# LIVE FLIGHT DETAILS
# =====================================================

@flights_bp.route("/live-flight-details")
def live_flight_details():

    departure_time = request.args.get(
        "departure_time",
        ""
    )

    arrival_time = request.args.get(
        "arrival_time",
        ""
    )

    # Convert live API date strings into datetime objects
    try:
        departure_time = datetime.strptime(
            departure_time,
            "%Y-%m-%d %H:%M"
        )

    except (ValueError, TypeError):
        departure_time = None

    try:
        arrival_time = datetime.strptime(
            arrival_time,
            "%Y-%m-%d %H:%M"
        )

    except (ValueError, TypeError):
        arrival_time = None

    try:
        price = float(
            request.args.get("price", 0)
        )

    except (ValueError, TypeError):
        price = 0

    flight = {
        "id": None,

        "airline": request.args.get(
            "airline",
            "Unknown Airline"
        ),

        "flight_number": request.args.get(
            "flight_number",
            "N/A"
        ),

        "origin": request.args.get(
            "origin",
            ""
        ),

        "destination": request.args.get(
            "destination",
            ""
        ),

        "departure_time": departure_time,

        "arrival_time": arrival_time,

        "price": price,

        "available_seats": "N/A",

        "is_live": True
    }

    passengers = request.args.get(
        "passengers",
        1,
        type=int
    )

    return render_template(
        "flight_details.html",
        flight=flight,
        passengers=passengers
    )