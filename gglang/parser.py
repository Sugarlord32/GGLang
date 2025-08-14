import os
from lark import Lark, Transformer, v_args, Token
from .ast import *

# Read the grammar file
grammar_path = os.path.join(os.path.dirname(__file__), 'grammar.lark')
with open(grammar_path, 'r') as f:
    gglang_grammar = f.read()

@v_args(inline=True)
class AstTransformer(Transformer):
    def start(self, *statements):
        return Program(statements=list(statements))

    def declaration(self, d):
        return d

    def var_typed_assign(self, name, var_type, value=None):
        return VarDecl(name=name.name, var_type=var_type.name, value=value)

    def var_infer_assign(self, name, value):
        return VarDecl(name=name.name, var_type=None, value=value)

    def const_assign(self, name, value):
        return ConstDecl(name=name.name, value=value)

    def lvalue(self, l):
        return l

    def assignment(self, target, value):
        return Assignment(target=target, value=value)

    def ternary(self, *items):
        if len(items) == 1:
            return items[0]
        cond, q_mark, then_branch, else_branch = items
        return Ternary(condition=cond, then_branch=then_branch, else_branch=else_branch)

    def pipe(self, *items):
        if len(items) == 1:
            return items[0]
        left, op, right = items
        return Pipe(left=left, op=op, right=right)

    def modified_expression(self, *children):
        expression = children[0]
        modifiers = list(children[1:])
        return ModifiedExpression(expression=expression, modifiers=modifiers)

    def modifier(self, m):
        return m

    def repetition_modifier(self, count):
        # count is an Integer node from the INT rule
        return RepetitionModifier(count=count.value)

    def conditional_modifier(self, condition):
        return ConditionalModifier(condition=condition)

    def typed_pipe_target(self, name, var_type):
        return TypedPipeTarget(name=name.name, var_type=var_type)

    def assignment_pipe(self, *args):
        # value, op, target, [type]
        if len(args) == 4:
            value, op, target, var_type = args
        else:
            value, op, target = args
            var_type = None
        return AssignmentPipe(target=target.name, value=value, var_type=var_type)

    def add_expr(self, *items):
        if len(items) == 1:
            return items[0]
        left, op, right = items
        return BinOp(left=left, op=op, right=right)

    def mul_expr(self, *items):
        if len(items) == 1:
            return items[0]
        left, op, right = items
        return BinOp(left=left, op=op, right=right)

    def comparison(self, *items):
        if len(items) == 1:
            return items[0]
        left, op, right = items
        return BinOp(left=left, op=op, right=right)

    def factor(self, value):
        return value

    def PIPE_OP(self, op):
        return op.value

    def ADD_OP(self, op):
        return op.value

    def MUL_OP(self, op):
        return op.value

    def COMP_OP(self, op):
        return op.value

    def ASSIGN_PIPE_OP(self, op):
        return op.value

    def Q_MARK(self, op):
        return op.value

    def fn_declaration(self, *args):
        if len(args) == 4:
            name, params, return_type, body = args
        else:
            name, return_type, body = args
            params = []
        return FuncDecl(name=name.name, params=params or [], return_type=return_type, body=body)

    def block(self, *statements):
        return Block(statements=list(statements))

    def params(self, *items):
        return list(items)

    def create_reference(self, value):
        return CreateReference(value=value)

    def param(self, *args):
        if len(args) == 3:
            name, _ref, param_type = args
            is_ref = True
        else:
            name, param_type = args
            is_ref = False
        return Param(name=name.name, param_type=param_type, is_ref=is_ref)

    def array_literal(self, *elements):
        return ArrayLiteral(elements=list(elements))

    def dictionary(self, *pairs):
        return Dictionary(pairs=list(pairs))

    def key_value_pair(self, key, value):
        return KeyValuePair(key=key, value=value)

    def array_access(self, array, index):
        return ArrayAccess(array=array, index=index)

    def for_loop(self, var_name, iterable, body):
        return ForLoop(variable=var_name.value, iterable=iterable, body=body)

    def try_catch(self, try_block, exception_var, catch_block):
        return TryCatch(try_block=try_block, exception_var=exception_var.name, catch_block=catch_block)

    def class_declaration(self, *args):
        # args are the children of the rule: CLASS, NAME, [superclass_name], block
        if len(args) == 4:
            _class, name, superclass_name, body = args
            superclass = superclass_name.name
        else:
            _class, name, body = args
            superclass = None
        return ClassDecl(name=name.name, superclass=superclass, body=body)

    def instance_var_decl(self, name, var_type, value=None):
        return InstanceVarDecl(name=name.name, var_type=var_type, value=value)

    def SUPER(self, _):
        return Super()

    def property_access(self, obj, name):
        return PropertyAccess(object=obj, name=name.name)

    def instance_var(self, name):
        return InstanceVar(name=name.name)

    def instance_var_declaration(self, var, value):
        return InstanceVarDecl(name=var.name, var_type=None, value=value)

    def property_access(self, obj, name):
        prop_name = name.value if isinstance(name, Token) else name.name
        return PropertyAccess(object=obj, name=prop_name)

    def instance_var(self, name):
        return InstanceVar(name=name.name)

    def instance_var_declaration(self, var, value):
        return InstanceVarDecl(name=var.name, var_type=None, value=value)

    def INTERPOLATED_STRING(self, token):
        content = token.value[2:-1] # Strip i" and "
        parts = []
        last_end = 0

        import re
        for match in re.finditer(r"#\{(.+?)\}", content):
            start, end = match.span()
            expr_str = match.group(1)

            if start > last_end:
                parts.append(String(value=content[last_end:start]))

            try:
                expr_tree = gglang_parser.parse(expr_str, start='expression')
                expr_ast = ast_builder.transform(expr_tree)
                parts.append(expr_ast)
            except Exception as e:
                # This is not ideal, but it's a fallback for robust parsing
                parts.append(String(value=f" FAILED_TO_PARSE: {expr_str} "))

            last_end = end

        if last_end < len(content):
            parts.append(String(value=content[last_end:]))

        return InterpolatedString(parts=parts)

    def call(self, c):
        return c

    def call_with_args(self, callee, args):
        if isinstance(callee, PropertyAccess):
            return MethodCall(callee=callee, args=args)
        return Call(callee=callee, args=args)

    def call_no_args(self, callee):
        if isinstance(callee, PropertyAccess):
            return MethodCall(callee=callee, args=[])
        return Call(callee=callee, args=[])

    def arguments(self, *items):
        return list(items)

    def return_statement(self, _return_keyword, value):
        return Return(value=value)

    def RETURN(self, _):
        # We don't need the token value, just its presence
        return None

    def TYPE(self, t):
        return Type(name=t.value)

    def NAME(self, n):
        return Variable(name=n.value)

    def ESCAPED_STRING(self, s):
        return String(value=s[1:-1])

    def INT(self, n):
        return Integer(value=int(n))

    def FLOAT(self, n):
        return Float(value=float(n))


# Create the parser
gglang_parser = Lark(gglang_grammar, start=['start', 'expression'], parser='lalr')
ast_builder = AstTransformer()

def parse(code, start='start'):
    """Parses GGLang code and returns an AST."""
    tree = gglang_parser.parse(code, start=start)
    return ast_builder.transform(tree)

# This file is a library, not meant to be run directly.
