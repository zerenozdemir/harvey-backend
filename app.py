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
        data = request.get_json(force=True)
        print("📥 FULL PAYLOAD:\n", data)

        handler = data.get("handler")

        # === TRIGGER HANDLER ===
        if handler == "trigger":
            return jsonify({
                "action": {
                    "say": "Hi! I'm Harvey. How can I help you today?",
                    "next_field": "message"
                }
            }), 200

        # === MESSAGE HANDLER ===
        elif handler == "message":
            user_input = data.get("message", {}).get("text", "").strip()
            visitor_id = data.get("visitor", {}).get("email", "anonymous")

            if not user_input:
                print("❌ No input from user.")
                return jsonify({
                    "action": {
                        "say": "I'm sorry, I didn't catch that. Could you rephrase?"
                    }
                }), 200

            print(f"💬 Visitor [{visitor_id}]: {user_input}")

            # Step 1: Create thread
            thread = openai.beta.threads.create()

            # Step 2: Add message
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

            # Step 4: Wait for run
            while run.status != "completed":
                time.sleep(1)
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

            # Step 5: Get assistant's reply
            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            assistant_reply = messages.data[0].content[0].text.value.strip()

            print(f"🤖 Harvey says: {assistant_reply}")

            return jsonify({
                "action": {
                    "say": assistant_reply
                }
            }), 200

        # === Unknown Handler ===
        else:
            print("⚠️ Unhandled handler type:", handler)
            return jsonify({
                "action": {
                    "say": "I'm not sure how to handle this type of message."
                }
            }), 200

    except Exception as e:
        print("❌ Exception:", e)
        return jsonify({
            "action": {
                "say": "Sorry, something went wrong on my end. Try again?"
            }
        }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
