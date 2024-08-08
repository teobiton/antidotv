import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, List

from antidotv.args import build_parser


def _read_file(fpath: str) -> str:
    with open(fpath, encoding="utf8") as f:
        return f.read()


def _is_verilog(fpath: str) -> bool:
    """Determine if input file is a Verilog or SystemVerilog file."""

    _extensions: List[str] = [".v", ".verilog", ".vlg", ".vh", ".sv", ".svh"]
    return any([fpath.endswith(ext) for ext in _extensions])


@dataclass
class Module:
    name: str
    inouts: List[str]

    def instantiate(self, instance: str, order: bool) -> str:
        """Rework the instantiation of the module"""

        format: List[str] = []
        tabs: str = self._resolve_tabs(instance) * " "

        for inout in self.inouts:
            if not re.findall(rf"\.\b({inout})\b *?.*?,", instance):
                format.append(f"{tabs}.{inout},")

        if order:
            return self._ordered_ios(instance, format)

        return instance.replace(".*", "\n".join(format).strip(",\n").strip())

    @staticmethod
    def _resolve_tabs(instance: str) -> int:
        match = re.search(r"( *)\.\*", instance)
        if match:
            return len(match.group(1))
        return 0

    def _ordered_ios(self, instance: str, new_ios: List[str]) -> str:
        """Order I/Os in new instance."""

        lines: List[str] = instance.replace(
            ".*", "\n".join(new_ios).strip()
        ).splitlines()
        ios_instantiation: Dict[str, str] = self._resolve_ios(lines)
        io: int = 0

        for nl, line in enumerate(lines):
            if any([line.strip().startswith(f".{inout}") for inout in self.inouts]):
                lines[nl] = ios_instantiation[self.inouts[io]]
                io += 1

        return "\n".join(lines).strip(",\n")

    def _resolve_ios(self, lines: List[str]) -> Dict[str, str]:
        """Match I/Os to how they're instantiated."""

        ios_instantiation: Dict[str, str] = {}

        for line in lines:
            for inout in self.inouts:
                match = re.match(rf"\.\b({inout})\b *?.*?,", line.strip())
                if match:
                    ios_instantiation[inout] = line
                    break

        return ios_instantiation


def find_sv_wildcards(root_folder: str) -> List[str]:
    """Find Verilog and SystemVerilog files with wildcards instantiations."""

    if os.path.isfile(root_folder):
        if _is_verilog(root_folder):
            file_content: str = _read_file(root_folder)
            if ".*" in file_content:
                return [root_folder]

    wildcards: List[str] = []

    # Walk through the root folder and its subdirectories
    for subdir, _, files in os.walk(root_folder):
        for file in files:
            if _is_verilog(file):
                file_path: str = os.path.join(subdir, file)
                file_content = _read_file(file_path)
                if ".*" in file_content:
                    wildcards.append(file_path)

    return wildcards


def find_sv_modules(root_folder: str) -> Dict[str, List[Module]]:
    """Find all modules definitions in Verilog and SystemVerilog files."""

    sv_modules: Dict[str, List[Module]] = {}

    # Regular expression to match SystemVerilog module definitions
    module_regex: re.Pattern[str] = re.compile(
        r"^\s*module\s+(\w+)(?:.|\s)*?endmodule", re.MULTILINE
    )

    # Walk through the root folder and its subdirectories
    for subdir, _, files in os.walk(root_folder):
        for file in files:
            if _is_verilog(file):
                file_path: str = os.path.join(subdir, file)
                file_content: str = _read_file(file_path)
                file_modules: List[Module] = []
                for match in module_regex.finditer(file_content):
                    if match:
                        start, end = match.span()
                        module: str = file_content[start:end]
                        file_modules.append(
                            Module(name=match.group(1), inouts=_parse_inouts(module))
                        )
            sv_modules[file_path] = file_modules

    return sv_modules


def _parse_inouts(module_content: str) -> List[str]:
    """Build a list of input and output signals of a Verilog or SystemVerilog module."""

    inouts: List[str] = []
    for match in re.finditer(
        r"^ *?\b(?:input|output|inout).+?(\w+)(?:\,|\s+?\)\;)",
        module_content,
        re.MULTILINE,
    ):
        name: str = match.group(1)
        inouts.append(name)
    return inouts


def replace_wildcards_with_signals(
    file_content: str, module: Module, order: bool
) -> str:
    """Replace wildcard instantiations with missing signals from called module."""

    cured_file_content: str = file_content

    readjust: int = 0

    for match in re.finditer(
        rf"(?s)^ +\b({module.name})\s*#?\(.*?\)\;", cured_file_content, re.MULTILINE
    ):
        print(f"[INFO]: {module.name} instantiated.")
        init: int = len(cured_file_content)
        start, end = match.span()

        start += readjust
        end += readjust

        instance: str = cured_file_content[start:end]
        if ".*" in instance:
            cured_file_content = (
                cured_file_content[:start]
                + module.instantiate(instance, order)
                + cured_file_content[end:]
            )
            print(f"[INFO]: Removed wildcard instantiation of {module.name}.")
        readjust = len(cured_file_content) - init

    return cured_file_content


def cure_from_wildcards(
    file_path: str, sv_modules: Dict[str, List[Module]], order: bool
) -> None:
    """Remove all wildcard instantiations from a file based on found modules."""

    print(f"[INFO]: Trying to cure {file_path}.")

    file_content: str = _read_file(file_path)

    for path in sv_modules.keys():
        for module in sv_modules[path]:
            file_content = replace_wildcards_with_signals(file_content, module, order)

    # Fix syntax errors if any
    for match in re.finditer(r",\n(\s+)\)\;", file_content, re.MULTILINE):
        _tabs: str = len(match.group(1)) * " "
        file_content = file_content.replace(match.group(0), f"\n{_tabs});")

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
        cure_from_wildcards(file, sv_modules, args.order)

    sys.exit(0)


if __name__ == "__main__":
    main()
