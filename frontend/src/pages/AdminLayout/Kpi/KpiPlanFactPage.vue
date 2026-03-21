<template>
    <div class="kpi-page">
        <section class="kpi-panel kpi-panel--hero">
            <div class="kpi-panel__header kpi-panel__header--hero">
                <div>
                    <p class="kpi-panel__eyebrow">KPI</p>
                    <h2 class="kpi-panel__title">План / факт</h2>
                    <p v-if="viewMode === 'overall'" class="kpi-panel__subtitle">
                        Сводно по показателям, группам и ресторанам.
                    </p>
                    <p v-else class="kpi-panel__subtitle">
                        Значения по выбранному ресторану.
                    </p>
                </div>
                <div class="kpi-plan-fact__hero-actions">
                    <div class="kpi-plan-fact__year-field">
                        <DateInput
                            v-model="yearPicker"
                            label="Год"
                            type="month"
                            min="2000-01"
                            max="2100-12"
                            :disabled="loading"
                        />
                    </div>
                    <div
                        class="kpi-plan-fact__mode-switch"
                        :class="{ 'is-restaurant': viewMode === 'restaurant' }"
                        role="tablist"
                        aria-label="Режим отображения KPI"
                    >
                        <span class="kpi-plan-fact__mode-indicator" aria-hidden="true"></span>
                        <button
                            v-for="option in viewModeOptions"
                            :key="option.value"
                            type="button"
                            class="kpi-plan-fact__mode-button"
                            :class="{ 'is-active': viewMode === option.value }"
                            :aria-pressed="(viewMode === option.value).toString()"
                            :disabled="loading"
                            @click="viewMode = option.value"
                        >
                            {{ option.label }}
                        </button>
                    </div>
                    <div v-if="viewMode === 'restaurant'" class="kpi-plan-fact__restaurant-field">
                        <Select
                            v-model="restaurantId"
                            label="Ресторан"
                            :options="restaurantOptions"
                            placeholder="Выберите ресторан"
                            :disabled="loading"
                        />
                    </div>
                </div>
            </div>
        </section>

        <section class="kpi-panel">
            <div v-if="!metrics.length" class="kpi-empty">
                <p class="kpi-empty__title">Показателей пока нет</p>
                <p class="kpi-empty__subtitle">Создайте KPI-показатели, чтобы видеть результаты.</p>
            </div>

            <div v-else class="kpi-table-wrapper">
                <table v-if="viewMode === 'restaurant'" class="kpi-table kpi-table--results">
                    <colgroup>
                        <col class="kpi-table__col kpi-table__col--metric" />
                        <col
                            v-for="month in months"
                            :key="`restaurant-col-${month.month}`"
                            class="kpi-table__col kpi-table__col--month"
                        />
                    </colgroup>
                    <thead>
                        <tr>
                            <th>Группа / показатель</th>
                            <th v-for="month in months" :key="month.month">{{ month.short }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <template
                            v-for="block in restaurantBlocks"
                            :key="block.type === 'group' ? `restaurant-group-${block.group.id}` : `restaurant-metric-${block.metric.id}`"
                        >
                            <tr v-if="block.type === 'metric'" class="kpi-row kpi-row--metric">
                                <td class="kpi-result__metric">
                                    <div>
                                        <div class="kpi-result__metric-name">{{ block.metric.name }}</div>
                                        <div v-if="metricMetaLabel(block.metric)" class="kpi-result__metric-unit">
                                            {{ metricMetaLabel(block.metric) }}
                                        </div>
                                    </div>
                                </td>
                                <td
                                    v-for="month in months"
                                    :key="`${block.metric.id}-${month.month}`"
                                    class="kpi-result__cell"
                                >
                                    <div class="kpi-result__value">
                                        {{ restaurantCellValue(block.metric.id, month.month) }}
                                    </div>
                                    <div class="kpi-result__status" :class="restaurantCellStatusClass(block.metric.id, month.month)">
                                        {{ restaurantCellStatusSymbol(block.metric.id, month.month) }}
                                    </div>
                                    <div class="kpi-result__hint">
                                        {{ restaurantCellHint(block.metric.id, month.month) }}
                                    </div>
                                </td>
                            </tr>

                            <template v-else>
                                <tr class="kpi-row kpi-row--group">
                                    <td class="kpi-result__metric kpi-result__metric--expandable kpi-result__metric--group">
                                        <button
                                            type="button"
                                            class="kpi-result__expander"
                                            @click="toggleExpanded(groupToggleKey(block.group.id))"
                                        >
                                            {{ expandedMetrics[groupToggleKey(block.group.id)] ? '▾' : '▸' }}
                                        </button>
                                        <div>
                                            <div class="kpi-result__metric-name">{{ block.group.name }}</div>
                                            <div class="kpi-result__metric-unit">
                                                {{ groupMetaLabel(block.group, block.metrics.length) }}
                                            </div>
                                        </div>
                                    </td>
                                    <td
                                        v-for="month in months"
                                        :key="`restaurant-group-${block.group.id}-${month.month}`"
                                        class="kpi-result__cell"
                                    >
                                        <div class="kpi-result__value">
                                            {{ selectedRestaurantGroupValueLabel(block, month.month) }}
                                        </div>
                                        <div
                                            class="kpi-result__status"
                                            :class="selectedRestaurantGroupStatusClass(block, month.month)"
                                        >
                                            {{ selectedRestaurantGroupStatusSymbol(block, month.month) }}
                                        </div>
                                        <div class="kpi-result__hint">
                                            {{ selectedRestaurantGroupHintLabel(block, month.month) }}
                                        </div>
                                    </td>
                                </tr>

                                <tr
                                    v-for="metric in block.metrics"
                                    v-show="expandedMetrics[groupToggleKey(block.group.id)]"
                                    :key="`restaurant-group-${block.group.id}-metric-${metric.id}`"
                                    class="kpi-row kpi-row--group-metric"
                                >
                                    <td class="kpi-result__metric kpi-result__metric--nested">
                                        <div>
                                            <div class="kpi-result__metric-name">{{ metric.name }}</div>
                                            <div v-if="metricMetaLabel(metric)" class="kpi-result__metric-unit">
                                                {{ metricMetaLabel(metric) }}
                                            </div>
                                        </div>
                                    </td>
                                    <td
                                        v-for="month in months"
                                        :key="`restaurant-group-metric-${metric.id}-${month.month}`"
                                        class="kpi-result__cell"
                                    >
                                        <div class="kpi-result__value">
                                            {{ restaurantCellValue(metric.id, month.month) }}
                                        </div>
                                        <div class="kpi-result__status" :class="restaurantCellStatusClass(metric.id, month.month)">
                                            {{ restaurantCellStatusSymbol(metric.id, month.month) }}
                                        </div>
                                        <div class="kpi-result__hint">
                                            {{ restaurantCellHint(metric.id, month.month) }}
                                        </div>
                                    </td>
                                </tr>
                            </template>
                        </template>
                    </tbody>
                </table>

                <table v-else class="kpi-table kpi-table--results kpi-table--overall">
                    <colgroup>
                        <col class="kpi-table__col kpi-table__col--metric" />
                        <col
                            v-for="month in months"
                            :key="`overall-col-${month.month}`"
                            class="kpi-table__col kpi-table__col--month"
                        />
                        <col class="kpi-table__col kpi-table__col--total" />
                    </colgroup>
                    <thead>
                        <tr>
                            <th>Показатель / группа</th>
                            <th v-for="month in months" :key="month.month">{{ month.short }}</th>
                            <th class="kpi-table__total">Итого</th>
                        </tr>
                    </thead>
                    <tbody>
                        <template
                            v-for="block in overallBlocks"
                            :key="block.type === 'group' ? `overall-group-${block.group.id}` : `overall-metric-${block.metric.id}`"
                        >
                            <template v-if="block.type === 'metric'">
                                <tr class="kpi-row kpi-row--metric">
                                    <td class="kpi-result__metric kpi-result__metric--expandable">
                                        <button
                                            type="button"
                                            class="kpi-result__expander"
                                            @click="toggleExpanded(metricToggleKey(block.metric.id))"
                                        >
                                            {{ expandedMetrics[metricToggleKey(block.metric.id)] ? '▾' : '▸' }}
                                        </button>
                                        <div>
                                            <div class="kpi-result__metric-name">{{ block.metric.name }}</div>
                                            <div v-if="metricMetaLabel(block.metric)" class="kpi-result__metric-unit">
                                                {{ metricMetaLabel(block.metric) }}
                                            </div>
                                        </div>
                                    </td>
                                    <td
                                        v-for="month in months"
                                        :key="`metric-${block.metric.id}-${month.month}`"
                                        class="kpi-result__cell"
                                    >
                                        <div class="kpi-result__value">
                                            {{ metricMonthValueLabel(block.metric, month.month) }}
                                        </div>
                                        <div class="kpi-result__status" :class="metricMonthStatusClass(block.metric, month.month)">
                                            {{ metricMonthStatusSymbol(block.metric, month.month) }}
                                        </div>
                                        <div class="kpi-result__hint">
                                            {{ metricMonthHintLabel(block.metric, month.month) }}
                                        </div>
                                    </td>
                                    <td class="kpi-result__cell kpi-result__cell--total">
                                        <div class="kpi-result__value">{{ metricTotalValueLabel(block.metric) }}</div>
                                        <div class="kpi-result__status" :class="metricTotalStatusClass(block.metric)">
                                            {{ metricTotalStatusSymbol(block.metric) }}
                                        </div>
                                        <div class="kpi-result__hint">
                                            {{ metricTotalHintLabel(block.metric) }}
                                        </div>
                                    </td>
                                </tr>

                                <tr
                                    v-for="rest in metricRestaurants(block.metric)"
                                    v-show="expandedMetrics[metricToggleKey(block.metric.id)]"
                                    :key="`metric-${block.metric.id}-rest-${rest.id}`"
                                    class="kpi-row kpi-row--restaurant"
                                >
                                    <td class="kpi-result__restaurant">
                                        {{ rest.name }}
                                    </td>
                                    <td
                                        v-for="month in months"
                                        :key="`metric-${block.metric.id}-rest-${rest.id}-${month.month}`"
                                        class="kpi-result__cell"
                                    >
                                        <div class="kpi-result__value">
                                            {{ restaurantFactLabel(block.metric.id, rest.id, month.month) }}
                                        </div>
                                        <div class="kpi-result__status" :class="restaurantStatusClass(block.metric.id, rest.id, month.month)">
                                            {{ restaurantStatusSymbol(block.metric.id, rest.id, month.month) }}
                                        </div>
                                        <div class="kpi-result__hint">
                                            {{ restaurantHintLabel(block.metric.id, rest.id, month.month) }}
                                        </div>
                                    </td>
                                    <td class="kpi-result__cell kpi-result__cell--total">
                                        <div class="kpi-result__value">{{ restaurantTotalValueLabel(block.metric.id, rest.id) }}</div>
                                        <div class="kpi-result__status" :class="restaurantTotalStatusClass(block.metric.id, rest.id)">
                                            {{ restaurantTotalStatusSymbol(block.metric.id, rest.id) }}
                                        </div>
                                        <div class="kpi-result__hint">
                                            {{ restaurantTotalHintLabel(block.metric.id, rest.id) }}
                                        </div>
                                    </td>
                                </tr>
                            </template>

                            <template v-else>
                                <tr class="kpi-row kpi-row--group">
                                    <td class="kpi-result__metric kpi-result__metric--expandable kpi-result__metric--group">
                                        <button
                                            type="button"
                                            class="kpi-result__expander"
                                            @click="toggleExpanded(groupToggleKey(block.group.id))"
                                        >
                                            {{ expandedMetrics[groupToggleKey(block.group.id)] ? '▾' : '▸' }}
                                        </button>
                                        <div>
                                            <div class="kpi-result__metric-name">{{ block.group.name }}</div>
                                            <div class="kpi-result__metric-unit">
                                                {{ groupMetaLabel(block.group, block.metrics.length) }}
                                            </div>
                                        </div>
                                    </td>
                                    <td
                                        v-for="month in months"
                                        :key="`group-${block.group.id}-${month.month}`"
                                        class="kpi-result__cell"
                                    >
                                        <div class="kpi-result__value">
                                            {{ groupMonthValueLabel(block, month.month) }}
                                        </div>
                                        <div class="kpi-result__status" :class="groupMonthStatusClass(block, month.month)">
                                            {{ groupMonthStatusSymbol(block, month.month) }}
                                        </div>
                                        <div class="kpi-result__hint">
                                            {{ groupMonthHintLabel(block, month.month) }}
                                        </div>
                                    </td>
                                    <td class="kpi-result__cell kpi-result__cell--total">
                                        <div class="kpi-result__value">{{ groupTotalValueLabel(block) }}</div>
                                        <div class="kpi-result__status" :class="groupTotalStatusClass(block)">
                                            {{ groupTotalStatusSymbol(block) }}
                                        </div>
                                        <div class="kpi-result__hint">
                                            {{ groupTotalHintLabel(block) }}
                                        </div>
                                    </td>
                                </tr>

                                <template v-for="rest in groupRestaurants(block)" :key="`group-${block.group.id}-rest-${rest.id}`">
                                    <tr
                                        v-show="expandedMetrics[groupToggleKey(block.group.id)]"
                                        class="kpi-row kpi-row--group-restaurant"
                                    >
                                        <td class="kpi-result__restaurant kpi-result__restaurant--expandable">
                                            <button
                                                type="button"
                                                class="kpi-result__expander"
                                                @click="toggleExpanded(groupRestaurantToggleKey(block.group.id, rest.id))"
                                            >
                                                {{ expandedMetrics[groupRestaurantToggleKey(block.group.id, rest.id)] ? '▾' : '▸' }}
                                            </button>
                                            <span>{{ rest.name }}</span>
                                        </td>
                                        <td
                                            v-for="month in months"
                                            :key="`group-${block.group.id}-rest-${rest.id}-${month.month}`"
                                            class="kpi-result__cell"
                                        >
                                            <div class="kpi-result__value">
                                                {{ groupRestaurantValueLabel(block, rest.id, month.month) }}
                                            </div>
                                            <div
                                                class="kpi-result__status"
                                                :class="groupRestaurantStatusClass(block, rest.id, month.month)"
                                            >
                                                {{ groupRestaurantStatusSymbol(block, rest.id, month.month) }}
                                            </div>
                                            <div class="kpi-result__hint">
                                                {{ groupRestaurantHintLabel(block, rest.id, month.month) }}
                                            </div>
                                        </td>
                                        <td class="kpi-result__cell kpi-result__cell--total">
                                            <div class="kpi-result__value">
                                                {{ groupRestaurantTotalValueLabel(block, rest.id) }}
                                            </div>
                                            <div
                                                class="kpi-result__status"
                                                :class="groupRestaurantTotalStatusClass(block, rest.id)"
                                            >
                                                {{ groupRestaurantTotalStatusSymbol(block, rest.id) }}
                                            </div>
                                            <div class="kpi-result__hint">
                                                {{ groupRestaurantTotalHintLabel(block, rest.id) }}
                                            </div>
                                        </td>
                                    </tr>

                                    <tr
                                        v-for="metric in groupMetricsForRestaurant(block, rest.id)"
                                        v-show="expandedMetrics[groupToggleKey(block.group.id)] && expandedMetrics[groupRestaurantToggleKey(block.group.id, rest.id)]"
                                        :key="`group-${block.group.id}-rest-${rest.id}-metric-${metric.id}`"
                                        class="kpi-row kpi-row--group-metric"
                                    >
                                        <td class="kpi-result__metric kpi-result__metric--nested">
                                            <div>
                                                <div class="kpi-result__metric-name">{{ metric.name }}</div>
                                                <div v-if="metricMetaLabel(metric)" class="kpi-result__metric-unit">
                                                    {{ metricMetaLabel(metric) }}
                                                </div>
                                            </div>
                                        </td>
                                        <td
                                            v-for="month in months"
                                            :key="`group-metric-${metric.id}-${rest.id}-${month.month}`"
                                            class="kpi-result__cell"
                                        >
                                            <div class="kpi-result__value">
                                                {{ restaurantFactLabel(metric.id, rest.id, month.month) }}
                                            </div>
                                            <div class="kpi-result__status" :class="restaurantStatusClass(metric.id, rest.id, month.month)">
                                                {{ restaurantStatusSymbol(metric.id, rest.id, month.month) }}
                                            </div>
                                            <div class="kpi-result__hint">
                                                {{ restaurantHintLabel(metric.id, rest.id, month.month) }}
                                            </div>
                                        </td>
                                        <td class="kpi-result__cell kpi-result__cell--total">
                                            <div class="kpi-result__value">{{ restaurantTotalValueLabel(metric.id, rest.id) }}</div>
                                            <div class="kpi-result__status" :class="restaurantTotalStatusClass(metric.id, rest.id)">
                                                {{ restaurantTotalStatusSymbol(metric.id, rest.id) }}
                                            </div>
                                            <div class="kpi-result__hint">
                                                {{ restaurantTotalHintLabel(metric.id, rest.id) }}
                                            </div>
                                        </td>
                                    </tr>
                                </template>
                            </template>
                        </template>
                    </tbody>
                </table>
            </div>
        </section>
    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { fetchKpiMetricGroupPlanFactsBulk, fetchKpiMetrics, fetchKpiPlanFactsBulk, fetchRestaurants } from '@/api';
import { useDebounce } from '@/composables/useDebounce';
import { useToast } from 'vue-toastification';
import DateInput from '@/components/UI-components/DateInput.vue';
import Select from '@/components/UI-components/Select.vue';

const toast = useToast();

const loading = ref(false);
const year = ref(new Date().getFullYear());
const yearPicker = ref(toYearPickerValue(year.value));
const viewMode = ref('overall');
const viewModeOptions = [
    { value: 'overall', label: 'Общий' },
    { value: 'restaurant', label: 'По ресторану' },
];

const metrics = ref([]);
const restaurants = ref([]);
const restaurantId = ref(null);

const months = [
    { month: 1, short: 'Янв' },
    { month: 2, short: 'Фев' },
    { month: 3, short: 'Мар' },
    { month: 4, short: 'Апр' },
    { month: 5, short: 'Май' },
    { month: 6, short: 'Июн' },
    { month: 7, short: 'Июл' },
    { month: 8, short: 'Авг' },
    { month: 9, short: 'Сен' },
    { month: 10, short: 'Окт' },
    { month: 11, short: 'Ноя' },
    { month: 12, short: 'Дек' },
];

const expandedMetrics = ref({});
const planFacts = ref({});
const groupPlanFacts = ref({});
const resultsRequestSeq = ref(0);

const restaurantOptions = computed(() =>
    restaurants.value.map((rest) => ({ value: Number(rest.id), label: rest.name })),
);

const metricsById = computed(() => {
    const next = new Map();
    (metrics.value || []).forEach((metric) => {
        next.set(Number(metric.id), metric);
    });
    return next;
});

const metricMetaById = computed(() => {
    const next = new Map();
    const selectedRestaurantId = viewMode.value === 'restaurant' ? Number(restaurantId.value) : null;
    (metrics.value || []).forEach((metric) => {
        const metricId = Number(metric?.id);
        if (!Number.isFinite(metricId)) return;

        const parts = [];
        if (metric?.unit) {
            parts.push(metric.unit);
        }

        const planValues = [];
        const metricFactsByRestaurant = planFacts.value?.[metricId] || {};
        Object.entries(metricFactsByRestaurant).forEach(([restId, monthFacts]) => {
            const numericRestId = Number(restId);
            if (
                Number.isFinite(selectedRestaurantId) &&
                selectedRestaurantId > 0 &&
                numericRestId !== selectedRestaurantId
            ) {
                return;
            }
            Object.values(monthFacts || {}).forEach((monthFact) => {
                const plan = parseNumber(monthFact?.plan_value);
                if (plan !== null) {
                    planValues.push(plan);
                }
            });
        });

        const planLabel = formatPlanRange(planValues);
        const maxScale = metric?.use_max_scale ? parseNumber(metric?.max_scale_value) : null;
        const hasScale = maxScale !== null && maxScale > 0;

        if (planLabel && hasScale) {
            parts.push(`План: ${planLabel} из ${formatNumber(maxScale)}`);
        } else if (planLabel) {
            parts.push(`План: ${planLabel}`);
        } else if (hasScale) {
            parts.push(`Макс. шкала: ${formatNumber(maxScale)}`);
        }

        next.set(metricId, parts.join(' • '));
    });
    return next;
});

const visibleMetrics = computed(() => {
    if (!restaurantId.value) {
        return metrics.value;
    }
    const selectedId = Number(restaurantId.value);
    return metrics.value.filter((metric) => metricAppliesToRestaurant(metric, selectedId));
});

const overallBlocks = computed(() => buildResultBlocks(metrics.value));
const restaurantBlocks = computed(() => buildResultBlocks(visibleMetrics.value));

function parseNumber(value) {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(String(value).replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : null;
}

function formatNumber(value) {
    if (value === null || value === undefined) return '—';
    const num = Number(value);
    if (!Number.isFinite(num)) return '—';
    return new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(num);
}

function toYearPickerValue(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return '';
    return `${Math.trunc(numeric)}-01`;
}

function parseYearFromPicker(value) {
    const raw = String(value ?? '').trim();
    if (!raw) return null;

    const isoMatch = raw.match(/^(\d{4})(?:-\d{2}(?:-\d{2})?)?$/);
    if (isoMatch) {
        return Number(isoMatch[1]);
    }

    const dotMonthMatch = raw.match(/^\d{2}\.(\d{4})$/);
    if (dotMonthMatch) {
        return Number(dotMonthMatch[1]);
    }

    const dotDateMatch = raw.match(/^\d{2}\.\d{2}\.(\d{4})$/);
    if (dotDateMatch) {
        return Number(dotDateMatch[1]);
    }

    return null;
}

function formatPlanRange(values) {
    if (!Array.isArray(values) || !values.length) return '';
    const min = Math.min(...values);
    const max = Math.max(...values);
    if (!Number.isFinite(min) || !Number.isFinite(max)) return '';
    if (Math.abs(min - max) < 0.000001) {
        return formatNumber(min);
    }
    return `${formatNumber(min)}-${formatNumber(max)}`;
}

function metricToggleKey(metricId) {
    return `metric-${metricId}`;
}

function groupToggleKey(groupId) {
    return `group-${groupId}`;
}

function groupRestaurantToggleKey(groupId, restId) {
    return `group-${groupId}-restaurant-${restId}`;
}

function buildResultBlocks(metricList) {
    const groups = new Map();
    (metricList || []).forEach((metric) => {
        const groupId = Number(metric?.group?.id);
        if (!Number.isFinite(groupId) || groupId <= 0) return;
        if (!groups.has(groupId)) {
            groups.set(groupId, {
                type: 'group',
                group: metric.group,
                metrics: [],
            });
        }
        groups.get(groupId).metrics.push(metric);
    });

    const seenGroups = new Set();
    return (metricList || []).reduce((items, metric) => {
        const groupId = Number(metric?.group?.id);
        if (Number.isFinite(groupId) && groupId > 0) {
            if (seenGroups.has(groupId)) {
                return items;
            }
            seenGroups.add(groupId);
            items.push(groups.get(groupId));
            return items;
        }
        items.push({ type: 'metric', metric });
        return items;
    }, []);
}

function metricAppliesToRestaurant(metric, restId) {
    const selectedId = Number(restId);
    if (!Number.isFinite(selectedId) || selectedId <= 0) {
        return false;
    }
    if (metric?.all_restaurants !== false) {
        return true;
    }
    if (!Array.isArray(metric?.restaurant_ids) || !metric.restaurant_ids.length) {
        return false;
    }
    return metric.restaurant_ids.map((id) => Number(id)).includes(selectedId);
}

function groupRestaurants(block) {
    const unique = new Map();
    (block?.metrics || []).forEach((metric) => {
        metricRestaurants(metric).forEach((rest) => {
            const restId = Number(rest.id);
            if (!unique.has(restId)) {
                unique.set(restId, rest);
            }
        });
    });
    return Array.from(unique.values());
}

function groupMetricsForRestaurant(block, restId) {
    return (block?.metrics || []).filter((metric) => metricAppliesToRestaurant(metric, restId));
}

function groupMetaLabel(group, metricsCount) {
    const parts = [];
    if (group?.unit) {
        parts.push(group.unit);
    }
    if (Number.isFinite(metricsCount) && metricsCount > 0) {
        parts.push(`${metricsCount} показ.`);
    }
    return parts.join(' • ') || 'Группа KPI';
}

function metricMetaLabel(metricOrId) {
    const metric = resolveMetric(metricOrId);
    if (!metric) return '';
    return metricMetaById.value.get(Number(metric.id)) || '';
}

function emptySummary() {
    return {
        actual: null,
        plan: null,
        meetsPlan: null,
        hint: '',
    };
}

function summaryReady(summary) {
    return summary?.actual !== null && summary?.actual !== undefined && summary?.plan !== null && summary?.plan !== undefined;
}

function compareToPlan(definition, planValue, factValue) {
    const plan = parseNumber(planValue);
    const fact = parseNumber(factValue);
    if (plan === null || fact === null) return null;
    const direction = definition?.plan_direction === 'lower_better' ? 'lower_better' : 'higher_better';
    if (direction === 'lower_better') {
        if (plan === 0) {
            return fact === 0;
        }
        return fact <= plan;
    }
    return fact >= plan;
}

function buildSummary(definition, actualValue, planValue) {
    const actual = parseNumber(actualValue);
    const plan = parseNumber(planValue);
    if (actual === null || plan === null) {
        return emptySummary();
    }
    return {
        actual,
        plan,
        meetsPlan: compareToPlan(definition, plan, actual),
        hint: '',
    };
}

function entry(metricId, restId, month) {
    return planFacts.value?.[metricId]?.[restId]?.[month] || null;
}

function groupPlanEntry(groupId, restId, month) {
    return groupPlanFacts.value?.[groupId]?.[restId]?.[month] || null;
}

function toggleExpanded(key) {
    expandedMetrics.value = {
        ...expandedMetrics.value,
        [key]: !expandedMetrics.value[key],
    };
}

function metricRestaurants(metric) {
    if (!metric) return [];
    if (metric.all_restaurants !== false) {
        return restaurants.value;
    }
    const allowed = Array.isArray(metric.restaurant_ids) ? metric.restaurant_ids.map((id) => Number(id)) : [];
    return restaurants.value.filter((rest) => allowed.includes(Number(rest.id)));
}

function averageNumeric(values) {
    if (!values.length) return null;
    return values.reduce((sum, value) => sum + Number(value), 0) / values.length;
}

function sumNumeric(values) {
    if (!values.length) return null;
    return values.reduce((sum, value) => sum + Number(value), 0);
}

function averageSummaries(definition, summaries) {
    const valid = summaries.filter(summaryReady);
    if (!valid.length) {
        return emptySummary();
    }
    return buildSummary(definition, averageNumeric(valid.map((item) => item.actual)), averageNumeric(valid.map((item) => item.plan)));
}

function sumSummaries(definition, summaries) {
    const valid = summaries.filter(summaryReady);
    if (!valid.length) {
        return emptySummary();
    }
    return buildSummary(definition, sumNumeric(valid.map((item) => item.actual)), sumNumeric(valid.map((item) => item.plan)));
}

function summaryValueLabel(summary) {
    return summaryReady(summary) ? formatNumber(summary.actual) : '—';
}

function summaryHintLabel(summary) {
    return summaryReady(summary) ? summary.hint : '';
}

function summaryStatusSymbol(summary) {
    if (!summaryReady(summary) || summary.meetsPlan === null) return '';
    return summary.meetsPlan ? '✓' : '✕';
}

function summaryStatusClass(summary) {
    if (!summaryReady(summary) || summary.meetsPlan === null) return 'is-muted';
    return summary.meetsPlan ? 'is-success' : 'is-danger';
}

function resolveMetric(metricOrId) {
    if (metricOrId && typeof metricOrId === 'object') {
        return metricOrId;
    }
    return metricsById.value.get(Number(metricOrId)) || null;
}

function metricMonthRestaurantSummary(metricOrId, restId, month) {
    const metric = resolveMetric(metricOrId);
    if (!metric) {
        return emptySummary();
    }
    const row = entry(Number(metric.id), Number(restId), Number(month));
    return buildSummary(metric, row?.fact_value, row?.plan_value);
}

function metricRestaurantYearSummary(metricOrId, restId) {
    const metric = resolveMetric(metricOrId);
    if (!metric) {
        return emptySummary();
    }
    return sumSummaries(
        metric,
        months.map(({ month }) => metricMonthRestaurantSummary(metric, restId, month)),
    );
}

function metricMonthOverallSummary(metric, month) {
    return averageSummaries(
        metric,
        metricRestaurants(metric).map((rest) => metricMonthRestaurantSummary(metric, Number(rest.id), month)),
    );
}

function metricOverallYearSummary(metric) {
    return averageSummaries(
        metric,
        metricRestaurants(metric).map((rest) => metricRestaurantYearSummary(metric, Number(rest.id))),
    );
}

function groupRestaurantMonthSummary(block, restId, month) {
    const metricSummaries = groupMetricsForRestaurant(block, restId)
        .map((metric) => metricMonthRestaurantSummary(metric, restId, month))
        .filter(summaryReady);
    if (!metricSummaries.length) {
        return emptySummary();
    }
    const planRow = groupPlanEntry(block?.group?.id, Number(restId), Number(month));
    return buildSummary(
        block?.group,
        averageNumeric(metricSummaries.map((item) => item.actual)),
        planRow?.plan_value,
    );
}

function groupRestaurantYearSummary(block, restId) {
    return sumSummaries(
        block?.group,
        months.map(({ month }) => groupRestaurantMonthSummary(block, restId, month)),
    );
}

function groupMonthSummary(block, month) {
    return averageSummaries(
        block?.group,
        groupRestaurants(block).map((rest) => groupRestaurantMonthSummary(block, Number(rest.id), month)),
    );
}

function groupOverallYearSummary(block) {
    return averageSummaries(
        block?.group,
        groupRestaurants(block).map((rest) => groupRestaurantYearSummary(block, Number(rest.id))),
    );
}

function restaurantCellSummary(metricId, month) {
    if (!restaurantId.value) {
        return emptySummary();
    }
    return metricMonthRestaurantSummary(metricId, Number(restaurantId.value), month);
}

function restaurantCellValue(metricId, month) {
    return summaryValueLabel(restaurantCellSummary(metricId, month));
}

function restaurantCellHint(metricId, month) {
    return summaryHintLabel(restaurantCellSummary(metricId, month));
}

function restaurantCellStatusSymbol(metricId, month) {
    return summaryStatusSymbol(restaurantCellSummary(metricId, month));
}

function restaurantCellStatusClass(metricId, month) {
    return summaryStatusClass(restaurantCellSummary(metricId, month));
}

function metricMonthValueLabel(metric, month) {
    return summaryValueLabel(metricMonthOverallSummary(metric, month));
}

function metricMonthHintLabel(metric, month) {
    return summaryHintLabel(metricMonthOverallSummary(metric, month));
}

function metricMonthStatusSymbol(metric, month) {
    return summaryStatusSymbol(metricMonthOverallSummary(metric, month));
}

function metricMonthStatusClass(metric, month) {
    return summaryStatusClass(metricMonthOverallSummary(metric, month));
}

function metricTotalValueLabel(metric) {
    return summaryValueLabel(metricOverallYearSummary(metric));
}

function metricTotalHintLabel(metric) {
    return summaryHintLabel(metricOverallYearSummary(metric));
}

function metricTotalStatusSymbol(metric) {
    return summaryStatusSymbol(metricOverallYearSummary(metric));
}

function metricTotalStatusClass(metric) {
    return summaryStatusClass(metricOverallYearSummary(metric));
}

function restaurantFactLabel(metricId, restId, month) {
    return summaryValueLabel(metricMonthRestaurantSummary(metricId, restId, month));
}

function restaurantHintLabel(metricId, restId, month) {
    return summaryHintLabel(metricMonthRestaurantSummary(metricId, restId, month));
}

function restaurantStatusSymbol(metricId, restId, month) {
    return summaryStatusSymbol(metricMonthRestaurantSummary(metricId, restId, month));
}

function restaurantStatusClass(metricId, restId, month) {
    return summaryStatusClass(metricMonthRestaurantSummary(metricId, restId, month));
}

function restaurantTotalValueLabel(metricId, restId) {
    return summaryValueLabel(metricRestaurantYearSummary(metricId, restId));
}

function restaurantTotalHintLabel(metricId, restId) {
    return summaryHintLabel(metricRestaurantYearSummary(metricId, restId));
}

function restaurantTotalStatusSymbol(metricId, restId) {
    return summaryStatusSymbol(metricRestaurantYearSummary(metricId, restId));
}

function restaurantTotalStatusClass(metricId, restId) {
    return summaryStatusClass(metricRestaurantYearSummary(metricId, restId));
}

function groupMonthValueLabel(block, month) {
    return summaryValueLabel(groupMonthSummary(block, month));
}

function groupMonthHintLabel(block, month) {
    return summaryHintLabel(groupMonthSummary(block, month));
}

function groupMonthStatusSymbol(block, month) {
    return summaryStatusSymbol(groupMonthSummary(block, month));
}

function groupMonthStatusClass(block, month) {
    return summaryStatusClass(groupMonthSummary(block, month));
}

function groupTotalValueLabel(block) {
    return summaryValueLabel(groupOverallYearSummary(block));
}

function groupTotalHintLabel(block) {
    return summaryHintLabel(groupOverallYearSummary(block));
}

function groupTotalStatusSymbol(block) {
    return summaryStatusSymbol(groupOverallYearSummary(block));
}

function groupTotalStatusClass(block) {
    return summaryStatusClass(groupOverallYearSummary(block));
}

function groupRestaurantValueLabel(block, restId, month) {
    return summaryValueLabel(groupRestaurantMonthSummary(block, restId, month));
}

function groupRestaurantHintLabel(block, restId, month) {
    return summaryHintLabel(groupRestaurantMonthSummary(block, restId, month));
}

function groupRestaurantStatusSymbol(block, restId, month) {
    return summaryStatusSymbol(groupRestaurantMonthSummary(block, restId, month));
}

function groupRestaurantStatusClass(block, restId, month) {
    return summaryStatusClass(groupRestaurantMonthSummary(block, restId, month));
}

function groupRestaurantTotalValueLabel(block, restId) {
    return summaryValueLabel(groupRestaurantYearSummary(block, restId));
}

function groupRestaurantTotalHintLabel(block, restId) {
    return summaryHintLabel(groupRestaurantYearSummary(block, restId));
}

function groupRestaurantTotalStatusSymbol(block, restId) {
    return summaryStatusSymbol(groupRestaurantYearSummary(block, restId));
}

function groupRestaurantTotalStatusClass(block, restId) {
    return summaryStatusClass(groupRestaurantYearSummary(block, restId));
}

function selectedRestaurantGroupSummary(block, month) {
    if (!restaurantId.value) {
        return emptySummary();
    }
    return groupRestaurantMonthSummary(block, Number(restaurantId.value), month);
}

function selectedRestaurantGroupValueLabel(block, month) {
    return summaryValueLabel(selectedRestaurantGroupSummary(block, month));
}

function selectedRestaurantGroupHintLabel(block, month) {
    return summaryHintLabel(selectedRestaurantGroupSummary(block, month));
}

function selectedRestaurantGroupStatusSymbol(block, month) {
    return summaryStatusSymbol(selectedRestaurantGroupSummary(block, month));
}

function selectedRestaurantGroupStatusClass(block, month) {
    return summaryStatusClass(selectedRestaurantGroupSummary(block, month));
}

async function loadMetrics() {
    try {
        const data = await fetchKpiMetrics();
        metrics.value = Array.isArray(data?.items) ? data.items : data || [];
    } catch (error) {
        toast.error('Не удалось загрузить показатели KPI');
        console.error(error);
    }
}

async function loadRestaurants() {
    try {
        const data = await fetchRestaurants();
        restaurants.value = Array.isArray(data?.items) ? data.items : data || [];
        if (!restaurantId.value && restaurants.value.length) {
            restaurantId.value = Number(restaurants.value[0].id);
        }
    } catch (error) {
        toast.error('Не удалось загрузить рестораны');
        console.error(error);
    }
}

function resetExpanded() {
    expandedMetrics.value = {};
}

async function loadResults() {
    const requestSeq = ++resultsRequestSeq.value;
    loading.value = true;
    try {
        if (!metrics.value.length) {
            await loadMetrics();
        }
        if (!restaurants.value.length) {
            await loadRestaurants();
        }
        resetExpanded();

        const yearValue = Number(year.value);
        const params = { year: yearValue };
        if (viewMode.value === 'restaurant') {
            if (!restaurantId.value) {
                if (requestSeq !== resultsRequestSeq.value) {
                    return;
                }
                planFacts.value = {};
                groupPlanFacts.value = {};
                return;
            }
            params.restaurant_id = Number(restaurantId.value);
        }

        const [metricPlanFactData, groupPlanFactData] = await Promise.all([
            fetchKpiPlanFactsBulk(params),
            fetchKpiMetricGroupPlanFactsBulk(params),
        ]);
        const items = Array.isArray(metricPlanFactData?.items) ? metricPlanFactData.items : metricPlanFactData || [];
        const nextMap = {};
        items.forEach((item) => {
            const metricId = Number(item.metric_id);
            const restId = Number(item.restaurant_id);
            const month = Number(item.month);
            if (!nextMap[metricId]) nextMap[metricId] = {};
            if (!nextMap[metricId][restId]) nextMap[metricId][restId] = {};
            nextMap[metricId][restId][month] = {
                plan_value: item.plan_value ?? null,
                fact_value: item.fact_value ?? null,
            };
        });
        if (requestSeq !== resultsRequestSeq.value) {
            return;
        }
        planFacts.value = nextMap;

        const groupItems = Array.isArray(groupPlanFactData?.items) ? groupPlanFactData.items : groupPlanFactData || [];
        const nextGroupMap = {};
        groupItems.forEach((item) => {
            const groupId = Number(item.group_id);
            const restId = Number(item.restaurant_id);
            const month = Number(item.month);
            if (!nextGroupMap[groupId]) nextGroupMap[groupId] = {};
            if (!nextGroupMap[groupId][restId]) nextGroupMap[groupId][restId] = {};
            nextGroupMap[groupId][restId][month] = {
                plan_value: item.plan_value ?? null,
                fact_value: item.fact_value ?? null,
            };
        });
        if (requestSeq !== resultsRequestSeq.value) {
            return;
        }
        groupPlanFacts.value = nextGroupMap;
    } catch (error) {
        if (requestSeq !== resultsRequestSeq.value) {
            return;
        }
        toast.error('Не удалось загрузить результаты KPI');
        console.error(error);
    } finally {
        if (requestSeq === resultsRequestSeq.value) {
            loading.value = false;
        }
    }
}

const scheduleResultsReload = useDebounce(() => {
    loadResults();
}, 250);

watch(
    () => yearPicker.value,
    (value) => {
        const parsedYear = parseYearFromPicker(value);
        if (parsedYear !== null && parsedYear !== Number(year.value)) {
            year.value = parsedYear;
        }
    },
);

watch(
    () => year.value,
    (value) => {
        const pickerValue = toYearPickerValue(value);
        if (pickerValue && yearPicker.value !== pickerValue) {
            yearPicker.value = pickerValue;
        }
        scheduleResultsReload();
    },
);

watch(
    () => viewMode.value,
    () => scheduleResultsReload(),
);

watch(
    () => restaurantId.value,
    () => {
        if (viewMode.value === 'restaurant') {
            scheduleResultsReload();
        }
    },
);

onMounted(async () => {
    await loadRestaurants();
    await loadMetrics();
    await loadResults();
});

onBeforeUnmount(() => {
    scheduleResultsReload.cancel?.();
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kpi-plan-fact' as *;
</style>
