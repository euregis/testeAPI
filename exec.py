import json
import argparse
import requests
from typing import Any, Dict, List
from string import Template
import jmespath

class WorkflowExecutor:
    def __init__(self, workflow: Dict[str, Any], use_proxy: bool = False, proxies: Dict[str, str] = None):
        self.workflow = workflow
        self.context = {"global": workflow.get("global", {}), "steps": {}}
        self.use_proxy = use_proxy
        self.proxies = proxies if use_proxy else {}

    def render_template(self, data: Any) -> Any:
        if isinstance(data, str):
            template = Template(data)
            flat_context = self.flatten_context()
            return template.safe_substitute(flat_context)
        elif isinstance(data, dict):
            return {k: self.render_template(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.render_template(v) for v in data]
        return data

    def flatten_context(self) -> Dict[str, str]:
        flat = {}
        def flatten(prefix, obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    flatten(f"{prefix}.{k}" if prefix else k, v)
            else:
                flat[prefix] = str(obj)
        flatten("", self.context["global"].get("input", {}))
        for step, result in self.context["steps"].items():
            flatten(step, result)
        return flat

    def resolve_dependencies(self, steps_to_run: List[str]) -> List[str]:
        steps = self.workflow["steps"]
        resolved = []
        visited = set()

        def add_with_deps(step_name):
            if step_name in visited:
                return
            step_data = steps.get(step_name)
            if not step_data:
                raise ValueError(f"Step '{step_name}' not found.")
            dep = step_data.get("dependsOn", "").strip()
            if dep:
                add_with_deps(dep)
            resolved.append(step_name)
            visited.add(step_name)

        for step in steps_to_run:
            add_with_deps(step)

        return resolved

    def validate(self, validations: List[Dict], response: requests.Response, body_json: Any):
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

            if self.compare(actual, operator, expected):
                success_validations.append(f"{target} {operator} {expected}")
            else:
                failed_validations.append(f"{target} {operator} {expected}, got {actual}")

        return success_validations, failed_validations

    def compare(self, actual, operator, expected) -> bool:
        if operator == "equals":
            return actual == expected
        elif operator == "notEquals":
            return actual != expected
        elif operator == "notEmpty":
            return bool(actual)
        elif operator == "greaterThan":
            return float(actual) > float(expected)
        elif operator == "contains":
            return str(expected) in str(actual)
        else:
            return False

    def run(self, steps_to_run: List[str] = None):
        all_steps = list(self.workflow["steps"].keys())
        steps_to_run = steps_to_run or all_steps
        steps_order = self.resolve_dependencies(steps_to_run)

        for step_name in steps_order:
            original_step = self.workflow["steps"][step_name]
            step = self.render_template(original_step)
            method = step["method"].upper()
            url = step["url"]
            headers = step.get("headers", {})
            body = step.get("body", {})

            print(f"\n🔷 Running step: {step_name} - {method} {url}")
            response = requests.request(
                method,
                url,
                headers=headers,
                json=body if method in ['POST', 'PUT', 'PATCH'] else None,
                proxies=self.proxies
            )

            try:
                body_json = response.json()
            except Exception:
                body_json = {}

            self.context["steps"][step_name] = {
                "status": response.status_code,
                "headers": dict(response.headers),
                "body": body_json
            }

            success_validations, failed_validations = self.validate(step.get("validations", []), response, body_json)

            if success_validations:
                print(f"✅ Successful validations for step '{step_name}':")
                for success in success_validations:
                    print(f"   - {success}")

            if failed_validations:
                print(f"❌ Failed validations for step '{step_name}':")
                for failure in failed_validations:
                    print(f"   - {failure}")
                break

            print(f"✅ Step '{step_name}' completed successfully (Status: {response.status_code})")

def main():
    parser = argparse.ArgumentParser(description="Workflow Executor CLI")
    parser.add_argument("json_path", help="Caminho para o arquivo JSON do workflow")
    parser.add_argument("--step", "-s", nargs="+", help="Step(s) a executar (executa dependências também)")
    parser.add_argument("--use-proxy", action="store_true", help="Usar proxy")
    parser.add_argument("--http-proxy", help="Proxy HTTP (ex: http://localhost:8080)")
    parser.add_argument("--https-proxy", help="Proxy HTTPS (ex: http://localhost:8080)")

    args = parser.parse_args()

    try:
        with open(args.json_path) as f:
            workflow_json = json.load(f)

        proxies = {
            "http": args.http_proxy,
            "https": args.https_proxy
        } if args.use_proxy else {}

        executor = WorkflowExecutor(workflow_json, use_proxy=args.use_proxy, proxies=proxies)
        executor.run(steps_to_run=args.step)
    except ValueError as e:
        print(e)

if __name__ == "__main__":
    main()
