from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from expense_App.components.group_service import GroupService
from expense_App.dependencies import get_current_user, get_db_session
from expense_App.entity.models import Group, Member, User
from expense_App.schemas.group import (
    GroupCreateRequest,
    GroupResponse,
    MemberAliasCreateRequest,
    MemberCreateRequest,
    MemberResponse,
    MembershipCreateRequest,
    MembershipUpdateRequest,
)


router = APIRouter(prefix="/groups")


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a group",
)
def create_group(
    payload: GroupCreateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Group:
    return GroupService(db).create_group(payload.name, current_user)


@router.get(
    "",
    response_model=list[GroupResponse],
    summary="List groups created by the current user",
)
def list_groups(
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[Group]:
    return GroupService(db).list_groups(current_user)


@router.get(
    "/{group_id}",
    response_model=GroupResponse,
    summary="Get one group",
)
def get_group(
    group_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Group:
    return GroupService(db).get_owned_group(group_id, current_user)


@router.post(
    "/{group_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member with an initial membership window",
)
def add_member(
    group_id: int,
    payload: MemberCreateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Member:
    return GroupService(db).add_member(
        group_id=group_id,
        display_name=payload.display_name,
        member_type=payload.member_type,
        joined_on=payload.joined_on,
        left_on=payload.left_on,
        aliases=payload.aliases,
        current_user=current_user,
    )


@router.get(
    "/{group_id}/members",
    response_model=list[MemberResponse],
    summary="List group members and membership windows",
)
def list_members(
    group_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[Member]:
    return GroupService(db).list_members(group_id, current_user)


@router.get(
    "/{group_id}/members/{member_id}",
    response_model=MemberResponse,
    summary="Get one group member",
)
def get_member(
    group_id: int,
    member_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Member:
    return GroupService(db).get_member(group_id, member_id, current_user)


@router.post(
    "/{group_id}/members/{member_id}/aliases",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an alias for messy imported names",
)
def add_member_alias(
    group_id: int,
    member_id: int,
    payload: MemberAliasCreateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Member:
    return GroupService(db).add_member_alias(
        group_id=group_id,
        member_id=member_id,
        raw_name=payload.raw_name,
        normalized_name=payload.normalized_name,
        current_user=current_user,
    )


@router.post(
    "/{group_id}/members/{member_id}/memberships",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add another membership window",
)
def add_membership_window(
    group_id: int,
    member_id: int,
    payload: MembershipCreateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Member:
    return GroupService(db).add_membership_window(
        group_id=group_id,
        member_id=member_id,
        joined_on=payload.joined_on,
        left_on=payload.left_on,
        current_user=current_user,
    )


@router.patch(
    "/{group_id}/members/{member_id}/memberships/{membership_id}",
    response_model=MemberResponse,
    summary="Update a membership window",
)
def update_membership_window(
    group_id: int,
    member_id: int,
    membership_id: int,
    payload: MembershipUpdateRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Member:
    return GroupService(db).update_membership_window(
        group_id=group_id,
        member_id=member_id,
        membership_id=membership_id,
        joined_on=payload.joined_on,
        left_on=payload.left_on,
        current_user=current_user,
    )
