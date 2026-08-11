package egovframework.library.book;

import java.io.Serializable;

/**
 * 도서 분류 코드 VO (TB_CATEGORY 매핑). 상위분류코드로 자기참조하는 계층형 분류.
 */
public class CategoryVO implements Serializable {

    private static final long serialVersionUID = 1L;

    private String categoryCd;      // 분류코드
    private String categoryNm;      // 분류명
    private String upperCategoryCd; // 상위분류코드 (최상위는 null)

    public String getCategoryCd() {
        return categoryCd;
    }

    public void setCategoryCd(String categoryCd) {
        this.categoryCd = categoryCd;
    }

    public String getCategoryNm() {
        return categoryNm;
    }

    public void setCategoryNm(String categoryNm) {
        this.categoryNm = categoryNm;
    }

    public String getUpperCategoryCd() {
        return upperCategoryCd;
    }

    public void setUpperCategoryCd(String upperCategoryCd) {
        this.upperCategoryCd = upperCategoryCd;
    }
}
