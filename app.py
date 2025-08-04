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

        handler_type = payload.get("handler")

        if handler_type == "trigger":
            # Trigger handler - first interaction
            return jsonify({
                "action": {
                    "say": "Hi! I'm Harvey. How can I help you today?"
                }
            }), 200

        elif handler_type == "message":
            # Message handler - visitor sends a message
            message_data = payload.get("message", {})
            user_input = message_data.get("text", "").strip()

            if not user_input:
                return jsonify({
                    "action": {
                        "say": "I'm sorry, I didn't catch that. Could you rephrase?"
                    }
                }), 200

            print(f"💬 Visitor said: {user_input}")

            # Step 1: Create a new thread
            thread = openai.beta.threads.create()

            # Step 2: Add user message
            openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_input
            )

            # Step 3: Run the assistant
            run = openai.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )

            # Step 4: Wait for completion
            while run.status != "completed":
                time.sleep(1)
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

            # Step 5: Get the reply
            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            assistant_reply = messages.data[0].content[0].text.value.strip()

            print(f"🤖 Harvey says: {assistant_reply}")

            return jsonify({
                "action": {
                    "say": assistant_reply
                }
            }), 200

        else:
            print(f"⚠️ Unhandled handler type: {handler_type}")
            return jsonify({
                "action": {
                    "say": "Sorry, I didn’t understand that event type."
                }
            }), 200

    except Exception as e:
        print("❌ Error occurred:", e)
        return jsonify({
            "action": {
                "say": "Sorry, something went wrong. Please try again."
            }
        }), 200  # Always return 200 for Zoho

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
