from os import path

from setuptools import find_packages, setup


def read_file(fname: str) -> str:
    with open(path.join(path.dirname(__file__), fname), encoding="utf8") as f:
        return f.read()


setup(
    name="antidotv",
    version="1.0.0",
    description="An antidote to remove wildcard I/O instantiation from Verilog and SystemVerilog files.",
    url="https://github.com/teobiton/antidotv",
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    author="Téo Biton",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        "console_scripts": [
            "antidotv=antidotv.main:main",
        ]
    },
    platforms="any",
)
