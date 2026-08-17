"""Name normalisation — camelCase spec identifiers → Python house style.

`operationId` → PascalCase class name, property/param → snake_case field, path
placeholders → snake_case, plus a keyword/collision guard. All pure string functions,
no spec knowledge.
"""

from __future__ import annotations

import keyword
import re

_PLACEHOLDER = re.compile(r"\{(\w+)\}")
#: One word token, tried left-to-right:
#: 1. acronym, optionally pluralised — ``IDs`` / ``URLs`` / ``APIs`` stay one token
#:    (``targetingParentStatusIDs`` → ``...status_ids``, not ``...i_ds``);
#: 2. ``[A-Z][a-z0-9]*`` — a capitalised word keeps trailing digits, so ``V1`` / ``V2`` stay
#:    whole (``V1GetAccountById`` → ``v1_get_...``, ``getChatsV2`` → ``get_chats_v2``);
#: 3. a lowercase/digit run.
#: Still: ``UserID`` → ``user_id``, ``HTTPServer`` → ``http_server``.
_TOKEN = re.compile(r"[A-Z]{2,}s?(?![a-z])|[A-Z][a-z0-9]*|[a-z0-9]+")


def _words(raw: str) -> list[str]:
    """Split ``raw`` into lowercase word tokens across camelCase, acronyms, and separators."""

    return [t.lower() for t in _TOKEN.findall(raw)]


#: field names that would shadow an imported type in the class namespace (Pydantic then
#: fails to resolve the annotation once the field's default becomes a class attribute).
_SHADOWS_TYPE = frozenset({"date", "datetime", "any"})


def snake(raw: str) -> str:
    """``userId`` / ``user-id`` / ``UserID`` → ``user_id`` (keyword- and type-shadow-safe)."""

    out = "_".join(_words(raw)) or "field"
    if out[0].isdigit():
        out = f"f_{out}"
    if keyword.iskeyword(out) or keyword.issoftkeyword(out) or out in _SHADOWS_TYPE:
        out = f"{out}_"
    return out


def pascal(raw: str) -> str:
    """``getItemInfo`` → ``GetItemInfo``; safe for a class identifier."""

    out = "".join(w.capitalize() for w in _words(raw)) or "Model"
    if out[0].isdigit():
        out = f"M{out}"
    return out


def class_name_for_operation(operation_id: str) -> str:
    """Method-class name from an ``operationId``."""

    return pascal(operation_id)


# Only ``post_`` is stripped from method names (``post_send_message`` → ``send_message``).
# ``get_`` is kept (reads as an accessor and disambiguates read vs write); ``delete_``/
# ``put_``/``patch_`` stay too — the verb is semantically load-bearing there.
_STRIP_VERB_PREFIXES = ("post_",)


def facade_method_name(class_name: str) -> str:
    """Ergonomic facade name: ``snake(class_name)`` with the ``post_`` verb dropped.

    ``PostSendMessage`` → ``send_message``; ``GetMessagesV3`` stays ``get_messages_v3``.
    Kept intact when stripping would leave an empty or digit-leading name.
    Global uniqueness is enforced afterwards by :mod:`collisions`.
    """

    name = snake(class_name)
    for verb in _STRIP_VERB_PREFIXES:
        if name.startswith(verb):
            stripped = name[len(verb) :]
            if stripped and not stripped[0].isdigit():
                return stripped
            break
    return name


def enum_class_name(owner: str, field: str) -> str:
    """StrEnum name for an inline enum on ``owner.field``."""

    return f"{pascal(owner)}{pascal(field)}"


def normalise_endpoint(path: str) -> str:
    """Rewrite ``{userId}``/``{itemId}`` placeholders to their snake_case field names."""

    return _PLACEHOLDER.sub(lambda m: "{" + snake(m.group(1)) + "}", path)


def placeholders(path: str) -> list[str]:
    """Snake-cased placeholder names in ``path`` (post-:func:`normalise_endpoint`)."""

    return [snake(m.group(1)) for m in _PLACEHOLDER.finditer(path)]
