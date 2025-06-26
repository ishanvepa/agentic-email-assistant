import time
from flask import Flask, jsonify, request
from flask_cors import CORS



app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])

@app.route("/fetch-semantic-scholar", methods=["GET"])
def r_fetch_semantic_scholar(total_results=100, batch_size=20):

    return papers_json


@app.route("/summarize-abstract", methods=["POST"])
def summarize_abstract():

    return jsonify({"summary": summary}), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)