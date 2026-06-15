from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from expense_App.entity.models import Group, GroupMembership, Member, MemberAlias, User
from expense_App.exception import ConflictException, DatabaseException, NotFoundException
from expense_App.logger import get_logger


logger = get_logger(__name__)


class GroupService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_group(self, name: str, current_user: User) -> Group:
        group = Group(name=name, created_by_user_id=current_user.id)
        try:
            self.db.add(group)
            self.db.commit()
            self.db.refresh(group)
            return group
        except SQLAlchemyError as error:
            self.db.rollback()
            logger.exception("Failed to create group user_id=%s", current_user.id)
            raise DatabaseException(message="Failed to create group.") from error

    def list_groups(self, current_user: User) -> list[Group]:
        statement = (
            select(Group)
            .where(Group.created_by_user_id == current_user.id)
            .order_by(Group.created_at.desc(), Group.id.desc())
        )
        return list(self.db.execute(statement).scalars().all())

    def get_owned_group(self, group_id: int, current_user: User) -> Group:
        group = self.db.get(Group, group_id)
        if not group or group.created_by_user_id != current_user.id:
            raise NotFoundException(
                message="Group was not found.",
                error_code="group_not_found",
                details={"group_id": group_id},
            )
        return group

    def get_group_detail(self, group_id: int, current_user: User) -> Group:
        statement = (
            select(Group)
            .where(
                Group.id == group_id,
                Group.created_by_user_id == current_user.id,
            )
            .options(
                selectinload(Group.members).selectinload(Member.aliases),
                selectinload(Group.members).selectinload(Member.memberships),
            )
        )
        group = self.db.execute(statement).scalar_one_or_none()
        if not group:
            raise NotFoundException(
                message="Group was not found.",
                error_code="group_not_found",
                details={"group_id": group_id},
            )
        return group

    def list_members(self, group_id: int, current_user: User) -> list[Member]:
        self.get_owned_group(group_id, current_user)
        statement = (
            select(Member)
            .where(Member.group_id == group_id)
            .options(selectinload(Member.aliases), selectinload(Member.memberships))
            .order_by(Member.display_name)
        )
        return list(self.db.execute(statement).scalars().all())

    def add_member(
        self,
        group_id: int,
        display_name: str,
        member_type: str,
        joined_on,
        left_on,
        aliases: list[str],
        current_user: User,
    ) -> Member:
        self.get_owned_group(group_id, current_user)
        existing = self._get_member_by_name(group_id, display_name)
        if existing:
            raise ConflictException(
                message="A member with this name already exists in the group.",
                error_code="member_already_exists",
                details={"group_id": group_id, "display_name": display_name},
            )

        member = Member(
            group_id=group_id,
            display_name=display_name,
            member_type=member_type,
        )
        membership = GroupMembership(
            group_id=group_id,
            member=member,
            joined_on=joined_on,
            left_on=left_on,
        )
        member.memberships.append(membership)
        for raw_alias in aliases:
            member.aliases.append(
                MemberAlias(
                    group_id=group_id,
                    raw_name=raw_alias,
                    normalized_name=display_name,
                )
            )

        try:
            self.db.add(member)
            self.db.commit()
            return self.get_member(group_id, member.id, current_user)
        except IntegrityError as error:
            self.db.rollback()
            raise ConflictException(
                message="A member or alias with this value already exists.",
                error_code="member_conflict",
                details={"group_id": group_id, "display_name": display_name},
            ) from error
        except SQLAlchemyError as error:
            self.db.rollback()
            logger.exception("Failed to add member group_id=%s", group_id)
            raise DatabaseException(message="Failed to add member.") from error

    def get_member(self, group_id: int, member_id: int, current_user: User) -> Member:
        self.get_owned_group(group_id, current_user)
        statement = (
            select(Member)
            .where(Member.id == member_id, Member.group_id == group_id)
            .options(selectinload(Member.aliases), selectinload(Member.memberships))
        )
        member = self.db.execute(statement).scalar_one_or_none()
        if not member:
            raise NotFoundException(
                message="Member was not found.",
                error_code="member_not_found",
                details={"group_id": group_id, "member_id": member_id},
            )
        return member

    def add_member_alias(
        self,
        group_id: int,
        member_id: int,
        raw_name: str,
        normalized_name: str | None,
        current_user: User,
    ) -> Member:
        member = self.get_member(group_id, member_id, current_user)
        alias = MemberAlias(
            group_id=group_id,
            member_id=member.id,
            raw_name=raw_name,
            normalized_name=normalized_name or member.display_name,
        )
        try:
            self.db.add(alias)
            self.db.commit()
            return self.get_member(group_id, member_id, current_user)
        except IntegrityError as error:
            self.db.rollback()
            raise ConflictException(
                message="This alias already exists in the group.",
                error_code="member_alias_already_exists",
                details={"group_id": group_id, "raw_name": raw_name},
            ) from error
        except SQLAlchemyError as error:
            self.db.rollback()
            logger.exception("Failed to add member alias group_id=%s member_id=%s", group_id, member_id)
            raise DatabaseException(message="Failed to add member alias.") from error

    def add_membership_window(
        self,
        group_id: int,
        member_id: int,
        joined_on,
        left_on,
        current_user: User,
    ) -> Member:
        member = self.get_member(group_id, member_id, current_user)
        membership = GroupMembership(
            group_id=group_id,
            member_id=member.id,
            joined_on=joined_on,
            left_on=left_on,
        )
        try:
            self.db.add(membership)
            self.db.commit()
            return self.get_member(group_id, member_id, current_user)
        except SQLAlchemyError as error:
            self.db.rollback()
            logger.exception("Failed to add membership window group_id=%s member_id=%s", group_id, member_id)
            raise DatabaseException(message="Failed to add membership window.") from error

    def update_membership_window(
        self,
        group_id: int,
        member_id: int,
        membership_id: int,
        joined_on,
        left_on,
        current_user: User,
    ) -> Member:
        self.get_member(group_id, member_id, current_user)
        membership = self.db.get(GroupMembership, membership_id)
        if not membership or membership.group_id != group_id or membership.member_id != member_id:
            raise NotFoundException(
                message="Membership window was not found.",
                error_code="membership_not_found",
                details={
                    "group_id": group_id,
                    "member_id": member_id,
                    "membership_id": membership_id,
                },
            )

        if joined_on is not None:
            membership.joined_on = joined_on
        if left_on is not None:
            membership.left_on = left_on
        if membership.left_on is not None and membership.left_on < membership.joined_on:
            raise ConflictException(
                message="left_on cannot be before joined_on.",
                error_code="invalid_membership_window",
            )

        try:
            self.db.commit()
            return self.get_member(group_id, member_id, current_user)
        except SQLAlchemyError as error:
            self.db.rollback()
            logger.exception("Failed to update membership window id=%s", membership_id)
            raise DatabaseException(message="Failed to update membership window.") from error

    def _get_member_by_name(self, group_id: int, display_name: str) -> Member | None:
        statement = select(Member).where(
            Member.group_id == group_id,
            Member.display_name == display_name,
        )
        return self.db.execute(statement).scalar_one_or_none()
