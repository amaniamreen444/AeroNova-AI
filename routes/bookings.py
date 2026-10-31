from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    flash
)

from database import get_db_connection


bookings_bp = Blueprint("bookings", __name__)


# ==========================================
# CHECK PASSENGER LOGIN
# ==========================================

def passenger_required():

    if "user_id" not in session:
        return False

    if session.get("user_role") != "passenger":
        return False

    return True
# ==========================================
# SAVE LIVE FLIGHT AND START BOOKING
# ==========================================

@bookings_bp.route("/book-live-flight")
def book_live_flight():

    if not passenger_required():

        flash(
            "Please login as a passenger to book a flight.",
            "warning"
        )

        return redirect(url_for("auth.login"))

    flight_number = request.args.get("flight_number")
    airline = request.args.get("airline")
    origin = request.args.get("origin")
    destination = request.args.get("destination")
    departure_time = request.args.get("departure_time")
    arrival_time = request.args.get("arrival_time")
    price = request.args.get("price")
    passengers = request.args.get("passengers", 1, type=int)

    if not all([
        flight_number,
        airline,
        origin,
        destination,
        departure_time,
        arrival_time,
        price
    ]):

        flash(
            "Live flight information is incomplete.",
            "danger"
        )

        return redirect(url_for("flights.search"))

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        # Check whether this flight is already stored
        cursor.execute(
            """
            SELECT id
            FROM flights
            WHERE flight_number = %s
            """,
            (flight_number,)
        )

        existing_flight = cursor.fetchone()

        if existing_flight:

            flight_id = existing_flight[0]

        else:

            cursor.execute(
                """
                INSERT INTO flights
                (
                    flight_number,
                    airline,
                    origin,
                    destination,
                    departure_time,
                    arrival_time,
                    price,
                    available_seats,
                    status
                )
                VALUES
                (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    flight_number,
                    airline,
                    origin,
                    destination,
                    departure_time,
                    arrival_time,
                    float(price),
                    100,
                    "Scheduled"
                )
            )

            flight_id = cursor.lastrowid

        connection.commit()

        return redirect(
            url_for(
                "bookings.start_booking",
                flight_id=flight_id,
                passengers=passengers
            )
        )

    except Exception as error:

        connection.rollback()

        print("LIVE FLIGHT SAVE ERROR:", error)

        flash(
            "Could not prepare the live flight for booking.",
            "danger"
        )

        return redirect(url_for("flights.search"))

    finally:

        cursor.close()
        connection.close()

# ==========================================
# START BOOKING
# ==========================================

@bookings_bp.route("/book/<int:flight_id>")
def start_booking(flight_id):

    if not passenger_required():

        flash(
            "Please login as a passenger to book a flight.",
            "warning"
        )

        return redirect(
            url_for("auth.login")
        )

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

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

        flash(
            "Flight not found.",
            "danger"
        )

        return redirect(
            url_for("flights.search")
        )

    passenger_count = request.args.get(
        "passengers",
        1,
        type=int
    )

    if passenger_count < 1:
        passenger_count = 1

    if passenger_count > flight["available_seats"]:

        flash(
            "Not enough seats are available.",
            "danger"
        )

        return redirect(
            url_for("flights.search")
        )

    # Store temporary booking information
    session["booking_flight_id"] = flight["id"]

    session["booking_passenger_count"] = passenger_count

    session["booking_flight_price"] = float(
        flight["price"]
    )

    # Clear old booking data
    session.pop("booking_passengers", None)
    session.pop("booking_seats", None)
    session.pop("booking_payment_method", None)

    return redirect(
        url_for("bookings.passenger_details")
    )


# ==========================================
# PASSENGER DETAILS
# ==========================================

@bookings_bp.route(
    "/passenger-details",
    methods=["GET", "POST"]
)
def passenger_details():

    if not passenger_required():

        return redirect(
            url_for("auth.login")
        )

    flight_id = session.get(
        "booking_flight_id"
    )

    if not flight_id:

        flash(
            "Please select a flight first.",
            "warning"
        )

        return redirect(
            url_for("flights.search")
        )

    passenger_count = int(
        session.get(
            "booking_passenger_count",
            1
        )
    )

    # --------------------------------------
    # SAVE PASSENGER DETAILS
    # --------------------------------------

    if request.method == "POST":

        passengers = []

        for i in range(passenger_count):

            full_name = request.form.get(
                f"full_name_{i}",
                ""
            ).strip()

            email = request.form.get(
                f"email_{i}",
                ""
            ).strip()

            phone = request.form.get(
                f"phone_{i}",
                ""
            ).strip()

            gender = request.form.get(
                f"gender_{i}",
                ""
            ).strip()

            date_of_birth = request.form.get(
                f"date_of_birth_{i}",
                ""
            ).strip()

            passport_number = request.form.get(
                f"passport_number_{i}",
                ""
            ).strip()

            if not full_name or not email or not phone:

                flash(
                    "Please fill in all required passenger details.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "bookings.passenger_details"
                    )
                )

            passengers.append(
                {
                    "full_name": full_name,
                    "email": email,
                    "phone": phone,
                    "gender": gender,
                    "date_of_birth": date_of_birth,
                    "passport_number": passport_number
                }
            )

        # Save passengers temporarily
        session["booking_passengers"] = passengers

        # IMPORTANT:
        # flight_id is required by seat_selection
        return redirect(
            url_for(
                "bookings.seat_selection",
                flight_id=flight_id
            )
        )

    # --------------------------------------
    # GET FLIGHT DETAILS
    # --------------------------------------

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

        flash(
            "Flight not found.",
            "danger"
        )

        return redirect(
            url_for("flights.search")
        )

    return render_template(
        "passenger_details.html",
        flight=flight,
        passenger_count=passenger_count
    )


# ==========================================
# SEAT SELECTION
# ==========================================

@bookings_bp.route(
    "/seat-selection/<int:flight_id>",
    methods=["GET", "POST"]
)
def seat_selection(flight_id):

    if not passenger_required():

        return redirect(
            url_for("auth.login")
        )

    # Make sure this is the currently selected flight
    session_flight_id = session.get(
        "booking_flight_id"
    )

    if not session_flight_id:

        flash(
            "Please start your booking again.",
            "warning"
        )

        return redirect(
            url_for("flights.search")
        )

    if int(session_flight_id) != int(flight_id):

        flash(
            "Invalid flight selection.",
            "danger"
        )

        return redirect(
            url_for("flights.search")
        )

    # Get passenger count
    passenger_count = int(
        session.get(
            "booking_passenger_count",
            1
        )
    )

    # --------------------------------------
    # GET FLIGHT
    # --------------------------------------

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

    # Get already booked seats
    cursor.execute(
        """
        SELECT seat_number
        FROM bookings
        WHERE flight_id = %s
        AND booking_status != 'Cancelled'
        """,
        (flight_id,)
    )

    booked_seats_data = cursor.fetchall()

    cursor.close()
    connection.close()

    if not flight:

        flash(
            "Flight not found.",
            "danger"
        )

        return redirect(
            url_for("flights.search")
        )

    booked_seats = [
        item["seat_number"]
        for item in booked_seats_data
        if item.get("seat_number")
    ]

    # --------------------------------------
    # SAVE SELECTED SEATS
    # --------------------------------------

    if request.method == "POST":

        selected_seats = request.form.get(
            "selected_seats",
            ""
        )

        seats = [
            seat.strip()
            for seat in selected_seats.split(",")
            if seat.strip()
        ]

        # Check correct number of seats
        if len(seats) != passenger_count:

            flash(
                f"Please select exactly "
                f"{passenger_count} seat(s).",
                "danger"
            )

            return redirect(
                url_for(
                    "bookings.seat_selection",
                    flight_id=flight_id
                )
            )

        # Prevent duplicate selection
        if len(set(seats)) != len(seats):

            flash(
                "You selected a duplicate seat.",
                "danger"
            )

            return redirect(
                url_for(
                    "bookings.seat_selection",
                    flight_id=flight_id
                )
            )

        # Check whether a seat is already booked
        for seat in seats:

            if seat in booked_seats:

                flash(
                    f"Seat {seat} is already occupied.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "bookings.seat_selection",
                        flight_id=flight_id
                    )
                )

        # Save selected seats
        session["booking_seats"] = seats

        flash(
            "Seats selected successfully!",
            "success"
        )

        # Go to payment
        return redirect(
            url_for("bookings.payment")
        )

    # --------------------------------------
    # SHOW SEAT SELECTION PAGE
    # --------------------------------------

    return render_template(
        "seat_selection.html",
        flight=flight,
        passenger_count=passenger_count,
        booked_seats=booked_seats
    )


# ==========================================
# BOOKING SUMMARY
# OPTIONAL REVIEW PAGE
# ==========================================

@bookings_bp.route("/booking-summary")
def booking_summary():

    if not passenger_required():

        return redirect(
            url_for("auth.login")
        )

    flight_id = session.get(
        "booking_flight_id"
    )

    passengers = session.get(
        "booking_passengers",
        []
    )

    seats = session.get(
        "booking_seats",
        []
    )

    if not flight_id or not passengers or not seats:

        flash(
            "Your booking session is incomplete.",
            "warning"
        )

        return redirect(
            url_for("flights.search")
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

    total_price = (
        float(flight["price"])
        * len(passengers)
    )

    return render_template(
        "booking_summary.html",
        flight=flight,
        passengers=passengers,
        seats=seats,
        total_price=total_price
    )


# ==========================================
# PAYMENT PAGE
# ==========================================

@bookings_bp.route(
    "/payment",
    methods=["GET", "POST"]
)
def payment():

    if not passenger_required():

        return redirect(
            url_for("auth.login")
        )

    flight_id = session.get(
        "booking_flight_id"
    )

    passengers = session.get(
        "booking_passengers",
        []
    )

    seats = session.get(
        "booking_seats",
        []
    )

    if not flight_id or not passengers or not seats:

        flash(
            "Please complete the booking details first.",
            "warning"
        )

        return redirect(
            url_for("flights.search")
        )

    # Get flight details
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

        flash(
            "Flight not found.",
            "danger"
        )

        return redirect(
            url_for("flights.search")
        )

    total_price = (
        float(flight["price"])
        * len(passengers)
    )

    # --------------------------------------
    # PROCESS PAYMENT
    # --------------------------------------

    if request.method == "POST":

        payment_method = request.form.get(
            "payment_method",
            ""
        )

        if not payment_method:

            flash(
                "Please select a payment method.",
                "danger"
            )

            return redirect(
                url_for("bookings.payment")
            )

        session[
            "booking_payment_method"
        ] = payment_method

        # Continue to booking confirmation process
        return redirect(
            url_for(
                "bookings.confirm_booking"
            )
        )

    return render_template(
        "payment.html",
        flight=flight,
        passengers=passengers,
        seats=seats,
        total_price=total_price
    )


# ==========================================
# CONFIRM BOOKING
# SIMULATED PAYMENT SUCCESS
# ==========================================

@bookings_bp.route("/confirm-booking")
def confirm_booking():

    if not passenger_required():

        return redirect(
            url_for("auth.login")
        )

    flight_id = session.get(
        "booking_flight_id"
    )

    passengers = session.get(
        "booking_passengers",
        []
    )

    seats = session.get(
        "booking_seats",
        []
    )

    payment_method = session.get(
        "booking_payment_method"
    )

    if (
        not flight_id
        or not passengers
        or not seats
        or not payment_method
    ):

        flash(
            "Your booking information is incomplete.",
            "warning"
        )

        return redirect(
            url_for("flights.search")
        )

    if len(passengers) != len(seats):

        flash(
            "Passenger and seat information does not match.",
            "danger"
        )

        return redirect(
            url_for("bookings.payment")
        )

    connection = get_db_connection()
    cursor = connection.cursor(
        dictionary=True
    )

    try:

        # ----------------------------------
        # GET LATEST FLIGHT DATA
        # ----------------------------------

        cursor.execute(
            """
            SELECT *
            FROM flights
            WHERE id = %s
            FOR UPDATE
            """,
            (flight_id,)
        )

        flight = cursor.fetchone()

        if not flight:

            raise Exception(
                "Flight not found."
            )

        if (
            flight["available_seats"]
            < len(passengers)
        ):

            raise Exception(
                "Not enough seats are available."
            )

        # ----------------------------------
        # CHECK SEATS AGAIN
        # ----------------------------------

        for seat in seats:

            cursor.execute(
                """
                SELECT id
                FROM bookings
                WHERE flight_id = %s
                AND seat_number = %s
                AND booking_status != 'Cancelled'
                """,
                (
                    flight_id,
                    seat
                )
            )

            existing_booking = cursor.fetchone()

            if existing_booking:

                raise Exception(
                    f"Seat {seat} was just booked by another passenger."
                )

        booking_ids = []

        price_per_passenger = float(
            flight["price"]
        )

        total_price = (
            price_per_passenger
            * len(passengers)
        )

        # ----------------------------------
        # CREATE BOOKINGS
        # ----------------------------------

        for index, passenger in enumerate(passengers):

            seat = seats[index]

            cursor.execute(
                """
                INSERT INTO bookings
                (
                    user_id,
                    flight_id,
                    seat_number,
                    total_price,
                    booking_status
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    session["user_id"],
                    flight_id,
                    seat,
                    price_per_passenger,
                    "Confirmed"
                )
            )

            booking_ids.append(
                cursor.lastrowid
            )

        # ----------------------------------
        # SAVE SIMULATED PAYMENT RECORDS
        # ----------------------------------

        for booking_id in booking_ids:

            cursor.execute(
                """
                INSERT INTO payments
                (
                    booking_id,
                    amount,
                    payment_method,
                    payment_status
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    booking_id,
                    price_per_passenger,
                    payment_method,
                    "Successful"
                )
            )


        # ----------------------------------
        # UPDATE AVAILABLE SEATS
        # ----------------------------------

        cursor.execute(
            """
            UPDATE flights
            SET available_seats =
                available_seats - %s
            WHERE id = %s
            """,
            (
                len(passengers),
                flight_id
            )
        )

        # ----------------------------------
        # SAVE CONFIRMATION DATA
        # ----------------------------------

        session["last_booking_ids"] = (
            booking_ids
        )

        session["last_total_price"] = (
            total_price
        )

        # ----------------------------------
        # COMMIT
        # ----------------------------------

        connection.commit()

        # Clear temporary data
        session.pop(
            "booking_flight_id",
            None
        )

        session.pop(
            "booking_passenger_count",
            None
        )

        session.pop(
            "booking_flight_price",
            None
        )

        session.pop(
            "booking_passengers",
            None
        )

        session.pop(
            "booking_seats",
            None
        )

        session.pop(
            "booking_payment_method",
            None
        )

        flash(
            "Payment successful! Your flight is confirmed.",
            "success"
        )

        return redirect(
            url_for(
                "bookings.booking_confirmation"
            )
        )

    except Exception as error:

        connection.rollback()

        print(
            "BOOKING ERROR:",
            error
        )

        flash(
            str(error),
            "danger"
        )

        return redirect(
            url_for(
                "bookings.payment"
            )
        )

    finally:

        cursor.close()
        connection.close()


# ==========================================
# BOOKING CONFIRMATION
# ==========================================

@bookings_bp.route("/booking-confirmation")
def booking_confirmation():

    if not passenger_required():

        return redirect(
            url_for("auth.login")
        )

    booking_ids = session.get(
        "last_booking_ids",
        []
    )

    if not booking_ids:

        flash(
            "No recent booking found.",
            "warning"
        )

        return redirect(
            url_for(
                "bookings.passenger_dashboard"
            )
        )

    connection = get_db_connection()
    cursor = connection.cursor(
        dictionary=True
    )

    placeholders = ",".join(
        ["%s"] * len(booking_ids)
    )

    cursor.execute(
        f"""
        SELECT
            bookings.id,
            bookings.seat_number,
            bookings.total_price,
            bookings.booking_status,

            flights.flight_number,
            flights.airline,
            flights.origin,
            flights.destination,
            flights.departure_time,
            flights.arrival_time

        FROM bookings

        JOIN flights
        ON bookings.flight_id = flights.id

        WHERE bookings.id IN ({placeholders})
        """,
        tuple(booking_ids)
    )

    bookings = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "booking_confirmation.html",
        bookings=bookings,
        total_price=session.get(
            "last_total_price"
        )
    )


# ==========================================
# PASSENGER DASHBOARD AND NOTIFICATIONS
# ==========================================

@bookings_bp.route("/dashboard")
def passenger_dashboard():

    if not passenger_required():
        return redirect(url_for("auth.login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Get the passenger's bookings
        cursor.execute(
            """
            SELECT
                bookings.id,
                flights.flight_number,
                flights.airline,
                flights.origin,
                flights.destination,
                flights.departure_time,
                flights.arrival_time,
                bookings.seat_number,
                bookings.total_price,
                bookings.booking_status
            FROM bookings
            JOIN flights
                ON bookings.flight_id = flights.id
            WHERE bookings.user_id = %s
            ORDER BY bookings.booked_at DESC
            """,
            (session["user_id"],)
        )

        bookings = cursor.fetchall()

        # Get cancellation approval/rejection notifications
        cursor.execute(
            """
            SELECT
                cr.id AS request_id,
                cr.booking_id,
                cr.request_status,
                cr.admin_note,
                cr.resolved_at,
                f.flight_number,
                f.origin,
                f.destination
            FROM cancellation_requests cr
            JOIN bookings b
                ON cr.booking_id = b.id
            JOIN flights f
                ON b.flight_id = f.id
            WHERE cr.user_id = %s
              AND cr.request_status IN ('Approved', 'Rejected')
            ORDER BY cr.resolved_at DESC, cr.id DESC
            """,
            (session["user_id"],)
        )

        cancellation_notifications = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "passenger_dashboard.html",
        bookings=bookings,
        cancellation_notifications=cancellation_notifications
    )



# ==========================================
# PASSENGER REQUESTS BOOKING CANCELLATION
# ==========================================

@bookings_bp.route(
    "/request-cancellation/<int:booking_id>",
    methods=["POST"]
)
def request_cancellation(booking_id):

    if not passenger_required():
        flash("Please login as a passenger.", "warning")
        return redirect(url_for("auth.login"))

    reason = request.form.get("reason", "").strip()

    if not reason:
        flash("Please provide a cancellation reason.", "warning")
        return redirect(url_for("bookings.passenger_dashboard"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Check that this booking belongs to the logged-in passenger
        cursor.execute(
            """
            SELECT id, user_id, booking_status
            FROM bookings
            WHERE id = %s AND user_id = %s
            """,
            (booking_id, session["user_id"])
        )

        booking = cursor.fetchone()

        if not booking:
            flash("Booking not found.", "danger")
            return redirect(url_for("bookings.passenger_dashboard"))

        if booking["booking_status"] != "Confirmed":
            flash(
                "Only confirmed bookings can be cancelled.",
                "warning"
            )
            return redirect(url_for("bookings.passenger_dashboard"))

        # Prevent multiple pending requests for the same booking
        cursor.execute(
            """
            SELECT id
            FROM cancellation_requests
            WHERE booking_id = %s
              AND user_id = %s
              AND request_status = 'Pending'
            """,
            (booking_id, session["user_id"])
        )

        if cursor.fetchone():
            flash(
                "A cancellation request is already pending for this booking.",
                "warning"
            )
            return redirect(url_for("bookings.passenger_dashboard"))

        # Save the cancellation request for admin review
        cursor.execute(
            """
            INSERT INTO cancellation_requests
                (booking_id, user_id, reason, request_status)
            VALUES (%s, %s, %s, 'Pending')
            """,
            (booking_id, session["user_id"], reason)
        )

        connection.commit()

        flash(
            "Cancellation request submitted. Please wait for admin approval.",
            "success"
        )

    except Exception as error:
        connection.rollback()
        print("CANCELLATION REQUEST ERROR:", error)

        flash(
            "Could not submit the cancellation request. Please try again.",
            "danger"
        )

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("bookings.passenger_dashboard"))
