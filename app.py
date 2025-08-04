from flask import Flask, request, jsonify
import openai
import time
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("HARVEY_ASSISTANT_ID")

print("OPENAI Key loaded:", openai.api_key)
print("Assistant ID loaded:", ASSISTANT_ID)

app = Flask(__name__)


@app.route("/", methods=["GET", "HEAD"])
def health_check():
    return "OK", 200


@app.route("/salesiq-webhook", methods=["POST"])
def handle_salesiq():
    try:
        data = request.get_json(force=True)
        print("Incoming request JSON:", data)

        # Extract user message from SalesIQ payload
        user_input = data.get("message") or data.get("msg") or ""
        user_input = user_input.strip()

        if not user_input:
            return jsonify({
                "replies": [
                    {"type": "text", "text": "I'm sorry, I didn't catch that. Could you rephrase?"}
                ],
                "status": "success"
            }), 200

        # Step 1: Create a new thread
        thread = openai.beta.threads.create()

        # Step 2: Add message to thread
        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        # Step 3: Run the Assistant
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Step 4: Wait for completion
        while run.status != "completed":
            time.sleep(1)
            run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        # Step 5: Fetch reply
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        assistant_reply = messages.data[0].content[0].text.value.strip()

        return jsonify({
            "replies": [
                {"type": "text", "text": assistant_reply}
            ],
            "status": "success"
        }), 200

    except Exception as e:
        print("Error:", e)
        return jsonify({
            "replies": [
                {"type": "text", "text": "Sorry, something went wrong. Please try again."}
            ],
            "status": "failure"
        }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
