"""KANT PA 과정 노트북용 자가 채점 도우미.

노트북 셀에서 다음처럼 사용한다::

    import grader
    _score = grader.ScoreKeeper()

    _score.grade(1,
        check('조건', mask.dtype == bool, '힌트'),
        ...)

    _score.summary()
"""

_score: dict = {}


def check(label: str, ok: bool, hint: str = "") -> bool:
    """조건 하나를 확인하고 결과를 출력한다."""
    ok = bool(ok)
    print(("  PASS  " if ok else "  FAIL  ") + label
          + ("" if ok else "   ->  " + hint))
    return ok


def grade(no: int, *conds: bool) -> None:
    """문항 하나의 채점 결과를 기록한다."""
    _score[no] = all(conds)
    print(f"[문항 {no}] {'통과' if _score[no] else '미통과'}")


def summary() -> None:
    """전체 통과 현황을 요약한다."""
    passed = sum(_score.values())
    print(f"통과 {passed} / 시도 {len(_score)} 문항")
    bad = [k for k, v in _score.items() if not v]
    print("다시 볼 문항:", ", ".join(map(str, bad)) if bad else "없음")
