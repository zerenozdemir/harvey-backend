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

# Load API key from environment variable (recommended for security)
openai.api_key = os.getenv("OPENAI_API_KEY")

# Replace with your real Assistant ID
ASSISTANT_ID = os.getenv("HARVEY_ASSISTANT_ID")

app = Flask(__name__)

@app.route("/salesiq-webhook", methods=["POST"])
def handle_salesiq():
    data = request.get_json()
    user_input = data.get("message", "")
    visitor_id = data.get("visitor_id", "anonymous")

    try:
        # Step 1: Create a thread
        thread = openai.beta.threads.create()

        # Step 2: Add message from visitor
        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        # Step 3: Run the assistant
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Step 4: Wait until run is complete
        while run.status != "completed":
            time.sleep(1)
            run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        # Step 5: Get the assistant's reply
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        assistant_reply = messages.data[0].content[0].text.value.strip()

        return jsonify({"reply": assistant_reply})

    except Exception as e:
        print("Error:", e)
        return jsonify({"reply": "Sorry, something went wrong. Please try again later."}), 500

if __name__ == "__main__":
    app.run(app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
)