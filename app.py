from flask import Flask, request, jsonify
import openai
import os
import time
from dotenv import load_dotenv

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
        print("📥 FULL PAYLOAD:\n", payload)

        handler = payload.get("handler")
        visitor = payload.get("visitor", {})
        visitor_id = visitor.get("email", "anonymous")

        # Handle trigger
        if handler == "trigger":
            print("⚡ Trigger Handler Activated")
            return jsonify({
                "action": {
                    "say": "Hi! I'm Harvey. How can I help you today?"
                }
            }), 200

        # Handle message
        elif handler == "message":
            user_input = payload.get("message", {}).get("text", "").strip()

            if not user_input:
                print("⚠️ Missing or empty message text")
                return jsonify({
                    "action": {
                        "say": "I'm sorry, I didn't catch that. Could you rephrase?"
                    }
                }), 200

            print(f"💬 [{visitor_id}] said: {user_input}")

            # Step 1: Create thread
            thread = openai.beta.threads.create()

            # Step 2: Add user message
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

            # Step 4: Wait for run to complete
            while run.status != "completed":
                time.sleep(1)
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

            # Step 5: Get assistant reply
            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            reply = messages.data[0].content[0].text.value.strip()

            print(f"🤖 Harvey: {reply}")

            return jsonify({
                "action": {
                    "say": reply
                }
            }), 200

        # Unhandled event type
        else:
            print(f"⚠️ Unhandled handler: {handler}")
            return jsonify({
                "action": {
                    "say": "Sorry, I'm not sure how to respond to that event type."
                }
            }), 200

    except Exception as e:
        print("❌ Exception:", e)
        return jsonify({
            "action": {
                "say": "Sorry, something went wrong. Please try again."
            }
        }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
