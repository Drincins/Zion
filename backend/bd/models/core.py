"""Core domain models (users, roles, restaurants)."""
from __future__ import annotations

import hashlib
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from backend.bd.database import Base

GENDER_ENUM = Enum("male", "female", name="user_gender")


def hash_iiko_password_sha1(password: str) -> str:
    """Return SHA1 hash used for iiko integrations."""
    return hashlib.sha1(password.encode("utf-8")).hexdigest()


user_restaurants = Table(
    "user_restaurants",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("restaurant_id", Integer, ForeignKey("restaurants.id"), primary_key=True),
    Index("ix_user_restaurants_restaurant_id", "restaurant_id"),
)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    api_router = Column("code", String, nullable=False, unique=True)
    router_description = Column("name", String, nullable=False)
    comment = Column("description", String, nullable=True)
    display_name = Column(String, nullable=True)
    responsibility_zone = Column(String, nullable=True)

    position_links = relationship(
        "PositionPermission",
        back_populates="permission",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    user_links = relationship(
        "UserPermission",
        back_populates="permission",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    positions = relationship(
        "Position",
        secondary="position_permissions",
        viewonly=True,
        lazy="selectin",
    )
    role_links = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    roles = relationship(
        "Role",
        secondary="role_permissions",
        viewonly=True,
        lazy="selectin",
    )
    users = relationship(
        "User",
        secondary="user_permissions",
        viewonly=True,
        lazy="selectin",
    )

    # --- Backwards compatibility aliases -------------------------------------
    @property
    def code(self) -> str:
        return self.api_router

    @code.setter
    def code(self, value: str) -> None:
        self.api_router = value

    @property
    def name(self) -> str:
        return self.router_description

    @name.setter
    def name(self, value: str) -> None:
        self.router_description = value

    @property
    def description(self) -> str | None:
        return self.comment

    @description.setter
    def description(self, value: str | None) -> None:
        self.comment = value


class PositionPermission(Base):
    __tablename__ = "position_permissions"

    id = Column(Integer, primary_key=True)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)

    position = relationship("Position", back_populates="permission_links")
    permission = relationship("Permission", back_populates="position_links")

    __table_args__ = (
        UniqueConstraint("position_id", "permission_id", name="uq_position_permissions_position_permission"),
        Index("ix_position_permissions_permission_id", "permission_id"),
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)

    role = relationship("Role", back_populates="permission_links")
    permission = relationship("Permission", back_populates="role_links")

    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
        Index("ix_role_permissions_permission_id", "permission_id"),
    )


class UserPermission(Base):
    __tablename__ = "user_permissions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)

    user = relationship("User", back_populates="permission_links")
    permission = relationship("Permission", back_populates="user_links")

    __table_args__ = (
        UniqueConstraint("user_id", "permission_id", name="uq_user_permissions_user_permission"),
        Index("ix_user_permissions_permission_id", "permission_id"),
    )


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    users = relationship("User", back_populates="company")
    restaurants = relationship("Restaurant", back_populates="company")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    level = Column(Integer, nullable=False, default=0)
    comment = Column(String, nullable=True)

    users = relationship("User", back_populates="role")
    permission_links = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        viewonly=True,
        lazy="selectin",
    )


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        Index("ix_users_fired", "fired"),
        Index("ix_users_workplace_fired", "workplace_restaurant_id", "fired"),
        Index("ix_users_company_fired", "company_id", "fired"),
        Index("ix_users_role_id", "role_id"),
        Index("ix_users_name_order", text("lower(last_name)"), text("lower(first_name)"), "id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    iiko_id = Column(String, unique=True, nullable=True)
    telegram_id = Column(BigInteger, unique=True, nullable=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    middle_name = Column(String)
    phone_number = Column(String)
    email = Column(String, nullable=True)
    iiko_code = Column(String)
    employee_row_id = Column(String, nullable=True, index=True)

    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="users")

    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    role = relationship("Role", back_populates="users")

    restaurants = relationship(
        "Restaurant",
        secondary=user_restaurants,
        back_populates="users",
    )
    workplace_restaurant_id = Column(
        Integer,
        ForeignKey("restaurants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    workplace_restaurant = relationship(
        "Restaurant",
        foreign_keys=[workplace_restaurant_id],
    )

    position_id = Column(Integer, ForeignKey("positions.id", ondelete="SET NULL"), nullable=True, index=True)
    rate = Column(Numeric(10, 2), nullable=True)
    individual_rate = Column(Numeric(10, 2), nullable=True)
    hire_date = Column(Date, nullable=True)
    fire_date = Column(Date, nullable=True)
    fired = Column(Boolean, nullable=False, default=False)
    staff_code = Column(String, nullable=True, unique=True)
    has_fingerprint = Column(Boolean, nullable=False, default=False)
    birth_date = Column(Date, nullable=True)
    photo_key = Column(String, nullable=True)
    gender = Column(GENDER_ENUM, nullable=True)
    is_cis_employee = Column(Boolean, nullable=False, default=False)
    is_formalized = Column(Boolean, nullable=False, server_default="false")
    has_full_restaurant_access = Column(Boolean, nullable=False, default=False)
    confidential_data_consent = Column(Boolean, nullable=False, default=False)

    position = relationship("Position", back_populates="users")
    attendances = relationship("Attendance", back_populates="user", cascade="all, delete-orphan")
    payroll_adjustments = relationship(
        "PayrollAdjustment",
        foreign_keys="PayrollAdjustment.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    payroll_adjustments_entered = relationship(
        "PayrollAdjustment",
        foreign_keys="PayrollAdjustment.responsible_id",
        back_populates="responsible",
    )
    salary_results = relationship(
        "PayrollSalaryResult",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="PayrollSalaryResult.user_id",
    )
    advance_statements_created = relationship(
        "PayrollAdvanceStatement",
        foreign_keys="PayrollAdvanceStatement.created_by_id",
        back_populates="created_by",
    )
    advance_statements_updated = relationship(
        "PayrollAdvanceStatement",
        foreign_keys="PayrollAdvanceStatement.updated_by_id",
        back_populates="updated_by",
    )
    training_events = relationship(
        "TrainingEventRecord",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    permission_links = relationship(
        "UserPermission",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    direct_permissions = relationship(
        "Permission",
        secondary="user_permissions",
        viewonly=True,
        lazy="selectin",
    )
    medical_check_records = relationship(
        "MedicalCheckRecord",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    cis_document_records = relationship(
        "CisDocumentRecord",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def has_global_access(self) -> bool:
        """Return True when the user should have unrestricted access."""
        from backend.services.permissions import has_global_access as _has_global_access

        return _has_global_access(self)

    @property
    def permission_codes(self) -> list[str]:
        """Return normalized permission codes available to the user."""
        from backend.services.permissions import get_user_permission_codes

        return sorted(get_user_permission_codes(self))


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    server = Column(String, nullable=False)
    department_code = Column(String, nullable=True, index=True)
    participates_in_sales = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    company_id = Column(Integer, ForeignKey("companies.id"))
    company = relationship("Company", back_populates="restaurants")

    iiko_login = Column(String, nullable=True)
    iiko_password_sha1 = Column(String, nullable=True)

    users = relationship(
        "User",
        secondary=user_restaurants,
        back_populates="restaurants",
    )

    attendances = relationship("Attendance", back_populates="restaurant")
