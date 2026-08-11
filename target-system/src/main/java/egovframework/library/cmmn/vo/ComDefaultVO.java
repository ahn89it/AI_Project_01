package egovframework.library.cmmn.vo;

import java.io.Serializable;

/**
 * 목록 조회 검색조건 공통 상위 VO. 각 도메인의 SearchVO가 상속해 페이징 정보를 공유한다.
 */
public class ComDefaultVO implements Serializable {

    private static final long serialVersionUID = 1L;

    private int pageIndex = 1;   // 현재 페이지 번호
    private int pageSize = 10;   // 페이지당 조회 건수
    private int firstIndex = 0;  // SQL LIMIT 시작 위치 (PagingUtil로 계산되어 채워짐)

    public int getPageIndex() {
        return pageIndex;
    }

    public void setPageIndex(int pageIndex) {
        this.pageIndex = pageIndex;
    }

    public int getPageSize() {
        return pageSize;
    }

    public void setPageSize(int pageSize) {
        this.pageSize = pageSize;
    }

    public int getFirstIndex() {
        return firstIndex;
    }

    public void setFirstIndex(int firstIndex) {
        this.firstIndex = firstIndex;
    }
}
