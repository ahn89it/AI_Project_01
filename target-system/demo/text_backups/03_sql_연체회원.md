# [플랜 B] Text-to-SQL — 이번 달 연체 회원

화면이 안 뜰 때 이 페이지를 그대로 띄우거나 읽어주면 됩니다.
(2026-08-13 실측: 응답 8~11초, 10/10 시연 확정 — 매번 정확히 20건)

---

**질문**: 이번 달 연체 회원 목록과 연체 일수를 보여줘

**생성된 SQL**:
```sql
SELECT O.OVERDUE_ID AS overdueId, O.LOAN_ID AS loanId, O.OVERDUE_START_DATE AS overdueStartDate,
       O.OVERDUE_DAYS AS overdueDays, M.MEMBER_ID AS memberId, M.MEMBER_NM AS memberNm
FROM TB_OVERDUE AS O
JOIN TB_LOAN AS L ON O.LOAN_ID = L.LOAN_ID
JOIN TB_MEMBER AS M ON L.MEMBER_ID = M.MEMBER_ID
WHERE O.OVERDUE_START_DATE >= '2026-08-01' AND O.OVERDUE_START_DATE < '2026-09-01'
ORDER BY O.OVERDUE_START_DATE DESC
LIMIT 100
```
> 안내: "LIMIT이 없어 자동으로 LIMIT 100을 추가했습니다." (sql_guard 자동 보정)

**결과 (20건)**:

| overdueId | loanId | overdueStartDate | overdueDays | memberId | memberNm |
|---|---|---|---|---|---|
| OD0020 | LN000020 | 2026-08-11 | 1 | MB00045 | 최채솔 |
| OD0002 | LN000002 | 2026-08-10 | 2 | MB00028 | 이가훈 |
| OD0019 | LN000019 | 2026-08-10 | 2 | MB00001 | 서유율 |
| OD0014 | LN000014 | 2026-08-10 | 2 | MB00075 | 오성은 |
| OD0006 | LN000006 | 2026-08-10 | 2 | MB00054 | 한성훈 |
| OD0009 | LN000009 | 2026-08-10 | 2 | MB00056 | 전서은 |
| OD0010 | LN000010 | 2026-08-09 | 3 | MB00001 | 서유율 |
| OD0015 | LN000015 | 2026-08-08 | 4 | MB00056 | 전서은 |
| OD0011 | LN000011 | 2026-08-08 | 4 | MB00017 | 정재율 |
| OD0008 | LN000008 | 2026-08-06 | 6 | MB00021 | 황유규 |
| OD0007 | LN000007 | 2026-08-04 | 8 | MB00075 | 오성은 |
| OD0003 | LN000003 | 2026-08-04 | 8 | MB00024 | 장성나 |
| OD0018 | LN000018 | 2026-08-03 | 9 | MB00069 | 송서솔 |
| OD0001 | LN000001 | 2026-08-03 | 9 | MB00061 | 임은결 |
| OD0005 | LN000005 | 2026-08-03 | 9 | MB00047 | 김서혁 |
| OD0016 | LN000016 | 2026-08-01 | 11 | MB00021 | 황유규 |
| OD0017 | LN000017 | 2026-08-01 | 11 | MB00045 | 최채솔 |
| OD0013 | LN000013 | 2026-08-01 | 11 | MB00050 | 홍하형 |
| OD0012 | LN000012 | 2026-08-01 | 11 | MB00050 | 홍하형 |
| OD0004 | LN000004 | 2026-08-01 | 11 | MB00054 | 한성훈 |
