from flask import Flask, request, jsonify
from openai import OpenAI
import os
import time
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    default_headers={"OpenAI-Beta": "assistants=v2"}
)

ASSISTANT_ID = os.getenv("HARVEY_ASSISTANT_ID")  # Still using this env var for now

app = Flask(__name__)

@app.route("/", methods=["GET", "HEAD"])
def health_check():
    return jsonify({"status": "OK"}), 200

@app.route("/salesiq-webhook", methods=["POST"])
def handle_salesiq():
    try:
        data = request.get_json(force=True)
        print("📥 Incoming Data:", data)

        user_input = data.get("message", {}).get("text", "").strip()
        visitor_id = data.get("visitor", {}).get("email", "anonymous")

        if not user_input:
            print("❌ Invalid or missing message text")
            return jsonify({
                "action": {
                    "say": "I'm sorry, I didn't catch that. Could you rephrase?"
                }
            }), 200

        print(f"💬 Visitor [{visitor_id}]: {user_input}")

        # Step 1: Create thread
        thread = client.beta.threads.create()

        # Step 2: Add user message
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        # Step 3: Run assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Step 4: Poll until complete
        while run.status not in ["completed", "failed", "cancelled"]:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

        if run.status != "completed":
            print(f"❌ Run did not complete successfully: {run.status}")
            return jsonify({
                "action": {
                    "say": "Sorry, I couldn't process that right now. Please try again."
                }
            }), 200

        # Step 5: Get assistant's response
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        assistant_reply = None
        for msg in messages.data:
            if msg.role == "assistant":
                assistant_reply = msg.content[0].text.value.strip()
                break

        if not assistant_reply:
            print("❌ No assistant reply found")
            return jsonify({
                "action": {
                    "say": "Sorry, I didn’t get that. Please try again."
                }
            }), 200

        print(f"🤖 DD says: {assistant_reply}")

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
        }), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
