"""프로젝트 전역 설정. 경로/모델명/DB 접속 정보는 반드시 이 모듈을 거쳐서 사용한다.

값은 .env로 덮어쓸 수 있다 (repo에는 .env.example만 커밋하고 .env는 커밋하지 않는다).
"""
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---- 분석 대상 (target-system) ----
TARGET_SYSTEM_DIR = Path(os.getenv("TARGET_SYSTEM_DIR", str(PROJECT_ROOT / "target-system")))
JAVA_SRC_DIR = TARGET_SYSTEM_DIR / "src" / "main" / "java"
MAPPER_XML_DIR = TARGET_SYSTEM_DIR / "src" / "main" / "resources" / "mappers"
DB_SCHEMA_SQL = TARGET_SYSTEM_DIR / "db" / "schema.sql"

# analyzer 인덱싱에서 제외할 파일/디렉터리 (분석 대상이 아닌 시연/문서 자료)
ANALYZER_EXCLUDE_NAMES = {"BUGS.md"}
ANALYZER_EXCLUDE_DIRS = {"demo"}

# 장애 진단(D8) 스택트레이스 파싱 시 "우리 코드" 프레임만 남기고 나머지(Spring/Tomcat/JDK)를
# 버리기 위한 패키지 접두사
DIAGNOSE_TARGET_PACKAGE_PREFIX = os.getenv("DIAGNOSE_TARGET_PACKAGE_PREFIX", "egovframework.library")

# ---- 산출물 저장 위치 ----
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))
PARSED_DIR = DATA_DIR / "parsed"
JAVA_SYMBOLS_JSON = PARSED_DIR / "java_symbols.json"
MAPPER_SQLS_JSON = PARSED_DIR / "mapper_sqls.json"

CHROMA_DIR = DATA_DIR / "chroma"
SQLITE_DB_PATH = DATA_DIR / "metadata.db"
GRAPH_DB_PATH = DATA_DIR / "graph.db"

# ---- LLM / 임베딩 ----
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "exaone3.5:7.8b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-large")

# ---- 대상 시스템 DB (MariaDB, 읽기전용 계정) ----
TARGET_DB_HOST = os.getenv("TARGET_DB_HOST", "127.0.0.1")
TARGET_DB_PORT = int(os.getenv("TARGET_DB_PORT", "3307"))
TARGET_DB_NAME = os.getenv("TARGET_DB_NAME", "library_db")
TARGET_DB_USER = os.getenv("TARGET_DB_USER", "ai_reader")
TARGET_DB_PASSWORD = os.getenv("TARGET_DB_PASSWORD", "ChangeMe_AiReader!2026")
TARGET_DB_QUERY_TIMEOUT_SEC = int(os.getenv("TARGET_DB_QUERY_TIMEOUT_SEC", "10"))

# ---- Text-to-SQL (D9) ----
# 시연 데이터(D3 시딩)가 2026-08 기준으로 만들어져 있어, "이번 달" 같은 상대 날짜 질의가
# 맞으려면 LLM에게 프로젝트의 기준일을 명시적으로 주입해야 한다 (실제 시스템 시계가 아님).
TEXT2SQL_DEMO_TODAY = os.getenv("TEXT2SQL_DEMO_TODAY", "2026-08-19")
TEXT2SQL_MAX_ROW_LIMIT = int(os.getenv("TEXT2SQL_MAX_ROW_LIMIT", "100"))
