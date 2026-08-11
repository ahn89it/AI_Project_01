"""호출그래프 빌더.

D4 산출물(java_symbols.json, mapper_sqls.json)을 조합해
    URL → Controller.메서드 → Service인터페이스.메서드 → ServiceImpl.메서드
        → Mapper인터페이스.메서드 → Mapper XML SQL(id) → 테이블
체인을 SQLite(data/graph.db)의 nodes/edges 테이블로 만든다.

연결 규칙
    a) URL → Controller 메서드: D4에서 이미 완성된 url 필드로 직접 매핑 (HANDLES)
    b) Controller/ServiceImpl → 주입된 Service/Mapper: 주입 필드(@Autowired/@Resource)
       타입과 메서드 본문 호출식(수신자.메서드명)을 조합 (CALLS)
       - 주입 필드에서 못 찾으면 eGov 명명 관례 폴백: 변수명을 카멜케이스 클래스명으로
         추정(bookService → BookService). target-system은 관례를 정확히 따르므로 유효하다.
    c) Service인터페이스 → ServiceImpl: implements 관계로 연결 (IMPLEMENTS)
    d) 같은 클래스 안의 다른 메서드 호출(내부 호출)도 CALLS 엣지로 저장
    e) Mapper인터페이스.메서드 → XML SQL: namespace + 메서드명 = SQL id (EXECUTES)
    f) SQL → 테이블: D4의 참조 테이블 목록 (REFERENCES)

VO/ETC 계층 클래스는 호출 체인의 일부가 아니므로 그래프 노드로 만들지 않는다
(수신자.메서드() 호출 중 이런 클래스를 향하는 것은 getter/유틸 호출로 보고 무시).

실행 방식:
    python -m analyzer.callgraph
    → data/graph.db를 삭제 후 재생성 (멱등성). schema_catalog(ddl_parser)도 같이 채운다.
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from server.config import GRAPH_DB_PATH, JAVA_SYMBOLS_JSON, MAPPER_SQLS_JSON

logger = logging.getLogger(__name__)

_CALLABLE_LAYERS = {"CONTROLLER", "SERVICE_INTERFACE", "SERVICE_IMPL", "MAPPER"}
_LAYER_TO_NODE_TYPE = {
    "CONTROLLER": "CONTROLLER_METHOD",
    "SERVICE_INTERFACE": "SERVICE_METHOD",
    "SERVICE_IMPL": "IMPL_METHOD",
    "MAPPER": "MAPPER_METHOD",
}


@dataclass
class NodeRecord:
    id: str
    node_type: str
    class_name: Optional[str]
    method_name: Optional[str]
    file_path: Optional[str]
    start_line: Optional[int]
    end_line: Optional[int]
    label: str
    summary: Optional[str]


@dataclass
class EdgeRecord:
    src_id: str
    dst_id: str
    edge_type: str


def _method_node_id(class_name: str, method_name: str, layer: str) -> str:
    return f"{_LAYER_TO_NODE_TYPE[layer]}::{class_name}.{method_name}"


def _url_node_id(url: str) -> str:
    return f"URL::{url}"


def _sql_node_id(namespace: str, sql_id: str) -> str:
    return f"SQL::{namespace}.{sql_id}"


def _table_node_id(table_name: str) -> str:
    return f"TABLE::{table_name}"


class GraphBuilder:
    def __init__(self, classes: list, sqls: list):
        self.classes = classes
        self.sqls = sqls
        self.classes_by_name = {c["class_name"]: c for c in classes}
        self.nodes: dict = {}
        self.edges: list = []
        self.stats = {
            "calls_examined": 0,
            "calls_resolved": 0,
            "calls_ignored": 0,
            "calls_unresolved": 0,
        }
        self.unresolved: list = []

    # ---- node helpers ----
    def _add_node(self, node: NodeRecord) -> None:
        self.nodes[node.id] = node

    def _add_edge(self, src_id: str, dst_id: str, edge_type: str) -> None:
        self.edges.append(EdgeRecord(src_id=src_id, dst_id=dst_id, edge_type=edge_type))

    # ---- build steps ----
    def build(self) -> None:
        self._add_method_nodes()
        self._add_url_nodes_and_handles_edges()
        self._add_sql_and_table_nodes()
        self._add_mapper_to_sql_edges()
        self._add_call_edges()
        self._add_implements_edges()

    def _add_method_nodes(self) -> None:
        for c in self.classes:
            layer = c["layer"]
            if layer not in _CALLABLE_LAYERS:
                continue
            node_type = _LAYER_TO_NODE_TYPE[layer]
            for m in c["methods"]:
                node_id = _method_node_id(c["class_name"], m["method_name"], layer)
                self._add_node(NodeRecord(
                    id=node_id,
                    node_type=node_type,
                    class_name=c["class_name"],
                    method_name=m["method_name"],
                    file_path=c["file_path"],
                    start_line=m["start_line"],
                    end_line=m["end_line"],
                    label=f"{c['class_name']}.{m['method_name']}",
                    summary=m.get("leading_comment"),
                ))

    def _add_url_nodes_and_handles_edges(self) -> None:
        for c in self.classes:
            if c["layer"] != "CONTROLLER":
                continue
            for m in c["methods"]:
                if not m.get("url"):
                    continue
                url = m["url"]
                url_id = _url_node_id(url)
                if url_id not in self.nodes:
                    self._add_node(NodeRecord(
                        id=url_id, node_type="URL", class_name=None, method_name=None,
                        file_path=None, start_line=None, end_line=None,
                        label=url, summary=", ".join(m.get("http_methods") or []) or None,
                    ))
                method_id = _method_node_id(c["class_name"], m["method_name"], "CONTROLLER")
                self._add_edge(url_id, method_id, "HANDLES")

    def _add_sql_and_table_nodes(self) -> None:
        for s in self.sqls:
            sql_id_full = _sql_node_id(s["namespace"], s["sql_id"])
            self._add_node(NodeRecord(
                id=sql_id_full, node_type="SQL", class_name=None, method_name=s["sql_id"],
                file_path=s["file_path"], start_line=s["start_line"], end_line=s["end_line"],
                label=f"{s['namespace']}.{s['sql_id']}", summary=s["sql_type"],
            ))
            for table in s["referenced_tables"]:
                table_id = _table_node_id(table)
                if table_id not in self.nodes:
                    self._add_node(NodeRecord(
                        id=table_id, node_type="TABLE", class_name=None, method_name=None,
                        file_path=None, start_line=None, end_line=None,
                        label=table, summary=None,
                    ))
                self._add_edge(sql_id_full, table_id, "REFERENCES")

    def _add_mapper_to_sql_edges(self) -> None:
        sql_index = {(s["namespace"], s["sql_id"]): _sql_node_id(s["namespace"], s["sql_id"]) for s in self.sqls}
        for c in self.classes:
            if c["layer"] != "MAPPER":
                continue
            fqcn = f"{c['package']}.{c['class_name']}" if c.get("package") else c["class_name"]
            for m in c["methods"]:
                key = (fqcn, m["method_name"])
                if key in sql_index:
                    method_id = _method_node_id(c["class_name"], m["method_name"], "MAPPER")
                    self._add_edge(method_id, sql_index[key], "EXECUTES")

    def _resolve_target_class(self, source_class: dict, receiver: Optional[str]) -> tuple:
        """반환: ('SELF', None) | ('CLASS', target_class_dict) | (None, None)"""
        if receiver is None or receiver == "this":
            return ("SELF", None)

        field_map = {f["field_name"]: f["field_type"] for f in source_class.get("injected_fields", [])}
        target_type = field_map.get(receiver)

        if target_type is None:
            # eGov 명명 관례 폴백: bookService -> BookService
            candidate = receiver[0].upper() + receiver[1:] if receiver else None
            if candidate in self.classes_by_name:
                cand_layer = self.classes_by_name[candidate]["layer"]
                if cand_layer in ("SERVICE_INTERFACE", "SERVICE_IMPL", "MAPPER"):
                    target_type = candidate

        if target_type is None:
            return (None, None)

        target_class = self.classes_by_name.get(target_type)
        if target_class is None:
            return (None, target_type)  # 이름은 얻었으나 클래스 자체가 없음 -> unresolved
        if target_class["layer"] not in _CALLABLE_LAYERS:
            return (None, None)  # VO/ETC로 잘못 짚은 경우 -> 노이즈로 무시
        return ("CLASS", target_class)

    def _add_call_edges(self) -> None:
        for c in self.classes:
            if c["layer"] not in ("CONTROLLER", "SERVICE_IMPL"):
                continue
            own_methods = {m["method_name"] for m in c["methods"]}
            src_layer = c["layer"]

            for m in c["methods"]:
                src_id = _method_node_id(c["class_name"], m["method_name"], src_layer)

                for call in m["calls"]:
                    self.stats["calls_examined"] += 1
                    receiver = call["receiver"]
                    method_name = call["method_name"]

                    kind, target = self._resolve_target_class(c, receiver)

                    if kind == "SELF":
                        if method_name in own_methods and method_name != m["method_name"]:
                            dst_id = _method_node_id(c["class_name"], method_name, src_layer)
                            self._add_edge(src_id, dst_id, "CALLS")
                            self.stats["calls_resolved"] += 1
                        else:
                            self.stats["calls_ignored"] += 1
                        continue

                    if kind is None and target is not None:
                        # 명명 관례로 타입까지는 짐작했으나 해당 클래스가 존재하지 않음
                        self.stats["calls_unresolved"] += 1
                        self.unresolved.append({
                            "class_name": c["class_name"], "method_name": m["method_name"],
                            "line": call["line"], "receiver": receiver, "call": method_name,
                            "reason": f"클래스 '{target}'를 찾을 수 없음",
                        })
                        logger.warning(
                            "호출 연결 실패: %s.%s():%d — %s.%s() (클래스 '%s' 없음)",
                            c["class_name"], m["method_name"], call["line"], receiver, method_name, target,
                        )
                        continue

                    if kind is None:
                        self.stats["calls_ignored"] += 1
                        continue

                    # kind == "CLASS"
                    target_class = target
                    target_layer = target_class["layer"]
                    target_method_names = {mm["method_name"] for mm in target_class["methods"]}
                    if method_name not in target_method_names:
                        self.stats["calls_unresolved"] += 1
                        self.unresolved.append({
                            "class_name": c["class_name"], "method_name": m["method_name"],
                            "line": call["line"], "receiver": receiver, "call": method_name,
                            "reason": f"'{target_class['class_name']}'에 메서드 '{method_name}' 없음",
                        })
                        logger.warning(
                            "호출 연결 실패: %s.%s():%d — %s.%s() ('%s'에 해당 메서드 없음)",
                            c["class_name"], m["method_name"], call["line"], receiver, method_name,
                            target_class["class_name"],
                        )
                        continue

                    dst_id = _method_node_id(target_class["class_name"], method_name, target_layer)
                    self._add_edge(src_id, dst_id, "CALLS")
                    self.stats["calls_resolved"] += 1

    def _add_implements_edges(self) -> None:
        for c in self.classes:
            if c["layer"] != "SERVICE_IMPL":
                continue
            for iface_name in c.get("implements", []):
                iface = self.classes_by_name.get(iface_name)
                if iface is None or iface["layer"] != "SERVICE_INTERFACE":
                    continue
                impl_methods = {m["method_name"] for m in c["methods"]}
                for m in iface["methods"]:
                    if m["method_name"] not in impl_methods:
                        continue
                    src_id = _method_node_id(iface["class_name"], m["method_name"], "SERVICE_INTERFACE")
                    dst_id = _method_node_id(c["class_name"], m["method_name"], "SERVICE_IMPL")
                    self._add_edge(src_id, dst_id, "IMPLEMENTS")


# ---------------------------------------------------------------------------
# SQLite 저장
# ---------------------------------------------------------------------------

def create_graph_tables(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS edges")
    conn.execute("DROP TABLE IF EXISTS nodes")
    conn.execute("""
        CREATE TABLE nodes (
            id TEXT PRIMARY KEY,
            node_type TEXT NOT NULL,
            class_name TEXT,
            method_name TEXT,
            file_path TEXT,
            start_line INTEGER,
            end_line INTEGER,
            label TEXT,
            summary TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            src_id TEXT NOT NULL,
            dst_id TEXT NOT NULL,
            edge_type TEXT NOT NULL,
            FOREIGN KEY (src_id) REFERENCES nodes(id),
            FOREIGN KEY (dst_id) REFERENCES nodes(id)
        )
    """)
    conn.execute("CREATE INDEX idx_nodes_type ON nodes(node_type)")
    conn.execute("CREATE INDEX idx_nodes_symbol ON nodes(class_name, method_name)")
    conn.execute("CREATE INDEX idx_edges_src ON edges(src_id)")
    conn.execute("CREATE INDEX idx_edges_dst ON edges(dst_id)")
    conn.execute("CREATE INDEX idx_edges_type ON edges(edge_type)")


def save_graph(conn: sqlite3.Connection, nodes: dict, edges: list) -> None:
    create_graph_tables(conn)
    conn.executemany(
        "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(n.id, n.node_type, n.class_name, n.method_name, n.file_path,
          n.start_line, n.end_line, n.label, n.summary) for n in nodes.values()],
    )
    conn.executemany(
        "INSERT INTO edges (src_id, dst_id, edge_type) VALUES (?, ?, ?)",
        [(e.src_id, e.dst_id, e.edge_type) for e in edges],
    )
    conn.commit()


# ---------------------------------------------------------------------------
# 조회 API (D7 RAG / D8 진단 / D9 Text-to-SQL / D10 매뉴얼이 사용)
# ---------------------------------------------------------------------------

def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def get_chain(conn: sqlite3.Connection, url: str) -> dict:
    """URL부터 도달 가능한 전체 체인(노드+엣지)을 반환한다.

    하나의 URL 처리 과정에서 여러 SQL/테이블에 닿을 수 있으므로 단일 경로가 아니라
    도달 가능한 부분그래프 전체를 반환한다.
    """
    conn.row_factory = sqlite3.Row
    url_node_id = _url_node_id(url)
    if conn.execute("SELECT 1 FROM nodes WHERE id=?", (url_node_id,)).fetchone() is None:
        return {"url": url, "found": False, "nodes": [], "edges": []}

    visited_nodes: dict = {}
    visited_edges: list = []
    frontier = [url_node_id]

    while frontier:
        next_frontier = []
        for nid in frontier:
            if nid in visited_nodes:
                continue
            row = conn.execute("SELECT * FROM nodes WHERE id=?", (nid,)).fetchone()
            if row is not None:
                visited_nodes[nid] = _row_to_dict(row)
            for erow in conn.execute("SELECT * FROM edges WHERE src_id=?", (nid,)).fetchall():
                visited_edges.append(_row_to_dict(erow))
                if erow["dst_id"] not in visited_nodes:
                    next_frontier.append(erow["dst_id"])
        frontier = next_frontier

    return {"url": url, "found": True, "nodes": list(visited_nodes.values()), "edges": visited_edges}


def expand(conn: sqlite3.Connection, node_id: str, depth: int = 1) -> dict:
    """특정 노드 기준 상하류(양방향)를 depth 홉까지 확장한다."""
    conn.row_factory = sqlite3.Row
    visited = {node_id}
    frontier = {node_id}
    edges_collected: list = []

    for _ in range(max(depth, 0)):
        next_frontier: set = set()
        for nid in frontier:
            for row in conn.execute(
                "SELECT * FROM edges WHERE src_id=? OR dst_id=?", (nid, nid)
            ).fetchall():
                edges_collected.append(_row_to_dict(row))
                other = row["dst_id"] if row["src_id"] == nid else row["src_id"]
                if other not in visited:
                    visited.add(other)
                    next_frontier.add(other)
        frontier = next_frontier

    placeholders = ",".join("?" * len(visited))
    nodes = [_row_to_dict(r) for r in conn.execute(
        f"SELECT * FROM nodes WHERE id IN ({placeholders})", list(visited)
    ).fetchall()]

    seen = set()
    uniq_edges = []
    for e in edges_collected:
        key = (e["src_id"], e["dst_id"], e["edge_type"])
        if key not in seen:
            seen.add(key)
            uniq_edges.append(e)

    return {"center": node_id, "nodes": nodes, "edges": uniq_edges}


def find_node_by_symbol(conn: sqlite3.Connection, class_name: str, method_name: str) -> Optional[dict]:
    """장애 진단(D8)용: 스택트레이스의 클래스.메서드 -> 파일:라인 매핑."""
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM nodes WHERE class_name=? AND method_name=? LIMIT 1",
        (class_name, method_name),
    ).fetchone()
    return _row_to_dict(row) if row else None


def find_sqls_by_table(conn: sqlite3.Connection, table_name: str) -> list:
    """Text-to-SQL(D9)용: 테이블 -> 관련 SQL 역추적."""
    conn.row_factory = sqlite3.Row
    table_id = _table_node_id(table_name)
    rows = conn.execute(
        """SELECT n.* FROM nodes n
           JOIN edges e ON e.src_id = n.id
           WHERE e.dst_id = ? AND e.edge_type = 'REFERENCES'""",
        (table_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def list_urls(conn: sqlite3.Connection) -> list:
    """매뉴얼 생성(D10)용: 전체 URL 목록."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM nodes WHERE node_type='URL' ORDER BY label").fetchall()
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 빌드 엔트리포인트
# ---------------------------------------------------------------------------

def run(db_path: Optional[Path] = None) -> dict:
    if not JAVA_SYMBOLS_JSON.exists() or not MAPPER_SQLS_JSON.exists():
        raise FileNotFoundError(
            "D4 산출물이 없습니다. 먼저 python -m analyzer.java_parser / analyzer.mapper_parser 를 실행하세요."
        )

    classes = json.loads(JAVA_SYMBOLS_JSON.read_text(encoding="utf-8"))
    sqls = json.loads(MAPPER_SQLS_JSON.read_text(encoding="utf-8"))

    builder = GraphBuilder(classes, sqls)
    builder.build()

    target_db = db_path or GRAPH_DB_PATH
    target_db.parent.mkdir(parents=True, exist_ok=True)
    if target_db.exists():
        target_db.unlink()  # 멱등성: 기존 DB 삭제 후 재생성

    conn = sqlite3.connect(target_db)
    try:
        save_graph(conn, builder.nodes, builder.edges)

        # DDL 스키마 카탈로그도 같은 DB에 채운다.
        from analyzer import ddl_parser
        tables = ddl_parser.parse_schema(ddl_parser.DB_SCHEMA_SQL)
        ddl_parser.store_schema_catalog(conn, tables)
    finally:
        conn.close()

    node_type_counts: dict = {}
    for n in builder.nodes.values():
        node_type_counts[n.node_type] = node_type_counts.get(n.node_type, 0) + 1
    edge_type_counts: dict = {}
    for e in builder.edges:
        edge_type_counts[e.edge_type] = edge_type_counts.get(e.edge_type, 0) + 1

    total_attempted = builder.stats["calls_resolved"] + builder.stats["calls_unresolved"]
    unresolved_ratio = (builder.stats["calls_unresolved"] / total_attempted) if total_attempted else 0.0

    result = {
        "node_counts": node_type_counts,
        "edge_counts": edge_type_counts,
        "call_stats": builder.stats,
        "unresolved_ratio": unresolved_ratio,
        "unresolved": builder.unresolved,
    }

    logger.info(
        "graph.db 저장 완료: %s (노드 %d개, 엣지 %d개, unresolved 비율 %.1f%%)",
        target_db, len(builder.nodes), len(builder.edges), unresolved_ratio * 100,
    )
    return result


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    parser = argparse.ArgumentParser(description="호출그래프 빌드")
    parser.parse_args()

    try:
        result = run()
        logger.info("노드 유형별: %s", result["node_counts"])
        logger.info("엣지 유형별: %s", result["edge_counts"])
        logger.info("호출 통계: %s", result["call_stats"])
        if result["unresolved"]:
            logger.warning("unresolved 목록 (%d건):", len(result["unresolved"]))
            for u in result["unresolved"]:
                logger.warning("  %s", u)
    except Exception:
        logger.error("callgraph 빌드 실패", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
