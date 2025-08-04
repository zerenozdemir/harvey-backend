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
        print("📥 FULL PAYLOAD:")
        print(data)

        handler_type = data.get("handler")
        user_input = data.get("message", {}).get("text", "").strip()
        visitor = data.get("visitor", {})
        visitor_id = visitor.get("email", "anonymous")

        # Handle trigger event
        if handler_type == "trigger":
            return jsonify({
                "action": {
                    "type": "reply",
                    "replies": [
                        {
                            "type": "text",
                            "text": "Hi! I'm Harvey. How can I help you today?"
                        }
                    ]
                }
            }), 200

        # Handle message event
        if handler_type == "message":
            if not user_input:
                return jsonify({
                    "action": {
                        "type": "reply",
                        "replies": [
                            {
                                "type": "text",
                                "text": "I'm sorry, I didn't catch that. Could you rephrase?"
                            }
                        ]
                    }
                }), 200

            print(f"💬 Visitor [{visitor_id}]: {user_input}")

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

            # Step 5: Get assistant's reply
            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            assistant_reply = messages.data[0].content[0].text.value.strip()

            print(f"🤖 Harvey says: {assistant_reply}")

            return jsonify({
                "action": {
                    "type": "reply",
                    "replies": [
                        {
                            "type": "text",
                            "text": assistant_reply
                        }
                    ]
                }
            }), 200

        # Fallback for unknown handler
        print("⚠️ Unhandled event type")
        return jsonify({
            "action": {
                "type": "reply",
                "replies": [
                    {
                        "type": "text",
                        "text": "Unhandled event type. Please try again."
                    }
                ]
            }
        }), 200

    except Exception as e:
        print("❌ Exception occurred:", e)
        return jsonify({
            "action": {
                "type": "reply",
                "replies": [
                    {
                        "type": "text",
                        "text": "Sorry, something went wrong. Please try again."
                    }
                ]
            }
        }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
