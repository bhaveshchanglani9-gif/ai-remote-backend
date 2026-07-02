import os
from flask import Flask, request, jsonify
from google import genai
from google.genai import types
from flask_cors import CORS
CORS(app)
app = Flask(__name__)

# Initialize Google GenAI Client using environment variable
gemini_client = genai.Client()

# Global variables acting as our cloud memory switchboard
device_channels = {
    "laptop": {"action": "NONE", "payload": ""},
    "mobile": {"action": "NONE", "payload": ""}
}
medication_logs = []

# System instructions to feed Gemini context, location, Hindi support, and structured output
SYSTEM_INSTRUCTION = """
You are the AI brain for 'SAHAYAK', a single-button universal assistive remote for an elderly user.
The user is located in Bhopal, Madhya Pradesh, India.
You accept voice inputs in English, pure Hindi, or mixed 'Hinglish' (e.g., 'laptop par youtube kholo').

Analyze the user's intent. You MUST respond ONLY in a rigid JSON format containing three fields:
1. "target": Where to send the action ("laptop", "mobile", or "none")
2. "action": The programmatic command ("OPEN_URL", "ZOOM_IN", "SPOKEN_RESPONSE")
3. "payload": The specific text, link, or spoken answer.

Examples:
- "Youtube kholo" -> {"target": "laptop", "action": "OPEN_URL", "payload": "https://youtube.com"}
- "Text bada karo" -> {"target": "laptop", "action": "ZOOM_IN", "payload": ""}
- "Bhopal ka Mausam kaisa hai?" -> {"target": "none", "action": "SPOKEN_RESPONSE", "payload": "Bhopal mein aaj mausam saaf hai."}
"""

@app.route("/process_voice", methods=["POST"])
def process_voice():
    data = request.json or {}
    user_speech = data.get("text", "")
    
    if not user_speech:
        return jsonify({"status": "error", "message": "No input speech provided"}), 400

    try:
        # Pass speech to Gemini along with our strict structure constraints
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_speech,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json"
            )
        )
        
        # Parse the JSON layout returned by Gemini
        ai_decision = response.json()
        target = ai_decision.get("target")
        action = ai_decision.get("action")
        payload = ai_decision.get("payload")

        # FEATURE A: ROUTING ACCESSIBILITY & URL ACTIONS TO THE LAPTOP
        if target in device_channels:
            device_channels[target] = {"action": action, "payload": payload}
            return jsonify({"action": "CONFIRMATION", "payload": f"Command sent to {target}"})

        # FEATURE B: RETURNING SPOKEN TEXT BACK TO THE HANDHELD SPEAKER
        if action == "SPOKEN_RESPONSE":
            return jsonify({"action": "SPOKEN_RESPONSE", "payload": payload})

        return jsonify(ai_decision)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint for Laptop/Mobile background agents to poll for pending commands
@app.route("/get_commands/<device_id>", methods=["GET"])
def get_commands(device_id):
    if device_id in device_channels:
        # Fetch the pending action, then clear it so it doesn't loop infinitely
        current_command = device_channels[device_id]
        device_channels[device_id] = {"action": "NONE", "payload": ""}
        return jsonify(current_command)
    return jsonify({"action": "NONE", "payload": ""}), 404

# FEATURE C: MEDICATION TRACKING ROUTE
@app.route("/log_medicine", methods=["POST"])
def log_medicine():
    data = request.json or {}
    status = data.get("status", "taken")
    medication_logs.append(status)
    return jsonify({"status": "success", "total_logs": len(medication_logs)})
    @app.route("/get_medicine_logs", methods=["GET"])
def get_medicine_logs():
    return jsonify({"logs": medication_logs})
