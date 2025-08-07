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
        payload = request.get_json(force=True)
        handler = payload.get("handler")
        print("📥 Payload:", payload)
        print("🔖 handler =", handler)

        # 1) New conversation started → send initial greeting
        if handler == "conversation.created":
            return jsonify({
                "action": "reply",
                "replies": [{
                    "text": "Hi! I’m DD. How can I help you today?"
                }]
            }), 200

        # 2) Visitor sent a message → process with OpenAI
        if handler == "message":
            visitor_message = payload.get("message", {}).get("text", "").strip()
            if not visitor_message:
                return jsonify({
                    "action": "reply",
                    "replies": [{
                        "text": "I’m sorry, I didn’t catch that. Could you rephrase?"
                    }]
                }), 200

            # Step 1: Create a new thread
            thread = openai.beta.threads.create()

            # Step 2: Add the user’s message
            openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=visitor_message
            )

            # Step 3: Request the assistant to run
            run = openai.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )

            # ⏱ Optional: wait a few seconds before polling
            time.sleep(5)

            # Step 4: Poll until completion (up to ~10s)
            for _ in range(10):
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                if run.status == "completed":
                    break
                time.sleep(1)
            else:
                return jsonify({
                    "action": "reply",
                    "replies": [{
                        "text": "Sorry, I’m having trouble right now. Please try again in a moment."
                    }]
                }), 200

            # Step 5: Pull out the assistant’s reply
            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            assistant_reply = None
            for msg in messages.data:
                if msg.role == "assistant":
                    # For Assistants v2: content is a list of choice objects
                    assistant_reply = msg.content[0].text.value.strip()
                    break

            if not assistant_reply:
                assistant_reply = "I’m not sure how to answer that. Try rephrasing?"

            return jsonify({
                "action": "reply",
                "replies": [{
                    "text": assistant_reply
                }]
            }), 200

        # 3) Anything else → fallback
        return jsonify({
            "action": "reply",
            "replies": [{
                "text": "Sorry, I didn’t understand that request."
            }]
        }), 200

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({
            "action": "reply",
            "replies": [{
                "text": "Something went wrong. Please try again later."
            }]
        }), 200

if __name__ == "__main__":
    # Run on port 10000 by default; override with environment variable PORT
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
