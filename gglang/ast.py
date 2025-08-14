from dataclasses import dataclass
from typing import List, Any, Optional

class Node:
    pass

@dataclass
class Program(Node):
    statements: List[Node]

@dataclass
class VarDecl(Node):
    name: str
    var_type: Optional[str]
    value: Node

@dataclass
class ConstDecl(Node):
    name: str
    value: Node

@dataclass
class Assignment(Node):
    target: Node
    value: Node


@dataclass
class CompoundAssignment(Node):
    target: Node
    op: str
    value: Node

@dataclass
class BinOp(Node):
    left: Node
    op: str
    right: Node

@dataclass
class Pipe(Node):
    left: Node
    op: str
    right: Node

@dataclass
class AssignmentPipe(Node):
    target: str
    value: Node
    var_type: Optional['Type']

@dataclass
class Ternary(Node):
    condition: Node
    then_branch: Node
    else_branch: Node

@dataclass
class InterpolatedString(Node):
    parts: List[Node]


@dataclass
class ArrayLiteral(Node):
    elements: List[Node]

@dataclass
class ArrayAccess(Node):
    array: Node
    index: Node

@dataclass
class ForLoop(Node):
    variable: str
    iterable: Node
    body: 'Block'

@dataclass
class ClassDecl(Node):
    name: str
    superclass: Optional[str]
    body: 'Block'

@dataclass
class PropertyAccess(Node):
    object: Node
    name: str

@dataclass
class MethodCall(Node):
    callee: Node
    args: List[Node]

@dataclass
class InstanceVar(Node):
    name: str

@dataclass
class InstanceVarDecl(Node):
    name: str
    var_type: 'Type'
    value: Node


@dataclass
class InstanceConstDecl(Node):
    name: str
    value: Node

@dataclass
class Super(Node):
    pass

@dataclass
class Block(Node):
    statements: List[Node]

@dataclass
class Param(Node):
    name: str
    param_type: 'Type'
    is_ref: bool


@dataclass
class FuncDecl(Node):
    name: str
    params: List['Param']
    return_type: 'Type'
    body: Node

@dataclass
class Integer(Node):
    value: int

@dataclass
class Float(Node):
    value: float

@dataclass
class String(Node):
    value: str

@dataclass
class Variable(Node):
    name: str

@dataclass
class Call(Node):
    callee: Node
    args: List[Node]

@dataclass
class Return(Node):
    value: Node

@dataclass
class Type(Node):
    name: str

@dataclass
class Modifier(Node):
    pass

@dataclass
class RepetitionModifier(Modifier):
    count: int

@dataclass
class ConditionalModifier(Modifier):
    condition: Node

@dataclass
class ModifiedExpression(Node):
    expression: Node
    modifiers: List[Modifier]

@dataclass
class TypedPipeTarget(Node):
    name: str
    var_type: 'Type'

@dataclass
class CreateReference(Node):
    value: Node

@dataclass
class TryCatch(Node):
    try_block: 'Block'
    exception_var: str
    catch_block: 'Block'

@dataclass
class KeyValuePair(Node):
    key: Node
    value: Node

@dataclass
class Dictionary(Node):
    pairs: List[KeyValuePair]
