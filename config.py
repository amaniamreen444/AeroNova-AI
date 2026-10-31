import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-to-a-secret-key")

    MYSQL_HOST = "localhost"
    MYSQL_USER = "root"
    MYSQL_PASSWORD = ""
    MYSQL_DATABASE = "aeronova"
