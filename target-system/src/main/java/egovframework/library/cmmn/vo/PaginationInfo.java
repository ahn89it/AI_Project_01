package egovframework.library.cmmn.vo;

import java.io.Serializable;

/**
 * 페이징 계산 결과 VO. PagingUtil.calcPagination()으로 생성되어 화면에 전달된다.
 */
public class PaginationInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    private int currentPageNo;         // 현재 페이지 번호
    private int recordCountPerPage;    // 페이지당 조회 건수
    private int totalRecordCount;      // 전체 건수
    private int totalPageCount;        // 전체 페이지 수
    private int firstPageNoOnPageList; // 화면에 보여줄 페이지 번호 목록의 첫 번호
    private int lastPageNoOnPageList;  // 화면에 보여줄 페이지 번호 목록의 마지막 번호
    private int firstRecordIndex;      // SQL LIMIT 시작 위치

    public int getCurrentPageNo() {
        return currentPageNo;
    }

    public void setCurrentPageNo(int currentPageNo) {
        this.currentPageNo = currentPageNo;
    }

    public int getRecordCountPerPage() {
        return recordCountPerPage;
    }

    public void setRecordCountPerPage(int recordCountPerPage) {
        this.recordCountPerPage = recordCountPerPage;
    }

    public int getTotalRecordCount() {
        return totalRecordCount;
    }

    public void setTotalRecordCount(int totalRecordCount) {
        this.totalRecordCount = totalRecordCount;
    }

    public int getTotalPageCount() {
        return totalPageCount;
    }

    public void setTotalPageCount(int totalPageCount) {
        this.totalPageCount = totalPageCount;
    }

    public int getFirstPageNoOnPageList() {
        return firstPageNoOnPageList;
    }

    public void setFirstPageNoOnPageList(int firstPageNoOnPageList) {
        this.firstPageNoOnPageList = firstPageNoOnPageList;
    }

    public int getLastPageNoOnPageList() {
        return lastPageNoOnPageList;
    }

    public void setLastPageNoOnPageList(int lastPageNoOnPageList) {
        this.lastPageNoOnPageList = lastPageNoOnPageList;
    }

    public int getFirstRecordIndex() {
        return firstRecordIndex;
    }

    public void setFirstRecordIndex(int firstRecordIndex) {
        this.firstRecordIndex = firstRecordIndex;
    }
}
