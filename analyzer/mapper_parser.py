"""MyBatis Mapper XML 파서.

target-system의 Mapper XML에서 namespace / SQL 문(id, 유형, 원문, 라인번호,
참조 테이블, resultType/parameterType)을 추출한다.

표준 xml.etree.ElementTree로 <mapper namespace="..."> 등 구조를 파싱하고,
<if>/<foreach> 같은 동적 태그를 텍스트 그대로 보존해야 하는 SQL 본문과
정확한 라인번호는 ElementTree가 주지 못하므로 정규식 기반 텍스트 스캔으로 보완한다
(MyBatis Mapper XML은 select/insert/update/delete가 서로 중첩되지 않으므로 안전하다).

단독 실행:
    python -m analyzer.mapper_parser [경로]
    (경로 생략 시 server.config.MAPPER_XML_DIR 전체를 스캔)

출력: server.config.MAPPER_SQLS_JSON (data/parsed/mapper_sqls.json)

산출물 JSON 스키마 (SQL 문 1개 = 1개 객체):
{
    "file_path": str,              # TARGET_SYSTEM_DIR 기준 상대경로
    "namespace": str | null,       # <mapper namespace="..."> (Mapper 인터페이스 FQCN과 연결)
    "sql_id": str,                 # <select id="..."> 등
    "sql_type": "select" | "insert" | "update" | "delete",
    "start_line": int,             # 1-based, 시작 태그 라인
    "end_line": int,               # 1-based, 종료 태그 라인
    "sql_text": str,               # SQL 원문 (동적 태그 포함, XML 엔티티는 디코딩)
    "referenced_tables": [str],    # TB_ 접두사 테이블명 (정규식 기반, 중복 제거)
    "result_type": str | null,
    "parameter_type": str | null
}
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path
from typing import Optional

from server.config import MAPPER_SQLS_JSON, MAPPER_XML_DIR, TARGET_SYSTEM_DIR

logger = logging.getLogger(__name__)

_STMT_RE = re.compile(
    r"<(select|insert|update|delete)\b([^>]*)>(.*?)</\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
_TABLE_RE = re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE)\s+(TB_[A-Za-z0-9_]+)", re.IGNORECASE)


@dataclass
class MapperSqlInfo:
    file_path: str
    namespace: Optional[str]
    sql_id: str
    sql_type: str
    start_line: int
    end_line: int
    sql_text: str
    referenced_tables: list
    result_type: Optional[str]
    parameter_type: Optional[str]


def _get_namespace(path: Path) -> Optional[str]:
    """표준 ElementTree로 <mapper namespace="..."> 를 파싱한다."""
    tree = ET.parse(path)
    root = tree.getroot()
    return root.get("namespace")


def _extract_tables(sql_text: str) -> list:
    seen = []
    for m in _TABLE_RE.finditer(sql_text):
        table = m.group(1).upper()
        if table not in seen:
            seen.append(table)
    return seen


def parse_file(path: Path) -> list:
    namespace = _get_namespace(path)

    text = path.read_text(encoding="utf-8")
    results = []

    for m in _STMT_RE.finditer(text):
        tag = m.group(1).lower()
        attrs_str = m.group(2)
        body = m.group(3)

        attrs = dict(_ATTR_RE.findall(attrs_str))
        sql_id = attrs.get("id", "")
        if not sql_id:
            continue

        sql_text = unescape(body.strip())
        start_line = text.count("\n", 0, m.start()) + 1
        end_line = text.count("\n", 0, m.end()) + 1

        try:
            rel_path = path.relative_to(TARGET_SYSTEM_DIR).as_posix()
        except ValueError:
            rel_path = path.as_posix()

        results.append(MapperSqlInfo(
            file_path=rel_path,
            namespace=namespace,
            sql_id=sql_id,
            sql_type=tag,
            start_line=start_line,
            end_line=end_line,
            sql_text=sql_text,
            referenced_tables=_extract_tables(sql_text),
            result_type=attrs.get("resultType"),
            parameter_type=attrs.get("parameterType"),
        ))

    return results


def parse_directory(root_dir: Path) -> tuple:
    """반환: (MapperSqlInfo 리스트, 파싱 실패한 파일 경로 리스트)"""
    all_sqls: list = []
    failed_files: list = []
    xml_files = sorted(root_dir.rglob("*.xml"))
    logger.info("Mapper XML 파일 %d개 발견 (%s)", len(xml_files), root_dir)

    for f in xml_files:
        try:
            sqls = parse_file(f)
            all_sqls.extend(sqls)
        except Exception:
            logger.warning("파싱 실패, 건너뜀: %s", f, exc_info=True)
            failed_files.append(f)
            continue

    return all_sqls, failed_files


def run(target_path: Optional[str] = None) -> list:
    root_dir = Path(target_path) if target_path else MAPPER_XML_DIR
    if not root_dir.exists():
        raise FileNotFoundError(f"경로가 존재하지 않습니다: {root_dir}")

    sqls, failed_files = parse_directory(root_dir)

    MAPPER_SQLS_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(MAPPER_SQLS_JSON, "w", encoding="utf-8") as fp:
        json.dump([asdict(s) for s in sqls], fp, ensure_ascii=False, indent=2)

    logger.info(
        "mapper_sqls.json 저장 완료: %s (SQL %d개, 실패 %d개)",
        MAPPER_SQLS_JSON, len(sqls), len(failed_files),
    )
    return sqls


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    parser = argparse.ArgumentParser(description="MyBatis Mapper XML 정적 분석")
    parser.add_argument("path", nargs="?", default=None, help="스캔할 디렉터리 (생략 시 mappers 전체)")
    args = parser.parse_args()

    try:
        run(args.path)
    except Exception:
        logger.error("mapper_parser 실행 실패", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
