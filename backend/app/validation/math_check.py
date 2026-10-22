"""Deliberately bounded exact arithmetic, without evaluating Python code."""

import ast
import re
from fractions import Fraction


class Unsupported(ValueError):
    pass


def arithmetic(expression: str) -> Fraction:
    expression = expression.strip()
    if not expression or len(expression) > 128 or not re.fullmatch(r"[0-9 .()+*/\-]+", expression):
        raise Unsupported("Use only bounded numeric arithmetic.")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError, RecursionError) as error:
        raise Unsupported("Expression is outside the arithmetic grammar.") from error
    if sum(1 for _ in ast.walk(tree)) > 40:
        raise Unsupported("Expression is too complex.")

    def visit(node, depth=0):
        if depth > 12:
            raise Unsupported("Expression nesting exceeds the limit.")
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            literal = ast.get_source_segment(expression, node)
            if len(literal) > 24 or not re.fullmatch(r"(?:\d+(?:\.\d*)?|\.\d+)", literal):
                raise Unsupported("Unsupported numeric literal.")
            value = Fraction(literal)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand, depth + 1) * (-1 if isinstance(node.op, ast.USub) else 1)
        elif isinstance(node, ast.BinOp):
            left, right = visit(node.left, depth + 1), visit(node.right, depth + 1)
            if isinstance(node.op, ast.Add):
                value = left + right
            elif isinstance(node.op, ast.Sub):
                value = left - right
            elif isinstance(node.op, ast.Mult):
                value = left * right
            elif isinstance(node.op, ast.Div):
                value = left / right
            elif isinstance(node.op, ast.Pow):
                if right.denominator != 1 or abs(right) > 8:
                    raise Unsupported("Exponent must be an integer between -8 and 8.")
                if left == 0 and right == 0:
                    raise ZeroDivisionError("Indeterminate zero power")
                value = left ** int(right)
            else:
                raise Unsupported("Unsupported operator.")
        else:
            raise Unsupported("Only numbers and arithmetic operators are supported.")
        if max(value.numerator.bit_length(), value.denominator.bit_length()) > 128:
            raise Unsupported("Exact arithmetic size exceeds the limit.")
        return value

    return visit(tree.body)


def check_math(stem, options, correct_option, question_type="numerical"):
    result = {"status": "unsupported", "computed": None, "matching_options": [], "detail": ""}
    if question_type not in ("conceptual", "numerical"):
        result["detail"] = (
            "This question type requires a dedicated validator. No mathematical pass was granted."
        )
        return result
    match = re.fullmatch(r"\s*(?:Calculate|Evaluate)\s*:\s*(.+?)\s*", stem, re.I)
    if not match:
        # Conservative triage only, never a proof that prose contains no maths.
        flagged = re.search(
            r"\d|[=+*/%]|\b(calculate|compute|evaluate|solve|sum|product|percent|average|equation|subtract|multiply|divide)\b",
            stem,
            re.I,
        )
        if question_type == "conceptual" and not flagged:
            result.update(
                status="not_applicable",
                detail="No explicit arithmetic pattern detected in this conceptual stem; teacher review is still required.",
            )
        else:
            result["detail"] = (
                "Unsupported mathematics or question type. Use Calculate: or Evaluate: followed by a numeric expression; no units, variables or word problems."
            )
        return result
    try:
        value = arithmetic(match[1])
        values = [arithmetic(option) for option in options]
        matches = [i for i, option in enumerate(values) if option == value]
        result.update(computed=str(value), matching_options=matches)
        if len(values) != 4 or len(set(values)) != 4:
            result.update(
                status="fail",
                detail="Four numerically distinct options are required; equivalent values are duplicates.",
            )
        elif matches != [correct_option]:
            result.update(
                status="fail",
                detail="Exactly one option must equal the independent calculation, and it must match the proposed key.",
            )
        else:
            result.update(
                status="pass",
                detail="Exact rational calculation matches one distinct option and the proposed key. No rounding tolerance was applied.",
            )
    except ZeroDivisionError:
        result.update(
            status="fail",
            detail="Undefined arithmetic, including division by zero, cannot be released.",
        )
    except (Unsupported, ValueError, OverflowError, RecursionError):
        result["detail"] = (
            "Expression or options are unsupported or exceed the bounded arithmetic limits. No mathematical pass was granted."
        )
    return result
