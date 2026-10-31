from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db_connection


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("auth.register"))

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()
        cursor = connection.cursor()

        try:

            cursor.execute(
                """
                INSERT INTO users
                (full_name, email, password, role)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    full_name,
                    email,
                    hashed_password,
                    "passenger"
                )
            )

            connection.commit()

            flash("Registration successful! Please login.", "success")

            return redirect(url_for("auth.login"))

        except Exception as error:

            flash("Email already exists.", "danger")
            print(error)

        finally:

            cursor.close()
            connection.close()

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["user_role"] = user["role"]

            if user["role"] == "admin":
                return redirect(url_for("admin.dashboard"))

            elif user["role"] == "staff":
                return redirect(url_for("staff.dashboard"))

            else:
                return redirect(
                    url_for("bookings.passenger_dashboard")
                )

        else:

            flash("Invalid email or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.", "success")

    return redirect(url_for("main.home"))
    