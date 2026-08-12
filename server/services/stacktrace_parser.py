"""Tomcat/Spring 스타일 에러 로그(스택트레이스) 파서.

예외 체인(최상위 + Caused by)과 "at ..." 스택 프레임을 추출하고,
Spring/Tomcat/JDK 프레임을 버리고 우리 코드(DIAGNOSE_TARGET_PACKAGE_PREFIX) 프레임만 남긴다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from server.config import DIAGNOSE_TARGET_PACKAGE_PREFIX

# at egovframework.library.loan.LoanServiceImpl.insertLoan(LoanServiceImpl.java:63)
_FRAME_RE = re.compile(r"at\s+([\w.$]+)\.([\w$<>]+)\(([\w]+\.java):(\d+)\)")

# NullPointerException: message  /  java.lang.NullPointerException: message
_EXCEPTION_RE = re.compile(r"^\s*([\w.$]*(?:Exception|Error)):?\s*(.*)$", re.MULTILINE)
_CAUSED_BY_RE = re.compile(r"^\s*Caused by:\s*([\w.$]*(?:Exception|Error)):?\s*(.*)$", re.MULTILINE)


class NotAStackTraceError(ValueError):
    """스택트레이스로 인식할 수 있는 "at ...(...java:NNN)" 패턴이 전혀 없을 때."""


@dataclass
class StackFrame:
    full_class: str   # egovframework.library.loan.LoanServiceImpl
    package: str
    class_name: str
    method_name: str
    file_name: str
    line_number: int


@dataclass
class ExceptionInfo:
    exception_class: str
    message: str


@dataclass
class ParsedStackTrace:
    exception_chain: list       # list[ExceptionInfo], 최상위부터 순서대로
    all_frames: list            # list[StackFrame], 로그에 등장한 전체 프레임
    our_frames: list            # list[StackFrame], 우리 코드(target package) 프레임만
    origin_frame: Optional[StackFrame]  # our_frames[0] (스택 최상단에 가장 가까운 우리 코드)


def _split_class(full_class: str) -> tuple:
    if "." in full_class:
        package, _, class_name = full_class.rpartition(".")
    else:
        package, class_name = "", full_class
    return package, class_name


def _parse_exception_chain(text: str) -> list:
    chain = []
    m = _EXCEPTION_RE.search(text)
    if m:
        chain.append(ExceptionInfo(exception_class=m.group(1), message=m.group(2).strip()))
    for m in _CAUSED_BY_RE.finditer(text):
        chain.append(ExceptionInfo(exception_class=m.group(1), message=m.group(2).strip()))
    return chain


def parse(error_log: str) -> ParsedStackTrace:
    frame_matches = list(_FRAME_RE.finditer(error_log))
    if not frame_matches:
        raise NotAStackTraceError(
            '스택트레이스로 인식되지 않습니다. "at 패키지.클래스.메서드(파일.java:라인)" 형태의 '
            "스택 프레임이 최소 1개 이상 포함된 에러 로그를 붙여넣어 주세요."
        )

    all_frames = []
    for m in frame_matches:
        full_class, method_name, file_name, line_str = m.groups()
        package, class_name = _split_class(full_class)
        all_frames.append(StackFrame(
            full_class=full_class, package=package, class_name=class_name,
            method_name=method_name, file_name=file_name, line_number=int(line_str),
        ))

    our_frames = [f for f in all_frames if f.full_class.startswith(DIAGNOSE_TARGET_PACKAGE_PREFIX)]
    origin_frame = our_frames[0] if our_frames else None

    exception_chain = _parse_exception_chain(error_log)

    return ParsedStackTrace(
        exception_chain=exception_chain,
        all_frames=all_frames,
        our_frames=our_frames,
        origin_frame=origin_frame,
    )
