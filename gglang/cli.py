import sys
import argparse
from gglang.parser import parse
from gglang.interpreter import Interpreter

def main():
    parser = argparse.ArgumentParser(description="GGLang Interpreter")
    parser.add_argument("filename", help="The GGLang script to execute.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode for the interpreter.")
    args = parser.parse_args()

    filename = args.filename
    try:
        with open(filename, 'r') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {filename}")
        sys.exit(1)

    try:
        ast = parse(code)
        interpreter = Interpreter(debug=args.debug)
        interpreter.interpret(ast)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
