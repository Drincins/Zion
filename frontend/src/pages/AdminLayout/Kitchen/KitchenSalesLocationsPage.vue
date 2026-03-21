<template>
    <div class="admin-page kitchen-sales-locations-page">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Локации продаж iiko</h1>
                <p class="admin-page__subtitle">
                    Настройка распределения продаж по ресторанам: подразделение/стол из iiko -> ресторан в системе.
                </p>
            </div>
            <div class="admin-page__header-actions">
                <Button :loading="loading" :disabled="loading" @click="reloadAll">Обновить</Button>
            </div>
        </header>

        <section class="kitchen-sales-locations-page__editor admin-page__section">
            <h3 class="kitchen-sales-locations-page__section-title">
                {{ editingId ? 'Редактирование правила' : 'Новое правило' }}
            </h3>
            <div class="kitchen-sales-locations-page__editor-grid">
                <Select
                    v-model="draft.source_restaurant_id"
                    label="Источник (ресторан)"
                    :options="sourceRestaurantOptions"
                    placeholder="Любой источник"
                />
                <Input
                    v-model="draft.department"
                    label="Подразделение iiko"
                    placeholder="Например: Основной зал"
                />
                <Input
                    v-model="draft.table_num"
                    label="Стол (опционально)"
                    placeholder="Например: 12"
                />
                <Select
                    v-model="draft.target_restaurant_id"
                    label="Целевой ресторан"
                    :options="targetRestaurantOptions"
                    placeholder="Выберите ресторан"
                />
                <Checkbox v-model="draft.is_active" label="Активно" />
                <Input
                    v-model="draft.comment"
                    label="Комментарий"
                    placeholder="Опционально"
                />
            </div>
            <div class="kitchen-sales-locations-page__editor-actions">
                <Button
                    :loading="saving"
                    :disabled="saving || !canManage"
                    @click="saveMapping"
                >
                    {{ editingId ? 'Сохранить' : 'Добавить правило' }}
                </Button>
                <Button
                    color="ghost"
                    :disabled="saving"
                    @click="resetDraft"
                >
                    Очистить
                </Button>
            </div>
        </section>

        <section class="admin-page__section">
            <h3 class="kitchen-sales-locations-page__section-title">Существующие правила</h3>
            <Table v-if="mappings.length">
                <thead>
                    <tr>
                        <th>Источник</th>
                        <th>Подразделение</th>
                        <th>Стол</th>
                        <th>Целевой ресторан</th>
                        <th>Активно</th>
                        <th>Комментарий</th>
                        <th class="admin-page__actions">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="row in mappings" :key="row.id">
                        <td>{{ row.source_restaurant_name || 'Любой источник' }}</td>
                        <td>{{ row.department || '-' }}</td>
                        <td>{{ row.table_num || '-' }}</td>
                        <td>{{ row.target_restaurant_name || `#${row.target_restaurant_id}` }}</td>
                        <td>{{ row.is_active ? 'Да' : 'Нет' }}</td>
                        <td>{{ row.comment || '-' }}</td>
                        <td class="admin-page__actions">
                            <button
                                type="button"
                                class="admin-page__icon-button"
                                title="Редактировать"
                                @click="editMapping(row)"
                            >
                                <BaseIcon name="Edit" />
                            </button>
                            <button
                                type="button"
                                class="admin-page__icon-button admin-page__icon-button--danger"
                                title="Удалить"
                                :disabled="deletingId === row.id || !canManage"
                                @click="deleteMapping(row)"
                            >
                                <BaseIcon name="Trash" />
                            </button>
                        </td>
                    </tr>
                </tbody>
            </Table>
            <div v-else-if="loading" class="admin-page__empty">Загрузка правил...</div>
            <div v-else class="admin-page__empty">Правила распределения еще не настроены.</div>
        </section>

        <section class="admin-page__section">
            <h3 class="kitchen-sales-locations-page__section-title">Подсказки из фактических данных</h3>
            <p class="kitchen-sales-locations-page__hint">
                Список подразделений/столов, которые уже встречались в синке. Можно подставить в форму выше.
            </p>
            <Table v-if="candidates.length">
                <thead>
                    <tr>
                        <th>Источник</th>
                        <th>Подразделение</th>
                        <th>Стол</th>
                        <th>Заказов</th>
                        <th>Последняя дата</th>
                        <th class="admin-page__actions">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="row in candidates" :key="candidateKey(row)">
                        <td>{{ row.source_restaurant_name || 'Не определен' }}</td>
                        <td>{{ row.department || '-' }}</td>
                        <td>{{ row.table_num || '-' }}</td>
                        <td>{{ formatNumber(row.orders_count) }}</td>
                        <td>{{ row.last_open_date || '-' }}</td>
                        <td class="admin-page__actions">
                            <Button
                                size="sm"
                                color="secondary"
                                @click="applyCandidate(row)"
                            >
                                Подставить
                            </Button>
                        </td>
                    </tr>
                </tbody>
            </Table>
            <div v-else-if="loadingCandidates" class="admin-page__empty">Загрузка подсказок...</div>
            <div v-else class="admin-page__empty">Подсказки пока недоступны (нет данных синка).</div>
        </section>
    </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue';
import {
    createKitchenSalesLocationMapping,
    deleteKitchenSalesLocationMapping,
    fetchKitchenRestaurants,
    fetchKitchenSalesLocationCandidates,
    fetchKitchenSalesLocationMappings,
    patchKitchenSalesLocationMapping,
} from '@/api';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import Button from '@/components/UI-components/Button.vue';
import Table from '@/components/UI-components/Table.vue';
import Select from '@/components/UI-components/Select.vue';
import Input from '@/components/UI-components/Input.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import { formatNumberValue } from '@/utils/format';

const toast = useToast();
const userStore = useUserStore();

const loading = ref(false);
const loadingCandidates = ref(false);
const saving = ref(false);
const deletingId = ref('');
const editingId = ref('');

const restaurants = ref([]);
const mappings = ref([]);
const candidates = ref([]);

const draft = reactive({
    source_restaurant_id: '',
    target_restaurant_id: '',
    department: '',
    table_num: '',
    comment: '',
    is_active: true,
});

const canManage = computed(() => userStore.hasAnyPermission('sales.tables.manage', 'iiko.manage'));

const sourceRestaurantOptions = computed(() => [
    { value: '', label: 'Любой источник' },
    ...(restaurants.value || []).map((row) => ({ value: String(row.id), label: row.name })),
]);

const targetRestaurantOptions = computed(() =>
    (restaurants.value || []).map((row) => ({ value: String(row.id), label: row.name })),
);

function candidateKey(row) {
    return `${row.source_restaurant_id || 'none'}:${row.department_norm || 'none'}:${row.table_num_norm || 'none'}`;
}

function formatNumber(value) {
    return formatNumberValue(value, {
        emptyValue: '0',
        invalidValue: '0',
        locale: 'ru-RU',
        minimumFractionDigits: 0,
        maximumFractionDigits: 20,
    });
}

function normalizeNullableId(value) {
    const clean = String(value ?? '').trim();
    if (!clean) {
        return null;
    }
    const parsed = Number(clean);
    return Number.isFinite(parsed) ? parsed : null;
}

function resetDraft() {
    editingId.value = '';
    draft.source_restaurant_id = '';
    draft.target_restaurant_id = '';
    draft.department = '';
    draft.table_num = '';
    draft.comment = '';
    draft.is_active = true;
}

function editMapping(row) {
    editingId.value = String(row.id || '');
    draft.source_restaurant_id = row.source_restaurant_id !== null && row.source_restaurant_id !== undefined
        ? String(row.source_restaurant_id)
        : '';
    draft.target_restaurant_id = row.target_restaurant_id !== null && row.target_restaurant_id !== undefined
        ? String(row.target_restaurant_id)
        : '';
    draft.department = row.department || '';
    draft.table_num = row.table_num || '';
    draft.comment = row.comment || '';
    draft.is_active = Boolean(row.is_active);
}

function applyCandidate(row) {
    draft.source_restaurant_id = row.source_restaurant_id !== null && row.source_restaurant_id !== undefined
        ? String(row.source_restaurant_id)
        : '';
    draft.department = row.department || '';
    draft.table_num = row.table_num || '';
}

async function loadRestaurants() {
    const data = await fetchKitchenRestaurants();
    restaurants.value = Array.isArray(data) ? data : [];
}

async function loadMappings() {
    const data = await fetchKitchenSalesLocationMappings({
        include_inactive: true,
    });
    mappings.value = Array.isArray(data) ? data : [];
}

async function loadCandidates() {
    loadingCandidates.value = true;
    try {
        const data = await fetchKitchenSalesLocationCandidates({ limit: 1000 });
        candidates.value = Array.isArray(data) ? data : [];
    } catch (error) {
        toast.error(`Ошибка загрузки подсказок: ${error.response?.data?.detail || error.message}`);
    } finally {
        loadingCandidates.value = false;
    }
}

async function reloadAll() {
    loading.value = true;
    try {
        await Promise.all([loadRestaurants(), loadMappings(), loadCandidates()]);
    } catch (error) {
        toast.error(`Ошибка загрузки: ${error.response?.data?.detail || error.message}`);
    } finally {
        loading.value = false;
    }
}

async function saveMapping() {
    if (!canManage.value) {
        return;
    }
    if (!String(draft.department || '').trim()) {
        toast.error('Укажите подразделение iiko');
        return;
    }
    const targetRestaurantId = normalizeNullableId(draft.target_restaurant_id);
    if (targetRestaurantId === null) {
        toast.error('Выберите целевой ресторан');
        return;
    }

    const payload = {
        source_restaurant_id: normalizeNullableId(draft.source_restaurant_id),
        target_restaurant_id: targetRestaurantId,
        department: String(draft.department || '').trim(),
        table_num: String(draft.table_num || '').trim() || null,
        comment: String(draft.comment || '').trim() || null,
        is_active: Boolean(draft.is_active),
    };

    saving.value = true;
    try {
        if (editingId.value) {
            await patchKitchenSalesLocationMapping(editingId.value, payload);
        } else {
            await createKitchenSalesLocationMapping(payload);
        }
        toast.success('Правило сохранено');
        resetDraft();
        await Promise.all([loadMappings(), loadCandidates()]);
    } catch (error) {
        toast.error(`Ошибка сохранения правила: ${error.response?.data?.detail || error.message}`);
    } finally {
        saving.value = false;
    }
}

async function deleteMapping(row) {
    if (!canManage.value || !row?.id) {
        return;
    }
    const confirmed = window.confirm('Удалить это правило распределения?');
    if (!confirmed) {
        return;
    }
    deletingId.value = String(row.id);
    try {
        await deleteKitchenSalesLocationMapping(row.id);
        if (editingId.value === String(row.id)) {
            resetDraft();
        }
        toast.success('Правило удалено');
        await Promise.all([loadMappings(), loadCandidates()]);
    } catch (error) {
        toast.error(`Ошибка удаления правила: ${error.response?.data?.detail || error.message}`);
    } finally {
        deletingId.value = '';
    }
}

reloadAll();
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kitchen-sales-locations' as *;
</style>
