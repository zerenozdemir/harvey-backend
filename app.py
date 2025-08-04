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
        data = request.get_json(force=True)
        print("\n📥 FULL PAYLOAD:")
        print(data)


        event_type = data.get("event")
        visitor_id = data.get("visitor_id", "anonymous")

        if not event_type:
            print("⚠️ No event type provided")
            return jsonify({
                "replies": [
                    {
                        "type": "text",
                        "text": "Hi! I'm Harvey. How can I help you today?"
                    }
                ]
            }), 200

        # Trigger handler
        if event_type == "trigger":
            print("⚡ Trigger event received")
            return jsonify({
                "replies": [
                    {
                        "type": "text",
                        "text": "Hi there! I'm Harvey, your assistant. How can I help you today?"
                    }
                ]
            }), 200

        # Message handler
        elif event_type == "message":
            user_input = data.get("message", "").strip()
            print(f"💬 Visitor [{visitor_id}]: {user_input}")

            if not user_input:
                return jsonify({
                    "replies": [
                        {
                            "type": "text",
                            "text": "I'm sorry, I didn't catch that. Could you rephrase?"
                        }
                    ]
                }), 200

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

            while run.status != "completed":
                time.sleep(1)
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            assistant_reply = messages.data[0].content[0].text.value.strip()

            print(f"🤖 Harvey says: {assistant_reply}")

            return jsonify({
                "replies": [
                    {
                        "type": "text",
                        "text": assistant_reply
                    }
                ]
            }), 200

        else:
            print(f"⚠️ Unrecognized event type: {event_type}")
            return jsonify({
                "replies": [
                    {
                        "type": "text",
                        "text": "I'm here to help, but didn't quite understand your request."
                    }
                ]
            }), 200

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({
            "replies": [
                {
                    "type": "text",
                    "text": "Sorry, something went wrong. Please try again."
                }
            ]
        }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
