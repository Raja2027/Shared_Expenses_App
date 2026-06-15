from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from expense_App.database import Base


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    groups_created = relationship("Group", back_populates="created_by")
    import_batches = relationship("ImportBatch", back_populates="uploaded_by")


class Group(TimestampMixin, Base):
    __tablename__ = "groups"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(160), nullable=False)
    created_by_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)

    created_by = relationship("User", back_populates="groups_created")
    members = relationship("Member", back_populates="group", cascade="all, delete-orphan")
    memberships = relationship("GroupMembership", back_populates="group", cascade="all, delete-orphan")
    import_batches = relationship("ImportBatch", back_populates="group")
    expenses = relationship("Expense", back_populates="group")
    settlements = relationship("Settlement", back_populates="group")


class Member(TimestampMixin, Base):
    __tablename__ = "members"
    __table_args__ = (
        UniqueConstraint("group_id", "display_name", name="uq_member_group_display_name"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id"), nullable=False, index=True)
    display_name = Column(String(120), nullable=False)
    member_type = Column(String(40), nullable=False, default="flatmate")

    group = relationship("Group", back_populates="members")
    aliases = relationship("MemberAlias", back_populates="member", cascade="all, delete-orphan")
    memberships = relationship("GroupMembership", back_populates="member", cascade="all, delete-orphan")


class MemberAlias(TimestampMixin, Base):
    __tablename__ = "member_aliases"
    __table_args__ = (
        UniqueConstraint("group_id", "raw_name", name="uq_member_alias_group_raw_name"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id"), nullable=False, index=True)
    member_id = Column(BigInteger, ForeignKey("members.id"), nullable=False, index=True)
    raw_name = Column(String(120), nullable=False)
    normalized_name = Column(String(120), nullable=False)

    member = relationship("Member", back_populates="aliases")


class GroupMembership(TimestampMixin, Base):
    __tablename__ = "group_memberships"

    id = Column(BigInteger, primary_key=True, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id"), nullable=False, index=True)
    member_id = Column(BigInteger, ForeignKey("members.id"), nullable=False, index=True)
    joined_on = Column(Date, nullable=False)
    left_on = Column(Date, nullable=True)

    group = relationship("Group", back_populates="memberships")
    member = relationship("Member", back_populates="memberships")


class ImportBatch(TimestampMixin, Base):
    __tablename__ = "import_batches"

    id = Column(BigInteger, primary_key=True, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id"), nullable=False, index=True)
    uploaded_by_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    status = Column(String(40), nullable=False, default="previewed")
    summary = Column(JSONB, nullable=False, default=dict)

    group = relationship("Group", back_populates="import_batches")
    uploaded_by = relationship("User", back_populates="import_batches")
    rows = relationship("ImportRow", back_populates="batch", cascade="all, delete-orphan")


class ImportRow(TimestampMixin, Base):
    __tablename__ = "import_rows"
    __table_args__ = (
        UniqueConstraint("import_batch_id", "raw_row_number", name="uq_import_row_batch_raw_row"),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    import_batch_id = Column(BigInteger, ForeignKey("import_batches.id"), nullable=False, index=True)
    raw_row_number = Column(BigInteger, nullable=False)
    raw_data = Column(JSONB, nullable=False)
    normalized_data = Column(JSONB, nullable=False, default=dict)
    status = Column(String(50), nullable=False, default="needs_review")

    batch = relationship("ImportBatch", back_populates="rows")
    anomalies = relationship("ImportAnomaly", back_populates="row", cascade="all, delete-orphan")
    expense = relationship("Expense", back_populates="import_row", uselist=False)
    settlement = relationship("Settlement", back_populates="import_row", uselist=False)


class ImportAnomaly(TimestampMixin, Base):
    __tablename__ = "import_anomalies"

    id = Column(BigInteger, primary_key=True, index=True)
    import_row_id = Column(BigInteger, ForeignKey("import_rows.id"), nullable=False, index=True)
    code = Column(String(120), nullable=False, index=True)
    severity = Column(String(30), nullable=False)
    field_name = Column(String(120), nullable=False)
    message = Column(Text, nullable=False)
    suggested_action = Column(Text, nullable=False)
    requires_user_approval = Column(Boolean, nullable=False, default=True)
    resolution_status = Column(String(40), nullable=False, default="open")
    resolved_by_user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    related_rows = Column(JSONB, nullable=False, default=list)

    row = relationship("ImportRow", back_populates="anomalies")


class Expense(TimestampMixin, Base):
    __tablename__ = "expenses"

    id = Column(BigInteger, primary_key=True, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id"), nullable=False, index=True)
    import_row_id = Column(BigInteger, ForeignKey("import_rows.id"), nullable=True, unique=True)
    description = Column(String(255), nullable=False)
    expense_date = Column(Date, nullable=False, index=True)
    paid_by_member_id = Column(BigInteger, ForeignKey("members.id"), nullable=False)
    amount_original = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    exchange_rate_to_inr = Column(Numeric(14, 6), nullable=False)
    amount_inr = Column(Numeric(14, 2), nullable=False)
    split_type = Column(String(40), nullable=False)
    status = Column(String(40), nullable=False, default="active")

    group = relationship("Group", back_populates="expenses")
    import_row = relationship("ImportRow", back_populates="expense")
    splits = relationship("ExpenseSplit", back_populates="expense", cascade="all, delete-orphan")


class ExpenseSplit(TimestampMixin, Base):
    __tablename__ = "expense_splits"

    id = Column(BigInteger, primary_key=True, index=True)
    expense_id = Column(BigInteger, ForeignKey("expenses.id"), nullable=False, index=True)
    member_id = Column(BigInteger, ForeignKey("members.id"), nullable=False, index=True)
    share_amount_original = Column(Numeric(14, 2), nullable=False)
    share_amount_inr = Column(Numeric(14, 2), nullable=False)
    split_basis = Column(String(80), nullable=False)

    expense = relationship("Expense", back_populates="splits")


class Settlement(TimestampMixin, Base):
    __tablename__ = "settlements"

    id = Column(BigInteger, primary_key=True, index=True)
    group_id = Column(BigInteger, ForeignKey("groups.id"), nullable=False, index=True)
    import_row_id = Column(BigInteger, ForeignKey("import_rows.id"), nullable=True, unique=True)
    paid_by_member_id = Column(BigInteger, ForeignKey("members.id"), nullable=False)
    paid_to_member_id = Column(BigInteger, ForeignKey("members.id"), nullable=False)
    settlement_date = Column(Date, nullable=False)
    amount_original = Column(Numeric(14, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    exchange_rate_to_inr = Column(Numeric(14, 6), nullable=False)
    amount_inr = Column(Numeric(14, 2), nullable=False)
    notes = Column(Text, nullable=True)

    group = relationship("Group", back_populates="settlements")
    import_row = relationship("ImportRow", back_populates="settlement")
