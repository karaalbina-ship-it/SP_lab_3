from dataclasses import dataclass, field


@dataclass
class Node:
    kind: str
    value: object = None
    children: list = field(default_factory=list)
    line: int = 0
    type: str = None
    id: int = 0

    def label(self):
        parts = [self.kind]
        if self.type:
            parts.append(self.type)
        if self.value is not None:
            parts.append(repr(self.value) if isinstance(self.value, str) and self.kind == "Str" else str(self.value))
        return " ".join(parts)


def number(root):
    n = 0
    stack = [root]
    while stack:
        node = stack.pop()
        node.id = n
        n += 1
        stack.extend(reversed(node.children))
    return root


def to_dict(node):
    return {
        "id": node.id,
        "kind": node.kind,
        "label": node.label(),
        "line": node.line,
        "children": [to_dict(c) for c in node.children],
    }


def print_tree(node, prefix="", last=True, top=True, out=None):
    out = [] if out is None else out
    if top:
        out.append(node.label())
    else:
        out.append(prefix + ("└── " if last else "├── ") + node.label())
    child_prefix = prefix if top else prefix + ("    " if last else "│   ")
    for i, c in enumerate(node.children):
        print_tree(c, child_prefix, i == len(node.children) - 1, False, out)
    return "\n".join(out)
