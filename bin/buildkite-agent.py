#! /nix/var/nix/profiles/default/bin/nix-shell
#! nix-shell python3.nix -i python3
import fnmatch
import json
import os
import subprocess
import sys
import tempfile
from io import BytesIO
from typing import Any

from ruamel.yaml import YAML


def _read_file_to_str(file: str) -> str:
    with open(file, 'r') as f:
        return f.read()


def _is_neighbor_to_current_file(path: str):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.dirname(os.path.abspath(path))
    return current_dir == target_dir


def _search_for_real_buildkite_agent() -> str:
    paths = os.environ.get('PATH', '').split(os.pathsep)
    for path in paths:
        executable = os.path.join(path, 'buildkite-agent')
        if _is_neighbor_to_current_file(executable):
            continue
        if os.path.isfile(executable) and os.access(executable, os.X_OK):
            return executable
    raise Exception('buildkite-agent not found!')


# BUILDKITE_PLUGINS="[{\"github.com/bz-canva/buildkite-agent-wrapper-buildkite-plugin#main\":
# {\"trusted_branches\":[\"master\",\"release-*\",\"boris-trusted*\"]}}, ... }]"
def _get_trusted_branches(json_str: str) -> list[str]:
    json_data = json.loads(json_str)
    plugin_config: dict[str, Any] = next(
        (key for key in json_data if "buildkite-agent-wrapper-buildkite-plugin" in key))
    return plugin_config.get("trusted_branches")


def _is_trusted_job() -> bool:
    current_branch = _require_env("BUILDKITE_BRANCH")
    trusted_branch = _get_trusted_branches(_require_env("BUILDKITE_PLUGINS"))

    for pattern in trusted_branch:
        if fnmatch.fnmatch(current_branch, pattern):
            return True
    return False


def _inject_into_steps(steps: list[Any]):
    for step in steps:
        if isinstance(step, dict) and "agents" in step:
            agents = step["agents"]
            if isinstance(agents, list):
                agents.append(f"trusted={str(_is_trusted_job()).lower()}")
            elif isinstance(agents, dict):
                agents["trusted"] = _is_trusted_job()
            else:
                raise Exception(f"Not supported: {agents}")


def _inject_trusted_tags_into_pipeline_yaml(pipeline_yaml: str) -> str:
    yaml = YAML()
    pipeline_data = yaml.load(pipeline_yaml)
    # if current branch is trusted branch, add 'trusted=true', else ass 'trusted=false'
    if isinstance(pipeline_data, list):
        _inject_into_steps(pipeline_data)
    else:
        _inject_into_steps(pipeline_data.get("steps", []))

    buf = BytesIO()
    yaml.dump(pipeline_data, buf)
    return buf.getvalue().decode("utf-8")


def _require_env(name: str) -> str:
    if (value := os.getenv(name)) is None:
        raise Exception(f"Env {name} doesn't exist!")
    return value


def _run_inherit_io(args: list[str]) -> int:
    print(f"Running: {args}")
    result = subprocess.run(args, stdout=sys.stdout, stderr=sys.stderr)
    return result.returncode


def main():
    if sys.argv[1:3] == ['pipeline', 'upload']:
        if len(sys.argv) == 3:
            pipeline_yaml = sys.stdin.read()
        else:
            pipeline_yaml = _read_file_to_str(sys.argv[3])

        yaml = _inject_trusted_tags_into_pipeline_yaml(pipeline_yaml)
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
            print(f"YAML:\n {yaml}")
            temp_file.write(yaml)
            temp_file_name = temp_file.name
            # print(_read_file_to_str(str(temp_file)))
        _run_inherit_io([_search_for_real_buildkite_agent()] + sys.argv[1:3] + [temp_file_name] + sys.argv[3:])
    else:
        _run_inherit_io([_search_for_real_buildkite_agent()] + sys.argv[1:])


if __name__ == "__main__":
    main()
