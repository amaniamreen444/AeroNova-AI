from flask import Flask
from config import Config

from routes.main import main_bp
from routes.auth import auth_bp
from routes.flights import flights_bp
from routes.bookings import bookings_bp
from routes.admin import admin_bp
from routes.staff import staff_bp
from routes.chatbot import chatbot_bp
from routes.support import support_bp


app = Flask(__name__)
app.config.from_object(Config)


app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(flights_bp)
app.register_blueprint(bookings_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(chatbot_bp) 
app.register_blueprint(support_bp)

if __name__ == "__main__":
    app.run(debug=True)