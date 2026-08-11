<%@ page contentType="text/html; charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ taglib prefix="fmt" uri="http://java.sun.com/jsp/jstl/fmt" %>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>회원 관리</title>
</head>
<body>
<h2>회원 목록</h2>

<form action="${pageContext.request.contextPath}/member/selectMemberList.do" method="get">
    <input type="text" name="memberNm" value="${searchVO.memberNm}" placeholder="회원 이름"/>
    <select name="memberStatus">
        <option value="">전체</option>
        <option value="1" ${searchVO.memberStatus == '1' ? 'selected' : ''}>정상</option>
        <option value="2" ${searchVO.memberStatus == '2' ? 'selected' : ''}>대출정지</option>
        <option value="9" ${searchVO.memberStatus == '9' ? 'selected' : ''}>탈퇴</option>
    </select>
    <button type="submit">검색</button>
</form>

<table border="1">
    <thead>
    <tr>
        <th>회원ID</th>
        <th>이름</th>
        <th>연락처</th>
        <th>이메일</th>
        <th>회원상태</th>
        <th>가입일</th>
    </tr>
    </thead>
    <tbody>
    <c:forEach var="member" items="${resultList}">
        <tr>
            <td>${member.memberId}</td>
            <td>${member.memberNm}</td>
            <td>${member.phone}</td>
            <td>${member.email}</td>
            <td>
                <c:choose>
                    <c:when test="${member.memberStatus == '1'}">정상</c:when>
                    <c:when test="${member.memberStatus == '2'}">대출정지</c:when>
                    <c:otherwise>탈퇴</c:otherwise>
                </c:choose>
            </td>
            <td><fmt:formatDate value="${member.joinDate}" pattern="yyyy-MM-dd"/></td>
        </tr>
    </c:forEach>
    </tbody>
</table>

<div>
    총 ${paginationInfo.totalRecordCount}건 / ${paginationInfo.currentPageNo} 페이지
    <c:forEach var="pageNo" begin="${paginationInfo.firstPageNoOnPageList}" end="${paginationInfo.lastPageNoOnPageList}">
        <a href="${pageContext.request.contextPath}/member/selectMemberList.do?pageIndex=${pageNo}&memberNm=${searchVO.memberNm}">${pageNo}</a>
    </c:forEach>
</div>

</body>
</html>
