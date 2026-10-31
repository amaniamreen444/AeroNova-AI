
from flask import (
    Blueprint, render_template, session,
    redirect, url_for, request, flash
)
from database import get_db_connection

staff_bp = Blueprint("staff", __name__)


@staff_bp.route("/staff/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("user_role") != "staff":
        return redirect(url_for("main.home"))

    return render_template("staff_dashboard.html")


@staff_bp.route("/staff/helpdesk")
def helpdesk():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("user_role") != "staff":
        return redirect(url_for("main.home"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                sr.id,
                sr.user_id,
                u.full_name,
                u.email,
                sr.subject,
                sr.message,
                sr.staff_reply,
                sr.status,
                sr.created_at,
                sr.updated_at
            FROM support_requests sr
            JOIN users u ON sr.user_id = u.id
            ORDER BY sr.created_at DESC
        """)
        support_requests = cursor.fetchall()

        return render_template(
            "staff_helpdesk.html",
            support_requests=support_requests
        )
    finally:
        cursor.close()
        conn.close()


@staff_bp.route("/staff/helpdesk/reply/<int:request_id>", methods=["POST"])
def reply_support_request(request_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("user_role") != "staff":
        return redirect(url_for("main.home"))

    staff_reply = request.form.get("staff_reply", "").strip()

    if not staff_reply:
        flash("Please enter a reply.", "error")
        return redirect(url_for("staff.helpdesk"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE support_requests
            SET staff_reply = %s,
                status = 'In Progress'
            WHERE id = %s
        """, (staff_reply, request_id))

        if cursor.rowcount == 0:
            conn.rollback()
            flash("Support request not found.", "error")
            return redirect(url_for("staff.helpdesk"))

        conn.commit()
        flash("Reply saved successfully.", "success")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("staff.helpdesk"))


@staff_bp.route(
    "/staff/helpdesk/status/<int:request_id>",
    methods=["POST"]
)
def update_support_status(request_id):
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("user_role") != "staff":
        return redirect(url_for("main.home"))

    status = request.form.get("status", "").strip()
    allowed_statuses = {"Open", "In Progress", "Resolved"}

    if status not in allowed_statuses:
        flash("Invalid support request status.", "error")
        return redirect(url_for("staff.helpdesk"))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE support_requests
            SET status = %s
            WHERE id = %s
        """, (status, request_id))

        if cursor.rowcount == 0:
            conn.rollback()
            flash("Support request not found.", "error")
            return redirect(url_for("staff.helpdesk"))

        conn.commit()
        flash("Request status updated successfully.", "success")
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("staff.helpdesk"))
