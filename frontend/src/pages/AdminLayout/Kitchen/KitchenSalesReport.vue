<template>
    <div class="admin-page kitchen-sales-page">
        <header class="admin-page__header">
            <div class="kitchen-sales-page__header-content">
                <h1 class="admin-page__title">Продажи</h1>
                <p class="admin-page__subtitle">
                    Конструктор отчета по продажам iiko: соберите строки, колонки, метрики и фильтры
                    под свою задачу.
                </p>
                <div class="kitchen-sales-page__header-meta">
                    <span class="kitchen-sales-page__meta-chip">
                        <span class="kitchen-sales-page__meta-chip-label">Период</span>
                        {{ periodLabel }}
                    </span>
                    <span class="kitchen-sales-page__meta-chip">
                        <span class="kitchen-sales-page__meta-chip-label">Режим</span>
                        {{ reportTypeLabel }}
                    </span>
                    <span class="kitchen-sales-page__meta-chip">
                        <span class="kitchen-sales-page__meta-chip-label">Ресторан</span>
                        {{ selectedRestaurantLabel }}
                    </span>
                    <span class="kitchen-sales-page__meta-chip">
                        <span class="kitchen-sales-page__meta-chip-label">Фильтры</span>
                        {{ formatNumber(activeFiltersCount) }}
                    </span>
                    <span v-if="reportBuilt" class="kitchen-sales-page__meta-chip">
                        <span class="kitchen-sales-page__meta-chip-label">Строк отчета</span>
                        {{ formatNumber(reportRows.length) }}
                    </span>
                </div>
                <div class="kitchen-sales-page__header-cta">
                    <Button color="secondary" :disabled="!canViewSalesReport" @click="toggleBuilder">
                        {{ isBuilderOpen ? 'Скрыть конструктор' : 'Построить отчет' }}
                    </Button>
                </div>
            </div>
        </header>

        <section v-if="!canViewSalesReport" class="admin-page__section">
            <div class="admin-page__empty">Недостаточно прав для просмотра отчета по продажам.</div>
        </section>

        <section v-if="canViewSalesReport && isBuilderOpen" class="kitchen-sales-page__builder-panel">
            <div class="kitchen-sales-page__builder-scroll">
                <div class="kitchen-sales-page__builder-layout">
                    <aside class="kitchen-sales-page__builder-rail">
                        <div class="kitchen-sales-page__compact-panel">
                            <div class="kitchen-sales-page__compact-row">
                                <p class="kitchen-sales-page__compact-label">Тип отчета</p>
                                <Select v-model="reportType" :options="reportTypeOptions" />
                            </div>
                            <div class="kitchen-sales-page__compact-row">
                                <p class="kitchen-sales-page__compact-label">Ресторан</p>
                                <Select
                                    v-model="restaurantId"
                                    :options="restaurantOptions"
                                    placeholder="Все рестораны"
                                />
                            </div>
                            <div class="kitchen-sales-page__compact-row">
                                <p class="kitchen-sales-page__compact-label">С даты</p>
                                <DateInput v-model="fromDate" />
                            </div>
                            <div class="kitchen-sales-page__compact-row">
                                <p class="kitchen-sales-page__compact-label">По дату</p>
                                <DateInput v-model="toDate" />
                            </div>
                            <div class="kitchen-sales-page__compact-row">
                                <p class="kitchen-sales-page__compact-label">Данные по</p>
                                <Select v-model="waiterMode" :options="waiterModeOptions" />
                            </div>
                            <div class="kitchen-sales-page__compact-row">
                                <p class="kitchen-sales-page__compact-label">Сотрудник</p>
                                <Select
                                    v-model="waiterKey"
                                    :options="waiterOptions"
                                    placeholder="Все сотрудники"
                                    searchable
                                    search-placeholder="Поиск сотрудника"
                                />
                            </div>
                            <div class="kitchen-sales-page__compact-row">
                                <p class="kitchen-sales-page__compact-label">Параметры</p>
                                <div class="kitchen-sales-page__compact-flags">
                                    <Checkbox v-model="showDeleted" label="Показывать удаленные" />
                                    <Checkbox
                                        v-model="realMoneyOnly"
                                        label="Формировать по реальным деньгам"
                                    />
                                </div>
                            </div>
                        </div>
                    </aside>

                    <div class="kitchen-sales-page__builder-main">
                        <div class="kitchen-sales-page__section-card">
                            <div class="kitchen-sales-page__section-head">
                                <h4 class="kitchen-sales-page__section-caption">
                                    {{
                                        reportType === 'sales'
                                            ? 'Строки и столбцы'
                                            : 'Дополнительные фильтры к отчету'
                                    }}
                                </h4>
                            </div>

                            <div
                                v-if="reportType === 'sales'"
                                class="kitchen-sales-page__constructor-grid"
                            >
                                <div class="kitchen-sales-page__builder-card">
                                    <p class="kitchen-sales-page__card-title">Строки</p>
                                    <Select
                                        v-model="constructorDraft.rowField"
                                        :options="rowFieldSelectorOptions"
                                        placeholder="Выберите поле"
                                        searchable
                                        search-placeholder="Поиск поля"
                                    />
                                    <p class="kitchen-sales-page__card-hint">
                                        В строках теперь выбирается только одно поле.
                                    </p>
                                </div>

                                <div class="kitchen-sales-page__builder-card">
                                    <p class="kitchen-sales-page__card-title">Столбцы</p>
                                    <Select
                                        v-model="constructorDraft.columnField"
                                        :options="columnFieldSelectorOptions"
                                        placeholder="Выберите поле"
                                        searchable
                                        search-placeholder="Поиск поля"
                                    />
                                    <p class="kitchen-sales-page__card-hint">
                                        В столбцах тоже используется только одно поле.
                                    </p>
                                </div>
                            </div>

                            <div
                                v-else
                                class="kitchen-sales-page__constructor-grid kitchen-sales-page__constructor-grid--abc"
                            >
                                <div class="kitchen-sales-page__builder-card">
                                    <p class="kitchen-sales-page__card-title">
                                        Настройки ABC-анализа
                                    </p>
                                    <div class="kitchen-sales-page__abc-grid">
                                        <Select
                                            v-model="abcSettings.group_by"
                                            label="Группировать по"
                                            :options="abcGroupOptions"
                                        />
                                        <Select
                                            v-model="abcSettings.basis_metric"
                                            label="Основа анализа"
                                            :options="abcMetricOptions"
                                        />
                                        <Input
                                            v-model="abcSettings.threshold_a"
                                            type="number"
                                            label="Граница A, %"
                                            placeholder="80"
                                        />
                                        <Input
                                            v-model="abcSettings.threshold_b"
                                            type="number"
                                            label="Граница B, %"
                                            placeholder="95"
                                        />
                                    </div>
                                    <p class="kitchen-sales-page__card-hint">
                                        Логика: A до {{ formatNumber(abcSettings.threshold_a) }}%, B
                                        до {{ formatNumber(abcSettings.threshold_b) }}%, остальное -
                                        C.
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div class="kitchen-sales-page__section-card">
                            <div class="kitchen-sales-page__rule-toolbar">
                                <h4 class="kitchen-sales-page__section-caption">Фильтры</h4>
                                <div class="kitchen-sales-page__rule-toolbar-actions">
                                    <button
                                        type="button"
                                        class="kitchen-sales-page__filter-toggle kitchen-sales-page__filter-toggle--plus"
                                        :class="{ 'is-active': activeRuleMode === 'include' }"
                                        title="Добавить включающий фильтр"
                                        @click="startRuleComposer('include')"
                                    >
                                        <span>Включить</span>
                                        <strong>{{ includeRules.length }}</strong>
                                    </button>
                                    <button
                                        type="button"
                                        class="kitchen-sales-page__filter-toggle kitchen-sales-page__filter-toggle--minus"
                                        :class="{ 'is-active': activeRuleMode === 'exclude' }"
                                        title="Добавить исключающий фильтр"
                                        @click="startRuleComposer('exclude')"
                                    >
                                        <span>Исключить</span>
                                        <strong>{{ excludeRules.length }}</strong>
                                    </button>
                                </div>
                            </div>

                            <p
                                v-if="!activeRuleMode && !includeRules.length && !excludeRules.length"
                                class="kitchen-sales-page__card-hint"
                            >
                                Нажмите «Включить» или «Исключить», затем выберите параметр и значение.
                            </p>
                            <p v-else-if="!activeRuleMode" class="kitchen-sales-page__card-hint">
                                Чтобы добавить еще правило, нажмите «Включить» или «Исключить».
                            </p>

                            <div
                                v-if="activeRuleMode"
                                class="kitchen-sales-page__builder-card kitchen-sales-page__builder-card--composer"
                            >
                                <div class="kitchen-sales-page__rule-header">
                                    <p class="kitchen-sales-page__card-title">
                                        {{
                                            activeRuleMode === 'include'
                                                ? 'Добавить во включение (+)'
                                                : 'Добавить в исключение (-)'
                                        }}
                                    </p>
                                </div>
                                <div class="kitchen-sales-page__rule-add-row">
                                    <Select
                                        v-model="ruleDraft.field_key"
                                        label="Параметр"
                                        :options="filterFieldOptions"
                                        placeholder="Выберите параметр"
                                        @update:model-value="onDraftFieldChange"
                                    />
                                    <Select
                                        v-if="ruleDraft.field_key"
                                        v-model="ruleDraft.value"
                                        label="Значение"
                                        :options="getFilterValueOptions(ruleDraft.field_key)"
                                        placeholder="Выберите значение"
                                        searchable
                                        search-placeholder="Поиск значения"
                                    />
                                    <Button
                                        color="ghost"
                                        :disabled="!ruleDraft.field_key || !ruleDraft.value"
                                        @click="addDraftRule"
                                    >
                                        + Добавить
                                    </Button>
                                </div>
                            </div>

                            <div
                                v-if="includeRules.length || excludeRules.length"
                                class="kitchen-sales-page__rule-lists"
                            >
                                <div v-if="includeRules.length" class="kitchen-sales-page__builder-card">
                                    <p class="kitchen-sales-page__rule-group-title">Включить (+)</p>
                                    <div class="kitchen-sales-page__rule-list">
                                        <div
                                            v-for="rule in includeRules"
                                            :key="rule.id"
                                            class="kitchen-sales-page__rule-item"
                                        >
                                            <span class="kitchen-sales-page__rule-item-text">
                                                {{ formatRuleLabel(rule) }}
                                            </span>
                                            <Button
                                                color="ghost"
                                                @click="removeFilterRule('include', rule.id)"
                                            >
                                                Удалить
                                            </Button>
                                        </div>
                                    </div>
                                </div>

                                <div v-if="excludeRules.length" class="kitchen-sales-page__builder-card">
                                    <p class="kitchen-sales-page__rule-group-title">Исключить (-)</p>
                                    <div class="kitchen-sales-page__rule-list">
                                        <div
                                            v-for="rule in excludeRules"
                                            :key="rule.id"
                                            class="kitchen-sales-page__rule-item"
                                        >
                                            <span class="kitchen-sales-page__rule-item-text">
                                                {{ formatRuleLabel(rule) }}
                                            </span>
                                            <Button
                                                color="ghost"
                                                @click="removeFilterRule('exclude', rule.id)"
                                            >
                                                Удалить
                                            </Button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div
                        class="kitchen-sales-page__builder-actions kitchen-sales-page__builder-actions--rail"
                    >
                        <Button
                            color="secondary"
                            :loading="loadingReport"
                            :disabled="loadingReport"
                            @click="buildReport"
                        >
                            Построить отчет
                        </Button>
                    </div>
                </div>
            </div>
        </section>
        <section v-if="canViewSalesReport && reportBuilt" class="kitchen-sales-page__stats">
            <article class="kitchen-sales-page__stat-card">
                <p class="kitchen-sales-page__stat-label">Позиции</p>
                <p class="kitchen-sales-page__stat-value">
                    {{ formatNumber(reportStats.items_count) }}
                </p>
            </article>
            <article class="kitchen-sales-page__stat-card">
                <p class="kitchen-sales-page__stat-label">Уникальных чеков</p>
                <p class="kitchen-sales-page__stat-value">
                    {{ formatNumber(reportStats.orders_count) }}
                </p>
            </article>
            <article class="kitchen-sales-page__stat-card">
                <p class="kitchen-sales-page__stat-label">Количество</p>
                <p class="kitchen-sales-page__stat-value">{{ formatNumber(reportStats.qty) }}</p>
            </article>
            <article class="kitchen-sales-page__stat-card">
                <p class="kitchen-sales-page__stat-label">Нагрузка кухни</p>
                <p class="kitchen-sales-page__stat-value">
                    {{ formatNumber(reportStats.kitchen_load_qty) }}
                </p>
            </article>
            <article class="kitchen-sales-page__stat-card">
                <p class="kitchen-sales-page__stat-label">Нагрузка зала</p>
                <p class="kitchen-sales-page__stat-value">
                    {{ formatNumber(reportStats.hall_load_qty) }}
                </p>
            </article>
            <article v-if="canViewSalesMoney" class="kitchen-sales-page__stat-card">
                <p class="kitchen-sales-page__stat-label">Продажи</p>
                <p class="kitchen-sales-page__stat-value">{{ formatMoney(reportStats.sum) }}</p>
            </article>
            <article v-if="canViewSalesMoney" class="kitchen-sales-page__stat-card">
                <p class="kitchen-sales-page__stat-label">Скидки</p>
                <p class="kitchen-sales-page__stat-value">
                    {{ formatMoney(reportStats.discount_sum) }}
                </p>
            </article>
        </section>

        <section v-if="canViewSalesReport && reportBuilt" class="admin-page__section">
            <h3 class="kitchen-sales-page__section-title">
                {{ reportType === 'abc' ? 'ABC-анализ' : 'Результат конструктора' }}
            </h3>

            <div v-if="loadingReport" class="admin-page__empty">Формируем отчет...</div>
            <div
                v-else-if="reportType === 'abc' ? !abcReportRows.length : !pivotData.rows.length"
                class="admin-page__empty"
            >
                Нет данных по выбранным параметрам.
            </div>

            <div v-else>
                <div v-if="reportType === 'sales'" class="kitchen-sales-page__metric-switcher">
                    <Select
                        v-model="activeMetricKey"
                        label="Показатель"
                        :options="reportMetricOptions"
                    />
                </div>

                <div class="kitchen-sales-page__report-wrap">
                    <Table v-if="reportType === 'abc'" class="kitchen-sales-page__report-table">
                        <thead>
                            <tr>
                                <th>{{ abcGroupLabel }}</th>
                                <th>Позиции</th>
                                <th>Количество</th>
                                <th v-if="canViewSalesMoney">Продажи, руб</th>
                                <th>{{ abcMetricLabel }}</th>
                                <th>Доля, %</th>
                                <th>Накопленно, %</th>
                                <th>Класс</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="row in abcReportRows" :key="row.group_value">
                                <td>{{ row.group_value }}</td>
                                <td class="kitchen-sales-page__metric-cell">
                                    {{ formatNumber(row.items_count) }}
                                </td>
                                <td class="kitchen-sales-page__metric-cell">
                                    {{ formatNumber(row.qty) }}
                                </td>
                                <td v-if="canViewSalesMoney" class="kitchen-sales-page__metric-cell">
                                    {{ formatMoney(row.sum) }}
                                </td>
                                <td class="kitchen-sales-page__metric-cell">
                                    {{
                                        abcSettings.basis_metric === 'sum'
                                            ? formatMoney(row.basis_value)
                                            : formatNumber(row.basis_value)
                                    }}
                                </td>
                                <td class="kitchen-sales-page__metric-cell">
                                    {{ formatNumber(row.share_percent) }}
                                </td>
                                <td class="kitchen-sales-page__metric-cell">
                                    {{ formatNumber(row.cumulative_percent) }}
                                </td>
                                <td class="kitchen-sales-page__metric-cell">
                                    <strong>{{ row.abc_class }}</strong>
                                </td>
                            </tr>
                        </tbody>
                    </Table>

                    <Table
                        v-else-if="pivotData.hasColumnBreakdown"
                        class="kitchen-sales-page__report-table"
                    >
                        <thead>
                            <tr>
                                <th
                                    v-for="rowField in pivotData.rowFields"
                                    :key="`head-row-${rowField.key}`"
                                    rowspan="2"
                                >
                                    {{ rowField.label }}
                                </th>
                                <th
                                    v-for="column in pivotData.columns"
                                    :key="`head-column-${column.key}`"
                                    :colspan="pivotData.metricDefs.length"
                                >
                                    {{ column.label }}
                                </th>
                                <th
                                    :colspan="pivotData.metricDefs.length"
                                    class="kitchen-sales-page__total-head"
                                >
                                    Итого
                                </th>
                            </tr>
                            <tr>
                                <template
                                    v-for="column in pivotData.columns"
                                    :key="`metric-head-${column.key}`"
                                >
                                    <th
                                        v-for="metric in pivotData.metricDefs"
                                        :key="`metric-head-${column.key}-${metric.key}`"
                                    >
                                        {{ metric.label }}
                                    </th>
                                </template>
                                <th
                                    v-for="metric in pivotData.metricDefs"
                                    :key="`metric-total-head-${metric.key}`"
                                    class="kitchen-sales-page__total-head"
                                >
                                    {{ metric.label }}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="row in pivotData.rows" :key="row.key">
                                <td
                                    v-for="(value, index) in row.values"
                                    :key="`row-value-${row.key}-${index}`"
                                >
                                    {{ value }}
                                </td>
                                <template
                                    v-for="column in pivotData.columns"
                                    :key="`row-cell-${row.key}-${column.key}`"
                                >
                                    <td
                                        v-for="metric in pivotData.metricDefs"
                                        :key="`row-cell-${row.key}-${column.key}-${metric.key}`"
                                        class="kitchen-sales-page__metric-cell"
                                    >
                                        {{
                                            formatMetric(
                                                cellMetricValue(row, column.key, metric.key),
                                                metric.format,
                                            )
                                        }}
                                    </td>
                                </template>
                                <td
                                    v-for="metric in pivotData.metricDefs"
                                    :key="`row-total-${row.key}-${metric.key}`"
                                    class="kitchen-sales-page__metric-cell kitchen-sales-page__total-cell"
                                >
                                    {{ formatMetric(row.totals[metric.key] ?? 0, metric.format) }}
                                </td>
                            </tr>
                            <tr class="kitchen-sales-page__grand-total-row">
                                <td :colspan="Math.max(1, pivotData.rowFields.length)">
                                    Итого по отчету
                                </td>
                                <template
                                    v-for="column in pivotData.columns"
                                    :key="`grand-column-${column.key}`"
                                >
                                    <td
                                        v-for="metric in pivotData.metricDefs"
                                        :key="`grand-column-${column.key}-${metric.key}`"
                                        class="kitchen-sales-page__metric-cell kitchen-sales-page__total-cell"
                                    >
                                        {{
                                            formatMetric(
                                                columnMetricValue(column.key, metric.key),
                                                metric.format,
                                            )
                                        }}
                                    </td>
                                </template>
                                <td
                                    v-for="metric in pivotData.metricDefs"
                                    :key="`grand-total-${metric.key}`"
                                    class="kitchen-sales-page__metric-cell kitchen-sales-page__total-cell"
                                >
                                    {{
                                        formatMetric(
                                            pivotData.grandTotals[metric.key] ?? 0,
                                            metric.format,
                                        )
                                    }}
                                </td>
                            </tr>
                        </tbody>
                    </Table>

                    <Table v-else class="kitchen-sales-page__report-table">
                        <thead>
                            <tr>
                                <th
                                    v-for="rowField in pivotData.rowFields"
                                    :key="`flat-head-row-${rowField.key}`"
                                >
                                    {{ rowField.label }}
                                </th>
                                <th
                                    v-for="metric in pivotData.metricDefs"
                                    :key="`flat-head-metric-${metric.key}`"
                                >
                                    {{ metric.label }}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="row in pivotData.rows" :key="row.key">
                                <td
                                    v-for="(value, index) in row.values"
                                    :key="`flat-row-value-${row.key}-${index}`"
                                >
                                    {{ value }}
                                </td>
                                <td
                                    v-for="metric in pivotData.metricDefs"
                                    :key="`flat-row-metric-${row.key}-${metric.key}`"
                                    class="kitchen-sales-page__metric-cell"
                                >
                                    {{ formatMetric(row.totals[metric.key] ?? 0, metric.format) }}
                                </td>
                            </tr>
                            <tr class="kitchen-sales-page__grand-total-row">
                                <td :colspan="Math.max(1, pivotData.rowFields.length)">
                                    Итого по отчету
                                </td>
                                <td
                                    v-for="metric in pivotData.metricDefs"
                                    :key="`flat-grand-${metric.key}`"
                                    class="kitchen-sales-page__metric-cell kitchen-sales-page__total-cell"
                                >
                                    {{
                                        formatMetric(
                                            pivotData.grandTotals[metric.key] ?? 0,
                                            metric.format,
                                        )
                                    }}
                                </td>
                            </tr>
                        </tbody>
                    </Table>
                </div>
            </div>
        </section>
    </div>
</template>

<script setup>
    import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
    import {
        fetchKitchenRestaurants,
        fetchKitchenSalesItems,
        fetchKitchenWaiterSalesOptions,
    } from '@/api';
    import { useDebounce } from '@/composables/useDebounce';
    import { useToast } from 'vue-toastification';
    import { useUserStore } from '@/stores/user';
    import Input from '@/components/UI-components/Input.vue';
    import DateInput from '@/components/UI-components/DateInput.vue';
    import Button from '@/components/UI-components/Button.vue';
    import Table from '@/components/UI-components/Table.vue';
    import Select from '@/components/UI-components/Select.vue';
    import Checkbox from '@/components/UI-components/Checkbox.vue';
    import {
        SALES_REPORT_FIELD_CATALOG,
        SALES_REPORT_FIELD_SETTINGS_EVENT,
        SALES_REPORT_FIELD_SETTINGS_STORAGE_KEY,
        loadSalesReportFieldSettings,
        normalizeSalesReportFieldSettings,
    } from './salesReportFieldSettings';
    import { formatDateValue, formatNumberValue } from '@/utils/format';

    const REPORT_FETCH_LIMIT = 500;
    const REPORT_PAGE_RETRY_BASE_DELAY_MS = 1200;
    const REPORT_PAGE_RETRY_MAX_DELAY_MS = 15000;
    const REPORT_PAGE_MAX_RETRY_ATTEMPTS = 5;

    const REPORT_TYPE_OPTIONS = [
        { value: 'sales', label: 'Отчет о продажах' },
        { value: 'abc', label: 'ABC-анализ' },
    ];

    const WAITER_MODE_OPTIONS = [
        { value: 'order_close', label: 'Закрытым заказам' },
        { value: 'item_punch', label: 'Пробитым позициям' },
    ];

    const FILTER_FIELD_CATALOG = SALES_REPORT_FIELD_CATALOG.filters;
    const DIMENSION_CATALOG = SALES_REPORT_FIELD_CATALOG.dimensions;
    const METRIC_CATALOG = SALES_REPORT_FIELD_CATALOG.metrics;

    const ABC_GROUP_OPTIONS = [
        { value: 'dish_name', label: 'Позиция' },
        { value: 'dish_group', label: 'Группа меню' },
        { value: 'dish_category', label: 'Категория меню' },
        { value: 'restaurant_name', label: 'Ресторан' },
        { value: 'hall_name', label: 'Зал' },
        { value: 'payment_type', label: 'Тип оплаты' },
        { value: 'employee_name', label: 'Сотрудник' },
    ];

    const ABC_METRIC_OPTIONS = [
        { value: 'sum', label: 'По продажам (руб)' },
        { value: 'qty', label: 'По количеству' },
        { value: 'items_count', label: 'По числу позиций' },
    ];

    const dimensionByKey = new Map(DIMENSION_CATALOG.map((item) => [item.key, item]));

    const userStore = useUserStore();
    const toast = useToast();
    const canViewSalesReport = computed(() =>
        userStore.hasAnyPermission(
            'sales.report.view_qty',
            'sales.report.view_money',
            'iiko.view',
            'iiko.manage',
        ),
    );
    const canViewSalesMoney = computed(() =>
        userStore.hasAnyPermission('sales.report.view_money', 'iiko.view', 'iiko.manage'),
    );

    const isBuilderOpen = ref(false);
    const loadingOptions = ref(false);
    const loadingReport = ref(false);
    const reportBuilt = ref(false);
    const hasLoadedOptions = ref(false);
    let optionsLoadAbortController = null;
    let reportBuildAbortController = null;
    let optionsLoadRequestSeq = 0;
    let reportBuildRequestSeq = 0;

    const reportType = ref('sales');
    const restaurantId = ref('');
    const fromDate = ref(defaultFromDate());
    const toDate = ref(defaultToDate());
    const showDeleted = ref(false);
    const realMoneyOnly = ref(false);
    const waiterMode = ref('order_close');
    const waiterKey = ref('');
    const activeMetricKey = ref('sum');
    const fieldSettings = ref(loadSalesReportFieldSettings());

    const restaurants = ref([]);
    const reportRows = ref([]);
    const optionsPayload = ref({
        waiters: [],
        groups: [],
        categories: [],
        positions: [],
        payment_types: [],
        halls: [],
        departments: [],
        tables: [],
    });

    const constructorDraft = reactive({
        rowField: '',
        columnField: '',
    });

    const abcSettings = reactive({
        group_by: 'dish_name',
        basis_metric: 'sum',
        threshold_a: 80,
        threshold_b: 95,
    });

    const includeRules = ref([]);
    const excludeRules = ref([]);
    const activeRuleMode = ref('');
    const ruleDraft = reactive({
        field_key: '',
        value: '',
    });

    let filterRuleCounter = 1;

    const filterOptions = computed(() =>
        FILTER_FIELD_CATALOG.filter((item) => fieldSettings.value?.filters?.[item.value] !== false),
    );
    const dimensionOptions = computed(() =>
        DIMENSION_CATALOG.filter((item) => fieldSettings.value?.dimensions?.[item.key] !== false),
    );
    const metricOptions = computed(() =>
        METRIC_CATALOG.filter((item) => {
            if (fieldSettings.value?.metrics?.[item.key] === false) {
                return false;
            }
            if (canViewSalesMoney.value) {
                return true;
            }
            return item.key !== 'sum' && item.key !== 'discount_sum';
        }),
    );

    const reportTypeOptions = computed(() => REPORT_TYPE_OPTIONS);
    const waiterModeOptions = computed(() => WAITER_MODE_OPTIONS);
    const abcGroupOptions = computed(() => ABC_GROUP_OPTIONS);
    const abcMetricOptions = computed(() =>
        canViewSalesMoney.value
            ? ABC_METRIC_OPTIONS
            : ABC_METRIC_OPTIONS.filter((item) => item.value !== 'sum'),
    );
    const reportMetricOptions = computed(() =>
        metricOptions.value.map((metric) => ({
            value: metric.key,
            label: metric.label,
        })),
    );
    const reportTypeLabel = computed(
        () =>
            reportTypeOptions.value.find((item) => item.value === reportType.value)?.label ||
            'Отчет',
    );
    const selectedRestaurantLabel = computed(() => {
        if (!restaurantId.value) {
            return 'Все рестораны';
        }
        const selectedRestaurant = (restaurants.value || []).find(
            (restaurant) => String(restaurant.id) === String(restaurantId.value),
        );
        return selectedRestaurant?.name || `Ресторан #${restaurantId.value}`;
    });
    const periodLabel = computed(
        () => `${formatCompactDate(fromDate.value)} - ${formatCompactDate(toDate.value)}`,
    );
    const activeFiltersCount = computed(() => {
        let total = includeRules.value.length + excludeRules.value.length;
        if (restaurantId.value) {
            total += 1;
        }
        if (waiterKey.value) {
            total += 1;
        }
        if (realMoneyOnly.value) {
            total += 1;
        }
        if (showDeleted.value) {
            total += 1;
        }
        return total;
    });

    const restaurantOptions = computed(() => [
        { value: '', label: 'Все рестораны' },
        ...(restaurants.value || []).map((restaurant) => ({
            value: String(restaurant.id),
            label: restaurant.name,
        })),
    ]);

    const waiterOptions = computed(() => {
        const options = [{ value: '', label: 'Все сотрудники' }];

        for (const waiter of optionsPayload.value.waiters || []) {
            const option = waiterOptionFromPayload(waiter);
            if (option) {
                options.push(option);
            }
        }

        return options;
    });

    const groupOptions = computed(() => toTextOptions(optionsPayload.value.groups));
    const categoryOptions = computed(() => toTextOptions(optionsPayload.value.categories));
    const positionOptions = computed(() => toTextOptions(optionsPayload.value.positions));
    const paymentTypeOptions = computed(() => toTextOptions(optionsPayload.value.payment_types));
    const hallOptions = computed(() => toTextOptions(optionsPayload.value.halls));
    const departmentOptions = computed(() => toTextOptions(optionsPayload.value.departments));
    const tableOptions = computed(() => toTextOptions(optionsPayload.value.tables));

    const waiterFilterOptions = computed(() => {
        const values = [];
        for (const waiter of optionsPayload.value.waiters || []) {
            const name = String(waiter?.name || '').trim();
            if (name) {
                values.push(name);
            }
        }
        return toTextOptions(values);
    });

    const rowFieldSelectorOptions = computed(() =>
        dimensionOptions.value.map((item) => ({ value: item.key, label: item.label })),
    );

    const columnFieldSelectorOptions = computed(() =>
        dimensionOptions.value.map((item) => ({ value: item.key, label: item.label })),
    );

    const selectedRowFieldObjects = computed(() => {
        const selected = dimensionByKey.get(constructorDraft.rowField);
        return selected ? [selected] : [];
    });

    const selectedColumnFieldObjects = computed(() => {
        const selected = dimensionByKey.get(constructorDraft.columnField);
        return selected ? [selected] : [];
    });

    const activeMetricDef = computed(() => {
        const options = metricOptions.value;
        if (!options.length) {
            return null;
        }
        return options.find((metric) => metric.key === activeMetricKey.value) || options[0];
    });

    const selectedMetricDefs = computed(() =>
        activeMetricDef.value ? [activeMetricDef.value] : [],
    );

    const filterFieldOptions = computed(() => filterOptions.value);
    const filterFieldLabelByKey = computed(
        () => new Map(filterOptions.value.map((item) => [String(item.value), String(item.label)])),
    );

    const filterValueOptionsByField = computed(() => {
        const namedRestaurants = (restaurants.value || [])
            .map((restaurant) => String(restaurant?.name || '').trim())
            .filter(Boolean);

        return {
            dish_group: groupOptions.value,
            dish_category: categoryOptions.value,
            dish_name: positionOptions.value,
            payment_type: paymentTypeOptions.value,
            waiter_name: waiterFilterOptions.value,
            hall_name: hallOptions.value,
            department: departmentOptions.value,
            table: tableOptions.value,
            restaurant_name: toTextOptions(namedRestaurants),
        };
    });

    const reportStats = computed(() => {
        const totals = createMetricTotals();
        const orders = new Set();

        for (const row of reportRows.value) {
            totals.items_count += 1;
            totals.qty += safeNumber(row?.qty);
            totals.kitchen_load_qty += safeNumber(row?.kitchen_load_qty);
            totals.hall_load_qty += safeNumber(row?.hall_load_qty);
            totals.sum += safeNumber(row?.sum);
            totals.discount_sum += safeNumber(row?.discount_sum);
            if (row?.order_id) {
                orders.add(String(row.order_id));
            }
        }

        return {
            ...totals,
            orders_count: orders.size,
        };
    });

    const abcMetricLabel = computed(() => {
        const metric = ABC_METRIC_OPTIONS.find((item) => item.value === abcSettings.basis_metric);
        return metric?.label || 'Показатель';
    });

    const abcGroupLabel = computed(() => {
        const group = ABC_GROUP_OPTIONS.find((item) => item.value === abcSettings.group_by);
        return group?.label || 'Группа';
    });

    const abcReportRows = computed(() => {
        const grouped = new Map();
        const metricKey = abcSettings.basis_metric;
        const thresholdA = safeNumber(abcSettings.threshold_a);
        const thresholdB = safeNumber(abcSettings.threshold_b);

        for (const row of reportRows.value || []) {
            const groupValue = resolveDimensionLabel(row, abcSettings.group_by);
            const key = String(groupValue || 'Не указано');
            if (!grouped.has(key)) {
                grouped.set(key, {
                    group_value: key,
                    items_count: 0,
                    qty: 0,
                    sum: 0,
                });
            }
            const bucket = grouped.get(key);
            bucket.items_count += 1;
            bucket.qty += safeNumber(row?.qty);
            bucket.sum += safeNumber(row?.sum);
        }

        const rows = Array.from(grouped.values())
            .map((item) => ({
                ...item,
                basis_value: safeNumber(item?.[metricKey]),
            }))
            .sort((a, b) => b.basis_value - a.basis_value);

        const totalBasis = rows.reduce((acc, item) => acc + safeNumber(item.basis_value), 0);
        let cumulative = 0;

        return rows.map((item) => {
            const share = totalBasis > 0 ? (safeNumber(item.basis_value) / totalBasis) * 100 : 0;
            cumulative += share;
            let abcClass = 'C';
            if (cumulative <= thresholdA) {
                abcClass = 'A';
            } else if (cumulative <= thresholdB) {
                abcClass = 'B';
            }
            return {
                ...item,
                share_percent: share,
                cumulative_percent: cumulative,
                abc_class: abcClass,
            };
        });
    });

    const pivotData = computed(() => {
        const selectedRowDefs = selectedRowFieldObjects.value;
        const rowFields = selectedRowDefs.length
            ? selectedRowDefs
            : [{ key: '__total__', label: 'Срез' }];
        const metricDefs = selectedMetricDefs.value;
        const columnFields = selectedColumnFieldObjects.value;
        const hasColumnBreakdown = columnFields.length > 0;
        const allColumnKey = '__all__';

        if (!metricDefs.length) {
            return {
                rowFields,
                metricDefs,
                columns: [],
                rows: [],
                columnTotals: new Map(),
                grandTotals: createMetricTotals(),
                hasColumnBreakdown,
            };
        }

        const columnsMap = new Map();
        const rowsMap = new Map();
        const columnTotalsMap = new Map();
        const grandTotals = createMetricTotals();

        if (!hasColumnBreakdown) {
            columnsMap.set(allColumnKey, { key: allColumnKey, label: 'Все данные' });
            columnTotalsMap.set(allColumnKey, createMetricTotals());
        }

        for (const row of reportRows.value) {
            const rowValues = selectedRowDefs.length
                ? selectedRowDefs.map((field) => resolveDimensionLabel(row, field.key))
                : ['Все данные'];
            const rowKey = selectedRowDefs.length ? rowValues.join('\u0001') : '__all_rows__';

            const columnValues = hasColumnBreakdown
                ? columnFields.map((field) => resolveDimensionLabel(row, field.key))
                : [];
            const columnKey = hasColumnBreakdown ? columnValues.join('\u0001') : allColumnKey;

            if (hasColumnBreakdown && !columnsMap.has(columnKey)) {
                columnsMap.set(columnKey, {
                    key: columnKey,
                    label: columnValues.join(' / '),
                });
                columnTotalsMap.set(columnKey, createMetricTotals());
            }

            let rowBucket = rowsMap.get(rowKey);
            if (!rowBucket) {
                rowBucket = {
                    key: rowKey,
                    values: rowValues,
                    cells: new Map(),
                    totals: createMetricTotals(),
                };
                rowsMap.set(rowKey, rowBucket);
            }

            let cellBucket = rowBucket.cells.get(columnKey);
            if (!cellBucket) {
                cellBucket = createMetricTotals();
                rowBucket.cells.set(columnKey, cellBucket);
            }

            accumulateMetrics(cellBucket, row);
            accumulateMetrics(rowBucket.totals, row);

            const columnTotals = columnTotalsMap.get(columnKey) || createMetricTotals();
            accumulateMetrics(columnTotals, row);
            columnTotalsMap.set(columnKey, columnTotals);

            accumulateMetrics(grandTotals, row);
        }

        const columns = Array.from(columnsMap.values()).sort((a, b) =>
            String(a.label || '').localeCompare(String(b.label || ''), 'ru', {
                sensitivity: 'base',
            }),
        );

        const rows = Array.from(rowsMap.values());
        if (selectedRowDefs.length) {
            rows.sort(comparePivotRows);
        }

        return {
            rowFields,
            metricDefs,
            columns,
            rows,
            columnTotals: columnTotalsMap,
            grandTotals,
            hasColumnBreakdown,
        };
    });

    function defaultToDate() {
        const date = new Date();
        return date.toISOString().slice(0, 10);
    }

    function defaultFromDate() {
        const date = new Date();
        date.setDate(date.getDate() - 6);
        return date.toISOString().slice(0, 10);
    }

    function safeNumber(value) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function normalizeText(value) {
        return String(value || '')
            .trim()
            .toLowerCase();
    }

    function toTextOptions(values) {
        return Array.from(
            new Set((values || []).map((value) => String(value || '').trim()).filter(Boolean)),
        )
            .sort((a, b) => a.localeCompare(b, 'ru', { sensitivity: 'base' }))
            .map((value) => ({ value, label: value }));
    }

    function waiterOptionFromPayload(waiter) {
        if (!waiter) {
            return null;
        }

        const name = String(waiter.name || '').trim() || 'Сотрудник';
        const hasMatch = waiter.user_id !== null && waiter.user_id !== undefined;
        const label = hasMatch ? name : `${name} (без сопоставления)`;
        if (waiter.user_id !== null && waiter.user_id !== undefined) {
            return {
                value: `user:${waiter.user_id}`,
                label,
                warning: false,
            };
        }
        if (waiter.iiko_id) {
            return {
                value: `iiko:${waiter.iiko_id}`,
                label,
                warning: !hasMatch,
            };
        }
        if (waiter.iiko_code) {
            return {
                value: `code:${waiter.iiko_code}`,
                label,
                warning: !hasMatch,
            };
        }
        return null;
    }

    function startRuleComposer(mode) {
        const normalizedMode = mode === 'exclude' ? 'exclude' : 'include';
        if (activeRuleMode.value === normalizedMode) {
            activeRuleMode.value = '';
            ruleDraft.field_key = '';
            ruleDraft.value = '';
            return;
        }
        activeRuleMode.value = normalizedMode;
        ruleDraft.field_key = '';
        ruleDraft.value = '';
    }

    function getFilterValueOptions(fieldKey) {
        const key = String(fieldKey || '').trim();
        return filterValueOptionsByField.value[key] || [];
    }

    function formatRuleLabel(rule) {
        const key = String(rule?.field_key || '').trim();
        const fieldLabel = filterFieldLabelByKey.value.get(key) || key || 'Параметр';
        const valueLabel = String(rule?.value || '').trim() || '-';
        return `${fieldLabel}: ${valueLabel}`;
    }

    function onDraftFieldChange() {
        ruleDraft.value = '';
    }

    function addDraftRule() {
        const mode = activeRuleMode.value === 'exclude' ? 'exclude' : 'include';
        const rules = mode === 'include' ? includeRules.value : excludeRules.value;
        const fieldKey = String(ruleDraft.field_key || '').trim();
        const value = String(ruleDraft.value || '').trim();
        if (!fieldKey || !value) {
            return;
        }

        const normalizedValue = normalizeText(value);
        const hasDuplicate = rules.some(
            (rule) =>
                String(rule?.field_key || '') === fieldKey &&
                normalizeText(rule?.value) === normalizedValue,
        );
        if (hasDuplicate) {
            return;
        }

        rules.push({
            id: `${mode}-${filterRuleCounter}`,
            field_key: fieldKey,
            value,
        });
        filterRuleCounter += 1;
        activeRuleMode.value = '';
        ruleDraft.field_key = '';
        ruleDraft.value = '';
    }

    function removeFilterRule(mode, ruleId) {
        const rules = mode === 'include' ? includeRules.value : excludeRules.value;
        const nextRules = rules.filter((rule) => rule.id !== ruleId);
        rules.splice(0, rules.length, ...nextRules);
    }

    function syncFieldSettingsState(rawSettings) {
        fieldSettings.value = normalizeSalesReportFieldSettings(rawSettings);

        const enabledRowKeys = new Set(dimensionOptions.value.map((item) => item.key));
        if (constructorDraft.rowField && !enabledRowKeys.has(constructorDraft.rowField)) {
            constructorDraft.rowField = rowFieldSelectorOptions.value[0]?.value || '';
        }

        const enabledColumnKeys = new Set(dimensionOptions.value.map((item) => item.key));
        if (constructorDraft.columnField && !enabledColumnKeys.has(constructorDraft.columnField)) {
            constructorDraft.columnField = columnFieldSelectorOptions.value[0]?.value || '';
        }

        const enabledFilterKeys = new Set(filterOptions.value.map((item) => item.value));
        includeRules.value = includeRules.value.filter((rule) =>
            enabledFilterKeys.has(rule.field_key),
        );
        excludeRules.value = excludeRules.value.filter((rule) =>
            enabledFilterKeys.has(rule.field_key),
        );
        if (!filterOptions.value.length) {
            activeRuleMode.value = '';
            ruleDraft.field_key = '';
            ruleDraft.value = '';
        } else if (ruleDraft.field_key && !enabledFilterKeys.has(ruleDraft.field_key)) {
            ruleDraft.field_key = '';
            ruleDraft.value = '';
        }

        if (!activeMetricDef.value) {
            activeMetricKey.value = '';
            return;
        }
        if (!metricOptions.value.some((item) => item.key === activeMetricKey.value)) {
            activeMetricKey.value = metricOptions.value[0].key;
        }
    }

    function ensureValidDates() {
        if (!fromDate.value || !toDate.value) {
            toast.error('Укажите обе даты для отчета');
            return false;
        }
        if (fromDate.value > toDate.value) {
            toast.error('Дата "С" не может быть позже даты "По"');
            return false;
        }
        return true;
    }

    function appendListParam(params, key, values) {
        for (const value of values || []) {
            params.append(key, String(value));
        }
    }

    function appendWaiterParam(params) {
        const value = String(waiterKey.value || '').trim();
        if (!value) {
            return;
        }
        if (value.startsWith('user:')) {
            const parsed = Number(value.slice(5));
            if (Number.isFinite(parsed)) {
                params.append('waiter_user_id', String(Math.trunc(parsed)));
            }
            return;
        }
        if (value.startsWith('iiko:')) {
            const iikoId = value.slice(5).trim();
            if (iikoId) {
                params.append('waiter_iiko_id', iikoId);
            }
            return;
        }
        if (value.startsWith('code:')) {
            const iikoCode = value.slice(5).trim();
            if (iikoCode) {
                params.append('waiter_iiko_code', iikoCode);
            }
        }
    }

    function buildCommonParams() {
        const params = new URLSearchParams();
        params.append('from_date', fromDate.value);
        params.append('to_date', toDate.value);
        params.append('deleted_mode', showDeleted.value ? 'all' : 'without_deleted');
        params.append('waiter_mode', waiterMode.value);

        if (restaurantId.value) {
            params.append('restaurant_id', String(restaurantId.value));
        }

        appendWaiterParam(params);
        return params;
    }

    function buildRuleValuesMap(rules) {
        const map = new Map();
        for (const rule of rules || []) {
            const fieldKey = String(rule?.field_key || '').trim();
            const normalizedValue = normalizeText(rule?.value);
            if (!fieldKey || !normalizedValue) {
                continue;
            }
            if (!map.has(fieldKey)) {
                map.set(fieldKey, new Set());
            }
            map.get(fieldKey).add(normalizedValue);
        }
        return map;
    }

    function appendIncludeRulesToParams(params) {
        const includeMap = buildRuleValuesMap(includeRules.value);
        const appendField = (fieldKey, paramKey) => {
            const values = Array.from(includeMap.get(fieldKey) || []);
            appendListParam(params, paramKey, values);
        };

        appendField('dish_group', 'include_groups');
        appendField('dish_category', 'include_categories');
        appendField('dish_name', 'include_positions');
        appendField('payment_type', 'include_payment_types');
        appendField('hall_name', 'include_halls');
        appendField('department', 'include_departments');
        appendField('table', 'include_tables');
    }

    function buildItemsParams() {
        const params = buildCommonParams();

        appendIncludeRulesToParams(params);

        return params;
    }

    function normalizeListResponse(payload) {
        if (Array.isArray(payload)) {
            return {
                items: payload,
                total: payload.length,
            };
        }

        return {
            items: Array.isArray(payload?.items) ? payload.items : [],
            total: safeNumber(payload?.total),
        };
    }

    function createCanceledError() {
        const error = new Error('Request canceled');
        error.name = 'CanceledError';
        error.code = 'ERR_CANCELED';
        return error;
    }

    function isRequestCanceled(error) {
        return (
            error?.code === 'ERR_CANCELED' ||
            error?.name === 'CanceledError' ||
            error?.message === 'canceled' ||
            error?.message === 'Request canceled'
        );
    }

    function throwIfAborted(signal) {
        if (signal?.aborted) {
            throw createCanceledError();
        }
    }

    function sleep(ms, signal) {
        return new Promise((resolve, reject) => {
            if (signal?.aborted) {
                reject(createCanceledError());
                return;
            }
            const timeoutId = window.setTimeout(() => {
                if (signal) {
                    signal.removeEventListener('abort', onAbort);
                }
                resolve();
            }, ms);

            function onAbort() {
                window.clearTimeout(timeoutId);
                signal?.removeEventListener('abort', onAbort);
                reject(createCanceledError());
            }

            if (signal) {
                signal.addEventListener('abort', onAbort, { once: true });
            }
        });
    }

    function isRetriableFetchError(error) {
        const status = Number(error?.response?.status || 0);
        if ([408, 425, 429, 500, 502, 503, 504].includes(status)) {
            return true;
        }
        return !status;
    }

    async function fetchAllItems(baseParams, signal) {
        const rows = [];
        let offset = 0;

        while (true) {
            throwIfAborted(signal);
            const params = new URLSearchParams(baseParams);
            params.set('limit', String(REPORT_FETCH_LIMIT));
            params.set('offset', String(offset));

            let payload = null;
            let attempt = 0;
            while (true) {
                try {
                    payload = normalizeListResponse(await fetchKitchenSalesItems(params, {
                        signal,
                    }));
                    break;
                } catch (error) {
                    if (isRequestCanceled(error) || signal?.aborted) {
                        throw error;
                    }
                    if (!isRetriableFetchError(error) || attempt >= REPORT_PAGE_MAX_RETRY_ATTEMPTS) {
                        throw error;
                    }
                    const waitMs = Math.min(
                        REPORT_PAGE_RETRY_BASE_DELAY_MS * Math.pow(2, attempt),
                        REPORT_PAGE_RETRY_MAX_DELAY_MS,
                    );
                    await sleep(waitMs, signal);
                    attempt += 1;
                }
            }

            rows.push(...(payload.items || []));

            if (!payload.items.length) {
                break;
            }

            if (payload.items.length < REPORT_FETCH_LIMIT) {
                break;
            }

            offset += REPORT_FETCH_LIMIT;
        }

        return rows;
    }

    function resolvePaymentType(row) {
        return String(
            row?.payment_method_name ||
                row?.non_cash_payment_type_name ||
                row?.payment_method_guid ||
                row?.non_cash_payment_type_id ||
                '',
        ).trim();
    }

    function resolveWaiterForFilter(row) {
        return String(
            row?.dish_waiter_user_name ||
                row?.dish_waiter_name_iiko ||
                row?.order_waiter_user_name ||
                row?.order_waiter_name_iiko ||
                row?.auth_user_name ||
                row?.auth_user_name_iiko ||
                row?.dish_waiter_iiko_id ||
                row?.order_waiter_iiko_id ||
                '',
        ).trim();
    }
    function resolveFilterFieldValue(row, fieldKey) {
        switch (fieldKey) {
            case 'dish_group':
                return row?.dish_group;
            case 'dish_category':
                return row?.dish_category;
            case 'dish_name':
                return row?.dish_name;
            case 'payment_type':
                return resolvePaymentType(row);
            case 'waiter_name':
                return resolveWaiterForFilter(row);
            case 'restaurant_name':
                return row?.restaurant_name || (row?.restaurant_id ? `#${row.restaurant_id}` : '');
            case 'source_restaurant_name':
                return (
                    row?.source_restaurant_name ||
                    (row?.source_restaurant_id ? `#${row.source_restaurant_id}` : '')
                );
            case 'hall_name':
                return row?.hall_name;
            case 'department':
                return row?.department;
            case 'table':
                return row?.table_num;
            default:
                return '';
        }
    }

    function isRealMoneyRow(row) {
        const paymentCategory = String(row?.payment_method_category || '')
            .trim()
            .toLowerCase();
        const nonCashCategory = String(row?.non_cash_payment_type_category || '')
            .trim()
            .toLowerCase();
        const categories = [paymentCategory, nonCashCategory].filter(Boolean);

        if (!categories.length) {
            return true;
        }
        return categories.includes('real_money');
    }

    function applyClientFilters(rows) {
        const includeMap = buildRuleValuesMap(includeRules.value);
        const excludeMap = buildRuleValuesMap(excludeRules.value);

        return (rows || []).filter((row) => {
            if (realMoneyOnly.value && !isRealMoneyRow(row)) {
                return false;
            }

            for (const [fieldKey, includeValues] of includeMap.entries()) {
                const rowValue = normalizeText(resolveFilterFieldValue(row, fieldKey));
                if (!includeValues.has(rowValue)) {
                    return false;
                }
            }

            for (const [fieldKey, excludeValues] of excludeMap.entries()) {
                const rowValue = normalizeText(resolveFilterFieldValue(row, fieldKey));
                if (excludeValues.has(rowValue)) {
                    return false;
                }
            }

            return true;
        });
    }

    async function loadRestaurants() {
        const data = await fetchKitchenRestaurants();
        restaurants.value = Array.isArray(data) ? data : [];
    }

    async function loadOptions() {
        if (!canViewSalesReport.value) {
            return;
        }
        if (!ensureValidDates()) {
            return;
        }

        if (optionsLoadAbortController) {
            optionsLoadAbortController.abort();
            optionsLoadAbortController = null;
        }
        const abortController = new AbortController();
        optionsLoadAbortController = abortController;
        const requestSeq = ++optionsLoadRequestSeq;
        loadingOptions.value = true;
        try {
            const payload = (await fetchKitchenWaiterSalesOptions(buildCommonParams(), {
                signal: abortController.signal,
            })) || {};
            if (requestSeq !== optionsLoadRequestSeq || abortController.signal.aborted) {
                return;
            }
            optionsPayload.value = {
                waiters: Array.isArray(payload.waiters) ? payload.waiters : [],
                groups: Array.isArray(payload.groups) ? payload.groups : [],
                categories: Array.isArray(payload.categories) ? payload.categories : [],
                positions: Array.isArray(payload.positions) ? payload.positions : [],
                payment_types: Array.isArray(payload.payment_types) ? payload.payment_types : [],
                halls: Array.isArray(payload.halls) ? payload.halls : [],
                departments: Array.isArray(payload.departments) ? payload.departments : [],
                tables: Array.isArray(payload.tables) ? payload.tables : [],
            };
            hasLoadedOptions.value = true;

            if (
                waiterKey.value &&
                !waiterOptions.value.some((option) => option.value === waiterKey.value)
            ) {
                waiterKey.value = '';
            }
        } catch (error) {
            if (isRequestCanceled(error) || requestSeq !== optionsLoadRequestSeq) {
                return;
            }
            toast.error(
                `Ошибка загрузки списков: ${error.response?.data?.detail || error.message}`,
            );
        } finally {
            if (requestSeq === optionsLoadRequestSeq) {
                loadingOptions.value = false;
            }
            if (optionsLoadAbortController === abortController) {
                optionsLoadAbortController = null;
            }
        }
    }

    async function buildReport() {
        if (!canViewSalesReport.value) {
            toast.error('Недостаточно прав для построения отчета');
            return;
        }
        if (!ensureValidDates()) {
            return;
        }

        if (reportType.value === 'sales' && !activeMetricDef.value) {
            toast.error('Включите хотя бы один показатель в настройках полей отчета');
            return;
        }

        if (reportType.value === 'abc') {
            const thresholdA = safeNumber(abcSettings.threshold_a);
            const thresholdB = safeNumber(abcSettings.threshold_b);
            if (
                thresholdA <= 0 ||
                thresholdA >= 100 ||
                thresholdB <= 0 ||
                thresholdB > 100 ||
                thresholdA >= thresholdB
            ) {
                toast.error('Проверьте границы ABC: A и B должны быть от 0 до 100, при этом A < B');
                return;
            }
        }

        if (reportBuildAbortController) {
            reportBuildAbortController.abort();
            reportBuildAbortController = null;
        }
        const abortController = new AbortController();
        reportBuildAbortController = abortController;
        const requestSeq = ++reportBuildRequestSeq;
        loadingReport.value = true;
        try {
            const params = buildItemsParams();
            const rows = await fetchAllItems(params, abortController.signal);
            if (requestSeq !== reportBuildRequestSeq || abortController.signal.aborted) {
                return;
            }
            reportRows.value = applyClientFilters(rows);
            reportBuilt.value = true;
            isBuilderOpen.value = false;
        } catch (error) {
            if (isRequestCanceled(error) || requestSeq !== reportBuildRequestSeq) {
                return;
            }
            toast.error(
                `Ошибка построения отчета: ${error.response?.data?.detail || error.message}`,
            );
        } finally {
            if (requestSeq === reportBuildRequestSeq) {
                loadingReport.value = false;
            }
            if (reportBuildAbortController === abortController) {
                reportBuildAbortController = null;
            }
        }
    }

    async function toggleBuilder() {
        if (!canViewSalesReport.value) {
            return;
        }
        isBuilderOpen.value = !isBuilderOpen.value;
        if (isBuilderOpen.value && !hasLoadedOptions.value) {
            await loadOptions();
        }
    }

    function resolveDimensionLabel(row, key) {
        switch (key) {
            case 'restaurant_name':
                return String(
                    row?.restaurant_name ||
                        (row?.restaurant_id ? `#${row.restaurant_id}` : 'Не указано'),
                );
            case 'source_restaurant_name':
                return String(
                    row?.source_restaurant_name ||
                        (row?.source_restaurant_id ? `#${row.source_restaurant_id}` : 'Не указано'),
                );
            case 'open_date':
                return formatDate(row?.open_date);
            case 'department':
                return String(row?.department || 'Не указано');
            case 'hall_name':
                return String(row?.hall_name || 'Не указано');
            case 'zone_name':
                return String(row?.zone_name || 'Не указано');
            case 'table_num':
                return String(row?.table_num || 'Не указано');
            case 'dish_group':
                return String(row?.dish_group || 'Не указано');
            case 'dish_category':
                return String(row?.dish_category || 'Не указано');
            case 'dish_name':
                return String(row?.dish_name || 'Не указано');
            case 'dish_code':
                return String(row?.dish_code || 'Не указано');
            case 'payment_type':
                return String(resolvePaymentType(row) || 'Не указано');
            case 'employee_name':
                return String(resolveWaiterForFilter(row) || 'Не указано');
            case 'auth_user_name':
                return String(
                    row?.auth_user_name ||
                        row?.auth_user_name_iiko ||
                        row?.auth_user_iiko_id ||
                        'Не указано',
                );
            case 'is_deleted':
                return row?.is_deleted ? 'Да' : 'Нет';
            default:
                return 'Не указано';
        }
    }
    function formatDate(value) {
        return formatDateValue(value, {
            emptyValue: 'Не указано',
            invalidValue: String(value),
            locale: 'ru-RU',
        });
    }

    function formatCompactDate(value) {
        const text = String(value || '').trim();
        if (!text) {
            return '-';
        }

        const simpleDateMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
        if (simpleDateMatch) {
            const [, year, month, day] = simpleDateMatch;
            return `${day}.${month}.${year.slice(-2)}`;
        }

        const parsed = new Date(text);
        if (Number.isNaN(parsed.getTime())) {
            return text;
        }
        return parsed.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: '2-digit',
        });
    }

    function getMetricValue(row, metricKey) {
        switch (metricKey) {
            case 'items_count':
                return 1;
            case 'qty':
                return safeNumber(row?.qty);
            case 'kitchen_load_qty':
                return safeNumber(row?.kitchen_load_qty);
            case 'hall_load_qty':
                return safeNumber(row?.hall_load_qty);
            case 'sum':
                return safeNumber(row?.sum);
            case 'discount_sum':
                return safeNumber(row?.discount_sum);
            default:
                return 0;
        }
    }

    function createMetricTotals() {
        return {
            items_count: 0,
            qty: 0,
            kitchen_load_qty: 0,
            hall_load_qty: 0,
            sum: 0,
            discount_sum: 0,
        };
    }

    function accumulateMetrics(target, row) {
        for (const metric of METRIC_CATALOG) {
            target[metric.key] = safeNumber(target[metric.key]) + getMetricValue(row, metric.key);
        }
    }

    function comparePivotRows(a, b) {
        const maxLength = Math.max(a.values.length, b.values.length);
        for (let index = 0; index < maxLength; index += 1) {
            const left = String(a.values[index] || '');
            const right = String(b.values[index] || '');
            const diff = left.localeCompare(right, 'ru', { sensitivity: 'base', numeric: true });
            if (diff !== 0) {
                return diff;
            }
        }
        return 0;
    }

    function cellMetricValue(row, columnKey, metricKey) {
        return safeNumber(row?.cells?.get(columnKey)?.[metricKey]);
    }

    function columnMetricValue(columnKey, metricKey) {
        return safeNumber(pivotData.value.columnTotals.get(columnKey)?.[metricKey]);
    }

    function formatNumber(value) {
        const number = Number(value);
        return formatNumberValue(number, {
            emptyValue: '-',
            invalidValue: '-',
            locale: 'ru-RU',
            minimumFractionDigits: Number.isInteger(number) ? 0 : 2,
            maximumFractionDigits: 2,
        });
    }

    function formatMoney(value) {
        return formatNumberValue(value, {
            emptyValue: '-',
            invalidValue: '-',
            locale: 'ru-RU',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    function formatMetric(value, format) {
        if (format === 'money') {
            return formatMoney(value);
        }
        return formatNumber(value);
    }

    function handleFieldSettingsStorage(event) {
        if (event?.key !== SALES_REPORT_FIELD_SETTINGS_STORAGE_KEY) {
            return;
        }
        syncFieldSettingsState(loadSalesReportFieldSettings());
    }

    function handleFieldSettingsUpdated(event) {
        syncFieldSettingsState(event?.detail || loadSalesReportFieldSettings());
    }

    const debouncedLoadOptions = useDebounce(() => {
        void loadOptions();
    }, 180);

    onMounted(async () => {
        syncFieldSettingsState(loadSalesReportFieldSettings());
        window.addEventListener('storage', handleFieldSettingsStorage);
        window.addEventListener(SALES_REPORT_FIELD_SETTINGS_EVENT, handleFieldSettingsUpdated);
        if (!canViewSalesReport.value) {
            return;
        }
        try {
            await loadRestaurants();
        } catch (error) {
            toast.error(
                `Ошибка загрузки ресторанов: ${error.response?.data?.detail || error.message}`,
            );
        }
    });

    onBeforeUnmount(() => {
        debouncedLoadOptions.cancel?.();
        if (optionsLoadAbortController) {
            optionsLoadAbortController.abort();
            optionsLoadAbortController = null;
        }
        if (reportBuildAbortController) {
            reportBuildAbortController.abort();
            reportBuildAbortController = null;
        }
        window.removeEventListener('storage', handleFieldSettingsStorage);
        window.removeEventListener(SALES_REPORT_FIELD_SETTINGS_EVENT, handleFieldSettingsUpdated);
    });

    watch(reportType, () => {
        reportBuilt.value = false;
        activeMetricKey.value = metricOptions.value[0]?.key || '';
        if (!canViewSalesMoney.value && abcSettings.basis_metric === 'sum') {
            abcSettings.basis_metric = 'qty';
        }
    });

    watch(canViewSalesMoney, (allowed) => {
        if (allowed) {
            return;
        }
        if (activeMetricKey.value === 'sum' || activeMetricKey.value === 'discount_sum') {
            activeMetricKey.value = metricOptions.value[0]?.key || '';
        }
        if (abcSettings.basis_metric === 'sum') {
            abcSettings.basis_metric = 'qty';
        }
    });

    watch([restaurantId, fromDate, toDate, waiterMode, showDeleted], () => {
        hasLoadedOptions.value = false;
        if (isBuilderOpen.value) {
            debouncedLoadOptions();
        }
    });
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kitchen-sales-report' as *;
</style>
