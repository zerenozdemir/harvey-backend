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

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"action": {"say": assistant_reply}})

@app.route("/salesiq-webhook", methods=["POST"])
def handle_salesiq():
    try:
        print("=== Zobot Webhook Triggered ===")

        # Raw body and headers
        raw = request.data.decode("utf-8")
        headers = dict(request.headers)

        print("Headers:", headers)
        print("Raw body:", raw)

        # Try parsing JSON
        try:
            data = request.get_json(force=True)
            print("Parsed JSON:", data)
        except Exception as json_err:
            print("❌ JSON parse error:", json_err)
            data = {}

        return jsonify({"status": "received", "echo": data}), 200

    except Exception as e:
        print("❌ Fatal error:", e)
        return jsonify({"error": "unhandled exception"}), 500


    except Exception as e:
        print("Error handling Zobot message:", e)
        return jsonify({"reply": "Sorry, something went wrong. Please try again later."}), 500


    except Exception as e:
        print("Error handling Zobot message:", e)
        return jsonify({"reply": "Sorry, something went wrong. Please try again later."}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
