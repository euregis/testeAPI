import json
import argparse
import re
import requests
from typing import Any, Dict, List
from jinja2 import Template
import jmespath

class WorkflowExecutor:
    def __init__(self, workflow: Dict[str, Any], use_proxy: bool = False, proxies: Dict[str, str] = None):
        self.workflow = workflow
        self.context = {"global": workflow.get("global", {}), "steps": {}}
        self.use_proxy = use_proxy
        self.proxies = proxies if use_proxy else {}

    def substituir_bloco(d: dict, bloco: str, valor_esperado: str) -> dict:
        """
        Substitui o bloco no dicionário pelo valor esperado.
        Exemplo:
            d = {'nome': 'joão', '{{...}}': '{{user1.body.address...}}'}
            bloco = '{{...}}'
            valor_esperado = '{{user1.body.address[1:-1]}}'
            resultado: {'nome': 'joão', '{{user1.body.address[1:-1]}}': '{{user1.body.address...}}'}
        """
        novo_dict = {}
        for k, v in d.items():
            if k == bloco:
                # Extrai o conteúdo entre {{ e ...}} para montar a nova chave
                if isinstance(v, str) and v.startswith("{{") and "..." in v:
                    inicio = v.find("{{") + 2
                    fim = v.find("...")
                    base = v[inicio:fim]
                    nova_chave = f"{{{{{base}[1:-1]}}}}"
                    novo_dict[nova_chave] = v
                else:
                    novo_dict[valor_esperado] = v
            else:
                novo_dict[k] = v
        return novo_dict

    # # Exemplo de uso:
    # d = {'nome': 'joão', '{{...}}': '{{user1.body.address...}}'}
    # resultado = substituir_bloco(d, '{{...}}', '{{user1.body.address[1:-1]}}')
    # print(resultado)

    # def render_template(self, data: Any) -> Any:
    #     if isinstance(data, str):
    #         print(f"\n\n\data: {data}\n\n\n")
    #         template = Template(data)
    #         flat_context = self.flatten_context()
    #         flat_context.update(self.context["global"])  # Inclui variáveis globais
    #         flat_context.update(self.context["steps"])
    #         # print(f"Flat context: {flat_context}")
    #         # print(f"Template: {template.render(flat_context)}")
    #         return template.render(flat_context)  # Substitui variáveis no template
    #     elif isinstance(data, dict):
    #         print(f"\n\n\Dict: {data}\n\n\n")
    #         # print(f"\n\n\address: {data}\n\n\n")
    #         # print(f"Dict: {data}")
    #         return {k: self.render_template(v) for k, v in data.items()}  # Processa dicionários
    #     elif isinstance(data, list):
    #         print(f"\n\nList: {data}\n\n\n")
    #         return [self.render_template(v) for v in data]  # Processa listas
    #     # print(f"Data: {data}")
    #     return data
    
    # def render_template(self, data: Any) -> Any:
    #     """
    #     Recebe um dict, transforma em string, executa o template.render(flat_context)
    #     e retorna novamente como dict.
    #     """
    #     # import json
    #     if isinstance(data, dict):
    #         data_str = json.dumps(data)
    #         data_str = self.substituir_bloco_jinja2(data_str)
    #         print(f"\n\DADOS: {data_str}\n\n\n")

    #         template = Template(data_str)
    #         flat_context = self.flatten_context()
    #         flat_context.update(self.context["global"])
    #         flat_context.update(self.context["steps"])
    #         context={**self.context["global"], **self.context["steps"]}
    #         print(f"\n\CONTEXT: {context}\n\n\n")
    #         rendered_str = template.render(context)
    #         print(f"\n\DEU BOM: {rendered_str}\n\n\n")
    #         return json.loads(rendered_str)
    #     elif isinstance(data, list):
    #         return [self.render_template_dict(v) for v in data]
    #     elif isinstance(data, str):
    #         template = Template(data)
    #         flat_context = self.flatten_context()
    #         flat_context.update(self.context["global"])
    #         flat_context.update(self.context["steps"])
    #         return template.render(flat_context)
    #     return data
    
    def expand_dict_keys(self, data):
        """Expande {{user1.body.address}} para os pares chave-valor do dict correspondente."""
        if isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                if isinstance(k, str) and k.startswith("{{") and k.endswith("}}"):
                    # Extrai o caminho do contexto
                    path = k[2:-2].strip()
                    value = self.get_from_context(path)
                    if isinstance(value, dict):
                        new_dict.update(value)
                    else:
                        # Se não for dict, insere normalmente
                        new_dict[path] = value
                else:
                    new_dict[k] = self.expand_dict_keys(v)
            return new_dict
        elif isinstance(data, list):
            return [self.expand_dict_keys(item) for item in data]
        return data

    def get_from_context(self, path):
        """Busca um valor do contexto usando notação ponto."""
        parts = path.split('.')
        value = {**self.context["global"], **self.context["steps"]}
        for part in parts:
            value = value.get(part)
            if value is None:
                break
        return value

    def render_template(self, data: Any) -> Any:
        if isinstance(data, dict):
            # Expande antes de renderizar
            data = self.expand_dict_keys(data)
            data_str = json.dumps(data)
            template = Template(data_str)
            flat_context = {**self.context["global"], **self.context["steps"]}
            rendered_str = template.render(flat_context)
            return json.loads(rendered_str)
        elif isinstance(data, list):
            return [self.render_template(v) for v in data]
        elif isinstance(data, str):
            template = Template(data)
            flat_context = {**self.context["global"], **self.context["steps"]}
            return template.render(flat_context)
        return data


    def substituir_bloco_jinja2(self, texto: str) -> str:
        """
        Substitui '"{{...}}": "{{algum.valor...}}"' por '{{algum.valor[1:-1]}}'
        """
        # Regex para encontrar '"{{...}}": "{{algum.valor...}}"'
        padrao = r'"{{\.\.\.}}":\s*"{{([^\.}]+(?:\.[^\.}]+)*)\.\.\.}}"'
        def repl(match):
            valor = match.group(1)
            return f'{{{{{valor}[1:-1]}}}}'
        return re.sub(padrao, repl, texto)

    def flatten_context(self) -> Dict[str, str]:
        flat = {}
        def flatten(prefix, obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    flatten(f"{prefix}.{k}" if prefix else k, v)
            else:
                flat[prefix] = str(obj)
        flatten("", self.context["global"])
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
        elif operator == "minLength":
            return len(str(actual)) >= int(expected)
        elif operator == "maxLength":
            return len(str(actual)) <= int(expected)
        elif operator == "isType":
            return isinstance(actual, eval(expected))
        elif operator == "matchesRegex":
            import re
            return re.match(expected, str(actual)) is not None
        else:
            return False

    def log(self, message: str):
        print(message)

    def run(self, steps_to_run: List[str] = None):
        all_steps = list(self.workflow["steps"].keys())
        steps_to_run = steps_to_run or all_steps
        steps_order = self.resolve_dependencies(steps_to_run)

        for step_name in steps_order:
            original_step = self.workflow["steps"][step_name]
            # print(f"Original step: {original_step}")

            step = self.render_template(original_step)
            # print(f"Step: {step}")

            method = step["method"].upper()
            url = step["url"]
            headers = step.get("headers", {})
            body = step.get("body", {})

            self.log(f"\n🔷 Running step: {step_name} - {method} {url}")
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

            # Armazena o status, headers e body no contexto
            self.context["steps"][step_name] = {
                "status": response.status_code,
                "headers": dict(response.headers),
                "body": body_json
            }

            success_validations, failed_validations = self.validate(step.get("validations", []), response, body_json)

            if success_validations:
                self.log(f"✅ Successful validations for step '{step_name}':")
                for success in success_validations:
                    self.log(f"   - {success}")

            if failed_validations:
                self.log(f"❌ Failed validations for step '{step_name}':")
                for failure in failed_validations:
                    self.log(f"   - {failure}")
                break

            self.log(f"✅ Step '{step_name}' completed successfully (Status: {response.status_code})")

    def run_single_step(self, steps_to_run: str):
        steps_order = self.resolve_dependencies([steps_to_run])
        results = []

        for step_name in steps_order:
            original_step = self.workflow["steps"][step_name]
            step = self.render_template(original_step)

            method = step["method"].upper()
            url = step["url"]
            headers = step.get("headers", {})
            body = step.get("body", {})

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
            if steps_to_run == step_name or failed_validations:
                
                step_result = {
                    "step": step_name,
                    "status": response.status_code,
                    "headers": dict(response.headers),
                    "body": body_json,
                    "success_validations": success_validations,
                    "failed_validations": failed_validations
                }
                results.append(step_result)

                if failed_validations:
                    break

        return results[-1]  # Return the result of the last executed step

def main():
    parser = argparse.ArgumentParser(description="Workflow Executor CLI")
    parser.add_argument("json_path", help="Caminho para o arquivo JSON do workflow")
    parser.add_argument("--step", "-s", nargs="+", help="Step(s) a executar (executa dependências também)")
    parser.add_argument("--use-proxy", action="store_true", help="Usar proxy")
    parser.add_argument("--http-proxy", help="Proxy HTTP (ex: http://localhost:8080)")
    parser.add_argument("--https-proxy", help="Proxy HTTPS (ex: http://localhost:8080)")

    args = parser.parse_args()

    try:
        with open("workflows/"+args.json_path) as f:
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
