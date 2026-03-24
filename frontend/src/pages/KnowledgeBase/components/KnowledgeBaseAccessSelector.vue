<template>
    <section class="kb-access-selector">
        <p class="kb-access-selector__hint">
            Если ничего не выбрано, папка доступна всем пользователям с доступом к Базе знаний.
        </p>
        <div v-if="selectedGroups.length" class="kb-access-selector__selected">
            <h4 class="kb-access-selector__selected-title">Выбрано</h4>
            <div class="kb-access-selector__selected-groups">
                <div
                    v-for="group in selectedGroups"
                    :key="`selected-${group.key}`"
                    class="kb-access-selector__selected-group"
                >
                    <p class="kb-access-selector__selected-label">{{ group.label }}</p>
                    <div class="kb-access-selector__chips">
                        <button
                            v-for="item in group.items"
                            :key="`selected-${group.key}-${item.id}`"
                            type="button"
                            class="kb-access-selector__chip"
                            :disabled="disabled"
                            @click="toggle(group.scopeKey, item.id, false)"
                        >
                            <span class="kb-access-selector__chip-text">{{ item.name }}</span>
                            <span class="kb-access-selector__chip-close">×</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
        <div class="kb-access-selector__grid">
            <div class="kb-access-selector__group">
                <h4 class="kb-access-selector__title">Рестораны</h4>
                <div class="kb-access-selector__search-wrap">
                    <input
                        v-model.trim="searchRestaurant"
                        type="text"
                        class="kb-access-selector__search"
                        placeholder="Поиск ресторана"
                        :disabled="disabled"
                    >
                </div>
                <div class="kb-access-selector__list">
                    <label v-for="item in filteredRestaurantOptions" :key="`restaurant-${item.id}`" class="kb-access-selector__option">
                        <input
                            type="checkbox"
                            :checked="isChecked('restaurant_ids', item.id)"
                            :disabled="disabled"
                            @change="toggle('restaurant_ids', item.id, $event.target.checked)"
                        >
                        <span>{{ item.name }}</span>
                    </label>
                    <p v-if="!restaurantOptions.length" class="kb-access-selector__empty">Нет ресторанов</p>
                    <p v-else-if="!filteredRestaurantOptions.length" class="kb-access-selector__empty">Ничего не найдено</p>
                </div>
            </div>

            <div class="kb-access-selector__group">
                <h4 class="kb-access-selector__title">Должности</h4>
                <div class="kb-access-selector__search-wrap">
                    <input
                        v-model.trim="searchPosition"
                        type="text"
                        class="kb-access-selector__search"
                        placeholder="Поиск должности"
                        :disabled="disabled"
                    >
                </div>
                <div class="kb-access-selector__list">
                    <label v-for="item in filteredPositionOptions" :key="`position-${item.id}`" class="kb-access-selector__option">
                        <input
                            type="checkbox"
                            :checked="isChecked('position_ids', item.id)"
                            :disabled="disabled"
                            @change="toggle('position_ids', item.id, $event.target.checked)"
                        >
                        <span>{{ item.name }}</span>
                    </label>
                    <p v-if="!positionOptions.length" class="kb-access-selector__empty">Нет должностей</p>
                    <p v-else-if="hasRestaurantFilter && !scopedPositionOptions.length" class="kb-access-selector__empty">
                        Нет должностей для выбранных ресторанов
                    </p>
                    <p v-else-if="!filteredPositionOptions.length" class="kb-access-selector__empty">Ничего не найдено</p>
                </div>
            </div>

            <div class="kb-access-selector__group">
                <h4 class="kb-access-selector__title">Сотрудники</h4>
                <div class="kb-access-selector__search-wrap">
                    <input
                        v-model.trim="searchUser"
                        type="text"
                        class="kb-access-selector__search"
                        placeholder="Поиск сотрудника"
                        :disabled="disabled"
                    >
                </div>
                <div class="kb-access-selector__list">
                    <label v-for="item in filteredUserOptions" :key="`user-${item.id}`" class="kb-access-selector__option">
                        <input
                            type="checkbox"
                            :checked="isChecked('user_ids', item.id)"
                            :disabled="disabled"
                            @change="toggle('user_ids', item.id, $event.target.checked)"
                        >
                        <span>{{ item.name }}</span>
                    </label>
                    <p v-if="!userOptions.length" class="kb-access-selector__empty">Нет сотрудников</p>
                    <p v-else-if="hasUserScopeFilters && !scopedUserOptions.length" class="kb-access-selector__empty">
                        Нет сотрудников по выбранным фильтрам
                    </p>
                    <p v-else-if="!filteredUserOptions.length" class="kb-access-selector__empty">Ничего не найдено</p>
                </div>
            </div>
        </div>
    </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { areKnowledgeBaseAccessEqual, normalizeKnowledgeBaseAccess } from '../utils/access';

const props = defineProps({
    modelValue: {
        type: Object,
        default: () => ({
            role_ids: [],
            position_ids: [],
            user_ids: [],
            restaurant_ids: [],
        }),
    },
    options: {
        type: Object,
        default: () => ({
            roles: [],
            positions: [],
            users: [],
            restaurants: [],
        }),
    },
    disabled: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(['update:modelValue']);

const normalizeAccess = (value) => ({
    ...normalizeKnowledgeBaseAccess(value),
    role_ids: [],
});
const isSameAccess = areKnowledgeBaseAccessEqual;

const localValue = ref(normalizeAccess(props.modelValue));
const searchPosition = ref('');
const searchUser = ref('');
const searchRestaurant = ref('');

const positionOptions = computed(() => normalizeOptions(props.options?.positions));
const userOptions = computed(() => normalizeOptions(props.options?.users));
const restaurantOptions = computed(() => normalizeOptions(props.options?.restaurants));
const positionOptionsMap = computed(() => toOptionsMap(positionOptions.value));
const userOptionsMap = computed(() => toOptionsMap(userOptions.value));
const restaurantOptionsMap = computed(() => toOptionsMap(restaurantOptions.value));

const selectedRestaurantIdSet = computed(() => new Set(localValue.value?.restaurant_ids || []));
const selectedPositionIdSet = computed(() => new Set(localValue.value?.position_ids || []));

const hasRestaurantFilter = computed(() => selectedRestaurantIdSet.value.size > 0);
const hasUserScopeFilters = computed(() => hasRestaurantFilter.value || selectedPositionIdSet.value.size > 0);

const scopedPositionOptions = computed(() => {
    if (!hasRestaurantFilter.value) {
        return positionOptions.value;
    }
    return positionOptions.value.filter((item) =>
        item.restaurantIds.some((restaurantId) => selectedRestaurantIdSet.value.has(restaurantId)),
    );
});

const scopedUserOptions = computed(() => {
    let list = userOptions.value;
    if (hasRestaurantFilter.value) {
        list = list.filter((item) =>
            item.restaurantIds.some((restaurantId) => selectedRestaurantIdSet.value.has(restaurantId)),
        );
    }
    if (selectedPositionIdSet.value.size) {
        list = list.filter((item) =>
            Number.isFinite(item.positionId) && selectedPositionIdSet.value.has(item.positionId),
        );
    }
    return list;
});

const filteredPositionOptions = computed(() => filterOptions(scopedPositionOptions.value, searchPosition.value));
const filteredUserOptions = computed(() => filterOptions(scopedUserOptions.value, searchUser.value));
const filteredRestaurantOptions = computed(() => filterOptions(restaurantOptions.value, searchRestaurant.value));
const selectedGroups = computed(() => buildSelectedGroups());

const scopedPositionIds = computed(() => scopedPositionOptions.value.map((item) => item.id));
const scopedUserIds = computed(() => scopedUserOptions.value.map((item) => item.id));

watch(
    () => props.modelValue,
    (nextValue) => {
        const normalized = normalizeAccess(nextValue);
        if (!isSameAccess(localValue.value, normalized)) {
            localValue.value = normalized;
        }
    },
    { immediate: true, deep: true },
);

watch(
    localValue,
    (nextValue) => {
        const normalized = normalizeAccess(nextValue);
        if (!isSameAccess(normalized, props.modelValue)) {
            emit('update:modelValue', normalized);
        }
    },
    { deep: true },
);

watch(
    [scopedPositionIds, scopedUserIds],
    () => {
        const next = normalizeAccess(localValue.value);
        const allowedPositionIds = new Set(scopedPositionIds.value);
        const allowedUserIds = new Set(scopedUserIds.value);

        const nextPositionIds = (next.position_ids || []).filter((id) => allowedPositionIds.has(Number(id)));
        const nextUserIds = (next.user_ids || []).filter((id) => allowedUserIds.has(Number(id)));

        const positionChanged = nextPositionIds.length !== (next.position_ids || []).length;
        const usersChanged = nextUserIds.length !== (next.user_ids || []).length;
        if (!positionChanged && !usersChanged) {
            return;
        }

        next.position_ids = nextPositionIds;
        next.user_ids = nextUserIds;
        localValue.value = next;
    },
    { immediate: true },
);

function normalizeOptions(value) {
    if (!Array.isArray(value)) {
        return [];
    }
    return value
        .map((item) => ({
            id: Number(item?.id),
            name: String(item?.name || '').trim(),
            restaurantIds: normalizeIdList(item?.restaurant_ids),
            positionId: normalizeSingleId(item?.position_id),
        }))
        .filter((item) => Number.isFinite(item.id) && item.id > 0);
}

function normalizeIdList(value) {
    if (!Array.isArray(value)) {
        return [];
    }
    const unique = new Set();
    value.forEach((item) => {
        const parsed = Number(item);
        if (Number.isFinite(parsed) && parsed > 0) {
            unique.add(parsed);
        }
    });
    return Array.from(unique).sort((a, b) => a - b);
}

function normalizeSingleId(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) {
        return null;
    }
    return parsed;
}

function toOptionsMap(list) {
    return Object.fromEntries((list || []).map((item) => [item.id, item]));
}

function filterOptions(options, query) {
    const q = String(query || '').trim().toLowerCase();
    if (!q) {
        return options;
    }
    return options.filter((item) => String(item.name || '').toLowerCase().includes(q));
}

function resolveSelectedItems(scopeKey, optionsMap) {
    const ids = localValue.value?.[scopeKey] || [];
    return ids.map((id) => {
        const numericId = Number(id);
        const found = optionsMap[numericId];
        if (found) {
            return found;
        }
        return {
            id: numericId,
            name: `ID ${numericId}`,
        };
    });
}

function buildSelectedGroups() {
    const groups = [
        {
            key: 'restaurants',
            label: 'Рестораны',
            scopeKey: 'restaurant_ids',
            items: resolveSelectedItems('restaurant_ids', restaurantOptionsMap.value),
        },
        {
            key: 'positions',
            label: 'Должности',
            scopeKey: 'position_ids',
            items: resolveSelectedItems('position_ids', positionOptionsMap.value),
        },
        {
            key: 'users',
            label: 'Сотрудники',
            scopeKey: 'user_ids',
            items: resolveSelectedItems('user_ids', userOptionsMap.value),
        },
    ];
    return groups.filter((group) => group.items.length > 0);
}

function isChecked(scopeKey, optionId) {
    return localValue.value?.[scopeKey]?.includes(Number(optionId));
}

function toggle(scopeKey, optionId, checked) {
    const next = normalizeAccess(localValue.value);
    const targetId = Number(optionId);
    const items = new Set(next[scopeKey] || []);
    if (checked) {
        items.add(targetId);
    } else {
        items.delete(targetId);
    }
    next[scopeKey] = Array.from(items).sort((a, b) => a - b);
    localValue.value = next;
}
</script>

<style scoped lang="scss">
.kb-access-selector {
    display: flex;
    flex-direction: column-reverse;
    gap: 8px;
}

.kb-access-selector__hint {
    margin: 0;
    font-size: 12px;
    color: var(--color-text-secondary);
}

.kb-access-selector__selected {
    border: 1px solid color-mix(in srgb, var(--color-border) 72%, transparent);
    border-radius: 10px;
    background: color-mix(in srgb, var(--color-surface) 92%, transparent);
    padding: 8px 10px;
}

.kb-access-selector__selected-title {
    margin: 0 0 8px;
    font-size: 12px;
    color: var(--color-text-secondary);
}

.kb-access-selector__selected-groups {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.kb-access-selector__selected-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.kb-access-selector__selected-label {
    margin: 0;
    font-size: 12px;
    color: var(--color-text-secondary);
}

.kb-access-selector__chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.kb-access-selector__chip {
    border: 1px solid color-mix(in srgb, var(--color-primary) 42%, var(--color-border) 58%);
    border-radius: 999px;
    background: color-mix(in srgb, var(--color-primary) 12%, transparent);
    color: var(--color-text);
    padding: 4px 8px;
    font-size: 12px;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
}

.kb-access-selector__chip:disabled {
    opacity: 0.72;
    cursor: default;
}

.kb-access-selector__chip-close {
    font-size: 12px;
    line-height: 1;
    color: var(--color-text-secondary);
}

.kb-access-selector__grid {
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.kb-access-selector__group {
    border: 1px solid color-mix(in srgb, var(--color-border) 72%, transparent);
    border-radius: 10px;
    background: color-mix(in srgb, var(--color-surface) 92%, transparent);
    min-height: 112px;
    display: flex;
    flex-direction: column;
}

.kb-access-selector__title {
    margin: 0;
    padding: 8px 10px;
    font-size: 12px;
    color: var(--color-text-secondary);
    border-bottom: 1px solid color-mix(in srgb, var(--color-border) 62%, transparent);
}

.kb-access-selector__search-wrap {
    padding: 8px 10px 0;
}

.kb-access-selector__search {
    width: 100%;
    border: 1px solid color-mix(in srgb, var(--color-border) 72%, transparent);
    border-radius: 8px;
    background: color-mix(in srgb, var(--color-surface) 88%, transparent);
    color: var(--color-text);
    padding: 6px 8px;
    font-size: 12px;
}

.kb-access-selector__list {
    padding: 8px 10px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-height: 308px;
    overflow: auto;
}

.kb-access-selector__option {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    font-size: 13px;
    color: var(--color-text);
}

.kb-access-selector__empty {
    margin: 0;
    font-size: 12px;
    color: var(--color-text-secondary);
}

@media (max-width: $mobile) {
    .kb-access-selector__grid {
        grid-template-columns: 1fr;
    }
}
</style>
