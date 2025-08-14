from .ast import *

_UNINITIALIZED = object()

class Environment:
    def __init__(self, enclosing=None):
        self.values = {}
        self.enclosing = enclosing

    def define(self, name, value):
        # In GGLang, we can redeclare variables.
        self.values[name] = value

    def get(self, name):
        if name in self.values:
            value = self.values[name]
            if value is _UNINITIALIZED:
                raise NameError(f"Variable '{name}' was declared but not assigned a value.")
            return value
        if self.enclosing is not None:
            return self.enclosing.get(name)
        raise NameError(f"Variable '{name}' is not defined.")

    def assign(self, name, value):
        if name in self.values:
            self.values[name] = value
            return
        if self.enclosing is not None:
            self.enclosing.assign(name, value)
            return
        raise NameError(f"Cannot assign to undefined variable '{name}'.")

class ReturnValue(Exception):
    def __init__(self, value):
        self.value = value


class GGLangSuper:
    def __init__(self, instance, superclass):
        self.instance = instance
        self.superclass = superclass

    def get(self, name):
        method = self.superclass.find_method(name)
        if method:
            return method.bind(self.instance)
        raise NameError(f"Undefined method '{name}' on super.")

class GGLangClass:
    def __init__(self, name, superclass, methods):
        self.name = name
        self.superclass = superclass
        self.methods = methods

    def find_method(self, name):
        if name in self.methods:
            return self.methods[name]
        if self.superclass:
            return self.superclass.find_method(name)
        return None

    def __call__(self, interpreter, args):
        instance = GGLangInstance(self)
        initializer = self.find_method("initialize")
        if initializer:
            initializer.bind(instance)(interpreter, args)
        return instance

class GGLangInstance:
    def __init__(self, klass):
        self.klass = klass
        self.fields = {}

    def get(self, name):
        if name in self.fields:
            return self.fields[name]

        method = self.klass.find_method(name)
        if method:
            return method.bind(self)

        raise NameError(f"Undefined property '{name}'.")

    def set(self, name, value):
        self.fields[name] = value

class GGLangFunction:
    def __init__(self, declaration: FuncDecl, closure: Environment):
        self.declaration = declaration
        self.closure = closure

    def bind(self, instance):
        env = Environment(enclosing=self.closure)
        env.define("this", instance)
        if instance.klass.superclass:
            env.define("super", GGLangSuper(instance, instance.klass.superclass))
        return GGLangFunction(self.declaration, env)

    def __call__(self, interpreter, args):
        # Create a new environment for the function call
        env = Environment(enclosing=self.closure)

        # Check argument count
        if len(args) != len(self.declaration.params):
            raise TypeError(f"Function '{self.declaration.name}' expected {len(self.declaration.params)} arguments, but got {len(args)}.")

        type_map = {
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
        }

        # Bind arguments to parameters with type checking
        for i, param in enumerate(self.declaration.params):
            arg_val = args[i]
            param_type_name = param.param_type.name

            if param_type_name in type_map:
                expected_py_type = type_map[param_type_name]
                if not isinstance(arg_val, expected_py_type):
                    raise TypeError(f"Argument '{param.name}' for function '{self.declaration.name}' must be of type '{param_type_name}', but got type '{type(arg_val).__name__}'.")

            env.define(param.name, arg_val)

        # Execute the function body
        try:
            interpreter.execute_block(self.declaration.body, env)
        except ReturnValue as ret:
            return ret.value

        return None # Implicit return None

class Interpreter:
    def __init__(self, debug=False):
        self.debug = debug
        self.environment = Environment()
        # Add built-in functions here
        self.environment.define("print", print)
        self.environment.define("int", int)
        self.environment.define("str", str)
        self.environment.define("float", float)
        self.environment.define("true", True)
        self.environment.define("false", False)
        self.environment.define("len", len)
        self.environment.define("assert", self._gglang_assert)
        self.environment.define("append", self._gglang_append)
        self.environment.define("pop", self._gglang_pop)
        self.environment.define("type", self._gglang_type)
        self.environment.define("input", self._gglang_input)
        self.environment.define("remove", self._gglang_remove)

    def _gglang_append(self, l, x):
        if not isinstance(l, list):
            raise TypeError("append() takes a list as the first argument.")
        l.append(x)

    def _gglang_pop(self, l, index=-1):
        if not isinstance(l, list):
            raise TypeError("pop() takes a list as the first argument.")
        if not isinstance(index, int):
            raise TypeError("pop() index must be an integer.")
        return l.pop(index)

    def _gglang_type(self, x):
        return type(x).__name__

    def _gglang_input(self, prompt=""):
        return input(prompt)

    def _gglang_remove(self, l, value):
        if not isinstance(l, list):
            raise TypeError("remove() takes a list as the first argument.")
        try:
            l.remove(value)
        except ValueError:
            raise ValueError(f"value '{value}' not found in list.")

    def _gglang_assert(self, condition, message=None):
        if not condition:
            raise AssertionError(message or "Assertion failed.")

    def interpret(self, program: Program):
        # First, execute all top-level statements to define functions and global variables
        for statement in program.statements:
            self.execute(statement)

        # After all declarations and statements are processed, find and run main
        try:
            main_function = self.environment.get("main")
            if isinstance(main_function, GGLangFunction):
                 main_function(self, [])
        except NameError:
            # No main function found, which is fine for a script.
            pass

    def _debug_print(self, message):
        if self.debug:
            print(f"[DEBUG] {message}")

    def execute(self, node: Node):
        self._debug_print(f"Executing node: {type(node).__name__}")
        if node is None:
            # This can happen for statements that don't return a value, like a call to a void function.
            return None
        method_name = f'visit_{type(node).__name__.lower()}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: Node):
        raise NotImplementedError(f"No visit_{type(node).__name__.lower()} method")

    def visit_vardecl(self, node: VarDecl):
        if node.value is None:
            self.environment.define(node.name, _UNINITIALIZED)
        else:
            value = self.execute(node.value)
            if node.var_type:
                type_name = node.var_type
                type_map = { "int": int, "float": float, "str": str, "bool": bool }
                if type_name in type_map:
                    if not isinstance(value, type_map[type_name]):
                        raise TypeError(f"Cannot assign value of type {type(value).__name__} to variable '{node.name}' of type '{type_name}'")
            self.environment.define(node.name, value)

    def visit_constdecl(self, node: ConstDecl):
        # For now, constants are the same as variables.
        # We can add immutability checks later.
        value = self.execute(node.value)
        self.environment.define(node.name, value)

    def visit_compoundassignment(self, node: CompoundAssignment):
        rhs_value = self.execute(node.value)
        target = node.target

        # Get current value
        if isinstance(target, Variable):
            current_value = self.environment.get(target.name)
        elif isinstance(target, InstanceVar):
            instance = self.environment.get("this")
            current_value = instance.get(target.name)
        elif isinstance(target, PropertyAccess):
            obj = self.execute(target.object)
            if isinstance(obj, GGLangInstance):
                current_value = obj.get(target.name)
            else:
                raise TypeError("Can only use compound assignment on properties of instances.")
        elif isinstance(target, ArrayAccess):
            obj = self.execute(target.array)
            key = self.execute(target.index)
            # This works for lists and dicts
            current_value = obj[key]
        else:
            raise TypeError(f"Invalid compound assignment target: {type(target)}")

        # Perform operation
        op = node.op.removesuffix("=")
        if op == '+':
            new_value = current_value + rhs_value
        elif op == '-':
            new_value = current_value - rhs_value
        elif op == '*':
            new_value = current_value * rhs_value
        elif op == '/':
            if isinstance(current_value, int) and isinstance(rhs_value, int):
                new_value = current_value // rhs_value
            else:
                new_value = current_value / rhs_value
        else:
            raise RuntimeError(f"Unknown compound assignment operator: {node.op}")

        # Assign back
        if isinstance(target, Variable):
            self.environment.assign(target.name, new_value)
        elif isinstance(target, InstanceVar):
            instance = self.environment.get("this")
            instance.set(target.name, new_value)
        elif isinstance(target, PropertyAccess):
            obj = self.execute(target.object)
            obj.set(target.name, new_value)
        elif isinstance(target, ArrayAccess):
            obj = self.execute(target.array)
            key = self.execute(target.index)
            obj[key] = new_value
        else:
            # This case should be caught by the initial check
            raise TypeError(f"Invalid compound assignment target: {type(target)}")

    def visit_assignment(self, node: Assignment):
        value = self.execute(node.value)
        target = node.target

        if isinstance(target, Variable):
            self.environment.assign(target.name, value)
        elif isinstance(target, InstanceVar):
            instance = self.environment.get("this")
            instance.set(target.name, value)
        elif isinstance(target, PropertyAccess):
            obj = self.execute(target.object)
            if isinstance(obj, GGLangInstance):
                obj.set(target.name, value)
            else:
                raise TypeError("Can only assign to properties of instances.")
        elif isinstance(target, ArrayAccess):
            obj = self.execute(target.array)
            key = self.execute(target.index)
            if isinstance(obj, list):
                if not isinstance(key, int):
                    raise TypeError("List index must be an integer.")
                obj[key] = value
            elif isinstance(obj, dict):
                obj[key] = value
            else:
                raise TypeError(f"Object of type {type(obj).__name__} does not support subscript assignment.")
        else:
            raise TypeError(f"Invalid assignment target: {type(target)}")

    def visit_variable(self, node: Variable):
        return self.environment.get(node.name)

    def visit_integer(self, node: Integer):
        return node.value

    def visit_float(self, node: Float):
        return node.value

    def visit_string(self, node: String):
        return node.value

    def visit_binop(self, node: BinOp):
        left = self.execute(node.left)
        right = self.execute(node.right)

        if node.op == '+':
            return left + right
        elif node.op == '-':
            return left - right
        elif node.op == '*':
            return left * right
        elif node.op == '/':
            if isinstance(left, int) and isinstance(right, int):
                return left // right
            return left / right
        # Comparison operators
        elif node.op == '>':
            return left > right
        elif node.op == '<':
            return left < right
        elif node.op == '>=':
            return left >= right
        elif node.op == '<=':
            return left <= right
        elif node.op == '==':
            return left == right
        elif node.op == '!=':
            return left != right
        else:
            raise RuntimeError(f"Unknown operator: {node.op}")

    def visit_assignmentpipe(self, node: AssignmentPipe):
        value = self.execute(node.value)
        self.environment.define(node.target, value)

    def visit_pipe(self, node: Pipe):
        left_val = self.execute(node.left)

        if node.op == "~~>":
            # --- Coercion Pipe Logic ---
            call_node = node.right
            if not isinstance(call_node, Call):
                raise TypeError("Coercion pipe '~~>' must be followed by a function call.")

            # Find the position of the placeholder '_'
            placeholder_index = -1
            for i, arg in enumerate(call_node.args):
                if isinstance(arg, Variable) and arg.name == '_':
                    placeholder_index = i
                    break

            if placeholder_index == -1:
                # No placeholder found, so no coercion needed. Act like a normal pipe.
                return self.execute_pipe_step(node.right, left_val)

            # Get the function object
            callee = self.execute(call_node.callee)
            if not isinstance(callee, GGLangFunction):
                # For now, coercion only works for user-defined GGLang functions
                raise TypeError("Coercion pipe '~~>' is currently only supported for user-defined functions.")

            # Get the expected parameter type
            if placeholder_index >= len(callee.declaration.params):
                raise TypeError(f"Too many arguments for function '{callee.declaration.name}'.")

            param = callee.declaration.params[placeholder_index]
            type_name = param.param_type.name

            # Get the coercion function (e.g., int, string)
            try:
                coercion_func = self.environment.get(type_name)
            except NameError:
                raise TypeError(f"Unknown type '{type_name}' for coercion.")

            # Coerce the value
            try:
                coerced_val = coercion_func(left_val)
            except (ValueError, TypeError):
                raise TypeError(f"Could not coerce value '{left_val}' to type '{type_name}'.")

            return self.execute_pipe_step(node.right, coerced_val)

        else: # Standard pipe "-->"
            return self.execute_pipe_step(node.right, left_val)

    def visit_repetitionmodifier(self, node: RepetitionModifier):
        # This node should not be visited directly.
        return node.count

    def visit_conditionalmodifier(self, node: ConditionalModifier):
        # This node should not be visited directly.
        return self.execute(node.condition)

    def visit_modifiedexpression(self, node: ModifiedExpression):
        # This is not expected to be called directly, as it should be handled by `visit_pipe`.
        # However, for completeness, we can execute it with a `None` input.
        return self.execute_modified_step(node, None)

    def execute_pipe_step(self, step_node, input_value):
        if isinstance(step_node, ModifiedExpression):
            return self.execute_modified_step(step_node, input_value)
        elif isinstance(step_node, TypedPipeTarget):
            # This is a pipe with a typed assignment target.
            # The pipe's value is assigned to the new variable.
            self.environment.define(step_node.name, input_value)
            # We can optionally do type checking here against step_node.var_type
            return input_value
        else:
            # Standard step execution (no modifiers)
            return self.execute_simple_step(step_node, input_value)

    def execute_simple_step(self, expression_node, input_value):
        pipe_env = Environment(enclosing=self.environment)
        pipe_env.define('_', input_value)

        original_env = self.environment
        self.environment = pipe_env
        try:
            result = self.execute(expression_node)
        finally:
            self.environment = original_env
        return result

    def execute_modified_step(self, modified_expr_node, input_value):
        current_value = input_value

        # Check all conditional modifiers first
        for modifier in modified_expr_node.modifiers:
            if isinstance(modifier, ConditionalModifier):
                # Evaluate the condition with the current input value for this step
                should_run = self.execute_simple_step(modifier.condition, current_value)
                if not should_run:
                    return current_value  # Skip step, pass value through

        # If conditions passed, find the repetition modifier (if any)
        repetition_count = 1
        for modifier in modified_expr_node.modifiers:
            if isinstance(modifier, RepetitionModifier):
                repetition_count = modifier.count
                break  # Assume only one repetition modifier

        # Execute the expression N times
        for _ in range(repetition_count):
            current_value = self.execute_simple_step(modified_expr_node.expression, current_value)

        return current_value

    def visit_ternary(self, node: Ternary):
        condition_val = self.execute(node.condition)
        if condition_val:
            return self.execute(node.then_branch)
        else:
            return self.execute(node.else_branch)

    def visit_interpolatedstring(self, node: InterpolatedString):
        result = []
        for part in node.parts:
            value = self.execute(part)
            result.append(str(value))
        return "".join(result)

    def execute_block(self, block_node, environment):
        original_env = self.environment
        self.environment = environment
        try:
            self.visit_block(block_node)
        finally:
            self.environment = original_env

    def visit_block(self, node: Block):
        for statement in node.statements:
            self.execute(statement)

    def visit_funcdecl(self, node: FuncDecl):
        function = GGLangFunction(node, self.environment)
        self.environment.define(node.name, function)

    def visit_return(self, node: Return):
        value = self.execute(node.value)
        raise ReturnValue(value)

    def visit_call(self, node: Call):
        callee = self.execute(node.callee) # Callee can be a complex expression

        args = [self.execute(arg) for arg in node.args]

        if isinstance(callee, GGLangFunction):
            return callee(self, args)
        elif isinstance(callee, GGLangClass):
            return callee(self, args)
        elif callable(callee):
            return callee(*args)
        else:
            raise TypeError(f"Object is not callable.")

    def visit_arrayliteral(self, node: ArrayLiteral):
        return [self.execute(elem) for elem in node.elements]

    def visit_dictionary(self, node: Dictionary):
        d = {}
        for pair in node.pairs:
            key = self.execute(pair.key)
            value = self.execute(pair.value)
            d[key] = value
        return d

    def visit_keyvaluepair(self, node: KeyValuePair):
        # This should not be called directly.
        pass

    def visit_arrayaccess(self, node: ArrayAccess):
        obj = self.execute(node.array)
        key = self.execute(node.index)

        if isinstance(obj, list):
            if not isinstance(key, int):
                raise TypeError("List index must be an integer.")
            return obj[key]
        elif isinstance(obj, dict):
            return obj[key]
        else:
            raise TypeError(f"Object of type {type(obj).__name__} does not support subscripting.")

    def visit_forloop(self, node: ForLoop):
        iterable = self.execute(node.iterable)
        # Iterate over a copy to prevent mutation issues
        for item in list(iterable):
            loop_env = Environment(enclosing=self.environment)
            loop_env.define(node.variable, item)
            self.execute_block(node.body, loop_env)

    def visit_createreference(self, node: CreateReference):
        # For now, we don't have a concept of references.
        # We just execute the value. This is incorrect but will
        # allow the parser to work.
        return self.execute(node.value)

    def visit_trycatch(self, node: TryCatch):
        try:
            self.execute(node.try_block)
        except Exception as e:
            catch_env = Environment(enclosing=self.environment)
            # We can make the exception object more structured later
            catch_env.define(node.exception_var, str(e))
            self.execute_block(node.catch_block, catch_env)

    def visit_classdecl(self, node: ClassDecl):
        superclass = None
        if node.superclass:
            superclass = self.environment.get(node.superclass)
            if not isinstance(superclass, GGLangClass):
                raise TypeError(f"Superclass must be a class. Got {type(superclass)}.")

        methods = {}
        for stmt in node.body.statements:
            if isinstance(stmt, FuncDecl):
                # The closure for a method should be the class's environment
                # so it can access other methods for 'super' calls.
                # But for now, the current env should be fine as functions are hoisted.
                methods[stmt.name] = GGLangFunction(stmt, self.environment)

        klass = GGLangClass(node.name, superclass, methods)
        self.environment.define(node.name, klass)

    def visit_super(self, node: Super):
        return self.environment.get("super")

    def visit_propertyaccess(self, node: PropertyAccess):
        obj = self.execute(node.object)
        if isinstance(obj, GGLangInstance):
            return obj.get(node.name)

        if isinstance(obj, GGLangSuper):
            return obj.get(node.name)

        if isinstance(obj, str):
            if node.name == "upper":
                return obj.upper
            if node.name == "lower":
                return obj.lower

        raise TypeError(f"Object of type {type(obj).__name__} has no property '{node.name}'.")

    def visit_instancevar(self, node: InstanceVar):
        instance = self.environment.get("this")
        return instance.get(node.name)

    def visit_instancevardecl(self, node: InstanceVarDecl):
        instance = self.environment.get("this")
        if not isinstance(instance, GGLangInstance):
            raise TypeError("Instance variable declaration must be inside a method.")

        if node.value is None:
            value = _UNINITIALIZED
        else:
            value = self.execute(node.value)

        if node.var_type:
            type_name = node.var_type
            type_map = { "int": int, "float": float, "str": str, "bool": bool }
            if type_name in type_map:
                if value is not _UNINITIALIZED and not isinstance(value, type_map[type_name]):
                    raise TypeError(f"Cannot assign value of type {type(value).__name__} to instance variable '@{node.name}' of type '{type_name}'")

        instance.set(node.name, value)

    def visit_instanceconstdecl(self, node: InstanceConstDecl):
        instance = self.environment.get("this")
        if not isinstance(instance, GGLangInstance):
            raise TypeError("Instance constant declaration must be inside a method.")

        value = self.execute(node.value)
        # As with global consts, we don't enforce immutability yet.
        instance.set(node.name, value)

    def visit_methodcall(self, node: MethodCall):
        # The callee is a property access, e.g., obj.method
        # We need to get the function first.
        func = self.visit_propertyaccess(node.callee)

        # Then we call it.
        if callable(func):
             args = [self.execute(arg) for arg in node.args]
             # For GGLangFunctions, we need to pass the interpreter.
             # The 'func' for a GGLang method is already bound to an instance.
             if isinstance(func, GGLangFunction):
                 return func(self, args)
             else: # built-in python method
                 return func(*args)

        raise TypeError(f"'{node.callee.name}' is not a function or method.")

    def visit_program(self, node: Program):
        for stmt in node.statements:
            self.execute(stmt)
