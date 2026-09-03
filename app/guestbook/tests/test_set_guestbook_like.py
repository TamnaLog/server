"""PUT /api/v1/guestbooks/{guestbookId}/like - 방명록 좋아요 테스트.

기준 문서: app/guestbook/docs/API_SPEC.md, app/guestbook/docs/BUSINESS_RULES.md (D)
"""

from datetime import date, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.guestbook import service
from app.guestbook.models import (
    Guestbook,
    GuestbookLike,
    RoadGuestbook,
    RoadGuestbookLike,
)
from app.map.models import Location
from app.user.models import User
from conftest import CURRENT_USER_ID, access_token_hash, auth_headers


LOCATION_ID = 39

# 나(=CURRENT_USER_ID) 말고 다른 사람들. 본인 방명록에는 좋아요를 누를 수 없다.
AUTHOR_USER_ID = 2
THIRD_USER_ID = 3

# 다른 사람이 쓴 방명록 (좋아요 대상)
GENERAL_ID = 101
ROAD_ID = 201

# 내가 쓴 방명록 (409 대상)
MY_GENERAL_ID = 102
MY_ROAD_ID = 202

# 소프트 삭제된 방명록
DELETED_GENERAL_ID = 111
DELETED_ROAD_ID = 211

# 두 테이블에 같은 id 가 있는 경우 (유형으로만 구분한다)
SHARED_ID = 300

VISITED_ON = date(2026, 8, 21)
SAVED_AT = datetime(2026, 8, 21, 14, 20, 0)
LIKED_AT = datetime(2026, 8, 22, 9, 0, 0)
CANCELED_AT = datetime(2026, 8, 23, 10, 0, 0)


@pytest.fixture
def like_data(db_session: Session) -> None:
    """사용자 3명 + 유형별 방명록. 좋아요는 각 테스트에서 만든다."""
    db_session.add_all(
        [
            Location(
                id=LOCATION_ID,
                content_id=126508,
                location_title="현애원",
                location_address="제주특별자치도 서귀포시 성산읍",
                location_category="관광지",
                radius=300,
                mx=126.9331,
                my=33.4582,
            ),
            User(
                id=CURRENT_USER_ID,
                access_token_hash=access_token_hash(CURRENT_USER_ID),
                nickname="몽글몽글파도",
                point=0,
            ),
            User(
                id=AUTHOR_USER_ID,
                access_token_hash=access_token_hash(AUTHOR_USER_ID),
                nickname="한라봉주스",
                point=0,
            ),
            User(
                id=THIRD_USER_ID,
                access_token_hash=access_token_hash(THIRD_USER_ID),
                nickname="돌하르방",
                point=0,
            ),
        ]
    )
    db_session.commit()

    _add_general(db_session, guestbook_id=GENERAL_ID, user_id=AUTHOR_USER_ID)
    _add_general(db_session, guestbook_id=MY_GENERAL_ID, user_id=CURRENT_USER_ID)
    _add_general(
        db_session,
        guestbook_id=DELETED_GENERAL_ID,
        user_id=AUTHOR_USER_ID,
        deleted_at=CANCELED_AT,
    )
    _add_road(db_session, guestbook_id=ROAD_ID, user_id=AUTHOR_USER_ID)
    _add_road(db_session, guestbook_id=MY_ROAD_ID, user_id=CURRENT_USER_ID)
    _add_road(
        db_session,
        guestbook_id=DELETED_ROAD_ID,
        user_id=AUTHOR_USER_ID,
        deleted_at=CANCELED_AT,
    )


def _add_general(
    db_session: Session,
    *,
    guestbook_id: int,
    user_id: int,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        Guestbook(
            id=guestbook_id,
            user_id=user_id,
            location_id=LOCATION_ID,
            visited_at=VISITED_ON,
            saved_at=SAVED_AT,
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _add_road(
    db_session: Session,
    *,
    guestbook_id: int,
    user_id: int,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        RoadGuestbook(
            id=guestbook_id,
            user_id=user_id,
            location_id=None,
            location_alias="성산 바다 앞",
            visited_at=VISITED_ON,
            mx=126.9331,
            my=33.4582,
            saved_at=SAVED_AT,
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _add_like(
    db_session: Session,
    *,
    guestbook_id: int = GENERAL_ID,
    user_id: int = CURRENT_USER_ID,
    created_at: datetime = LIKED_AT,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        GuestbookLike(
            guestbook_id=guestbook_id,
            user_id=user_id,
            created_at=created_at,
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _add_road_like(
    db_session: Session,
    *,
    guestbook_id: int = ROAD_ID,
    user_id: int = CURRENT_USER_ID,
    created_at: datetime = LIKED_AT,
    deleted_at: datetime | None = None,
) -> None:
    db_session.add(
        RoadGuestbookLike(
            road_guestbook_id=guestbook_id,
            user_id=user_id,
            created_at=created_at,
            deleted_at=deleted_at,
        )
    )
    db_session.commit()


def _put(
    client: TestClient,
    guestbook_id: object = GENERAL_ID,
    *,
    body: dict[str, object] | None = None,
    guestbook_type: str = "GENERAL",
    is_liked: bool = True,
    user_id: int = CURRENT_USER_ID,
) -> Any:
    payload = (
        {"guestbookType": guestbook_type, "isLiked": is_liked} if body is None else body
    )
    return client.put(
        f"/api/v1/guestbooks/{guestbook_id}/like",
        json=payload,
        headers=auth_headers(user_id),
    )


def _likes(db_session: Session) -> list[GuestbookLike]:
    db_session.expire_all()
    return list(db_session.scalars(select(GuestbookLike).order_by(GuestbookLike.id)).all())


def _road_likes(db_session: Session) -> list[RoadGuestbookLike]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(RoadGuestbookLike).order_by(RoadGuestbookLike.id)
        ).all()
    )


# ---------------------------------------------------------------------
# 좋아요 설정 (isLiked = true)
# ---------------------------------------------------------------------


def test_좋아요를_누르면_200과_최종_상태를_반환한다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    response = _put(client)

    assert response.status_code == 200
    assert response.json() == {
        "guestbookId": GENERAL_ID,
        "guestbookType": "GENERAL",
        "isLiked": True,
        "likeCount": 1,
    }

    likes = _likes(db_session)
    assert len(likes) == 1
    assert (likes[0].guestbook_id, likes[0].user_id) == (GENERAL_ID, CURRENT_USER_ID)
    assert likes[0].deleted_at is None


def test_취소했던_좋아요는_새_행을_만들지_않고_되살린다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    _add_like(db_session, created_at=LIKED_AT, deleted_at=CANCELED_AT)

    body = _put(client).json()

    likes = _likes(db_session)
    # 행이 늘지 않고 deleted_at 만 지워진다. created_at 은 처음 누른 시각 그대로다.
    assert len(likes) == 1
    assert likes[0].deleted_at is None
    assert likes[0].created_at == LIKED_AT
    assert body["isLiked"] is True
    assert body["likeCount"] == 1


def test_이미_좋아요_상태면_값을_바꾸지_않고_성공한다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    _add_like(db_session)
    before = _likes(db_session)[0]
    before_id, before_created_at = before.id, before.created_at

    body = _put(client).json()

    likes = _likes(db_session)
    assert len(likes) == 1
    assert (likes[0].id, likes[0].created_at) == (before_id, before_created_at)
    assert likes[0].deleted_at is None
    assert body == {
        "guestbookId": GENERAL_ID,
        "guestbookType": "GENERAL",
        "isLiked": True,
        "likeCount": 1,
    }


def test_같은_요청을_여러_번_보내도_결과가_같다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    first = _put(client).json()
    second = _put(client).json()
    third = _put(client).json()

    # 멱등하다. 반전이 아니라 최종 상태를 지정하는 API 다.
    assert first == second == third
    assert len(_likes(db_session)) == 1


# ---------------------------------------------------------------------
# 좋아요 취소 (isLiked = false)
# ---------------------------------------------------------------------


def test_좋아요를_취소하면_행을_지우지_않고_deleted_at을_기록한다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    _add_like(db_session)

    body = _put(client, is_liked=False).json()

    likes = _likes(db_session)
    # 하드 삭제하지 않는다.
    assert len(likes) == 1
    assert likes[0].deleted_at is not None
    assert likes[0].created_at == LIKED_AT
    assert body == {
        "guestbookId": GENERAL_ID,
        "guestbookType": "GENERAL",
        "isLiked": False,
        "likeCount": 0,
    }


def test_좋아요를_누른_적_없는데_취소하면_행을_만들지_않는다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    body = _put(client, is_liked=False).json()

    assert _likes(db_session) == []
    assert body["isLiked"] is False
    assert body["likeCount"] == 0


def test_이미_취소된_좋아요는_deleted_at을_다시_쓰지_않는다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    _add_like(db_session, deleted_at=CANCELED_AT)

    body = _put(client, is_liked=False).json()

    likes = _likes(db_session)
    # 이미 요청한 상태와 같으므로 값을 갱신하지 않는다.
    assert len(likes) == 1
    assert likes[0].deleted_at == CANCELED_AT
    assert body["likeCount"] == 0


def test_눌렀다_취소했다_다시_눌러도_행은_하나다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    _put(client, is_liked=True)
    _put(client, is_liked=False)
    body = _put(client, is_liked=True).json()

    assert len(_likes(db_session)) == 1
    assert body["isLiked"] is True
    assert body["likeCount"] == 1


# ---------------------------------------------------------------------
# likeCount
# ---------------------------------------------------------------------


def test_likeCount는_다른_사용자의_좋아요도_함께_센다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    _add_like(db_session, user_id=AUTHOR_USER_ID)
    _add_like(db_session, user_id=THIRD_USER_ID)

    body = _put(client).json()

    # 방금 누른 내 좋아요까지 3개다.
    assert body["likeCount"] == 3


def test_likeCount는_취소된_좋아요를_세지_않는다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    _add_like(db_session, user_id=AUTHOR_USER_ID)
    _add_like(db_session, user_id=THIRD_USER_ID, deleted_at=CANCELED_AT)

    body = _put(client).json()

    assert body["likeCount"] == 2


def test_likeCount는_다른_방명록의_좋아요를_세지_않는다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    _add_general(db_session, guestbook_id=103, user_id=AUTHOR_USER_ID)
    _add_like(db_session, guestbook_id=103, user_id=AUTHOR_USER_ID)
    _add_like(db_session, guestbook_id=103, user_id=THIRD_USER_ID)

    body = _put(client).json()

    assert body["likeCount"] == 1


# ---------------------------------------------------------------------
# 유형별 테이블 분리
# ---------------------------------------------------------------------


def test_길바닥_방명록_좋아요는_ROAD_GUESTBOOK_LIKE에_저장한다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    body = _put(client, ROAD_ID, guestbook_type="ROAD").json()

    assert body == {
        "guestbookId": ROAD_ID,
        "guestbookType": "ROAD",
        "isLiked": True,
        "likeCount": 1,
    }
    road_likes = _road_likes(db_session)
    assert len(road_likes) == 1
    assert (road_likes[0].road_guestbook_id, road_likes[0].user_id) == (
        ROAD_ID,
        CURRENT_USER_ID,
    )
    # 일반 방명록 좋아요 테이블은 건드리지 않는다.
    assert _likes(db_session) == []


def test_길바닥_방명록_좋아요도_취소하면_deleted_at을_기록한다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    _add_road_like(db_session)

    body = _put(client, ROAD_ID, guestbook_type="ROAD", is_liked=False).json()

    road_likes = _road_likes(db_session)
    assert len(road_likes) == 1
    assert road_likes[0].deleted_at is not None
    assert body["likeCount"] == 0


def test_두_테이블에_같은_id가_있으면_요청_유형의_방명록만_쓴다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    _add_general(db_session, guestbook_id=SHARED_ID, user_id=AUTHOR_USER_ID)
    _add_road(db_session, guestbook_id=SHARED_ID, user_id=AUTHOR_USER_ID)

    _put(client, SHARED_ID, guestbook_type="ROAD")

    # 같은 id 라도 유형이 정한 테이블에만 좋아요가 생긴다.
    assert [like.road_guestbook_id for like in _road_likes(db_session)] == [SHARED_ID]
    assert _likes(db_session) == []


def test_두_유형의_좋아요_개수는_서로_섞이지_않는다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    _add_general(db_session, guestbook_id=SHARED_ID, user_id=AUTHOR_USER_ID)
    _add_road(db_session, guestbook_id=SHARED_ID, user_id=AUTHOR_USER_ID)
    _add_like(db_session, guestbook_id=SHARED_ID, user_id=AUTHOR_USER_ID)
    _add_like(db_session, guestbook_id=SHARED_ID, user_id=THIRD_USER_ID)

    body = _put(client, SHARED_ID, guestbook_type="ROAD").json()

    # 일반 방명록 쪽 좋아요 2개는 길바닥 개수에 포함되지 않는다.
    assert body["likeCount"] == 1


@pytest.mark.parametrize(
    ("guestbook_id", "guestbook_type"),
    [
        pytest.param(ROAD_ID, "GENERAL", id="길바닥_id를_일반으로"),
        pytest.param(GENERAL_ID, "ROAD", id="일반_id를_길바닥으로"),
    ],
)
def test_유형과_실제_테이블이_다르면_404다(
    client: TestClient,
    db_session: Session,
    like_data: None,
    guestbook_id: int,
    guestbook_type: str,
) -> None:
    response = _put(client, guestbook_id, guestbook_type=guestbook_type)

    # 선택한 유형에서 못 찾아도 다른 유형 테이블을 추가로 조회하지 않는다.
    assert response.status_code == 404
    assert response.json() == {"code": "GUESTBOOK_NOT_FOUND"}
    assert _likes(db_session) == []
    assert _road_likes(db_session) == []


# ---------------------------------------------------------------------
# 동시 요청 (유니크 제약)
# ---------------------------------------------------------------------


def test_유니크_충돌이_나면_기존_행을_되살리고_중복_행을_만들지_않는다(
    client: TestClient,
    db_session: Session,
    like_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 조회 직후 다른 요청이 행을 먼저 만든 상황을 흉내 낸다.
    # (행은 이미 있는데 우리 쪽 조회 결과는 None 이라 INSERT 를 시도한다)
    _add_like(db_session, deleted_at=CANCELED_AT)
    original_find = service._find_like
    calls: list[int] = []

    def find_like_once_missing(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:
            return None
        return original_find(*args, **kwargs)

    monkeypatch.setattr(service, "_find_like", find_like_once_missing)

    response = _put(client)

    assert response.status_code == 200
    assert response.json()["likeCount"] == 1
    likes = _likes(db_session)
    # 중복 행을 만들지 않고 기존 행을 되살린다.
    assert len(likes) == 1
    assert likes[0].deleted_at is None
    assert likes[0].created_at == LIKED_AT


# ---------------------------------------------------------------------
# 404 / 409
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("guestbook_id", "guestbook_type"),
    [
        pytest.param(9999, "GENERAL", id="없는_일반_방명록"),
        pytest.param(9999, "ROAD", id="없는_길바닥_방명록"),
        pytest.param(DELETED_GENERAL_ID, "GENERAL", id="삭제된_일반_방명록"),
        pytest.param(DELETED_ROAD_ID, "ROAD", id="삭제된_길바닥_방명록"),
    ],
)
def test_대상_방명록이_없으면_404다(
    client: TestClient,
    db_session: Session,
    like_data: None,
    guestbook_id: int,
    guestbook_type: str,
) -> None:
    response = _put(client, guestbook_id, guestbook_type=guestbook_type)

    assert response.status_code == 404
    assert response.json() == {"code": "GUESTBOOK_NOT_FOUND"}
    assert _likes(db_session) == []
    assert _road_likes(db_session) == []


@pytest.mark.parametrize("is_liked", [True, False])
def test_본인_방명록이면_409다(
    client: TestClient, db_session: Session, like_data: None, is_liked: bool
) -> None:
    response = _put(client, MY_GENERAL_ID, is_liked=is_liked)

    # isLiked 값과 관계없이 막는다.
    assert response.status_code == 409
    assert response.json() == {"code": "OWN_GUESTBOOK_LIKE_NOT_ALLOWED"}
    assert _likes(db_session) == []


def test_본인_길바닥_방명록도_409다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    response = _put(client, MY_ROAD_ID, guestbook_type="ROAD")

    assert response.status_code == 409
    assert response.json() == {"code": "OWN_GUESTBOOK_LIKE_NOT_ALLOWED"}
    assert _road_likes(db_session) == []


def test_삭제된_본인_방명록은_409가_아니라_404다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    _add_general(db_session, guestbook_id=112, user_id=CURRENT_USER_ID, deleted_at=CANCELED_AT)

    response = _put(client, 112)

    # 삭제된 방명록은 작성자와 관계없이 존재하지 않는 것으로 본다. (존재 검사가 먼저)
    assert response.status_code == 404
    assert response.json() == {"code": "GUESTBOOK_NOT_FOUND"}


# ---------------------------------------------------------------------
# 400 / 401
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"isLiked": True}, id="유형_누락"),
        pytest.param({"guestbookType": "GENERAL"}, id="isLiked_누락"),
        pytest.param({"guestbookType": "MEMO", "isLiked": True}, id="정의되지_않은_유형"),
        pytest.param({"guestbookType": "general", "isLiked": True}, id="소문자_유형"),
        pytest.param(
            {"guestbookType": "GENERAL", "isLiked": "네"}, id="불리언이_아닌_isLiked"
        ),
        pytest.param(
            {"guestbookType": "GENERAL", "isLiked": True, "userId": 2}, id="정의되지_않은_필드"
        ),
        pytest.param({}, id="빈_body"),
    ],
)
def test_요청_Body가_잘못되면_400이다(
    client: TestClient, db_session: Session, like_data: None, body: dict
) -> None:
    response = _put(client, body=body)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _likes(db_session) == []


@pytest.mark.parametrize(
    "guestbook_id",
    [pytest.param(0, id="0"), pytest.param(-1, id="음수"), pytest.param("abc", id="정수가_아님")],
)
def test_path_값이_잘못되면_400이다(
    client: TestClient, db_session: Session, like_data: None, guestbook_id: object
) -> None:
    response = _put(client, guestbook_id)

    assert response.status_code == 400
    assert response.json() == {"code": "INVALID_REQUEST"}
    assert _likes(db_session) == []


def test_인증_헤더가_없으면_401이다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    client.headers.pop("Authorization", None)

    response = client.put(
        f"/api/v1/guestbooks/{GENERAL_ID}/like",
        json={"guestbookType": "GENERAL", "isLiked": True},
    )

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _likes(db_session) == []


def test_토큰의_사용자가_없으면_401이다(
    client: TestClient, db_session: Session, like_data: None
) -> None:
    response = _put(client, user_id=999)

    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHORIZED_USER"}
    assert _likes(db_session) == []
