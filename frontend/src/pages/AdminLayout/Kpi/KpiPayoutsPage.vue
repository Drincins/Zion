<template>
    <div class="kpi-page">
        <section class="kpi-panel kpi-panel--hero">
            <div class="kpi-panel__header">
                <div>
                    <p class="kpi-panel__eyebrow">KPI</p>
                    <h2 class="kpi-panel__title">Выплаты KPI</h2>
                    <p class="kpi-panel__subtitle">Формирование и история начислений.</p>
                </div>
            </div>
        </section>

        <FiltersPanel v-model="isHistoryFiltersOpen" title="Фильтры">
            <div
                class="filters-panel__controls filters-panel__controls--end kpi-history-filters__controls"
            >
                <Select
                    v-model="filters.status"
                    label="Статус"
                    :options="statusOptions"
                    placeholder="Все статусы"
                />
                <DateInput v-model="filters.periodFrom" label="Период от" />
                <DateInput v-model="filters.periodTo" label="Период до" />
                <Button color="ghost" size="sm" :loading="loadingBatches" @click="loadBatches">
                    Применить
                </Button>
            </div>
        </FiltersPanel>

        <section class="kpi-panel">
            <div class="kpi-panel__header">
                <div>
                    <h2 class="kpi-panel__title">История выплат</h2>
                    <p class="kpi-panel__subtitle">Найдено: {{ historyCards.length }}</p>
                </div>
                <div class="kpi-panel__header-actions">
                    <button
                        type="button"
                        class="kpi-panel__icon-button kpi-panel__icon-button--primary"
                        :disabled="!canManage || previewLoading"
                        title="Сформировать выплату"
                        aria-label="Сформировать выплату"
                        @click="openPreviewModal"
                    >
                        <BaseIcon name="Plus" />
                    </button>
                    <button
                        type="button"
                        class="kpi-panel__icon-button"
                        :disabled="loadingBatches"
                        title="Обновить историю"
                        aria-label="Обновить историю"
                        @click="loadBatches"
                    >
                        <BaseIcon name="Refresh" />
                    </button>
                </div>
            </div>
            <div v-if="historyCards.length" class="kpi-history-table-wrapper">
                <table class="kpi-history-table">
                    <colgroup>
                        <col class="kpi-history-table__col kpi-history-table__col--restaurant" />
                        <col class="kpi-history-table__col kpi-history-table__col--metric" />
                        <col class="kpi-history-table__col kpi-history-table__col--created" />
                        <col class="kpi-history-table__col kpi-history-table__col--posted" />
                        <col class="kpi-history-table__col kpi-history-table__col--status" />
                    </colgroup>
                    <thead>
                        <tr>
                            <th>Ресторан</th>
                            <th>KPI</th>
                            <th>Создано</th>
                            <th>Записано</th>
                            <th>Статус</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="card in historyCards"
                            :key="card.key"
                            class="kpi-history-table__row"
                            tabindex="0"
                            role="button"
                            @click="openBatchGroup(card.batch_ids)"
                            @keydown.enter.prevent="openBatchGroup(card.batch_ids)"
                            @keydown.space.prevent="openBatchGroup(card.batch_ids)"
                        >
                            <td>{{ restaurantLabel(card.restaurant_id) }}</td>
                            <td>{{ metricLabel(card.metric_id) }}</td>
                            <td>{{ card.created_at ? formatDate(card.created_at) : '—' }}</td>
                            <td>{{ card.posted_at ? formatDate(card.posted_at) : '—' }}</td>
                            <td>
                                <span class="kpi-card__status" :class="`is-${card.status}`">
                                    {{ statusLabels[card.status] || card.status }}
                                </span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p v-else class="kpi-list__empty">Нет выплат по выбранным фильтрам.</p>
        </section>

        <Modal
            v-if="showPreviewModal"
            class="kpi-modal-window kpi-modal-window--preview"
            @close="closePreviewModal"
        >
            <template #header>
                <div class="kpi-modal__header">
                    <div>
                        <p class="kpi-panel__eyebrow">Выплаты KPI</p>
                        <h3 class="kpi-modal__title">Сформировать выплаты</h3>
                        <p class="kpi-modal__subtitle">
                            Можно выбрать сразу несколько KPI и ресторанов для одного периода.
                        </p>
                    </div>
                    <div class="kpi-modal__header-actions">
                        <button
                            type="button"
                            class="kpi-modal__icon-button"
                            :disabled="previewLoading"
                            title="Закрыть"
                            aria-label="Закрыть"
                            @click="closePreviewModal"
                        >
                            <BaseIcon name="Close" />
                        </button>
                    </div>
                </div>
            </template>

            <div class="kpi-posting">
                <Select
                    v-model="previewForm.month"
                    label="Месяц"
                    :options="monthOptions"
                    placeholder="Выберите месяц"
                    :disabled="previewLoading"
                />
                <Input
                    v-model="previewForm.year"
                    label="Год"
                    type="number"
                    min="2000"
                    max="2100"
                    :disabled="previewLoading"
                />
                <Input
                    v-model="previewForm.comment"
                    label="Комментарий"
                    placeholder="Например: Расчет за период"
                    :disabled="previewLoading"
                />
            </div>

            <section class="kpi-preview-metrics">
                <div class="kpi-preview-metrics__header">
                    <div>
                        <h4 class="kpi-preview-metrics__title">Показатели KPI</h4>
                        <p class="kpi-preview-metrics__subtitle">
                            Выбрано: {{ selectedPreviewMetricIds.length }}
                        </p>
                    </div>
                    <div class="kpi-preview-metrics__actions">
                        <Button
                            color="ghost"
                            size="sm"
                            :disabled="previewLoading"
                            @click="selectAllPreviewMetrics"
                        >
                            Выбрать все
                        </Button>
                        <Button
                            color="ghost"
                            size="sm"
                            :disabled="previewLoading"
                            @click="clearPreviewMetrics"
                        >
                            Очистить
                        </Button>
                    </div>
                </div>
                <div class="kpi-preview-metrics__list">
                    <label
                        v-for="option in metricOptions"
                        :key="`preview-metric-${option.value}`"
                        class="kpi-preview-metrics__item"
                    >
                        <input
                            type="checkbox"
                            :checked="isPreviewMetricSelected(option.value)"
                            :disabled="previewLoading"
                            @change="togglePreviewMetric(option.value)"
                        />
                        <span>{{ option.label }}</span>
                    </label>
                </div>
            </section>

            <section class="kpi-preview-metrics">
                <div class="kpi-preview-metrics__header">
                    <div>
                        <h4 class="kpi-preview-metrics__title">Рестораны</h4>
                        <p class="kpi-preview-metrics__subtitle">
                            Выбрано: {{ selectedPreviewRestaurantIds.length }}
                        </p>
                    </div>
                    <div class="kpi-preview-metrics__actions">
                        <Button
                            color="ghost"
                            size="sm"
                            :disabled="previewLoading"
                            @click="selectAllPreviewRestaurants"
                        >
                            Выбрать все
                        </Button>
                        <Button
                            color="ghost"
                            size="sm"
                            :disabled="previewLoading"
                            @click="clearPreviewRestaurants"
                        >
                            Очистить
                        </Button>
                    </div>
                </div>
                <div class="kpi-preview-metrics__list">
                    <label
                        v-for="option in restaurantOptions"
                        :key="`preview-restaurant-${option.value}`"
                        class="kpi-preview-metrics__item"
                    >
                        <input
                            type="checkbox"
                            :checked="isPreviewRestaurantSelected(option.value)"
                            :disabled="previewLoading"
                            @change="togglePreviewRestaurant(option.value)"
                        />
                        <span>{{ option.label }}</span>
                    </label>
                </div>
            </section>

            <div class="kpi-panel__actions">
                <Button
                    color="primary"
                    :disabled="
                        !canManage ||
                        !selectedPreviewMetricIds.length ||
                        !selectedPreviewRestaurantIds.length ||
                        !previewForm.month
                    "
                    :loading="previewLoading"
                    @click="handlePreview"
                >
                    Сформировать выплаты
                </Button>
            </div>
        </Modal>

        <Modal
            v-if="showPayoutModal"
            class="kpi-modal-window kpi-modal-window--wide"
            @close="closePayoutModal"
        >
            <template #header>
                <div class="kpi-modal__header">
                    <div>
                        <p class="kpi-panel__eyebrow">
                            Выплаты KPI · {{ payoutModalBatches.length }}
                        </p>
                        <h3 class="kpi-modal__title">
                            {{ restaurantLabel(payoutModalRestaurantId) }}
                        </h3>
                        <p class="kpi-modal__subtitle">
                            Показатель: <strong>{{ metricLabel(payoutModalMetricId) }}</strong> ·
                            Период:
                            {{ formatDateRange(payoutModalPeriodStart, payoutModalPeriodEnd) }} ·
                            Статус: <strong>{{ payoutModalStatusLabel }}</strong>
                        </p>
                        <div v-if="payoutModalRows.length" class="kpi-summary">
                            <p class="kpi-summary__title">{{ payoutSummaryScopeLabel }}</p>
                            <div class="kpi-summary__grid">
                                <div class="kpi-summary__card">
                                    <p class="kpi-summary__label">Итого сумма</p>
                                    <p
                                        class="kpi-summary__value"
                                        :class="{
                                            'is-negative': payoutSummary.amount_total < 0,
                                            'is-positive': payoutSummary.amount_total > 0,
                                        }"
                                    >
                                        {{ formatMoney(payoutSummary.amount_total) }}
                                    </p>
                                    <p class="kpi-summary__meta">
                                        Сотрудников: {{ payoutSummary.row_count }}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="kpi-modal__header-actions">
                        <button
                            type="button"
                            class="kpi-modal__icon-button"
                            :disabled="postingBatch || deletingDrafts"
                            title="Закрыть"
                            aria-label="Закрыть"
                            @click="closePayoutModal"
                        >
                            <BaseIcon name="Close" />
                        </button>
                    </div>
                </div>
            </template>

            <div class="kpi-modal__toolbar">
                <div class="kpi-modal__toolbar-left">
                    <Button
                        color="outline"
                        size="sm"
                        :disabled="postingBatch || deletingDrafts"
                        @click="refreshPayoutModal"
                    >
                        Обновить
                    </Button>
                </div>
                <div class="kpi-modal__toolbar-right">
                    <Button
                        color="danger"
                        size="sm"
                        :disabled="
                            !canManage || !payoutModalHasDrafts || postingBatch || deletingDrafts
                        "
                        :loading="deletingDrafts"
                        @click="handleDeleteDraftBatches"
                    >
                        {{ draftBatchCount > 1 ? 'Удалить черновики' : 'Удалить черновик' }}
                    </Button>
                    <Button
                        color="primary"
                        size="sm"
                        :disabled="
                            !canManage || !payoutModalHasDrafts || postingBatch || deletingDrafts
                        "
                        :loading="postingBatch || deletingDrafts"
                        @click="handlePostBatches"
                    >
                        Записать начисления
                    </Button>
                </div>
            </div>

            <div class="kpi-modal__body">
                <div class="kpi-posting">
                    <Select
                        v-model="postForm.adjustmentTypeId"
                        label="Тип операции"
                        :options="adjustmentTypeOptions"
                        placeholder="Выберите тип"
                        :disabled="!payoutModalHasDrafts || postingBatch || deletingDrafts"
                    />
                    <div class="kpi-modal__field">
                        <label class="kpi-panel__label">Дата операции</label>
                        <DateInput
                            v-model="postForm.date"
                            :disabled="!payoutModalHasDrafts || postingBatch || deletingDrafts"
                        />
                    </div>
                    <Input
                        v-model="postForm.comment"
                        label="Комментарий"
                        placeholder="Например: KPI расчет"
                        :disabled="!payoutModalHasDrafts || postingBatch || deletingDrafts"
                    />
                </div>

                <div class="kpi-table-wrapper">
                    <div v-if="payoutCalcSummary" class="kpi-payout-calc">
                        <span v-if="payoutCalcSummary.comparison_basis === 'plan_percent'">
                            План:
                            <strong>{{ formatKpiValue(payoutCalcSummary.plan_value) }}</strong> ·
                            Факт:
                            <strong>{{ formatKpiValue(payoutCalcSummary.fact_value) }}</strong> ·
                            Выполнение:
                            <strong>{{ formatPercent(payoutCalcSummary.comparison_value) }}</strong>
                            · Порог:
                            <strong>{{ formatPercent(payoutCalcSummary.target_value) }}</strong>
                        </span>
                        <span v-else>
                            Факт:
                            <strong>{{ formatKpiValue(payoutCalcSummary.fact_value) }}</strong> ·
                            Условие:
                            <strong
                                >{{ payoutCalcSummary.bonus_condition }}
                                {{ formatKpiValue(payoutCalcSummary.target_value) }}</strong
                            >
                        </span>
                    </div>
                    <table class="kpi-table kpi-table--payout">
                        <thead>
                            <tr>
                                <th>Сотрудник</th>
                                <th>Должность</th>
                                <th>База</th>
                                <th>Часы</th>
                                <th>Сумма</th>
                                <th>Комментарий</th>
                                <th />
                                <th class="kpi-table__post-head">Статус записи</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="row in payoutModalRows" :key="row.key">
                                <td>{{ payoutEmployeeLabel(row) }}</td>
                                <td>{{ positionLabel(row.position_id) }}</td>
                                <td>{{ formatMoney(row.base_amount) }}</td>
                                <td>{{ formatHours(row.calc_snapshot?.hours_sum) }}</td>
                                <td>
                                    <div v-if="isRowEditing(row)" class="kpi-table__editor">
                                        <input
                                            v-model.number="row.amount"
                                            class="kpi-table__input"
                                            type="number"
                                            step="0.01"
                                            :disabled="
                                                row.status !== 'draft' ||
                                                postingBatch ||
                                                deletingDrafts ||
                                                savingItemId === row.item_id
                                            "
                                            @keydown.enter.prevent="() => handleToggleRowEdit(row)"
                                        />
                                    </div>
                                    <div v-else class="kpi-table__value">
                                        {{ formatMoney(row.amount) }}
                                    </div>
                                </td>
                                <td>
                                    <div v-if="isRowEditing(row)" class="kpi-table__editor">
                                        <input
                                            v-model="row.comment"
                                            class="kpi-table__input"
                                            type="text"
                                            placeholder="Комментарий"
                                            :disabled="
                                                row.status !== 'draft' ||
                                                postingBatch ||
                                                deletingDrafts ||
                                                savingItemId === row.item_id
                                            "
                                            @keydown.enter.prevent="() => handleToggleRowEdit(row)"
                                        />
                                    </div>
                                    <div
                                        v-else
                                        class="kpi-table__value kpi-table__value--comment"
                                        :class="{ 'is-empty': !row.comment }"
                                    >
                                        {{ row.comment || '—' }}
                                    </div>
                                </td>
                                <td class="kpi-table__actions">
                                    <div class="kpi-table__actions-inner">
                                        <button
                                            type="button"
                                            class="kpi-table__icon-button"
                                            :class="{ 'is-active': isRowEditing(row) }"
                                            :disabled="
                                                row.status !== 'draft' ||
                                                postingBatch ||
                                                deletingDrafts ||
                                                savingItemId === row.item_id ||
                                                deletingItemId === row.item_id
                                            "
                                            :title="
                                                isRowEditing(row)
                                                    ? 'Сохранить изменения'
                                                    : 'Редактировать'
                                            "
                                            @click="() => handleToggleRowEdit(row)"
                                        >
                                            <BaseIcon name="Edit" />
                                        </button>
                                        <button
                                            type="button"
                                            class="kpi-table__icon-button kpi-table__icon-button--danger"
                                            :disabled="
                                                row.status !== 'draft' ||
                                                postingBatch ||
                                                deletingDrafts ||
                                                deletingItemId === row.item_id ||
                                                savingItemId === row.item_id
                                            "
                                            title="Удалить строку"
                                            @click="() => handleDeleteRow(row)"
                                        >
                                            <BaseIcon name="Trash" />
                                        </button>
                                    </div>
                                </td>
                                <td class="kpi-table__post-cell">
                                    <span
                                        class="kpi-post-result__status"
                                        :class="`is-${rowPostStatusClass(row)}`"
                                    >
                                        {{ rowPostStatusLabel(row) }}
                                    </span>
                                    <p v-if="rowPostReason(row)" class="kpi-post-result__reason">
                                        {{ rowPostReason(row) }}
                                    </p>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </Modal>
    </div>
</template>

<script setup>
    import { computed, onMounted, ref } from 'vue';
    import {
        createKpiPayoutPreviewByMetric,
        deleteKpiPayoutBatch,
        deleteKpiPayoutItem,
        fetchAccessPositions,
        fetchAllEmployees,
        fetchKpiPayoutBatchesBulk,
        fetchKpiPayoutBatches,
        fetchKpiMetrics,
        fetchPayrollAdjustmentTypes,
        fetchRestaurants,
        postKpiPayoutBatch,
        updateKpiPayoutItem,
    } from '@/api';
    import { useToast } from 'vue-toastification';
    import { useUserStore } from '@/stores/user';
    import Button from '@/components/UI-components/Button.vue';
    import FiltersPanel from '@/components/UI-components/FiltersPanel.vue';
    import Input from '@/components/UI-components/Input.vue';
    import DateInput from '@/components/UI-components/DateInput.vue';
    import Modal from '@/components/UI-components/Modal.vue';
    import Select from '@/components/UI-components/Select.vue';
    import BaseIcon from '@/components/UI-components/BaseIcon.vue';

    const toast = useToast();
    const userStore = useUserStore();

    const metrics = ref([]);
    const restaurants = ref([]);
    const positions = ref([]);
    const employeeDirectory = ref([]);
    const batches = ref([]);
    const adjustmentTypes = ref([]);
    const KPI_TYPE_NAME_HINTS = ['kpi бонус', 'kpi штраф', 'kpi', 'премия', 'штраф', 'удерж'];

    const previewForm = ref({
        metricIds: [],
        restaurantIds: [],
        month: new Date().getMonth() + 1,
        year: new Date().getFullYear(),
        comment: '',
    });
    const previewLoading = ref(false);
    const showPreviewModal = ref(false);

    const filters = ref({
        status: null,
        periodFrom: '',
        periodTo: '',
    });
    const isHistoryFiltersOpen = ref(false);

    const loadingBatches = ref(false);
    const showPayoutModal = ref(false);
    const payoutModalBatches = ref([]);
    const payoutModalRows = ref([]);
    const editingRowKey = ref(null);
    const rowPostResults = ref({});
    const savingItemId = ref(null);
    const deletingItemId = ref(null);
    const postingBatch = ref(false);
    const deletingDrafts = ref(false);

    const postForm = ref({
        adjustmentTypeId: null,
        date: '',
        comment: '',
    });

    const statusOptions = [
        { value: 'draft', label: 'Черновик' },
        { value: 'posted', label: 'Записано' },
    ];
    const statusLabels = {
        draft: 'Черновик',
        posted: 'Записано',
        partial: 'Частично',
    };
    const rowPostStatusLabels = {
        draft: 'Черновик',
        pending: 'Записываем',
        created: 'Записано',
        error: 'Ошибка',
    };

    const canManage = computed(() =>
        userStore.hasAnyPermission('kpi.payouts.manage', 'kpi.manage', 'system.admin'),
    );

    const restaurantMap = computed(
        () => new Map(restaurants.value.map((item) => [Number(item.id), item.name])),
    );
    const positionMap = computed(
        () => new Map(positions.value.map((item) => [Number(item.id), item.name])),
    );
    const employeeDirectoryMap = computed(
        () =>
            new Map(
                (employeeDirectory.value || [])
                    .map((employee) => [Number(employee?.id), employee])
                    .filter(([id]) => Number.isFinite(id) && id > 0),
            ),
    );

    const metricOptions = computed(() =>
        metrics.value.map((metric) => ({
            value: metric.id,
            label: metric.unit ? `${metric.name} (${metric.unit})` : metric.name,
        })),
    );
    const selectedPreviewMetricIds = computed(() => {
        const source = Array.isArray(previewForm.value.metricIds)
            ? previewForm.value.metricIds
            : [];
        return Array.from(
            new Set(
                source
                    .map((value) => Number(value))
                    .filter((value) => Number.isFinite(value) && value > 0),
            ),
        );
    });
    const selectedPreviewRestaurantIds = computed(() => {
        const source = Array.isArray(previewForm.value.restaurantIds)
            ? previewForm.value.restaurantIds
            : [];
        return Array.from(
            new Set(
                source
                    .map((value) => Number(value))
                    .filter((value) => Number.isFinite(value) && value > 0),
            ),
        );
    });

    const restaurantOptions = computed(() =>
        restaurants.value.map((rest) => ({ value: Number(rest.id), label: rest.name })),
    );
    const monthOptions = [
        { value: 1, label: 'Январь' },
        { value: 2, label: 'Февраль' },
        { value: 3, label: 'Март' },
        { value: 4, label: 'Апрель' },
        { value: 5, label: 'Май' },
        { value: 6, label: 'Июнь' },
        { value: 7, label: 'Июль' },
        { value: 8, label: 'Август' },
        { value: 9, label: 'Сентябрь' },
        { value: 10, label: 'Октябрь' },
        { value: 11, label: 'Ноябрь' },
        { value: 12, label: 'Декабрь' },
    ];

    const payoutModalRestaurantId = computed(
        () => payoutModalBatches.value?.[0]?.restaurant_id ?? null,
    );
    const payoutModalMetricId = computed(() => payoutModalBatches.value?.[0]?.metric_id ?? null);
    const payoutModalPeriodStart = computed(
        () => payoutModalBatches.value?.[0]?.period_start ?? null,
    );
    const payoutModalPeriodEnd = computed(() => payoutModalBatches.value?.[0]?.period_end ?? null);
    const payoutModalHasDrafts = computed(() =>
        payoutModalBatches.value.some((batch) => batch.status === 'draft'),
    );
    const draftBatchCount = computed(
        () => payoutModalBatches.value.filter((batch) => batch.status === 'draft').length,
    );
    const payoutModalStatusLabel = computed(() => {
        if (!payoutModalBatches.value.length) return '—';
        const hasDraft = payoutModalBatches.value.some((batch) => batch.status === 'draft');
        const hasPosted = payoutModalBatches.value.some((batch) => batch.status === 'posted');
        if (hasDraft && hasPosted) return 'Частично записано';
        if (hasPosted) return 'Записано';
        return 'Черновик';
    });
    const historyCards = computed(() => {
        const groups = new Map();
        for (const batch of batches.value || []) {
            const key = [
                Number(batch.metric_id || 0),
                Number(batch.restaurant_id || 0),
                batch.period_start || '',
                batch.period_end || '',
            ].join('|');
            if (!groups.has(key)) {
                groups.set(key, {
                    key,
                    metric_id: batch.metric_id,
                    restaurant_id: batch.restaurant_id,
                    period_start: batch.period_start,
                    period_end: batch.period_end,
                    created_at: batch.created_at || null,
                    posted_at: batch.posted_at || null,
                    batch_ids: [],
                    has_draft: false,
                    has_posted: false,
                });
            }
            const item = groups.get(key);
            item.batch_ids.push(Number(batch.id));
            item.has_draft = item.has_draft || batch.status === 'draft';
            item.has_posted = item.has_posted || batch.status === 'posted';
            if (
                batch.created_at &&
                (!item.created_at || new Date(batch.created_at) > new Date(item.created_at))
            ) {
                item.created_at = batch.created_at;
            }
            if (
                batch.posted_at &&
                (!item.posted_at || new Date(batch.posted_at) > new Date(item.posted_at))
            ) {
                item.posted_at = batch.posted_at;
            }
        }

        return Array.from(groups.values())
            .map((item) => ({
                ...item,
                status:
                    item.has_draft && item.has_posted
                        ? 'partial'
                        : item.has_posted
                          ? 'posted'
                          : 'draft',
                batch_ids: item.batch_ids.sort((a, b) => a - b),
            }))
            .sort((a, b) => {
                const left = a.created_at ? new Date(a.created_at).getTime() : 0;
                const right = b.created_at ? new Date(b.created_at).getTime() : 0;
                return right - left;
            });
    });

    const payoutSummaryScopeLabel = computed(() =>
        payoutModalHasDrafts.value ? 'Итоги по черновику' : 'Итоги',
    );
    const payoutSummary = computed(() => {
        const allRows = Array.isArray(payoutModalRows.value) ? payoutModalRows.value : [];
        const draftRows = allRows.filter((row) => row.status === 'draft');
        const rows = draftRows.length ? draftRows : allRows;

        let amountTotal = 0;

        for (const row of rows) {
            amountTotal += quantizeMoney(parseAmount(row?.amount));
        }

        amountTotal = quantizeMoney(amountTotal);

        return {
            row_count: rows.length,
            amount_total: amountTotal,
        };
    });

    const payoutCalcSummary = computed(() => {
        const batchesList = Array.isArray(payoutModalBatches.value) ? payoutModalBatches.value : [];
        const firstBatch = batchesList?.[0];
        const snapshot =
            firstBatch?.calc_summary ||
            (Array.isArray(firstBatch?.items) ? firstBatch.items?.[0]?.calc_snapshot : null);
        if (!snapshot || typeof snapshot !== 'object') return null;
        return {
            comparison_basis: snapshot.comparison_basis,
            plan_value: snapshot.plan_value,
            fact_value: snapshot.fact_value,
            comparison_value: snapshot.comparison_value,
            target_value: snapshot.target_value,
            bonus_condition: snapshot.bonus_condition,
        };
    });

    function normalizeName(value) {
        return String(value || '')
            .trim()
            .toLowerCase();
    }

    const adjustmentTypeOptions = computed(() =>
        adjustmentTypes.value
            .filter((type) => type.kind === 'accrual' || type.kind === 'deduction')
            .map((type) => ({
                value: String(type.id),
                label: `${type.name} · ${type.kind === 'deduction' ? 'Удержание' : 'Начисление'}`,
            })),
    );

    function restaurantLabel(id) {
        if (!id) return 'Ресторан не указан';
        return restaurantMap.value.get(Number(id)) || `Ресторан ${id}`;
    }

    function positionLabel(id) {
        if (!id) return 'Должность не указана';
        return positionMap.value.get(Number(id)) || `Должность ${id}`;
    }

    function formatEmployeeName(employee) {
        const parts = [employee?.last_name, employee?.first_name, employee?.middle_name]
            .map((part) => (part || '').trim())
            .filter(Boolean);
        if (parts.length) {
            return parts.join(' ');
        }
        return String(employee?.username || employee?.staff_code || employee?.id || '').trim();
    }

    function payoutEmployeeLabel(row) {
        const directName = String(row?.full_name || '').trim();
        if (directName) {
            return directName;
        }
        const employee = employeeDirectoryMap.value.get(Number(row?.user_id));
        if (employee) {
            return formatEmployeeName(employee);
        }
        const staffCode = String(row?.staff_code || '').trim();
        if (staffCode) {
            return staffCode;
        }
        return row?.user_id ? `ID ${row.user_id}` : '—';
    }

    function formatDate(value) {
        if (!value) return '';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return value;
        }
        return date.toLocaleDateString('ru-RU');
    }

    function formatDateRange(start, end) {
        if (!start && !end) return '';
        if (start && end && start === end) return start;
        return [start, end].filter(Boolean).join(' — ');
    }

    function formatMoney(value) {
        const numberValue = Number(value || 0);
        return new Intl.NumberFormat('ru-RU', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(numberValue);
    }

    function formatKpiValue(value) {
        if (value === null || value === undefined || value === '') return '—';
        const numberValue = Number(value);
        if (!Number.isFinite(numberValue)) return String(value);
        return new Intl.NumberFormat('ru-RU', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
        }).format(numberValue);
    }

    function formatPercent(value) {
        if (value === null || value === undefined || value === '') return '—';
        const numberValue = Number(value);
        if (!Number.isFinite(numberValue)) return String(value);
        return `${Math.round(numberValue * 10) / 10}%`;
    }

    function formatHours(value) {
        if (value === null || value === undefined || value === '') return '—';
        const numberValue = Number(value);
        if (!Number.isFinite(numberValue)) return String(value);
        return `${Math.round(numberValue * 10) / 10}`;
    }

    function parseAmount(value) {
        if (value === null || value === undefined || value === '') return 0;
        const parsed = Number(String(value).replace(',', '.'));
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function resetRowPostResults() {
        rowPostResults.value = {};
    }

    function resetEditingRow() {
        editingRowKey.value = null;
    }

    function isRowEditing(row) {
        return Boolean(row?.key) && editingRowKey.value === String(row.key);
    }

    function setRowPostResults(rowKeys, status, reason = '') {
        if (!Array.isArray(rowKeys) || !rowKeys.length) return;
        const next = { ...rowPostResults.value };
        rowKeys.forEach((rowKey) => {
            next[String(rowKey)] = {
                status,
                reason: reason || '',
            };
        });
        rowPostResults.value = next;
    }

    function getRowPostResult(row) {
        const key = String(row?.key || '');
        if (key && rowPostResults.value[key]) {
            return rowPostResults.value[key];
        }
        if (row?.status === 'posted') {
            return {
                status: 'created',
                reason: 'Записано',
            };
        }
        return {
            status: 'draft',
            reason: '',
        };
    }

    function rowPostStatusClass(row) {
        return getRowPostResult(row).status;
    }

    function rowPostStatusLabel(row) {
        const status = rowPostStatusClass(row);
        return rowPostStatusLabels[status] || status || '—';
    }

    function rowPostReason(row) {
        const result = getRowPostResult(row);
        const reason = String(result.reason || '').trim();
        if (!reason) return '';
        if (result.status === 'created' && reason.toLowerCase() === 'записано') return '';
        if (result.status === 'pending' && reason === 'Записываем...') return '';
        return reason;
    }

    function normalizeIsoDate(value) {
        if (!value) return '';
        if (value instanceof Date && !Number.isNaN(value.getTime())) {
            const year = value.getFullYear();
            const month = String(value.getMonth() + 1).padStart(2, '0');
            const day = String(value.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }
        const raw = String(value).trim();
        if (!raw) return '';
        if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
            return raw;
        }
        const dotMatch = raw.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
        if (dotMatch) {
            return `${dotMatch[3]}-${dotMatch[2]}-${dotMatch[1]}`;
        }
        const isoDateTimeMatch = raw.match(/^(\d{4}-\d{2}-\d{2})[T\s]/);
        if (isoDateTimeMatch) {
            return isoDateTimeMatch[1];
        }
        return '';
    }

    function resolveApiErrorMessage(error, fallback) {
        const detail = error?.response?.data?.detail;

        if (typeof detail === 'string' && detail.trim()) {
            return detail;
        }

        if (Array.isArray(detail) && detail.length) {
            const message = detail
                .map((item) => {
                    if (typeof item === 'string') return item;
                    if (!item || typeof item !== 'object') return '';
                    const itemMessage = typeof item.msg === 'string' ? item.msg : '';
                    const itemLoc = Array.isArray(item.loc) ? item.loc.join('.') : '';
                    if (itemMessage && itemLoc) {
                        return `${itemLoc}: ${itemMessage}`;
                    }
                    return itemMessage;
                })
                .filter(Boolean)
                .join('; ');
            if (message) return message;
        }

        if (detail && typeof detail === 'object') {
            const objectMessage = detail.message || detail.error || detail.msg;
            if (typeof objectMessage === 'string' && objectMessage.trim()) {
                return objectMessage;
            }
        }

        if (typeof error?.message === 'string' && error.message.trim()) {
            return error.message;
        }

        return fallback;
    }

    async function loadOptions() {
        try {
            const [metricsData, restaurantsData, positionsData, typesData, employeesData] =
                await Promise.all([
                    fetchKpiMetrics(),
                    fetchRestaurants(),
                    fetchAccessPositions(),
                    fetchPayrollAdjustmentTypes(),
                    fetchAllEmployees({ include_fired: true, limit: 250 }),
                ]);
            metrics.value = Array.isArray(metricsData?.items)
                ? metricsData.items
                : metricsData || [];
            restaurants.value = Array.isArray(restaurantsData?.items)
                ? restaurantsData.items
                : restaurantsData || [];
            positions.value = Array.isArray(positionsData)
                ? positionsData
                : positionsData?.items || [];
            adjustmentTypes.value = Array.isArray(typesData?.items)
                ? typesData.items
                : typesData || [];
            employeeDirectory.value = Array.isArray(employeesData?.items)
                ? employeesData.items
                : Array.isArray(employeesData)
                  ? employeesData
                  : [];
        } catch (error) {
            toast.error('Не удалось загрузить справочники KPI');
            console.error(error);
        }
    }

    async function loadBatches() {
        loadingBatches.value = true;
        try {
            const params = {};
            if (filters.value.status) params.status = filters.value.status;
            if (filters.value.periodFrom) params.period_from = filters.value.periodFrom;
            if (filters.value.periodTo) params.period_to = filters.value.periodTo;
            const data = await fetchKpiPayoutBatches(params);
            batches.value = Array.isArray(data?.items) ? data.items : data || [];
        } catch (error) {
            toast.error('Не удалось загрузить выплаты KPI');
            console.error(error);
        } finally {
            loadingBatches.value = false;
        }
    }

    function openPreviewModal() {
        if (!canManage.value || previewLoading.value) return;
        showPreviewModal.value = true;
    }

    function closePreviewModal() {
        showPreviewModal.value = false;
    }

    function isPreviewMetricSelected(metricId) {
        const normalizedId = Number(metricId);
        if (!Number.isFinite(normalizedId) || normalizedId <= 0) return false;
        return selectedPreviewMetricIds.value.includes(normalizedId);
    }

    function togglePreviewMetric(metricId) {
        const normalizedId = Number(metricId);
        if (!Number.isFinite(normalizedId) || normalizedId <= 0) return;
        const next = new Set(selectedPreviewMetricIds.value);
        if (next.has(normalizedId)) {
            next.delete(normalizedId);
        } else {
            next.add(normalizedId);
        }
        previewForm.value.metricIds = Array.from(next);
    }

    function selectAllPreviewMetrics() {
        previewForm.value.metricIds = metricOptions.value
            .map((option) => Number(option.value))
            .filter((value) => Number.isFinite(value) && value > 0);
    }

    function clearPreviewMetrics() {
        previewForm.value.metricIds = [];
    }

    function isPreviewRestaurantSelected(restaurantId) {
        const normalizedId = Number(restaurantId);
        if (!Number.isFinite(normalizedId) || normalizedId <= 0) return false;
        return selectedPreviewRestaurantIds.value.includes(normalizedId);
    }

    function togglePreviewRestaurant(restaurantId) {
        const normalizedId = Number(restaurantId);
        if (!Number.isFinite(normalizedId) || normalizedId <= 0) return;
        const next = new Set(selectedPreviewRestaurantIds.value);
        if (next.has(normalizedId)) {
            next.delete(normalizedId);
        } else {
            next.add(normalizedId);
        }
        previewForm.value.restaurantIds = Array.from(next);
    }

    function selectAllPreviewRestaurants() {
        previewForm.value.restaurantIds = restaurantOptions.value
            .map((option) => Number(option.value))
            .filter((value) => Number.isFinite(value) && value > 0);
    }

    function clearPreviewRestaurants() {
        previewForm.value.restaurantIds = [];
    }

    async function handlePreview() {
        const metricIds = selectedPreviewMetricIds.value;
        const restaurantIds = selectedPreviewRestaurantIds.value;
        if (!metricIds.length || !restaurantIds.length || !previewForm.value.month) {
            toast.error('Выберите KPI, рестораны и месяц');
            return;
        }

        previewLoading.value = true;
        try {
            const createdPairs = [];
            const emptyPairs = [];
            const failedPairs = [];

            const basePayload = {
                year: Number(previewForm.value.year),
                month: Number(previewForm.value.month),
                comment: previewForm.value.comment || undefined,
            };

            for (const restaurantId of restaurantIds) {
                for (const metricId of metricIds) {
                    const payload = {
                        ...basePayload,
                        metric_id: Number(metricId),
                        restaurant_id: Number(restaurantId),
                    };
                    try {
                        const data = await createKpiPayoutPreviewByMetric(payload);
                        const items = Array.isArray(data?.items) ? data.items : data || [];
                        if (!items.length) {
                            emptyPairs.push({ metricId, restaurantId });
                            continue;
                        }
                        createdPairs.push({
                            metricId,
                            restaurantId,
                            batches: items,
                        });
                    } catch (error) {
                        failedPairs.push({
                            metricId,
                            restaurantId,
                            message: resolveApiErrorMessage(
                                error,
                                'Не удалось сформировать выплату',
                            ),
                        });
                        console.error(error);
                    }
                }
            }

            if (!createdPairs.length) {
                if (failedPairs.length) {
                    const first = failedPairs[0];
                    const metricName = metricLabel(first.metricId);
                    const restaurantName = restaurantLabel(first.restaurantId);
                    toast.error(`Ошибка для "${metricName}" · ${restaurantName}: ${first.message}`);
                } else {
                    toast.info('Нет сотрудников для выбранных KPI и ресторанов');
                }
                return;
            }

            const createdBatchCount = createdPairs.reduce(
                (sum, item) => sum + (Array.isArray(item.batches) ? item.batches.length : 0),
                0,
            );
            const selectedPairsCount = metricIds.length * restaurantIds.length;

            await loadBatches();

            if (selectedPairsCount === 1 && createdPairs.length === 1) {
                const singleResult = createdPairs[0];
                closePreviewModal();
                openPayoutModal(singleResult.batches, { metricId: singleResult.metricId });
                toast.success(`Сформировано выплат: ${singleResult.batches.length}`);
                return;
            }

            closePreviewModal();

            if (failedPairs.length || emptyPairs.length) {
                toast.warning(
                    `Сформировано для ${createdPairs.length} сочетаний из ${selectedPairsCount} (пакетов: ${createdBatchCount}). ` +
                        `Без сотрудников: ${emptyPairs.length}. Ошибок: ${failedPairs.length}.`,
                );
                return;
            }

            toast.success(
                `Сформировано для ${createdPairs.length} сочетаний KPI/ресторан (пакетов: ${createdBatchCount})`,
            );
        } catch (error) {
            toast.error(resolveApiErrorMessage(error, 'Не удалось сформировать выплату'));
            console.error(error);
        } finally {
            previewLoading.value = false;
        }
    }

    function metricLabel(id) {
        if (!id) return '—';
        const metric = metrics.value.find((row) => Number(row.id) === Number(id));
        return metric?.name || `KPI ${id}`;
    }

    function quantizeMoney(value) {
        const numberValue = Number(value || 0);
        return Number.isFinite(numberValue) ? Math.round(numberValue * 100) / 100 : 0;
    }

    function buildPayoutModalRows(batchesList) {
        const rows = [];
        (batchesList || []).forEach((batch) => {
            const status = batch.status;
            const positionId = batch.position_id;
            const items = Array.isArray(batch?.items) ? batch.items : [];
            items.forEach((item) => {
                const bonus = quantizeMoney(parseAmount(item.bonus_amount));
                const penalty = quantizeMoney(parseAmount(item.penalty_amount));
                const amount = quantizeMoney(parseAmount(item.amount || bonus || penalty));
                rows.push({
                    key: `${batch.id}-${item.id}`,
                    batch_id: Number(batch.id),
                    item_id: Number(item.id),
                    status,
                    position_id: positionId,
                    user_id: item.user_id,
                    staff_code: item.staff_code,
                    full_name: item.full_name,
                    base_amount: item.base_amount,
                    amount,
                    comment: item.comment || '',
                    calc_snapshot: item.calc_snapshot || null,
                    original_amount: amount,
                    original_comment: item.comment || '',
                });
            });
        });

        rows.sort((a, b) => {
            const nameA = String(payoutEmployeeLabel(a) || '').toLowerCase();
            const nameB = String(payoutEmployeeLabel(b) || '').toLowerCase();
            return nameA.localeCompare(nameB, 'ru');
        });

        return rows;
    }

    function hydratePostForm({ metricId, periodEnd, comment }) {
        const today = new Date().toISOString().slice(0, 10);
        postForm.value.date = periodEnd || today;
        postForm.value.comment = comment || '';

        const metric = metrics.value.find((row) => Number(row.id) === Number(metricId));
        postForm.value.adjustmentTypeId =
            (metric?.bonus_adjustment_type_id ? String(metric.bonus_adjustment_type_id) : null) ||
            (metric?.penalty_adjustment_type_id
                ? String(metric.penalty_adjustment_type_id)
                : null) ||
            resolveDefaultAdjustmentTypeId();
    }

    function openPayoutModal(batchesList, { metricId } = {}) {
        const normalizedBatches = Array.isArray(batchesList) ? batchesList : [];
        if (!normalizedBatches.length) {
            toast.info('Выплата не найдена или уже удалена');
            return;
        }

        resetEditingRow();
        resetRowPostResults();
        payoutModalBatches.value = normalizedBatches;
        payoutModalRows.value = buildPayoutModalRows(payoutModalBatches.value);

        const first = payoutModalBatches.value?.[0] || {};
        const fallbackMetricId = selectedPreviewMetricIds.value[0] || null;
        const resolvedMetricId =
            Number(first.metric_id || metricId || fallbackMetricId || 0) || null;
        hydratePostForm({
            metricId: resolvedMetricId,
            periodEnd: first.period_end,
            comment: first.comment || previewForm.value.comment,
        });

        showPayoutModal.value = true;
    }

    async function openBatchGroup(batchIds) {
        const ids = Array.isArray(batchIds)
            ? batchIds.map((item) => Number(item)).filter((item) => Number.isFinite(item))
            : [];
        if (!ids.length) return;
        try {
            const data = await fetchKpiPayoutBatchesBulk(ids);
            const list = Array.isArray(data?.items) ? data.items : data || [];
            if (!list.length) {
                toast.info('Выплата не найдена или уже удалена');
                await loadBatches();
                return;
            }
            openPayoutModal(list, { metricId: list?.[0]?.metric_id });
        } catch (error) {
            toast.error(resolveApiErrorMessage(error, 'Не удалось загрузить выплату'));
            console.error(error);
        }
    }

    function closePayoutModal() {
        showPayoutModal.value = false;
        payoutModalBatches.value = [];
        payoutModalRows.value = [];
        resetEditingRow();
        resetRowPostResults();
        savingItemId.value = null;
        deletingItemId.value = null;
    }

    async function refreshPayoutModal() {
        if (!payoutModalBatches.value.length) return;
        try {
            const ids = payoutModalBatches.value.map((batch) => Number(batch.id));
            const data = await fetchKpiPayoutBatchesBulk(ids);
            const refreshed = Array.isArray(data?.items) ? data.items : data || [];
            payoutModalBatches.value = refreshed;
            payoutModalRows.value = buildPayoutModalRows(refreshed);
            resetEditingRow();
            resetRowPostResults();
        } catch (error) {
            toast.error(resolveApiErrorMessage(error, 'Не удалось обновить выплаты'));
            console.error(error);
        }
    }

    function isRowDirty(row) {
        if (!row || row.status !== 'draft') return false;
        if (quantizeMoney(parseAmount(row.amount)) !== quantizeMoney(row.original_amount)) {
            return true;
        }
        const nextComment = String(row.comment || '');
        const prevComment = String(row.original_comment || '');
        return nextComment !== prevComment;
    }

    async function persistRow(row) {
        if (!row || row.status !== 'draft') return;
        const payload = {
            amount: quantizeMoney(parseAmount(row.amount)),
            comment: row.comment || null,
        };
        await updateKpiPayoutItem(row.batch_id, row.item_id, payload);
        row.original_amount = payload.amount;
        row.original_comment = payload.comment || '';
    }

    async function handleSaveRow(row, options = {}) {
        const { silent = false, closeAfterSave = false } = options;
        if (!row || row.status !== 'draft') return;
        if (!isRowDirty(row)) {
            if (closeAfterSave && isRowEditing(row)) {
                resetEditingRow();
            }
            return true;
        }

        savingItemId.value = row.item_id;
        try {
            await persistRow(row);
            if (!silent) {
                toast.success('Строка обновлена');
            }
            if (closeAfterSave && isRowEditing(row)) {
                resetEditingRow();
            }
            return true;
        } catch (error) {
            if (!silent) {
                toast.error(resolveApiErrorMessage(error, 'Не удалось обновить строку'));
            }
            console.error(error);
            return false;
        } finally {
            savingItemId.value = null;
        }
    }

    async function handleToggleRowEdit(row) {
        if (!row || row.status !== 'draft') return;
        if (postingBatch.value || deletingDrafts.value) return;

        const rowKey = String(row.key || '');
        if (!rowKey) return;

        if (editingRowKey.value && editingRowKey.value !== rowKey) {
            toast.info('Сначала завершите редактирование текущей строки');
            return;
        }

        if (editingRowKey.value === rowKey) {
            await handleSaveRow(row, { silent: true, closeAfterSave: true });
            return;
        }

        editingRowKey.value = rowKey;
    }

    async function handleDeleteRow(row) {
        if (!row || row.status !== 'draft') return;
        if (!window.confirm('Удалить сотрудника из выплаты?')) {
            return;
        }

        deletingItemId.value = row.item_id;
        try {
            const updatedBatch = await deleteKpiPayoutItem(row.batch_id, row.item_id);
            payoutModalBatches.value = payoutModalBatches.value.map((batch) =>
                Number(batch.id) === Number(updatedBatch.id) ? updatedBatch : batch,
            );
            payoutModalRows.value = buildPayoutModalRows(payoutModalBatches.value);
            if (isRowEditing(row)) {
                resetEditingRow();
            }
            if (row?.key) {
                const next = { ...rowPostResults.value };
                delete next[String(row.key)];
                rowPostResults.value = next;
            }
            toast.success('Сотрудник удален из выплаты');
            await loadBatches();
        } catch (error) {
            toast.error(resolveApiErrorMessage(error, 'Не удалось удалить сотрудника'));
            console.error(error);
        } finally {
            deletingItemId.value = null;
        }
    }

    async function handleDeleteDraftBatches() {
        if (!payoutModalHasDrafts.value) {
            toast.info('Нет черновиков для удаления');
            return;
        }

        const draftBatches = payoutModalBatches.value.filter((batch) => batch.status === 'draft');
        const label = draftBatches.length > 1 ? `черновики (${draftBatches.length})` : 'черновик';
        if (!window.confirm(`Удалить ${label} выплаты KPI?`)) {
            return;
        }

        deletingDrafts.value = true;
        try {
            for (const batch of draftBatches) {
                await deleteKpiPayoutBatch(batch.id);
            }

            const next = payoutModalBatches.value.filter((batch) => batch.status !== 'draft');
            if (!next.length) {
                closePayoutModal();
            } else {
                payoutModalBatches.value = next;
                payoutModalRows.value = buildPayoutModalRows(next);
                resetEditingRow();
            }

            toast.success('Черновики удалены');
            await loadBatches();
        } catch (error) {
            toast.error(resolveApiErrorMessage(error, 'Не удалось удалить черновик'));
            console.error(error);
        } finally {
            deletingDrafts.value = false;
        }
    }

    function resolveDefaultAdjustmentTypeId() {
        const list = adjustmentTypes.value.filter(
            (type) => type.kind === 'accrual' || type.kind === 'deduction',
        );
        if (!list.length) return null;
        const lowerHints = KPI_TYPE_NAME_HINTS.map((item) => normalizeName(item));
        const match = list.find((type) =>
            lowerHints.some((hint) => normalizeName(type.name).includes(hint)),
        );
        if (match) return String(match.id);
        return String(list[0].id);
    }

    async function handlePostBatches() {
        if (!payoutModalHasDrafts.value) {
            toast.info('Нет черновиков для записи');
            return;
        }
        if (!postForm.value.date) {
            toast.error('Укажите дату операции');
            return;
        }
        if (!postForm.value.adjustmentTypeId) {
            toast.error('Выберите тип операции');
            return;
        }

        const normalizedDate = normalizeIsoDate(postForm.value.date);
        if (!normalizedDate) {
            toast.error('Укажите корректную дату операции');
            return;
        }

        const adjustmentTypeId = Number(postForm.value.adjustmentTypeId);
        if (!Number.isFinite(adjustmentTypeId) || adjustmentTypeId <= 0) {
            toast.error('Выберите корректный тип операции');
            return;
        }

        postingBatch.value = true;
        try {
            resetEditingRow();
            const payload = {
                adjustment_type_id: adjustmentTypeId,
                date: normalizedDate,
                comment: postForm.value.comment || undefined,
            };

            postForm.value.date = normalizedDate;
            resetRowPostResults();

            const dirtyRows = payoutModalRows.value.filter(isRowDirty);
            for (const row of dirtyRows) {
                try {
                    await persistRow(row);
                } catch (error) {
                    const reason = resolveApiErrorMessage(
                        error,
                        'Не удалось сохранить строку перед записью',
                    );
                    setRowPostResults([row.key], 'error', reason);
                    throw error;
                }
            }

            const draftBatches = payoutModalBatches.value.filter(
                (batch) => batch.status === 'draft',
            );
            const updatedBatches = [];
            let failedBatchCount = 0;

            for (const batch of draftBatches) {
                const batchRowKeys = payoutModalRows.value
                    .filter(
                        (row) =>
                            row.status === 'draft' && Number(row.batch_id) === Number(batch.id),
                    )
                    .map((row) => row.key);

                setRowPostResults(batchRowKeys, 'pending', 'Записываем...');

                try {
                    const updated = await postKpiPayoutBatch(batch.id, payload);
                    updatedBatches.push(updated);
                    setRowPostResults(batchRowKeys, 'created', 'Записано');
                } catch (error) {
                    failedBatchCount += 1;
                    const reason = resolveApiErrorMessage(error, 'Не удалось записать начисления');
                    setRowPostResults(batchRowKeys, 'error', reason);
                    console.error(error);
                }
            }

            if (updatedBatches.length) {
                const updatedMap = new Map(
                    updatedBatches.map((batch) => [Number(batch.id), batch]),
                );
                const nextBatches = payoutModalBatches.value.map(
                    (batch) => updatedMap.get(Number(batch.id)) || batch,
                );
                payoutModalBatches.value = nextBatches;
                payoutModalRows.value = buildPayoutModalRows(nextBatches);

                const persistedResults = { ...rowPostResults.value };
                payoutModalRows.value.forEach((row) => {
                    if (persistedResults[row.key]) return;
                    if (row.status === 'posted') {
                        persistedResults[row.key] = {
                            status: 'created',
                            reason: 'Записано',
                        };
                    }
                });
                rowPostResults.value = persistedResults;
            }

            if (failedBatchCount > 0 && updatedBatches.length > 0) {
                toast.warning('Часть начислений записана. Проверьте статусы строк справа.');
            } else if (failedBatchCount > 0) {
                toast.error('Не удалось записать начисления. Проверьте статусы строк справа.');
            } else {
                toast.success('Начисления записаны');
            }
            await loadBatches();
        } catch (error) {
            toast.error(resolveApiErrorMessage(error, 'Не удалось записать начисления'));
            console.error(error);
        } finally {
            postingBatch.value = false;
        }
    }

    onMounted(async () => {
        await loadOptions();
        await loadBatches();
    });
</script>

<style scoped lang="scss">
    @use '@/assets/styles/pages/kpi-payouts' as *;
</style>
