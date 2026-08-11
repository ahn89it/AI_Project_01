<%@ page contentType="text/html; charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ taglib prefix="fmt" uri="http://java.sun.com/jsp/jstl/fmt" %>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>연체 관리</title>
</head>
<body>
<h2>연체자 목록</h2>

<form action="${pageContext.request.contextPath}/overdue/refreshOverdueStatus.do" method="post">
    <button type="submit">연체 상태 일괄 갱신</button>
</form>

<form action="${pageContext.request.contextPath}/overdue/selectOverdueList.do" method="get">
    <input type="text" name="memberId" value="${searchVO.memberId}" placeholder="회원ID"/>
    <select name="sanctionStatus">
        <option value="">전체</option>
        <option value="1" ${searchVO.sanctionStatus == '1' ? 'selected' : ''}>제재중</option>
        <option value="2" ${searchVO.sanctionStatus == '2' ? 'selected' : ''}>해제됨</option>
    </select>
    <button type="submit">검색</button>
</form>

<table border="1">
    <thead>
    <tr>
        <th>연체ID</th>
        <th>회원명</th>
        <th>도서명</th>
        <th>연체시작일</th>
        <th>연체일수</th>
        <th>연체해제일</th>
        <th>제재상태</th>
        <th>처리</th>
    </tr>
    </thead>
    <tbody>
    <c:forEach var="overdue" items="${resultList}">
        <tr>
            <td>${overdue.overdueId}</td>
            <td>${overdue.memberNm}</td>
            <td>${overdue.bookTitle}</td>
            <td><fmt:formatDate value="${overdue.overdueStartDate}" pattern="yyyy-MM-dd"/></td>
            <td>${overdue.overdueDays}</td>
            <td><fmt:formatDate value="${overdue.releaseDate}" pattern="yyyy-MM-dd"/></td>
            <td>${overdue.sanctionStatus == '1' ? '제재중' : '해제됨'}</td>
            <td>
                <c:if test="${overdue.sanctionStatus == '1'}">
                    <form action="${pageContext.request.contextPath}/overdue/updateRelease.do" method="post" style="display:inline">
                        <input type="hidden" name="overdueId" value="${overdue.overdueId}"/>
                        <button type="submit">해제</button>
                    </form>
                </c:if>
            </td>
        </tr>
    </c:forEach>
    </tbody>
</table>

<div>
    총 ${paginationInfo.totalRecordCount}건 / ${paginationInfo.currentPageNo} 페이지
    <c:forEach var="pageNo" begin="${paginationInfo.firstPageNoOnPageList}" end="${paginationInfo.lastPageNoOnPageList}">
        <a href="${pageContext.request.contextPath}/overdue/selectOverdueList.do?pageIndex=${pageNo}&memberId=${searchVO.memberId}">${pageNo}</a>
    </c:forEach>
</div>

</body>
</html>
