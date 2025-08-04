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
        print("📥 Incoming:", payload)

        # Determine which handler is being triggered
        event_type = payload.get("event")

        if event_type == "trigger":
            # Send a welcome message when chat starts
            return jsonify({
                "replies": [
                    {"type": "text", "text": "Hi there! I'm Harvey. Ask me anything about DynaDome structures."}
                ]
            }), 200

        elif event_type == "message":
            user_input = payload.get("message", {}).get("text", "").strip()
            visitor_id = payload.get("visitor", {}).get("id", "anonymous")

            if not user_input:
                return jsonify({
                    "replies": [
                        {"type": "text", "text": "I'm sorry, I didn't catch that. Could you rephrase?"}
                    ]
                }), 200

            print(f"💬 {visitor_id}: {user_input}")

            # Thread and Assistant interaction
            thread = openai.beta.threads.create()

            openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_input
            )

            run = openai.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )

            # Wait for the assistant to finish
            while run.status != "completed":
                time.sleep(1)
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            assistant_reply = messages.data[0].content[0].text.value.strip()

            print(f"🤖 Harvey: {assistant_reply}")

            return jsonify({
                "replies": [
                    {"type": "text", "text": assistant_reply}
                ]
            }), 200

        else:
            print("⚠️ Unrecognized event type.")
            return jsonify({"replies": [{"type": "text", "text": "Unhandled event."}]}), 200

    except Exception as e:
        print("❌ Exception:", e)
        return jsonify({
            "replies": [
                {"type": "text", "text": "Sorry, something went wrong. Please try again."}
            ]
        }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
