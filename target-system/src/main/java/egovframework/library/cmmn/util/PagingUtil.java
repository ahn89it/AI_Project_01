package egovframework.library.cmmn.util;

import egovframework.library.cmmn.vo.PaginationInfo;

/**
 * 목록 조회 페이징 계산 유틸.
 */
public final class PagingUtil {

    /** 화면 하단에 보여줄 페이지 번호 개수 */
    private static final int PAGE_LIST_SIZE = 10;

    private PagingUtil() {
    }

    public static PaginationInfo calcPagination(int totalRecordCount, int currentPageNo, int recordCountPerPage) {
        PaginationInfo info = new PaginationInfo();

        int safeRecordCountPerPage = recordCountPerPage <= 0 ? 10 : recordCountPerPage;
        int safeCurrentPageNo = currentPageNo <= 0 ? 1 : currentPageNo;

        info.setTotalRecordCount(totalRecordCount);
        info.setRecordCountPerPage(safeRecordCountPerPage);
        info.setCurrentPageNo(safeCurrentPageNo);

        int totalPageCount = (int) Math.ceil((double) totalRecordCount / safeRecordCountPerPage);
        info.setTotalPageCount(totalPageCount);

        int firstPageNoOnPageList = ((safeCurrentPageNo - 1) / PAGE_LIST_SIZE) * PAGE_LIST_SIZE + 1;
        int lastPageNoOnPageList = Math.max(firstPageNoOnPageList, Math.min(firstPageNoOnPageList + PAGE_LIST_SIZE - 1, totalPageCount));
        info.setFirstPageNoOnPageList(firstPageNoOnPageList);
        info.setLastPageNoOnPageList(lastPageNoOnPageList);

        info.setFirstRecordIndex((safeCurrentPageNo - 1) * safeRecordCountPerPage);

        return info;
    }
}
