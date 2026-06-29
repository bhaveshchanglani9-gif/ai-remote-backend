import os
import json
from flask import Flask, request, jsonify
from google import genai
from google.genai import types

app = Flask(__name__)
client = genai.Client()

# Global database held in memory to store active commands for devices
DEVICE_CHANNELS = {
    "laptop": {"action": "NONE", "payload": ""},
    "tv": {"action": "NONE", "payload": ""},
    "phone": {"action": "NONE", "payload": ""}
}

@app.route("/process_voice", methods=["POST"])
def process_voice():
    data = request.get_json()
    user_voice_text = data.get("command", "")
    
    system_instruction = (
        "You are the central brain for an elderly care AI remote. "
        "Determine if the user is asking a question or controlling a device (tv, laptop, phone). "
        "For questions, answer them warmly and clearly. For controls, identify the target and app link. "
        "Respond ONLY with this JSON schema:\n"
        "{\n"
        '  "type": "control" | "question",\n'
        '  "target_device": "laptop" | "tv" | "phone" | "none",\n'
        '  "action": "OPEN_URL" | "SPEAK_ANSWER",\n'
        '  "payload": "the website link (e.g. https://youtube.com) OR the verbal answer text"\n'
        "}"
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[user_voice_text],
            config=types.GenerateContentConfig(system_instruction=system_instruction, response_mime_type="application/json")
        )
        
        result = json.loads(response.text)
        
        # If it's a device command, route it to that specific device's channel
        target = result.get("target_device")
        if target in DEVICE_CHANNELS:
            DEVICE_CHANNELS[target] = {"action": result["action"], "payload": result["payload"]}
            
        return jsonify(result)
    except Exception as e:
        return jsonify({"type": "question", "action": "SPEAK_ANSWER", "payload": "Please try again."}), 500

@app.route("/get_commands/<device_id>", methods=["GET"])
def get_commands(device_id):
    # Devices constantly check this endpoint to see if they have work to do
    command = DEVICE_CHANNELS.get(device_id, {"action": "NONE", "payload": ""})
    # Reset channel after reading so it doesn't loop infinitely
    DEVICE_CHANNELS[device_id] = {"action": "NONE", "payload": ""}
    return jsonify(command)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))