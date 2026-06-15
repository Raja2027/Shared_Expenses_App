from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Group name must contain at least two characters.")
        return cleaned


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_by_user_id: int
    created_at: datetime


class MemberAliasCreateRequest(BaseModel):
    raw_name: str = Field(min_length=1, max_length=120)
    normalized_name: str | None = Field(default=None, max_length=120)

    @field_validator("raw_name", "normalized_name")
    @classmethod
    def clean_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Name cannot be blank.")
        return cleaned


class MemberAliasResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    raw_name: str
    normalized_name: str


class MembershipBase(BaseModel):
    joined_on: date
    left_on: date | None = None

    @model_validator(mode="after")
    def validate_date_window(self):
        if self.left_on is not None and self.left_on < self.joined_on:
            raise ValueError("left_on cannot be before joined_on.")
        return self


class MembershipCreateRequest(MembershipBase):
    pass


class MembershipUpdateRequest(BaseModel):
    joined_on: date | None = None
    left_on: date | None = None

    @model_validator(mode="after")
    def validate_date_window(self):
        if self.joined_on is not None and self.left_on is not None and self.left_on < self.joined_on:
            raise ValueError("left_on cannot be before joined_on.")
        return self


class GroupMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    joined_on: date
    left_on: date | None


class MemberCreateRequest(MembershipBase):
    display_name: str = Field(min_length=1, max_length=120)
    member_type: str = Field(default="flatmate", min_length=1, max_length=40)
    aliases: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("display_name", "member_type")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Value cannot be blank.")
        return cleaned

    @field_validator("aliases")
    @classmethod
    def clean_aliases(cls, values: list[str]) -> list[str]:
        cleaned_aliases = []
        seen = set()
        for value in values:
            cleaned = " ".join(value.split())
            if cleaned and cleaned.lower() not in seen:
                cleaned_aliases.append(cleaned)
                seen.add(cleaned.lower())
        return cleaned_aliases


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    display_name: str
    member_type: str
    created_at: datetime
    aliases: list[MemberAliasResponse] = []
    memberships: list[GroupMembershipResponse] = []
