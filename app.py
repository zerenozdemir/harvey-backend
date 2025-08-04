from flask import Flask, request, jsonify
import openai
import time
import os
from dotenv import load_dotenv
import traceback

# Load environment variables from .env
load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("HARVEY_ASSISTANT_ID")

print("OPENAI Key loaded:", openai.api_key)
print("Assistant ID loaded:", ASSISTANT_ID)

app = Flask(__name__)

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "Harvey backend is running!"})

@app.route("/salesiq-webhook", methods=["POST"])
def handle_salesiq():
    try:
        data = request.get_json()
        
        # Handle 'message' as string or dict
        raw_input = data.get("message", "")
        if isinstance(raw_input, dict):
            user_input = raw_input.get("text", "").strip()
        else:
            user_input = str(raw_input).strip()
        
        visitor_id = data.get("visitor_id", "anonymous")

        if not user_input:
            return jsonify({"reply": "I didn't receive any message. Could you please rephrase or try again?"}), 400

        print(f"📩 Message from {visitor_id}: {user_input}")

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

        # Step 4: Wait for assistant to finish
        while run.status != "completed":
            time.sleep(1)
            run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        # Step 5: Get the assistant's reply
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        assistant_reply = messages.data[0].content[0].text.value.strip()

        print("🤖 Assistant reply:", assistant_reply)

        return jsonify({"reply": assistant_reply})

    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
        return jsonify({"reply": "Sorry, something went wrong. Please try again later."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
