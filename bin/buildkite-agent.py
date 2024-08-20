#! /nix/var/nix/profiles/default/bin/nix-shell
#! nix-shell python3.nix -i python3
import os
import subprocess
import sys
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


def _is_trusted_job() -> bool:
    return True


def _inject_into_steps(steps: list[Any]):
    for step in steps:
        if isinstance(step, dict) and "agents" in step:
            agents = step["agents"]
            if isinstance(agents, list):
                agents.append("trusted=true")
            elif isinstance(agents, dict):
                agents["trusted"] = True
            else:
                raise Exception(f"Not supported: {agents}")


def _inject_trusted_tags_into_pipeline_yaml(pipeline_yaml: str):
    yaml = YAML()
    pipeline_data = yaml.load(pipeline_yaml)
    # if current branch is trusted branch, add 'trusted=true', else ass 'trusted=false'
    if isinstance(pipeline_data, list):
        _inject_into_steps(pipeline_data)
    else:
        _inject_into_steps(pipeline_data.get("steps", []))


def _run_inherit_io(args: list[str]) -> int:
    result = subprocess.run(args, stdout=sys.stdout, stderr=sys.stderr)
    return result.returncode


def main():
    print(f"args: {sys.argv}")
    if len(sys.argv) > 3 and sys.argv[1:3] == ['pipeline', 'upload']:
        pipeline_file = sys.argv[3]
        print(_read_file_to_str(pipeline_file))
    else:
        _run_inherit_io([_search_for_real_buildkite_agent()] + sys.argv[1:])


if __name__ == "__main__":
    print(f"config: {os.getenv('BUILDKITE_PLUGIN_CONFIGURATION')}")
    main()
