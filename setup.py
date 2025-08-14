from setuptools import setup, find_packages

setup(
    name="gglang",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'gglang': ['grammar.lark'],
    },
    install_requires=[
        "lark-parser",
    ],
    entry_points={
        "console_scripts": [
            "gglang = gglang.cli:main",
        ],
    },
    author="Jules",
    author_email="jules@example.com",
    description="An interpreter for the gglang programming language.",
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url="https://github.com/example/gglang",
)
