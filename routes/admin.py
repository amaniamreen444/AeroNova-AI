
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


admin_bp = Blueprint("admin", __name__)


def admin_required():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("user_role") != "admin":
        return redirect(url_for("main.home"))

    return None


@admin_bp.route("/admin/dashboard")
def dashboard():
    access_check = admin_required()
    if access_check:
        return access_check

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT COUNT(*) AS total FROM users")
        total_users = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM flights")
        total_flights = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM bookings")
        total_bookings = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT COALESCE(SUM(total_price), 0) AS revenue
            FROM bookings
            WHERE booking_status = 'Confirmed'
        """)
        revenue = cursor.fetchone()["revenue"]

        cursor.execute("""
            SELECT
                bookings.id,
                bookings.seat_number,
                bookings.total_price,
                bookings.booking_status,
                bookings.booked_at,
                users.full_name,
                users.email,
                flights.flight_number,
                flights.airline,
                flights.origin,
                flights.destination
            FROM bookings
            LEFT JOIN users ON bookings.user_id = users.id
            LEFT JOIN flights ON bookings.flight_id = flights.id
            ORDER BY bookings.id DESC
            LIMIT 10
        """)
        recent_bookings = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM cancellation_requests
            WHERE request_status = 'Pending'
        """)
        pending_cancellations = cursor.fetchone()["total"]

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_flights=total_flights,
        total_bookings=total_bookings,
        revenue=revenue,
        recent_bookings=recent_bookings,
        pending_cancellations=pending_cancellations
    )


@admin_bp.route("/admin/cancellations")
def cancellations():
    access_check = admin_required()
    if access_check:
        return access_check

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                cr.id AS request_id,
                cr.booking_id,
                cr.user_id,
                cr.reason,
                cr.request_status,
                cr.admin_note,
                cr.requested_at,
                cr.resolved_at,
                u.full_name,
                u.email,
                b.booking_status,
                b.total_price,
                b.seat_number,
                f.flight_number,
                f.airline,
                f.origin,
                f.destination,
                f.departure_time
            FROM cancellation_requests cr
            JOIN users u ON cr.user_id = u.id
            JOIN bookings b ON cr.booking_id = b.id
            JOIN flights f ON b.flight_id = f.id
            ORDER BY
                CASE WHEN cr.request_status = 'Pending'
                     THEN 0 ELSE 1 END,
                cr.requested_at DESC
        """)
        cancellation_requests = cursor.fetchall()

    finally:
        cursor.close()
        connection.close()

    return render_template(
        "admin_cancellations.html",
        cancellation_requests=cancellation_requests
    )


@admin_bp.route("/admin/cancellations/<int:request_id>/resolve", methods=["POST"])
def resolve_cancellation(request_id):
    access_check = admin_required()
    if access_check:
        return access_check

    action = request.form.get("action", "").strip().lower()
    admin_note = request.form.get("admin_note", "").strip()

    if action not in ("approve", "reject"):
        flash("Invalid cancellation action.", "error")
        return redirect(url_for("admin.cancellations"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute("""
            SELECT id, booking_id, user_id, request_status
            FROM cancellation_requests
            WHERE id = %s
            FOR UPDATE
        """, (request_id,))
        cancellation = cursor.fetchone()

        if not cancellation:
            connection.rollback()
            flash("Cancellation request was not found.", "error")
            return redirect(url_for("admin.cancellations"))

        if cancellation["request_status"] != "Pending":
            connection.rollback()
            flash("This request has already been processed.", "error")
            return redirect(url_for("admin.cancellations"))

        cursor.execute("""
            SELECT id, user_id, booking_status
            FROM bookings
            WHERE id = %s
            FOR UPDATE
        """, (cancellation["booking_id"],))
        booking = cursor.fetchone()

        if not booking or booking["user_id"] != cancellation["user_id"]:
            connection.rollback()
            flash("The booking does not match this cancellation request.", "error")
            return redirect(url_for("admin.cancellations"))

        if action == "approve":
            if booking["booking_status"] != "Confirmed":
                connection.rollback()
                flash(
                    "Only confirmed bookings can be cancelled through this request.",
                    "error"
                )
                return redirect(url_for("admin.cancellations"))

            cursor.execute("""
                UPDATE bookings
                SET booking_status = 'Cancelled'
                WHERE id = %s
            """, (booking["id"],))

            new_status = "Approved"

        else:
            new_status = "Rejected"

        cursor.execute("""
            UPDATE cancellation_requests
            SET request_status = %s,
                admin_note = %s,
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (new_status, admin_note or None, request_id))

        connection.commit()
        flash(
            "Cancellation request " + new_status.lower() + " successfully.",
            "success"
        )

    except Exception:
        connection.rollback()
        app_error_message = (
            "Unable to process this request. Check the Flask terminal for details."
        )
        flash(app_error_message, "error")

    finally:
        cursor.close()
        connection.close()

    return redirect(url_for("admin.cancellations"))
