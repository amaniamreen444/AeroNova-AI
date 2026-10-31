
import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from flask import Blueprint, jsonify, request, url_for
from google import genai

from routes.flights import (
    search_live_flights,
    format_live_flights,
    get_airport_code,
)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

chatbot_bp = Blueprint("chatbot", __name__)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None


def understand_request(message):
    prompt = f"""
You are the request parser for AeroNova AI flight booking.

Today's date is {date.today().isoformat()}.

Read the user message and return ONLY valid JSON with these fields:
{{
  "intent": "flight_search" or "general",
  "origin": "city or airport code, or empty string",
  "destination": "city or airport code, or empty string",
  "departure_date": "YYYY-MM-DD or empty string",
  "passengers": integer,
  "sort": "cheap" or "best",
  "reply": "short helpful message"
}}

Rules:
- For flight searches, identify the departure city, destination and date.
- Convert relative dates such as tomorrow into YYYY-MM-DD using today's date.
- Default passengers to 1.
- Use sort "cheap" when the user asks for cheap, cheapest, or lowest-price flights.
- If the user requests a flight search but gives no date, leave departure_date empty.
- If required information is missing, write a short question in reply.
- Never invent prices, schedules, or flight results.
- For general questions, set intent to general and write a helpful reply.

User message: {message}
"""

    response = client.interactions.create(
        model="gemini-3.5-flash-lite",
        input=prompt,
    )

    text = (response.output_text or "").strip()
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


@chatbot_bp.route("/api/chat", methods=["POST"])
def chat():
    if client is None:
        return jsonify({
            "reply": "The AI assistant is not configured."
        }), 500

    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"reply": "Please type a message."}), 400

    if len(message) > 2000:
        return jsonify({
            "reply": "Please keep your message under 2000 characters."
        }), 400

    try:
        parsed = understand_request(message)

        if parsed.get("intent") != "flight_search":
            return jsonify({
                "reply": parsed.get("reply") or "How can I help with your travel plans?",
                "flights": []
            })

        origin = parsed.get("origin", "").strip()
        destination = parsed.get("destination", "").strip()
        departure_date = parsed.get("departure_date", "").strip()
        passengers = max(1, min(int(parsed.get("passengers", 1)), 9))

        if not origin or not destination:
            return jsonify({
                "reply": "Please tell me your departure city and destination.",
                "flights": []
            })

        if not departure_date:
            return jsonify({
                "reply": (
                    f"I can find flights from {origin} to {destination}. "
                    "What date would you like to travel? "
                    "For example, 25 October 2026."
                ),
                "flights": []
            })

        try:
            date.fromisoformat(departure_date)
        except ValueError:
            return jsonify({
                "reply": "Please tell me your travel date, such as 25 October 2026.",
                "flights": []
            })

        origin_code = get_airport_code(origin)
        destination_code = get_airport_code(destination)

        if not origin_code or not destination_code:
            return jsonify({
                "reply": (
                    "I couldn't identify one of those airports. "
                    "Please try a supported city name or three-letter airport code."
                ),
                "flights": []
            })

        search_type = (
            "cheap" if parsed.get("sort") == "cheap" else "best"
        )

        api_result = search_live_flights(
            origin=origin_code,
            destination=destination_code,
            departure_date=departure_date,
            adults=passengers,
            search_type=search_type,
        )

        flights = format_live_flights(api_result)
        flights = sorted(flights, key=lambda flight: flight["price"])
        flights = flights[:10]

        for flight in flights:
            flight["select_url"] = url_for(
                "flights.live_flight_details",
                airline=flight["airline"],
                flight_number=flight["flight_number"],
                origin=flight["origin"],
                destination=flight["destination"],
                departure_time=flight["departure_time"],
                arrival_time=flight["arrival_time"],
                price=flight["price"],
                passengers=passengers,
            )

        if not flights:
            return jsonify({
                "reply": (
                    f"I couldn't find live flights from {origin_code} "
                    f"to {destination_code} on {departure_date}. "
                    "Try another date."
                ),
                "flights": []
            })

        return jsonify({
            "reply": (
                f"I found {len(flights)} flight options from "
                f"{origin_code} to {destination_code} on {departure_date}. "
                "Here are the lowest-priced results returned by the flight API."
            ),
            "flights": flights
        })

    except Exception as error:
        print("GEMINI CHAT ERROR:", repr(error))
        return jsonify({
            "reply": "Sorry, I couldn't complete that request. Please try again.",
            "flights": []
        }), 502
