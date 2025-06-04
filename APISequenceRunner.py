import requests
import time
import json
import os
import argparse
import random
import string
from jinja2 import Template
from datetime import datetime

class APIRunner:
    def __init__(self, sequence_name, environment):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, 'config.json')
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.sequence_name = sequence_name
        self.environment = environment
        self.variables = self.config.get('env', {}).copy()
        self.generators = self.config.get('generators', {})
        self.base_dir = base_dir

    def render_template(self, template_str):
        template = Template(template_str)
        return template.render(**self.variables)

    def extract_variables(self, extract_config, response_json):
        for var_name, path in extract_config.items():
            keys = path.split('.')
            value = response_json
            try:
                for key in keys:
                    value = value[key]
                self.variables[var_name] = value
            except (KeyError, TypeError):
                print(f"Warning: Could not extract {var_name} from path {path}")

    def load_template(self, template_path):
        full_path = os.path.join(self.base_dir, template_path)
        with open(full_path, 'r') as f:
            return f.read()

    def evaluate_success_condition(self, condition, response_json):
        try:
            keys = condition['path'].split('.')
            value = response_json
            for key in keys:
                value = value[key]
            if 'equals' in condition:
                return value == condition['equals']
            elif 'exists' in condition:
                return condition['exists'] == (value is not None)
        except (KeyError, TypeError):
            return False
        return False

    def generate_value(self, spec):
        if spec['type'] == 'pattern':
            result = ''
            for ch in spec['pattern']:
                if ch == '#':
                    result += random.choice(string.digits)
                elif ch == '@':
                    result += random.choice(string.ascii_letters)
                else:
                    result += ch
            return result
        elif spec['type'] == 'alphanumeric':
            return ''.join(random.choices(string.ascii_letters + string.digits, k=spec.get('length', 10)))
        return ''

    def apply_dynamic_variables(self, dynamic_var_config):
        for var_name, generator_key in dynamic_var_config.items():
            spec = self.generators.get(generator_key)
            if spec:
                self.variables[var_name] = self.generate_value(spec)

    def get_nested_value(self, json_obj, path):
        keys = path.split('.')
        value = json_obj
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return None

    def make_request(self, step_name):
        step = self.config['api_calls'][step_name]
        system = step.get('system')
        env_systems = self.config.get('environments', {}).get(self.environment, {})
        base_url = env_systems.get(system)

        if not base_url:
            raise ValueError(f"Base URL for system '{system}' in environment '{self.environment}' is not defined")

        dynamic_vars = step.get('dynamic_variables', {})
        template_path = step.get('template', None)
        extract = step.get('extract', {})
        retries = step.get('retries', 3)
        timeout = step.get('timeout', 10)
        duration_limit = step.get('duration_limit', 300)
        success_condition = step.get('success_condition')
        print_output = step.get('print_output')
        method = step.get('method', 'GET').upper()

        start_time = datetime.now()

        for attempt in range(retries):
            if (datetime.now() - start_time).total_seconds() > duration_limit:
                raise TimeoutError(f"Exceeded total duration limit for {step_name}")

            if dynamic_vars:
                self.apply_dynamic_variables(dynamic_vars)

            endpoint_template = self.render_template(step['endpoint'])
            url = base_url + endpoint_template
            headers = json.loads(self.render_template(json.dumps(step.get('headers', {}))))

            body = None
            if template_path:
                template_str = self.load_template(template_path)
                rendered_body = self.render_template(template_str)
                body = json.loads(rendered_body)

            try:
                print(f"Calling {method} {url} (attempt {attempt + 1})")
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    json=body,
                    timeout=timeout
                )
                response.raise_for_status()
                response_json = response.json()

                if success_condition:
                    if self.evaluate_success_condition(success_condition, response_json):
                        print(f"Success condition met for {step_name}.")
                        if extract:
                            self.extract_variables(extract, response_json)
                        if print_output:
                            message = print_output.get("message", "")
                            value_path = print_output.get("path")
                            value = self.get_nested_value(response_json, value_path) if value_path else None
                            print(f"{message}: {value}")
                        return response
                    else:
                        print(f"Success condition not met for {step_name}.")
                        raise Exception("Condition not satisfied")
                else:
                    if extract:
                        self.extract_variables(extract, response_json)
                    if print_output:
                        message = print_output.get("message", "")
                        value_path = print_output.get("path")
                        value = self.get_nested_value(response_json, value_path) if value_path else None
                        print(f"{message}: {value}")
                    return response

            except requests.RequestException as e:
                print(f"Request failed: {e}")
                time.sleep(2 ** attempt)
            except Exception as e:
                print(f"Condition error: {e}")
                time.sleep(2 ** attempt)

        raise Exception(f"Failed to call {url} after {retries} attempts")

    def run(self):
        sequence = self.config['sequences'][self.sequence_name]
        for step_name in sequence:
            self.make_request(step_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run API sequence from config")
    parser.add_argument('sequence', help="Sequence name to execute")
    parser.add_argument('environment', help="Environment to use (e.g. test2, test3, QA2, QA3)")
    args = parser.parse_args()

    runner = APIRunner(args.sequence, args.environment)
    runner.run()