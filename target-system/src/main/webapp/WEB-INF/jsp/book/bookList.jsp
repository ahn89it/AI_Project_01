<%@ page contentType="text/html; charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ taglib prefix="fmt" uri="http://java.sun.com/jsp/jstl/fmt" %>
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>도서 관리</title>
</head>
<body>
<h2>도서 목록</h2>

<form action="${pageContext.request.contextPath}/book/selectBookList.do" method="get">
    <input type="text" name="title" value="${searchVO.title}" placeholder="서명"/>
    <input type="text" name="author" value="${searchVO.author}" placeholder="저자"/>
    <select name="loanYn">
        <option value="">전체</option>
        <option value="Y" ${searchVO.loanYn == 'Y' ? 'selected' : ''}>대출가능</option>
        <option value="N" ${searchVO.loanYn == 'N' ? 'selected' : ''}>대출중</option>
    </select>
    <button type="submit">검색</button>
</form>

<table border="1">
    <thead>
    <tr>
        <th>도서ID</th>
        <th>서명</th>
        <th>저자</th>
        <th>출판사</th>
        <th>분류</th>
        <th>소장위치</th>
        <th>대출가능여부</th>
    </tr>
    </thead>
    <tbody>
    <c:forEach var="book" items="${resultList}">
        <tr>
            <td>${book.bookId}</td>
            <td>${book.title}</td>
            <td>${book.author}</td>
            <td>${book.publisher}</td>
            <td>${book.categoryNm}</td>
            <td>${book.location}</td>
            <td>${book.loanYn == 'Y' ? '대출가능' : '대출중'}</td>
        </tr>
    </c:forEach>
    </tbody>
</table>

<div>
    총 ${paginationInfo.totalRecordCount}건 / ${paginationInfo.currentPageNo} 페이지
    <c:forEach var="pageNo" begin="${paginationInfo.firstPageNoOnPageList}" end="${paginationInfo.lastPageNoOnPageList}">
        <a href="${pageContext.request.contextPath}/book/selectBookList.do?pageIndex=${pageNo}&title=${searchVO.title}&author=${searchVO.author}">${pageNo}</a>
    </c:forEach>
</div>

</body>
</html>
