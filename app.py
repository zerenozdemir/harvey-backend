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
        print("📥 Incoming Payload:", payload)

        handler = payload.get("handler")
        visitor = payload.get("visitor", {})
        visitor_id = visitor.get("id", "anonymous")

        # Handle Trigger (initial greeting)
        if handler == "trigger":
            print("🟡 Trigger handler hit.")
            return jsonify({
                "action": {
                    "replies": [
                        {"type": "text", "text": "Hi! I'm Harvey. How can I help you today?"}
                    ]
                }
            }), 200

        # Handle Message (user input)
        if handler == "message":
            message_obj = payload.get("message", {})
            user_input = message_obj.get("text", "").strip()

            if not user_input:
                return jsonify({
                    "action": {
                        "replies": [
                            {"type": "text", "text": "I'm sorry, I didn't catch that. Could you rephrase?"}
                        ]
                    }
                }), 200

            print(f"💬 Visitor [{visitor_id}]: {user_input}")

            # OpenAI: Create thread and run assistant
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

            # Wait for completion
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
                "action": {
                    "replies": [
                        {"type": "text", "text": assistant_reply}
                    ]
                }
            }), 200

        # Catch all for unhandled handlers
        print(f"⚠️ Unhandled handler type: {handler}")
        return jsonify({
            "action": {
                "replies": [
                    {"type": "text", "text": "Unhandled event. Please try again."}
                ]
            }
        }), 200

    except Exception as e:
        print("❌ Exception:", e)
        return jsonify({
            "action": {
                "replies": [
                    {"type": "text", "text": "Sorry, something went wrong. Please try again."}
                ]
            }
        }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
