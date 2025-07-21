from flask import Flask, request
from dotenv import load_dotenv
import os
import requests
import re

app = Flask(__name__)

# Load environment variables from .env
load_dotenv()
PAGE_ACCESS_TOKEN = os.getenv('PAGE_ACCESS_TOKEN')  # Facebook Page Access Token

# Your secret verify token (set in Facebook webhook)
VERIFY_TOKEN = os.getenv('VERIFY_TOKEN', 'your_default_verify_token_here')


def postprocess(response):
    # Replace bold/underline tags with *
    response = re.sub(r"<\/?u>", "*", response)
    response = re.sub(r"<\/?b>", "*", response)
    response = re.sub(r"\*\*(.*?)\*\*", r"*\1*", response)
    response = re.sub(
        r'\[(https?://[^\]]+)\]\(\1\)',
        r'[Click here](\1)',
        response
    )
    response = re.sub(r"\n+", "\n", response)
    return response.strip()


def chatbot_reply(message):
    try:
        model_api_url = "192.168.1.29:8000"
        payload = {
            "message": message,
            "language": "en"
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(model_api_url, json=payload, headers=headers)

        if response.status_code == 200:
            model_output = response.json()
            raw_reply = model_output.get("response", "")
            print("Raw reply from model:", raw_reply)
            return postprocess(raw_reply)
        else:
            print("Model error:", response.text)
            return "Sorry, I couldn't process your request right now."
    except Exception as e:
        print("Exception while calling model:", e)
        return "Oops! Something went wrong."


def send_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v18.0/me/messages"
    headers = {
        'Content-Type': 'application/json'
    }
    params = {
        'access_token': PAGE_ACCESS_TOKEN
    }
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }

    response = requests.post(url, headers=headers, params=params, json=payload)
    print("Sent reply:", response.status_code, response.text)
    return response


@app.route('/')
def home():
    return "Messenger Bot is running", 200


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("WEBHOOK VERIFIED")
            return challenge, 200
        else:
            print("WEBHOOK VERIFICATION FAILED")
            return "Verification failed", 403

    elif request.method == 'POST':
        data = request.get_json()
        print("Received webhook event:", data)
        try:
            for entry in data.get("entry", []):
                for messaging_event in entry.get("messaging", []):
                    if "message" in messaging_event:
                        sender_id = messaging_event["sender"]["id"]
                        message_text = messaging_event["message"].get("text")

                        if message_text:
                            print(f"Received message from {sender_id}: {message_text}")
                            bot_response = chatbot_reply(message_text)
                            send_message(sender_id, bot_response)
        except Exception as e:
            print("Error processing webhook:", e)

        return "EVENT_RECEIVED", 200


# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=8000)
