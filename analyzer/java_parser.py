"""Java 소스 파서 (tree-sitter 기반).

target-system의 Java 파일에서 클래스/메서드/어노테이션/필드주입/호출식을 추출한다.
여기서 뽑는 정보는 "원재료"다 — Controller가 어떤 Service의 어떤 메서드를 호출하는지
실제로 연결(호출그래프)하는 작업은 D5에서 한다. 오늘은 정확한 추출까지만.

단독 실행:
    python -m analyzer.java_parser [경로]
    (경로 생략 시 server.config.JAVA_SRC_DIR 전체를 스캔)

출력: server.config.JAVA_SYMBOLS_JSON (data/parsed/java_symbols.json)

산출물 JSON 스키마 (파일 1개 = ClassInfo 객체 1개 이상):
{
    "file_path": str,          # TARGET_SYSTEM_DIR 기준 상대경로 (예: "src/main/java/.../LoanServiceImpl.java")
    "package": str | null,
    "class_name": str,
    "kind": "class" | "interface" | "enum",
    "layer": "CONTROLLER" | "SERVICE_INTERFACE" | "SERVICE_IMPL" | "MAPPER" | "VO" | "ETC",
    "start_line": int,         # 1-based, inclusive
    "end_line": int,           # 1-based, inclusive
    "class_annotations": [{"name": str, "args": {str: str}}],
    "extends": str | null,
    "implements": [str],
    "injected_fields": [       # @Autowired / @Resource 붙은 필드만
        {"field_type": str, "field_name": str, "annotation": str, "annotation_args": {str: str}}
    ],
    "methods": [
        {
            "method_name": str,
            "return_type": str,
            "parameters": [{"type": str, "name": str}],
            "start_line": int,
            "end_line": int,
            "annotations": [{"name": str, "args": {str: str}}],
            "url": str | null,         # 클래스 레벨 @RequestMapping과 조합한 완전한 URL
            "http_methods": [str],     # ["GET"], ["POST"] 등. 판별 불가 시 []
            "calls": [{"receiver": str | null, "method_name": str, "line": int}],
            "leading_comment": str | null   # 메서드 바로 위 주석 원문 (있으면)
        }
    ]
}
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import tree_sitter_java as tsjava
from tree_sitter import Language, Node, Parser

from server.config import JAVA_SRC_DIR, JAVA_SYMBOLS_JSON, TARGET_SYSTEM_DIR

logger = logging.getLogger(__name__)

_JAVA_LANGUAGE = Language(tsjava.language())

_REQUEST_MAPPING_ANNOTATIONS = {
    "RequestMapping": None,
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
}

_TOP_LEVEL_TYPE_NODES = {"class_declaration", "interface_declaration", "enum_declaration"}


@dataclass
class AnnotationInfo:
    name: str
    args: dict


@dataclass
class ParamInfo:
    type: str
    name: str


@dataclass
class CallInfo:
    receiver: Optional[str]
    method_name: str
    line: int


@dataclass
class InjectedFieldInfo:
    field_type: str
    field_name: str
    annotation: str
    annotation_args: dict


@dataclass
class MethodInfo:
    method_name: str
    return_type: str
    parameters: list
    start_line: int
    end_line: int
    annotations: list
    url: Optional[str]
    http_methods: list
    calls: list
    leading_comment: Optional[str]


@dataclass
class ClassInfo:
    file_path: str
    package: Optional[str]
    class_name: str
    kind: str
    layer: str
    start_line: int
    end_line: int
    class_annotations: list
    extends: Optional[str]
    implements: list
    injected_fields: list
    methods: list


def _text(src: bytes, node: Node) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _get_modifiers(node: Node) -> Optional[Node]:
    """class_declaration/method_declaration/field_declaration의 'modifiers' 자식.
    tree-sitter-java 문법에서 modifiers는 이름 붙은 필드가 아니라 위치 기반으로 찾는다."""
    return next((c for c in node.children if c.type == "modifiers"), None)


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def _parse_annotation_args(src: bytes, ann_node: Node) -> dict:
    """annotation_argument_list를 {key: value} dict로 변환.
    단일 값 형태(@Service("x"))는 {"value": "x"}로 취급한다."""
    args: dict = {}
    arg_list = ann_node.child_by_field_name("arguments")
    if arg_list is None:
        return args
    for child in arg_list.children:
        if child.type == "element_value_pair":
            key_node = child.child_by_field_name("key")
            value_node = child.child_by_field_name("value")
            key = _text(src, key_node) if key_node else "value"
            value = _strip_quotes(_text(src, value_node)) if value_node else ""
            args[key] = value
        elif child.type in ("(", ")", ","):
            continue
        else:
            # 단일 값 형태: @Service("loanService")
            args["value"] = _strip_quotes(_text(src, child))
    return args


def _extract_annotations(src: bytes, modifiers_node: Optional[Node]) -> list:
    annotations = []
    if modifiers_node is None:
        return annotations
    for child in modifiers_node.children:
        if child.type == "marker_annotation":
            name_node = child.child_by_field_name("name")
            name = _text(src, name_node) if name_node else _text(src, child).lstrip("@")
            annotations.append(AnnotationInfo(name=name, args={}))
        elif child.type == "annotation":
            name_node = child.child_by_field_name("name")
            name = _text(src, name_node) if name_node else _text(src, child).lstrip("@")
            annotations.append(AnnotationInfo(name=name, args=_parse_annotation_args(src, child)))
    return annotations


def _extract_type_list(src: bytes, node: Optional[Node]) -> list:
    """super_interfaces / extends_interfaces 등 (implements/extends 키워드 + type_list) 노드에서
    타입명만 추출한다 ('implements'/'extends' 키워드 토큰은 제외)."""
    if node is None:
        return []
    type_list_node = next((c for c in node.children if c.type == "type_list"), None)
    if type_list_node is None:
        return []
    return [_text(src, t) for t in type_list_node.children if t.type != ","]


def _find_calls(src: bytes, body_node: Optional[Node]) -> list:
    calls = []
    if body_node is None:
        return calls

    def walk(n: Node):
        if n.type == "method_invocation":
            name_node = n.child_by_field_name("name")
            object_node = n.child_by_field_name("object")
            method_name = _text(src, name_node) if name_node else ""
            receiver = _text(src, object_node) if object_node else None
            calls.append(CallInfo(receiver=receiver, method_name=method_name, line=n.start_point[0] + 1))
        for c in n.children:
            walk(c)

    walk(body_node)
    return calls


def _leading_comment(src: bytes, member_node: Node) -> Optional[str]:
    prev = member_node.prev_sibling
    if prev is not None and prev.type in ("line_comment", "block_comment"):
        text = _text(src, prev).strip()
        if any("가" <= ch <= "힣" for ch in text):  # 한글 포함 여부
            return text
    return None


def _build_url_and_methods(class_base_paths: list, method_annotations: list) -> tuple:
    url = None
    http_methods: list = []
    for ann in method_annotations:
        if ann.name not in _REQUEST_MAPPING_ANNOTATIONS:
            continue
        path = ann.args.get("value") or ann.args.get("path") or ""
        base = class_base_paths[0] if class_base_paths else ""
        combined = (base.rstrip("/") + "/" + path.lstrip("/")) if base else path
        if combined:
            url = combined
        fixed_method = _REQUEST_MAPPING_ANNOTATIONS[ann.name]
        if fixed_method:
            http_methods.append(fixed_method)
        else:
            method_val = ann.args.get("method", "")
            for m in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                if m in method_val:
                    http_methods.append(m)
    return url, http_methods


def _classify_layer(kind: str, class_name: str, annotations: list) -> str:
    ann_names = {a.name for a in annotations}
    if "Controller" in ann_names or "RestController" in ann_names:
        return "CONTROLLER"
    if "Service" in ann_names:
        return "SERVICE_IMPL"
    if kind == "interface" and class_name.endswith("Mapper"):
        return "MAPPER"
    if kind == "interface" and class_name.endswith("Service"):
        return "SERVICE_INTERFACE"
    if class_name.endswith("VO"):
        return "VO"
    return "ETC"


def _extract_methods(src: bytes, class_body: Node, class_base_paths: list) -> list:
    methods = []
    for member in class_body.children:
        if member.type != "method_declaration":
            continue
        modifiers = _get_modifiers(member)
        annotations = _extract_annotations(src, modifiers)

        name_node = member.child_by_field_name("name")
        type_node = member.child_by_field_name("type")
        params_node = member.child_by_field_name("parameters")
        body_node = member.child_by_field_name("body")

        parameters = []
        if params_node is not None:
            for p in params_node.children:
                if p.type == "formal_parameter":
                    p_type = p.child_by_field_name("type")
                    p_name = p.child_by_field_name("name")
                    parameters.append(ParamInfo(
                        type=_text(src, p_type) if p_type else "",
                        name=_text(src, p_name) if p_name else "",
                    ))

        url, http_methods = _build_url_and_methods(class_base_paths, annotations)

        methods.append(MethodInfo(
            method_name=_text(src, name_node) if name_node else "",
            return_type=_text(src, type_node) if type_node else "void",
            parameters=[asdict(p) for p in parameters],
            start_line=member.start_point[0] + 1,
            end_line=member.end_point[0] + 1,
            annotations=[asdict(a) for a in annotations],
            url=url,
            http_methods=http_methods,
            calls=[asdict(c) for c in _find_calls(src, body_node)],
            leading_comment=_leading_comment(src, member),
        ))
    return methods


def _extract_injected_fields(src: bytes, class_body: Node) -> list:
    injected = []
    for member in class_body.children:
        if member.type != "field_declaration":
            continue
        modifiers = _get_modifiers(member)
        annotations = _extract_annotations(src, modifiers)
        inject_ann = next((a for a in annotations if a.name in ("Autowired", "Resource")), None)
        if inject_ann is None:
            continue

        type_node = member.child_by_field_name("type")
        declarator = member.child_by_field_name("declarator")
        name_node = declarator.child_by_field_name("name") if declarator else None

        injected.append(InjectedFieldInfo(
            field_type=_text(src, type_node) if type_node else "",
            field_name=_text(src, name_node) if name_node else "",
            annotation=inject_ann.name,
            annotation_args=inject_ann.args,
        ))
    return injected


def parse_file(path: Path, parser: Parser) -> list:
    """Java 파일 1개를 파싱해 ClassInfo 리스트를 반환한다 (보통 1개, 드물게 여러 개)."""
    src = path.read_bytes()
    tree = parser.parse(src)
    root = tree.root_node

    package = None
    pkg_node = next((c for c in root.children if c.type == "package_declaration"), None)
    if pkg_node is not None:
        ident = next((c for c in pkg_node.children if c.type in ("identifier", "scoped_identifier")), None)
        if ident is not None:
            package = _text(src, ident)

    try:
        rel_path = path.relative_to(TARGET_SYSTEM_DIR).as_posix()
    except ValueError:
        rel_path = path.as_posix()

    results = []
    for type_node in root.children:
        if type_node.type not in _TOP_LEVEL_TYPE_NODES:
            continue

        kind = {
            "class_declaration": "class",
            "interface_declaration": "interface",
            "enum_declaration": "enum",
        }[type_node.type]

        name_node = type_node.child_by_field_name("name")
        class_name = _text(src, name_node) if name_node else "(unknown)"

        modifiers = _get_modifiers(type_node)
        class_annotations = _extract_annotations(src, modifiers)

        superclass_node = type_node.child_by_field_name("superclass")
        extends_name = None
        if superclass_node is not None:
            type_id = next((c for c in superclass_node.children if c.type != "extends"), superclass_node)
            extends_name = _text(src, type_id)

        interfaces_node = type_node.child_by_field_name("interfaces")
        implements_list = _extract_type_list(src, interfaces_node)

        class_body = type_node.child_by_field_name("body")
        if class_body is None:
            continue

        base_paths = []
        req_mapping = next((a for a in class_annotations if a.name == "RequestMapping"), None)
        if req_mapping is not None:
            path_val = req_mapping.args.get("value") or req_mapping.args.get("path")
            if path_val:
                base_paths.append(path_val)

        methods = _extract_methods(src, class_body, base_paths)
        injected_fields = _extract_injected_fields(src, class_body)
        layer = _classify_layer(kind, class_name, class_annotations)

        results.append(ClassInfo(
            file_path=rel_path,
            package=package,
            class_name=class_name,
            kind=kind,
            layer=layer,
            start_line=type_node.start_point[0] + 1,
            end_line=type_node.end_point[0] + 1,
            class_annotations=[asdict(a) for a in class_annotations],
            extends=extends_name,
            implements=implements_list,
            injected_fields=[asdict(f) for f in injected_fields],
            methods=methods,
        ))
    return results


def parse_directory(root_dir: Path) -> tuple:
    """반환: (ClassInfo 리스트, 파싱 실패한 파일 경로 리스트)"""
    parser = Parser(_JAVA_LANGUAGE)
    all_classes: list = []
    failed_files: list = []
    java_files = sorted(root_dir.rglob("*.java"))
    logger.info("Java 파일 %d개 발견 (%s)", len(java_files), root_dir)

    for f in java_files:
        try:
            classes = parse_file(f, parser)
            all_classes.extend(classes)
        except Exception:
            logger.warning("파싱 실패, 건너뜀: %s", f, exc_info=True)
            failed_files.append(f)
            continue

    return all_classes, failed_files


def run(target_path: Optional[str] = None) -> list:
    root_dir = Path(target_path) if target_path else JAVA_SRC_DIR
    if not root_dir.exists():
        raise FileNotFoundError(f"경로가 존재하지 않습니다: {root_dir}")

    classes, failed_files = parse_directory(root_dir)

    JAVA_SYMBOLS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(JAVA_SYMBOLS_JSON, "w", encoding="utf-8") as fp:
        json.dump([asdict(c) for c in classes], fp, ensure_ascii=False, indent=2)

    logger.info(
        "java_symbols.json 저장 완료: %s (클래스 %d개, 실패 %d개)",
        JAVA_SYMBOLS_JSON, len(classes), len(failed_files),
    )
    return classes


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    parser = argparse.ArgumentParser(description="Java 소스 정적 분석 (tree-sitter)")
    parser.add_argument("path", nargs="?", default=None, help="스캔할 디렉터리 (생략 시 target-system 전체)")
    args = parser.parse_args()

    try:
        run(args.path)
    except Exception:
        logger.error("java_parser 실행 실패", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
