from flask import Flask, request, jsonify
import openai
import os
import time
from dotenv import load_dotenv

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
        data = request.get_json(force=True)
        print("📥 Full Payload:", data)

        handler_type = data.get("handler")
        user_input = data.get("message", {}).get("text", "").strip()

        # Handle Trigger (when user lands on the site)
        if handler_type == "trigger":
            return jsonify({
                "action": {
                    "say": "Hi! I'm DD. How can I help you today?"
                }
            }), 200

        # Handle Message (when user sends a message)
        if handler_type == "message":
            if not user_input:
                return jsonify({
                    "action": {
                        "say": "I'm sorry, I didn't catch that. Could you rephrase?"
                    }
                }), 200

            print(f"💬 Visitor says: {user_input}")

            # Assistant v2 call
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

            # Wait for run to complete
            while True:
                time.sleep(1)
                run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                if run.status == "completed":
                    break
                elif run.status == "failed":
                    return jsonify({
                        "action": {
                            "say": "Something went wrong. Please try again later."
                        }
                    }), 200

            # Get response message
            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            assistant_reply = messages.data[0].content[0].text.value.strip()

            print(f"🤖 DD says: {assistant_reply}")

            return jsonify({
                "action": {
                    "say": assistant_reply
                }
            }), 200

        # Unhandled handlers
        return jsonify({
            "action": {
                "say": "Sorry, I didn’t understand that request."
            }
        }), 200

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({
            "action": {
                "say": "Sorry, something went wrong on my end. Please try again."
            }
        }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
