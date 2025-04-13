import os
import json
from flask import Flask, request, jsonify, render_template
import requests
import jmespath

app = Flask(__name__)

WORKFLOW_FILE = "workflow.json"

def load_workflow():
    if os.path.exists(WORKFLOW_FILE):
        with open(WORKFLOW_FILE, "r") as f:
            return json.load(f)
    return {
        "workflowName": "SampleChain",
        "global": {
            "input": {
                "userId": "12345",
                "token": "abcde12345"
            }
        },
        "steps": {}
    }

def save_workflow(data):
    with open(WORKFLOW_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Load once when app starts (can also reload per request)
workflow = load_workflow()


# In-memory workflow store
workflow = {
    "workflowName": "SampleChain",
    "global": {
        "input": {
            "userId": "12345",
            "token": "abcde12345"
        }
    },
    "steps": {}
}

@app.route("/workflow", methods=["GET"])
def get_workflow():
    return jsonify(load_workflow())

@app.route("/workflow", methods=["PUT"])
def update_workflow():
    wf = load_workflow()
    wf["workflowName"] = data.get("workflowName", wf["workflowName"])
    wf["global"] = data.get("global", wf["global"])
    save_workflow(wf)
    return jsonify({"message": "Workflow updated", "workflow": wf})

@app.route("/steps", methods=["POST"])
def add_step():
    data = request.json
    step_name = data.get("name")
    if not step_name:
        return jsonify({"error": "Step 'name' is required"}), 400
    wf = load_workflow()
    wf["steps"][step_name] = {
        "method": data.get("method"),
        "url": data.get("url"),
        "headers": data.get("headers", {}),
        "body": data.get("body", {}),
        "dependsOn": data.get("dependsOn", []),
        "validations": data.get("validations", [])
    }
    save_workflow(wf)
    return jsonify({"message": f"Step '{step_name}' added", "step": wf["steps"][step_name]})

@app.route("/steps/<name>", methods=["PUT"])
def update_step(name):
    wf = load_workflow()
    if name not in wf["steps"]:
        return jsonify({"error": f"Step '{name}' not found"}), 404
    data = request.json
    wf["steps"][name].update({
        "method": data.get("method", wf["steps"][name]["method"]),
        "url": data.get("url", wf["steps"][name]["url"]),
        "headers": data.get("headers", wf["steps"][name].get("headers", {})),
        "body": data.get("body", wf["steps"][name].get("body", {})),
        "dependsOn": data.get("dependsOn", wf["steps"][name].get("dependsOn", [])),
        "validations": data.get("validations", wf["steps"][name].get("validations", []))
    })
    save_workflow(wf)
    return jsonify({"message": f"Step '{name}' updated", "step": wf["steps"][name]})

@app.route("/steps/<name>", methods=["DELETE"])
def delete_step(name):
    wf = load_workflow()
    if name in wf["steps"]:
        del wf["steps"][name]
        save_workflow(wf)
        return jsonify({"message": f"Step '{name}' deleted"})
    return jsonify({"error": f"Step '{name}' not found"}), 404

@app.route("/steps/<name>/execute", methods=["POST"])
def execute_step(name):
    wf = load_workflow()
    step = wf["steps"].get(name)
    if not step:
        return jsonify({"error": f"Step '{name}' not found"}), 404

    method = step["method"].upper()
    url = step["url"]
    headers = step.get("headers", {})
    body = step.get("body", {})

    response = requests.request(
        method,
        url,
        headers=headers,
        json=body if method in ["POST", "PUT", "PATCH"] else None
    )

    try:
        body_json = response.json()
    except Exception:
        body_json = {}

    validations = step.get("validations", [])
    success_validations = []
    failed_validations = []

    for v in validations:
        target = v["target"]
        operator = v["operator"]
        expected = v.get("value")

        if target.startswith("body."):
            actual = jmespath.search(target[5:], body_json)
        elif target.startswith("headers."):
            actual = response.headers.get(target[8:])
        elif target == "status":
            actual = response.status_code
        else:
            continue

        if operator == "equals" and actual == expected:
            success_validations.append(f"{target} {operator} {expected}")
        elif operator == "notEquals" and actual != expected:
            success_validations.append(f"{target} {operator} {expected}")
        elif operator == "notEmpty" and bool(actual):
            success_validations.append(f"{target} {operator}")
        elif operator == "greaterThan" and float(actual) > float(expected):
            success_validations.append(f"{target} {operator} {expected}")
        elif operator == "contains" and str(expected) in str(actual):
            success_validations.append(f"{target} {operator} {expected}")
        else:
            failed_validations.append(f"{target} {operator} {expected}, got {actual}")

    return jsonify({
        "status": response.status_code,
        "headers": dict(response.headers),
        "body": body_json,
        "success_validations": success_validations,
        "failed_validations": failed_validations
    })

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)