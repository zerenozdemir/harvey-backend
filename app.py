from flask import Flask, request, jsonify
import openai
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("HARVEY_ASSISTANT_ID")

print("OPENAI Key loaded:", openai.api_key)
print("Assistant ID loaded:", ASSISTANT_ID)

app = Flask(__name__)

@app.route("/", methods=["GET", "HEAD"])
def health_check():
    return jsonify({"status": "OK"}), 200

@app.route("/salesiq-webhook", methods=["POST"])
def handle_salesiq():
    try:
        payload = request.get_json(force=True)
        print("📥 FULL PAYLOAD:")
        print(payload)

        handler_type = payload.get("handler", "")
        message_data = payload.get("message", {})
        user_input = message_data.get("text", "").strip()

        # Handle initial trigger event
        if handler_type == "trigger":
            print("🚀 Trigger event received")
            return jsonify({
                "action": {
                    "replies": ["Hi! I'm Harvey, your assistant. How can I help you today?"]
                }
            }), 200

        # Handle message event
        elif handler_type == "message":
            if not user_input:
                return jsonify({
                    "action": {
                        "replies": ["I didn’t catch that. Could you try rephrasing?"]
                    }
                }), 200

            print(f"💬 Visitor message: {user_input}")

            # Step 1: Create thread
            thread = openai.beta.threads.create()

            # Step 2: Add message to thread
            openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_input
            )

            # Step 3: Run assistant
            run = openai.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )

            # Step 4: Wait until completed
            while run.status != "completed":
                time.sleep(1)
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

            # Step 5: Get assistant reply
            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            assistant_reply = messages.data[0].content[0].text.value.strip()

            print(f"🤖 Harvey says: {assistant_reply}")

            return jsonify({
                "action": {
                    "replies": [assistant_reply]
                }
            }), 200

        else:
            print(f"⚠️ Unknown handler type: {handler_type}")
            return jsonify({
                "action": {
                    "replies": ["Unhandled event type."]
                }
            }), 200

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({
            "action": {
                "replies": ["Sorry, something went wrong. Please try again later."]
            }
        }), 200  # Return 200 to avoid Zoho retries

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
