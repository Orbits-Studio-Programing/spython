"""A small interpreter for the spython programming language."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class SpythonError(Exception):
    """Base class for language errors."""


class SpythonSyntaxError(SpythonError):
    pass


class SpythonRuntimeError(SpythonError):
    pass


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    line: int
    column: int


_TOKEN_RE = re.compile(
    r"(?P<SPACE>\s+)"
    r"|(?P<COMMENT>//[^\n]*|\#[^\n]*)"
    r"|(?P<STRING>\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')"
    r"|(?P<NUMBER>\d+(?:\.\d+)?)"
    r"|(?P<IDENT>[A-Za-z_][A-Za-z_0-9]*)"
    r"|(?P<OP>==|!=|<=|>=|&&|\|\||[+*/%<>=!()\[\]{};,-])"
)


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0
    line = 1
    column = 1
    while index < len(source):
        match = _TOKEN_RE.match(source, index)
        if match is None:
            raise SpythonSyntaxError(
                f"Unexpected character {source[index]!r} at {line}:{column}"
            )
        text = match.group()
        kind = match.lastgroup
        if kind not in {"SPACE", "COMMENT"}:
            tokens.append(Token(kind or "", text, line, column))
        newlines = text.count("\n")
        if newlines:
            line += newlines
            column = len(text.rsplit("\n", 1)[-1]) + 1
        else:
            column += len(text)
        index = match.end()
    tokens.append(Token("EOF", "", line, column))
    return tokens


@dataclass
class Literal:
    value: object


@dataclass
class Variable:
    name: str


@dataclass
class Assign:
    name: str
    value: object


@dataclass
class IndexAssign:
    receiver: object
    index: object
    value: object


@dataclass
class Unary:
    operator: str
    operand: object


@dataclass
class Binary:
    left: object
    operator: str
    right: object


@dataclass
class Call:
    callee: object
    arguments: list[object]


@dataclass
class ListExpression:
    elements: list[object]


@dataclass
class Index:
    receiver: object
    index: object


@dataclass
class Let:
    name: str
    value: object


@dataclass
class ExpressionStatement:
    expression: object


@dataclass
class Block:
    statements: list[object]


@dataclass
class If:
    condition: object
    then_branch: Block
    else_branch: Block | None


@dataclass
class While:
    condition: object
    body: Block


@dataclass
class FunctionDeclaration:
    name: str
    parameters: list[str]
    body: Block


@dataclass
class Return:
    value: object | None


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0

    def parse(self) -> list[object]:
        statements = []
        while not self.check("EOF"):
            statements.append(self.declaration())
        return statements

    def declaration(self) -> object:
        if self.match_text("fn"):
            return self.function_declaration()
        return self.statement()

    def function_declaration(self) -> FunctionDeclaration:
        name = self.consume_kind("IDENT", "Expected a function name")
        self.consume_text("(", "Expected '(' after function name")
        parameters: list[str] = []
        if not self.check_text(")"):
            while True:
                parameters.append(
                    self.consume_kind("IDENT", "Expected a parameter name").text
                )
                if not self.match_text(","):
                    break
        self.consume_text(")", "Expected ')' after parameters")
        body = self.block()
        return FunctionDeclaration(name.text, parameters, body)

    def statement(self) -> object:
        if self.match_text("let"):
            name = self.consume_kind("IDENT", "Expected a variable name")
            self.consume_text("=", "Expected '=' after variable name")
            value = self.expression()
            self.consume_text(";", "Expected ';' after declaration")
            return Let(name.text, value)
        if self.match_text("if"):
            condition = self.condition()
            then_branch = self.block()
            else_branch = self.block() if self.match_text("else") else None
            return If(condition, then_branch, else_branch)
        if self.match_text("while"):
            condition = self.condition()
            return While(condition, self.block())
        if self.match_text("return"):
            value = None if self.check_text(";") else self.expression()
            self.consume_text(";", "Expected ';' after return value")
            return Return(value)
        if self.check_text("{"):
            return self.block()
        expression = self.expression()
        self.consume_text(";", "Expected ';' after expression")
        return ExpressionStatement(expression)

    def condition(self) -> object:
        if self.match_text("("):
            value = self.expression()
            self.consume_text(")", "Expected ')' after condition")
            return value
        return self.expression()

    def block(self) -> Block:
        self.consume_text("{", "Expected '{'")
        statements = []
        while not self.check_text("}") and not self.check("EOF"):
            statements.append(self.declaration())
        self.consume_text("}", "Expected '}' after block")
        return Block(statements)

    def expression(self) -> object:
        return self.assignment()

    def assignment(self) -> object:
        expression = self.logical_or()
        if self.match_text("="):
            value = self.assignment()
            if isinstance(expression, Variable):
                return Assign(expression.name, value)
            if isinstance(expression, Index):
                return IndexAssign(expression.receiver, expression.index, value)
            self.error(self.previous(), "Invalid assignment target")
        return expression

    def logical_or(self) -> object:
        expression = self.logical_and()
        while self.match_text("||", "or"):
            expression = Binary(expression, "or", self.logical_and())
        return expression

    def logical_and(self) -> object:
        expression = self.equality()
        while self.match_text("&&", "and"):
            expression = Binary(expression, "and", self.equality())
        return expression

    def equality(self) -> object:
        expression = self.comparison()
        while self.match_text("==", "!="):
            operator = self.previous().text
            expression = Binary(expression, operator, self.comparison())
        return expression

    def comparison(self) -> object:
        expression = self.term()
        while self.match_text("<", "<=", ">", ">="):
            operator = self.previous().text
            expression = Binary(expression, operator, self.term())
        return expression

    def term(self) -> object:
        expression = self.factor()
        while self.match_text("+", "-"):
            operator = self.previous().text
            expression = Binary(expression, operator, self.factor())
        return expression

    def factor(self) -> object:
        expression = self.unary()
        while self.match_text("*", "/", "%"):
            operator = self.previous().text
            expression = Binary(expression, operator, self.unary())
        return expression

    def unary(self) -> object:
        if self.match_text("!", "not", "-"):
            return Unary(self.previous().text, self.unary())
        return self.call()

    def call(self) -> object:
        expression = self.primary()
        while True:
            if self.match_text("("):
                arguments = []
                if not self.check_text(")"):
                    while True:
                        arguments.append(self.expression())
                        if not self.match_text(","):
                            break
                self.consume_text(")", "Expected ')' after arguments")
                expression = Call(expression, arguments)
            elif self.match_text("["):
                index = self.expression()
                self.consume_text("]", "Expected ']' after index")
                expression = Index(expression, index)
            else:
                break
        return expression

    def primary(self) -> object:
        if self.match_text("true"):
            return Literal(True)
        if self.match_text("false"):
            return Literal(False)
        if self.match_text("null"):
            return Literal(None)
        if self.match_kind("NUMBER"):
            text = self.previous().text
            return Literal(float(text) if "." in text else int(text))
        if self.match_kind("STRING"):
            return Literal(ast.literal_eval(self.previous().text))
        if self.match_kind("IDENT"):
            return Variable(self.previous().text)
        if self.match_text("["):
            elements = []
            if not self.check_text("]"):
                while True:
                    elements.append(self.expression())
                    if not self.match_text(","):
                        break
            self.consume_text("]", "Expected ']' after list elements")
            return ListExpression(elements)
        if self.match_text("("):
            expression = self.expression()
            self.consume_text(")", "Expected ')' after expression")
            return expression
        self.error(self.peek(), "Expected an expression")

    def match_kind(self, kind: str) -> bool:
        if self.check(kind):
            self.advance()
            return True
        return False

    def match_text(self, *texts: str) -> bool:
        if self.peek().text in texts:
            self.advance()
            return True
        return False

    def check(self, kind: str) -> bool:
        return self.peek().kind == kind

    def check_text(self, text: str) -> bool:
        return self.peek().text == text

    def consume_kind(self, kind: str, message: str) -> Token:
        if self.check(kind):
            return self.advance()
        self.error(self.peek(), message)

    def consume_text(self, text: str, message: str) -> Token:
        if self.check_text(text):
            return self.advance()
        self.error(self.peek(), message)

    def advance(self) -> Token:
        token = self.peek()
        if token.kind != "EOF":
            self.current += 1
        return token

    def peek(self) -> Token:
        return self.tokens[self.current]

    def previous(self) -> Token:
        return self.tokens[self.current - 1]

    @staticmethod
    def error(token: Token, message: str) -> None:
        raise SpythonSyntaxError(f"{message} at {token.line}:{token.column}")


class Environment:
    def __init__(self, parent: Environment | None = None):
        self.parent = parent
        self.values: dict[str, object] = {}

    def define(self, name: str, value: object) -> None:
        self.values[name] = value

    def get(self, name: str) -> object:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise SpythonRuntimeError(f"Undefined variable '{name}'")

    def assign(self, name: str, value: object) -> None:
        if name in self.values:
            self.values[name] = value
        elif self.parent is not None:
            self.parent.assign(name, value)
        else:
            raise SpythonRuntimeError(f"Undefined variable '{name}'")


@dataclass
class SpFunction:
    declaration: FunctionDeclaration
    closure: Environment


@dataclass
class Builtin:
    name: str
    function: Callable[..., object]


class ReturnSignal(Exception):
    def __init__(self, value: object):
        self.value = value


class Interpreter:
    def __init__(self, output: Callable[[str], object] = print):
        self.output = output
        self.globals = Environment()
        self.environment = self.globals
        self.globals.define("print", Builtin("print", self._print))

    def interpret(self, statements: list[object]) -> None:
        try:
            for statement in statements:
                self.execute(statement)
        except ReturnSignal as error:
            raise SpythonRuntimeError("Cannot return from top-level code") from error

    def execute(self, statement: object) -> None:
        if isinstance(statement, Let):
            self.environment.define(statement.name, self.evaluate(statement.value))
        elif isinstance(statement, ExpressionStatement):
            self.evaluate(statement.expression)
        elif isinstance(statement, Block):
            self.execute_block(statement, Environment(self.environment))
        elif isinstance(statement, If):
            if self._truthy(self.evaluate(statement.condition)):
                self.execute(statement.then_branch)
            elif statement.else_branch is not None:
                self.execute(statement.else_branch)
        elif isinstance(statement, While):
            while self._truthy(self.evaluate(statement.condition)):
                self.execute(statement.body)
        elif isinstance(statement, FunctionDeclaration):
            function = SpFunction(statement, self.environment)
            self.environment.define(statement.name, function)
        elif isinstance(statement, Return):
            value = None if statement.value is None else self.evaluate(statement.value)
            raise ReturnSignal(value)
        else:
            raise SpythonRuntimeError("Unknown statement")

    def execute_block(self, block: Block, environment: Environment) -> None:
        previous = self.environment
        self.environment = environment
        try:
            for statement in block.statements:
                self.execute(statement)
        finally:
            self.environment = previous

    def evaluate(self, expression: object) -> object:
        if isinstance(expression, Literal):
            return expression.value
        if isinstance(expression, Variable):
            return self.environment.get(expression.name)
        if isinstance(expression, Assign):
            value = self.evaluate(expression.value)
            self.environment.assign(expression.name, value)
            return value
        if isinstance(expression, IndexAssign):
            receiver = self.evaluate(expression.receiver)
            index = self.evaluate(expression.index)
            value = self.evaluate(expression.value)
            self._set_index(receiver, index, value)
            return value
        if isinstance(expression, ListExpression):
            return [self.evaluate(element) for element in expression.elements]
        if isinstance(expression, Index):
            receiver = self.evaluate(expression.receiver)
            index = self.evaluate(expression.index)
            return self._get_index(receiver, index)
        if isinstance(expression, Unary):
            operand = self.evaluate(expression.operand)
            if expression.operator in {"!", "not"}:
                return not self._truthy(operand)
            if expression.operator == "-":
                return -self._number(operand, "Unary '-' requires a number")
        if isinstance(expression, Binary):
            return self._evaluate_binary(expression)
        if isinstance(expression, Call):
            callee = self.evaluate(expression.callee)
            arguments = [self.evaluate(argument) for argument in expression.arguments]
            return self._call(callee, arguments)
        raise SpythonRuntimeError("Unknown expression")

    def _evaluate_binary(self, expression: Binary) -> object:
        left = self.evaluate(expression.left)
        if expression.operator in {"and", "&&"}:
            return self.evaluate(expression.right) if self._truthy(left) else left
        if expression.operator in {"or", "||"}:
            return left if self._truthy(left) else self.evaluate(expression.right)
        right = self.evaluate(expression.right)
        operator = expression.operator
        try:
            if operator == "+":
                if type(left) is type(right) and isinstance(left, (int, float, str)):
                    return left + right
                raise SpythonRuntimeError("'+' requires two numbers or two strings")
            if operator == "-":
                return self._number(left, "'-' requires numbers") - self._number(
                    right, "'-' requires numbers"
                )
            if operator == "*":
                return self._number(left, "'*' requires numbers") * self._number(
                    right, "'*' requires numbers"
                )
            if operator == "/":
                return self._number(left, "'/' requires numbers") / self._number(
                    right, "'/' requires numbers"
                )
            if operator == "%":
                return self._number(left, "'%' requires numbers") % self._number(
                    right, "'%' requires numbers"
                )
            if operator in {"<", "<=", ">", ">="}:
                if type(left) is not type(right) or not isinstance(
                    left, (int, float, str)
                ):
                    raise SpythonRuntimeError("Comparison requires matching numbers or strings")
                return {"<": left < right, "<=": left <= right, ">": left > right, ">=": left >= right}[operator]
            if operator == "==":
                return left == right
            if operator == "!=":
                return left != right
        except ZeroDivisionError as error:
            raise SpythonRuntimeError("Division by zero") from error
        return None

    def _call(self, callee: object, arguments: list[object]) -> object:
        if isinstance(callee, Builtin):
            return callee.function(*arguments)
        if not isinstance(callee, SpFunction):
            raise SpythonRuntimeError("Can only call functions")
        declaration = callee.declaration
        if len(arguments) != len(declaration.parameters):
            raise SpythonRuntimeError(
                f"'{declaration.name}' expects {len(declaration.parameters)} arguments, "
                f"got {len(arguments)}"
            )
        environment = Environment(callee.closure)
        for name, value in zip(declaration.parameters, arguments):
            environment.define(name, value)
        try:
            self.execute_block(declaration.body, environment)
        except ReturnSignal as result:
            return result.value
        return None

    @staticmethod
    def _validate_index(index: object) -> int:
        if isinstance(index, bool) or not isinstance(index, int):
            raise SpythonRuntimeError("Index must be an integer")
        return index

    def _get_index(self, receiver: object, index: object) -> object:
        if not isinstance(receiver, (list, str)):
            raise SpythonRuntimeError("Indexing requires a list or string")
        index = self._validate_index(index)
        try:
            return receiver[index]
        except IndexError as error:
            raise SpythonRuntimeError("Index out of range") from error

    def _set_index(self, receiver: object, index: object, value: object) -> None:
        if not isinstance(receiver, list):
            raise SpythonRuntimeError("Indexed assignment requires a list")
        index = self._validate_index(index)
        try:
            receiver[index] = value
        except IndexError as error:
            raise SpythonRuntimeError("Index out of range") from error

    def _print(self, *values: object) -> None:
        self.output(" ".join(self._stringify(value) for value in values))

    @staticmethod
    def _number(value: object, message: str) -> int | float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SpythonRuntimeError(message)
        return value

    @staticmethod
    def _truthy(value: object) -> bool:
        return value is not None and value is not False

    @staticmethod
    def _stringify(value: object) -> str:
        if value is None:
            return "null"
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        if isinstance(value, list):
            return "[" + ", ".join(Interpreter._stringify(item) for item in value) + "]"
        return str(value)


def run(source: str, output: Callable[[str], object] = print) -> None:
    statements = Parser(tokenize(source)).parse()
    Interpreter(output).interpret(statements)


def main() -> int:
    argument_parser = argparse.ArgumentParser(description="Run a spython source file")
    argument_parser.add_argument("file", type=Path, help="path to a .spy source file")
    arguments = argument_parser.parse_args()
    try:
        run(arguments.file.read_text(encoding="utf-8"))
    except (OSError, SpythonError) as error:
        print(f"spython: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())