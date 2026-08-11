<%@ page contentType="text/html; charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ taglib prefix="fmt" uri="http://java.sun.com/jsp/jstl/fmt" %>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>대출/반납 관리</title>
</head>
<body>
<h2>대출 목록</h2>

<form action="${pageContext.request.contextPath}/loan/selectLoanList.do" method="get">
    <input type="text" name="memberId" value="${searchVO.memberId}" placeholder="회원ID"/>
    <select name="loanStatus">
        <option value="">전체</option>
        <option value="1" ${searchVO.loanStatus == '1' ? 'selected' : ''}>대출중</option>
        <option value="2" ${searchVO.loanStatus == '2' ? 'selected' : ''}>반납완료</option>
        <option value="3" ${searchVO.loanStatus == '3' ? 'selected' : ''}>연체중</option>
    </select>
    <button type="submit">검색</button>
</form>

<table border="1">
    <thead>
    <tr>
        <th>대출ID</th>
        <th>도서명</th>
        <th>회원명</th>
        <th>대출일</th>
        <th>반납예정일</th>
        <th>실제반납일</th>
        <th>상태</th>
        <th>연장횟수</th>
        <th>처리</th>
    </tr>
    </thead>
    <tbody>
    <c:forEach var="loan" items="${resultList}">
        <tr>
            <td>${loan.loanId}</td>
            <td>${loan.bookTitle}</td>
            <td>${loan.memberNm}</td>
            <td><fmt:formatDate value="${loan.loanDate}" pattern="yyyy-MM-dd"/></td>
            <td><fmt:formatDate value="${loan.dueDate}" pattern="yyyy-MM-dd"/></td>
            <td><fmt:formatDate value="${loan.returnDate}" pattern="yyyy-MM-dd"/></td>
            <td>
                <c:choose>
                    <c:when test="${loan.loanStatus == '1'}">대출중</c:when>
                    <c:when test="${loan.loanStatus == '2'}">반납완료</c:when>
                    <c:otherwise>연체중</c:otherwise>
                </c:choose>
            </td>
            <td>${loan.extendCnt}</td>
            <td>
                <c:if test="${loan.loanStatus == '1'}">
                    <form action="${pageContext.request.contextPath}/loan/updateReturn.do" method="post" style="display:inline">
                        <input type="hidden" name="loanId" value="${loan.loanId}"/>
                        <button type="submit">반납</button>
                    </form>
                    <form action="${pageContext.request.contextPath}/loan/updateExtend.do" method="post" style="display:inline">
                        <input type="hidden" name="loanId" value="${loan.loanId}"/>
                        <button type="submit">연장</button>
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
        <a href="${pageContext.request.contextPath}/loan/selectLoanList.do?pageIndex=${pageNo}&memberId=${searchVO.memberId}">${pageNo}</a>
    </c:forEach>
</div>

</body>
</html>
