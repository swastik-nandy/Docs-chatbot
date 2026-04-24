# rag/ingestion/parser/enrichment/component_context.py

from copy import deepcopy
from typing import Any, Dict, List, Optional


ComponentFrame = Dict[str, Any]
ComponentStack = List[ComponentFrame]


# --------------------------------------STACK FORMATTING-------------------------------------------

def copy_stack(stack: ComponentStack) -> ComponentStack:
    """
    Return a safe copy of the active component stack.
    """

    return deepcopy(stack or [])


def format_props(props: Optional[Dict[str, Any]]) -> str:
    """
    Convert component props into stable text.

    Example:
        {"label": "v1.42", "description": "2026-04-13"}

    Becomes:
        description=2026-04-13; label=v1.42

    Sorting keeps output deterministic.
    """

    props = props or {}

    parts = []

    for key in sorted(props.keys()):
        value = props.get(key)

        if value is None or value == "":
            continue

        parts.append(f"{key}={value}")

    return "; ".join(parts)


def format_component(frame: ComponentFrame) -> str:
    """
    Convert one component frame into readable context.

    Example:
        Update(description=2026-04-13; label=v1.42)

    This is generic. The function does not know what Update means.
    """

    name = frame.get("name") or "Component"
    props = frame.get("props") or {}

    prop_text = format_props(props)

    if prop_text:
        return f"{name}({prop_text})"

    return name


def format_stack(stack: ComponentStack) -> str:
    """
    Convert a nested component stack into readable context.

    Example:
        Update(label=v1.42) > Tabs > Tab(title=npm)
    """

    if not stack:
        return ""

    return " > ".join(
        format_component(frame)
        for frame in stack
        if frame
    )


# --------------------------------------STACK MUTATION-------------------------------------------

def push_component(
    stack: ComponentStack,
    name: str,
    props: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Push a component frame onto the active stack.
    """

    stack.append({
        "name": name or "Component",
        "props": dict(props or {}),
    })


def pop_component(
    stack: ComponentStack,
    name: str = "",
) -> None:
    """
    Pop a component frame safely.

    Handles normal nesting:

        <A><B></B></A>

    Also tolerates imperfect close order by removing the nearest matching
    frame from the top side.
    """

    if not stack:
        return

    if not name:
        stack.pop()
        return

    if stack[-1].get("name") == name:
        stack.pop()
        return

    for index in range(len(stack) - 1, -1, -1):
        if stack[index].get("name") == name:
            del stack[index:]
            return


# --------------------------------------METADATA-------------------------------------------

def current_component_meta(stack: ComponentStack) -> Dict[str, Any]:
    """
    Build generic component metadata from the current stack.

    This metadata can be attached to:
    - sections
    - content blocks
    - IR blocks
    """

    if not stack:
        return {}

    stack_copy = copy_stack(stack)
    nearest = stack_copy[-1] if stack_copy else {}

    return {
        "component_stack": stack_copy,
        "component_context": format_stack(stack_copy),
        "component_name": nearest.get("name", ""),
        "component_props": nearest.get("props", {}),
    }


def attach_to_content_block(
    block: Dict[str, Any],
    stack: ComponentStack,
) -> Dict[str, Any]:
    """
    Attach active component metadata to a parser content block.

    Content blocks are things like:
    - paragraph
    - list
    - code
    - table
    - self-closing component
    """

    if not block or not stack:
        return block

    meta = current_component_meta(stack)

    block.setdefault("meta", {})
    block["meta"].update(meta)

    # Also expose fields directly for debug visibility.
    block["component_stack"] = meta.get("component_stack", [])
    block["component_context"] = meta.get("component_context", "")
    block["component_name"] = meta.get("component_name", "")
    block["component_props"] = meta.get("component_props", {})

    return block


def merge_into_meta(
    base_meta: Optional[Dict[str, Any]],
    stack: ComponentStack,
) -> Dict[str, Any]:
    """
    Merge component metadata into IR block metadata.
    """

    result = dict(base_meta or {})

    if stack:
        result.update(current_component_meta(stack))

    return result


def stack_from_content_or_section(
    item: Dict[str, Any],
    section: Dict[str, Any],
) -> ComponentStack:
    """
    Resolve component stack for a content block.

    Priority:
    1. direct item component_stack
    2. item meta component_stack
    3. section component_stack
    """

    item_meta = item.get("meta", {}) or {}

    return (
        item.get("component_stack")
        or item_meta.get("component_stack")
        or section.get("component_stack")
        or []
    )


def effective_local_context(
    base_local_context: str,
    stack: ComponentStack,
) -> str:
    """
    Combine component context with heading/local context.

    This makes retrieval_text include component context without making
    block_builder.py know MDX-specific details.
    """

    base_local_context = (base_local_context or "").strip()
    component_context = format_stack(stack)

    if component_context and base_local_context:
        return f"{component_context} > {base_local_context}"

    return component_context or base_local_context


# --------------------------------------SELF-CLOSING COMPONENTS-------------------------------------------

def build_self_closing_component_block(
    name: str,
    props: Optional[Dict[str, Any]],
    stack: ComponentStack,
) -> Dict[str, Any]:
    """
    Convert a self-closing MDX component into a lightweight content block.

    Example:
        <Card title="API Reference" href="/reference/api" />

    Becomes:
        {
            "type": "component",
            "name": "Card",
            "props": {...},
            "text": "Component: Card (href=/reference/api; title=API Reference)"
        }

    No component name is hardcoded.
    """

    name = name or "Component"
    props = dict(props or {})

    prop_text = format_props(props)

    text = f"Component: {name}"

    if prop_text:
        text += f" ({prop_text})"

    block = {
        "type": "component",
        "name": name,
        "props": props,
        "text": text,
    }

    return attach_to_content_block(block, stack)