from backend.graph.email_assistant_graph import email_assistant_app
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route("/run-agent", methods=["GET"])
async def run_agent_flask():
    query = request.args.get("query", "")
    result = email_assistant_app.invoke({"input": query})
    return jsonify(result)

