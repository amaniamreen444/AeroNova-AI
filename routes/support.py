
from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from database import get_db_connection

support_bp = Blueprint("support", __name__)


def passenger_required():
    if "user_id" not in session:
        return False

    if session.get("user_role") != "passenger":
        return False

    return True


@support_bp.route("/support", methods=["GET", "POST"])
def support_page():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    if session.get("user_role") != "passenger":
        return redirect(url_for("main.home"))

    user_id = session["user_id"]
    connection = None
    cursor = None

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()

        if not subject or not message:
            flash("Please enter both a subject and a message.", "error")
        else:
            try:
                connection = get_db_connection()
                cursor = connection.cursor()

                cursor.execute(
                    """
                    INSERT INTO support_requests
                    (user_id, subject, message)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, subject, message)
                )

                connection.commit()
                flash("Your support request was sent successfully!", "success")

                return redirect(url_for("support.support_page"))

            except Exception as e:
                if connection:
                    connection.rollback()

                print("Support request error:", e)
                flash("Unable to send your request. Please try again.", "error")

            finally:
                if cursor:
                    cursor.close()
                if connection and connection.is_connected():
                    connection.close()

    requests_list = []

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, subject, message, staff_reply,
                   status, created_at, updated_at
            FROM support_requests
            WHERE user_id = %s
            ORDER BY created_at DESC
            """,
            (user_id,)
        )

        requests_list = cursor.fetchall()

    except Exception as e:
        print("Load support requests error:", e)
        flash("Unable to load your support requests.", "error")

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

    return render_template(
        "passenger_support.html",
        requests_list=requests_list
    )
