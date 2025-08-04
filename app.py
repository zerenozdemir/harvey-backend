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
    return jsonify({"status": "Harvey backend is live."}), 200

@app.route("/salesiq-webhook", methods=["POST"])
def handle_salesiq():
    try:
        data = request.get_json(force=True)

        user_input = data.get("message", "").strip()
        visitor_id = data.get("visitor_id", "anonymous")

        if not user_input:
            print("❌ No message content received.")
            return jsonify({"reply": "Sorry, I didn’t catch that. Could you try again?"}), 400

        print(f"💬 Visitor [{visitor_id}]: {user_input}")

        # Create thread
        thread = openai.beta.threads.create()

        # Add user message
        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        # Run assistant
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Poll for completion
        while run.status != "completed":
            time.sleep(1)
            run = openai.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

        # Retrieve assistant response
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        assistant_reply = messages.data[0].content[0].text.value.strip()

        print(f"🤖 Harvey: {assistant_reply}")

        return jsonify({
            "action": {
                "say": assistant_reply
            }
        }), 200

    except Exception as e:
        print("❌ Exception:", e)
        return jsonify({
            "action": {
                "say": "Sorry, something went wrong. Please try again."
            }
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
