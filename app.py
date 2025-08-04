from flask import Flask, request, jsonify
import openai
import os
import time
from dotenv import load_dotenv

# Load env variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("HARVEY_ASSISTANT_ID")

app = Flask(__name__)

@app.route("/", methods=["GET", "HEAD"])
def health_check():
    return jsonify({"status": "OK"}), 200

@app.route("/salesiq-webhook", methods=["POST"])
def handle_salesiq():
    try:
        payload = request.get_json(force=True)
        print("📥 Incoming Payload:", payload)

        # Handle initial Zobot trigger
        if payload.get("handler") == "trigger":
            return jsonify({
                "action": "reply",
                "replies": [{
                    "text": "Hi! I'm Harvey. How can I help you?"
                }],
                "suggestions": [
                    "What is a DynaDome?",
                    "Tell me about pricing",
                    "Can I use it year-round?",
                    "How does it open?"
                ]
            }), 200

        # Handle regular chat or message operation
        operation = payload.get("operation")  # Expected: "chat" or "message"
        message = payload.get("message", {})
        visitor_message = message.get("text", "").strip()
        response = {}

        if operation == "chat":
            # First visitor message
            response["action"] = "reply"
            response["replies"] = [{
                "text": "Hi again! What can I help you with today?"
            }]
            response["suggestions"] = [
                "What is a DynaDome?",
                "Tell me about pricing",
                "Can I use it year-round?",
                "How does it open?"
            ]

        elif operation == "message":
            if not visitor_message:
                response["action"] = "reply"
                response["replies"] = [{
                    "text": "I'm sorry, I didn't catch that. Could you rephrase?"
                }]
                return jsonify(response), 200

            # Use OpenAI Assistant to reply
            thread = openai.beta.threads.create()
            openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=visitor_message
            )
            run = openai.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )

            timeout = 10
            waited = 0
            while run.status != "completed" and waited < timeout:
                time.sleep(1)
                waited += 1
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

            assistant_reply = "I'm still thinking. Could you try again?"
            if run.status == "completed":
                messages = openai.beta.threads.messages.list(thread_id=thread.id)
                for msg in messages.data:
                    if msg.role == "assistant":
                        assistant_reply = msg.content[0].text.value.strip()
                        break

            response["action"] = "reply"
            response["replies"] = [{"text": assistant_reply}]

        else:
            # Unrecognized event
            response["action"] = "reply"
            response["replies"] = [{
                "text": "Sorry, I didn’t understand that operation type."
            }]

        print("🚀 Responding with:", response)
        return jsonify(response), 200

    except Exception as e:
        print("❌ Error occurred:", e)
        return jsonify({
            "action": "reply",
            "replies": [{
                "text": "Something went wrong. Please try again later."
            }]
        }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
