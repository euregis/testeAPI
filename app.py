import os
import json
from flask import Flask, request, jsonify, render_template
import requests
import jmespath
from exec import WorkflowExecutor  # Import the WorkflowExecutor class

app = Flask(__name__)

WORKFLOW_FILE = "workflow.json"

def load_workflow(name):
    workflow = "workflows/"+ name+".json"
    if os.path.exists(workflow):
        with open(workflow, "r") as f:
            return json.load(f)
    return {
        "workflowName": "SampleChain",
        "global": {
                "userId": "12345",
                "token": "abcde12345"
        },
        "steps": {},
        "useProxy": False
    }

def save_workflow(name, data):
    with open("workflows/"+name+".json", "w") as f:
        json.dump(data, f, indent=2)

# # Load once when app starts (can also reload per request)
# workflow = load_workflow()


@app.route("/workflow/<wf_name>", methods=["GET"])
def get_workflow(wf_name):
    return jsonify(load_workflow(wf_name))

@app.route("/workflow/<wf_name>", methods=["PUT"])
def update_workflow(wf_name):
    data = request.json
    wf = load_workflow(wf_name)
    wf["workflowName"] = data.get("workflowName", wf["workflowName"])
    wf["global"] = data.get("global", wf["global"])
    wf["useProxy"] = data.get("useProxy", wf.get("useProxy", False))
    save_workflow(wf_name, wf)
    return jsonify({"message": "Workflow updated", "workflow": wf})

@app.route("/workflow/<wf_name>/steps", methods=["POST"])
def add_step(wf_name):
    data = request.json
    step_name = data.get("name")
    if not step_name:
        return jsonify({"error": "Step 'name' is required"}), 400
    wf = load_workflow(wf_name)
    wf["steps"][step_name] = {
        "method": data.get("method"),
        "url": data.get("url"),
        "headers": data.get("headers", {}),
        "body": data.get("body", {}),
        "dependsOn": data.get("dependsOn", []),
        "validations": data.get("validations", [])
    }
    save_workflow(wf_name, wf)
    return jsonify({"message": f"Step '{step_name}' added", "step": wf["steps"][step_name]})

@app.route("/workflow/<wf_name>/steps/<name>", methods=["PUT"])
def update_step(wf_name, name):
    wf = load_workflow(wf_name)
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
    save_workflow(wf_name, wf)
    return jsonify({"message": f"Step '{name}' updated", "step": wf["steps"][name]})

@app.route("/workflow/<wf_name>/steps/<name>", methods=["DELETE"])
def delete_step(wf_name, name):
    wf = load_workflow(wf_name)
    if name in wf["steps"]:
        del wf["steps"][name]
        save_workflow(wf_name, wf)
        return jsonify({"message": f"Step '{name}' deleted"})
    return jsonify({"error": f"Step '{name}' not found"}), 404

@app.route("/workflow/<wf_name>/steps/<name>/execute", methods=["POST"])
def execute_step(wf_name, name):
    wf = load_workflow(wf_name)
    if name not in wf["steps"]:
        return jsonify({"error": f"Step '{name}' not found"}), 404

    json_data = request.get_json(force=True, silent=True) or {}
    env = json_data.get("env")
    use_proxy = json_data.get("useProxy", wf.get("useProxy", False))
    print("env", env, "useProxy", use_proxy)
    executor = WorkflowExecutor(wf)
    try:
        # Passe o use_proxy para o executor se necessário
        result = executor.run_single_step(name, env=env, use_proxy=use_proxy)
        result["env"] = env
        result["useProxy"] = use_proxy
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/workflows", methods=["GET"])
def list_workflows():
    workflows_dir = "workflows"
    if not os.path.exists(workflows_dir):
        os.makedirs(workflows_dir)
    workflows = [f.replace(".json", "") for f in os.listdir(workflows_dir) if f.endswith(".json")]
    return jsonify(workflows)

@app.route("/environments", methods=["GET"])
def list_environments():
    env_dir = os.path.join(os.path.dirname(__file__), "envs")
    envs = []
    if os.path.exists(env_dir):
        for fname in os.listdir(env_dir):
            if fname.startswith(".env"):
                env_name = fname.replace(".env.", "")
                envs.append({"name": env_name, "file": fname})
    return jsonify(envs)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)