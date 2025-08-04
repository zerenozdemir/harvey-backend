from flask import Flask, request, jsonify
import openai
import time
import os
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set API credentials
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("HARVEY_ASSISTANT_ID")

print("OPENAI Key loaded:", openai.api_key)
print("Assistant ID loaded:", ASSISTANT_ID)

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Harvey backend is running."})

@app.route("/salesiq-webhook", methods=["POST"])
def handle_salesiq():
    try:
        data = request.get_json()
        user_input = data.get("message", "")
        visitor_id = data.get("visitor_id", "anonymous")

        print(f"📩 Received message: {user_input} from visitor {visitor_id}")

        # Step 1: Create a thread
        thread = openai.beta.threads.create()

        # Step 2: Add user message to thread
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
            run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        # Step 5: Get assistant reply
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        assistant_reply = messages.data[0].content[0].text.value.strip()

        print(f"🤖 Harvey's reply: {assistant_reply}")

        return jsonify({"reply": assistant_reply})

    except Exception as e:
        print("❌ Error occurred while processing webhook:")
        print(e)
        traceback.print_exc()
        return jsonify({"reply": "Sorry, something went wrong. Please try again later."}), 500

if __name__ == "__main__":
    # Required for Render deployment
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
