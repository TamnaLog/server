"""TourAPI 장소 상세 설명(`overview`) 정리 테스트.

정리 규칙은 app/map/docs/BUSINESS_RULES.md - 지도 장소 상세 조회 2장에 있다.
`overview` 에는 HTML 태그와 엔티티가 섞여 오므로 프론트가 그대로 표시할 수 있는
일반 문자열로 바꿔서 내려줘야 한다.

장소 상세 조회 API 테스트는 이 함수를 스텁으로 막기 때문에 정리 규칙이 검증되지 않는다.
그래서 HTTP 호출만 대신하고 정리 로직은 실제로 태워서 확인한다.
"""

from typing import Any

import pytest

from app.services import kto


@pytest.fixture
def detail_common_item(monkeypatch: pytest.MonkeyPatch):
    """TourAPI 호출만 대신하고 정리 로직은 그대로 태운다."""

    def set_item(item: dict[str, Any] | None) -> None:
        monkeypatch.setattr(kto, "_get_detail_common_item", lambda content_id: item)

    return set_item


def test_HTML_태그를_제거한다(detail_common_item) -> None:
    detail_common_item({"overview": "<p>제주 동쪽 바다</p><br>정상에서 볼 수 있습니다."})

    assert kto.get_location_overview(1) == "제주 동쪽 바다 정상에서 볼 수 있습니다."


def test_HTML_엔티티를_일반_문자로_바꾼다(detail_common_item) -> None:
    detail_common_item({"overview": "성산일출봉 &amp; 우도 &quot;제주&quot;"})

    assert kto.get_location_overview(1) == '성산일출봉 & 우도 "제주"'


def test_엔티티로_감싼_태그도_태그로_보고_제거한다(detail_common_item) -> None:
    # 명세 순서가 "엔티티 변환 -> 태그 제거" 라 &lt;b&gt; 는 <b> 가 됐다가 지워진다.
    detail_common_item({"overview": "&lt;b&gt;굵게&lt;/b&gt; 표시"})

    assert kto.get_location_overview(1) == "굵게 표시"


def test_연속된_공백과_줄바꿈을_하나로_줄인다(detail_common_item) -> None:
    detail_common_item({"overview": "제주   동쪽\n\n바다\t위"})

    assert kto.get_location_overview(1) == "제주 동쪽 바다 위"


def test_앞뒤_공백을_제거한다(detail_common_item) -> None:
    detail_common_item({"overview": "   성산일출봉   "})

    assert kto.get_location_overview(1) == "성산일출봉"


@pytest.mark.parametrize(
    "overview",
    [
        pytest.param("", id="빈_문자열"),
        pytest.param("   ", id="공백만"),
        pytest.param("<br><br>", id="태그만"),
        pytest.param(None, id="overview_없음"),
        pytest.param(12345, id="문자열이_아님"),
    ],
)
def test_정리_결과가_비면_null이다(detail_common_item, overview: object) -> None:
    detail_common_item({"overview": overview})

    assert kto.get_location_overview(1) is None


def test_TourAPI_조회에_실패하면_null이다(detail_common_item) -> None:
    detail_common_item(None)

    assert kto.get_location_overview(1) is None


def test_정리할_것이_없으면_원문_그대로_반환한다(detail_common_item) -> None:
    plain = "제주 동쪽 바다 위로 솟아오른 응회구입니다."
    detail_common_item({"overview": plain})

    assert kto.get_location_overview(1) == plain
