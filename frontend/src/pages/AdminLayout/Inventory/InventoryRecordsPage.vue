<template>
    <section class="inventory-page__section inventory-movements">
        <header class="inventory-movements__header">
            <div class="inventory-movements__header-main">
                <h1 class="inventory-movements__title">Журнал операций</h1>
                <p class="inventory-movements__subtitle">
                    История операций по складу с фильтрами по товарам, объектам, типам действий и сотрудникам.
                </p>
            </div>
            <div class="inventory-movements__header-actions">
                <router-link :to="{ name: 'inventory-balance' }" class="inventory-movements__back-link">
                    Назад
                </router-link>
                <Button color="ghost" size="sm" :loading="loading" @click="loadMovements">Обновить</Button>
            </div>
        </header>

        <section class="inventory-movements__filters-panel">
            <button class="inventory-movements__filters-toggle" type="button" @click="isFiltersOpen = !isFiltersOpen">
                Фильтры
                <span :class="['inventory-movements__filters-icon', { 'is-open': isFiltersOpen }]">▼</span>
            </button>

            <form v-if="isFiltersOpen" class="inventory-movements__filters" @submit.prevent="loadMovements">
                <DateInput v-model="dateFrom" label="С даты" />
                <DateInput v-model="dateTo" label="По дату" />
                <Input
                    v-model="searchQuery"
                    label="Поиск"
                    placeholder="Код или название товара"
                />

            <div :ref="(el) => setFilterRef('catalog', el)" class="movements-multiselect">
                <label class="movements-multiselect__label">Товары и категории</label>
                <button type="button" class="movements-multiselect__trigger" @click="toggleDropdown('catalog')">
                    <span>{{ catalogFilterLabel }}</span>
                    <span>{{ dropdownState.catalog ? '▲' : '▼' }}</span>
                </button>
                <div v-if="dropdownState.catalog" class="movements-multiselect__menu">
                    <button type="button" class="movements-multiselect__clear" @click="clearSelection('catalog')">
                        Все товары и категории
                    </button>
                    <template v-for="group in groupedCatalogOptions" :key="`g:${group.id}`">
                        <div class="movements-catalog__row movements-catalog__row--group">
                            <button
                                v-if="group.categories.length"
                                type="button"
                                class="movements-catalog__toggle"
                                @click="toggleCatalogGroup(group.id)"
                            >
                                {{ isCatalogGroupExpanded(group.id) ? '⌄' : '›' }}
                            </button>
                            <span v-else class="movements-catalog__toggle movements-catalog__toggle--placeholder" />
                            <label class="movements-multiselect__option">
                                <input
                                    type="checkbox"
                                    :checked="selectedFilters.catalog.includes(`g:${group.id}`)"
                                    @change="toggleSelection('catalog', `g:${group.id}`)"
                                />
                                <span>{{ group.name }}</span>
                            </label>
                        </div>
                        <template v-if="isCatalogGroupExpanded(group.id)">
                            <template v-for="category in group.categories" :key="`c:${category.id}`">
                                <div class="movements-catalog__row movements-catalog__row--category">
                                    <button
                                        v-if="category.items.length"
                                        type="button"
                                        class="movements-catalog__toggle"
                                        @click="toggleCatalogCategory(category.id)"
                                    >
                                        {{ isCatalogCategoryExpanded(category.id) ? '⌄' : '›' }}
                                    </button>
                                    <span v-else class="movements-catalog__toggle movements-catalog__toggle--placeholder" />
                                    <label class="movements-multiselect__option">
                                        <input
                                            type="checkbox"
                                            :checked="selectedFilters.catalog.includes(`c:${category.id}`)"
                                            @change="toggleSelection('catalog', `c:${category.id}`)"
                                        />
                                        <span>{{ category.name }}</span>
                                    </label>
                                </div>
                                <template v-if="isCatalogCategoryExpanded(category.id)">
                                    <div
                                        v-for="item in category.items"
                                        :key="`i:${item.id}`"
                                        class="movements-catalog__row movements-catalog__row--item"
                                    >
                                        <span class="movements-catalog__toggle movements-catalog__toggle--placeholder" />
                                        <label class="movements-multiselect__option">
                                            <input
                                                type="checkbox"
                                                :checked="selectedFilters.catalog.includes(`i:${item.id}`)"
                                                @change="toggleSelection('catalog', `i:${item.id}`)"
                                            />
                                            <span>{{ item.code || `ITEM-${item.id}` }} · {{ item.name }}</span>
                                        </label>
                                    </div>
                                </template>
                            </template>
                        </template>
                    </template>
                </div>
            </div>

            <div :ref="(el) => setFilterRef('objects', el)" class="movements-multiselect">
                <label class="movements-multiselect__label">Объекты</label>
                <button type="button" class="movements-multiselect__trigger" @click="toggleDropdown('objects')">
                    <span>{{ objectFilterLabel }}</span>
                    <span>{{ dropdownState.objects ? '▲' : '▼' }}</span>
                </button>
                <div v-if="dropdownState.objects" class="movements-multiselect__menu">
                    <button type="button" class="movements-multiselect__clear" @click="clearSelection('objects')">
                        Все объекты
                    </button>
                    <label
                        v-for="option in objectOptions"
                        :key="option.value"
                        class="movements-multiselect__option"
                    >
                        <input
                            type="checkbox"
                            :checked="selectedFilters.objects.includes(option.value)"
                            @change="toggleSelection('objects', option.value)"
                        />
                        <span>{{ option.label }}</span>
                    </label>
                </div>
            </div>

            <div :ref="(el) => setFilterRef('actions', el)" class="movements-multiselect">
                <label class="movements-multiselect__label">Типы действий</label>
                <button type="button" class="movements-multiselect__trigger" @click="toggleDropdown('actions')">
                    <span>{{ actionFilterLabel }}</span>
                    <span>{{ dropdownState.actions ? '▲' : '▼' }}</span>
                </button>
                <div v-if="dropdownState.actions" class="movements-multiselect__menu">
                    <button type="button" class="movements-multiselect__clear" @click="clearSelection('actions')">
                        Все действия
                    </button>
                    <label
                        v-for="option in actionOptions"
                        :key="option.value"
                        class="movements-multiselect__option"
                    >
                        <input
                            type="checkbox"
                            :checked="selectedFilters.actions.includes(option.value)"
                            @change="toggleSelection('actions', option.value)"
                        />
                        <span>{{ option.label }}</span>
                    </label>
                </div>
            </div>

            <div :ref="(el) => setFilterRef('actors', el)" class="movements-multiselect">
                <label class="movements-multiselect__label">Сотрудники</label>
                <button type="button" class="movements-multiselect__trigger" @click="toggleDropdown('actors')">
                    <span>{{ actorFilterLabel }}</span>
                    <span>{{ dropdownState.actors ? '▲' : '▼' }}</span>
                </button>
                <div v-if="dropdownState.actors" class="movements-multiselect__menu">
                    <button type="button" class="movements-multiselect__clear" @click="clearSelection('actors')">
                        Все сотрудники
                    </button>
                    <label
                        v-for="option in actorOptions"
                        :key="option.value"
                        class="movements-multiselect__option"
                    >
                        <input
                            type="checkbox"
                            :checked="selectedFilters.actors.includes(option.value)"
                            @change="toggleSelection('actors', option.value)"
                        />
                        <span>{{ option.label }}</span>
                    </label>
                </div>
            </div>

                <div class="inventory-page__form-actions">
                    <Button type="submit" color="primary" size="sm" :loading="loading">Показать</Button>
                    <Button type="button" color="ghost" size="sm" :disabled="loading" @click="resetFilters">Сбросить</Button>
                </div>
            </form>
        </section>

        <p class="inventory-movements__summary">
            Записей: <strong>{{ movements.length }}</strong>
        </p>

        <div v-if="loading" class="inventory-page__loading">Загрузка движений...</div>
        <div v-else class="inventory-movements__table-area">
            <Table v-if="movements.length">
                <thead>
                    <tr>
                        <th>Дата (МСК)</th>
                        <th>Действие</th>
                        <th>Товар</th>
                        <th>Объект</th>
                        <th>Кол-во</th>
                        <th>Кто сделал</th>
                        <th>Детали</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="event in movements" :key="event.id">
                        <td>{{ formatDateTime(event.created_at) }}</td>
                        <td>
                            <span class="inventory-movements__action" :class="actionClass(event.action_type)">
                                {{ event.action_label }}
                            </span>
                        </td>
                        <td>
                            <div class="inventory-movements__item">
                                <strong>{{ event.item_name || '—' }}</strong>
                                <span>{{ event.item_code || '—' }}</span>
                            </div>
                        </td>
                        <td>{{ formatObject(event) }}</td>
                        <td>{{ formatQuantity(event) }}</td>
                        <td>{{ event.actor_name || 'Система' }}</td>
                        <td>{{ formatDetails(event) }}</td>
                    </tr>
                </tbody>
            </Table>
            <p v-else class="inventory-page__empty">Движения не найдены.</p>
        </div>
    </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Table from '@/components/UI-components/Table.vue';
import { useClickOutside } from '@/composables/useClickOutside';
import { formatDateTimeValue } from '@/utils/format';
import {
    fetchEmployees,
    fetchInventoryCategories,
    fetchInventoryDepartments,
    fetchInventoryGroups,
    fetchInventoryItems,
    fetchInventoryMovementActions,
    fetchInventoryMovements,
} from '@/api';

const toast = useToast();

const loading = ref(false);
const movements = ref([]);
const isFiltersOpen = ref(true);

const groups = ref([]);
const items = ref([]);
const categories = ref([]);
const departments = ref([]);
const actions = ref([]);
const staff = ref([]);

const dateFrom = ref('');
const dateTo = ref('');
const searchQuery = ref('');

const selectedFilters = reactive({
    catalog: [],
    objects: [],
    actions: [],
    actors: [],
});

const dropdownState = reactive({
    catalog: false,
    objects: false,
    actions: false,
    actors: false,
});

const filterRefs = reactive({
    catalog: null,
    objects: null,
    actions: null,
    actors: null,
});

const catalogExpandedGroupIds = ref(new Set());
const catalogExpandedCategoryIds = ref(new Set());

const groupMap = computed(() => {
    const map = new Map();
    groups.value.forEach((group) => map.set(Number(group.id), group));
    return map;
});

const categoryMap = computed(() => {
    const map = new Map();
    categories.value.forEach((category) => map.set(Number(category.id), category));
    return map;
});

const itemMap = computed(() => {
    const map = new Map();
    items.value.forEach((item) => map.set(Number(item.id), item));
    return map;
});

const groupedCatalogOptions = computed(() => {
    const groupsMap = new Map();
    for (const item of items.value) {
        const groupId = Number(item.group_id || 0);
        const categoryId = Number(item.category_id || 0);
        let groupNode = groupsMap.get(groupId);
        if (!groupNode) {
            groupNode = {
                id: groupId,
                name: groupMap.value.get(groupId)?.name || `Группа #${groupId}`,
                categoriesMap: new Map(),
            };
            groupsMap.set(groupId, groupNode);
        }
        let categoryNode = groupNode.categoriesMap.get(categoryId);
        if (!categoryNode) {
            categoryNode = {
                id: categoryId,
                name: categoryMap.value.get(categoryId)?.name || `Категория #${categoryId}`,
                items: [],
            };
            groupNode.categoriesMap.set(categoryId, categoryNode);
        }
        categoryNode.items.push(item);
    }

    return Array.from(groupsMap.values())
        .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }))
        .map((groupNode) => ({
            id: groupNode.id,
            name: groupNode.name,
            categories: Array.from(groupNode.categoriesMap.values())
                .sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }))
                .map((categoryNode) => ({
                    id: categoryNode.id,
                    name: categoryNode.name,
                    items: [...categoryNode.items].sort((a, b) =>
                        String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }),
                    ),
                })),
        }));
});

const objectOptions = computed(() => {
    const source = departments.value.filter((option) =>
        ['warehouse', 'restaurant', 'subdivision'].includes(option.type),
    );
    const ordered = [...source].sort((a, b) => {
        const rank = (entry) => {
            if (entry.type === 'warehouse') return 0;
            if (entry.type === 'restaurant') return 1;
            return 2;
        };
        const rankDiff = rank(a) - rank(b);
        if (rankDiff !== 0) return rankDiff;
        return String(a.label || '').localeCompare(String(b.label || ''), 'ru', { sensitivity: 'base' });
    });
    return ordered.map((option) => ({ value: option.id, label: option.label }));
});

const actionOptions = computed(() =>
    actions.value
        .map((action) => ({ value: action.value, label: action.label }))
        .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' })),
);

const actorOptions = computed(() =>
    staff.value
        .map((user) => ({ value: String(user.id), label: formatUser(user) }))
        .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' })),
);

const catalogFilterLabel = computed(() =>
    buildCatalogFilterLabel(selectedFilters.catalog, 'Все товары и категории'),
);
const objectFilterLabel = computed(() => buildFilterLabel(selectedFilters.objects, objectOptions.value, 'Все объекты'));
const actionFilterLabel = computed(() => buildFilterLabel(selectedFilters.actions, actionOptions.value, 'Все действия'));
const actorFilterLabel = computed(() => buildFilterLabel(selectedFilters.actors, actorOptions.value, 'Все сотрудники'));

function setFilterRef(key, element) {
    filterRefs[key] = element;
}

function closeAllDropdowns(exceptKey = '') {
    Object.keys(dropdownState).forEach((key) => {
        if (key !== exceptKey) {
            dropdownState[key] = false;
        }
    });
}

function toggleDropdown(key) {
    const nextState = !dropdownState[key];
    closeAllDropdowns(nextState ? key : '');
    dropdownState[key] = nextState;
}

function toggleSelection(key, value) {
    const selected = selectedFilters[key];
    const index = selected.indexOf(value);
    if (index >= 0) {
        selected.splice(index, 1);
        return;
    }
    selected.push(value);
}

function clearSelection(key) {
    selectedFilters[key].splice(0, selectedFilters[key].length);
}

function buildFilterLabel(selectedValues, options, fallback) {
    if (!selectedValues.length) {
        return fallback;
    }
    if (selectedValues.length === 1) {
        const selectedOption = options.find((option) => option.value === selectedValues[0]);
        return selectedOption ? selectedOption.label : fallback;
    }
    return `Выбрано: ${selectedValues.length}`;
}

function parseCatalogToken(value) {
    if (!value || !String(value).includes(':')) {
        return null;
    }
    const [kind, idRaw] = String(value).split(':');
    const id = Number(idRaw);
    if (!Number.isFinite(id)) {
        return null;
    }
    return { kind, id };
}

function getCatalogNodeLabel(value) {
    const parsed = parseCatalogToken(value);
    if (!parsed) {
        return '';
    }
    if (parsed.kind === 'g') {
        return groupMap.value.get(parsed.id)?.name || `Группа #${parsed.id}`;
    }
    if (parsed.kind === 'c') {
        const category = categoryMap.value.get(parsed.id);
        if (!category) {
            return `Категория #${parsed.id}`;
        }
        const groupName = groupMap.value.get(Number(category.group_id))?.name || '';
        return [groupName, category.name].filter(Boolean).join(' > ');
    }
    if (parsed.kind === 'i') {
        const item = itemMap.value.get(parsed.id);
        return item ? `${item.code || `ITEM-${item.id}`} · ${item.name}` : `Товар #${parsed.id}`;
    }
    return '';
}

function buildCatalogFilterLabel(selectedValues, fallback) {
    if (!selectedValues.length) {
        return fallback;
    }
    if (selectedValues.length === 1) {
        return getCatalogNodeLabel(selectedValues[0]) || fallback;
    }
    return `Выбрано: ${selectedValues.length}`;
}

function isCatalogGroupExpanded(groupId) {
    return catalogExpandedGroupIds.value.has(Number(groupId));
}

function isCatalogCategoryExpanded(categoryId) {
    return catalogExpandedCategoryIds.value.has(Number(categoryId));
}

function toggleCatalogGroup(groupId) {
    const next = new Set(catalogExpandedGroupIds.value);
    if (next.has(Number(groupId))) {
        next.delete(Number(groupId));
    } else {
        next.add(Number(groupId));
    }
    catalogExpandedGroupIds.value = next;
}

function toggleCatalogCategory(categoryId) {
    const next = new Set(catalogExpandedCategoryIds.value);
    if (next.has(Number(categoryId))) {
        next.delete(Number(categoryId));
    } else {
        next.add(Number(categoryId));
    }
    catalogExpandedCategoryIds.value = next;
}

function formatUser(user) {
    if (!user) {
        return '';
    }
    const fullName = [user.last_name, user.first_name, user.patronymic].filter(Boolean).join(' ').trim();
    return fullName || user.username || `ID ${user.id}`;
}

function actionClass(actionType) {
    if (actionType === 'transfer') return 'is-transfer';
    if (actionType === 'writeoff') return 'is-writeoff';
    if (actionType === 'cost_changed' || actionType === 'item_updated') return 'is-update';
    if (actionType === 'item_created' || actionType === 'quantity_increase') return 'is-create';
    if (actionType === 'item_deleted' || actionType === 'record_deleted') return 'is-delete';
    return '';
}

function formatDateTime(value) {
    return formatDateTimeValue(value, {
        emptyValue: '—',
        invalidValue: '—',
        locale: 'ru-RU',
        timeZone: 'Europe/Moscow',
        options: {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        },
    });
}

function formatObject(event) {
    const from = event.from_location_name;
    const to = event.to_location_name;
    if (from && to) {
        return `${from} → ${to}`;
    }
    if (to) {
        return to;
    }
    if (from) {
        return from;
    }
    return '—';
}

function formatQuantity(event) {
    if (event.quantity === null || event.quantity === undefined) {
        return '—';
    }
    const value = Number(event.quantity);
    if (!Number.isFinite(value)) {
        return '—';
    }
    if (event.action_type === 'writeoff') {
        return value > 0 ? `-${value}` : `${value}`;
    }
    if (value > 0 && ['quantity_increase', 'quantity_adjusted'].includes(event.action_type)) {
        return `+${value}`;
    }
    return `${value}`;
}

function formatField(field) {
    const map = {
        quantity: 'Количество',
        cost: 'Стоимость',
        default_cost: 'Базовая стоимость',
        code: 'Код',
        name: 'Название',
        group_id: 'Группа',
        category_id: 'Категория',
        kind_id: 'Вид',
        photo_url: 'Фото',
        note: 'Описание',
        record_id: 'Операция',
    };
    return map[field] || field || '';
}

function formatDetails(event) {
    const parts = [];
    const hasOldValue = event.old_value !== null && event.old_value !== undefined;
    const hasNewValue = event.new_value !== null && event.new_value !== undefined;
    if (event.field && (hasOldValue || hasNewValue)) {
        parts.push(`${formatField(event.field)}: ${event.old_value ?? '—'} → ${event.new_value ?? '—'}`);
    }
    if (event.comment) {
        parts.push(event.comment);
    }
    return parts.length ? parts.join(' · ') : '—';
}

function buildMovementParams() {
    const params = { limit: 1000 };
    if (dateFrom.value) {
        params.created_from = `${dateFrom.value}T00:00:00+03:00`;
    }
    if (dateTo.value) {
        params.created_to = `${dateTo.value}T23:59:59+03:00`;
    }
    const query = searchQuery.value.trim();
    if (query) {
        params.q = query;
    }
    if (selectedFilters.catalog.length) {
        const itemIds = new Set();
        for (const token of selectedFilters.catalog) {
            const parsed = parseCatalogToken(token);
            if (!parsed) {
                continue;
            }
            if (parsed.kind === 'i') {
                itemIds.add(parsed.id);
                continue;
            }
            if (parsed.kind === 'c') {
                items.value
                    .filter((item) => Number(item.category_id) === parsed.id)
                    .forEach((item) => itemIds.add(Number(item.id)));
                continue;
            }
            if (parsed.kind === 'g') {
                items.value
                    .filter((item) => Number(item.group_id) === parsed.id)
                    .forEach((item) => itemIds.add(Number(item.id)));
            }
        }
        if (itemIds.size) {
            params.item_ids = Array.from(itemIds);
        }
    }
    if (selectedFilters.objects.length) {
        params.object_ids = [...selectedFilters.objects];
    }
    if (selectedFilters.actions.length) {
        params.action_types = [...selectedFilters.actions];
    }
    if (selectedFilters.actors.length) {
        params.actor_ids = selectedFilters.actors.map((id) => Number(id));
    }
    return params;
}

async function loadLookups() {
    const [groupData, itemsData, categoriesData, departmentData, actionData, staffData] = await Promise.all([
        fetchInventoryGroups(),
        fetchInventoryItems({ include_locations: false }),
        fetchInventoryCategories(),
        fetchInventoryDepartments(),
        fetchInventoryMovementActions(),
        fetchEmployees({ include_fired: true, limit: 1000 }),
    ]);
    groups.value = Array.isArray(groupData) ? groupData : [];
    items.value = Array.isArray(itemsData) ? itemsData : [];
    categories.value = Array.isArray(categoriesData) ? categoriesData : [];
    departments.value = Array.isArray(departmentData) ? departmentData : [];
    actions.value = Array.isArray(actionData) ? actionData : [];
    staff.value = Array.isArray(staffData?.items) ? staffData.items : [];
}

async function loadMovements() {
    loading.value = true;
    closeAllDropdowns();
    try {
        const data = await fetchInventoryMovements(buildMovementParams());
        movements.value = Array.isArray(data) ? data : [];
    } catch (error) {
        toast.error('Не удалось загрузить журнал операций');
        console.error(error);
    } finally {
        loading.value = false;
    }
}

async function resetFilters() {
    dateFrom.value = '';
    dateTo.value = '';
    searchQuery.value = '';
    clearSelection('catalog');
    clearSelection('objects');
    clearSelection('actions');
    clearSelection('actors');
    await loadMovements();
}

useClickOutside(() =>
    Object.keys(filterRefs).map((key) => ({
        element: () => filterRefs[key],
        when: () => Boolean(dropdownState[key]),
        onOutside: () => {
            dropdownState[key] = false;
        },
    })),
);

onMounted(async () => {
    try {
        await loadLookups();
        await loadMovements();
    } catch (error) {
        toast.error('Не удалось загрузить справочники движений');
        console.error(error);
    }
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-records' as *;
</style>
