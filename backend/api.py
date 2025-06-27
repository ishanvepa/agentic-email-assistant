import time
import uuid
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from langchain_core.messages import HumanMessage
from multi_agent_graph import supervisor_prebuilt


app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])

@app.route("/agent", methods=["POST"])
def agent():
    data = request.get_json()
    user_prompt = data.get("prompt", "")
    print(f"Received prompt: {user_prompt}")
    if not user_prompt:
        return jsonify({"error": "No prompt provided"}), 400

    thread_id = uuid.uuid4()
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 20,
        "verbose": True
    }

    try:
        result = supervisor_prebuilt.invoke(
            {"messages": [HumanMessage(content=user_prompt)]},
            config=config
        )
        messages = [
            {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().strftime("%I:%M %p").lstrip("0").lower(),
            "action": msg.content,
            "status": "completed"
            }
            for msg in result["messages"]
        ]
        print("Agent output:")
        return jsonify({"response": messages})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)