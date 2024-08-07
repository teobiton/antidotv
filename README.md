![I really hate .*](./docs/_static/antidote.png)

This is an antidote against wildcard instantiations for your Verilog and SystemVerilog files.
Yes, it's completely an overkill, but it works.

```bash
# Install
pip install .

# Usage
# <root_dir> is where to search for modules instantiated in <vlg_file>
antidotv <vlg_filev> <root_dir>

# Also works with a path to a directory to fix several files at once
antidotv <project_dir> <root_dir>

# Use --order to fix wildcards and order I/Os
antidotv <project_dir> <root_dir> --order
```