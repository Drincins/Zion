"""Inventory schemas."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Literal

from pydantic import BaseModel, ConfigDict, Field


class InvGroupBase(BaseModel):
    name: str


class InvGroupCreate(InvGroupBase):
    pass


class InvGroupUpdate(BaseModel):
    name: Optional[str] = None


class InvGroupRead(InvGroupBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class InvCategoryBase(BaseModel):
    name: str
    group_id: int


class InvCategoryCreate(InvCategoryBase):
    pass


class InvCategoryUpdate(BaseModel):
    name: Optional[str] = None
    group_id: Optional[int] = None


class InvCategoryRead(InvCategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class InvKindBase(BaseModel):
    name: str
    category_id: int
    group_id: int


class InvKindCreate(InvKindBase):
    pass


class InvKindUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    group_id: Optional[int] = None


class InvKindRead(InvKindBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class InvItemBase(BaseModel):
    code: Optional[str] = None
    name: str
    category_id: int
    group_id: int
    kind_id: Optional[int] = None
    cost: Decimal
    default_cost: Optional[Decimal] = None
    note: Optional[str] = None
    manufacturer: Optional[str] = None
    storage_conditions: Optional[str] = None
    photo_url: Optional[str] = None
    use_instance_codes: bool = True
    is_active: bool = True


class InvItemCreate(InvItemBase):
    initial_quantity: Optional[int] = 0
    initial_location_kind: Optional[Literal["warehouse", "restaurant", "subdivision"]] = None
    initial_restaurant_id: Optional[int] = None
    initial_storage_place_id: Optional[int] = None
    initial_subdivision_id: Optional[int] = None


class InvItemUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    category_id: Optional[int] = None
    group_id: Optional[int] = None
    kind_id: Optional[int] = None
    cost: Optional[Decimal] = None
    default_cost: Optional[Decimal] = None
    photo_url: Optional[str] = None
    note: Optional[str] = None
    manufacturer: Optional[str] = None
    storage_conditions: Optional[str] = None
    use_instance_codes: Optional[bool] = None
    is_active: Optional[bool] = None


class InvItemLocationSummary(BaseModel):
    location_kind: Literal["warehouse", "restaurant", "subdivision"]
    restaurant_id: Optional[int] = None
    storage_place_id: Optional[int] = None
    storage_place_name: Optional[str] = None
    subdivision_id: Optional[int] = None
    location_name: str
    quantity: int
    avg_cost: Optional[Decimal] = None
    last_arrival_at: Optional[datetime] = None


class InvItemRead(InvItemBase):
    id: int
    created_at: datetime
    photo_key: Optional[str] = None
    kind_name: Optional[str] = None
    total_quantity: int = 0
    warehouse_quantity: int = 0
    location_totals: List[InvItemLocationSummary] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class InvItemRecordBase(BaseModel):
    item_id: int
    category_id: int
    group_id: int
    restaurant_id: int
    user_id: Optional[int] = None
    quantity: int = 1
    cost: Decimal
    comment: Optional[str] = None
    photo_url: Optional[str] = None


class InvItemRecordCreate(InvItemRecordBase):
    pass


class InvItemRecordUpdate(BaseModel):
    item_id: Optional[int] = None
    category_id: Optional[int] = None
    group_id: Optional[int] = None
    restaurant_id: Optional[int] = None
    user_id: Optional[int] = None
    quantity: Optional[int] = None
    cost: Optional[Decimal] = None
    photo_url: Optional[str] = None


class InvItemRecordRead(InvItemRecordBase):
    id: int
    created_at: datetime
    photo_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InventoryBalanceItem(BaseModel):
    item_id: int
    item_name: str
    total_quantity: int
    total_cost: Decimal
    record_count: int


class InventoryBalance(BaseModel):
    restaurant_id: int
    total_quantity: int
    total_cost: Decimal
    record_count: int
    items: List[InventoryBalanceItem]


class InvItemChangeRead(BaseModel):
    id: int
    item_id: int
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: Optional[int] = None
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryDepartmentOption(BaseModel):
    id: str
    type: Literal["meta", "warehouse", "restaurant", "subdivision"]
    label: str
    restaurant_id: Optional[int] = None
    subdivision_id: Optional[int] = None


class InvItemTransferCreate(BaseModel):
    source_kind: Optional[Literal["warehouse", "restaurant", "subdivision"]] = "warehouse"
    source_restaurant_id: Optional[int] = None
    source_storage_place_id: Optional[int] = None
    source_subdivision_id: Optional[int] = None
    target_kind: Literal["warehouse", "restaurant", "subdivision"]
    quantity: int
    restaurant_id: Optional[int] = None
    storage_place_id: Optional[int] = None
    subdivision_id: Optional[int] = None
    comment: Optional[str] = None


class InvItemTransferRead(BaseModel):
    item_id: int
    moved: int
    source_kind: Literal["warehouse", "restaurant", "subdivision"]
    target_kind: Literal["warehouse", "restaurant", "subdivision"]
    source_restaurant_id: Optional[int] = None
    source_storage_place_id: Optional[int] = None
    source_subdivision_id: Optional[int] = None
    restaurant_id: Optional[int] = None
    storage_place_id: Optional[int] = None
    subdivision_id: Optional[int] = None
    instance_codes: List[str]


class InvItemAllocateCreate(BaseModel):
    location_kind: Literal["warehouse", "restaurant", "subdivision"]
    restaurant_id: Optional[int] = None
    storage_place_id: Optional[int] = None
    subdivision_id: Optional[int] = None
    quantity: int = Field(ge=1)
    unit_cost: Optional[Decimal] = None
    comment: Optional[str] = None


class InvItemAllocateRead(BaseModel):
    item_id: int
    location_kind: Literal["warehouse", "restaurant", "subdivision"]
    restaurant_id: Optional[int] = None
    storage_place_id: Optional[int] = None
    subdivision_id: Optional[int] = None
    added: int
    unit_cost: Decimal
    instance_codes: List[str]


class InvItemQuantityUpdate(BaseModel):
    location_kind: Literal["warehouse", "restaurant", "subdivision"]
    restaurant_id: Optional[int] = None
    storage_place_id: Optional[int] = None
    subdivision_id: Optional[int] = None
    quantity: int = Field(ge=0)
    unit_cost: Optional[Decimal] = None
    comment: Optional[str] = None


class InvItemQuantityUpdateRead(BaseModel):
    item_id: int
    location_kind: Literal["warehouse", "restaurant", "subdivision"]
    restaurant_id: Optional[int] = None
    storage_place_id: Optional[int] = None
    subdivision_id: Optional[int] = None
    previous_quantity: int
    quantity: int
    delta: int


class InventoryMovementActionOption(BaseModel):
    value: str
    label: str


class InvMovementEventRead(BaseModel):
    id: int
    created_at: datetime
    action_type: str
    action_label: str
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    item_id: Optional[int] = None
    item_code: Optional[str] = None
    item_name: Optional[str] = None
    group_id: Optional[int] = None
    group_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    kind_id: Optional[int] = None
    kind_name: Optional[str] = None
    quantity: Optional[int] = None
    from_location_kind: Optional[str] = None
    from_restaurant_id: Optional[int] = None
    from_storage_place_id: Optional[int] = None
    from_subdivision_id: Optional[int] = None
    from_location_name: Optional[str] = None
    to_location_kind: Optional[str] = None
    to_restaurant_id: Optional[int] = None
    to_storage_place_id: Optional[int] = None
    to_subdivision_id: Optional[int] = None
    to_location_name: Optional[str] = None
    field: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    comment: Optional[str] = None


class InventoryRestaurantItemArrivalRead(BaseModel):
    id: int
    created_at: datetime
    action_type: str
    action_label: str
    actor_name: Optional[str] = None
    quantity: int = 0
    source_location_name: Optional[str] = None
    target_location_name: Optional[str] = None
    comment: Optional[str] = None


class InventoryItemInstanceSummaryRead(BaseModel):
    instance_id: Optional[int] = None
    instance_code: str
    sequence_no: Optional[int] = None
    purchase_cost: Optional[Decimal] = None
    arrived_at: Optional[datetime] = None
    is_current: bool = False
    current_location_name: Optional[str] = None
    current_storage_place_id: Optional[int] = None
    current_storage_place_name: Optional[str] = None
    status_key: str = "history"
    status_label: str = "История"
    last_event_at: Optional[datetime] = None
    last_event_action: Optional[str] = None
    last_event_label: Optional[str] = None
    last_comment: Optional[str] = None


class InventoryItemInstanceEventRead(BaseModel):
    id: int
    created_at: datetime
    action_type: str
    action_label: str
    actor_name: Optional[str] = None
    instance_id: Optional[int] = None
    instance_code: Optional[str] = None
    purchase_cost: Optional[Decimal] = None
    from_storage_place_id: Optional[int] = None
    from_location_name: Optional[str] = None
    to_storage_place_id: Optional[int] = None
    to_location_name: Optional[str] = None
    comment: Optional[str] = None


class InventoryItemInstanceEventCreate(BaseModel):
    event_type_id: int
    comment: Optional[str] = None


class InventoryRestaurantItemCardRead(BaseModel):
    item_id: int
    restaurant_id: int
    quantity: int
    avg_cost: Optional[Decimal] = None
    last_arrival_at: Optional[datetime] = None
    storage_place_id: Optional[int] = None
    instance_tracking_enabled: bool = False
    arrivals: List[InventoryRestaurantItemArrivalRead] = Field(default_factory=list)
    instances: List[InventoryItemInstanceSummaryRead] = Field(default_factory=list)


class InventoryInstanceEventTypeBase(BaseModel):
    code: Optional[str] = None
    name: str
    description: Optional[str] = None
    is_active: bool = True
    is_manual: bool = False
    status_key: Optional[str] = None
    status_label: Optional[str] = None
    sort_order: int = 100


class InventoryInstanceEventTypeCreate(InventoryInstanceEventTypeBase):
    pass


class InventoryInstanceEventTypeUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_manual: Optional[bool] = None
    status_key: Optional[str] = None
    status_label: Optional[str] = None
    sort_order: Optional[int] = None


class InventoryInstanceEventTypeRead(InventoryInstanceEventTypeBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryStoragePlaceBase(BaseModel):
    name: str
    scope_kind: Literal["restaurant"] = "restaurant"
    restaurant_id: Optional[int] = None
    description: Optional[str] = None
    is_active: bool = True
    sort_order: int = 100


class InventoryStoragePlaceCreate(InventoryStoragePlaceBase):
    pass


class InventoryStoragePlaceUpdate(BaseModel):
    name: Optional[str] = None
    scope_kind: Optional[Literal["restaurant"]] = None
    restaurant_id: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class InventoryStoragePlaceRead(InventoryStoragePlaceBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
