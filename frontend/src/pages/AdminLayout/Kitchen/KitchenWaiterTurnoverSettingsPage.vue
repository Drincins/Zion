<template>
    <div class="admin-page kitchen-waiter-turnover-settings-page">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Настройки учета продаж</h1>
                <p class="admin-page__subtitle">Правила расчета оборота в стиле KPI.</p>
            </div>
            <div class="admin-page__header-actions">
                <Button :loading="loadingOptions" :disabled="loadingOptions" color="secondary" @click="loadFilterOptions">
                    Обновить списки
                </Button>
                <Button color="ghost" @click="openCreateRuleModal">Новое правило</Button>
            </div>
        </header>

        <section class="kitchen-waiter-turnover-settings-page__filters">
            <Select v-model="restaurantId" label="Ресторан (для списков)" :options="restaurantOptions" placeholder="Все рестораны" />
            <DateInput v-model="fromDate" label="Период с" />
            <DateInput v-model="toDate" label="Период по" />
        </section>

        <section class="admin-page__section">
            <div class="kitchen-waiter-turnover-settings-page__rules-header">
                <h3>Правила</h3>
                <Button color="ghost" :loading="loadingRules" :disabled="loadingRules" @click="loadRules">Обновить правила</Button>
            </div>

            <div v-if="loadingRules" class="admin-page__empty">Загрузка правил...</div>
            <div v-else-if="rules.length" class="kitchen-waiter-turnover-settings-page__rules-list">
                <article v-for="rule in rules" :key="rule.id" class="kitchen-waiter-turnover-settings-page__rule-card">
                    <div class="kitchen-waiter-turnover-settings-page__rule-top">
                        <span class="kitchen-waiter-turnover-settings-page__rule-title">{{ rule.rule_name || 'Без названия' }}</span>
                        <span class="kitchen-waiter-turnover-settings-page__rule-status" :class="{ 'is-muted': !rule.is_active }">
                            {{ rule.is_active ? 'Активно' : 'Отключено' }}
                        </span>
                    </div>
                    <div class="kitchen-waiter-turnover-settings-page__rule-meta">
                        <span>Учет официанта: {{ waiterModeLabel(rule.waiter_mode) }}</span>
                        <span>Что считаем: {{ amountModeLabel(rule.amount_mode) }}</span>
                        <span>Удаленные: {{ deletedModeLabel(rule.deleted_mode) }}</span>
                        <span>Реальные деньги: {{ rule.real_money_only ? 'Да' : 'Нет' }}</span>
                    </div>
                    <div class="kitchen-waiter-turnover-settings-page__rule-footer">
                        <span v-if="rule.updated_at">Обновлено: {{ formatDateTime(rule.updated_at) }}</span>
                        <div class="kitchen-waiter-turnover-settings-page__rule-actions">
                            <Button size="sm" @click="openEditRuleModal(rule)">Изменить</Button>
                            <Button size="sm" color="danger" :loading="deletingRuleId === String(rule.id)" @click="deleteRule(rule.id)">
                                Удалить
                            </Button>
                        </div>
                    </div>
                </article>
            </div>
            <p v-else class="admin-page__empty">Правила пока не созданы.</p>
        </section>

        <Modal v-if="isRuleModalOpen" @close="closeRuleModal">
            <template #header>
                <div>
                    <h3 class="kitchen-waiter-turnover-settings-page__modal-title">{{ modalTitle }}</h3>
                    <p class="kitchen-waiter-turnover-settings-page__modal-subtitle">Для кого действует правило и как считать оборот.</p>
                </div>
            </template>

            <div class="kitchen-waiter-turnover-settings-page__tabs">
                <button
                    v-for="tab in modalTabs"
                    :key="tab.value"
                    type="button"
                    class="kitchen-waiter-turnover-settings-page__tab"
                    :class="{ 'is-active': activeModalTab === tab.value }"
                    @click="activeModalTab = tab.value"
                >
                    {{ tab.label }}
                </button>
            </div>

            <div v-if="loadingSettings" class="admin-page__empty">Загрузка правила...</div>

            <template v-else>
                <div v-if="activeModalTab === 'scope'" class="kitchen-waiter-turnover-settings-page__tab-content">
                    <Input v-model="settings.rule_name" label="Название правила" placeholder="Например: Официанты без удаленных заказов" required />
                    <Checkbox v-model="settings.is_active" label="Сделать правило активным" />

                    <div class="kitchen-waiter-turnover-settings-page__section-block">
                        <h4>Для каких должностей</h4>
                        <p class="kitchen-waiter-turnover-settings-page__hint">Если список пустой, правило действует для всех должностей.</p>
                        <div class="kitchen-waiter-turnover-settings-page__add-row">
                            <Select
                                v-model="drafts.positionId"
                                :options="positionSelectOptions"
                                placeholder="Выберите должность"
                                searchable
                                search-placeholder="Поиск должности"
                            />
                            <Button color="ghost" @click="addPositionScope">Добавить</Button>
                        </div>
                        <div v-if="settings.position_ids.length" class="kitchen-waiter-turnover-settings-page__chips">
                            <button
                                v-for="positionId in settings.position_ids"
                                :key="`position-${positionId}`"
                                type="button"
                                class="kitchen-waiter-turnover-settings-page__chip"
                                @click="removePositionScope(positionId)"
                            >
                                {{ positionNameById[positionId] || `#${positionId}` }} ✕
                            </button>
                        </div>
                    </div>
                </div>

                <div v-else class="kitchen-waiter-turnover-settings-page__tab-content">
                    <Select
                        v-model="settings.waiter_mode"
                        label="Учет официанта"
                        :options="waiterModeOptions"
                        placeholder="Выберите режим"
                    />
                    <Select v-model="settings.amount_mode" label="Что считаем" :options="amountModeOptions" placeholder="Выберите режим" />
                    <Select v-model="settings.deleted_mode" label="Удаленные заказы" :options="deletedModeOptions" placeholder="Выберите режим" />
                    <Checkbox v-model="settings.real_money_only" label="Только реальные деньги" />
                    <Input v-model="settings.comment" label="Комментарий" placeholder="Опционально" />
                </div>
            </template>

            <template #footer>
                <div class="kitchen-waiter-turnover-settings-page__modal-actions">
                    <Button color="primary" :loading="saving" @click="saveRule">{{ modalActionLabel }}</Button>
                    <Button color="ghost" :disabled="saving" @click="closeRuleModal">Отмена</Button>
                    <Button
                        v-if="editingRuleId"
                        color="danger"
                        :loading="deletingRuleId === editingRuleId"
                        :disabled="saving"
                        @click="deleteRule(editingRuleId)"
                    >
                        Удалить
                    </Button>
                </div>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';
import {
    createWaiterTurnoverRule,
    deleteWaiterTurnoverRule,
    fetchKitchenRestaurants,
    fetchKitchenWaiterSalesOptions,
    fetchWaiterTurnoverRule,
    fetchWaiterTurnoverRules,
    patchWaiterTurnoverRule,
} from '@/api';
import Button from '@/components/UI-components/Button.vue';
import Select from '@/components/UI-components/Select.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import Modal from '@/components/UI-components/Modal.vue';
import { formatDateTimeValue } from '@/utils/format';

const toast = useToast();

const loadingRules = ref(false);
const loadingSettings = ref(false);
const loadingOptions = ref(false);
const saving = ref(false);
const deletingRuleId = ref('');

const rules = ref([]);
const editingRuleId = ref('');
const isRuleModalOpen = ref(false);
const activeModalTab = ref('scope');

const restaurants = ref([]);
const positionOptions = ref([]);

const restaurantId = ref('');
const fromDate = ref(defaultMonthStart());
const toDate = ref(defaultToday());

const modalTabs = [
    { value: 'scope', label: 'Для кого' },
    { value: 'calc', label: 'Что считаем' },
];

const settings = reactive({
    rule_name: '',
    is_active: false,
    real_money_only: true,
    waiter_mode: 'order_close',
    amount_mode: 'sum_without_discount',
    deleted_mode: 'without_deleted',
    position_ids: [],
    include_groups: [],
    exclude_groups: [],
    include_categories: [],
    exclude_categories: [],
    include_positions: [],
    exclude_positions: [],
    include_payment_method_guids: [],
    comment: '',
});

const drafts = reactive({
    positionId: '',
});

const amountModeOptions = [
    { value: 'sum_without_discount', label: 'Сумма без скидки' },
    { value: 'sum_with_discount', label: 'Сумма со скидкой' },
    { value: 'discount_only', label: 'Только скидка' },
];
const waiterModeOptions = [
    { value: 'order_close', label: 'По закрытию заказа' },
    { value: 'item_punch', label: 'По пробитию позиции' },
];

const deletedModeOptions = [
    { value: 'without_deleted', label: 'Все без удаленных' },
    { value: 'all', label: 'Показать все' },
    { value: 'only_deleted', label: 'Только удаленные' },
];

const modalTitle = computed(() => (editingRuleId.value ? 'Редактировать правило' : 'Новое правило'));
const modalActionLabel = computed(() => (editingRuleId.value ? 'Сохранить' : 'Создать'));

const restaurantOptions = computed(() => [
    { value: '', label: 'Все рестораны' },
    ...(restaurants.value || []).map((item) => ({
        value: String(item.id),
        label: item.name || `#${item.id}`,
    })),
]);

const positionNameById = computed(() => {
    const map = {};
    for (const item of positionOptions.value || []) {
        map[item.id] = item.name || `#${item.id}`;
    }
    return map;
});

const positionSelectOptions = computed(() =>
    (positionOptions.value || []).map((item) => ({
        value: String(item.id),
        label: item.name || `#${item.id}`,
    })),
);
function defaultToday() {
    return new Date().toISOString().slice(0, 10);
}

function defaultMonthStart() {
    const dt = new Date();
    dt.setDate(1);
    return dt.toISOString().slice(0, 10);
}

function normalizeText(value) {
    return String(value || '').trim();
}

function normalizeList(values) {
    const unique = [];
    const seen = new Set();
    for (const item of values || []) {
        const value = normalizeText(item);
        if (!value) {
            continue;
        }
        const key = value.toLowerCase();
        if (seen.has(key)) {
            continue;
        }
        seen.add(key);
        unique.push(value);
    }
    return unique;
}

function normalizeIntList(values) {
    const unique = [];
    const seen = new Set();
    for (const raw of values || []) {
        const value = Number(raw);
        if (!Number.isFinite(value)) {
            continue;
        }
        const parsed = Math.trunc(value);
        if (parsed <= 0 || seen.has(parsed)) {
            continue;
        }
        seen.add(parsed);
        unique.push(parsed);
    }
    return unique;
}

function resetSettingsDraft() {
    settings.rule_name = '';
    settings.is_active = false;
    settings.real_money_only = true;
    settings.waiter_mode = 'order_close';
    settings.amount_mode = 'sum_without_discount';
    settings.deleted_mode = 'without_deleted';
    settings.position_ids = [];
    settings.include_groups = [];
    settings.exclude_groups = [];
    settings.include_categories = [];
    settings.exclude_categories = [];
    settings.include_positions = [];
    settings.exclude_positions = [];
    settings.include_payment_method_guids = [];
    settings.comment = '';
}

function applySettingsPayload(payload) {
    settings.rule_name = payload?.rule_name || '';
    settings.is_active = Boolean(payload?.is_active);
    settings.real_money_only = payload?.real_money_only !== false;
    settings.waiter_mode = payload?.waiter_mode || 'order_close';
    settings.amount_mode = payload?.amount_mode || 'sum_without_discount';
    settings.deleted_mode = payload?.deleted_mode || 'without_deleted';
    settings.position_ids = normalizeIntList(payload?.position_ids);
    settings.include_groups = normalizeList(payload?.include_groups);
    settings.exclude_groups = normalizeList(payload?.exclude_groups);
    settings.include_categories = normalizeList(payload?.include_categories);
    settings.exclude_categories = normalizeList(payload?.exclude_categories);
    settings.include_positions = normalizeList(payload?.include_positions);
    settings.exclude_positions = normalizeList(payload?.exclude_positions);
    settings.include_payment_method_guids = normalizeList(payload?.include_payment_method_guids);
    settings.comment = payload?.comment || '';
    if (Array.isArray(payload?.position_options)) {
        positionOptions.value = payload.position_options;
    }
}

function addPositionScope() {
    const value = Number(drafts.positionId || 0);
    if (!Number.isFinite(value) || value <= 0) {
        return;
    }
    if (!settings.position_ids.includes(value)) {
        settings.position_ids = [...settings.position_ids, value];
    }
    drafts.positionId = '';
}

function removePositionScope(positionId) {
    settings.position_ids = settings.position_ids.filter((id) => id !== positionId);
}

function ensureValidDates() {
    if (!fromDate.value || !toDate.value) {
        toast.error('Укажите даты периода для загрузки списков');
        return false;
    }
    if (fromDate.value > toDate.value) {
        toast.error('Дата "с" не может быть позже даты "по"');
        return false;
    }
    return true;
}

function amountModeLabel(mode) {
    return amountModeOptions.find((item) => item.value === mode)?.label || mode || '-';
}

function waiterModeLabel(mode) {
    return waiterModeOptions.find((item) => item.value === mode)?.label || mode || '-';
}

function deletedModeLabel(mode) {
    return deletedModeOptions.find((item) => item.value === mode)?.label || mode || '-';
}

function formatDateTime(value) {
    return formatDateTimeValue(value, {
        emptyValue: '-',
        invalidValue: String(value),
        locale: 'ru-RU',
    });
}

async function loadRestaurants() {
    const data = await fetchKitchenRestaurants();
    restaurants.value = Array.isArray(data) ? data : [];
}

async function loadRules() {
    loadingRules.value = true;
    try {
        const payload = await fetchWaiterTurnoverRules();
        rules.value = Array.isArray(payload?.items) ? payload.items : [];
        if (Array.isArray(payload?.position_options)) {
            positionOptions.value = payload.position_options;
        }
    } catch (error) {
        toast.error(`Ошибка загрузки правил: ${error.response?.data?.detail || error.message}`);
    } finally {
        loadingRules.value = false;
    }
}

async function loadSelectedRule(ruleId) {
    if (!ruleId) {
        return;
    }
    loadingSettings.value = true;
    try {
        const payload = await fetchWaiterTurnoverRule(ruleId);
        applySettingsPayload(payload || {});
    } catch (error) {
        toast.error(`Ошибка загрузки правила: ${error.response?.data?.detail || error.message}`);
    } finally {
        loadingSettings.value = false;
    }
}

function openCreateRuleModal() {
    editingRuleId.value = '';
    resetSettingsDraft();
    settings.rule_name = `Правило ${Math.max((rules.value || []).length + 1, 1)}`;
    settings.is_active = (rules.value || []).length === 0;
    activeModalTab.value = 'scope';
    isRuleModalOpen.value = true;
}

async function openEditRuleModal(rule) {
    if (!rule?.id) {
        return;
    }
    editingRuleId.value = String(rule.id);
    activeModalTab.value = 'scope';
    isRuleModalOpen.value = true;
    await loadSelectedRule(editingRuleId.value);
}

function closeRuleModal() {
    isRuleModalOpen.value = false;
    loadingSettings.value = false;
    saving.value = false;
    deletingRuleId.value = '';
}

async function deleteRule(ruleId) {
    const id = String(ruleId || '');
    if (!id) {
        return;
    }
    if (!window.confirm('Удалить правило?')) {
        return;
    }

    deletingRuleId.value = id;
    try {
        await deleteWaiterTurnoverRule(id);
        toast.success('Правило удалено');
        await loadRules();
        if (editingRuleId.value === id) {
            closeRuleModal();
        }
    } catch (error) {
        toast.error(`Ошибка удаления правила: ${error.response?.data?.detail || error.message}`);
    } finally {
        deletingRuleId.value = '';
    }
}

async function loadFilterOptions() {
    if (!ensureValidDates()) {
        return;
    }
    loadingOptions.value = true;
    try {
        await fetchKitchenWaiterSalesOptions({
            from_date: fromDate.value,
            to_date: toDate.value,
            ...(restaurantId.value ? { restaurant_id: Number(restaurantId.value) } : {}),
        });
    } catch (error) {
        toast.error(`Ошибка загрузки списков: ${error.response?.data?.detail || error.message}`);
    } finally {
        loadingOptions.value = false;
    }
}

async function saveRule() {
    saving.value = true;
    try {
        const requestPayload = {
            rule_name: normalizeText(settings.rule_name) || 'Правило',
            is_active: Boolean(settings.is_active),
            real_money_only: Boolean(settings.real_money_only),
            waiter_mode: settings.waiter_mode || 'order_close',
            amount_mode: settings.amount_mode || 'sum_without_discount',
            deleted_mode: settings.deleted_mode || 'without_deleted',
            position_ids: normalizeIntList(settings.position_ids),
            include_groups: normalizeList(settings.include_groups),
            exclude_groups: normalizeList(settings.exclude_groups),
            include_categories: normalizeList(settings.include_categories),
            exclude_categories: normalizeList(settings.exclude_categories),
            include_positions: normalizeList(settings.include_positions),
            exclude_positions: normalizeList(settings.exclude_positions),
            include_payment_method_guids: normalizeList(settings.include_payment_method_guids),
            comment: normalizeText(settings.comment) || null,
        };

        let payload = null;
        if (editingRuleId.value) {
            payload = await patchWaiterTurnoverRule(editingRuleId.value, requestPayload);
            toast.success('Правило обновлено');
        } else {
            payload = await createWaiterTurnoverRule(requestPayload);
            toast.success('Правило создано');
        }

        applySettingsPayload(payload || {});
        if (payload?.id) {
            editingRuleId.value = String(payload.id);
        }
        await loadRules();
        closeRuleModal();
    } catch (error) {
        toast.error(`Ошибка сохранения: ${error.response?.data?.detail || error.message}`);
    } finally {
        saving.value = false;
    }
}

onMounted(async () => {
    await loadRestaurants();
    await loadRules();
    await loadFilterOptions();
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kitchen-waiter-turnover-settings' as *;
</style>
