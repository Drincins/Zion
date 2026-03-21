<template>
    <section class="activity-log">
        <div class="activity-log__header">
            <div>
                <h2>Журнал действий</h2>
                <p class="activity-log__subtitle">Изменения сотрудников</p>
            </div>
            <div class="activity-log__actions">
                <Button color="ghost" size="sm" :loading="loading" @click="refreshEvents">Обновить</Button>
            </div>
        </div>

        <div class="activity-log__filters">
            <Input
                v-model="searchInput"
                label="Поиск"
                placeholder="Сотрудник, поле, автор, значение"
            />
            <Select
                v-model="actionFilter"
                label="Тип действия"
                :options="actionTypeOptions"
            />
            <DateInput v-model="dateFrom" label="Дата с" />
            <DateInput v-model="dateTo" label="Дата по" />
            <div class="activity-log__filters-actions">
                <Button color="primary" size="sm" :loading="loading" @click="applyFilters">
                    Показать
                </Button>
            </div>
        </div>

        <div v-if="loading" class="activity-log__state">Загрузка...</div>
        <div v-else-if="error" class="activity-log__state activity-log__state--error">{{ error }}</div>
        <div v-else-if="sortedEvents.length" class="activity-log__table-wrapper">
            <Table class="activity-log__table">
                <thead>
                    <tr>
                        <th :aria-sort="getAriaSort('created_at')">
                            <button
                                type="button"
                                class="activity-log__sort"
                                :class="{ 'is-active': sortKey === 'created_at' }"
                                @click="toggleSort('created_at')"
                            >
                                Дата
                                <span v-if="sortKey === 'created_at'" class="activity-log__sort-indicator">
                                    {{ sortIndicator }}
                                </span>
                            </button>
                        </th>
                        <th :aria-sort="getAriaSort('user')">
                            <button
                                type="button"
                                class="activity-log__sort"
                                :class="{ 'is-active': sortKey === 'user' }"
                                @click="toggleSort('user')"
                            >
                                Сотрудник
                                <span v-if="sortKey === 'user'" class="activity-log__sort-indicator">
                                    {{ sortIndicator }}
                                </span>
                            </button>
                        </th>
                        <th :aria-sort="getAriaSort('field')">
                            <button
                                type="button"
                                class="activity-log__sort"
                                :class="{ 'is-active': sortKey === 'field' }"
                                @click="toggleSort('field')"
                            >
                                Поле
                                <span v-if="sortKey === 'field'" class="activity-log__sort-indicator">
                                    {{ sortIndicator }}
                                </span>
                            </button>
                        </th>
                        <th :aria-sort="getAriaSort('old_value')">
                            <button
                                type="button"
                                class="activity-log__sort"
                                :class="{ 'is-active': sortKey === 'old_value' }"
                                @click="toggleSort('old_value')"
                            >
                                Было
                                <span v-if="sortKey === 'old_value'" class="activity-log__sort-indicator">
                                    {{ sortIndicator }}
                                </span>
                            </button>
                        </th>
                        <th :aria-sort="getAriaSort('new_value')">
                            <button
                                type="button"
                                class="activity-log__sort"
                                :class="{ 'is-active': sortKey === 'new_value' }"
                                @click="toggleSort('new_value')"
                            >
                                Стало
                                <span v-if="sortKey === 'new_value'" class="activity-log__sort-indicator">
                                    {{ sortIndicator }}
                                </span>
                            </button>
                        </th>
                        <th :aria-sort="getAriaSort('author')">
                            <button
                                type="button"
                                class="activity-log__sort"
                                :class="{ 'is-active': sortKey === 'author' }"
                                @click="toggleSort('author')"
                            >
                                Автор
                                <span v-if="sortKey === 'author'" class="activity-log__sort-indicator">
                                    {{ sortIndicator }}
                                </span>
                            </button>
                        </th>
                        <th :aria-sort="getAriaSort('comment')">
                            <button
                                type="button"
                                class="activity-log__sort"
                                :class="{ 'is-active': sortKey === 'comment' }"
                                @click="toggleSort('comment')"
                            >
                                Комментарий
                                <span v-if="sortKey === 'comment'" class="activity-log__sort-indicator">
                                    {{ sortIndicator }}
                                </span>
                            </button>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="event in sortedEvents" :key="event.id">
                        <td>{{ event._display.createdAt }}</td>
                        <td>{{ event._display.user }}</td>
                        <td>{{ event._display.field }}</td>
                        <td class="activity-log__value">{{ event._display.oldValue }}</td>
                        <td class="activity-log__value">{{ event._display.newValue }}</td>
                        <td>{{ event._display.author }}</td>
                        <td class="activity-log__value">{{ event._display.comment }}</td>
                    </tr>
                </tbody>
            </Table>
        </div>
        <p v-else class="activity-log__state">Записей пока нет.</p>

        <div v-if="hasMore" class="activity-log__footer">
            <Button color="ghost" size="sm" :loading="loadingMore" @click="loadMore">
                Показать ещё
            </Button>
        </div>
    </section>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Select from '@/components/UI-components/Select.vue';
import Table from '@/components/UI-components/Table.vue';
import { fetchEmployeeChangeEvents } from '@/api';
import { changeFieldLabels, formatChangeField, formatChangeValue } from '@/utils/changeEvents';
import { normalizeMojibakeText } from '@/utils/textEncoding';
import { useDebounce } from '@/composables/useDebounce';

const toast = useToast();

const events = ref([]);
const loading = ref(false);
const loadingMore = ref(false);
const error = ref('');
const searchInput = ref('');
const search = ref('');
const actionFilter = ref('');
const dateFrom = ref('');
const dateTo = ref('');
const limit = 120;
const hasMore = ref(false);
const sortKey = ref('created_at');
const sortDirection = ref('desc');
const collator = new Intl.Collator('ru', { numeric: true, sensitivity: 'base' });
const normalizeText = normalizeMojibakeText;
const applySearch = useDebounce((value) => {
    search.value = value;
}, 250);

const sourceLabels = {
    system: 'Система',
    manual: 'Вручную',
    import: 'Импорт',
    sync: 'Синхронизация',
    api: 'API',
};

const actionTypeOptions = computed(() => {
    const map = new Map();
    Object.entries(changeFieldLabels).forEach(([field, label]) => {
        map.set(field, label);
    });
    events.value.forEach((event) => {
        if (!event.field) {
            return;
        }
        if (!map.has(event.field)) {
            map.set(event.field, formatChangeField(event.field));
        }
    });
    const options = Array.from(map.entries())
        .map(([value, label]) => ({ value, label }))
        .sort((a, b) => collator.compare(a.label, b.label));
    return [{ value: '', label: 'Все действия' }, ...options];
});

const filteredEvents = computed(() => {
    let list = events.value;
    if (actionFilter.value) {
        list = list.filter((event) => event.field === actionFilter.value);
    }
    if (dateFrom.value || dateTo.value) {
        list = list.filter((event) => {
            const key = event._dateKey;
            if (!key) {
                return false;
            }
            if (dateFrom.value && key < dateFrom.value) {
                return false;
            }
            if (dateTo.value && key > dateTo.value) {
                return false;
            }
            return true;
        });
    }
    const query = (search.value || '').trim().toLowerCase();
    if (!query) {
        return list;
    }
    return list.filter((event) => event._search?.includes(query));
});

const sortedEvents = computed(() => {
    const list = [...filteredEvents.value];
    const key = sortKey.value;
    const direction = sortDirection.value === 'asc' ? 1 : -1;
    list.sort((a, b) => {
        const va = getSortValue(a, key);
        const vb = getSortValue(b, key);
        if (va === null || va === undefined) {
            return vb === null || vb === undefined ? 0 : 1 * direction;
        }
        if (vb === null || vb === undefined) {
            return -1 * direction;
        }
        if (typeof va === 'number' && typeof vb === 'number') {
            return (va - vb) * direction;
        }
        return collator.compare(String(va), String(vb)) * direction;
    });
    return list;
});

function formatChangeAuthor(event) {
    if (event?.changed_by_name) {
        return normalizeText(event.changed_by_name);
    }
    if (event?.changed_by_id) {
        return `ID ${event.changed_by_id}`;
    }
    if (event?.source) {
        const mapped = sourceLabels[event.source] || event.source;
        return normalizeText(mapped);
    }
    return '-';
}

function formatChangeDate(value) {
    if (!value) {
        return '-';
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return String(value);
    }
    return parsed.toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function formatTargetUser(event) {
    if (event?.user_name) {
        return normalizeText(event.user_name);
    }
    if (event?.user_id) {
        return `ID ${event.user_id}`;
    }
    return '-';
}

function formatComment(value) {
    if (!value) {
        return '-';
    }
    return normalizeText(String(value));
}

function parseDateKey(value) {
    if (!value) {
        return null;
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return null;
    }
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function parseDateTs(value) {
    if (!value) {
        return null;
    }
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed.getTime();
}

function prepareEvent(event) {
    const display = {
        createdAt: formatChangeDate(event.created_at),
        user: formatTargetUser(event),
        field: formatChangeField(event.field),
        oldValue: formatChangeValue(event.old_value),
        newValue: formatChangeValue(event.new_value),
        author: formatChangeAuthor(event),
        comment: formatComment(event.comment),
    };
    const searchIndex = [
        display.createdAt,
        display.user,
        display.field,
        display.oldValue,
        display.newValue,
        display.author,
        display.comment,
        event.source,
    ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
    return {
        ...event,
        _display: display,
        _search: searchIndex,
        _createdAtTs: parseDateTs(event.created_at),
        _dateKey: parseDateKey(event.created_at),
    };
}

function getSortValue(event, key) {
    switch (key) {
        case 'created_at':
            return event._createdAtTs ?? 0;
        case 'user':
            return event._display?.user;
        case 'field':
            return event._display?.field;
        case 'old_value':
            return event._display?.oldValue;
        case 'new_value':
            return event._display?.newValue;
        case 'author':
            return event._display?.author;
        case 'comment':
            return event._display?.comment;
        default:
            return event._createdAtTs ?? 0;
    }
}

function toggleSort(key) {
    if (sortKey.value === key) {
        sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
        return;
    }
    sortKey.value = key;
    sortDirection.value = key === 'created_at' ? 'desc' : 'asc';
}

const sortIndicator = computed(() => (sortDirection.value === 'asc' ? '▲' : '▼'));

function getAriaSort(key) {
    if (sortKey.value !== key) {
        return 'none';
    }
    return sortDirection.value === 'asc' ? 'ascending' : 'descending';
}

async function loadEvents({ reset } = { reset: false }) {
    if (loading.value || loadingMore.value) {
        return;
    }
    if (reset) {
        loading.value = true;
        error.value = '';
    } else {
        loadingMore.value = true;
    }

    try {
        const offset = reset ? 0 : events.value.length;
        const params = {
            limit,
            offset,
            field: actionFilter.value || undefined,
            date_from: dateFrom.value || undefined,
            date_to: dateTo.value || undefined,
        };
        const data = await fetchEmployeeChangeEvents(params);
        const items = Array.isArray(data?.items) ? data.items.map(prepareEvent) : [];
        events.value = reset ? items : [...events.value, ...items];
        hasMore.value = items.length === limit;
    } catch (err) {
        const detail = err?.response?.data?.detail;
        error.value = detail || 'Не удалось загрузить журнал действий';
        toast.error(error.value);
    } finally {
        loading.value = false;
        loadingMore.value = false;
    }
}

function refreshEvents() {
    loadEvents({ reset: true });
}

function loadMore() {
    if (hasMore.value) {
        loadEvents({ reset: false });
    }
}

function applyFilters() {
    loadEvents({ reset: true });
}

watch(
    searchInput,
    (value) => {
        if (search.value === value) {
            return;
        }
        applySearch(value);
    },
    { flush: 'post' },
);

onMounted(() => {
    loadEvents({ reset: true });
});
</script>

<style scoped>
.activity-log {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.activity-log__header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
}

.activity-log__subtitle {
    margin: 4px 0 0;
    color: #6b7280;
    font-size: 14px;
}

.activity-log__actions {
    display: flex;
    gap: 8px;
}

.activity-log__filters {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 12px;
    align-items: end;
}

.activity-log__filters-actions {
    display: flex;
    justify-content: flex-end;
}

.activity-log__state {
    color: #6b7280;
}

.activity-log__state--error {
    color: #c0392b;
}

.activity-log__table-wrapper {
    overflow: auto;
    max-height: 70vh;
}

.activity-log__sort {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: none;
    border: none;
    font: inherit;
    padding: 0;
    cursor: pointer;
    color: inherit;
}

.activity-log__sort.is-active {
    color: var(--color-primary, #2563eb);
}

.activity-log__sort-indicator {
    font-size: 12px;
    opacity: 0.7;
}

.activity-log__table :deep(td),
.activity-log__table :deep(th) {
    vertical-align: top;
}

.activity-log__table :deep(thead th) {
    position: sticky;
    top: 0;
    background: var(--color-surface, #fff);
    z-index: 2;
    box-shadow: 0 1px 0 var(--color-border, #e5e7eb);
}

.activity-log__value {
    max-width: 260px;
    white-space: normal;
    word-break: break-word;
}

.activity-log__footer {
    display: flex;
    justify-content: center;
}
</style>
