"""Inventory models."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.bd.database import Base


class InvGroup(Base):
    __tablename__ = "inv_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    categories: Mapped[list["InvCategory"]] = relationship(
        "InvCategory", back_populates="group", cascade="all, delete-orphan"
    )
    items: Mapped[list["InvItem"]] = relationship(
        "InvItem", back_populates="group", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - convenience representation
        return f"<InvGroup id={self.id} name={self.name!r}>"


class InvCategory(Base):
    __tablename__ = "inv_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("inv_groups.id", ondelete="RESTRICT"), nullable=False, index=True)

    group: Mapped["InvGroup"] = relationship("InvGroup", back_populates="categories")
    kinds: Mapped[list["InvKind"]] = relationship(
        "InvKind", back_populates="category", cascade="all, delete-orphan"
    )
    items: Mapped[list["InvItem"]] = relationship(
        "InvItem", back_populates="category", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("name", "group_id", name="uq_inv_categories_name_group"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<InvCategory id={self.id} name={self.name!r} group_id={self.group_id}>"


class InvKind(Base):
    __tablename__ = "inv_kinds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inv_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inv_groups.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    category: Mapped["InvCategory"] = relationship("InvCategory", back_populates="kinds")
    group: Mapped["InvGroup"] = relationship("InvGroup")
    items: Mapped[list["InvItem"]] = relationship(
        "InvItem", back_populates="kind", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("name", "category_id", name="uq_inv_kinds_name_category"),
        Index("ix_inv_kinds_group_category", "group_id", "category_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<InvKind id={self.id} name={self.name!r} category_id={self.category_id} group_id={self.group_id}>"


class InvItem(Base):
    __tablename__ = "inv_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("inv_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("inv_groups.id", ondelete="RESTRICT"), nullable=False, index=True)
    kind_id: Mapped[int] = mapped_column(Integer, ForeignKey("inv_kinds.id", ondelete="RESTRICT"), nullable=False, index=True)
    cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    default_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    use_instance_codes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    category: Mapped["InvCategory"] = relationship("InvCategory", back_populates="items")
    group: Mapped["InvGroup"] = relationship("InvGroup", back_populates="items")
    kind: Mapped["InvKind"] = relationship("InvKind", back_populates="items")
    records: Mapped[list["InvItemRecord"]] = relationship(
        "InvItemRecord", back_populates="item", cascade="all, delete-orphan"
    )
    instances: Mapped[list["InvItemInstance"]] = relationship(
        "InvItemInstance", back_populates="item", cascade="all, delete-orphan"
    )
    instance_events: Mapped[list["InvItemInstanceEvent"]] = relationship(
        "InvItemInstanceEvent", back_populates="item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("code", name="uq_inv_items_code"),
        UniqueConstraint("name", "category_id", name="uq_inv_items_name_category"),
        Index("ix_inv_items_group_category", "group_id", "category_id"),
        Index("ix_inv_items_group_category_kind", "group_id", "category_id", "kind_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<InvItem id={self.id} name={self.name!r} cat={self.category_id} grp={self.group_id}>"


class InvItemRecord(Base):
    __tablename__ = "inv_item_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("inv_items.id", ondelete="RESTRICT"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("inv_categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("inv_groups.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    restaurant_id: Mapped[int] = mapped_column(Integer, ForeignKey("restaurants.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    item: Mapped["InvItem"] = relationship("InvItem", back_populates="records")
    category: Mapped["InvCategory"] = relationship("InvCategory")
    group: Mapped["InvGroup"] = relationship("InvGroup")

    __table_args__ = (
        Index("ix_inv_item_records_restaurant_created", "restaurant_id", "created_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<InvItemRecord id={self.id} item={self.item_id} rest={self.restaurant_id} at={self.created_at}>"


class InvItemStock(Base):
    __tablename__ = "inv_item_stock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(Integer, ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("inv_items.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("restaurant_id", "item_id", name="uq_inv_item_stock_rest_item"),
        Index("ix_inv_item_stock_rest_item", "restaurant_id", "item_id"),
    )


class InvItemChange(Base):
    __tablename__ = "inv_item_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("inv_items.id", ondelete="CASCADE"), nullable=False, index=True)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class InvItemInstance(Base):
    __tablename__ = "inv_item_instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("inv_items.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    instance_code: Mapped[str | None] = mapped_column(String(80), nullable=True, unique=True, index=True)
    purchase_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    location_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="warehouse")
    restaurant_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    storage_place_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("inv_storage_places.id", ondelete="SET NULL"), nullable=True, index=True
    )
    subdivision_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurant_subdivisions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    arrived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    item: Mapped["InvItem"] = relationship("InvItem", back_populates="instances")
    events: Mapped[list["InvItemInstanceEvent"]] = relationship(
        "InvItemInstanceEvent", back_populates="instance"
    )

    __table_args__ = (
        UniqueConstraint("item_id", "sequence_no", name="uq_inv_item_instances_item_seq"),
        Index("ix_inv_item_instances_kind_rest", "location_kind", "restaurant_id"),
        Index("ix_inv_item_instances_rest_place", "restaurant_id", "storage_place_id"),
        Index("ix_inv_item_instances_kind_sub", "location_kind", "subdivision_id"),
    )


class InvItemInstanceEvent(Base):
    __tablename__ = "inv_item_instance_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    actor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inv_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instance_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("inv_item_instances.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sequence_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    instance_code_snapshot: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    purchase_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    from_location_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    from_restaurant_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    from_storage_place_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("inv_storage_places.id", ondelete="SET NULL"), nullable=True, index=True
    )
    from_subdivision_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurant_subdivisions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    to_location_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_restaurant_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    to_storage_place_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("inv_storage_places.id", ondelete="SET NULL"), nullable=True, index=True
    )
    to_subdivision_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurant_subdivisions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    item: Mapped["InvItem"] = relationship("InvItem", back_populates="instance_events")
    instance: Mapped["InvItemInstance | None"] = relationship("InvItemInstance", back_populates="events")

    __table_args__ = (
        Index("ix_inv_item_instance_events_item_created", "item_id", "created_at"),
        Index("ix_inv_item_instance_events_code_created", "instance_code_snapshot", "created_at"),
        Index("ix_inv_item_instance_events_action_created", "action_type", "created_at"),
        Index("ix_inv_item_instance_events_to_rest", "to_location_kind", "to_restaurant_id"),
        Index("ix_inv_item_instance_events_from_rest", "from_location_kind", "from_restaurant_id"),
        Index("ix_inv_item_instance_events_to_place", "to_storage_place_id", "created_at"),
        Index("ix_inv_item_instance_events_from_place", "from_storage_place_id", "created_at"),
    )


class InvInstanceEventType(Base):
    __tablename__ = "inv_instance_event_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    status_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_inv_instance_event_types_manual_active", "is_manual", "is_active"),
        Index("ix_inv_instance_event_types_sort", "sort_order", "name"),
    )


class InvStoragePlace(Base):
    __tablename__ = "inv_storage_places"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="restaurant", server_default="restaurant")
    restaurant_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_inv_storage_places_scope_sort", "scope_kind", "sort_order", "name"),
    )


class InvMovementEvent(Base):
    __tablename__ = "inv_movement_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    actor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    item_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("inv_items.id", ondelete="SET NULL"), nullable=True, index=True
    )
    item_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    item_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    group_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("inv_groups.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("inv_categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("inv_kinds.id", ondelete="SET NULL"), nullable=True, index=True
    )

    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    from_location_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    from_restaurant_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    from_storage_place_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("inv_storage_places.id", ondelete="SET NULL"), nullable=True, index=True
    )
    from_subdivision_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurant_subdivisions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    to_location_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_restaurant_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    to_storage_place_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("inv_storage_places.id", ondelete="SET NULL"), nullable=True, index=True
    )
    to_subdivision_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("restaurant_subdivisions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    field: Mapped[str | None] = mapped_column(String(64), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_inv_movement_events_created_at", "created_at"),
        Index("ix_inv_movement_events_item_created", "item_id", "created_at"),
        Index("ix_inv_movement_events_action_created", "action_type", "created_at"),
        Index("ix_inv_movement_events_from_rest", "from_location_kind", "from_restaurant_id"),
        Index("ix_inv_movement_events_to_rest", "to_location_kind", "to_restaurant_id"),
        Index("ix_inv_movement_events_from_place", "from_storage_place_id", "created_at"),
        Index("ix_inv_movement_events_to_place", "to_storage_place_id", "created_at"),
        Index("ix_inv_movement_events_from_sub", "from_location_kind", "from_subdivision_id"),
        Index("ix_inv_movement_events_to_sub", "to_location_kind", "to_subdivision_id"),
    )
