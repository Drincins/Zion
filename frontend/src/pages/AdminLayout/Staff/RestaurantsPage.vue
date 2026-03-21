<template>
    <div class="admin-page">
        <header class="admin-page__header">
            <div>
                <h1 class="admin-page__title">Рестораны</h1>
                <p class="admin-page__subtitle">Справочник ресторанов и параметры интеграции iiko.</p>
            </div>
            <div class="admin-page__header-actions">
                <div class="admin-page__toolbar">
                    <Input
                        v-model="search"
                        class="admin-page__search"
                        placeholder="Поиск по названию"
                    />
                    <Button
                        type="button"
                        color="secondary"
                        size="sm"
                        :loading="loading"
                        @click="loadRestaurants"
                    >
                        Обновить
                    </Button>
                    <Button
                        v-if="canManageRestaurants"
                        type="button"
                        color="primary"
                        size="sm"
                        @click="openCreateRestaurantModal"
                    >
                        Добавить ресторан
                    </Button>
                </div>
            </div>
        </header>

        <section v-if="canViewRestaurants" class="admin-page__section">
            <Table v-if="filteredRestaurants.length">
                <thead>
                    <tr>
                        <th>Название</th>
                        <th>Сервер</th>
                        <th>Код департамента / ТП (iiko)</th>
                        <th>iiko login</th>
                        <th>Участвует в продажах</th>
                        <th class="admin-page__actions">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="rest in filteredRestaurants" :key="rest.id">
                        <td>
                            <button type="button" class="admin-page__row-link" @click="openEditModal(rest)">
                                {{ rest.name }}
                            </button>
                        </td>
                        <td>{{ rest.server || '—' }}</td>
                        <td>{{ rest.department_code || '—' }}</td>
                        <td>{{ rest.iiko_login || '—' }}</td>
                        <td>{{ rest.participates_in_sales ? 'Да' : 'Нет' }}</td>
                        <td class="admin-page__actions">
                            <button
                                type="button"
                                class="admin-page__icon-button"
                                title="Редактировать"
                                @click="openEditModal(rest)"
                            >
                                <BaseIcon name="Edit" />
                            </button>
                        </td>
                    </tr>
                </tbody>
            </Table>

            <div v-else class="admin-page__empty">
                <p v-if="loading">Загрузка ресторанов...</p>
                <p v-else>Рестораны не найдены.</p>
            </div>
        </section>

        <div v-else class="admin-page__empty">
            <p>Доступ ограничен.</p>
        </div>

        <Modal v-if="canViewRestaurants && isCreateRestaurantModalOpen" @close="closeCreateRestaurantModal">
            <template #header>
                <div>
                    <h3 class="restaurants__modal-title">Новый ресторан</h3>
                    <p class="restaurants__modal-subtitle">Заполните данные ресторана и доступы iiko.</p>
                </div>
            </template>
            <form class="restaurants__form" @submit.prevent="handleCreateRestaurant">
                <Input v-model="restaurantName" label="Название" required />
                <Input v-model="restaurantServer" label="Сервер" required />
                <Input v-model="restaurantDepartmentCode" label="Код департамента / ТП (iiko)" />
                <Input v-model="restaurantIikoLogin" label="iiko login" required />
                <Input v-model="restaurantIikoPassword" label="iiko пароль" type="password" required />
                <Checkbox v-model="restaurantParticipatesInSales" label="Участвует в продажах" />
            </form>
            <template #footer>
                <Button type="button" color="primary" @click="handleCreateRestaurant">Создать</Button>
                <Button type="button" color="ghost" @click="closeCreateRestaurantModal">Отмена</Button>
            </template>
        </Modal>

        <Modal v-if="canViewRestaurants && editRestaurant" @close="cancelEditRestaurant">
            <template #header>
                <div>
                    <h3 class="restaurants__modal-title">Редактировать: {{ editRestaurant.name }}</h3>
                    <p class="restaurants__modal-subtitle">Обновите параметры ресторана.</p>
                </div>
            </template>
            <div class="restaurants__tabs">
                <button
                    type="button"
                    :class="['restaurants__tab', { 'is-active': editModalTab === 'main' }]"
                    @click="editModalTab = 'main'"
                >
                    Основное
                </button>
                <button
                    type="button"
                    :class="['restaurants__tab', { 'is-active': editModalTab === 'sync' }]"
                    @click="editModalTab = 'sync'"
                >
                    Настройка синхронизации
                </button>
            </div>

            <form v-if="editModalTab === 'main'" class="restaurants__form" @submit.prevent="handleUpdateRestaurant">
                <Input v-model="editRestaurant.name" label="Название" required />
                <Input v-model="editRestaurant.server" label="Сервер" required />
                <Input v-model="editRestaurant.department_code" label="Код департамента / ТП (iiko)" />
                <Input v-model="editRestaurant.iiko_login" label="iiko login" required />
                <Input v-model="editRestaurant.iiko_password" label="Новый iiko пароль" type="password" />
                <Checkbox v-model="editRestaurant.participates_in_sales" label="Участвует в продажах" />
            </form>

            <div v-else class="restaurants__sync-panel">
                <div v-if="syncSettingsLoading" class="admin-page__empty">Загрузка настроек синхронизации...</div>
                <template v-else>
                    <Checkbox
                        v-model="salesSyncSettings.auto_sync_enabled"
                        label="Автоматическая синхронизация включена"
                    />

                    <div class="restaurants__sync-grid">
                        <Input
                            v-model="salesSyncSettings.daily_sync_time"
                            type="time"
                            label="Ежедневный запуск (время)"
                        />
                        <Input
                            v-model="salesSyncSettings.daily_lookback_days"
                            type="number"
                            min="0"
                            label="Ежедневный охват (дней назад)"
                        />
                        <Checkbox
                            v-model="salesSyncSettings.weekly_sync_enabled"
                            label="Еженедельная глобальная прогрузка"
                        />
                        <Select
                            v-model="salesSyncSettings.weekly_sync_weekday"
                            :options="weekdayOptions"
                            label="День недели глобальной прогрузки"
                        />
                        <Input
                            v-model="salesSyncSettings.weekly_sync_time"
                            type="time"
                            label="Время глобальной прогрузки"
                        />
                        <Input
                            v-model="salesSyncSettings.weekly_lookback_days"
                            type="number"
                            min="0"
                            label="Глобальный охват (дней назад)"
                        />
                        <Input
                            v-model="salesSyncSettings.manual_default_lookback_days"
                            type="number"
                            min="0"
                            label="Ручной запуск: период по умолчанию (дней)"
                        />
                    </div>

                    <div class="restaurants__sync-meta">
                        <p>Последний запуск: {{ formatDateTime(salesSyncSettings.last_sync_at) }}</p>
                        <p>Последний успешный: {{ formatDateTime(salesSyncSettings.last_successful_sync_at) }}</p>
                        <p>Последний ручной: {{ formatDateTime(salesSyncSettings.last_manual_sync_at) }}</p>
                        <p>Статус: {{ salesSyncSettings.last_sync_status || '—' }}</p>
                        <p>Сценарий: {{ salesSyncSettings.last_sync_scope || '—' }}</p>
                        <p>Ежедневный запуск за: {{ salesSyncSettings.last_daily_run_on || '—' }}</p>
                        <p>Еженедельный запуск за: {{ salesSyncSettings.last_weekly_run_on || '—' }}</p>
                        <p v-if="salesSyncSettings.last_sync_error">Ошибка: {{ salesSyncSettings.last_sync_error }}</p>
                    </div>

                    <div class="restaurants__manual-sync">
                        <h4 class="restaurants__manual-title">Ручная синхронизация за период</h4>
                        <div class="restaurants__manual-grid">
                            <DateInput v-model="syncRunFromDate" label="С даты" />
                            <DateInput v-model="syncRunToDate" label="По дату" />
                        </div>
                        <Button
                            type="button"
                            color="secondary"
                            :loading="syncSettingsRunning"
                            :disabled="syncSettingsRunning || !canRunSalesSync"
                            @click="runManualSalesSync"
                        >
                            Синхронизировать период
                        </Button>
                        <div v-if="syncChunkRows.length" class="restaurants__sync-chunks">
                            <div class="restaurants__sync-chunks-header">
                                <span class="restaurants__sync-chunks-title">Прогресс по окнам</span>
                                <span class="restaurants__sync-chunks-summary">{{ syncChunkProgressText }}</span>
                            </div>
                            <ul class="restaurants__sync-chunks-list">
                                <li
                                    v-for="row in syncChunkRows"
                                    :key="`sync-chunk-${row.index}`"
                                    class="restaurants__sync-chunk"
                                    :class="`is-${row.status}`"
                                >
                                    <div class="restaurants__sync-chunk-main">
                                        <span class="restaurants__sync-chunk-window">
                                            {{ row.index }}. {{ row.from_date }} — {{ row.to_date }}
                                        </span>
                                        <span class="restaurants__sync-chunk-status">{{ formatSyncChunkStatus(row.status) }}</span>
                                    </div>
                                    <p v-if="row.summary" class="restaurants__sync-chunk-summary">{{ row.summary }}</p>
                                    <p v-if="row.detail" class="restaurants__sync-chunk-detail">{{ row.detail }}</p>
                                </li>
                            </ul>
                        </div>
                    </div>

                    <div class="restaurants__sync-operations">
                        <div class="restaurants__sync-operations-header">
                            <h4 class="restaurants__manual-title">Операции синхронизации</h4>
                            <Button
                                type="button"
                                color="ghost"
                                size="sm"
                                :loading="syncOperationsLoading"
                                @click="loadSalesSyncOperations"
                            >
                                Обновить список
                            </Button>
                        </div>
                        <div v-if="syncOperationsLoading" class="restaurants__sync-operations-empty">
                            Загрузка операций...
                        </div>
                        <Table v-else-if="syncOperations.length">
                            <thead>
                                <tr>
                                    <th>PID</th>
                                    <th>Статус</th>
                                    <th>Запущено</th>
                                    <th>Длительность</th>
                                    <th>Инициатор</th>
                                    <th class="admin-page__actions">Действия</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="row in syncOperations" :key="row.pid">
                                    <td>{{ row.pid }}</td>
                                    <td>{{ formatOperationStage(row) }}</td>
                                    <td>{{ formatDateTime(row.started_at) }}</td>
                                    <td>{{ formatOperationAge(row.age_seconds) }}</td>
                                    <td>{{ row.actor || '—' }}</td>
                                    <td class="admin-page__actions">
                                        <Button
                                            type="button"
                                            color="danger"
                                            size="sm"
                                            :loading="stoppingOperationPid === row.pid"
                                            :disabled="stoppingOperationPid !== null"
                                            @click="cancelSalesSyncOperation(row)"
                                        >
                                            Остановить
                                        </Button>
                                    </td>
                                </tr>
                            </tbody>
                        </Table>
                        <div v-else class="restaurants__sync-operations-empty">
                            Активных операций нет.
                        </div>
                    </div>

                    <p v-if="syncSettingsSummary" class="restaurants__sync-summary">{{ syncSettingsSummary }}</p>
                </template>
            </div>
            <template #footer>
                <Button
                    v-if="editModalTab === 'main'"
                    type="button"
                    color="primary"
                    :loading="saving"
                    :disabled="!canManageRestaurantSettings"
                    @click="handleUpdateRestaurant"
                >
                    Сохранить
                </Button>
                <Button
                    v-else
                    type="button"
                    color="primary"
                    :loading="syncSettingsSaving"
                    :disabled="!canManageRestaurantSettings"
                    @click="saveSalesSyncSettings"
                >
                    Сохранить настройки
                </Button>
                <Button
                    type="button"
                    color="ghost"
                    :disabled="saving || syncSettingsSaving || syncSettingsRunning"
                    @click="cancelEditRestaurant"
                >
                    Отмена
                </Button>
                <Button
                    type="button"
                    color="danger"
                    :loading="deletingRestaurant"
                    :disabled="saving || syncSettingsSaving || syncSettingsRunning || !canManageRestaurants"
                    @click="handleDeleteCurrentRestaurant"
                >
                    Удалить
                </Button>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import {
    cancelRestaurantSalesSyncOperation,
    createRestaurant,
    deleteRestaurant,
    fetchCompanies,
    fetchRestaurantSalesSyncOperations,
    fetchRestaurantSalesSyncSettings,
    fetchRestaurantsByCompany,
    runRestaurantSalesSync,
    updateRestaurant,
    updateRestaurantSalesSyncSettings,
} from '@/api';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Button from '@/components/UI-components/Button.vue';
import Table from '@/components/UI-components/Table.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import { formatDateTimeValue } from '@/utils/format';

const userStore = useUserStore();
const toast = useToast();

const canViewRestaurants = computed(() =>
    userStore.hasAnyPermission(
        'restaurants.manage',
        'restaurants.view',
        'restaurants.settings.view',
        'restaurants.settings.manage',
        'system.admin',
    ),
);
const canManageRestaurants = computed(() =>
    userStore.hasAnyPermission('restaurants.manage', 'system.admin'),
);
const canManageRestaurantSettings = computed(() =>
    userStore.hasAnyPermission(
        'restaurants.settings.manage',
        'restaurants.manage',
        'system.admin',
    ),
);
const canManageIiko = computed(() =>
    userStore.hasAnyPermission('iiko.manage', 'system.admin'),
);
const canRunSalesSync = computed(() =>
    canManageIiko.value || canManageRestaurantSettings.value,
);

const restaurants = ref([]);
const loading = ref(false);
const saving = ref(false);
const search = ref('');

const editRestaurant = ref(null);
const editModalTab = ref('main');
const isCreateRestaurantModalOpen = ref(false);

const restaurantName = ref('');
const restaurantServer = ref('');
const restaurantDepartmentCode = ref('');
const restaurantIikoLogin = ref('');
const restaurantIikoPassword = ref('');
const restaurantParticipatesInSales = ref(true);

const deletingRestaurant = ref(false);
const syncSettingsLoading = ref(false);
const syncSettingsSaving = ref(false);
const syncSettingsRunning = ref(false);
const syncSettingsSummary = ref('');
const syncOperationsLoading = ref(false);
const syncOperations = ref([]);
const stoppingOperationPid = ref(null);
const syncRunFromDate = ref('');
const syncRunToDate = ref('');
const syncChunkProgressText = ref('');
const syncChunkRows = ref([]);
const salesSyncSettings = ref(createDefaultSalesSyncSettings());
const loadedSalesSyncSettingsRestaurantId = ref(null);
let syncOperationsPollTimer = null;
let loadRestaurantsPromise = null;
let loadRestaurantsRequestKey = '';
let syncOperationsRequestId = 0;
const SALES_SYNC_MANUAL_CHUNK_DAYS = 3;

const FALLBACK_COMPANY_ID = 1;
const defaultCompanyId = ref(null);
let isResolvingDefaultCompany = false;
const weekdayOptions = [
    { value: 0, label: 'Понедельник' },
    { value: 1, label: 'Вторник' },
    { value: 2, label: 'Среда' },
    { value: 3, label: 'Четверг' },
    { value: 4, label: 'Пятница' },
    { value: 5, label: 'Суббота' },
    { value: 6, label: 'Воскресенье' },
];

const filteredRestaurants = computed(() => {
    const list = Array.isArray(restaurants.value) ? restaurants.value : [];
    const query = (search.value || '').trim().toLocaleLowerCase('ru-RU');
    if (!query) {
        return list;
    }
    return list.filter((rest) => String(rest?.name ?? '').toLocaleLowerCase('ru-RU').includes(query));
});

async function ensureDefaultCompanyId() {
    if (defaultCompanyId.value !== null) {
        return defaultCompanyId.value;
    }

    if (isResolvingDefaultCompany) {
        return new Promise((resolve) => {
            const stop = watch(
                defaultCompanyId,
                (value) => {
                    if (value !== null) {
                        stop();
                        resolve(value);
                    }
                },
                { immediate: defaultCompanyId.value !== null },
            );
        });
    }

    isResolvingDefaultCompany = true;
    try {
        const data = await fetchCompanies();
        if (Array.isArray(data) && data.length > 0) {
            defaultCompanyId.value = data[0].id;
            return defaultCompanyId.value;
        }

        toast.error('Список компаний пуст. Создайте компанию, чтобы добавить ресторан.');
        defaultCompanyId.value = FALLBACK_COMPANY_ID;
        return defaultCompanyId.value;
    } catch (error) {
        console.error('Не удалось определить компанию для ресторана', error);
        defaultCompanyId.value = FALLBACK_COMPANY_ID;
        return defaultCompanyId.value;
    } finally {
        isResolvingDefaultCompany = false;
    }
}

function openCreateRestaurantModal() {
    if (!canManageRestaurants.value) {
        return;
    }
    isCreateRestaurantModalOpen.value = true;
}

function closeCreateRestaurantModal() {
    isCreateRestaurantModalOpen.value = false;
    restaurantName.value = '';
    restaurantServer.value = '';
    restaurantDepartmentCode.value = '';
    restaurantIikoLogin.value = '';
    restaurantIikoPassword.value = '';
    restaurantParticipatesInSales.value = true;
}

function openEditModal(rest) {
    if (!rest) {
        return;
    }
    editModalTab.value = 'main';
    syncSettingsSummary.value = '';
    syncChunkProgressText.value = '';
    syncChunkRows.value = [];
    const defaultTo = new Date().toISOString().slice(0, 10);
    const defaultFrom = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    syncRunToDate.value = defaultTo;
    syncRunFromDate.value = defaultFrom;
    editRestaurant.value = {
        ...rest,
        participates_in_sales: rest?.participates_in_sales !== false,
        iiko_password: '',
    };
}

function cancelEditRestaurant() {
    editRestaurant.value = null;
    saving.value = false;
    syncSettingsSummary.value = '';
    syncSettingsLoading.value = false;
    syncSettingsSaving.value = false;
    syncSettingsRunning.value = false;
    syncOperationsLoading.value = false;
    syncOperations.value = [];
    syncChunkProgressText.value = '';
    syncChunkRows.value = [];
    stoppingOperationPid.value = null;
    loadedSalesSyncSettingsRestaurantId.value = null;
    stopSalesSyncOperationsPolling();
    salesSyncSettings.value = createDefaultSalesSyncSettings();
}

async function handleCreateRestaurant() {
    if (!canManageRestaurants.value) {
        return;
    }
    const name = restaurantName.value.trim();
    const server = restaurantServer.value.trim();
    const iikoLogin = restaurantIikoLogin.value.trim();
    const iikoPassword = restaurantIikoPassword.value;
    if (!name || !server || !iikoLogin || !iikoPassword) {
        toast.error('Заполните обязательные поля');
        return;
    }
    try {
        saving.value = true;
        const companyId = await ensureDefaultCompanyId();
        await createRestaurant(companyId, {
            name,
            server,
            department_code: restaurantDepartmentCode.value.trim() || null,
            participates_in_sales: Boolean(restaurantParticipatesInSales.value),
            iiko_login: iikoLogin,
            iiko_password: iikoPassword,
        });
        toast.success('Ресторан создан');
        closeCreateRestaurantModal();
        await loadRestaurants();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Ошибка при создании ресторана');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

async function loadRestaurants() {
    if (!canViewRestaurants.value) {
        restaurants.value = [];
        return;
    }
    const companyId = await ensureDefaultCompanyId();
    const requestKey = `${Number(companyId) || 0}:view=${canViewRestaurants.value ? 1 : 0}`;
    if (loadRestaurantsPromise && loadRestaurantsRequestKey === requestKey) {
        return await loadRestaurantsPromise;
    }

    loading.value = true;
    const currentPromise = (async () => {
        try {
            const data = await fetchRestaurantsByCompany({
                company_id: companyId,
            });
            restaurants.value = Array.isArray(data)
                ? data.map((row) => ({
                    ...row,
                    participates_in_sales: row?.participates_in_sales !== false,
                }))
                : [];
        } catch (error) {
            if (error?.response?.status === 403) {
                restaurants.value = [];
            } else {
                toast.error('Не удалось загрузить рестораны');
                console.error(error);
            }
        } finally {
            loading.value = false;
        }
    })();

    loadRestaurantsPromise = currentPromise;
    loadRestaurantsRequestKey = requestKey;
    try {
        await currentPromise;
    } finally {
        if (loadRestaurantsPromise === currentPromise) {
            loadRestaurantsPromise = null;
            loadRestaurantsRequestKey = '';
        }
    }
}

async function handleUpdateRestaurant() {
    if (!canManageRestaurantSettings.value || !editRestaurant.value) return;
    try {
        saving.value = true;
        await updateRestaurant(editRestaurant.value.id, {
            name: editRestaurant.value.name,
            server: editRestaurant.value.server,
            department_code: editRestaurant.value.department_code || null,
            participates_in_sales: Boolean(editRestaurant.value.participates_in_sales),
            iiko_login: editRestaurant.value.iiko_login,
            iiko_password: editRestaurant.value.iiko_password,
        });
        toast.success('Ресторан обновлен');
        editRestaurant.value = null;
        await loadRestaurants();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Ошибка при обновлении ресторана');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

async function handleDeleteCurrentRestaurant() {
    if (!canManageRestaurants.value || !editRestaurant.value) return;
    const { id, name } = editRestaurant.value;
    if (!confirm(`Удалить ресторан "${name}" (ID ${id})?`)) return;

    try {
        deletingRestaurant.value = true;
        await deleteRestaurant(id);
        toast.success(`Ресторан "${name}" удален`);
        editRestaurant.value = null;
        await loadRestaurants();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Ошибка при удалении ресторана');
        console.error(error);
    } finally {
        deletingRestaurant.value = false;
    }
}

function createDefaultSalesSyncSettings() {
    return {
        auto_sync_enabled: false,
        daily_sync_time: '07:00',
        daily_lookback_days: 1,
        weekly_sync_enabled: true,
        weekly_sync_weekday: 0,
        weekly_sync_time: '08:00',
        weekly_lookback_days: 14,
        manual_default_lookback_days: 1,
        last_daily_run_on: null,
        last_weekly_run_on: null,
        last_sync_at: null,
        last_successful_sync_at: null,
        last_manual_sync_at: null,
        last_sync_scope: null,
        last_sync_status: null,
        last_sync_error: null,
    };
}

function normalizeSettingsPayload(payload) {
    return {
        ...createDefaultSalesSyncSettings(),
        ...(payload || {}),
        daily_lookback_days: Number(payload?.daily_lookback_days ?? 1),
        weekly_sync_weekday: Number(payload?.weekly_sync_weekday ?? 0),
        weekly_lookback_days: Number(payload?.weekly_lookback_days ?? 14),
        manual_default_lookback_days: Number(payload?.manual_default_lookback_days ?? 1),
    };
}

function formatDateTime(value) {
    return formatDateTimeValue(value, {
        emptyValue: '—',
        invalidValue: String(value),
        locale: 'ru-RU',
    });
}

async function loadSalesSyncSettings(restaurantId) {
    if (!restaurantId) {
        return;
    }
    syncSettingsLoading.value = true;
    try {
        const data = await fetchRestaurantSalesSyncSettings(restaurantId);
        salesSyncSettings.value = normalizeSettingsPayload(data);
        const defaultDaysBack = Math.max(0, Number(salesSyncSettings.value.manual_default_lookback_days || 1));
        const toDate = new Date();
        const fromDate = new Date();
        fromDate.setDate(fromDate.getDate() - defaultDaysBack);
        syncRunToDate.value = toDate.toISOString().slice(0, 10);
        syncRunFromDate.value = fromDate.toISOString().slice(0, 10);
        loadedSalesSyncSettingsRestaurantId.value = Number(restaurantId) || null;
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось загрузить настройки синхронизации');
    } finally {
        syncSettingsLoading.value = false;
    }
}

async function ensureSalesSyncSettingsLoaded(restaurantId, { force = false } = {}) {
    const normalizedId = Number(restaurantId);
    if (!Number.isFinite(normalizedId) || normalizedId <= 0) {
        return;
    }
    if (!force && loadedSalesSyncSettingsRestaurantId.value === normalizedId) {
        return;
    }
    await loadSalesSyncSettings(normalizedId);
}

async function loadSalesSyncOperations({ silent = false } = {}) {
    const restaurantId = Number(editRestaurant.value?.id);
    if (!restaurantId) {
        syncOperations.value = [];
        return;
    }
    const requestId = ++syncOperationsRequestId;
    if (!silent) {
        syncOperationsLoading.value = true;
    }
    try {
        const data = await fetchRestaurantSalesSyncOperations(restaurantId);
        if (requestId !== syncOperationsRequestId) {
            return;
        }
        syncOperations.value = Array.isArray(data?.operations) ? data.operations : [];
    } catch (error) {
        if (!silent && requestId === syncOperationsRequestId) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось загрузить операции синхронизации');
        }
    } finally {
        if (!silent && requestId === syncOperationsRequestId) {
            syncOperationsLoading.value = false;
        }
    }
}

async function cancelSalesSyncOperation(row) {
    const restaurantId = Number(editRestaurant.value?.id);
    const pid = Number(row?.pid);
    if (!restaurantId || !pid) {
        return;
    }
    stoppingOperationPid.value = pid;
    try {
        await cancelRestaurantSalesSyncOperation(restaurantId, { pid });
        toast.success(`Операция PID ${pid} остановлена`);
        await loadSalesSyncOperations({ silent: true });
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось остановить операцию');
    } finally {
        stoppingOperationPid.value = null;
    }
}

function stopSalesSyncOperationsPolling() {
    if (syncOperationsPollTimer) {
        clearInterval(syncOperationsPollTimer);
        syncOperationsPollTimer = null;
    }
}

function startSalesSyncOperationsPolling() {
    stopSalesSyncOperationsPolling();
    if (!editRestaurant.value || editModalTab.value !== 'sync') {
        return;
    }
    syncOperationsPollTimer = setInterval(() => {
        loadSalesSyncOperations({ silent: true });
    }, 5000);
}

function formatOperationAge(seconds) {
    const value = Number(seconds || 0);
    if (!Number.isFinite(value) || value <= 0) {
        return '0с';
    }
    const total = Math.floor(value);
    const mins = Math.floor(total / 60);
    const secs = total % 60;
    if (!mins) {
        return `${secs}с`;
    }
    return `${mins}м ${secs}с`;
}

function formatOperationStage(row) {
    const stage = String(row?.stage || '').toLowerCase();
    if (stage === 'queued') {
        return 'В очереди';
    }
    if (stage === 'running') {
        return 'Выполняется';
    }
    return row?.state || '—';
}

function parseIsoDate(value) {
    const text = String(value || '').trim();
    const match = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) {
        return null;
    }
    const year = Number(match[1]);
    const monthIndex = Number(match[2]) - 1;
    const day = Number(match[3]);
    const date = new Date(Date.UTC(year, monthIndex, day));
    return Number.isNaN(date.getTime()) ? null : date;
}

function formatIsoDate(date) {
    return date.toISOString().slice(0, 10);
}

function splitDateRangeByDays(fromDate, toDate, chunkDays = SALES_SYNC_MANUAL_CHUNK_DAYS) {
    const startDate = parseIsoDate(fromDate);
    const endDate = parseIsoDate(toDate);
    if (!startDate || !endDate || startDate > endDate) {
        return [];
    }
    const windows = [];
    let cursor = new Date(startDate);
    while (cursor <= endDate) {
        const chunkEnd = new Date(cursor);
        chunkEnd.setUTCDate(chunkEnd.getUTCDate() + Math.max(Number(chunkDays || 0), 1) - 1);
        if (chunkEnd > endDate) {
            chunkEnd.setTime(endDate.getTime());
        }
        windows.push({
            from_date: formatIsoDate(cursor),
            to_date: formatIsoDate(chunkEnd),
        });
        cursor = new Date(chunkEnd);
        cursor.setUTCDate(cursor.getUTCDate() + 1);
    }
    return windows;
}

function syncErrorDetail(error) {
    const detail = error?.response?.data?.detail;
    if (typeof detail === 'string') {
        return detail;
    }
    if (detail && typeof detail === 'object') {
        if (typeof detail.message === 'string' && detail.message) {
            return detail.message;
        }
        return JSON.stringify(detail);
    }
    return error?.message || 'Неизвестная ошибка';
}

function formatSyncChunkStatus(status) {
    const normalized = String(status || '').toLowerCase();
    if (normalized === 'running') {
        return 'Выполняется';
    }
    if (normalized === 'ok') {
        return 'Успешно';
    }
    if (normalized === 'error') {
        return 'Ошибка';
    }
    return 'Ожидание';
}

async function saveSalesSyncSettings() {
    if (!editRestaurant.value || !canManageRestaurantSettings.value) {
        return;
    }
    syncSettingsSaving.value = true;
    syncSettingsSummary.value = '';
    try {
        const payload = {
            auto_sync_enabled: Boolean(salesSyncSettings.value.auto_sync_enabled),
            daily_sync_time: String(salesSyncSettings.value.daily_sync_time || '07:00'),
            daily_lookback_days: Number(salesSyncSettings.value.daily_lookback_days || 0),
            weekly_sync_enabled: Boolean(salesSyncSettings.value.weekly_sync_enabled),
            weekly_sync_weekday: Number(salesSyncSettings.value.weekly_sync_weekday || 0),
            weekly_sync_time: String(salesSyncSettings.value.weekly_sync_time || '08:00'),
            weekly_lookback_days: Number(salesSyncSettings.value.weekly_lookback_days || 0),
            manual_default_lookback_days: Number(salesSyncSettings.value.manual_default_lookback_days || 0),
        };
        const data = await updateRestaurantSalesSyncSettings(editRestaurant.value.id, payload);
        salesSyncSettings.value = normalizeSettingsPayload(data);
        syncSettingsSummary.value = 'Настройки синхронизации сохранены.';
        toast.success('Настройки синхронизации сохранены');
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Ошибка при сохранении настроек синхронизации');
    } finally {
        syncSettingsSaving.value = false;
    }
}

async function runManualSalesSync() {
    if (!editRestaurant.value || !canRunSalesSync.value) {
        return;
    }
    if (!syncRunFromDate.value || !syncRunToDate.value) {
        toast.error('Укажите обе даты для ручной синхронизации');
        return;
    }
    if (syncRunFromDate.value > syncRunToDate.value) {
        toast.error('Дата "С" не может быть позже даты "По"');
        return;
    }

    syncSettingsRunning.value = true;
    syncSettingsSummary.value = '';
    syncChunkProgressText.value = '';
    syncChunkRows.value = [];
    try {
        const windows = splitDateRangeByDays(syncRunFromDate.value, syncRunToDate.value, SALES_SYNC_MANUAL_CHUNK_DAYS);
        if (!windows.length) {
            toast.error('Не удалось разбить период на окна синхронизации');
            return;
        }

        syncChunkRows.value = windows.map((window, index) => ({
            index: index + 1,
            from_date: window.from_date,
            to_date: window.to_date,
            status: 'pending',
            summary: '',
            detail: '',
        }));

        const totals = {
            windows: windows.length,
            ok: 0,
            error: 0,
            orders: 0,
            items: 0,
            mapped_orders: 0,
            unmapped_orders: 0,
            routing_conflicts: 0,
        };

        for (const row of syncChunkRows.value) {
            row.status = 'running';
            row.summary = '';
            row.detail = '';
            syncChunkProgressText.value = `Окно ${row.index} из ${windows.length}: ${row.from_date} — ${row.to_date}`;
            try {
                const data = await runRestaurantSalesSync(editRestaurant.value.id, {
                    from_date: row.from_date,
                    to_date: row.to_date,
                });
                const result = data?.result || {};
                const settings = data?.settings || {};
                salesSyncSettings.value = normalizeSettingsPayload(settings);
                row.status = 'ok';
                row.summary =
                    `orders=${result.orders || 0}, items=${result.items || 0}, ` +
                    `mapped=${result.mapped_orders || 0}, unmapped=${result.unmapped_orders || 0}`;

                totals.ok += 1;
                totals.orders += Number(result.orders || 0);
                totals.items += Number(result.items || 0);
                totals.mapped_orders += Number(result.mapped_orders || 0);
                totals.unmapped_orders += Number(result.unmapped_orders || 0);
                totals.routing_conflicts += Number(result.routing_conflicts || 0);
            } catch (error) {
                row.status = 'error';
                row.detail = syncErrorDetail(error);
                totals.error += 1;
            }
        }

        syncChunkProgressText.value = `Готово: успешно ${totals.ok} из ${totals.windows}, ошибок ${totals.error}.`;
        syncSettingsSummary.value =
            `Ручная синхронизация: окон=${totals.windows}, успешно=${totals.ok}, ошибок=${totals.error}, ` +
            `orders=${totals.orders}, items=${totals.items}, mapped_orders=${totals.mapped_orders}, ` +
            `unmapped_orders=${totals.unmapped_orders}, routing_conflicts=${totals.routing_conflicts}`;

        if (totals.error > 0) {
            toast.warning(`Синхронизация завершена с ошибками: ${totals.error} из ${totals.windows}`);
        } else {
            toast.success('Ручная синхронизация выполнена');
        }
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Ошибка ручной синхронизации');
    } finally {
        syncSettingsRunning.value = false;
        loadSalesSyncOperations({ silent: true });
    }
}

onMounted(() => {
    if (canViewRestaurants.value) {
        ensureDefaultCompanyId();
        loadRestaurants();
    }
});

onBeforeUnmount(() => {
    stopSalesSyncOperationsPolling();
});

watch(
    () => canViewRestaurants.value,
    (canView) => {
        if (!canView) {
            restaurants.value = [];
            isCreateRestaurantModalOpen.value = false;
            editRestaurant.value = null;
            return;
        }
        ensureDefaultCompanyId();
        loadRestaurants();
    },
);

watch(
    () => [editRestaurant.value?.id, editModalTab.value],
    async ([restaurantId, tab]) => {
        if (!restaurantId || tab !== 'sync') {
            stopSalesSyncOperationsPolling();
            return;
        }
        await ensureSalesSyncSettingsLoaded(restaurantId);
        await loadSalesSyncOperations({ silent: true });
        startSalesSyncOperationsPolling();
    },
);
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/staff-restaurants' as *;
</style>
