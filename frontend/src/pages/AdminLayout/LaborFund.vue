<template>
    <div class="labor-fund">
        <section
            v-if="canViewLaborSummary"
            class="labor-fund__card labor-fund__card--filters"
        >
            <header class="labor-fund__card-header labor-fund__card-header--filters">
                <div class="labor-fund__header-main">
                    <p class="labor-fund__section-label">Дашборд</p>
                    <h3 class="labor-fund__card-title">Фонд оплаты труда</h3>
                    <p class="labor-fund__subtitle">
                        Выберите фильтры и нажмите «Построить отчет», чтобы загрузить дашборд.
                    </p>
                </div>
            </header>

            <section class="labor-fund__filters-panel">
                <div class="labor-fund__filters-panel-header">
                    <p class="labor-fund__filters-panel-title">Фильтры</p>
                    <div class="labor-fund__filters-panel-controls">
                        <Button
                            v-if="canManageLaborSummarySettings && canViewLaborSummaryCost"
                            color="ghost"
                            size="sm"
                            :disabled="settingsLoading || !hasSelectedRestaurants"
                            @click="openSettingsModal"
                        >
                            Настройки расчета
                        </Button>
                        <button
                            type="button"
                            class="labor-fund__collapse-trigger"
                            :aria-expanded="filtersExpanded"
                            aria-label="Развернуть или свернуть фильтры"
                            @click="toggleFiltersExpanded"
                        >
                            <span :class="['labor-fund__collapse-icon', { 'is-open': filtersExpanded }]">▼</span>
                        </button>
                    </div>
                </div>

                <p v-if="!filtersExpanded" class="labor-fund__filters-summary">
                    {{ filtersSummary }}
                </p>

                <div v-show="filtersExpanded" class="labor-fund__filters-body">
                    <div class="labor-fund__filters-layout">
                        <div class="labor-fund__filters-stack">
                            <div :ref="(el) => setFilterRef('restaurants', el)" class="labor-fund__filter-picker">
                                <p class="labor-fund__filter-title">Рестораны</p>
                                <button
                                    type="button"
                                    class="labor-fund__filter-picker-trigger"
                                    :disabled="!restaurantOptions.length"
                                    @click="toggleFilterDropdown('restaurants')"
                                >
                                    <span
                                        :class="[
                                            'labor-fund__filter-picker-value',
                                            { 'is-placeholder': !restaurantSelectionLabel },
                                        ]"
                                    >
                                        {{ restaurantSelectionLabel || 'Выберите ресторан' }}
                                    </span>
                                    <span
                                        :class="[
                                            'labor-fund__filter-picker-icon',
                                            { 'is-open': dropdownState.restaurants },
                                        ]"
                                    >
                                        ▼
                                    </span>
                                </button>
                                <div v-if="dropdownState.restaurants" class="labor-fund__filter-picker-menu">
                                    <div class="labor-fund__filter-picker-actions">
                                        <button
                                            type="button"
                                            class="labor-fund__filter-picker-clear"
                                            @click="toggleAllRestaurants(true)"
                                        >
                                            Все рестораны
                                        </button>
                                        <button
                                            type="button"
                                            class="labor-fund__filter-picker-clear"
                                            @click="toggleAllRestaurants(false)"
                                        >
                                            Сброс
                                        </button>
                                    </div>
                                    <div class="labor-fund__filter-picker-options">
                                        <label
                                            v-for="option in restaurantOptions"
                                            :key="option.value"
                                            class="labor-fund__filter-picker-option"
                                        >
                                            <input
                                                type="checkbox"
                                                :checked="isRestaurantSelected(option.value)"
                                                @change="(event) => toggleRestaurantSelection(option.value, event.target.checked)"
                                            />
                                            <span>{{ option.label }}</span>
                                        </label>
                                    </div>
                                </div>
                            </div>

                            <div :ref="(el) => setFilterRef('subdivisions', el)" class="labor-fund__filter-picker">
                                <p class="labor-fund__filter-title">Подразделения</p>
                                <button
                                    type="button"
                                    class="labor-fund__filter-picker-trigger"
                                    :disabled="!hasSelectedRestaurants || optionsLoading"
                                    @click="toggleFilterDropdown('subdivisions')"
                                >
                                    <span
                                        :class="[
                                            'labor-fund__filter-picker-value',
                                            { 'is-placeholder': !subdivisionSelectionLabel },
                                        ]"
                                    >
                                        {{ subdivisionSelectionLabel || 'Выберите подразделение' }}
                                    </span>
                                    <span
                                        :class="[
                                            'labor-fund__filter-picker-icon',
                                            { 'is-open': dropdownState.subdivisions },
                                        ]"
                                    >
                                        ▼
                                    </span>
                                </button>
                                <div v-if="dropdownState.subdivisions" class="labor-fund__filter-picker-menu">
                                    <input
                                        v-model="subdivisionSearch"
                                        type="text"
                                        class="labor-fund__filter-picker-search"
                                        placeholder="Поиск подразделения"
                                    />
                                    <div class="labor-fund__filter-picker-actions">
                                        <button
                                            type="button"
                                            class="labor-fund__filter-picker-clear"
                                            @click="toggleAllSubdivisions(true)"
                                        >
                                            Все подразделения
                                        </button>
                                        <button
                                            type="button"
                                            class="labor-fund__filter-picker-clear"
                                            @click="toggleAllSubdivisions(false)"
                                        >
                                            Сброс
                                        </button>
                                    </div>
                                    <div class="labor-fund__filter-picker-options">
                                        <label
                                            v-for="option in filteredSubdivisionOptions"
                                            :key="option.value"
                                            class="labor-fund__filter-picker-option"
                                        >
                                            <input
                                                type="checkbox"
                                                :checked="isSubdivisionSelected(option.value)"
                                                @change="(event) => toggleSubdivisionSelection(option.value, event.target.checked)"
                                            />
                                            <span>{{ option.label }}</span>
                                        </label>
                                        <p
                                            v-if="!filteredSubdivisionOptions.length"
                                            class="labor-fund__filter-picker-empty"
                                        >
                                            Ничего не найдено
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <div :ref="(el) => setFilterRef('positions', el)" class="labor-fund__filter-picker">
                                <p class="labor-fund__filter-title">Должности</p>
                                <button
                                    type="button"
                                    class="labor-fund__filter-picker-trigger"
                                    :disabled="!hasSelectedRestaurants || optionsLoading"
                                    @click="toggleFilterDropdown('positions')"
                                >
                                    <span
                                        :class="[
                                            'labor-fund__filter-picker-value',
                                            { 'is-placeholder': !positionSelectionLabel },
                                        ]"
                                    >
                                        {{ positionSelectionLabel || 'Выберите должность' }}
                                    </span>
                                    <span
                                        :class="[
                                            'labor-fund__filter-picker-icon',
                                            { 'is-open': dropdownState.positions },
                                        ]"
                                    >
                                        ▼
                                    </span>
                                </button>
                                <div v-if="dropdownState.positions" class="labor-fund__filter-picker-menu">
                                    <input
                                        v-model="positionSearch"
                                        type="text"
                                        class="labor-fund__filter-picker-search"
                                        placeholder="Поиск должности"
                                    />
                                    <div class="labor-fund__filter-picker-actions">
                                        <button
                                            type="button"
                                            class="labor-fund__filter-picker-clear"
                                            @click="toggleAllPositions(true)"
                                        >
                                            Все должности
                                        </button>
                                        <button
                                            type="button"
                                            class="labor-fund__filter-picker-clear"
                                            @click="toggleAllPositions(false)"
                                        >
                                            Сброс
                                        </button>
                                    </div>
                                    <div class="labor-fund__filter-picker-options">
                                        <label
                                            v-for="option in filteredPositionOptions"
                                            :key="option.value"
                                            class="labor-fund__filter-picker-option"
                                        >
                                            <input
                                                type="checkbox"
                                                :checked="isPositionSelected(option.value)"
                                                @change="(event) => togglePositionSelection(option.value, event.target.checked)"
                                            />
                                            <span>{{ option.label }}</span>
                                        </label>
                                        <p
                                            v-if="!filteredPositionOptions.length"
                                            class="labor-fund__filter-picker-empty"
                                        >
                                            Ничего не найдено
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="labor-fund__filters-side">
                            <div class="labor-fund__filter-block labor-fund__filter-block--dates">
                                <div class="labor-fund__filter-title">Период</div>
                                <div class="labor-fund__filter-dates">
                                    <DateInput v-model="dateFrom" label="Дата с" />
                                    <DateInput v-model="dateTo" label="Дата по" />
                                </div>
                            </div>
                        </div>
                    </div>

                    <p v-if="canViewLaborSummaryCost" class="labor-fund__settings-summary">
                        Настройки расчета затрат применяются автоматически:
                        <span>{{ laborSettingsSummary }}</span>
                    </p>
                    <p v-if="settingsError" class="labor-fund__filter-note labor-fund__filter-note--warn">
                        {{ settingsError }}
                    </p>

                    <div v-if="optionsError" class="labor-fund__state labor-fund__state--error">
                        {{ optionsError }}
                    </div>
                    <div v-if="filtersError" class="labor-fund__state labor-fund__state--error">
                        {{ filtersError }}
                    </div>

                    <div class="labor-fund__filters-actions">
                        <Button
                            color="primary"
                            size="sm"
                            :loading="laborSummaryLoading"
                            @click="applyFilters"
                        >
                            Построить отчет
                        </Button>
                        <Button
                            color="ghost"
                            size="sm"
                            :disabled="laborSummaryLoading"
                            @click="resetFilters"
                        >
                            Сброс
                        </Button>
                    </div>
                </div>
            </section>
        </section>
        <p v-else class="labor-fund__state labor-fund__state--error">
            Нет доступа к ФОТ.
        </p>

        <section
            v-if="canViewLaborSummary && hasAppliedFilters"
            class="labor-fund__card labor-fund__card--results"
        >
            <header class="labor-fund__card-header">
                <div>
                    <p class="labor-fund__section-label">{{ appliedPeriodLabel }}</p>
                    <h3 class="labor-fund__card-title">Часы по подразделениям</h3>
                </div>
                <div class="labor-fund__results-actions">
                    <Select v-model="chartMetric" label="Метрика" :options="chartMetricOptions" />
                </div>
            </header>

            <div v-if="isDirty" class="labor-fund__state">
                Фильтры изменены. Нажмите «Построить отчет», чтобы обновить дашборд.
            </div>

            <div v-if="laborSummaryLoading" class="labor-fund__state">Загрузка данных...</div>
            <div v-else-if="laborSummaryError" class="labor-fund__state labor-fund__state--error">
                {{ laborSummaryError }}
            </div>
            <div v-else-if="!laborSummaryRows.length" class="labor-fund__state">
                Данные пока не найдены.
            </div>
            <div v-else>
                <div class="labor-fund__stats">
                    <div class="labor-fund__stat-card">
                        <div class="labor-fund__stat-label">Часы</div>
                        <div class="labor-fund__stat-value">
                            {{ formatHours(laborSummaryTotals?.hours) }}
                        </div>
                    </div>
                    <div class="labor-fund__stat-card">
                        <div class="labor-fund__stat-label">Ночные часы</div>
                        <div class="labor-fund__stat-value">
                            {{ formatHours(laborSummaryTotals?.night_hours) }}
                        </div>
                    </div>
                    <div v-if="showCostAccrual" class="labor-fund__stat-card">
                        <div class="labor-fund__stat-label">Начисления</div>
                        <div class="labor-fund__stat-value">
                            {{ formatAmount(laborSummaryTotals?.accrual_amount) }}
                        </div>
                    </div>
                    <div v-if="showCostDeduction" class="labor-fund__stat-card">
                        <div class="labor-fund__stat-label">Удержания</div>
                        <div class="labor-fund__stat-value">
                            {{ formatAmount(laborSummaryTotals?.deduction_amount) }}
                        </div>
                    </div>
                    <div v-if="showCostTotal" class="labor-fund__stat-card">
                        <div class="labor-fund__stat-label">Факт затрат</div>
                        <div class="labor-fund__stat-value">
                            {{ formatAmount(laborSummaryTotals?.total_cost) }}
                        </div>
                    </div>
                    <div v-if="showRevenueMetrics" class="labor-fund__stat-card">
                        <div class="labor-fund__stat-label">Выручка</div>
                        <div class="labor-fund__stat-value">
                            {{ formatAmount(laborSummaryTotals?.revenue_amount) }}
                        </div>
                    </div>
                    <div v-if="showLaborToRevenueRatio" class="labor-fund__stat-card">
                        <div class="labor-fund__stat-label">ФОТ / Выручка</div>
                        <div class="labor-fund__stat-value">
                            {{ formatPercent(laborToRevenuePercentValue) }}
                        </div>
                    </div>
                </div>

                <div class="labor-fund__charts labor-fund__charts--summary">
                    <div class="labor-fund__chart-card labor-fund__chart-card--histogram">
                        <div class="labor-fund__summary-chart-header">
                            <div>
                                <div class="labor-fund__chart-title">Сводка ФОТ: подразделения и должности</div>
                                <div class="labor-fund__chart-subtitle">{{ summaryHistogramSubtitle }}</div>
                            </div>
                            <Button
                                v-if="summaryHistogramSelectedSubdivision"
                                color="ghost"
                                size="sm"
                                @click="resetSummaryHistogramDrilldown"
                            >
                                Назад к подразделениям
                            </Button>
                        </div>
                        <div v-if="!summaryHistogramItems.length" class="labor-fund__muted">
                            Нет данных.
                        </div>
                        <VChart
                            v-else
                            class="labor-fund__summary-histogram"
                            :option="summaryHistogramOption"
                            autoresize
                            @click="handleSummaryHistogramClick"
                        />
                        <p class="labor-fund__chart-hint">
                            Клик по столбцу подразделения показывает столбцы должностей этого подразделения.
                            Бледно-красным выделяются топ-5 должностей по текущей метрике.
                        </p>
                    </div>
                </div>
            </div>
        </section>

        <Modal v-if="settingsModalOpen && canManageLaborSummarySettings && canViewLaborSummaryCost" @close="closeSettingsModal">
            <template #header>
                <div class="labor-fund__settings-modal-header">
                    <h3 class="labor-fund__settings-modal-title">Настройки расчета ФОТ</h3>
                    <button type="button" class="labor-fund__settings-modal-close" @click="closeSettingsModal">✕</button>
                </div>
            </template>

            <div class="labor-fund__settings-grid">
                <p v-if="settingsError" class="labor-fund__filter-note labor-fund__filter-note--warn">
                    {{ settingsError }}
                </p>
                <div class="labor-fund__filter-block labor-fund__filter-block--cost">
                    <div class="labor-fund__filter-title">Состав затрат</div>
                    <div class="labor-fund__filter-inline-options">
                        <label class="labor-fund__filter-inline-item">
                            <input v-model="includeAccrualCost" type="checkbox" />
                            <span>Начисления</span>
                        </label>
                        <label class="labor-fund__filter-inline-item">
                            <input v-model="includeDeductionCost" type="checkbox" />
                            <span>Удержания</span>
                        </label>
                    </div>
                    <p class="labor-fund__filter-help">
                        Выбранные компоненты используются в колонках затрат и в «Факт затрат».
                    </p>
                </div>
                <div class="labor-fund__filter-block">
                    <div class="labor-fund__filter-title">Какие начисления и удержания учитывать</div>
                    <p class="labor-fund__filter-help">
                        Выбранные типы участвуют в расчетах «Начисления», «Удержания» и «Факт затрат».
                    </p>
                    <div v-if="adjustmentTypesLoading" class="labor-fund__muted">
                        Загрузка типов корректировок...
                    </div>
                    <p v-else-if="adjustmentTypesError" class="labor-fund__filter-note labor-fund__filter-note--warn">
                        {{ adjustmentTypesError }}
                    </p>
                    <div v-else class="labor-fund__types-grid">
                        <div class="labor-fund__types-group">
                            <div class="labor-fund__types-header">
                                <span>Начисления</span>
                                <div class="labor-fund__types-actions">
                                    <button
                                        type="button"
                                        class="labor-fund__types-action"
                                        @click="toggleAllAccrualTypes(true)"
                                    >
                                        Все
                                    </button>
                                    <button
                                        type="button"
                                        class="labor-fund__types-action"
                                        @click="toggleAllAccrualTypes(false)"
                                    >
                                        Сброс
                                    </button>
                                </div>
                            </div>
                            <div class="labor-fund__types-list">
                                <label
                                    v-for="option in accrualAdjustmentTypeOptions"
                                    :key="`accrual:${option.value}`"
                                    class="labor-fund__type-option"
                                >
                                    <input
                                        v-model="selectedAccrualAdjustmentTypeIds"
                                        type="checkbox"
                                        :value="option.value"
                                    />
                                    <span>{{ option.label }}</span>
                                </label>
                                <p
                                    v-if="!accrualAdjustmentTypeOptions.length"
                                    class="labor-fund__filter-picker-empty"
                                >
                                    Нет доступных типов
                                </p>
                            </div>
                        </div>
                        <div class="labor-fund__types-group">
                            <div class="labor-fund__types-header">
                                <span>Удержания</span>
                                <div class="labor-fund__types-actions">
                                    <button
                                        type="button"
                                        class="labor-fund__types-action"
                                        @click="toggleAllDeductionTypes(true)"
                                    >
                                        Все
                                    </button>
                                    <button
                                        type="button"
                                        class="labor-fund__types-action"
                                        @click="toggleAllDeductionTypes(false)"
                                    >
                                        Сброс
                                    </button>
                                </div>
                            </div>
                            <div class="labor-fund__types-list">
                                <label
                                    v-for="option in deductionAdjustmentTypeOptions"
                                    :key="`deduction:${option.value}`"
                                    class="labor-fund__type-option"
                                >
                                    <input
                                        v-model="selectedDeductionAdjustmentTypeIds"
                                        type="checkbox"
                                        :value="option.value"
                                    />
                                    <span>{{ option.label }}</span>
                                </label>
                                <p
                                    v-if="!deductionAdjustmentTypeOptions.length"
                                    class="labor-fund__filter-picker-empty"
                                >
                                    Нет доступных типов
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="labor-fund__filter-block">
                    <div class="labor-fund__filter-title">Выручка для показателя ФОТ</div>
                    <div class="labor-fund__filter-inline-options">
                        <label class="labor-fund__filter-inline-item">
                            <input v-model="revenueExcludeDeleted" type="checkbox" />
                            <span>Без удаленных заказов</span>
                        </label>
                        <label class="labor-fund__filter-inline-item">
                            <input v-model="revenueRealMoneyOnly" type="checkbox" />
                            <span>Только реальные деньги</span>
                        </label>
                    </div>
                    <Select
                        v-model="revenueAmountMode"
                        class="labor-fund__inline-select"
                        label="База выручки"
                        :options="revenueAmountModeOptions"
                    />
                </div>
            </div>

            <template #footer>
                <Button color="ghost" :disabled="settingsSaving" @click="closeSettingsModal">Отмена</Button>
                <Button color="primary" :loading="settingsSaving" @click="saveSettings">Сохранить настройки</Button>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { use } from 'echarts/core';
import { BarChart } from 'echarts/charts';
import { CanvasRenderer } from 'echarts/renderers';
import { GridComponent, TooltipComponent } from 'echarts/components';
import {
    fetchLaborSummary,
    fetchLaborSummaryOptions,
    fetchLaborSummarySettings,
    fetchPayrollAdjustmentTypes,
    fetchRestaurants,
    updateLaborSummarySettings,
} from '@/api';
import { useUserStore } from '@/stores/user';
import Button from '@/components/UI-components/Button.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import { useClickOutside } from '@/composables/useClickOutside';
import VChart from 'vue-echarts';

use([
    CanvasRenderer,
    BarChart,
    GridComponent,
    TooltipComponent,
]);

const userStore = useUserStore();

const restaurants = ref([]);
const selectedRestaurantIds = ref([]);

const optionsLoading = ref(false);
const optionsError = ref('');
const subdivisions = ref([]);
const positions = ref([]);
const adjustmentTypes = ref([]);
const adjustmentTypesLoading = ref(false);
const adjustmentTypesError = ref('');

const selectedSubdivisionIds = ref([]);
const selectedPositionIds = ref([]);
const selectedAccrualAdjustmentTypeIds = ref([]);
const selectedDeductionAdjustmentTypeIds = ref([]);
const subdivisionSearch = ref('');
const positionSearch = ref('');

const dateFrom = ref(getCurrentMonthStartIso());
const dateTo = ref(getTodayIso());

const includeBaseCost = ref(true);
const includeAccrualCost = ref(true);
const includeDeductionCost = ref(true);
const revenueExcludeDeleted = ref(true);
const revenueRealMoneyOnly = ref(true);
const revenueAmountMode = ref('sum_without_discount');
const settingsModalOpen = ref(false);
const settingsLoading = ref(false);
const settingsSaving = ref(false);
const settingsError = ref('');
const settingsSnapshot = ref(null);
const settingsLoaded = ref(false);
const settingsUseAllAccrualTypes = ref(true);
const settingsUseAllDeductionTypes = ref(true);

const filtersError = ref('');
const appliedFilters = ref(null);
const isDirty = ref(false);

const laborSummary = ref(null);
const laborSummaryLoading = ref(false);
const laborSummaryError = ref('');

const chartMetric = ref('hours');
const summaryHistogramSubdivisionKey = ref('');
const filtersExpanded = ref(false);
const defaultReportInitializing = ref(false);
const defaultReportInitialized = ref(false);
const optionsRequestId = ref(0);
const summaryRequestId = ref(0);
const optionsDebounceTimer = ref(null);
const optionsCache = new Map();
const summaryCache = new Map();

const dropdownState = reactive({
    restaurants: false,
    subdivisions: false,
    positions: false,
});

const filterRefs = reactive({
    restaurants: null,
    subdivisions: null,
    positions: null,
});

const canViewLaborSummary = computed(() =>
    userStore.hasAnyPermission('labor.summary.dashboard.view', 'labor.summary.view'),
);
const canViewLaborSummaryCost = computed(() =>
    userStore.hasPermission('labor.summary.view_cost'),
);
const canManageLaborSummarySettings = computed(() =>
    userStore.hasPermission('labor.summary.settings.manage'),
);
const revenueAmountModeOptions = [
    { value: 'sum_without_discount', label: 'Сумма без скидок' },
    { value: 'sum_with_discount', label: 'Сумма со скидками' },
    { value: 'discount_only', label: 'Только скидки' },
];

const restaurantOptions = computed(() => {
    const list = Array.isArray(restaurants.value) ? restaurants.value : [];
    return list.map((restaurant) => ({
        label: restaurant?.name || `Ресторан #${restaurant?.id}`,
        value: restaurant?.id,
    }));
});

const selectedRestaurantIdsNormalized = computed(() => normalizeNumbers(selectedRestaurantIds.value));

const hasSelectedRestaurants = computed(() => selectedRestaurantIdsNormalized.value.length > 0);

const subdivisionOptions = computed(() => {
    const list = Array.isArray(subdivisions.value) ? subdivisions.value : [];
    const unique = new Map();

    list.forEach((item) => {
        const id = Number(item?.id);
        if (!Number.isFinite(id)) {
            return;
        }
        unique.set(id, item?.name || `Подразделение #${id}`);
    });

    return Array.from(unique.entries())
        .map(([id, name]) => ({ value: id, label: name }))
        .sort((a, b) => a.label.localeCompare(b.label, 'ru'));
});

const positionOptions = computed(() => {
    const list = Array.isArray(positions.value) ? positions.value : [];
    const unique = new Map();

    list.forEach((item) => {
        const id = Number(item?.id);
        if (!Number.isFinite(id)) {
            return;
        }
        const name = item?.name || `Должность #${id}`;
        unique.set(id, name);
    });

    return Array.from(unique.entries())
        .map(([id, name]) => ({ value: id, label: name }))
        .sort((a, b) => a.label.localeCompare(b.label, 'ru'));
});

const accrualAdjustmentTypeOptions = computed(() => {
    const list = Array.isArray(adjustmentTypes.value) ? adjustmentTypes.value : [];
    return list
        .filter((item) => String(item?.kind || '') === 'accrual')
        .map((item) => ({
            value: Number(item?.id),
            label: String(item?.name || `Начисление #${item?.id || '?'}`),
        }))
        .filter((item) => Number.isFinite(item.value))
        .sort((a, b) => a.label.localeCompare(b.label, 'ru'));
});

const deductionAdjustmentTypeOptions = computed(() => {
    const list = Array.isArray(adjustmentTypes.value) ? adjustmentTypes.value : [];
    return list
        .filter((item) => String(item?.kind || '') === 'deduction')
        .map((item) => ({
            value: Number(item?.id),
            label: String(item?.name || `Удержание #${item?.id || '?'}`),
        }))
        .filter((item) => Number.isFinite(item.value))
        .sort((a, b) => a.label.localeCompare(b.label, 'ru'));
});

const selectedSubdivisionIdsNormalized = computed(() => normalizeNumbers(selectedSubdivisionIds.value));
const selectedPositionIdsNormalized = computed(() => normalizeNumbers(selectedPositionIds.value));
const selectedAccrualAdjustmentTypeIdsNormalized = computed(() =>
    normalizeNumbers(selectedAccrualAdjustmentTypeIds.value),
);
const selectedDeductionAdjustmentTypeIdsNormalized = computed(() =>
    normalizeNumbers(selectedDeductionAdjustmentTypeIds.value),
);

const filteredSubdivisionOptions = computed(() => {
    const q = subdivisionSearch.value.trim().toLowerCase();
    if (!q) {
        return subdivisionOptions.value;
    }
    return subdivisionOptions.value.filter((option) => option.label.toLowerCase().includes(q));
});

const filteredPositionOptions = computed(() => {
    const q = positionSearch.value.trim().toLowerCase();
    if (!q) {
        return positionOptions.value;
    }
    return positionOptions.value.filter((option) => option.label.toLowerCase().includes(q));
});

const restaurantSelectionLabel = computed(() =>
    buildFilterSelectionLabel({
        selectedIds: selectedRestaurantIdsNormalized.value,
        options: restaurantOptions.value,
        fallback: 'Все рестораны',
    }),
);

const subdivisionSelectionLabel = computed(() => {
    if (!hasSelectedRestaurants.value) {
        return 'Сначала выберите ресторан';
    }
    if (optionsLoading.value) {
        return 'Загрузка...';
    }
    return buildFilterSelectionLabel({
        selectedIds: selectedSubdivisionIdsNormalized.value,
        options: subdivisionOptions.value,
        fallback: 'Все подразделения',
    });
});

const positionSelectionLabel = computed(() => {
    if (!hasSelectedRestaurants.value) {
        return 'Сначала выберите ресторан';
    }
    if (optionsLoading.value) {
        return 'Загрузка...';
    }
    return buildFilterSelectionLabel({
        selectedIds: selectedPositionIdsNormalized.value,
        options: positionOptions.value,
        fallback: 'Все должности',
    });
});

const restaurantSelectionKey = computed(() => selectedRestaurantIdsNormalized.value.join(','));
const subdivisionSelectionKey = computed(() => selectedSubdivisionIdsNormalized.value.join(','));
const positionSelectionKey = computed(() => selectedPositionIdsNormalized.value.join(','));

const hasAppliedFilters = computed(() => !!appliedFilters.value);
const appliedCostOptions = computed(() => normalizeCostOptions(appliedFilters.value?.costOptions));
const showCostAccrual = computed(
    () => canViewLaborSummaryCost.value && appliedCostOptions.value.includeAccrualCost,
);
const showCostDeduction = computed(
    () => canViewLaborSummaryCost.value && appliedCostOptions.value.includeDeductionCost,
);
const showCostTotal = computed(
    () => canViewLaborSummaryCost.value,
);

const filtersSummary = computed(() => {
    const restaurantsSelected = selectedRestaurantIdsNormalized.value.length;
    const restaurantsTotal = restaurantOptions.value.length;

    const subdivisionsSelected = selectedSubdivisionIdsNormalized.value.length;
    const subdivisionsTotal = subdivisionOptions.value.length;

    const positionsSelected = selectedPositionIdsNormalized.value.length;
    const positionsTotal = positionOptions.value.length;
    const costLabel = buildCostFilterLabel({
        includeAccrualCost: includeAccrualCost.value,
        includeDeductionCost: includeDeductionCost.value,
    });
    const adjustmentTypeLabel = buildAdjustmentTypeFilterLabel({
        accrualSelected: selectedAccrualAdjustmentTypeIdsNormalized.value.length,
        accrualTotal: accrualAdjustmentTypeOptions.value.length,
        deductionSelected: selectedDeductionAdjustmentTypeIdsNormalized.value.length,
        deductionTotal: deductionAdjustmentTypeOptions.value.length,
    });
    const revenueLabel = buildRevenueFilterLabel({
        revenueExcludeDeleted: revenueExcludeDeleted.value,
        revenueRealMoneyOnly: revenueRealMoneyOnly.value,
        revenueAmountMode: revenueAmountMode.value,
    });

    const countLabel = (selected, total) => {
        if (!total) {
            return '0';
        }
        if (selected === total) {
            return `все (${total})`;
        }
        return `${selected} из ${total}`;
    };

    let periodLabel = 'период не задан';
    if (dateFrom.value && dateTo.value) {
        periodLabel = dateFrom.value === dateTo.value ? dateFrom.value : `${dateFrom.value} — ${dateTo.value}`;
    } else if (dateFrom.value) {
        periodLabel = `с ${dateFrom.value}`;
    } else if (dateTo.value) {
        periodLabel = `по ${dateTo.value}`;
    }

    const parts = [
        `Рестораны: ${countLabel(restaurantsSelected, restaurantsTotal)}`,
        `Подразделения: ${countLabel(subdivisionsSelected, subdivisionsTotal)}`,
        `Должности: ${countLabel(positionsSelected, positionsTotal)}`,
        periodLabel,
    ];
    if (canViewLaborSummaryCost.value) {
        parts.splice(3, 0, `Затраты: ${costLabel}`);
        parts.splice(4, 0, `Типы: ${adjustmentTypeLabel}`);
    }
    parts.push(`Выручка: ${revenueLabel}`);
    return parts.join(' · ');
});

const laborSettingsSummary = computed(() => {
    const costLabel = buildCostFilterLabel({
        includeAccrualCost: includeAccrualCost.value,
        includeDeductionCost: includeDeductionCost.value,
    });
    const adjustmentTypeLabel = buildAdjustmentTypeFilterLabel({
        accrualSelected: selectedAccrualAdjustmentTypeIdsNormalized.value.length,
        accrualTotal: accrualAdjustmentTypeOptions.value.length,
        deductionSelected: selectedDeductionAdjustmentTypeIdsNormalized.value.length,
        deductionTotal: deductionAdjustmentTypeOptions.value.length,
    });
    const revenueLabel = buildRevenueFilterLabel({
        revenueExcludeDeleted: revenueExcludeDeleted.value,
        revenueRealMoneyOnly: revenueRealMoneyOnly.value,
        revenueAmountMode: revenueAmountMode.value,
    });
    return `затраты: ${costLabel} · типы: ${adjustmentTypeLabel} · выручка: ${revenueLabel}`;
});

function toggleFiltersExpanded() {
    filtersExpanded.value = !filtersExpanded.value;
    if (!filtersExpanded.value) {
        closeAllDropdowns();
    }
}

function setFilterRef(key, element) {
    filterRefs[key] = element;
}

function closeAllDropdowns(exceptKey = '') {
    Object.keys(dropdownState).forEach((key) => {
        if (key === exceptKey) {
            return;
        }
        dropdownState[key] = false;
    });
    if (exceptKey !== 'subdivisions') {
        subdivisionSearch.value = '';
    }
    if (exceptKey !== 'positions') {
        positionSearch.value = '';
    }
}

function toggleFilterDropdown(key) {
    const nextState = !dropdownState[key];
    closeAllDropdowns(nextState ? key : '');
    dropdownState[key] = nextState;
}

function buildFilterSelectionLabel({ selectedIds, options, fallback }) {
    if (!Array.isArray(options) || !options.length) {
        return fallback;
    }
    if (!Array.isArray(selectedIds) || !selectedIds.length || selectedIds.length === options.length) {
        return `${fallback} (${options.length})`;
    }
    if (selectedIds.length === 1) {
        const selected = options.find((option) => Number(option.value) === Number(selectedIds[0]));
        return selected?.label || fallback;
    }
    return `Выбрано: ${selectedIds.length}`;
}

function normalizeCostOptions(value) {
    return {
        includeBaseCost: true,
        includeAccrualCost: value?.includeAccrualCost !== false,
        includeDeductionCost: value?.includeDeductionCost !== false,
    };
}

function normalizeRevenueOptions(value) {
    const mode = String(value?.revenueAmountMode || '').trim().toLowerCase();
    const allowedModes = new Set(['sum_without_discount', 'sum_with_discount', 'discount_only']);
    return {
        revenueExcludeDeleted: value?.revenueExcludeDeleted !== false,
        revenueRealMoneyOnly: value?.revenueRealMoneyOnly !== false,
        revenueAmountMode: allowedModes.has(mode) ? mode : 'sum_without_discount',
    };
}

function buildCostFilterLabel({
    includeAccrualCost,
    includeDeductionCost,
}) {
    const labels = ['база'];
    if (includeAccrualCost) {
        labels.push('начисления');
    }
    if (includeDeductionCost) {
        labels.push('удержания');
    }
    return labels.join(', ');
}

function buildAdjustmentTypeFilterLabel({
    accrualSelected,
    accrualTotal,
    deductionSelected,
    deductionTotal,
}) {
    const resolvePart = (selected, total) => {
        if (!total) {
            return 'нет';
        }
        if (selected >= total) {
            return `все (${total})`;
        }
        if (!selected) {
            return `0 из ${total}`;
        }
        return `${selected} из ${total}`;
    };

    return `начисления ${resolvePart(accrualSelected, accrualTotal)}, удержания ${resolvePart(deductionSelected, deductionTotal)}`;
}

function buildRevenueFilterLabel({
    revenueExcludeDeleted,
    revenueRealMoneyOnly,
    revenueAmountMode,
}) {
    const labels = [];
    labels.push(revenueExcludeDeleted ? 'без удаленных' : 'с удаленными');
    labels.push(revenueRealMoneyOnly ? 'реальные деньги' : 'все оплаты');
    if (revenueAmountMode === 'sum_with_discount') {
        labels.push('с учетом скидок');
    } else if (revenueAmountMode === 'discount_only') {
        labels.push('только скидки');
    } else {
        labels.push('без скидок');
    }
    return labels.join(', ');
}

const appliedPeriodLabel = computed(() => {
    const payload = appliedFilters.value;
    if (!payload) {
        return '';
    }
    const from = payload.dateFrom || '';
    const to = payload.dateTo || '';

    if (!from || !to) {
        return 'Период';
    }
    if (from === to) {
        return `Период: ${from}`;
    }
    return `Период: ${from} — ${to}`;
});

function isMoneyMetric(metric) {
    return ['amount', 'accrual_amount', 'deduction_amount', 'total_cost'].includes(String(metric || ''));
}

function metricValueNumber(item, metric) {
    const raw = item?.[metric];
    const value = Number(raw || 0);
    return Number.isFinite(value) ? value : 0;
}

function formatMetricValueWithCurrency(metric, value) {
    if (isMoneyMetric(metric)) {
        return formatAmountWithCurrency(value);
    }
    return formatHours(value);
}

function formatAmountWithCurrency(value) {
    const formatted = formatAmount(value);
    return formatted === '-' ? formatted : `${formatted} ₽`;
}

function chartMetricLabel(metric, { prep = false, lower = false } = {}) {
    const map = {
        hours: { base: 'часы', prep: 'часам' },
        total_cost: { base: 'факт затрат', prep: 'факту затрат' },
    };
    const resolved = map[String(metric || '')] || map.hours;
    const value = prep ? resolved.prep : resolved.base;
    return lower ? value.toLowerCase() : value;
}

const chartMetricOptions = computed(() => {
    const list = [{ value: 'hours', label: 'Часы' }];
    if (showCostTotal.value) {
        list.push({ value: 'total_cost', label: 'Факт затрат' });
    }
    return list;
});

watch(
    () => chartMetricOptions.value.map((item) => item.value).join(','),
    (availableValues) => {
        const values = String(availableValues || '').split(',').filter(Boolean);
        if (values.length && !values.includes(chartMetric.value)) {
            chartMetric.value = 'hours';
        }
    },
);

const laborSummaryRows = computed(() => laborSummary.value?.subdivisions || []);
const laborSummaryTotals = computed(() => laborSummary.value?.totals || null);

watch(
    () => laborSummaryRows.value.map((row) => getSubdivisionKey(row)),
    (keys) => {
        if (summaryHistogramSubdivisionKey.value && !keys.includes(summaryHistogramSubdivisionKey.value)) {
            summaryHistogramSubdivisionKey.value = '';
        }
    },
);

const showRevenueMetrics = computed(
    () => laborSummaryTotals.value?.revenue_amount !== null && laborSummaryTotals.value?.revenue_amount !== undefined,
);
const laborToRevenuePercentValue = computed(() => {
    const revenue = Number(laborSummaryTotals.value?.revenue_amount || 0);
    const totalCost = Number(laborSummaryTotals.value?.total_cost || 0);
    if (!Number.isFinite(revenue) || !Number.isFinite(totalCost) || revenue <= 0) {
        return null;
    }
    return (totalCost / revenue) * 100;
});
const showLaborToRevenueRatio = computed(
    () => showRevenueMetrics.value && showCostTotal.value && laborToRevenuePercentValue.value !== null,
);
const topPositionHighlightLimit = 5;

const summaryHistogramSelectedSubdivision = computed(() => {
    if (!summaryHistogramSubdivisionKey.value) {
        return null;
    }
    return laborSummaryRows.value.find((row) => getSubdivisionKey(row) === summaryHistogramSubdivisionKey.value) || null;
});

const summaryHistogramItems = computed(() => {
    const metric = chartMetric.value;
    const rows = Array.isArray(laborSummaryRows.value) ? laborSummaryRows.value : [];
    const totalCost = Number(laborSummaryTotals.value?.total_cost || 0);

    if (summaryHistogramSelectedSubdivision.value) {
        const subdivision = summaryHistogramSelectedSubdivision.value;
        const subdivisionCost = Number(subdivision?.total_cost || 0);
        return (Array.isArray(subdivision?.positions) ? subdivision.positions : [])
            .map((position) => {
                const value = metricValueNumber(position, metric);
                if (value <= 0) {
                    return null;
                }
                const positionCost = Number(position?.total_cost || 0);
                return {
                    key: getPositionEntryKey(subdivision, position),
                    sourceKey: getPositionKey(position),
                    label: position?.position_name || 'Без должности',
                    value,
                    metrics: {
                        hours: Number(position?.hours || 0),
                        night_hours: Number(position?.night_hours || 0),
                        amount: Number(position?.amount || 0),
                        accrual_amount: Number(position?.accrual_amount || 0),
                        deduction_amount: Number(position?.deduction_amount || 0),
                        total_cost: positionCost,
                    },
                    sharePercent: totalCost > 0 ? (positionCost / totalCost) * 100 : 0,
                    shareInParentPercent: subdivisionCost > 0 ? (positionCost / subdivisionCost) * 100 : 0,
                    nodeType: 'position',
                };
            })
            .filter(Boolean)
            .sort((a, b) => b.value - a.value);
    }

    return rows
        .map((row) => {
            const value = metricValueNumber(row, metric);
            if (value <= 0) {
                return null;
            }
            const rowCost = Number(row?.total_cost || 0);
            return {
                key: getSubdivisionKey(row),
                sourceKey: getSubdivisionKey(row),
                label: row?.subdivision_name || 'Без подразделения',
                value,
                metrics: {
                    hours: Number(row?.hours || 0),
                    night_hours: Number(row?.night_hours || 0),
                    amount: Number(row?.amount || 0),
                    accrual_amount: Number(row?.accrual_amount || 0),
                    deduction_amount: Number(row?.deduction_amount || 0),
                    total_cost: rowCost,
                },
                sharePercent: totalCost > 0 ? (rowCost / totalCost) * 100 : 0,
                shareInParentPercent: 100,
                nodeType: 'subdivision',
            };
        })
        .filter(Boolean)
        .sort((a, b) => b.value - a.value);
});

const topPositionHighlightKeys = computed(() => {
    const metric = chartMetric.value;
    const rows = Array.isArray(laborSummaryRows.value) ? laborSummaryRows.value : [];
    const all = [];
    rows.forEach((row) => {
        (Array.isArray(row?.positions) ? row.positions : []).forEach((position) => {
            const value = metricValueNumber(position, metric);
            if (value > 0) {
                all.push({
                    key: getPositionEntryKey(row, position),
                    value,
                });
            }
        });
    });
    return new Set(
        all
            .sort((a, b) => b.value - a.value)
            .slice(0, topPositionHighlightLimit)
            .map((item) => item.key),
    );
});

const summaryHistogramSubtitle = computed(() => {
    const metric = chartMetricLabel(chartMetric.value, { prep: true, lower: true });
    if (summaryHistogramSelectedSubdivision.value) {
        const name = summaryHistogramSelectedSubdivision.value?.subdivision_name || 'Без подразделения';
        return `Должности подразделения «${name}» по ${metric}`;
    }
    return `Подразделения по ${metric}. Кликни столбец для детализации должностей.`;
});

const summaryHistogramOption = computed(() => {
    const items = summaryHistogramItems.value;
    if (!items.length) {
        return null;
    }
    const metricName = chartMetricLabel(chartMetric.value, { lower: true });
    const maxValue = Math.max(...items.map((item) => Number(item.value || 0)), 0);
    const isPositionsLevel = !!summaryHistogramSelectedSubdivision.value;

    const seriesData = items.map((item) => {
        const isTop = isPositionsLevel && topPositionHighlightKeys.value.has(item.key);
        return {
            ...item,
            value: Number(item.value || 0),
            itemStyle: {
                color: isTop
                    ? 'rgba(221, 119, 119, 0.58)'
                    : 'rgba(212, 163, 115, 0.72)',
                borderRadius: [6, 6, 6, 6],
            },
        };
    });

    return {
        animationDuration: 220,
        grid: {
            left: 210,
            right: 28,
            top: 12,
            bottom: 16,
            containLabel: false,
        },
        tooltip: {
            trigger: 'item',
            confine: true,
            backgroundColor: 'rgba(17, 19, 24, 0.96)',
            borderColor: 'rgba(212, 163, 115, 0.45)',
            borderWidth: 1,
            textStyle: {
                color: '#f5efe6',
                fontSize: 12,
            },
            formatter: (params) => {
                const node = params?.data || {};
                const metrics = node?.metrics || {};
                const metric = String(chartMetric.value || '');
                const title = escapeHtml(node?.label || '—');
                const typeLabel = node?.nodeType === 'position' ? 'Должность' : 'Подразделение';
                const valueLabel = formatMetricValueWithCurrency(metric, Number(node?.value || 0));
                const lines = [
                    `<div style="font-weight:700;font-size:13px;margin-bottom:6px;">${title}</div>`,
                    `<div style="opacity:.9;margin-bottom:6px;">${typeLabel}</div>`,
                    `<div><span style="opacity:.75;">${escapeHtml(metricName)}:</span> <b>${escapeHtml(valueLabel)}</b></div>`,
                    `<div><span style="opacity:.75;">Ночные:</span> <b>${escapeHtml(formatHours(metrics.night_hours))}</b></div>`,
                ];
                if (metric !== 'hours') {
                    lines.push(`<div><span style="opacity:.75;">Часы:</span> <b>${escapeHtml(formatHours(metrics.hours))}</b></div>`);
                }
                if (showCostAccrual.value) {
                    lines.push(`<div><span style="opacity:.75;">Начисления:</span> <b>${escapeHtml(formatAmountWithCurrency(metrics.accrual_amount))}</b></div>`);
                }
                if (showCostDeduction.value) {
                    lines.push(`<div><span style="opacity:.75;">Удержания:</span> <b>${escapeHtml(formatAmountWithCurrency(metrics.deduction_amount))}</b></div>`);
                }
                if (showCostTotal.value && metric !== 'total_cost') {
                    lines.push(`<div><span style="opacity:.75;">Факт затрат:</span> <b>${escapeHtml(formatAmountWithCurrency(metrics.total_cost))}</b></div>`);
                }
                if (showCostTotal.value) {
                    lines.push(`<div><span style="opacity:.75;">Доля ФОТ (общая):</span> <b>${escapeHtml(formatPercent(node?.sharePercent))}</b></div>`);
                    if (node?.nodeType === 'position') {
                        lines.push(`<div><span style="opacity:.75;">Доля в подразделении:</span> <b>${escapeHtml(formatPercent(node?.shareInParentPercent))}</b></div>`);
                    }
                }
                return lines.join('');
            },
        },
        xAxis: {
            type: 'value',
            max: maxValue > 0 ? maxValue * 1.12 : undefined,
            axisLabel: {
                color: '#b8b3a9',
                formatter: (value) => formatMetricValueWithCurrency(chartMetric.value, value),
            },
            splitLine: {
                lineStyle: {
                    color: 'rgba(255, 255, 255, 0.08)',
                },
            },
        },
        yAxis: {
            type: 'category',
            inverse: true,
            data: items.map((item) => item.label),
            axisTick: { show: false },
            axisLine: { show: false },
            axisLabel: {
                color: '#d7d2c9',
                width: 190,
                overflow: 'truncate',
            },
        },
        series: [
            {
                type: 'bar',
                data: seriesData,
                barMaxWidth: 28,
                label: {
                    show: true,
                    position: 'right',
                    color: '#d8d3c9',
                    formatter: ({ data }) => (
                        showCostTotal.value
                            ? formatPercent(Number(data?.sharePercent || 0))
                            : formatMetricValueWithCurrency(chartMetric.value, Number(data?.value || 0))
                    ),
                },
                emphasis: {
                    itemStyle: {
                        color: 'rgba(212, 163, 115, 0.9)',
                    },
                },
            },
        ],
    };
});

useClickOutside(() =>
    Object.keys(dropdownState).map((key) => ({
        element: filterRefs[key],
        when: () => dropdownState[key],
        onOutside: () => {
            dropdownState[key] = false;
            if (key === 'subdivisions') {
                subdivisionSearch.value = '';
            }
            if (key === 'positions') {
                positionSearch.value = '';
            }
        },
    })),
);

onMounted(async () => {
    if (canViewLaborSummary.value) {
        await loadRestaurants();
        await loadAdjustmentTypes();
        await initializeDefaultReport();
    }
});

onBeforeUnmount(() => {
    if (optionsDebounceTimer.value) {
        clearTimeout(optionsDebounceTimer.value);
        optionsDebounceTimer.value = null;
    }
});

watch(
    () => canViewLaborSummary.value,
    async (allowed) => {
        if (allowed) {
            await loadRestaurants();
            await loadAdjustmentTypes();
            await initializeDefaultReport();
            return;
        }
        optionsRequestId.value += 1;
        summaryRequestId.value += 1;
        optionsLoading.value = false;
        laborSummaryLoading.value = false;
        if (optionsDebounceTimer.value) {
            clearTimeout(optionsDebounceTimer.value);
            optionsDebounceTimer.value = null;
        }
        appliedFilters.value = null;
        isDirty.value = false;
        laborSummary.value = null;
        restaurants.value = [];
        subdivisions.value = [];
        positions.value = [];
        selectedRestaurantIds.value = [];
        selectedSubdivisionIds.value = [];
        selectedPositionIds.value = [];
        selectedAccrualAdjustmentTypeIds.value = [];
        selectedDeductionAdjustmentTypeIds.value = [];
        adjustmentTypes.value = [];
        adjustmentTypesError.value = '';
        adjustmentTypesLoading.value = false;
        includeBaseCost.value = true;
        includeAccrualCost.value = true;
        includeDeductionCost.value = true;
        selectedAccrualAdjustmentTypeIds.value = [];
        selectedDeductionAdjustmentTypeIds.value = [];
        revenueExcludeDeleted.value = true;
        revenueRealMoneyOnly.value = true;
        revenueAmountMode.value = 'sum_without_discount';
        settingsModalOpen.value = false;
        settingsLoading.value = false;
        settingsSaving.value = false;
        settingsError.value = '';
        settingsSnapshot.value = null;
        settingsLoaded.value = false;
        settingsUseAllAccrualTypes.value = true;
        settingsUseAllDeductionTypes.value = true;
        defaultReportInitializing.value = false;
        defaultReportInitialized.value = false;
    },
);

watch(
    () => canViewLaborSummaryCost.value,
    (allowed) => {
        if (allowed && canViewLaborSummary.value) {
            loadAdjustmentTypes();
            loadSettings({ silent: true });
            return;
        }
        adjustmentTypes.value = [];
        adjustmentTypesError.value = '';
        selectedAccrualAdjustmentTypeIds.value = [];
        selectedDeductionAdjustmentTypeIds.value = [];
        settingsModalOpen.value = false;
        settingsError.value = '';
        settingsSnapshot.value = null;
        settingsLoaded.value = false;
        settingsUseAllAccrualTypes.value = true;
        settingsUseAllDeductionTypes.value = true;
    },
);

watch(
    () => restaurantSelectionKey.value,
    () => {
        if (!canViewLaborSummary.value) {
            return;
        }
        markDirty();
        scheduleOptionsReload();
        loadSettings({ silent: true });
    },
);

watch(
    () => subdivisionSelectionKey.value,
    () => {
        markDirty();
    },
);

watch(
    () => positionSelectionKey.value,
    () => {
        markDirty();
    },
);

watch(dateFrom, () => {
    markDirty();
});

watch(dateTo, () => {
    markDirty();
});

async function loadRestaurants() {
    try {
        const data = await fetchRestaurants();
        restaurants.value = Array.isArray(data) ? data : data?.items || [];
    } catch (error) {
        console.error(error);
        restaurants.value = [];
    } finally {
        if (!selectedRestaurantIdsNormalized.value.length) {
            selectedRestaurantIds.value = resolveDefaultRestaurantIds();
        } else {
            const available = new Set(restaurantOptions.value.map((option) => Number(option.value)));
            const filtered = selectedRestaurantIdsNormalized.value.filter((id) => available.has(id));
            selectedRestaurantIds.value = filtered.length ? filtered : resolveDefaultRestaurantIds();
        }
    }
}

async function loadAdjustmentTypes() {
    if (!canViewLaborSummaryCost.value) {
        adjustmentTypes.value = [];
        adjustmentTypesError.value = '';
        adjustmentTypesLoading.value = false;
        selectedAccrualAdjustmentTypeIds.value = [];
        selectedDeductionAdjustmentTypeIds.value = [];
        return;
    }

    adjustmentTypesLoading.value = true;
    adjustmentTypesError.value = '';

    try {
        const data = await fetchPayrollAdjustmentTypes();
        const items = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
        adjustmentTypes.value = items;
        syncAdjustmentTypeSelections({
            forceAllAccrual: !settingsLoaded.value || settingsUseAllAccrualTypes.value,
            forceAllDeduction: !settingsLoaded.value || settingsUseAllDeductionTypes.value,
            keepEmptyAccrual: settingsLoaded.value && !settingsUseAllAccrualTypes.value,
            keepEmptyDeduction: settingsLoaded.value && !settingsUseAllDeductionTypes.value,
        });
    } catch (error) {
        console.error(error);
        adjustmentTypes.value = [];
        selectedAccrualAdjustmentTypeIds.value = [];
        selectedDeductionAdjustmentTypeIds.value = [];
        adjustmentTypesError.value =
            error?.response?.status === 403
                ? 'Нет доступа к справочнику типов корректировок. Используются все доступные типы.'
                : error?.response?.data?.detail || 'Не удалось загрузить типы корректировок.';
    } finally {
        adjustmentTypesLoading.value = false;
    }
}

function getSettingsRestaurantId() {
    return selectedRestaurantIdsNormalized.value[0] || null;
}

function captureSettingsSnapshot() {
    return {
        includeBaseCost: true,
        includeAccrualCost: includeAccrualCost.value,
        includeDeductionCost: includeDeductionCost.value,
        selectedAccrualAdjustmentTypeIds: [...selectedAccrualAdjustmentTypeIdsNormalized.value],
        selectedDeductionAdjustmentTypeIds: [...selectedDeductionAdjustmentTypeIdsNormalized.value],
        settingsUseAllAccrualTypes: settingsUseAllAccrualTypes.value,
        settingsUseAllDeductionTypes: settingsUseAllDeductionTypes.value,
        revenueExcludeDeleted: revenueExcludeDeleted.value,
        revenueRealMoneyOnly: revenueRealMoneyOnly.value,
        revenueAmountMode: revenueAmountMode.value,
    };
}

function applySettingsSnapshot(snapshot) {
    if (!snapshot) {
        return;
    }
    includeBaseCost.value = true;
    includeAccrualCost.value = snapshot.includeAccrualCost !== false;
    includeDeductionCost.value = snapshot.includeDeductionCost !== false;
    selectedAccrualAdjustmentTypeIds.value = normalizeNumbers(snapshot.selectedAccrualAdjustmentTypeIds);
    selectedDeductionAdjustmentTypeIds.value = normalizeNumbers(snapshot.selectedDeductionAdjustmentTypeIds);
    settingsUseAllAccrualTypes.value = snapshot.settingsUseAllAccrualTypes !== false;
    settingsUseAllDeductionTypes.value = snapshot.settingsUseAllDeductionTypes !== false;
    revenueExcludeDeleted.value = snapshot.revenueExcludeDeleted !== false;
    revenueRealMoneyOnly.value = snapshot.revenueRealMoneyOnly !== false;
    revenueAmountMode.value = normalizeRevenueOptions({ revenueAmountMode: snapshot.revenueAmountMode }).revenueAmountMode;
    syncAdjustmentTypeSelections({
        forceAllAccrual: settingsUseAllAccrualTypes.value,
        forceAllDeduction: settingsUseAllDeductionTypes.value,
        keepEmptyAccrual: !settingsUseAllAccrualTypes.value,
        keepEmptyDeduction: !settingsUseAllDeductionTypes.value,
    });
}

function applySettingsPayload(payload) {
    includeBaseCost.value = true;
    includeAccrualCost.value = payload?.include_accrual_cost !== false;
    includeDeductionCost.value = payload?.include_deduction_cost !== false;
    settingsUseAllAccrualTypes.value =
        payload?.accrual_adjustment_type_ids === null || payload?.accrual_adjustment_type_ids === undefined;
    settingsUseAllDeductionTypes.value =
        payload?.deduction_adjustment_type_ids === null || payload?.deduction_adjustment_type_ids === undefined;
    selectedAccrualAdjustmentTypeIds.value = normalizeNumbers(payload?.accrual_adjustment_type_ids);
    selectedDeductionAdjustmentTypeIds.value = normalizeNumbers(payload?.deduction_adjustment_type_ids);
    revenueExcludeDeleted.value = payload?.revenue_exclude_deleted !== false;
    revenueRealMoneyOnly.value = payload?.revenue_real_money_only !== false;
    revenueAmountMode.value = normalizeRevenueOptions({ revenueAmountMode: payload?.revenue_amount_mode }).revenueAmountMode;
    settingsLoaded.value = true;
    syncAdjustmentTypeSelections({
        forceAllAccrual: settingsUseAllAccrualTypes.value,
        forceAllDeduction: settingsUseAllDeductionTypes.value,
        keepEmptyAccrual: !settingsUseAllAccrualTypes.value,
        keepEmptyDeduction: !settingsUseAllDeductionTypes.value,
    });
}

async function loadSettings({ silent = false } = {}) {
    if (!canViewLaborSummaryCost.value || !canViewLaborSummary.value) {
        return;
    }
    const restaurantId = getSettingsRestaurantId();
    if (!restaurantId) {
        settingsLoaded.value = false;
        return;
    }

    if (!silent) {
        settingsLoading.value = true;
    }
    settingsError.value = '';

    try {
        const data = await fetchLaborSummarySettings({ restaurant_id: restaurantId });
        applySettingsPayload(data);
    } catch (error) {
        console.error(error);
        settingsError.value = error?.response?.data?.detail || 'Не удалось загрузить настройки расчета ФОТ.';
    } finally {
        settingsLoading.value = false;
    }
}

async function openSettingsModal() {
    settingsError.value = '';
    if (!settingsLoaded.value && !settingsLoading.value) {
        await loadSettings();
    }
    settingsSnapshot.value = captureSettingsSnapshot();
    settingsModalOpen.value = true;
}

function closeSettingsModal({ restore = true } = {}) {
    if (settingsSaving.value) {
        return;
    }
    if (restore && settingsSnapshot.value) {
        applySettingsSnapshot(settingsSnapshot.value);
    }
    settingsSnapshot.value = null;
    settingsModalOpen.value = false;
    settingsError.value = '';
}

function buildAdjustmentTypeFiltersPayload() {
    const allAccrualTypeIds = accrualAdjustmentTypeOptions.value.map((option) => Number(option.value));
    const allDeductionTypeIds = deductionAdjustmentTypeOptions.value.map((option) => Number(option.value));
    const accrualIds = selectedAccrualAdjustmentTypeIdsNormalized.value;
    const deductionIds = selectedDeductionAdjustmentTypeIdsNormalized.value;

    const accrualTypeIds =
        allAccrualTypeIds.length && accrualIds.length !== allAccrualTypeIds.length
            ? (accrualIds.length ? accrualIds : [0])
            : null;
    const deductionTypeIds =
        allDeductionTypeIds.length && deductionIds.length !== allDeductionTypeIds.length
            ? (deductionIds.length ? deductionIds : [0])
            : null;

    return { accrualTypeIds, deductionTypeIds };
}

function buildSettingsUpdatePayload() {
    const allAccrualTypeIds = accrualAdjustmentTypeOptions.value.map((option) => Number(option.value));
    const allDeductionTypeIds = deductionAdjustmentTypeOptions.value.map((option) => Number(option.value));
    const availableAccrualTypeIds = new Set(allAccrualTypeIds);
    const availableDeductionTypeIds = new Set(allDeductionTypeIds);
    const accrualIds = selectedAccrualAdjustmentTypeIdsNormalized.value.filter((id) =>
        availableAccrualTypeIds.has(id),
    );
    const deductionIds = selectedDeductionAdjustmentTypeIdsNormalized.value.filter((id) =>
        availableDeductionTypeIds.has(id),
    );

    return {
        include_base_cost: true,
        include_accrual_cost: includeAccrualCost.value !== false,
        include_deduction_cost: includeDeductionCost.value !== false,
        accrual_adjustment_type_ids:
            !allAccrualTypeIds.length || accrualIds.length === allAccrualTypeIds.length ? null : [...accrualIds],
        deduction_adjustment_type_ids:
            !allDeductionTypeIds.length || deductionIds.length === allDeductionTypeIds.length
                ? null
                : [...deductionIds],
        revenue_real_money_only: revenueRealMoneyOnly.value !== false,
        revenue_exclude_deleted: revenueExcludeDeleted.value !== false,
        revenue_amount_mode: normalizeRevenueOptions({ revenueAmountMode: revenueAmountMode.value }).revenueAmountMode,
    };
}

function buildCurrentCostOptions() {
    return normalizeCostOptions({
        includeBaseCost: true,
        includeAccrualCost: includeAccrualCost.value,
        includeDeductionCost: includeDeductionCost.value,
    });
}

async function refreshAppliedSummaryWithSettings() {
    if (!appliedFilters.value) {
        return;
    }
    const normalizedRevenueOptions = normalizeRevenueOptions({
        revenueExcludeDeleted: revenueExcludeDeleted.value,
        revenueRealMoneyOnly: revenueRealMoneyOnly.value,
        revenueAmountMode: revenueAmountMode.value,
    });
    const nextAppliedFilters = {
        ...appliedFilters.value,
        adjustmentTypeFilters: buildAdjustmentTypeFiltersPayload(),
        revenueOptions: normalizedRevenueOptions,
        costOptions: buildCurrentCostOptions(),
    };
    appliedFilters.value = nextAppliedFilters;
    await loadLaborSummary(nextAppliedFilters);
}

async function saveSettings() {
    if (!canManageLaborSummarySettings.value) {
        return;
    }
    const restaurantId = getSettingsRestaurantId();
    if (!restaurantId) {
        settingsError.value = 'Сначала выберите хотя бы один ресторан.';
        return;
    }

    settingsSaving.value = true;
    settingsError.value = '';
    let shouldCloseModal = false;
    try {
        const payload = buildSettingsUpdatePayload();
        const data = await updateLaborSummarySettings(payload, { restaurant_id: restaurantId });
        applySettingsPayload(data);
        await refreshAppliedSummaryWithSettings();
        shouldCloseModal = true;
    } catch (error) {
        console.error(error);
        settingsError.value = error?.response?.data?.detail || 'Не удалось сохранить настройки расчета ФОТ.';
    } finally {
        settingsSaving.value = false;
        if (shouldCloseModal) {
            closeSettingsModal({ restore: false });
        }
    }
}

async function loadOptions() {
    if (!canViewLaborSummary.value) {
        optionsRequestId.value += 1;
        optionsLoading.value = false;
        return;
    }
    const ids = selectedRestaurantIdsNormalized.value;
    if (!ids.length) {
        optionsRequestId.value += 1;
        optionsLoading.value = false;
        subdivisions.value = [];
        positions.value = [];
        selectedSubdivisionIds.value = [];
        selectedPositionIds.value = [];
        return;
    }

    const cacheKey = buildLaborSummaryOptionsCacheKey(ids);
    const cached = optionsCache.get(cacheKey);
    if (cached) {
        subdivisions.value = cached.subdivisions;
        positions.value = cached.positions;
        optionsError.value = '';
        syncFilterSelections();
        return;
    }

    const requestId = optionsRequestId.value + 1;
    optionsRequestId.value = requestId;
    optionsLoading.value = true;
    optionsError.value = '';

    try {
        const data = await fetchLaborSummaryOptions({ restaurant_id: ids });
        if (requestId !== optionsRequestId.value) {
            return;
        }

        const nextSubdivisions = Array.isArray(data?.subdivisions) ? data.subdivisions : [];
        const nextPositions = Array.isArray(data?.positions) ? data.positions : [];
        subdivisions.value = nextSubdivisions;
        positions.value = nextPositions;
        optionsCache.set(cacheKey, {
            subdivisions: nextSubdivisions,
            positions: nextPositions,
        });
        trimMapCache(optionsCache, 20);
    } catch (error) {
        if (requestId !== optionsRequestId.value) {
            return;
        }

        console.error(error);
        optionsError.value =
            error?.response?.data?.detail || 'Не удалось загрузить список подразделений и должностей';
        subdivisions.value = [];
        positions.value = [];
    } finally {
        if (requestId === optionsRequestId.value) {
            optionsLoading.value = false;
            syncFilterSelections();
        }
    }
}

async function loadLaborSummary(payload) {
    if (!canViewLaborSummary.value) {
        summaryRequestId.value += 1;
        laborSummaryLoading.value = false;
        return;
    }

    const ids = payload?.restaurantIds || selectedRestaurantIdsNormalized.value;
    if (!ids.length) {
        summaryRequestId.value += 1;
        laborSummaryLoading.value = false;
        laborSummary.value = null;
        return;
    }

    const cacheKey = buildLaborSummaryCacheKey(payload);
    const cached = summaryCache.get(cacheKey);
    if (cached) {
        laborSummaryError.value = '';
        laborSummary.value = cloneForCache(cached);
        return;
    }

    const requestId = summaryRequestId.value + 1;
    summaryRequestId.value = requestId;
    laborSummaryLoading.value = true;
    laborSummaryError.value = '';

    try {
        laborSummary.value = null;

        const results = await Promise.allSettled(
            ids.map((id) =>
                fetchLaborSummary({
                    restaurant_id: id,
                    include_positions: true,
                    fallback_to_company_revenue_if_zero: payload?.fallbackToCompanyRevenueIfZero === true,
                    date_from: payload?.dateFrom || undefined,
                    date_to: payload?.dateTo || undefined,
                    restaurant_subdivision_ids: payload?.restaurantSubdivisionIds || undefined,
                    position_ids: payload?.positionIds || undefined,
                }),
            ),
        );

        if (requestId !== summaryRequestId.value) {
            return;
        }

        const fulfilled = results
            .filter((item) => item.status === 'fulfilled')
            .map((item) => item.value);

        if (!fulfilled.length) {
            const reason = results[0]?.reason;
            throw reason;
        }

        if (results.some((item) => item.status === 'rejected')) {
            laborSummaryError.value = 'Данные ресторана не загрузились.';
        }

        const merged = mergeLaborSummaries(fulfilled, payload?.costOptions);
        laborSummary.value = merged;
        summaryCache.set(cacheKey, cloneForCache(merged));
        trimMapCache(summaryCache, 30);
    } catch (error) {
        if (requestId !== summaryRequestId.value) {
            return;
        }

        console.error(error);
        laborSummaryError.value = error?.response?.data?.detail || 'Не удалось загрузить сводку';
        laborSummary.value = null;
    } finally {
        if (requestId === summaryRequestId.value) {
            laborSummaryLoading.value = false;
        }
    }
}

function resolveDefaultRestaurantIds() {
    const available = restaurantOptions.value
        .map((option) => Number(option.value))
        .filter((value) => Number.isFinite(value));
    if (!available.length) {
        return [];
    }
    if (available.length === 1) {
        return available;
    }
    if (Array.isArray(userStore.restaurantIds) && userStore.restaurantIds.length) {
        return userStore.restaurantIds.filter((id) => available.includes(id));
    }
    return available;
}

function resolveInitialRestaurantIds() {
    const available = restaurantOptions.value
        .map((option) => Number(option.value))
        .filter((value) => Number.isFinite(value));
    if (!available.length) {
        return [];
    }

    const workplaceId = Number(userStore.workplaceRestaurantId);
    if (Number.isFinite(workplaceId) && available.includes(workplaceId)) {
        return [workplaceId];
    }

    return resolveDefaultRestaurantIds();
}

async function initializeDefaultReport() {
    if (!canViewLaborSummary.value || defaultReportInitialized.value || defaultReportInitializing.value) {
        return;
    }
    const initialRestaurantIds = resolveInitialRestaurantIds();
    if (!initialRestaurantIds.length) {
        return;
    }

    defaultReportInitializing.value = true;
    filtersExpanded.value = false;

    try {
        dateFrom.value = getCurrentMonthStartIso();
        dateTo.value = getTodayIso();
        selectedRestaurantIds.value = initialRestaurantIds;
        selectedSubdivisionIds.value = [];
        selectedPositionIds.value = [];

        await loadOptions();
        syncFilterSelections();

        if (canViewLaborSummaryCost.value) {
            await loadSettings({ silent: true });
        }

        await applyFilters();
        defaultReportInitialized.value = true;
    } finally {
        defaultReportInitializing.value = false;
    }
}

function normalizeNumbers(values) {
    const raw = Array.isArray(values) ? values : [];
    return Array.from(
        new Set(raw.map((value) => Number(value)).filter((value) => Number.isFinite(value))),
    ).sort((a, b) => a - b);
}

function getSubdivisionKey(row) {
    return `${row?.subdivision_id ?? 'none'}:${row?.subdivision_name ?? ''}`;
}

function getPositionKey(position) {
    if (position?.position_id !== null && position?.position_id !== undefined) {
        return `id:${position.position_id}`;
    }
    return `name:${position?.position_name || ''}`;
}

function getPositionEntryKey(row, position) {
    return `${getSubdivisionKey(row)}::${getPositionKey(position)}`;
}

function handleSummaryHistogramClick(params) {
    if (summaryHistogramSelectedSubdivision.value) {
        return;
    }
    const sourceKey = String(params?.data?.sourceKey || '');
    if (!sourceKey) {
        return;
    }
    const row = laborSummaryRows.value.find((item) => getSubdivisionKey(item) === sourceKey);
    if (!row || !Array.isArray(row?.positions) || !row.positions.length) {
        return;
    }
    summaryHistogramSubdivisionKey.value = sourceKey;
}

function resetSummaryHistogramDrilldown() {
    summaryHistogramSubdivisionKey.value = '';
}

function isRestaurantSelected(value) {
    const id = Number(value);
    return selectedRestaurantIdsNormalized.value.includes(id);
}

function toggleRestaurantSelection(value, checked) {
    const id = Number(value);
    if (!Number.isFinite(id)) {
        return;
    }
    if (checked) {
        selectedRestaurantIds.value = Array.from(new Set([...selectedRestaurantIdsNormalized.value, id]));
    } else {
        selectedRestaurantIds.value = selectedRestaurantIdsNormalized.value.filter((item) => item !== id);
    }
}

function toggleAllRestaurants(checked) {
    if (checked) {
        selectedRestaurantIds.value = restaurantOptions.value.map((option) => Number(option.value));
    } else {
        selectedRestaurantIds.value = [];
    }
}

function isSubdivisionSelected(value) {
    const id = Number(value);
    return selectedSubdivisionIdsNormalized.value.includes(id);
}

function toggleSubdivisionSelection(value, checked) {
    const id = Number(value);
    if (!Number.isFinite(id)) {
        return;
    }
    if (checked) {
        selectedSubdivisionIds.value = Array.from(new Set([...selectedSubdivisionIdsNormalized.value, id]));
    } else {
        selectedSubdivisionIds.value = selectedSubdivisionIdsNormalized.value.filter((item) => item !== id);
    }
}

function toggleAllSubdivisions(checked) {
    if (checked) {
        selectedSubdivisionIds.value = subdivisionOptions.value.map((option) => Number(option.value));
    } else {
        selectedSubdivisionIds.value = [];
    }
}

function isPositionSelected(value) {
    const id = Number(value);
    return selectedPositionIdsNormalized.value.includes(id);
}

function togglePositionSelection(value, checked) {
    const id = Number(value);
    if (!Number.isFinite(id)) {
        return;
    }
    if (checked) {
        selectedPositionIds.value = Array.from(new Set([...selectedPositionIdsNormalized.value, id]));
    } else {
        selectedPositionIds.value = selectedPositionIdsNormalized.value.filter((item) => item !== id);
    }
}

function toggleAllPositions(checked) {
    if (checked) {
        selectedPositionIds.value = positionOptions.value.map((option) => Number(option.value));
    } else {
        selectedPositionIds.value = [];
    }
}

function toggleAllAccrualTypes(checked) {
    if (checked) {
        selectedAccrualAdjustmentTypeIds.value = accrualAdjustmentTypeOptions.value.map((option) => Number(option.value));
    } else {
        selectedAccrualAdjustmentTypeIds.value = [];
    }
}

function toggleAllDeductionTypes(checked) {
    if (checked) {
        selectedDeductionAdjustmentTypeIds.value = deductionAdjustmentTypeOptions.value.map((option) => Number(option.value));
    } else {
        selectedDeductionAdjustmentTypeIds.value = [];
    }
}

function syncAdjustmentTypeSelections({
    forceAll = false,
    keepEmpty = false,
    forceAllAccrual,
    forceAllDeduction,
    keepEmptyAccrual,
    keepEmptyDeduction,
} = {}) {
    const availableAccrualIds = new Set(accrualAdjustmentTypeOptions.value.map((option) => Number(option.value)));
    const availableDeductionIds = new Set(deductionAdjustmentTypeOptions.value.map((option) => Number(option.value)));

    const nextAccrual = selectedAccrualAdjustmentTypeIdsNormalized.value.filter((id) => availableAccrualIds.has(id));
    const nextDeduction = selectedDeductionAdjustmentTypeIdsNormalized.value.filter((id) =>
        availableDeductionIds.has(id),
    );

    const shouldForceAllAccrual = forceAllAccrual ?? forceAll;
    const shouldForceAllDeduction = forceAllDeduction ?? forceAll;
    const shouldKeepEmptyAccrual = keepEmptyAccrual ?? keepEmpty;
    const shouldKeepEmptyDeduction = keepEmptyDeduction ?? keepEmpty;

    selectedAccrualAdjustmentTypeIds.value =
        shouldForceAllAccrual || (!nextAccrual.length && !shouldKeepEmptyAccrual)
            ? Array.from(availableAccrualIds.values())
            : nextAccrual;
    selectedDeductionAdjustmentTypeIds.value =
        shouldForceAllDeduction || (!nextDeduction.length && !shouldKeepEmptyDeduction)
            ? Array.from(availableDeductionIds.values())
            : nextDeduction;
}

function syncFilterSelections() {
    const availableSubdivisions = new Set(subdivisionOptions.value.map((option) => Number(option.value)));
    const availablePositions = new Set(positionOptions.value.map((option) => Number(option.value)));

    const filteredSubdivisions = selectedSubdivisionIdsNormalized.value.filter((id) => availableSubdivisions.has(id));
    selectedSubdivisionIds.value = filteredSubdivisions.length
        ? filteredSubdivisions
        : Array.from(availableSubdivisions.values());

    const filteredPositions = selectedPositionIdsNormalized.value.filter((id) => availablePositions.has(id));
    selectedPositionIds.value = filteredPositions.length
        ? filteredPositions
        : Array.from(availablePositions.values());
}

async function applyFilters() {
    filtersError.value = '';

    if (!hasSelectedRestaurants.value) {
        filtersError.value = 'Выберите хотя бы один ресторан.';
        return;
    }

    if (!dateFrom.value || !dateTo.value) {
        filtersError.value = 'Укажите диапазон дат.';
        return;
    }

    if (dateFrom.value > dateTo.value) {
        filtersError.value = 'Дата «с» не может быть позже даты «по».';
        return;
    }

    if (subdivisionOptions.value.length && !selectedSubdivisionIdsNormalized.value.length) {
        filtersError.value = 'Выберите подразделения.';
        return;
    }

    if (positionOptions.value.length && !selectedPositionIdsNormalized.value.length) {
        filtersError.value = 'Выберите должности.';
        return;
    }

    const allSubdivisionIds = subdivisionOptions.value.map((option) => Number(option.value));
    const allPositionIds = positionOptions.value.map((option) => Number(option.value));

    const restaurantSubdivisionIds =
        allSubdivisionIds.length && selectedSubdivisionIdsNormalized.value.length !== allSubdivisionIds.length
            ? selectedSubdivisionIdsNormalized.value
            : null;

    const positionIds =
        allPositionIds.length && selectedPositionIdsNormalized.value.length !== allPositionIds.length
            ? selectedPositionIdsNormalized.value
            : null;
    const adjustmentTypeFilters = buildAdjustmentTypeFiltersPayload();
    const normalizedRevenueOptions = normalizeRevenueOptions({
        revenueExcludeDeleted: revenueExcludeDeleted.value,
        revenueRealMoneyOnly: revenueRealMoneyOnly.value,
        revenueAmountMode: revenueAmountMode.value,
    });

    appliedFilters.value = {
        restaurantIds: selectedRestaurantIdsNormalized.value,
        fallbackToCompanyRevenueIfZero: selectedRestaurantIdsNormalized.value.length === 1,
        dateFrom: dateFrom.value,
        dateTo: dateTo.value,
        restaurantSubdivisionIds,
        positionIds,
        adjustmentTypeFilters,
        revenueOptions: normalizedRevenueOptions,
        costOptions: buildCurrentCostOptions(),
    };

    summaryHistogramSubdivisionKey.value = '';
    isDirty.value = false;
    filtersExpanded.value = false;
    closeAllDropdowns();

    await loadLaborSummary(appliedFilters.value);
}

function resetFilters() {
    filtersError.value = '';
    optionsError.value = '';
    laborSummaryError.value = '';
    closeAllDropdowns();

    laborSummary.value = null;
    appliedFilters.value = null;
    isDirty.value = false;
    summaryHistogramSubdivisionKey.value = '';

    chartMetric.value = 'hours';
    dateFrom.value = getCurrentMonthStartIso();
    dateTo.value = getTodayIso();

    selectedRestaurantIds.value = resolveDefaultRestaurantIds();
}

function markDirty() {
    if (appliedFilters.value) {
        isDirty.value = true;
    }
}

function scheduleOptionsReload() {
    if (optionsDebounceTimer.value) {
        clearTimeout(optionsDebounceTimer.value);
    }
    optionsDebounceTimer.value = setTimeout(() => {
        optionsDebounceTimer.value = null;
        loadOptions();
    }, 180);
}

function buildLaborSummaryOptionsCacheKey(restaurantIds) {
    return normalizeNumbers(restaurantIds).join(',');
}

function buildLaborSummaryCacheKey(payload) {
    const costOptions = normalizeCostOptions(payload?.costOptions);
    const revenueOptions = normalizeRevenueOptions(payload?.revenueOptions);
    const adjustmentTypeFilters = payload?.adjustmentTypeFilters || {};
    return JSON.stringify({
        restaurantIds: normalizeNumbers(payload?.restaurantIds),
        fallbackToCompanyRevenueIfZero: payload?.fallbackToCompanyRevenueIfZero === true,
        dateFrom: payload?.dateFrom || null,
        dateTo: payload?.dateTo || null,
        restaurantSubdivisionIds: normalizeNumbers(payload?.restaurantSubdivisionIds),
        positionIds: normalizeNumbers(payload?.positionIds),
        accrualAdjustmentTypeIds: normalizeNumbers(adjustmentTypeFilters?.accrualTypeIds),
        deductionAdjustmentTypeIds: normalizeNumbers(adjustmentTypeFilters?.deductionTypeIds),
        showCost: canViewLaborSummaryCost.value,
        includeBaseCost: costOptions.includeBaseCost,
        includeAccrualCost: costOptions.includeAccrualCost,
        includeDeductionCost: costOptions.includeDeductionCost,
        revenueExcludeDeleted: revenueOptions.revenueExcludeDeleted,
        revenueRealMoneyOnly: revenueOptions.revenueRealMoneyOnly,
        revenueAmountMode: revenueOptions.revenueAmountMode,
    });
}

function trimMapCache(cacheMap, maxSize) {
    if (cacheMap.size <= maxSize) {
        return;
    }
    while (cacheMap.size > maxSize) {
        const firstKey = cacheMap.keys().next().value;
        cacheMap.delete(firstKey);
    }
}

function cloneForCache(value) {
    if (value === null || value === undefined) {
        return value;
    }
    if (typeof structuredClone === 'function') {
        try {
            return structuredClone(value);
        } catch {
            // fallback below
        }
    }
    return JSON.parse(JSON.stringify(value));
}

function getTodayIso() {
    return new Date().toISOString().slice(0, 10);
}

function getCurrentMonthStartIso() {
    const now = new Date();
    const first = new Date(now.getFullYear(), now.getMonth(), 1);
    return first.toISOString().slice(0, 10);
}

function mergeLaborSummaries(items, costOptionsInput) {
    const showCost = canViewLaborSummaryCost.value;
    const costOptions = normalizeCostOptions(costOptionsInput);
    const useBaseCost = showCost;
    const useAccrualCost = showCost && costOptions.includeAccrualCost;
    const useDeductionCost = showCost && costOptions.includeDeductionCost;
    const subdivisionMap = new Map();
    let totalHours = 0;
    let totalNightHours = 0;
    let totalAmount = 0;
    let totalAccrualAmount = 0;
    let totalDeductionAmount = 0;
    let totalCostAmount = 0;
    let totalRevenueAmount = 0;
    let hasRevenueAmount = false;

    const toNumber = (value) => {
        const parsed = Number(value || 0);
        return Number.isFinite(parsed) ? parsed : 0;
    };

    const pickCostParts = ({ amount, accrualAmount, deductionAmount }) => {
        const amountValue = useBaseCost ? toNumber(amount) : 0;
        const accrualValue = useAccrualCost ? toNumber(accrualAmount) : 0;
        const deductionValue = useDeductionCost ? toNumber(deductionAmount) : 0;
        return {
            amount: amountValue,
            accrualAmount: accrualValue,
            deductionAmount: deductionValue,
            totalCost: amountValue + accrualValue - deductionValue,
        };
    };

    items.forEach((item) => {
        if (!item) {
            return;
        }
        totalHours += toNumber(item?.totals?.hours);
        totalNightHours += toNumber(item?.totals?.night_hours);
        const revenueAmount = item?.totals?.revenue_amount;
        if (revenueAmount !== null && revenueAmount !== undefined) {
            hasRevenueAmount = true;
            totalRevenueAmount += toNumber(revenueAmount);
        }
        if (showCost) {
            const totalsCost = pickCostParts({
                amount: item?.totals?.amount,
                accrualAmount: item?.totals?.accrual_amount,
                deductionAmount: item?.totals?.deduction_amount,
            });
            totalAmount += totalsCost.amount;
            totalAccrualAmount += totalsCost.accrualAmount;
            totalDeductionAmount += totalsCost.deductionAmount;
            totalCostAmount += totalsCost.totalCost;
        }
        (item?.subdivisions || []).forEach((subdivision) => {
            const key =
                subdivision?.subdivision_id !== null && subdivision?.subdivision_id !== undefined
                    ? `id:${subdivision.subdivision_id}`
                    : `name:${subdivision?.subdivision_name || ''}`;
            if (!subdivisionMap.has(key)) {
                subdivisionMap.set(key, {
                    subdivision_id: subdivision?.subdivision_id ?? null,
                    subdivision_name: subdivision?.subdivision_name ?? null,
                    hours: 0,
                    night_hours: 0,
                    amount: 0,
                    accrual_amount: 0,
                    deduction_amount: 0,
                    total_cost: 0,
                    positions: new Map(),
                });
            }
            const target = subdivisionMap.get(key);
            target.hours += toNumber(subdivision?.hours);
            target.night_hours += toNumber(subdivision?.night_hours);
            if (showCost) {
                const subdivisionCost = pickCostParts({
                    amount: subdivision?.amount,
                    accrualAmount: subdivision?.accrual_amount,
                    deductionAmount: subdivision?.deduction_amount,
                });
                target.amount += subdivisionCost.amount;
                target.accrual_amount += subdivisionCost.accrualAmount;
                target.deduction_amount += subdivisionCost.deductionAmount;
                target.total_cost += subdivisionCost.totalCost;
            }
            (subdivision?.positions || []).forEach((position) => {
                const posKey =
                    position?.position_id !== null && position?.position_id !== undefined
                        ? `id:${position.position_id}`
                        : `name:${position?.position_name || ''}`;
                if (!target.positions.has(posKey)) {
                    target.positions.set(posKey, {
                        position_id: position?.position_id ?? null,
                        position_name: position?.position_name ?? null,
                        hours: 0,
                        night_hours: 0,
                        amount: 0,
                        accrual_amount: 0,
                        deduction_amount: 0,
                        total_cost: 0,
                    });
                }
                const posTarget = target.positions.get(posKey);
                posTarget.hours += toNumber(position?.hours);
                posTarget.night_hours += toNumber(position?.night_hours);
                if (showCost) {
                    const positionCost = pickCostParts({
                        amount: position?.amount,
                        accrualAmount: position?.accrual_amount,
                        deductionAmount: position?.deduction_amount,
                    });
                    posTarget.amount += positionCost.amount;
                    posTarget.accrual_amount += positionCost.accrualAmount;
                    posTarget.deduction_amount += positionCost.deductionAmount;
                    posTarget.total_cost += positionCost.totalCost;
                }
            });
        });
    });

    const subdivisions = Array.from(subdivisionMap.values()).map((item) => ({
        subdivision_id: item.subdivision_id,
        subdivision_name: item.subdivision_name,
        hours: item.hours,
        night_hours: item.night_hours,
        amount: showCost ? item.amount : null,
        accrual_amount: showCost ? item.accrual_amount : null,
        deduction_amount: showCost ? item.deduction_amount : null,
        total_cost: showCost ? item.total_cost : null,
        positions: Array.from(item.positions.values()).map((pos) => ({
            position_id: pos.position_id,
            position_name: pos.position_name,
            hours: pos.hours,
            night_hours: pos.night_hours,
            amount: showCost ? pos.amount : null,
            accrual_amount: showCost ? pos.accrual_amount : null,
            deduction_amount: showCost ? pos.deduction_amount : null,
            total_cost: showCost ? pos.total_cost : null,
        })),
    }));

    subdivisions.sort((a, b) => Number(b.hours || 0) - Number(a.hours || 0));
    subdivisions.forEach((row) => {
        if (Array.isArray(row.positions)) {
            row.positions.sort((a, b) => Number(b.hours || 0) - Number(a.hours || 0));
        }
    });

    return {
        subdivisions,
        totals: {
            hours: totalHours,
            night_hours: totalNightHours,
            amount: showCost ? totalAmount : null,
            accrual_amount: showCost ? totalAccrualAmount : null,
            deduction_amount: showCost ? totalDeductionAmount : null,
            total_cost: showCost ? totalCostAmount : null,
            revenue_amount: hasRevenueAmount ? totalRevenueAmount : null,
        },
    };
}

function formatHours(value) {
    if (value === null || value === undefined || value === '') {
        return '-';
    }
    const numberValue = Number(value);
    if (!Number.isFinite(numberValue)) {
        return '-';
    }
    return numberValue.toFixed(2);
}

function formatAmount(value) {
    if (value === null || value === undefined || value === '') {
        return '-';
    }
    const numberValue = Number(value);
    if (!Number.isFinite(numberValue)) {
        return '-';
    }
    return numberValue.toLocaleString('ru-RU', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function formatPercent(value) {
    if (value === null || value === undefined || value === '') {
        return '-';
    }
    const numberValue = Number(value);
    if (!Number.isFinite(numberValue)) {
        return '-';
    }
    return `${numberValue.toFixed(2)}%`;
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/labor-fund' as *;
</style>
