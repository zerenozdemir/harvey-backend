from flask import Flask, request, jsonify
import openai
import os
from dotenv import load_dotenv
import time

# Load environment variables
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

        handler = payload.get("handler")
        operation = payload.get("operation")
        message = payload.get("message", {})
        visitor_message = message.get("text", "").strip()

        # Case 1: Visitor opens chat (trigger)
        if handler == "trigger":
            return jsonify({
                "action": "reply",
                "replies": [{
                    "text": "Hi! I'm Harvey. How can I help you?"
                }]
            }), 200

        # Case 2: First or ongoing visitor message
        if operation in ["chat", "message"]:
            if not visitor_message:
                return jsonify({
                    "action": "reply",
                    "replies": [{
                        "text": "I'm sorry, I didn't catch that. Could you rephrase?"
                    }]
                }), 200

            # Step 1: Create thread
            thread = openai.beta.threads.create()

            # Step 2: Add user message
            openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=visitor_message
            )

            # Step 3: Run assistant
            run = openai.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )

            # Step 4: Wait until run completes (no timeout fallback)
            while True:
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                if run.status == "completed":
                    break
                time.sleep(1)

            # Step 5: Get assistant's reply
            assistant_reply = "Hmm, no response yet."
            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            for msg in messages.data:
                if msg.role == "assistant":
                    assistant_reply = msg.content[0].text.value.strip()
                    break

            return jsonify({
                "action": "reply",
                "replies": [{
                    "text": assistant_reply
                }]
            }), 200

        # Case 3: Unknown handler or operation
        return jsonify({
            "action": "reply",
            "replies": [{
                "text": "Sorry, I didn’t understand that request."
            }]
        }), 200

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
