from flask import Flask, request, jsonify
import openai
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("HARVEY_ASSISTANT_ID")

app = Flask(__name__)
memory_cache = {}

@app.route("/", methods=["GET", "HEAD"])
def health_check():
    return jsonify({"status": "OK"}), 200

@app.route("/salesiq-webhook", methods=["POST"])
def handle_zobot():
    try:
        payload = request.get_json(force=True)
        print("📥 Incoming Payload:", payload)

        handler = payload.get("handler")
        operation = payload.get("operation")
        trigger_name = payload.get("trigger_name")
        message = payload.get("message", {})
        visitor_message = message.get("text", "").strip()
        visitor_id = payload.get("visitor", {}).get("id", "anonymous")

        # 1. Initial trigger when chat opens
        if handler == "trigger":
            return jsonify({
                "action": "reply",
                "replies": [{
                    "text": "Hi! I'm Harvey. How can I help you?"
                }]
            }), 200

        # 2. First user message → reply fast and set up nexttrigger
        if operation in ["chat", "message"] and not trigger_name:
            if not visitor_message:
                return jsonify({
                    "action": "reply",
                    "replies": [{
                        "text": "I'm sorry, I didn't catch that. Could you rephrase?"
                    }]
                }), 200

            memory_cache[visitor_id] = visitor_message  # Save the input
            return jsonify({
                "action": "reply",
                "replies": [{
                    "text": "Got it! Give me a few seconds to think..."
                }],
                "nexttrigger": "continue_ai"
            }), 200

        # 3. Second phase: handle nexttrigger to reply with AI
        if trigger_name == "continue_ai":
            stored_question = memory_cache.get(visitor_id)
            if not stored_question:
                return jsonify({
                    "action": "reply",
                    "replies": [{
                        "text": "Hmm, I couldn’t find your earlier message. Could you try again?"
                    }]
                }), 200

            # Step 1: Create thread
            thread = openai.beta.threads.create()

            # Step 2: Add user message
            openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=stored_question
            )

            # Step 3: Run the assistant
            run = openai.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=ASSISTANT_ID
            )

            # Step 4: Wait until assistant finishes
            while True:
                run = openai.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
                if run.status == "completed":
                    break
                time.sleep(1)

            # Step 5: Extract assistant reply
            assistant_reply = "Hmm, I’m not sure how to respond right now."
            messages = openai.beta.threads.messages.list(thread_id=thread.id)
            for msg in messages.data:
                if msg.role == "assistant":
                    assistant_reply = msg.content[0].text.value.strip()
                    break

            # Optional: clean up
            memory_cache.pop(visitor_id, None)

            return jsonify({
                "action": "reply",
                "replies": [{
                    "text": assistant_reply
                }]
            }), 200

        # 4. Fallback for unrecognized cases
        return jsonify({
            "action": "reply",
            "replies": [{
                "text": "Sorry, I didn’t understand that."
            }]
        }), 200

    except Exception as e:
        print("❌ Error occurred:", e)
        return jsonify({
            "action": "reply",
            "replies": [{
                "text": "Something went wrong. Please try again later."
            }]
        }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
