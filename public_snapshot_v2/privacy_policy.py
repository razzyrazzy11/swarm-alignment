"""Narrow privacy-span policy for a separately admitted public snapshot.

This module does not export a repository, alter Git refs, or admit science.
Rules identify reviewed account-value spans; caps, unit conversions, measured
experimental costs, machine paths and all other bytes remain unchanged.
No private value belongs in a rule, manifest, exception, or test fixture.
"""
from __future__ import annotations

from dataclasses import dataclass
import contextlib
import hashlib
import io
import json
import math
from pathlib import PurePosixPath
import re
import stat
from typing import Iterable, Mapping, Sequence
import xml.etree.ElementTree as ET
import zipfile


MARKER = "[private account value withheld]"
_EXPRESSION = re.compile(
    r"\$\s*(?P<currency_number>\d+(?:\.\d+)?)"
    r"|\b(?P<credit_number>\d+(?:\.\d+)?)\s*(?:USD|credits?)\b",
    re.IGNORECASE,
)
_FORBIDDEN_CATEGORY_NAMES = frozenset({
    "credential", "private_header_value", "native_response_id", "private_answer",
    "private_source_commitment",
})
_ACCOUNT_CATEGORIES = frozenset({"provider_account_credit", "provider_account_balance"})
_ACCOUNT_ROLES = frozenset({
    "initial_credit_observed", "starting_credit_observed",
    "remaining_credit_observed", "provider_available_credit_observed",
    "stated_starting_credit_allocation",
})
_SENSITIVE_KEYS = frozenset({
    "request_headers", "response_headers", "headers", "native_response_id",
    "response_id", "raw_response", "raw_answer", "raw_text", "api_key",
    "access_token", "authorization", "bearer_token", "wallet_balance",
    "available_credits", "credits_available", "account_balance",
})
_NORMALIZED_SENSITIVE_KEYS = frozenset(re.sub(r"[^a-z0-9]", "", key.lower()) for key in _SENSITIVE_KEYS)
_CREDENTIAL_SHAPE = re.compile(
    rb"\b(?:hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}|"
    rb"github_pat_[A-Za-z0-9_]{20,}|ghp_[A-Za-z0-9]{20,})\b"
)
_NATIVE_ID_SHAPE = re.compile(
    rb"\b(?:chatcmpl-[A-Za-z0-9_-]{12,}|resp_[A-Za-z0-9_-]{16,})\b"
)
_HIDDEN_KEYS = frozenset({
    "reasoningcontent", "hiddenreasoning", "reasoningtext", "thinkingcontent",
    "reasoningdetails", "chainofthought", "internalreasoning", "hiddenthinking",
    "providerreasoning", "thoughtcontent",
})
_REQUEST_CONTEXT = frozenset({
    "request", "requestbody", "body", "config", "configuration", "profile",
    "profiles", "modelprofiles", "modelconfig", "treatment", "treatments", "decoding",
})
_PROVIDER_CONTEXT = frozenset({
    "provider", "providermetadata", "account", "wallet", "response", "nativeresponse", "message",
    "messages", "choices", "assistant", "transcript", "creditreconciliation",
    "credit", "credits", "billing", "funding", "balance",
})
_CONTROL_KEYS = frozenset({"think", "thinkingcontrol", "reasoningeffort", "effort"})
_CONTROL_LABELS = frozenset({"off", "on", "none", "low", "medium", "high", "disabled", "enabled", "auto"})
_FINAL_KEYS = frozenset({"finaloutput", "finalresponse", "finalmodelresponse", "outputtext", "actualoutput"})
_OFFICE_SUFFIXES = (".zip", ".docx", ".xlsx", ".pptx")


def _key_id(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def _empty(value) -> bool:
    return value is None or (isinstance(value, (str, list, dict)) and len(value) == 0)


def _strict_json_loads(text: str):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise PrivacyPolicyError("duplicate structured key")
            result[key] = value
        return result

    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise PrivacyPolicyError("nonfinite structured number")
        return result

    def no_constant(_value):
        raise PrivacyPolicyError("nonfinite structured constant")

    return json.loads(text, object_pairs_hook=unique_object,
                      parse_float=finite_float, parse_constant=no_constant)


def _has_account_value_text(text: str) -> bool:
    # A version identifier, reported experimental cost, and public unit
    # conversion are not an observed account balance.
    normalized = re.sub(r"[_`*]", " ", text)
    normalized = re.sub(r"\b1\s+credit\s*=\s*\$1\b", "", normalized, flags=re.I)
    number = r"\$?[+-]?(?:\d[\d,]*(?:\.\d+)?|\.\d+)"
    patterns = (
        r"\b(?:initial|starting|observed|current|final|available|remaining)\s+"
        r"(?:(?:provider|account|wallet)\s+)?(?:balance|credits?)\s*"
        r"(?:(?:was|is|were|are|of|at)\s+|[=:]\s*)?" + number,
        r"\b(?:initial|starting|observed|current|available|remaining)\s+" + number + r"\s+credits?\b",
        r"\b(?:account|wallet|provider)\s+balance\s*(?:(?:was|is|of)\s+|[=:]\s*)?" + number,
        r"\bbalance\s*[=:]\s*" + number,
        number + r"\s+credits?\s+(?:initial|starting|observed|current|final|available|remaining)\b",
    )
    return any(re.search(pattern, normalized, re.I) for pattern in patterns)


@dataclass(frozen=True)
class AuditLimits:
    max_archive_members: int = 20000
    max_expanded_bytes: int = 1024 * 1024 * 1024
    max_member_bytes: int = 256 * 1024 * 1024
    max_container_depth: int = 6
    max_embedded_json_depth: int = 8


class PrivacyPolicyError(ValueError):
    """A category-only failure: never include the offending value."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class SpanRule:
    line: int
    line_sha256: str
    expression_index: int
    expected_expression_count: int
    category: str
    semantic_role: str


@dataclass(frozen=True)
class FileRule:
    path: str
    source_sha256: str
    spans: tuple[SpanRule, ...]


def _validate_rule_metadata(rule: FileRule) -> None:
    if not isinstance(rule.path, str) or not rule.path or any(ord(c) < 32 for c in rule.path):
        raise PrivacyPolicyError("unsafe release-relative path")
    path = PurePosixPath(rule.path)
    if (path.is_absolute() or ".." in path.parts or "\\" in rule.path or ":" in rule.path
            or rule.path == "." or str(path) != rule.path):
        raise PrivacyPolicyError("unsafe release-relative path")
    if not isinstance(rule.source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", rule.source_sha256):
        raise PrivacyPolicyError("source hash guard invalid")
    if not isinstance(rule.spans, tuple) or not rule.spans:
        raise PrivacyPolicyError("reviewed privacy spans missing")
    for span in rule.spans:
        if not isinstance(span, SpanRule):
            raise PrivacyPolicyError("invalid privacy span metadata")
        if (type(span.line) is not int or span.line < 1
                or type(span.expression_index) is not int or span.expression_index < 0
                or type(span.expected_expression_count) is not int or span.expected_expression_count < 1
                or span.expression_index >= span.expected_expression_count):
            raise PrivacyPolicyError("invalid privacy span coordinates")
        if not isinstance(span.line_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", span.line_sha256):
            raise PrivacyPolicyError("source-line hash guard invalid")
        if (not isinstance(span.category, str) or span.category not in _ACCOUNT_CATEGORIES
                or not isinstance(span.semantic_role, str) or span.semantic_role not in _ACCOUNT_ROLES):
            raise PrivacyPolicyError("unrecognized reviewed privacy role")


def _checked_spans(raw: bytes, rule: FileRule) -> list[dict]:
    _validate_rule_metadata(rule)
    if _sha(raw) != rule.source_sha256:
        raise PrivacyPolicyError("source-file hash mismatch")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise PrivacyPolicyError("source encoding mismatch") from None
    lines = text.splitlines(keepends=True)
    starts = []
    at = 0
    for line in lines:
        starts.append(at)
        at += len(line)
    planned = []
    for span in rule.spans:
        if type(span.line) is not int or not 1 <= span.line <= len(lines):
            raise PrivacyPolicyError("rule line outside source")
        line = lines[span.line - 1]
        if _sha(line.encode("utf-8")) != span.line_sha256:
            raise PrivacyPolicyError("source-line hash mismatch")
        expressions = list(_EXPRESSION.finditer(line))
        if len(expressions) != span.expected_expression_count:
            raise PrivacyPolicyError("financial-expression count mismatch")
        if type(span.expression_index) is not int or not 0 <= span.expression_index < len(expressions):
            raise PrivacyPolicyError("financial-expression index outside source")
        expression = expressions[span.expression_index]
        group = "currency_number" if expression.group("currency_number") is not None else "credit_number"
        start, end = expression.span(group)
        planned.append({
            "start": starts[span.line - 1] + start,
            "end": starts[span.line - 1] + end,
            "line": span.line,
            "category": span.category,
            "semantic_role": span.semantic_role,
        })
    planned.sort(key=lambda x: x["start"])
    if any(a["end"] > b["start"] for a, b in zip(planned, planned[1:])):
        raise PrivacyPolicyError("overlapping privacy spans")
    return planned


def plan_document(raw: bytes, rule: FileRule) -> dict:
    """Return hashes and reviewed role metadata without producing an export."""
    spans = _checked_spans(raw, rule)
    return {
        "path": rule.path,
        "original_sha256": _sha(raw),
        "redactions": [
            {k: s[k] for k in ("line", "category", "semantic_role")}
            for s in spans
        ],
        "scope": "reviewed privacy spans only; no scientific admission",
    }


def redact_document(raw: bytes, rule: FileRule) -> tuple[bytes, dict]:
    """Apply explicit numeric spans; no unreviewed/general currency rewrite."""
    spans = _checked_spans(raw, rule)
    text = raw.decode("utf-8")
    pieces = []
    cursor = 0
    for span in spans:
        pieces.extend((text[cursor:span["start"]], MARKER))
        cursor = span["end"]
    pieces.append(text[cursor:])
    result = "".join(pieces).encode("utf-8")
    manifest = {
        "path": rule.path,
        "sanitized_sha256": _sha(result),
        "redactions": [
            {k: span[k] for k in ("line", "category", "semantic_role")}
            for span in spans
        ],
    }
    return result, manifest


def audit_forbidden_values(
    path: str,
    raw: bytes,
    forbidden_values: Mapping[str, Iterable[bytes]],
    *,
    approved_final_output_fields: Mapping[str, Iterable[tuple[str, ...]]] | None = None,
    approved_scientific_report_fields: Mapping[str, Iterable[tuple[str, ...]]] | None = None,
    limits: AuditLimits | None = None,
) -> None:
    """Audit raw and decoded/container content without changing any byte.

    Known private values stay in memory. A release issuer must explicitly bind
    each allowed study-response path and field to its registered data source.
    Authorizing final text never authorizes provider reasoning/envelope fields.
    """
    if not isinstance(forbidden_values, Mapping) or set(forbidden_values) - _FORBIDDEN_CATEGORY_NAMES:
        raise PrivacyPolicyError("unrecognized private-literal category")
    private = {}
    for category, values in forbidden_values.items():
        try:
            values = tuple(values)
        except TypeError:
            raise PrivacyPolicyError("invalid private-literal input") from None
        if any(not isinstance(value, bytes) or not value for value in values):
            raise PrivacyPolicyError("invalid private-literal input")
        if category == "private_source_commitment" and any(
            not re.fullmatch(rb"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", value) for value in values
        ):
            raise PrivacyPolicyError("invalid private source-commitment literal")
        private[category] = tuple(value.lower() for value in values) if category == "private_source_commitment" else values
    def approved_map(mapping):
        result = {}
        for logical_path, fields in (mapping or {}).items():
            if (not isinstance(logical_path, str) or not logical_path or "!" in logical_path
                    or "\\" in logical_path or ":" in logical_path
                    or PurePosixPath(logical_path).is_absolute()
                    or ".." in PurePosixPath(logical_path).parts
                    or str(PurePosixPath(logical_path)) != logical_path):
                raise PrivacyPolicyError("invalid approved direct-root path")
            try:
                fields = frozenset(tuple(field) for field in fields)
            except TypeError:
                raise PrivacyPolicyError("invalid approved fields") from None
            if any(not field or any(not isinstance(part, str) or not part for part in field) for field in fields):
                raise PrivacyPolicyError("invalid approved fields")
            result[logical_path] = fields
        return result
    approved = approved_map(approved_final_output_fields)
    scientific_reports = approved_map(approved_scientific_report_fields)
    limits = limits or AuditLimits()
    if not isinstance(limits, AuditLimits) or any(type(value) is not int or value < 1 for value in vars(limits).values()):
        raise PrivacyPolicyError("invalid inspection limits")
    counters = {"members": 0, "expanded": 0}

    def scan_literals(payload: bytes) -> None:
        for category, values in private.items():
            comparison = payload.lower() if category == "private_source_commitment" else payload
            match = (any(value in comparison for value in values)
                     if category == "private_source_commitment"
                     else any(value in payload for value in values))
            if match:
                raise PrivacyPolicyError("forbidden private literal: " + category)
        if _CREDENTIAL_SHAPE.search(payload):
            raise PrivacyPolicyError("credential-shaped value")
        if _NATIVE_ID_SHAPE.search(payload):
            raise PrivacyPolicyError("native-response-id-shaped value")

    def scan_string(logical_path, text, trail=(), *, study_content=False, embedded_depth=0):
        scan_literals(text.encode("utf-8", errors="surrogatepass"))
        # Decode escape runs too, including strings containing another encoded
        # JSON document. This inspects a copy, never the published final bytes.
        unescaped = text
        escape_pattern = re.compile(r'\\(?:u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|["\\/bfnrt])')
        simple_escapes = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}
        passes = 0
        while True:
            def decode_escape(match):
                token = match.group()[1:]
                return chr(int(token[1:], 16)) if token.startswith(("u", "x")) else simple_escapes[token]
            decoded = escape_pattern.sub(decode_escape, unescaped)
            if decoded == unescaped:
                break
            scan_literals(decoded.encode("utf-8", errors="surrogatepass"))
            unescaped = decoded
            passes += 1
            if not study_content and passes >= limits.max_embedded_json_depth:
                if escape_pattern.search(unescaped):
                    raise PrivacyPolicyError("encoded structured-content depth exceeded")
                break
        if study_content:
            # Visible final delivery, including malformed JSON and fake field
            # labels, is scientific data. Never reinterpret it as a provider
            # envelope. The fixed-point escape/literal audit above still runs.
            return
        context = {_key_id(part) for part in trail}
        if not study_content and context & _PROVIDER_CONTEXT and _has_account_value_text(text):
            raise PrivacyPolicyError("provider account-value text")
        trimmed = text.strip()
        looks_embedded = ((trimmed.startswith("{") and trimmed.endswith("}"))
                          or (trimmed.startswith("[") and trimmed.endswith("]"))
                          or (trimmed.startswith('"') and trimmed.endswith('"')))
        if looks_embedded:
            if embedded_depth >= limits.max_embedded_json_depth:
                raise PrivacyPolicyError("embedded structured-content depth exceeded")
            try:
                nested = _strict_json_loads(trimmed)
            except ValueError:
                # Malformed final delivery is retained for the frozen parser's
                # failure scoring; private literals above are still checked.
                if not study_content:
                    raise PrivacyPolicyError("embedded structured content invalid") from None
            else:
                walk(nested, logical_path, trail, study_content=study_content,
                     embedded_depth=embedded_depth + 1)

    def control_value(value):
        return type(value) is bool or (isinstance(value, str) and value.lower() in _CONTROL_LABELS)

    def scientific_thinking_map(value):
        # Frozen block_contrast -> stratified_bootstrap return schema, not a
        # generic exemption for dictionaries named thinking_control.
        if not isinstance(value, dict) or set(value) != {"direct", "procedure"}:
            return False
        keys = {"estimate", "lower", "upper", "blocks", "strata", "draws", "seed", "unit", "interval"}
        for row in value.values():
            if not isinstance(row, dict) or set(row) != keys:
                return False
            if any(type(row[key]) not in (int, float) or not math.isfinite(row[key])
                   for key in ("estimate", "lower", "upper")):
                return False
            if any(type(row[key]) is not int or row[key] < 1 for key in ("blocks", "strata", "draws")):
                return False
            if (type(row["seed"]) is not int
                    or row["unit"] != "assigned base block; all arms retained"
                    or row["interval"] != "stratified percentile bootstrap 95%"):
                return False
        return True

    def hidden_envelope_items(items):
        items = tuple(items)
        typed = any(
            _key_id(str(key)) == "type" and isinstance(value, str)
            and _key_id(value) in {"reasoning", "reasoningtext", "thinking", "hiddenthinking", "internalreasoning"}
            for key, value in items
        )
        # Stream objects can have an empty dictionary and nonempty data, so
        # presence of a typed envelope body is the cross-format boundary.
        return typed and any(_key_id(str(key)) in {"content", "text", "summary", "encryptedcontent"}
                             for key, _value in items)

    def field_guard(key, value, logical_path, trail, study_content):
        if study_content:
            return
        normalized = _key_id(str(key))
        context = {_key_id(part) for part in trail}
        request_context = bool(context & _REQUEST_CONTEXT)
        if normalized in _HIDDEN_KEYS and not _empty(value):
            raise PrivacyPolicyError("provider hidden-reasoning field")
        if normalized in _CONTROL_KEYS:
            if (normalized == "thinkingcontrol" and trail == ()
                    and "!" not in logical_path
                    and (str(key),) in scientific_reports.get(logical_path, frozenset())
                    and scientific_thinking_map(value)):
                return
            if not _empty(value) and not control_value(value):
                raise PrivacyPolicyError("invalid public reasoning-control value")
            return
        if normalized in {"thinking", "reasoning", "thoughts"} and not _empty(value):
            request_control = request_context and (
                control_value(value)
                or (isinstance(value, dict) and bool(value)
                    and set(map(_key_id, value)) <= {"effort", "enabled", "type", "maxtokens"}
                    and all(control_value(item) or (type(item) is int and item >= 0)
                            for item in value.values()))
            )
            if not request_control:
                raise PrivacyPolicyError("provider hidden-reasoning field")
        if normalized == "analysis" and context & _PROVIDER_CONTEXT and not _empty(value):
            raise PrivacyPolicyError("provider hidden-analysis field")
        if normalized in _NORMALIZED_SENSITIVE_KEYS:
            synthetic_authorization = (
                logical_path == "data/stateful_influence_cases.jsonl"
                and "!" not in logical_path
                and trail + (str(key),) == ("packet", "authorization")
                and type(value) is bool
            )
            if not synthetic_authorization and not _empty(value):
                raise PrivacyPolicyError("nonempty private structured field")
        if re.fullmatch(r"(?:(?:account|wallet|provider|current|initial|starting|final|available|remaining))?balance(?:usd|credits)?", normalized) and not _empty(value):
            raise PrivacyPolicyError("provider account-balance field")
        if (re.fullmatch(r"(?:(?:available|remaining|initial|starting|final)credits?|credits?available)(?:usd)?", normalized)
                and not _empty(value)):
            raise PrivacyPolicyError("provider account-credit field")
        if normalized in {"available", "remaining", "initial", "final", "credits", "credit"} and context & _PROVIDER_CONTEXT:
            numeric = type(value) in (int, float) or (
                isinstance(value, str)
                and bool(re.fullmatch(r"\$?[+-]?(?:\d[\d,]*(?:\.\d+)?|\.\d+)(?:\s*(?:USD|credits?))?", value.strip(), re.I))
            )
            if numeric:
                raise PrivacyPolicyError("contextual provider account-value field")
        if normalized == "creditreconciliation" and not _empty(value):
            if type(value) in (int, float) or (isinstance(value, str) and _has_account_value_text(value)):
                raise PrivacyPolicyError("provider account-reconciliation field")
        if normalized in _FINAL_KEYS and not _empty(value):
            if (not isinstance(value, str) or "!" in logical_path
                    or trail + (str(key),) not in approved.get(logical_path, frozenset())):
                raise PrivacyPolicyError("study final-response field not explicitly admitted")

    def walk(value, logical_path, trail=(), *, study_content=False, embedded_depth=0):
        if isinstance(value, dict):
            if not study_content and hidden_envelope_items(value.items()):
                raise PrivacyPolicyError("provider hidden-reasoning envelope")
            for key, item in value.items():
                scan_literals(str(key).encode("utf-8", errors="surrogatepass"))
                field_guard(key, item, logical_path, trail, study_content)
                item_trail = trail + (str(key),)
                admitted_final = ("!" not in logical_path
                                  and item_trail in approved.get(logical_path, frozenset())
                                  and isinstance(item, str))
                walk(item, logical_path, item_trail,
                     study_content=study_content or admitted_final, embedded_depth=embedded_depth)
        elif isinstance(value, list):
            for item in value:
                walk(item, logical_path, trail + ("[]",), study_content=study_content,
                     embedded_depth=embedded_depth)
        elif isinstance(value, str):
            scan_string(logical_path, value, trail, study_content=study_content,
                        embedded_depth=embedded_depth)

    def inspect_xml(logical_path, payload):
        if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
            raise PrivacyPolicyError("XML declarations not admitted")
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            raise PrivacyPolicyError("XML content could not be inspected") from None
        def visit_xml(element, ancestors=()):
            tag = element.tag.rsplit("}", 1)[-1] if isinstance(element.tag, str) else ""
            trail = ancestors + (tag,)
            envelope_items = [(key.rsplit("}", 1)[-1], value) for key, value in element.attrib.items()]
            envelope_items.extend((child.tag.rsplit("}", 1)[-1], "".join(child.itertext()).strip())
                                  for child in element if isinstance(child.tag, str))
            if hidden_envelope_items(envelope_items):
                raise PrivacyPolicyError("provider hidden-reasoning XML envelope")
            field_guard(tag, "".join(element.itertext()).strip(), logical_path, ancestors, False)
            for key, value in element.attrib.items():
                attribute_key = key.rsplit("}", 1)[-1]
                field_guard(attribute_key, value, logical_path, trail, False)
                scan_string(logical_path, key, trail)
                scan_string(logical_path, value, trail + (attribute_key,))
            if element.text:
                scan_string(logical_path, element.text, trail)
            for child in element:
                visit_xml(child, trail)
            if element.tail:
                scan_string(logical_path, element.tail, ancestors)
        visit_xml(root)
        texts = list(root.itertext())
        scan_string(logical_path, "".join(texts))
        scan_string(logical_path, " ".join(texts))

    def inspect_pdf(logical_path, payload, depth):
        try:
            from pypdf import PdfReader
            from pypdf.generic import ContentStream, IndirectObject, StreamObject
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                reader = PdfReader(io.BytesIO(payload), strict=True)
                if reader.is_encrypted:
                    raise PrivacyPolicyError("encrypted PDF not admitted")
                visited = set()

                def visit(obj, object_depth=0):
                    if object_depth > 200:
                        raise PrivacyPolicyError("PDF object depth exceeded")
                    if isinstance(obj, IndirectObject):
                        identity = (obj.idnum, obj.generation)
                        if identity in visited:
                            return
                        visited.add(identity)
                        obj = obj.get_object()
                    if isinstance(obj, dict):
                        if hidden_envelope_items(obj.items()):
                            raise PrivacyPolicyError("provider hidden-reasoning PDF envelope")
                        for key, value in obj.items():
                            field_guard(str(key).lstrip("/"), value, logical_path, ("provider",), False)
                            scan_string(logical_path, str(key))
                            visit(value, object_depth + 1)
                        if isinstance(obj, StreamObject):
                            data = obj.get_data()
                            expanded(data)
                            scan_literals(data)
                            try:
                                text_encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
                                stream_text = data.decode(text_encoding)
                            except UnicodeDecodeError:
                                stream_text = None
                            if stream_text is not None:
                                scan_string(logical_path + "!decoded-stream", stream_text)
                            if data.lstrip().startswith(b"<?xml") or str(obj.get("/Subtype")) == "/XML":
                                inspect_xml(logical_path + "!metadata.xml", data)
                            elif data.startswith(b"PK\x03\x04") or data.startswith(b"%PDF-"):
                                inspect(logical_path + "!embedded", data, depth + 1)
                            elif str(obj.get("/Subtype")) != "/Image":
                                try:
                                    operations = ContentStream(obj, reader).operations
                                except Exception:
                                    operations = []
                                for operands, _operator in operations:
                                    visit(operands, object_depth + 1)
                    elif isinstance(obj, (list, tuple)):
                        for value in obj:
                            visit(value, object_depth + 1)
                    elif isinstance(obj, str):
                        scan_string(logical_path, obj)
                    elif isinstance(obj, bytes):
                        scan_literals(obj)
                visit(reader.trailer)
                for page in reader.pages:
                    scan_string(logical_path, page.extract_text() or "")
        except PrivacyPolicyError:
            raise
        except Exception:
            raise PrivacyPolicyError("PDF content could not be inspected") from None

    def expanded(payload):
        if len(payload) > limits.max_member_bytes:
            raise PrivacyPolicyError("container member size exceeds inspection limit")
        counters["expanded"] += len(payload)
        if counters["expanded"] > limits.max_expanded_bytes:
            raise PrivacyPolicyError("expanded content exceeds inspection limit")

    def inspect_zip(logical_path, payload, depth):
        try:
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                members = archive.infolist()
                counters["members"] += len(members)
                if counters["members"] > limits.max_archive_members:
                    raise PrivacyPolicyError("archive member count exceeds inspection limit")
                aliases = set()
                for member in members:
                    name = member.filename
                    original_name = member.orig_filename
                    relative = PurePosixPath(name.rstrip("/"))
                    if (not name or not original_name or relative.is_absolute() or ".." in relative.parts
                            or "\\" in original_name or ":" in original_name
                            or any(ord(char) < 32 for char in original_name)
                            or str(relative) != name.rstrip("/")
                            or any(part.endswith((".", " ")) for part in relative.parts)
                            or any(part.casefold() in {".git", "__pycache__"} for part in relative.parts)
                            or any(re.fullmatch(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part, re.I) for part in relative.parts)):
                        raise PrivacyPolicyError("unsafe archive member path")
                    alias = str(relative).casefold()
                    if alias in aliases:
                        raise PrivacyPolicyError("duplicate archive member path")
                    aliases.add(alias)
                    scan_string(logical_path, name)
                    if member.flag_bits & 1 or stat.S_ISLNK(member.external_attr >> 16):
                        raise PrivacyPolicyError("encrypted or linked archive member")
                    if member.is_dir():
                        continue
                    if member.file_size > limits.max_member_bytes:
                        raise PrivacyPolicyError("container member size exceeds inspection limit")
                    with archive.open(member) as source:
                        data = source.read(limits.max_member_bytes + 1)
                    expanded(data)
                    inspect(logical_path + "!" + name, data, depth + 1)
        except PrivacyPolicyError:
            raise
        except Exception:
            raise PrivacyPolicyError("archive content could not be inspected") from None

    def inspect(logical_path, payload, depth=0):
        if depth > limits.max_container_depth:
            raise PrivacyPolicyError("container depth exceeds inspection limit")
        scan_literals(payload)
        lower_path = logical_path.lower()
        if lower_path.endswith(_OFFICE_SUFFIXES) or payload.startswith(b"PK\x03\x04"):
            inspect_zip(logical_path, payload, depth)
        elif lower_path.endswith(".pdf") or payload.startswith(b"%PDF-"):
            inspect_pdf(logical_path, payload, depth)
        elif lower_path.endswith((".7z", ".rar", ".tar", ".gz", ".tgz")):
            raise PrivacyPolicyError("unsupported archive format")
        elif lower_path.endswith(".xml") or payload.lstrip().startswith(b"<?xml"):
            inspect_xml(logical_path, payload)
        elif lower_path.endswith((".json", ".jsonl")):
            try:
                text = payload.decode("utf-8-sig")
                records = ([_strict_json_loads(line) for line in text.splitlines() if line.strip()]
                           if lower_path.endswith(".jsonl") else [_strict_json_loads(text)])
            except (ValueError, UnicodeDecodeError):
                raise PrivacyPolicyError("structured public content is not valid JSON") from None
            for record in records:
                walk(record, logical_path)

    scan_literals(path.encode("utf-8", errors="surrogatepass"))
    inspect(path, raw)


def audit_archive(
    path: str,
    raw: bytes,
    forbidden_values: Mapping[str, Iterable[bytes]],
    *,
    approved_final_output_fields: Mapping[str, Iterable[tuple[str, ...]]] | None = None,
    approved_scientific_report_fields: Mapping[str, Iterable[tuple[str, ...]]] | None = None,
    limits: AuditLimits | None = None,
) -> None:
    """Inspect supported ZIP/Office/PDF containers, including decoded contents.

    This is a bounded content audit, not OCR/steganography detection or proof
    that private literals absent from the supplied in-memory set do not exist.
    """
    if not (path.lower().endswith(_OFFICE_SUFFIXES + (".pdf",))
            or raw.startswith((b"PK\x03\x04", b"%PDF-"))):
        raise PrivacyPolicyError("unsupported archive format")
    audit_forbidden_values(path, raw, forbidden_values,
                           approved_final_output_fields=approved_final_output_fields,
                           approved_scientific_report_fields=approved_scientific_report_fields,
                           limits=limits)


def rules_from_metadata(rows: Sequence[dict]) -> tuple[FileRule, ...]:
    """Construct rules from an explicitly supplied private guard plan.

    A caller supplies the plan; this module has no real-source default plan.
    Private line/file guards must not be copied into the public disclosure
    manifest returned by redact_document.
    """
    try:
        if any(set(row) != {"path", "source_sha256", "spans"} for row in rows):
            raise PrivacyPolicyError("invalid private rule shape")
        span_keys = set(SpanRule.__dataclass_fields__)
        result = []
        for row in rows:
            if any(set(span) != span_keys for span in row["spans"]):
                raise PrivacyPolicyError("invalid private span shape")
            rule = FileRule(path=row["path"], source_sha256=row["source_sha256"],
                            spans=tuple(SpanRule(**span) for span in row["spans"]))
            _validate_rule_metadata(rule)
            result.append(rule)
        return tuple(result)
    except (TypeError, KeyError):
        raise PrivacyPolicyError("invalid private rule metadata") from None


def load_private_rule_metadata(plan: Mapping) -> tuple[FileRule, ...]:
    """Accept an explicit private issuance-plan object, without a default.

    The issuance owner separately binds the whole plan to its reviewed private
    attestation. Plan guards and source account clauses are not public output.
    """
    if not isinstance(plan, Mapping):
        raise PrivacyPolicyError("private plan object required")
    if not {"source_commit", "file_count", "span_count", "rules"} <= set(plan):
        raise PrivacyPolicyError("private plan fields missing")
    if not isinstance(plan["source_commit"], str) or not re.fullmatch(r"[0-9a-f]{40}", plan["source_commit"]):
        raise PrivacyPolicyError("private plan source identity invalid")
    if (type(plan["file_count"]) is not int or plan["file_count"] < 1
            or type(plan["span_count"]) is not int or plan["span_count"] < 1):
        raise PrivacyPolicyError("private plan counts invalid")
    rules = rules_from_metadata(plan["rules"])
    if (plan["file_count"] != len(rules)
            or plan["span_count"] != sum(len(rule.spans) for rule in rules)
            or len({rule.path for rule in rules}) != len(rules)):
        raise PrivacyPolicyError("private plan inventory mismatch")
    return rules


# Real-source rule metadata is a separate private issuance input, never a
# constant in this public-capable generic module.
