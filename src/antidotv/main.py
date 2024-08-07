import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, List

from antidotv.args import build_parser


@dataclass
class Module:
    name: str
    inouts: List[str]

    def instantiate(self, instance: str) -> str:
        _format: str = ""
        _tabs: str = self._resolve_tabs(instance) * " "
        for inout in self.inouts:
            if not re.findall(rf"\.\b({inout})\b *?.*?,", instance):
                _format += f"{_tabs}.{inout},\n"
        return _format.strip(",\n").strip()

    @staticmethod
    def _resolve_tabs(instance: str) -> int:
        match = re.search(r"( *)\.\*", instance)
        if match:
            return len(match.group(1))
        return 0


def find_sv_wildcards(root_folder: str) -> List[str]:
    if os.path.isfile(root_folder):
        if root_folder.endswith(".sv"):
            with open(root_folder, "r") as f:
                file_content: str = f.read()
                if ".*" in file_content:
                    return [root_folder]

    wildcards: List[str] = []

    # Walk through the root folder and its subdirectories
    for subdir, _, files in os.walk(root_folder):
        for file in files:
            if file.endswith(".sv"):
                file_path: str = os.path.join(subdir, file)
                with open(file_path, "r") as f:
                    file_content: str = f.read()
                    if ".*" in file_content:
                        wildcards.append(file_path)

    return wildcards


def find_sv_modules(root_folder: str) -> Dict[str, List[Module]]:
    sv_modules: Dict[str, List[Module]] = {}

    # Regular expression to match SystemVerilog module definitions
    module_regex: re.Pattern[str] = re.compile(
        r"^\s*module\s+(\w+)(?:.|\s)*?endmodule", re.MULTILINE
    )

    # Walk through the root folder and its subdirectories
    for subdir, _, files in os.walk(root_folder):
        for file in files:
            if file.endswith(".sv"):
                file_path: str = os.path.join(subdir, file)
                with open(file_path, "r") as f:
                    file_content: str = f.read()
                    file_modules: List[Module] = []
                    for match in module_regex.finditer(file_content):
                        if match:
                            start, end = match.span()
                            module: str = file_content[start:end]
                            file_modules.append(
                                Module(name=match.group(1), inouts=parse_inouts(module))
                            )
            sv_modules[file_path] = file_modules

    return sv_modules


def parse_inouts(module_content: str) -> List[str]:
    inouts: List[str] = []
    for match in re.finditer(
        r"^ *?\b(input|output|inout).+?(\w+)(\,|\s\)\;)", module_content, re.MULTILINE
    ):
        _, name, _ = match.groups()
        inouts.append(name)
    return inouts


def replace_star_with_signals(file_content: str, module: Module) -> str:
    cured_file_content: str = file_content

    for match in re.finditer(
        rf"(?s)^ +\b({module.name})\s*#?\(.*?\)\;", cured_file_content, re.MULTILINE
    ):
        print(f"[INFO]: {module.name} instantiated.")
        start, end = match.span()
        instance: str = cured_file_content[start:end]
        if ".*" in instance:
            replacement: str = module.instantiate(instance)
            new_instance: str = instance.replace(".*", replacement)
            print(f"[INFO]: Removed wildcard instantiation of {module.name}.")
            cured_file_content = (
                cured_file_content[:start] + new_instance + cured_file_content[end:]
            )

    return cured_file_content


def cure_from_wildcards(file_path: str, sv_modules: Dict[str, List[Module]]) -> None:
    print(f"[INFO]: Trying to cure {file_path}.")

    with open(file_path, "r") as f:
        file_content = f.read()

    for path in sv_modules.keys():
        for module in sv_modules[path]:
            file_content = replace_star_with_signals(file_content, module)

    # Fix syntax errors if any
    for match in re.finditer(rf",\n\s+\)\;", file_content, re.MULTILINE):
        file_content = file_content.replace(match.group(0), "\n  );")

    # Write the updated content back to the input file
    with open(file_path, "w") as f:
        f.write(file_content)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Read the input SystemVerilog file
    input_path: str = args.path
    # Define the paths to search for module definitions
    search_path: str = args.root

    files: List[str] = find_sv_wildcards(input_path)

    print(f"[INFO] Found {len(files)} file(s) to cure in {input_path}.")

    if not files:
        sys.exit(0)

    sv_modules: Dict[str, List[Module]] = find_sv_modules(search_path)

    print(f"[INFO] Found {len(sv_modules)} modules in {search_path}.")

    for file in files:
        cure_from_wildcards(file, sv_modules)

    sys.exit(0)


if __name__ == "__main__":
    main()
