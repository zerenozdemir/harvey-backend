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

        # 1) New chat opened → send greeting
        if handler == "conversation.created":
            return jsonify({
                "action": "reply",
                "replies": [{ "text": "Hi! I’m DD. How can I help you today?" }]
            }), 200

        # 2) Visitor sent a message → process with OpenAI
        if handler == "message":
            visitor_message = payload.get("message", {}).get("text", "").strip()
            if not visitor_message:
                return jsonify({
                    "action": "reply",
                    "replies": [{ "text": "I didn’t catch that—could you rephrase?" }]
                }), 200

            # OpenAI thread logic
            thread = openai.beta.threads.create()
            openai.beta.threads.messages.create(thread_id=thread.id, role="user", content=visitor_message)
            run = openai.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)

            time.sleep(5)
            for _ in range(10):
                run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
                if run.status == "completed":
                    break
                time.sleep(1)
            else:
                return jsonify({
                    "action": "reply",
                    "replies": [{ "text": "Sorry, I’m having trouble right now. Please try again in a moment." }]
                }), 200

            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            assistant_reply = next(
                (m.content[0].text.value.strip() for m in messages.data if m.role == "assistant"),
                "I’m not sure how to answer that. Try rephrasing?"
            )

            return jsonify({
                "action": "reply",
                "replies": [{ "text": assistant_reply }]
            }), 200

        # 3) All other handlers → do nothing
        return jsonify({}), 200

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({
            "action": "reply",
            "replies": [{ "text": "Something went wrong. Please try again later." }]
        }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
