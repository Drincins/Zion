<template>
    <div class="advance-page">
        <header class="advance-page__header">
            <div class="advance-page__heading">
                <p class="advance-page__eyebrow">Бухгалтерия</p>
                <h1 class="advance-page__title">Ведомости</h1>
                <div class="advance-tabs">
                    <button
                        type="button"
                        class="advance-tabs__button"
                        :class="{ 'is-active': activeTab === 'draft' }"
                        @click="activeTab = 'draft'"
                    >
                        Черновик
                    </button>
                    <button
                        type="button"
                        class="advance-tabs__button"
                        :class="{ 'is-active': activeTab === 'statement' }"
                        @click="activeTab = 'statement'"
                    >
                        Ведомость
                    </button>
                </div>
            </div>
        </header>

        <section class="advance-panel">
            <div class="advance-panel__header">
                <div>
                    <h2 class="advance-panel__title">Фильтры</h2>
                    <p class="advance-panel__subtitle">Выберите ресторан и месяц для списка.</p>
                </div>
            </div>
            <div class="advance-panel__grid">
                <Select
                    v-model="listFilters.restaurantId"
                    label="Ресторан"
                    :options="restaurantFilterOptions"
                    placeholder="Все рестораны"
                />
                <div class="advance-panel__field">
                    <label class="advance-panel__label" for="filter-month">Месяц</label>
                    <DateInput
                        id="filter-month"
                        v-model="listFilters.month"
                        type="month"
                        placeholder="ММ.ГГГГ"
                    />
                </div>
                <div class="advance-panel__field">
                    <Select
                        v-model="sortBy"
                        label="Сортировка"
                        :options="sortOptions"
                        placeholder="Сортировка"
                    />
                </div>
                <div class="advance-panel__field advance-panel__field--align">
                    <Button color="outline" size="sm" @click="toggleSortDirection">
                        {{ sortDirectionLabel }}
                    </Button>
                </div>
            </div>
        </section>

        <section class="advance-panel">
            <div class="advance-panel__header">
                <div>
                    <h2 class="advance-panel__title">{{ activeTabLabel }}</h2>
                    <p class="advance-panel__subtitle">Найдено: {{ visibleCards.length }}</p>
                </div>
                <div
                    v-if="activeTab === 'statement' && canDownload && hasConsolidatedCandidates"
                    class="advance-panel__header-actions"
                >
                    <Button color="success" size="sm" @click="openConsolidatedModal">Общая ведомость</Button>
                </div>
            </div>

            <div v-if="visibleCards.length" class="advance-list">
                <template v-for="item in visibleCards" :key="`${item.kind}-${item.id}`">
                    <button
                        v-if="item.kind === 'consolidated'"
                        type="button"
                        class="advance-card advance-card--consolidated"
                        @click="openConsolidatedStatementModal(item.id)"
                    >
                        <div class="advance-card__top">
                            <span class="advance-card__id">Общая № {{ item.id }}</span>
                            <span class="advance-card__status advance-card__status--consolidated">
                                Сводная
                            </span>
                        </div>
                        <div class="advance-card__title">
                            {{ item.title || 'Общая ведомость' }}
                        </div>
                        <div class="advance-card__range">
                            {{ formatDateRange(item.date_from, item.date_to) }}
                        </div>
                        <div class="advance-card__meta">
                            <span class="advance-card__chip advance-card__chip--soft">
                                Ведомостей: {{ item.statement_ids?.length || 0 }}
                            </span>
                        </div>
                        <div class="advance-card__footer">
                            <span v-if="item.created_at">Создано: {{ formatDate(item.created_at) }}</span>
                        </div>
                    </button>

                    <button
                        v-else
                        type="button"
                        class="advance-card"
                        @click="openStatementModal(item.id)"
                    >
                        <div class="advance-card__top">
                            <span class="advance-card__id">№ {{ item.id }}</span>
                            <span class="advance-card__status" :class="`is-${item.status}`">
                                {{ statusLabel(item.status) }}
                            </span>
                        </div>
                        <div class="advance-card__title">
                            {{ item.restaurant_name || 'Ресторан не задан' }}
                        </div>
                        <div class="advance-card__range">
                            {{ formatDateRange(item.date_from, item.date_to) }}
                        </div>
                        <div class="advance-card__meta">
                            <span class="advance-card__chip" :class="`is-${item.statement_kind || 'advance'}`">
                                {{ statementKindLabel(item.statement_kind) }}
                            </span>
                            <span v-if="item.subdivision_name" class="advance-card__chip">
                                {{ item.subdivision_name }}
                            </span>
                            <span
                                v-if="item.statement_kind !== 'salary' && item.salary_percent !== null && item.salary_percent !== undefined"
                                class="advance-card__chip"
                            >
                                Аванс {{ formatNumber(item.salary_percent) }}%
                            </span>
                            <span v-if="item.fixed_only" class="advance-card__chip advance-card__chip--soft">
                                Только оклад
                            </span>
                            <span v-else class="advance-card__chip advance-card__chip--soft">
                                Все форматы
                            </span>
                        </div>
                        <div class="advance-card__footer">
                            <span v-if="item.created_at">Создано: {{ formatDate(item.created_at) }}</span>
                            <span v-if="item.updated_at">Обновлено: {{ formatDate(item.updated_at) }}</span>
                        </div>
                    </button>
                </template>
            </div>
            <p v-else class="advance-list__empty">{{ emptyListLabel }}</p>

            <div v-if="activeTab === 'draft'" class="advance-panel__footer">
                <Button color="primary" :disabled="!canCreate" @click="openCreateModal">
                    Сформировать черновик
                </Button>
            </div>
        </section>

        <div v-if="showStatementModal && currentStatement" class="advance-modal">
            <div class="advance-modal__dialog advance-modal__dialog--wide">
                <div class="advance-modal__header">
                    <div>
                        <p class="advance-panel__eyebrow">{{ currentStatementLabel }} № {{ currentStatement.id }}</p>
                        <h3 class="advance-modal__title">
                            {{ currentStatement.restaurant_name || 'Ресторан не задан' }}
                            · {{ formatDateRange(currentStatement.date_from, currentStatement.date_to) }}
                        </h3>
                        <div class="advance-modal__status-row">
                            <span class="advance-modal__status-chip advance-modal__status-chip--kind">
                                {{ statementKindLabel(currentStatement.statement_kind) }}
                            </span>
                            <span class="advance-modal__status-chip" :class="`is-${currentStatement.status}`">
                                {{ statusLabel(currentStatement.status) }}
                            </span>
                            <span
                                v-if="currentStatement.posted_at"
                                class="advance-modal__status-chip advance-modal__status-chip--soft"
                            >
                                Записан {{ formatDate(currentStatement.posted_at) }}
                            </span>
                        </div>
                    </div>
                    <div class="advance-modal__header-actions">
                        <button
                            type="button"
                            class="advance-modal__icon-button advance-modal__icon-button--danger"
                            :disabled="!canDelete || isDeleting"
                            title="Удалить ведомость"
                            aria-label="Удалить ведомость"
                            @click="handleDelete"
                        >
                            <BaseIcon name="Trash" />
                        </button>
                        <button
                            type="button"
                            class="advance-modal__icon-button"
                            :disabled="isRefreshing || !canRefresh"
                            title="Обновить расчёты"
                            aria-label="Обновить расчёты"
                            @click="handleRefresh"
                        >
                            <BaseIcon name="Refresh" />
                        </button>
                        <button
                            type="button"
                            class="advance-modal__icon-button advance-modal__icon-button--excel"
                            :disabled="isDownloading || !canDownload"
                            title="Скачать Excel"
                            aria-label="Скачать Excel"
                            @click="handleDownload"
                        >
                            <BaseIcon name="Excel" />
                        </button>
                        <button
                            type="button"
                            class="advance-modal__icon-button"
                            title="Закрыть"
                            aria-label="Закрыть"
                            @click="closeStatementModal"
                        >
                            <BaseIcon name="Close" />
                        </button>
                    </div>
                </div>

                <div class="advance-modal__toolbar">
                    <div class="advance-modal__status-form">
                        <div class="advance-modal__status-field">
                            <Select
                                v-model="selectedStatus"
                                label="Статус ведомости"
                                :options="statusSelectOptions"
                                placeholder="Выберите статус"
                            />
                        </div>
                        <Button
                            color="outline"
                            size="sm"
                            :disabled="!canApplySelectedStatus || isStatusChanging"
                            :loading="isStatusChanging"
                            @click="applySelectedStatus"
                        >
                            Применить
                        </Button>
                    </div>
                    <div class="advance-modal__toolbar-right">
                        <Button
                            color="danger"
                            size="sm"
                            :disabled="!canPost || isStatusChanging"
                            @click="openPostModal"
                        >
                            Записать ведомость
                        </Button>
                    </div>
                </div>

                <div class="advance-modal__body">
                    <div class="advance-summary">
                        <div class="advance-summary__card">
                            <p class="advance-summary__label">Начислено за часы</p>
                            <p class="advance-summary__value">{{ formatMoney(statementTotals.calculated_amount) }}</p>
                        </div>
                        <div class="advance-summary__card">
                            <p class="advance-summary__label">Итого начислений</p>
                            <p class="advance-summary__value">{{ formatMoney(statementSummaryAccrualAmount) }}</p>
                        </div>
                        <div class="advance-summary__card">
                            <p class="advance-summary__label">Итого удержаний</p>
                            <p class="advance-summary__value">{{ formatMoney(statementSummaryDeductionAmount) }}</p>
                        </div>
                        <div class="advance-summary__card advance-summary__card--accent">
                            <p class="advance-summary__label">Итого к выдаче</p>
                            <p class="advance-summary__value">{{ formatMoney(statementTotals.final_amount) }}</p>
                        </div>
                        <div
                            v-if="showAdvanceSummaryCard"
                            class="advance-summary__card advance-summary__card--accent"
                        >
                            <p class="advance-summary__label">Аванс</p>
                            <p class="advance-summary__value">{{ formatMoney(statementAdvanceDeductionAmount) }}</p>
                        </div>
                        <div
                            v-if="showStatementFotSummaryCards"
                            class="advance-summary__card"
                        >
                            <p class="advance-summary__label">Выручка</p>
                            <p class="advance-summary__value">{{ statementFotRevenueAmountLabel }}</p>
                        </div>
                        <div
                            v-if="showStatementFotSummaryCards"
                            class="advance-summary__card"
                        >
                            <p class="advance-summary__label">Итого начислено</p>
                            <p class="advance-summary__value">{{ statementFotAccruedAmountLabel }}</p>
                        </div>
                        <div
                            v-if="showStatementFotSummaryCards"
                            class="advance-summary__card advance-summary__card--accent"
                        >
                            <p class="advance-summary__label">ФОТ</p>
                            <p class="advance-summary__value">{{ statementFotShareLabel }}</p>
                        </div>
                    </div>
                    <div
                        v-if="isSalaryStatement"
                        class="advance-statement-tabs"
                        role="tablist"
                        aria-label="Режим просмотра ведомости"
                    >
                        <button
                            type="button"
                            class="advance-statement-tabs__button"
                            :class="{ 'is-active': statementViewTab === 'table' }"
                            :aria-selected="statementViewTab === 'table'"
                            @click="setStatementViewTab('table')"
                        >
                            Таблица
                        </button>
                        <button
                            type="button"
                            class="advance-statement-tabs__button"
                            :class="{ 'is-active': statementViewTab === 'histogram' }"
                            :aria-selected="statementViewTab === 'histogram'"
                            @click="setStatementViewTab('histogram')"
                        >
                            Гистограмма
                        </button>
                    </div>

                    <div v-if="!isSalaryStatement || statementViewTab === 'table'" class="advance-table-wrapper">
                        <table class="advance-table">
                            <thead>
                                <tr>
                                    <th class="advance-table__col advance-table__col--position" :aria-sort="getItemAriaSort('position_name')">
                                        <button
                                            type="button"
                                            class="advance-table__sort"
                                            :class="{ 'is-active': isItemSortActive('position_name') }"
                                            @click="toggleItemSort('position_name')"
                                        >
                                            Должность
                                            <span v-if="isItemSortActive('position_name')" class="advance-table__sort-icon">
                                                {{ itemSortIndicator('position_name') }}
                                            </span>
                                        </button>
                                    </th>
                                    <th class="advance-table__col advance-table__col--employee" :aria-sort="getItemAriaSort('full_name')">
                                        <button
                                            type="button"
                                            class="advance-table__sort"
                                            :class="{ 'is-active': isItemSortActive('full_name') }"
                                            @click="toggleItemSort('full_name')"
                                        >
                                            Сотрудник
                                            <span v-if="isItemSortActive('full_name')" class="advance-table__sort-icon">
                                                {{ itemSortIndicator('full_name') }}
                                            </span>
                                        </button>
                                    </th>
                                    <th class="advance-table__col advance-table__col--hours" :aria-sort="getItemAriaSort('fact_hours')">
                                        <button
                                            type="button"
                                            class="advance-table__sort"
                                            :class="{ 'is-active': isItemSortActive('fact_hours') }"
                                            @click="toggleItemSort('fact_hours')"
                                        >
                                            Часы
                                            <span v-if="isItemSortActive('fact_hours')" class="advance-table__sort-icon">
                                                {{ itemSortIndicator('fact_hours') }}
                                            </span>
                                        </button>
                                    </th>
                                    <th class="advance-table__col advance-table__col--hours" :aria-sort="getItemAriaSort('night_hours')">
                                        <button
                                            type="button"
                                            class="advance-table__sort"
                                            :class="{ 'is-active': isItemSortActive('night_hours') }"
                                            @click="toggleItemSort('night_hours')"
                                        >
                                            Ночные часы
                                            <span v-if="isItemSortActive('night_hours')" class="advance-table__sort-icon">
                                                {{ itemSortIndicator('night_hours') }}
                                            </span>
                                        </button>
                                    </th>
                                    <th class="advance-table__col advance-table__col--money" :aria-sort="getItemAriaSort('rate')">
                                        <button
                                            type="button"
                                            class="advance-table__sort"
                                            :class="{ 'is-active': isItemSortActive('rate') }"
                                            @click="toggleItemSort('rate')"
                                        >
                                            Ставка
                                            <span v-if="isItemSortActive('rate')" class="advance-table__sort-icon">
                                                {{ itemSortIndicator('rate') }}
                                            </span>
                                        </button>
                                    </th>
                                    <th class="advance-table__col advance-table__col--money" :aria-sort="getItemAriaSort('accrual_amount')">
                                        <button
                                            type="button"
                                            class="advance-table__sort"
                                            :class="{ 'is-active': isItemSortActive('accrual_amount') }"
                                            @click="toggleItemSort('accrual_amount')"
                                        >
                                            Начисления
                                            <span v-if="isItemSortActive('accrual_amount')" class="advance-table__sort-icon">
                                                {{ itemSortIndicator('accrual_amount') }}
                                            </span>
                                        </button>
                                    </th>
                                    <th class="advance-table__col advance-table__col--money" :aria-sort="getItemAriaSort('deduction_amount')">
                                        <button
                                            type="button"
                                            class="advance-table__sort"
                                            :class="{ 'is-active': isItemSortActive('deduction_amount') }"
                                            @click="toggleItemSort('deduction_amount')"
                                        >
                                            Удержания
                                            <span v-if="isItemSortActive('deduction_amount')" class="advance-table__sort-icon">
                                                {{ itemSortIndicator('deduction_amount') }}
                                            </span>
                                        </button>
                                    </th>
                                    <th class="advance-table__col advance-table__col--money" :aria-sort="getItemAriaSort('calculated_amount')">
                                        <button
                                            type="button"
                                            class="advance-table__sort"
                                            :class="{ 'is-active': isItemSortActive('calculated_amount') }"
                                            @click="toggleItemSort('calculated_amount')"
                                        >
                                            Расчёт
                                            <span v-if="isItemSortActive('calculated_amount')" class="advance-table__sort-icon">
                                                {{ itemSortIndicator('calculated_amount') }}
                                            </span>
                                        </button>
                                    </th>
                                    <th class="advance-table__col advance-table__col--money" :aria-sort="getItemAriaSort('total_accrued')">
                                        <button
                                            type="button"
                                            class="advance-table__sort"
                                            :class="{ 'is-active': isItemSortActive('total_accrued') }"
                                            @click="toggleItemSort('total_accrued')"
                                        >
                                            Итого начислено
                                            <span v-if="isItemSortActive('total_accrued')" class="advance-table__sort-icon">
                                                {{ itemSortIndicator('total_accrued') }}
                                            </span>
                                        </button>
                                    </th>
                                    <th class="advance-table__col advance-table__col--final" :aria-sort="getItemAriaSort('final_amount')">
                                        <button
                                            type="button"
                                            class="advance-table__sort"
                                            :class="{ 'is-active': isItemSortActive('final_amount') }"
                                            @click="toggleItemSort('final_amount')"
                                        >
                                            Итог
                                            <span v-if="isItemSortActive('final_amount')" class="advance-table__sort-icon">
                                                {{ itemSortIndicator('final_amount') }}
                                            </span>
                                        </button>
                                    </th>
                                    <th class="advance-table__col advance-table__col--comment">Комментарий</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr
                                    v-for="item in sortedStatementItems"
                                    :key="item.id"
                                    :class="{ 'advance-table__row--fired': item.fired }"
                                >
                                    <td class="advance-table__cell--position">{{ item.position_name || '—' }}</td>
                                    <td class="advance-table__cell--employee">
                                        <button
                                            type="button"
                                            class="advance-table__employee-link"
                                            @click.stop="openEmployeeCard(item.user_id)"
                                        >
                                            {{ item.full_name }}
                                        </button>
                                    </td>
                                    <td class="advance-table__cell--number">{{ formatNumber(item.fact_hours) }}</td>
                                    <td class="advance-table__cell--number">{{ formatNumber(item.night_hours) }}</td>
                                    <td class="advance-table__cell--money">{{ formatMoney(item.rate) }}</td>
                                    <td class="advance-table__cell--money">{{ formatMoney(item.accrual_amount) }}</td>
                                    <td class="advance-table__cell--money">{{ formatMoney(item.deduction_amount) }}</td>
                                    <td class="advance-table__cell--money">{{ formatMoney(item.calculated_amount) }}</td>
                                    <td class="advance-table__cell--money">
                                        {{ formatMoney(getItemTotalAccruedValue(item, currentStatement.statement_kind)) }}
                                    </td>
                                    <td class="advance-table__cell--final">
                                        <div class="advance-table__editable-cell">
                                            <input
                                                v-model.number="item.final_amount"
                                                class="advance-table__input"
                                                type="number"
                                                step="0.01"
                                                :disabled="!canEditItem"
                                                @focus="() => rememberPersistedFinalAmount(item)"
                                                @change="() => saveItem(item)"
                                                @keydown.enter.prevent="($event) => $event.target.blur()"
                                                @blur="() => saveItem(item)"
                                            >
                                            <span v-if="item.manual" class="advance-table__tag">Ручная правка</span>
                                        </div>
                                    </td>
                                    <td class="advance-table__cell--comment">
                                        <input
                                            v-model="item.comment"
                                            class="advance-table__input"
                                            type="text"
                                            :disabled="!canEditItem"
                                            placeholder="Комментарий"
                                            @blur="() => saveItem(item)"
                                        >
                                    </td>
                                </tr>
                            </tbody>
                            <tfoot v-if="statementTotals.row_count">
                                <tr class="advance-table__totals">
                                    <td colspan="2">
                                        Итого
                                        <span class="advance-table__totals-meta">
                                            (строк: {{ statementTotals.row_count }})
                                        </span>
                                    </td>
                                    <td class="advance-table__cell--number">{{ formatNumber(statementTotals.fact_hours) }}</td>
                                    <td class="advance-table__cell--number">{{ formatNumber(statementTotals.night_hours) }}</td>
                                    <td class="advance-table__cell--money">—</td>
                                    <td class="advance-table__cell--money">{{ formatMoney(statementTotals.accrual_amount) }}</td>
                                    <td class="advance-table__cell--money">{{ formatMoney(statementTotals.deduction_amount) }}</td>
                                    <td class="advance-table__cell--money">{{ formatMoney(statementTotals.calculated_amount) }}</td>
                                    <td class="advance-table__cell--money">{{ formatMoney(statementTotals.total_accrued) }}</td>
                                    <td class="advance-table__cell--money">{{ formatMoney(statementTotals.final_amount) }}</td>
                                    <td class="advance-table__cell--comment">—</td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                    <div v-else class="advance-consolidated-histogram advance-statement-histogram">
                        <div class="advance-statement-histogram__header">
                            <div>
                                <p class="advance-consolidated-histogram__title">Гистограмма ФОТ по настройкам</p>
                                <p class="advance-consolidated-histogram__subtitle">
                                    {{ statementHistogramSubtitle }}
                                </p>
                            </div>
                            <Button
                                v-if="statementHistogramSelectedSubdivision"
                                color="ghost"
                                size="sm"
                                @click="resetStatementHistogramDrilldown"
                            >
                                Назад к подразделениям
                            </Button>
                        </div>
                        <p v-if="statementHistogramLoading" class="advance-consolidated-summary__loading">
                            Загружаем гистограмму...
                        </p>
                        <p v-else-if="statementHistogramError" class="advance-consolidated-summary__error">
                            {{ statementHistogramError }}
                        </p>
                        <p v-else-if="!statementHistogramItems.length" class="advance-list__empty">
                            Нет данных для гистограммы.
                        </p>
                        <VChart
                            v-else
                            class="advance-statement-histogram__chart"
                            :option="statementHistogramOption"
                            autoresize
                            @click="handleStatementHistogramClick"
                        />
                        <p class="advance-statement-histogram__hint">
                            Клик по столбцу подразделения показывает столбцы должностей этого подразделения.
                        </p>
                    </div>
                </div>
            </div>
        </div>

        <div v-if="showConsolidatedModal" class="advance-modal">
            <div class="advance-modal__dialog advance-modal__dialog--wide advance-consolidated">
                <div class="advance-modal__header">
                    <div>
                        <h3 class="advance-modal__title">Сводная ведомость</h3>
                        <p class="advance-modal__subtitle">Выберите проверенные ведомости для общего файла.</p>
                    </div>
                    <div class="advance-modal__header-actions">
                        <Button color="ghost" size="sm" @click="closeConsolidatedModal">Закрыть</Button>
                    </div>
                </div>
                <div class="advance-modal__body">
                    <div class="advance-consolidated__toolbar">
                        <Button color="outline" size="sm" @click="toggleConsolidatedSelectAll">
                            {{ isAllConsolidatedSelected ? 'Снять выделение' : 'Выбрать все' }}
                        </Button>
                        <p class="advance-consolidated__meta">Выбрано: {{ consolidatedSelectedCount }} / {{ consolidatedCandidateIds.length }}</p>
                    </div>
                    <div v-if="hasConsolidatedCandidates" class="advance-consolidated__list">
                        <label
                            v-for="item in consolidatedCandidates"
                            :key="item.id"
                            class="advance-consolidated__item"
                        >
                            <input
                                class="advance-consolidated__checkbox"
                                type="checkbox"
                                :checked="isConsolidatedSelected(item.id)"
                                @change="toggleConsolidatedSelection(item.id)"
                            >
                            <span class="advance-consolidated__info">
                                <span class="advance-consolidated__title">&#8470; {{ item.id }} &middot; {{ formatDateRange(item.date_from, item.date_to) }}</span>
                                <span class="advance-consolidated__subtitle">{{ item.restaurant_name || 'Ресторан не задан' }}</span>
                            </span>
                            <span class="advance-consolidated__status" :class="`is-${item.status}`">
                                {{ statusLabel(item.status) }}
                            </span>
                        </label>
                    </div>
                    <p v-else class="advance-list__empty advance-consolidated__empty">Нет ведомостей для сводного файла.</p>
                </div>
                <div class="advance-modal__actions advance-consolidated__actions">
                    <Button color="outline" @click="closeConsolidatedModal">Отмена</Button>
                    <Button
                        color="success"
                        :loading="isConsolidatedCreating"
                        :disabled="!consolidatedSelectedCount"
                        @click="handleConsolidatedCreate"
                    >
                        Создать общую ведомость
                    </Button>
                    <Button
                        color="outline"
                        :loading="isConsolidatedDownloading"
                        :disabled="!consolidatedSelectedCount"
                        @click="handleConsolidatedDownload"
                    >
                        Скачать файл
                    </Button>
                </div>
            </div>
        </div>

        <div v-if="showConsolidatedStatementModal && currentConsolidated" class="advance-modal">
            <div class="advance-modal__dialog advance-modal__dialog--wide advance-consolidated-card">
                <div class="advance-modal__header">
                    <div>
                        <p class="advance-panel__eyebrow">Общая ведомость № {{ currentConsolidated.id }}</p>
                        <h3 class="advance-modal__title">
                            {{ currentConsolidated.title || 'Общая ведомость' }}
                            · {{ formatDateRange(currentConsolidated.date_from, currentConsolidated.date_to) }}
                        </h3>
                        <p class="advance-modal__subtitle">Внутри: {{ consolidatedStatementsInCurrent.length }} ведомостей.</p>
                    </div>
                    <div class="advance-modal__header-actions">
                        <button
                            type="button"
                            class="advance-modal__icon-button"
                            title="Закрыть"
                            aria-label="Закрыть"
                            @click="closeConsolidatedStatementModal"
                        >
                            <BaseIcon name="Close" />
                        </button>
                    </div>
                </div>
                <div class="advance-modal__body">
                    <div class="advance-consolidated-card__tabs" role="tablist" aria-label="Режим просмотра общей ведомости">
                        <button
                            type="button"
                            class="advance-consolidated-card__tab"
                            :class="{ 'is-active': consolidatedViewTab === 'statements' }"
                            :aria-selected="consolidatedViewTab === 'statements'"
                            @click="consolidatedViewTab = 'statements'"
                        >
                            Ведомости
                        </button>
                        <button
                            type="button"
                            class="advance-consolidated-card__tab"
                            :class="{ 'is-active': consolidatedViewTab === 'histogram' }"
                            :aria-selected="consolidatedViewTab === 'histogram'"
                            @click="consolidatedViewTab = 'histogram'"
                        >
                            Гистограмма
                        </button>
                    </div>

                    <div v-if="consolidatedViewTab === 'statements'" class="advance-consolidated-card__panel">
                        <div class="advance-consolidated-summary">
                            <p class="advance-consolidated-summary__title">Итоги по общей ведомости</p>
                            <p v-if="consolidatedTotalsLoading" class="advance-consolidated-summary__loading">
                                Считаем итоги...
                            </p>
                            <p v-else-if="consolidatedTotalsError" class="advance-consolidated-summary__error">
                                {{ consolidatedTotalsError }}
                            </p>
                            <div v-else class="advance-consolidated-summary__grid">
                                <div class="advance-consolidated-summary__card">
                                    <p class="advance-consolidated-summary__label">Начислено</p>
                                    <p class="advance-consolidated-summary__value">{{ formatMoney(consolidatedTotals.accrual_total) }}</p>
                                    <p class="advance-consolidated-summary__meta">
                                        Строк с начислением: {{ consolidatedTotals.accrual_rows_count }}
                                    </p>
                                </div>
                                <div class="advance-consolidated-summary__card">
                                    <p class="advance-consolidated-summary__label">Удержано</p>
                                    <p class="advance-consolidated-summary__value">{{ formatMoney(consolidatedTotals.deduction_total) }}</p>
                                    <p class="advance-consolidated-summary__meta">
                                        Строк с удержанием: {{ consolidatedTotals.deduction_rows_count }}
                                    </p>
                                </div>
                                <div class="advance-consolidated-summary__card">
                                    <p class="advance-consolidated-summary__label">К выплате</p>
                                    <p
                                        class="advance-consolidated-summary__value"
                                        :class="consolidatedTotals.final_total < 0 ? 'is-negative' : ''"
                                    >
                                        {{ formatMoney(consolidatedTotals.final_total) }}
                                    </p>
                                    <p class="advance-consolidated-summary__meta">Сотрудников: {{ consolidatedTotals.row_count }}</p>
                                </div>
                                <div class="advance-consolidated-summary__card">
                                    <p class="advance-consolidated-summary__label">Ведомостей</p>
                                    <p class="advance-consolidated-summary__value">{{ consolidatedTotals.loaded_statement_count }} / {{ consolidatedTotals.statement_count }}</p>
                                    <p class="advance-consolidated-summary__meta">Загружено для итогов</p>
                                </div>
                            </div>
                            <p v-if="consolidatedTotalsWarning" class="advance-consolidated-summary__warning">
                                {{ consolidatedTotalsWarning }}
                            </p>
                        </div>

                        <div v-if="consolidatedStatementsInCurrent.length" class="advance-list advance-consolidated-card__grid">
                            <button
                                v-for="stmt in consolidatedStatementsInCurrent"
                                :key="stmt.id"
                                type="button"
                                class="advance-card advance-consolidated-card__tile"
                                :disabled="stmt.missing"
                                @click="() => openStatementFromConsolidated(stmt.id)"
                            >
                                <div class="advance-card__top">
                                    <span class="advance-card__id">№ {{ stmt.id }}</span>
                                    <span
                                        class="advance-card__status"
                                        :class="stmt.missing ? 'is-missing' : `is-${stmt.status}`"
                                    >
                                        {{ stmt.missing ? 'Удалена' : statusLabel(stmt.status) }}
                                    </span>
                                </div>
                                <div class="advance-card__title">
                                    {{ stmt.restaurant_name || 'Ресторан не задан' }}
                                </div>
                                <div class="advance-card__range">
                                    {{ formatDateRange(stmt.date_from, stmt.date_to) }}
                                </div>
                                <div class="advance-card__meta">
                                    <template v-if="consolidatedStatementTotals[stmt.id]">
                                        <span class="advance-card__chip advance-card__chip--soft">
                                            К выплате: {{ formatMoney(consolidatedStatementTotals[stmt.id].final_total) }}
                                        </span>
                                        <span class="advance-card__chip advance-card__chip--soft">
                                            Строк: {{ consolidatedStatementTotals[stmt.id].row_count }}
                                        </span>
                                    </template>
                                    <span
                                        v-else-if="consolidatedTotalsLoading && !stmt.missing"
                                        class="advance-card__chip advance-card__chip--soft"
                                    >
                                        Считаем итоги...
                                    </span>
                                </div>
                            </button>
                        </div>
                        <p v-else class="advance-list__empty advance-consolidated-card__empty">Нет ведомостей внутри этой общей ведомости.</p>
                    </div>

                    <div v-else class="advance-consolidated-histogram advance-statement-histogram advance-consolidated-card__panel">
                        <div class="advance-statement-histogram__header">
                            <div>
                                <p class="advance-consolidated-histogram__title">Гистограмма по подразделениям</p>
                                <p class="advance-consolidated-histogram__subtitle">
                                    {{ consolidatedHistogramSubtitle }}
                                </p>
                            </div>
                            <Button
                                v-if="consolidatedHistogramSelectedSubdivision"
                                color="ghost"
                                size="sm"
                                @click="resetConsolidatedHistogramDrilldown"
                            >
                                Назад к подразделениям
                            </Button>
                        </div>

                        <p v-if="consolidatedHistogramLoading" class="advance-consolidated-summary__loading">
                            Загружаем гистограмму...
                        </p>
                        <p v-else-if="consolidatedHistogramError" class="advance-consolidated-summary__error">
                            {{ consolidatedHistogramError }}
                        </p>
                        <p v-else-if="!consolidatedHistogramItems.length" class="advance-list__empty">
                            Нет данных для гистограммы.
                        </p>
                        <VChart
                            v-else
                            class="advance-statement-histogram__chart"
                            :option="consolidatedHistogramOption"
                            autoresize
                            @click="handleConsolidatedHistogramClick"
                        />
                        <p class="advance-statement-histogram__hint">
                            Клик по столбцу подразделения показывает столбцы должностей этого подразделения во всей компании.
                        </p>
                        <p v-if="consolidatedTotalsWarning" class="advance-consolidated-summary__warning">
                            {{ consolidatedTotalsWarning }}
                        </p>
                    </div>
                </div>
                <div class="advance-modal__actions advance-consolidated-card__actions">
                    <Button color="outline" @click="closeConsolidatedStatementModal">Закрыть</Button>
                    <Button
                        color="danger"
                        :loading="isConsolidatedStatementDeleting"
                        @click="handleConsolidatedStatementDelete"
                    >
                        Удалить
                    </Button>
                    <Button
                        color="success"
                        :loading="isConsolidatedStatementDownloading"
                        @click="handleConsolidatedStatementDownload"
                    >
                        Скачать файл
                    </Button>
                </div>
            </div>
        </div>

        <div v-if="showCreateModal" class="advance-modal">
            <div class="advance-modal__dialog">
                <h3 class="advance-modal__title">Сформировать черновик</h3>
                <p class="advance-modal__subtitle">Заполним параметры расчёта ведомости.</p>
                <div class="advance-panel__grid advance-modal__grid">
                    <div class="advance-panel__field advance-panel__field--full">
                        <label class="advance-panel__label">Тип ведомости</label>
                        <div class="advance-kind-toggle" :class="{ 'is-salary': createForm.statementKind === 'salary' }">
                            <span class="advance-kind-toggle__label" :class="{ 'is-active': createForm.statementKind === 'advance' }">
                                Аванс
                            </span>
                            <label class="advance-kind-toggle__switch">
                                <input
                                    :checked="createForm.statementKind === 'salary'"
                                    type="checkbox"
                                    :disabled="isCreating"
                                    @change="createForm.statementKind = $event.target.checked ? 'salary' : 'advance'"
                                >
                                <span class="advance-kind-toggle__slider" />
                            </label>
                            <span class="advance-kind-toggle__label" :class="{ 'is-active': createForm.statementKind === 'salary' }">
                                Зарплата
                            </span>
                        </div>
                    </div>
                    <Select
                        v-model="createForm.restaurantId"
                        label="Ресторан"
                        :options="restaurantOptions"
                        placeholder="Выберите ресторан"
                        :disabled="isCreating"
                    />
                    <div class="advance-panel__field">
                        <label class="advance-panel__label" for="create-date-from">Дата с</label>
                        <DateInput
                            id="create-date-from"
                            v-model="createForm.dateFrom"
                            :disabled="isCreating"
                        />
                    </div>
                    <div class="advance-panel__field">
                        <label class="advance-panel__label" for="create-date-to">Дата по</label>
                        <DateInput
                            id="create-date-to"
                            v-model="createForm.dateTo"
                            :disabled="isCreating"
                        />
                    </div>
                    <div v-if="createForm.statementKind === 'advance'" class="advance-panel__field">
                        <label class="advance-panel__label" for="create-salary-percent">Процент аванса</label>
                        <input
                        id="create-salary-percent"
                        v-model.number="createForm.salaryPercent"
                        class="advance-panel__input"
                        type="number"
                        step="1"
                        min="0"
                        max="100"
                        :disabled="isCreating"
                        >
                    </div>
                    <div v-else class="advance-panel__field">
                        <p class="advance-panel__label">Процент ведомости</p>
                        <p class="advance-panel__hint">Для зарплатной ведомости используется 100% автоматически.</p>
                    </div>
                </div>
                <div class="advance-modal__actions">
                    <Button color="ghost" :disabled="isCreating" @click="closeCreateModal">Отмена</Button>
                    <Button color="primary" :loading="isCreating" @click="submitCreate">Сформировать</Button>
                </div>
            </div>
        </div>

        <div v-if="showPostModal" class="advance-modal advance-modal--top">
            <div class="advance-modal__dialog">
                <h3 class="advance-modal__title">Записать ведомость</h3>
                <p class="advance-modal__subtitle">Создадим массовое начисление по итоговым суммам.</p>
                <div class="advance-panel__grid advance-modal__grid">
                    <Select
                        v-model="postForm.adjustmentTypeId"
                        label="Тип начисления"
                        :options="adjustmentTypeOptions"
                        placeholder="Выберите тип"
                        :disabled="postLoading"
                    />
                    <div class="advance-panel__field">
                        <label class="advance-panel__label" for="post-date">Дата операции</label>
                        <DateInput
                            id="post-date"
                            v-model="postForm.date"
                            :disabled="postLoading"
                        />
                    </div>
                </div>
                <div class="advance-panel__field">
                    <label class="advance-panel__label" for="post-comment">Комментарий</label>
                    <textarea
                        id="post-comment"
                        v-model="postForm.comment"
                        class="advance-panel__textarea"
                        rows="2"
                        :disabled="postLoading"
                    />
                </div>
                <div v-if="postResultRows.length" class="advance-post-result">
                    <div class="advance-post-result__summary">
                        <span class="advance-post-result__pill is-created">
                            Создано: {{ postResult.createdCount }}
                        </span>
                        <span v-if="postResult.skippedCount" class="advance-post-result__pill is-skipped">
                            Пропущено: {{ postResult.skippedCount }}
                        </span>
                        <span v-if="postResult.errorCount" class="advance-post-result__pill is-error">
                            Ошибок: {{ postResult.errorCount }}
                        </span>
                    </div>
                    <div class="advance-post-result__table-wrap">
                        <table class="advance-post-result__table">
                            <thead>
                                <tr>
                                    <th>Сотрудник</th>
                                    <th>Табельный</th>
                                    <th>Статус</th>
                                    <th>Комментарий</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr
                                    v-for="(row, rowIndex) in postResultRows"
                                    :key="`${row.staffCode}-${row.status}-${row.reason || ''}-${rowIndex}`"
                                    :class="`is-${row.status}`"
                                >
                                    <td>{{ row.fullName || '—' }}</td>
                                    <td>{{ row.staffCode || '—' }}</td>
                                    <td>
                                        <span class="advance-post-result__status" :class="`is-${row.status}`">
                                            {{ postStatusLabel(row.status) }}
                                        </span>
                                    </td>
                                    <td>{{ row.reason || '—' }}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="advance-modal__actions">
                    <Button color="ghost" :disabled="postLoading" @click="closePostModal">Отмена</Button>
                    <Button color="primary" :loading="postLoading" @click="handlePost">Записать</Button>
                </div>
            </div>
        </div>

        <EmployeesPage v-if="showEmployeeCardOverlay" modal-only class="advance-page__employee-overlay" />
    </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { use } from 'echarts/core';
import { BarChart } from 'echarts/charts';
import { CanvasRenderer } from 'echarts/renderers';
import { GridComponent, TooltipComponent } from 'echarts/components';
import { useRoute, useRouter } from 'vue-router';
import { useToast } from 'vue-toastification';
import {
    changeAdvanceStatus,
    createAdvanceStatement,
    downloadAdvanceStatement,
    fetchAdvanceStatement,
    fetchAdvanceStatementTotals,
    fetchAdvanceStatements,
    fetchAdvanceConsolidatedStatements,
    fetchLaborSummary,
    fetchTimesheetOptions,
    refreshAdvanceStatement,
    updateAdvanceItemsCompact,
    postAdvanceStatement,
    fetchPayrollAdjustmentTypes,
    deleteAdvanceStatement,
    downloadAdvanceConsolidated,
    createAdvanceConsolidatedStatement,
    downloadAdvanceConsolidatedById,
    deleteAdvanceConsolidatedStatement,
} from '@/api';
import Button from '@/components/UI-components/Button.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Select from '@/components/UI-components/Select.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import EmployeesPage from '@/pages/AdminLayout/Employees/EmployeesPage.vue';
import { useUserStore } from '@/stores/user';
import { formatDateValue, formatNumberValue } from '@/utils/format';
import { downloadBlobFile } from '@/utils/downloadBlobFile';
import VChart from 'vue-echarts';

use([
    CanvasRenderer,
    BarChart,
    GridComponent,
    TooltipComponent,
]);

const toast = useToast();
const userStore = useUserStore();
const route = useRoute();
const router = useRouter();

const statements = ref([]);
const consolidatedStatements = ref([]);
const currentStatement = ref(null);
const showStatementModal = ref(false);
const statementViewTab = ref('table');
const statementHistogramLoading = ref(false);
const statementHistogramError = ref('');
const statementHistogramRows = ref([]);
const statementHistogramSubdivisionKey = ref('');
const statementHistogramTotals = ref(null);
const isCreating = ref(false);
const isRefreshing = ref(false);
const isDownloading = ref(false);
const isDeleting = ref(false);
const restaurantOptions = ref([]);
const showCreateModal = ref(false);
const isStatusChanging = ref(false);
const showPostModal = ref(false);
const postLoading = ref(false);
const postForm = ref({
    adjustmentTypeId: '',
    date: '',
    comment: '',
});
const postResult = ref({
    createdCount: 0,
    createdTotal: 0,
    skippedCount: 0,
    errorCount: 0,
    rows: [],
});
const adjustmentTypes = ref([]);
const showConsolidatedModal = ref(false);
const isConsolidatedDownloading = ref(false);
const consolidatedSelectedIds = ref([]);
const currentConsolidated = ref(null);
const showConsolidatedStatementModal = ref(false);
const consolidatedViewTab = ref('statements');
const isConsolidatedCreating = ref(false);
const isConsolidatedStatementDownloading = ref(false);
const isConsolidatedStatementDeleting = ref(false);
const showEmployeeCardOverlay = ref(false);
const selectedStatus = ref('');
const pendingItemSaveMap = new Map();
const persistedItemFinalAmountMap = new Map();
let pendingItemSaveTimer = null;
let pendingItemSaveRequest = null;

const consolidatedTotalsLoading = ref(false);
const consolidatedTotalsError = ref('');
const consolidatedTotalsWarning = ref('');
const consolidatedHistogramLoading = ref(false);
const consolidatedHistogramError = ref('');
const consolidatedHistogramRows = ref([]);
const consolidatedHistogramSubdivisionKey = ref('');
const consolidatedTotals = ref({
    statement_count: 0,
    loaded_statement_count: 0,
    row_count: 0,
    accrual_total: 0,
    deduction_total: 0,
    final_total: 0,
    accrual_rows_count: 0,
    deduction_rows_count: 0,
});
const consolidatedStatementTotals = ref({});

const activeTab = ref('draft');
const listFilters = ref({
    restaurantId: '',
    month: '',
});
const createForm = ref({
    restaurantId: '',
    dateFrom: '',
    dateTo: '',
    statementKind: 'advance',
    salaryPercent: 50,
});

function formatDate(value) {
    return formatDateValue(value, {
        emptyValue: '',
        invalidValue: '',
        locale: 'ru-RU',
    });
}

function formatDateRange(from, to) {
    const start = formatDate(from);
    const end = formatDate(to);
    if (start && end) return `${start} — ${end}`;
    return start || end || '';
}

function formatMoney(value) {
    return formatNumberValue(value, {
        emptyValue: '0.00',
        invalidValue: '0.00',
        locale: 'en-US',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
        useGrouping: false,
    });
}

function formatNumber(value) {
    const num = Number(value);
    if (Number.isNaN(num)) return '0';
    return num.toFixed(2);
}

function formatPercent(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) return '0.00%';
    return `${formatNumberValue(num * 100, {
        emptyValue: '0.00',
        invalidValue: '0.00',
        locale: 'ru-RU',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
        useGrouping: false,
    })}%`;
}

function getItemTotalAccruedValue(item, statementKind) {
    const finalAmount = Number(item?.final_amount ?? 0) || 0;
    const deductionAmount = Number(item?.deduction_amount ?? 0) || 0;
    if (String(statementKind || '').toLowerCase() !== 'salary') {
        return quantizeMoney(finalAmount);
    }
    return quantizeMoney(finalAmount + deductionAmount);
}

function statementKindLabel(kind) {
    return String(kind || '').toLowerCase() === 'salary' ? 'Зарплата' : 'Аванс';
}

function postStatusLabel(status) {
    if (status === 'created') return 'Создано';
    if (status === 'skipped') return 'Пропущено';
    if (status === 'error') return 'Ошибка';
    return status || '—';
}

function sanitizeFilePart(value, fallback = 'vedomost') {
    const raw = String(value || '').trim();
    if (!raw) return fallback;
    const normalized = raw
        .replace(/[\\/:*?"<>|]+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
    return normalized || fallback;
}

function ensureXlsxFilename(name, fallback = 'vedomost.xlsx') {
    const base = sanitizeFilePart(name, '').trim();
    if (!base) {
        return fallback;
    }
    return /\.xlsx$/i.test(base) ? base : `${base}.xlsx`;
}

function buildStatementFileName(statement) {
    if (!statement) return 'vedomost.xlsx';
    const kind = String(statement.statement_kind || '').toLowerCase() === 'salary' ? 'Зарплата' : 'Аванс';
    const restaurantPart = sanitizeFilePart(
        statement.restaurant_name || (statement.restaurant_id ? `Ресторан ${statement.restaurant_id}` : ''),
        'Ресторан',
    );
    const dateFrom = statement.date_from || 'from';
    const dateTo = statement.date_to || 'to';
    const range = dateFrom === dateTo ? dateFrom : `${dateFrom} - ${dateTo}`;
    return ensureXlsxFilename(`Ведомость ${kind} ${restaurantPart} ${range}`);
}

function buildConsolidatedFileName(monthLabel) {
    const label = sanitizeFilePart(monthLabel || '', new Date().toISOString().slice(0, 7));
    return ensureXlsxFilename(`Сводная ведомость ${label}`, 'svodnaya_vedomost.xlsx');
}

function buildConsolidatedStatementFileName(consolidated, monthLabel) {
    const idPart = Number(consolidated?.id);
    const label = sanitizeFilePart(
        monthLabel || consolidated?.date_from?.slice(0, 7) || new Date().toISOString().slice(0, 7),
        new Date().toISOString().slice(0, 7),
    );
    if (Number.isFinite(idPart) && idPart > 0) {
        return ensureXlsxFilename(`Сводная ведомость ${idPart} ${label}`, 'svodnaya_vedomost.xlsx');
    }
    return buildConsolidatedFileName(label);
}

function resetPostResult() {
    postResult.value = {
        createdCount: 0,
        createdTotal: 0,
        skippedCount: 0,
        errorCount: 0,
        rows: [],
    };
}

function resolveEmployeeIdFromQuery(value) {
    const raw = Array.isArray(value) ? value[0] : value;
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
}

function removeEmployeeQueryFromRoute() {
    if (!route.query.employeeId) return;
    const nextQuery = { ...route.query };
    delete nextQuery.employeeId;
    router.replace({ query: nextQuery });
}

function openEmployeeCard(userId) {
    const employeeId = Number(userId);
    if (!Number.isFinite(employeeId)) return;
    showEmployeeCardOverlay.value = true;
    router.replace({
        query: {
            ...route.query,
            employeeId: String(employeeId),
        },
    });
}

function quantizeMoney(value) {
    const num = Number(value ?? 0);
    if (!Number.isFinite(num)) return 0;
    return Math.round(num * 100) / 100;
}

const sortBy = ref('created_at');
const sortDirection = ref('desc');
const sortOptions = [
    { label: 'По дате создания', value: 'created_at' },
    { label: 'По периоду (с)', value: 'date_from' },
    { label: 'По периоду (по)', value: 'date_to' },
    { label: 'По ресторану', value: 'restaurant_name' },
    { label: 'По статусу', value: 'status' },
];
const statusOrder = {
    draft: 0,
    review: 1,
    confirmed: 2,
    ready: 3,
    posted: 4,
};

function parseDate(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? 0 : date.getTime();
}

function getMonthRange(value) {
    if (!value) return null;
    const [year, month] = value.split('-').map((part) => Number(part));
    if (!year || !month) return null;
    const start = new Date(year, month - 1, 1);
    const end = new Date(year, month, 0);
    return { start, end };
}

function statementMatchesMonth(statement, monthValue) {
    const range = getMonthRange(monthValue);
    if (!range) return true;
    const from = new Date(statement.date_from);
    const to = new Date(statement.date_to);
    if (Number.isNaN(from.getTime()) || Number.isNaN(to.getTime())) return true;
    return from <= range.end && to >= range.start;
}

const draftStatuses = new Set(['draft', 'review']);
const statementStatuses = new Set(['confirmed', 'ready', 'posted']);
const itemSortKey = ref('');
const itemSortDirection = ref('asc');

const visibleStatements = computed(() => {
    const groupedStatementIds = new Set(
        consolidatedStatements.value
            .flatMap((item) => (Array.isArray(item?.statement_ids) ? item.statement_ids : []))
            .map((id) => Number(id))
            .filter((id) => Number.isFinite(id)),
    );
    const items = statements.value.filter((item) => {
        if (activeTab.value === 'draft' && !draftStatuses.has(item.status)) return false;
        if (activeTab.value === 'statement' && !statementStatuses.has(item.status)) return false;
        if (activeTab.value === 'statement' && groupedStatementIds.has(Number(item.id))) return false;
        if (listFilters.value.restaurantId) {
            const restaurantId = Number(listFilters.value.restaurantId);
            if (item.restaurant_id !== restaurantId) return false;
        }
        if (!statementMatchesMonth(item, listFilters.value.month)) return false;
        return true;
    });

    const direction = sortDirection.value === 'asc' ? 1 : -1;
    items.sort((a, b) => {
        let aValue;
        let bValue;
        switch (sortBy.value) {
            case 'date_from':
                aValue = parseDate(a.date_from);
                bValue = parseDate(b.date_from);
                break;
            case 'date_to':
                aValue = parseDate(a.date_to);
                bValue = parseDate(b.date_to);
                break;
            case 'restaurant_name':
                aValue = (a.restaurant_name || '').toLowerCase();
                bValue = (b.restaurant_name || '').toLowerCase();
                break;
            case 'status':
                aValue = statusOrder[a.status] ?? 0;
                bValue = statusOrder[b.status] ?? 0;
                break;
            case 'created_at':
            default:
                aValue = parseDate(a.created_at);
                bValue = parseDate(b.created_at);
                break;
        }
        if (typeof aValue === 'string' || typeof bValue === 'string') {
            return String(aValue).localeCompare(String(bValue), 'ru', { sensitivity: 'base' }) * direction;
        }
        return (Number(aValue) - Number(bValue)) * direction;
    });
    return items;
});

function normalizeConsolidatedStatement(payload) {
    if (!payload) return null;
    const rawIds = Array.isArray(payload.statement_ids) ? payload.statement_ids : [];
    const orderedIds = [];
    const seen = new Set();
    for (const rawId of rawIds) {
        const id = Number(rawId);
        if (!Number.isFinite(id) || seen.has(id)) continue;
        seen.add(id);
        orderedIds.push(id);
    }
    return { ...payload, statement_ids: orderedIds };
}

const statementById = computed(() => {
    const map = new Map();
    for (const stmt of statements.value) {
        map.set(Number(stmt.id), stmt);
    }
    return map;
});

const visibleConsolidatedStatements = computed(() => {
    if (activeTab.value !== 'statement') return [];
    const items = consolidatedStatements.value.filter((item) => {
        if (!statementMatchesMonth(item, listFilters.value.month)) return false;
        if (listFilters.value.restaurantId) {
            const restaurantId = Number(listFilters.value.restaurantId);
            const ids = Array.isArray(item.statement_ids) ? item.statement_ids : [];
            const hasRestaurant = ids.some((id) => {
                const stmt = statementById.value.get(Number(id));
                return stmt?.restaurant_id === restaurantId;
            });
            if (!hasRestaurant) return false;
        }
        return true;
    });
    items.sort((a, b) => parseDate(b.created_at) - parseDate(a.created_at));
    return items;
});

const visibleCards = computed(() => {
    const statementCards = visibleStatements.value.map((item) => ({ kind: 'statement', ...item }));
    if (activeTab.value !== 'statement') return statementCards;
    const consolidatedCards = visibleConsolidatedStatements.value.map((item) => ({ kind: 'consolidated', ...item }));
    return [...consolidatedCards, ...statementCards];
});

const consolidatedStatementsInCurrent = computed(() => {
    const group = currentConsolidated.value;
    if (!group) return [];
    const ids = Array.isArray(group.statement_ids) ? group.statement_ids : [];
    return ids.map((rawId) => {
        const id = Number(rawId);
        const stmt = statementById.value.get(id);
        if (stmt) return { ...stmt, missing: false };
        return {
            id,
            missing: true,
            restaurant_name: null,
            date_from: group.date_from,
            date_to: group.date_to,
            status: null,
        };
    });
});

let consolidatedTotalsRunId = 0;
let consolidatedHistogramRunId = 0;

async function loadConsolidatedTotals() {
    const group = currentConsolidated.value;
    if (!group) return;

    const runId = (consolidatedTotalsRunId += 1);
    const groupId = Number(group.id);

    const rawIds = Array.isArray(group.statement_ids) ? group.statement_ids : [];
    const ids = [];
    const seen = new Set();
    for (const rawId of rawIds) {
        const id = Number(rawId);
        if (!Number.isFinite(id) || seen.has(id)) continue;
        seen.add(id);
        ids.push(id);
    }

    consolidatedTotalsLoading.value = true;
    consolidatedTotalsError.value = '';
    consolidatedTotalsWarning.value = '';
    consolidatedStatementTotals.value = {};
    consolidatedTotals.value = {
        statement_count: ids.length,
        loaded_statement_count: 0,
        row_count: 0,
        accrual_total: 0,
        deduction_total: 0,
        final_total: 0,
        accrual_rows_count: 0,
        deduction_rows_count: 0,
    };

    try {
        const payload = await fetchAdvanceStatementTotals(ids);
        if (runId !== consolidatedTotalsRunId) return;

        const rows = Array.isArray(payload?.items) ? payload.items : [];
        const missingIds = Array.isArray(payload?.missing_ids)
            ? payload.missing_ids.map((value) => Number(value)).filter((value) => Number.isFinite(value))
            : [];

        const perStatement = {};
        let loadedCount = 0;
        let rowCount = 0;
        let accrualTotal = 0;
        let deductionTotal = 0;
        let finalTotal = 0;
        let accrualRows = 0;
        let deductionRows = 0;

        for (const row of rows) {
            const stmtId = Number(row?.statement_id);
            if (!Number.isFinite(stmtId)) continue;
            const totals = {
                row_count: Number(row?.row_count ?? 0) || 0,
                accrual_total: quantizeMoney(Number(row?.accrual_total ?? 0) || 0),
                deduction_total: quantizeMoney(Number(row?.deduction_total ?? 0) || 0),
                final_total: quantizeMoney(Number(row?.final_total ?? 0) || 0),
                accrual_rows_count: Number(row?.accrual_rows_count ?? 0) || 0,
                deduction_rows_count: Number(row?.deduction_rows_count ?? 0) || 0,
            };
            perStatement[String(stmtId)] = totals;
            loadedCount += 1;
            rowCount += totals.row_count;
            accrualTotal += totals.accrual_total;
            deductionTotal += totals.deduction_total;
            finalTotal += totals.final_total;
            accrualRows += totals.accrual_rows_count;
            deductionRows += totals.deduction_rows_count;
        }

        if (runId !== consolidatedTotalsRunId) return;
        if (!showConsolidatedStatementModal.value || Number(currentConsolidated.value?.id) !== groupId) return;

        consolidatedStatementTotals.value = perStatement;
        consolidatedTotals.value = {
            statement_count: ids.length,
            loaded_statement_count: loadedCount,
            row_count: rowCount,
            accrual_total: quantizeMoney(accrualTotal),
            deduction_total: quantizeMoney(deductionTotal),
            final_total: quantizeMoney(finalTotal),
            accrual_rows_count: accrualRows,
            deduction_rows_count: deductionRows,
        };

        if (missingIds.length) {
            consolidatedTotalsWarning.value = `Не удалось загрузить итоги по ведомостям: № ${missingIds.join(', ')}`;
        }
    } catch (error) {
        const detail = error?.response?.data?.detail;
        consolidatedTotalsError.value = detail || 'Не удалось посчитать итоги';
        console.error(error);
    } finally {
        if (runId === consolidatedTotalsRunId) {
            consolidatedTotalsLoading.value = false;
        }
    }
}

function normalizeText(value) {
    return String(value ?? '').trim().toLowerCase();
}

function getConsolidatedSubdivisionHistogramKey(row) {
    return `name:${normalizeText(row?.subdivision_name || 'Без подразделения')}`;
}

function getConsolidatedPositionHistogramKey(position) {
    return `name:${normalizeText(position?.position_name || 'Без должности')}`;
}

async function loadConsolidatedHistogram() {
    consolidatedHistogramRows.value = [];
    consolidatedHistogramError.value = '';
    consolidatedHistogramSubdivisionKey.value = '';

    const group = currentConsolidated.value;
    if (!group) {
        consolidatedHistogramLoading.value = false;
        return;
    }

    const rawIds = Array.isArray(group.statement_ids) ? group.statement_ids : [];
    const ids = [];
    const seen = new Set();
    for (const rawId of rawIds) {
        const id = Number(rawId);
        if (!Number.isFinite(id) || seen.has(id)) continue;
        seen.add(id);
        ids.push(id);
    }
    if (!ids.length) {
        consolidatedHistogramLoading.value = false;
        return;
    }

    const runId = (consolidatedHistogramRunId += 1);
    const groupId = Number(group.id);
    consolidatedHistogramLoading.value = true;

    try {
        const statementsPayload = await Promise.all(ids.map(async (id) => {
            try {
                return await fetchAdvanceStatement(id);
            } catch (error) {
                if (Number(error?.response?.status) === 404) {
                    return null;
                }
                throw error;
            }
        }));
        if (runId !== consolidatedHistogramRunId) return;
        if (!showConsolidatedStatementModal.value || Number(currentConsolidated.value?.id) !== groupId) return;

        const subdivisionMap = new Map();

        for (const statement of statementsPayload) {
            if (!statement || !Array.isArray(statement.items)) continue;
            const statementKind = statement.statement_kind;
            for (const item of statement.items) {
                const subdivisionName = String(item?.subdivision_name || '').trim() || 'Без подразделения';
                const positionName = String(item?.position_name || '').trim() || 'Без должности';
                const subdivisionKey = getConsolidatedSubdivisionHistogramKey({ subdivision_name: subdivisionName });
                const positionKey = getConsolidatedPositionHistogramKey({ position_name: positionName });
                const totalAccrued = getItemTotalAccruedValue(item, statementKind);
                const hours = Number(item?.fact_hours ?? 0) || 0;
                const nightHours = Number(item?.night_hours ?? 0) || 0;
                const accrualAmount = Number(item?.accrual_amount ?? 0) || 0;
                const deductionAmount = Number(item?.deduction_amount ?? 0) || 0;

                if (!subdivisionMap.has(subdivisionKey)) {
                    subdivisionMap.set(subdivisionKey, {
                        subdivision_name: subdivisionName,
                        hours: 0,
                        night_hours: 0,
                        accrual_amount: 0,
                        deduction_amount: 0,
                        total_cost: 0,
                        row_count: 0,
                        positions: new Map(),
                    });
                }
                const subdivisionEntry = subdivisionMap.get(subdivisionKey);
                subdivisionEntry.hours += hours;
                subdivisionEntry.night_hours += nightHours;
                subdivisionEntry.accrual_amount += accrualAmount;
                subdivisionEntry.deduction_amount += deductionAmount;
                subdivisionEntry.total_cost += totalAccrued;
                subdivisionEntry.row_count += 1;

                if (!subdivisionEntry.positions.has(positionKey)) {
                    subdivisionEntry.positions.set(positionKey, {
                        position_name: positionName,
                        hours: 0,
                        night_hours: 0,
                        accrual_amount: 0,
                        deduction_amount: 0,
                        total_cost: 0,
                        row_count: 0,
                    });
                }
                const positionEntry = subdivisionEntry.positions.get(positionKey);
                positionEntry.hours += hours;
                positionEntry.night_hours += nightHours;
                positionEntry.accrual_amount += accrualAmount;
                positionEntry.deduction_amount += deductionAmount;
                positionEntry.total_cost += totalAccrued;
                positionEntry.row_count += 1;
            }
        }

        consolidatedHistogramRows.value = Array.from(subdivisionMap.values())
            .map((subdivision) => ({
                subdivision_name: subdivision.subdivision_name,
                hours: quantizeMoney(subdivision.hours),
                night_hours: quantizeMoney(subdivision.night_hours),
                accrual_amount: quantizeMoney(subdivision.accrual_amount),
                deduction_amount: quantizeMoney(subdivision.deduction_amount),
                total_cost: quantizeMoney(subdivision.total_cost),
                row_count: subdivision.row_count,
                positions: Array.from(subdivision.positions.values())
                    .map((position) => ({
                        position_name: position.position_name,
                        hours: quantizeMoney(position.hours),
                        night_hours: quantizeMoney(position.night_hours),
                        accrual_amount: quantizeMoney(position.accrual_amount),
                        deduction_amount: quantizeMoney(position.deduction_amount),
                        total_cost: quantizeMoney(position.total_cost),
                        row_count: position.row_count,
                    }))
                    .sort((a, b) => b.total_cost - a.total_cost),
            }))
            .sort((a, b) => b.total_cost - a.total_cost);
    } catch (error) {
        const detail = error?.response?.data?.detail;
        consolidatedHistogramError.value = detail || 'Не удалось загрузить гистограмму общей ведомости.';
        console.error(error);
    } finally {
        if (runId === consolidatedHistogramRunId) {
            consolidatedHistogramLoading.value = false;
        }
    }
}

const consolidatedHistogramSelectedSubdivision = computed(() => {
    if (!consolidatedHistogramSubdivisionKey.value) return null;
    return (
        consolidatedHistogramRows.value.find(
            (row) => getConsolidatedSubdivisionHistogramKey(row) === consolidatedHistogramSubdivisionKey.value,
        ) || null
    );
});

const consolidatedHistogramItems = computed(() => {
    const rows = Array.isArray(consolidatedHistogramRows.value) ? consolidatedHistogramRows.value : [];
    const totalAccruedAll = rows.reduce((acc, row) => acc + Math.max(0, Number(row?.total_cost || 0)), 0);

    if (consolidatedHistogramSelectedSubdivision.value) {
        const subdivision = consolidatedHistogramSelectedSubdivision.value;
        const positions = Array.isArray(subdivision?.positions) ? subdivision.positions : [];
        const parentCost = Math.max(0, Number(subdivision?.total_cost || 0));
        return positions
            .map((position) => {
                const value = Number(position?.total_cost || 0);
                if (value <= 0) return null;
                return {
                    key: `${getConsolidatedSubdivisionHistogramKey(subdivision)}::${getConsolidatedPositionHistogramKey(position)}`,
                    sourceKey: getConsolidatedPositionHistogramKey(position),
                    nodeType: 'position',
                    label: position?.position_name || 'Без должности',
                    value,
                    metrics: {
                        hours: Number(position?.hours || 0),
                        night_hours: Number(position?.night_hours || 0),
                        accrual_amount: Number(position?.accrual_amount || 0),
                        deduction_amount: Number(position?.deduction_amount || 0),
                        total_cost: value,
                        row_count: Number(position?.row_count || 0),
                    },
                    sharePercent: totalAccruedAll > 0 ? (value / totalAccruedAll) * 100 : 0,
                    shareInParentPercent: parentCost > 0 ? (value / parentCost) * 100 : 0,
                };
            })
            .filter(Boolean)
            .sort((a, b) => b.value - a.value);
    }

    return rows
        .map((row) => {
            const value = Number(row?.total_cost || 0);
            if (value <= 0) return null;
            return {
                key: getConsolidatedSubdivisionHistogramKey(row),
                sourceKey: getConsolidatedSubdivisionHistogramKey(row),
                nodeType: 'subdivision',
                label: row?.subdivision_name || 'Без подразделения',
                value,
                metrics: {
                    hours: Number(row?.hours || 0),
                    night_hours: Number(row?.night_hours || 0),
                    accrual_amount: Number(row?.accrual_amount || 0),
                    deduction_amount: Number(row?.deduction_amount || 0),
                    total_cost: value,
                    row_count: Number(row?.row_count || 0),
                },
                sharePercent: totalAccruedAll > 0 ? (value / totalAccruedAll) * 100 : 0,
                shareInParentPercent: 100,
            };
        })
        .filter(Boolean)
        .sort((a, b) => b.value - a.value);
});

const consolidatedHistogramSubtitle = computed(() => {
    if (consolidatedHistogramSelectedSubdivision.value) {
        const name = consolidatedHistogramSelectedSubdivision.value?.subdivision_name || 'Без подразделения';
        return `Должности подразделения «${name}» по итогу начислено во всей компании.`;
    }
    return 'Подразделения всей компании по итогу начислено. Кликни столбец для детализации должностей.';
});

const consolidatedHistogramOption = computed(() => {
    const items = consolidatedHistogramItems.value;
    if (!items.length) return null;
    const maxValue = Math.max(...items.map((item) => Number(item.value || 0)), 0);

    return {
        animationDuration: 220,
        grid: {
            left: 230,
            right: 26,
            top: 12,
            bottom: 18,
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
                const title = escapeHtml(node?.label || '—');
                const typeLabel = node?.nodeType === 'position' ? 'Должность' : 'Подразделение';
                const lines = [
                    `<div style="font-weight:700;font-size:13px;margin-bottom:6px;">${title}</div>`,
                    `<div style="opacity:.9;margin-bottom:6px;">${typeLabel}</div>`,
                    `<div><span style="opacity:.75;">Итого начислено:</span> <b>${escapeHtml(`${formatMoney(node?.value || 0)} ₽`)}</b></div>`,
                    `<div><span style="opacity:.75;">Часы:</span> <b>${escapeHtml(formatNumber(metrics?.hours || 0))}</b></div>`,
                    `<div><span style="opacity:.75;">Ночные:</span> <b>${escapeHtml(formatNumber(metrics?.night_hours || 0))}</b></div>`,
                    `<div><span style="opacity:.75;">Начисления:</span> <b>${escapeHtml(`${formatMoney(metrics?.accrual_amount || 0)} ₽`)}</b></div>`,
                    `<div><span style="opacity:.75;">Удержания:</span> <b>${escapeHtml(`${formatMoney(metrics?.deduction_amount || 0)} ₽`)}</b></div>`,
                    `<div><span style="opacity:.75;">Строк:</span> <b>${escapeHtml(String(metrics?.row_count || 0))}</b></div>`,
                    `<div><span style="opacity:.75;">Доля общей суммы:</span> <b>${escapeHtml(formatPercent((Number(node?.sharePercent || 0)) / 100))}</b></div>`,
                ];
                if (node?.nodeType === 'position') {
                    lines.push(`<div><span style="opacity:.75;">Доля в подразделении:</span> <b>${escapeHtml(formatPercent((Number(node?.shareInParentPercent || 0)) / 100))}</b></div>`);
                }
                return lines.join('');
            },
        },
        xAxis: {
            type: 'value',
            max: maxValue > 0 ? maxValue * 1.12 : undefined,
            axisLabel: {
                color: '#b8b3a9',
                formatter: (value) => `${formatMoney(value)} ₽`,
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
                width: 210,
                overflow: 'truncate',
            },
        },
        series: [
            {
                type: 'bar',
                data: items.map((item) => ({
                    ...item,
                    itemStyle: {
                        color: 'rgba(212, 163, 115, 0.72)',
                        borderRadius: [6, 6, 6, 6],
                    },
                })),
                barMaxWidth: 28,
                label: {
                    show: true,
                    position: 'right',
                    color: '#d8d3c9',
                    formatter: ({ data }) => formatPercent((Number(data?.sharePercent || 0)) / 100),
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

function handleConsolidatedHistogramClick(params) {
    if (consolidatedHistogramSelectedSubdivision.value) {
        return;
    }
    const sourceKey = String(params?.data?.sourceKey || '');
    if (!sourceKey) return;
    const row = consolidatedHistogramRows.value.find(
        (item) => getConsolidatedSubdivisionHistogramKey(item) === sourceKey,
    );
    if (!row || !Array.isArray(row?.positions) || !row.positions.length) {
        return;
    }
    consolidatedHistogramSubdivisionKey.value = sourceKey;
}

function resetConsolidatedHistogramDrilldown() {
    consolidatedHistogramSubdivisionKey.value = '';
}

function getItemSortValue(item, key) {
    const statementKind = currentStatement.value?.statement_kind;
    switch (key) {
        case 'full_name':
            return normalizeText(item.full_name);
        case 'position_name':
            return normalizeText(item.position_name);
        case 'fact_hours':
            return Number(item.fact_hours ?? 0);
        case 'night_hours':
            return Number(item.night_hours ?? 0);
        case 'rate':
            return Number(item.rate ?? 0);
        case 'accrual_amount':
            return Number(item.accrual_amount ?? 0);
        case 'deduction_amount':
            return Number(item.deduction_amount ?? 0);
        case 'calculated_amount':
            return Number(item.calculated_amount ?? 0);
        case 'final_amount':
            return Number(item.final_amount ?? 0);
        case 'total_accrued':
            return getItemTotalAccruedValue(item, statementKind);
        case 'comment':
            return normalizeText(item.comment);
        default:
            return 0;
    }
}

const sortedStatementItems = computed(() => {
    const baseItems = currentStatement.value?.items ?? [];
    const items = [...baseItems];
    if (!itemSortKey.value) return items;
    const direction = itemSortDirection.value === 'asc' ? 1 : -1;
    const key = itemSortKey.value;
    items.sort((a, b) => {
        const aValue = getItemSortValue(a, key);
        const bValue = getItemSortValue(b, key);
        if (typeof aValue === 'string' || typeof bValue === 'string') {
            return String(aValue).localeCompare(String(bValue), 'ru', { sensitivity: 'base' }) * direction;
        }
        return (Number(aValue) - Number(bValue)) * direction;
    });
    return items;
});

const statementTotals = computed(() => {
    const totals = {
        row_count: 0,
        fact_hours: 0,
        night_hours: 0,
        accrual_amount: 0,
        deduction_amount: 0,
        calculated_amount: 0,
        total_accrued: 0,
        final_amount: 0,
    };
    const statementKind = currentStatement.value?.statement_kind;
    for (const item of sortedStatementItems.value) {
        totals.row_count += 1;
        totals.fact_hours += Number(item?.fact_hours ?? 0) || 0;
        totals.night_hours += Number(item?.night_hours ?? 0) || 0;
        totals.accrual_amount += Number(item?.accrual_amount ?? 0) || 0;
        totals.deduction_amount += Number(item?.deduction_amount ?? 0) || 0;
        totals.calculated_amount += Number(item?.calculated_amount ?? 0) || 0;
        totals.total_accrued += getItemTotalAccruedValue(item, statementKind);
        totals.final_amount += Number(item?.final_amount ?? 0) || 0;
    }
    totals.fact_hours = quantizeMoney(totals.fact_hours);
    totals.night_hours = quantizeMoney(totals.night_hours);
    totals.accrual_amount = quantizeMoney(totals.accrual_amount);
    totals.deduction_amount = quantizeMoney(totals.deduction_amount);
    totals.calculated_amount = quantizeMoney(totals.calculated_amount);
    totals.total_accrued = quantizeMoney(totals.total_accrued);
    totals.final_amount = quantizeMoney(totals.final_amount);
    return totals;
});

const isSalaryStatement = computed(
    () => String(currentStatement.value?.statement_kind || '').toLowerCase() === 'salary',
);

const hasStatementAdjustmentSummaries = computed(
    () => Boolean(currentStatement.value) && Array.isArray(currentStatement.value?.adjustment_summaries),
);

const statementAdjustmentSummaries = computed(() => (
    Array.isArray(currentStatement.value?.adjustment_summaries)
        ? currentStatement.value.adjustment_summaries
        : []
));

const statementVisibleAdjustmentSummaries = computed(() => (
    statementAdjustmentSummaries.value.filter((item) => Boolean(item?.show_in_report))
));

function sumStatementAdjustmentSummaries(kind) {
    return quantizeMoney(
        statementVisibleAdjustmentSummaries.value.reduce((acc, item) => {
            if (String(item?.kind || '').toLowerCase() !== kind) {
                return acc;
            }
            return acc + (Number(item?.amount ?? 0) || 0);
        }, 0),
    );
}

function isAdvanceAdjustmentSummary(item) {
    return String(item?.kind || '').toLowerCase() === 'deduction' && Boolean(item?.is_advance);
}

const canViewLaborSummaryCost = computed(
    () =>
        userStore.hasPermission('labor.summary.view')
        && userStore.hasPermission('labor.summary.dashboard.view')
        && userStore.hasPermission('labor.summary.view_cost'),
);

function getStatementSubdivisionHistogramKey(row) {
    const id = Number(row?.subdivision_id);
    if (Number.isFinite(id)) return `id:${id}`;
    return `name:${String(row?.subdivision_name || '').trim().toLowerCase()}`;
}

function getStatementPositionHistogramKey(position) {
    const id = Number(position?.position_id);
    if (Number.isFinite(id)) return `id:${id}`;
    return `name:${String(position?.position_name || '').trim().toLowerCase()}`;
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

async function loadStatementHistogram() {
    statementHistogramRows.value = [];
    statementHistogramError.value = '';
    statementHistogramSubdivisionKey.value = '';
    statementHistogramTotals.value = null;

    if (!isSalaryStatement.value) {
        statementHistogramLoading.value = false;
        return;
    }
    if (!canViewLaborSummaryCost.value) {
        statementHistogramLoading.value = false;
        statementHistogramError.value = 'Нет доступа к данным ФОТ для построения гистограммы.';
        return;
    }

    const restaurantId = Number(currentStatement.value?.restaurant_id);
    const dateFrom = currentStatement.value?.date_from;
    const dateTo = currentStatement.value?.date_to;
    if (!Number.isFinite(restaurantId) || !dateFrom || !dateTo) {
        statementHistogramLoading.value = false;
        statementHistogramError.value = 'Недостаточно данных ведомости для построения гистограммы.';
        return;
    }

    statementHistogramLoading.value = true;
    try {
        const data = await fetchLaborSummary({
            restaurant_id: restaurantId,
            date_from: dateFrom,
            date_to: dateTo,
            include_positions: true,
        });
        statementHistogramTotals.value = {
            total_cost: quantizeMoney(Number(data?.totals?.total_cost ?? 0) || 0),
            revenue_amount: quantizeMoney(Number(data?.totals?.revenue_amount ?? 0) || 0),
        };

        const subdivisions = Array.isArray(data?.subdivisions) ? data.subdivisions : [];
        statementHistogramRows.value = subdivisions.map((subdivision) => {
            const positions = Array.isArray(subdivision?.positions) ? subdivision.positions : [];
            return {
                subdivision_id: Number.isFinite(Number(subdivision?.subdivision_id))
                    ? Number(subdivision?.subdivision_id)
                    : null,
                subdivision_name: subdivision?.subdivision_name || 'Без подразделения',
                hours: quantizeMoney(Number(subdivision?.hours ?? 0) || 0),
                night_hours: quantizeMoney(Number(subdivision?.night_hours ?? 0) || 0),
                accrual_amount: quantizeMoney(Number(subdivision?.accrual_amount ?? 0) || 0),
                deduction_amount: quantizeMoney(Number(subdivision?.deduction_amount ?? 0) || 0),
                total_cost: quantizeMoney(Number(subdivision?.total_cost ?? 0) || 0),
                positions: positions.map((position) => ({
                    position_id: Number.isFinite(Number(position?.position_id)) ? Number(position?.position_id) : null,
                    position_name: position?.position_name || 'Без должности',
                    hours: quantizeMoney(Number(position?.hours ?? 0) || 0),
                    night_hours: quantizeMoney(Number(position?.night_hours ?? 0) || 0),
                    accrual_amount: quantizeMoney(Number(position?.accrual_amount ?? 0) || 0),
                    deduction_amount: quantizeMoney(Number(position?.deduction_amount ?? 0) || 0),
                    total_cost: quantizeMoney(Number(position?.total_cost ?? 0) || 0),
                })),
            };
        });

        const keys = statementHistogramRows.value.map((row) => getStatementSubdivisionHistogramKey(row));
        if (statementHistogramSubdivisionKey.value && !keys.includes(statementHistogramSubdivisionKey.value)) {
            statementHistogramSubdivisionKey.value = '';
        }
    } catch (error) {
        const detail = error?.response?.data?.detail;
        statementHistogramError.value = detail || 'Не удалось загрузить гистограмму по настройкам ФОТ.';
        statementHistogramTotals.value = null;
        console.error(error);
    } finally {
        statementHistogramLoading.value = false;
    }
}

const statementHistogramSelectedSubdivision = computed(() => {
    if (!statementHistogramSubdivisionKey.value) return null;
    return (
        statementHistogramRows.value.find(
            (row) => getStatementSubdivisionHistogramKey(row) === statementHistogramSubdivisionKey.value,
        ) || null
    );
});

const statementHistogramItems = computed(() => {
    const rows = Array.isArray(statementHistogramRows.value) ? statementHistogramRows.value : [];
    const totalCostAll = rows.reduce((acc, row) => acc + Math.max(0, Number(row?.total_cost || 0)), 0);

    if (statementHistogramSelectedSubdivision.value) {
        const subdivision = statementHistogramSelectedSubdivision.value;
        const positions = Array.isArray(subdivision?.positions) ? subdivision.positions : [];
        const parentCost = Math.max(0, Number(subdivision?.total_cost || 0));
        return positions
            .map((position) => {
                const value = Number(position?.total_cost || 0);
                if (value <= 0) return null;
                return {
                    key: `${getStatementSubdivisionHistogramKey(subdivision)}::${getStatementPositionHistogramKey(position)}`,
                    sourceKey: getStatementPositionHistogramKey(position),
                    nodeType: 'position',
                    label: position?.position_name || 'Без должности',
                    value,
                    metrics: {
                        hours: Number(position?.hours || 0),
                        night_hours: Number(position?.night_hours || 0),
                        accrual_amount: Number(position?.accrual_amount || 0),
                        deduction_amount: Number(position?.deduction_amount || 0),
                        total_cost: value,
                    },
                    sharePercent: totalCostAll > 0 ? (value / totalCostAll) * 100 : 0,
                    shareInParentPercent: parentCost > 0 ? (value / parentCost) * 100 : 0,
                };
            })
            .filter(Boolean)
            .sort((a, b) => b.value - a.value);
    }

    return rows
        .map((row) => {
            const value = Number(row?.total_cost || 0);
            if (value <= 0) return null;
            return {
                key: getStatementSubdivisionHistogramKey(row),
                sourceKey: getStatementSubdivisionHistogramKey(row),
                nodeType: 'subdivision',
                label: row?.subdivision_name || 'Без подразделения',
                value,
                metrics: {
                    hours: Number(row?.hours || 0),
                    night_hours: Number(row?.night_hours || 0),
                    accrual_amount: Number(row?.accrual_amount || 0),
                    deduction_amount: Number(row?.deduction_amount || 0),
                    total_cost: value,
                },
                sharePercent: totalCostAll > 0 ? (value / totalCostAll) * 100 : 0,
                shareInParentPercent: 100,
            };
        })
        .filter(Boolean)
        .sort((a, b) => b.value - a.value);
});

const statementHistogramSubtitle = computed(() => {
    if (statementHistogramSelectedSubdivision.value) {
        const name = statementHistogramSelectedSubdivision.value?.subdivision_name || 'Без подразделения';
        return `Должности подразделения «${name}» по факту затрат.`;
    }
    return 'Подразделения по факту затрат. Кликни столбец для детализации должностей.';
});

const statementHistogramOption = computed(() => {
    const items = statementHistogramItems.value;
    if (!items.length) return null;
    const maxValue = Math.max(...items.map((item) => Number(item.value || 0)), 0);

    return {
        animationDuration: 220,
        grid: {
            left: 230,
            right: 26,
            top: 12,
            bottom: 18,
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
                const title = escapeHtml(node?.label || '—');
                const typeLabel = node?.nodeType === 'position' ? 'Должность' : 'Подразделение';
                const lines = [
                    `<div style="font-weight:700;font-size:13px;margin-bottom:6px;">${title}</div>`,
                    `<div style="opacity:.9;margin-bottom:6px;">${typeLabel}</div>`,
                    `<div><span style="opacity:.75;">Факт затрат:</span> <b>${escapeHtml(`${formatMoney(node?.value || 0)} ₽`)}</b></div>`,
                    `<div><span style="opacity:.75;">Часы:</span> <b>${escapeHtml(formatNumber(metrics?.hours || 0))}</b></div>`,
                    `<div><span style="opacity:.75;">Ночные:</span> <b>${escapeHtml(formatNumber(metrics?.night_hours || 0))}</b></div>`,
                    `<div><span style="opacity:.75;">Начисления:</span> <b>${escapeHtml(`${formatMoney(metrics?.accrual_amount || 0)} ₽`)}</b></div>`,
                    `<div><span style="opacity:.75;">Удержания:</span> <b>${escapeHtml(`${formatMoney(metrics?.deduction_amount || 0)} ₽`)}</b></div>`,
                    `<div><span style="opacity:.75;">Доля ФОТ (общая):</span> <b>${escapeHtml(formatPercent((Number(node?.sharePercent || 0)) / 100))}</b></div>`,
                ];
                if (node?.nodeType === 'position') {
                    lines.push(`<div><span style="opacity:.75;">Доля в подразделении:</span> <b>${escapeHtml(formatPercent((Number(node?.shareInParentPercent || 0)) / 100))}</b></div>`);
                }
                return lines.join('');
            },
        },
        xAxis: {
            type: 'value',
            max: maxValue > 0 ? maxValue * 1.12 : undefined,
            axisLabel: {
                color: '#b8b3a9',
                formatter: (value) => `${formatMoney(value)} ₽`,
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
                width: 210,
                overflow: 'truncate',
            },
        },
        series: [
            {
                type: 'bar',
                data: items.map((item) => ({
                    ...item,
                    itemStyle: {
                        color: 'rgba(212, 163, 115, 0.72)',
                        borderRadius: [6, 6, 6, 6],
                    },
                })),
                barMaxWidth: 28,
                label: {
                    show: true,
                    position: 'right',
                    color: '#d8d3c9',
                    formatter: ({ data }) => formatPercent((Number(data?.sharePercent || 0)) / 100),
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

function handleStatementHistogramClick(params) {
    if (statementHistogramSelectedSubdivision.value) {
        return;
    }
    const sourceKey = String(params?.data?.sourceKey || '');
    if (!sourceKey) return;
    const row = statementHistogramRows.value.find(
        (item) => getStatementSubdivisionHistogramKey(item) === sourceKey,
    );
    if (!row || !Array.isArray(row?.positions) || !row.positions.length) {
        return;
    }
    statementHistogramSubdivisionKey.value = sourceKey;
}

function resetStatementHistogramDrilldown() {
    statementHistogramSubdivisionKey.value = '';
}

const statementSummaryAccrualAmount = computed(() => {
    if (!hasStatementAdjustmentSummaries.value) {
        return quantizeMoney(Number(statementTotals.value.accrual_amount ?? 0) || 0);
    }
    return sumStatementAdjustmentSummaries('accrual');
});

const statementSummaryDeductionAmount = computed(() => {
    if (!hasStatementAdjustmentSummaries.value) {
        return quantizeMoney(Math.abs(Number(statementTotals.value.deduction_amount ?? 0) || 0));
    }
    return sumStatementAdjustmentSummaries('deduction');
});

const statementAdvanceDeductionAmount = computed(() => {
    if (!hasStatementAdjustmentSummaries.value) {
        return 0;
    }
    return quantizeMoney(
        statementVisibleAdjustmentSummaries.value.reduce((acc, item) => {
            if (!isAdvanceAdjustmentSummary(item)) {
                return acc;
            }
            return acc + (Number(item?.amount ?? 0) || 0);
        }, 0),
    );
});

const showAdvanceSummaryCard = computed(() => {
    if (!currentStatement.value) return false;
    if (String(currentStatement.value.statement_kind || '').toLowerCase() !== 'salary') return false;
    return statementAdvanceDeductionAmount.value > 0;
});

const showStatementFotSummaryCards = computed(
    () => isSalaryStatement.value && canViewLaborSummaryCost.value,
);

const statementFotRevenueAmount = computed(() => (
    Number(statementHistogramTotals.value?.revenue_amount ?? 0) || 0
));

const statementFotAccruedAmount = computed(() => (
    Number(statementTotals.value?.total_accrued ?? 0) || 0
));

const statementFotShareValue = computed(() => {
    if (statementFotRevenueAmount.value <= 0) return null;
    return statementFotAccruedAmount.value / statementFotRevenueAmount.value;
});

const statementFotRevenueAmountLabel = computed(() => {
    if (statementHistogramTotals.value) {
        return `${formatMoney(statementFotRevenueAmount.value)} ₽`;
    }
    if (statementHistogramLoading.value) {
        return 'Загружаем...';
    }
    return '—';
});

const statementFotAccruedAmountLabel = computed(() => `${formatMoney(statementFotAccruedAmount.value)} ₽`);

const statementFotShareLabel = computed(() => {
    if (!statementHistogramTotals.value && statementHistogramLoading.value) {
        return 'Загружаем...';
    }
    if (statementFotShareValue.value === null) {
        return '—';
    }
    return formatPercent(statementFotShareValue.value);
});

const statementStaffCodeNameMap = computed(() => {
    const map = new Map();
    for (const item of currentStatement.value?.items || []) {
        const code = String(item?.staff_code || '').trim();
        if (!code || map.has(code)) continue;
        map.set(code, item?.full_name || '');
    }
    return map;
});

const postResultRows = computed(() =>
    (postResult.value.rows || []).map((row) => ({
        ...row,
        fullName: row.fullName || statementStaffCodeNameMap.value.get(row.staffCode) || '',
    })),
);

function toggleItemSort(key) {
    if (itemSortKey.value === key) {
        itemSortDirection.value = itemSortDirection.value === 'asc' ? 'desc' : 'asc';
        return;
    }
    itemSortKey.value = key;
    itemSortDirection.value = 'asc';
}

function isItemSortActive(key) {
    return itemSortKey.value === key;
}

function itemSortIndicator(key) {
    if (!isItemSortActive(key)) return '';
    return itemSortDirection.value === 'asc' ? '▲' : '▼';
}

function getItemAriaSort(key) {
    if (!isItemSortActive(key)) return 'none';
    return itemSortDirection.value === 'asc' ? 'ascending' : 'descending';
}

function setStatementViewTab(tab) {
    const nextTab = tab === 'histogram' ? 'histogram' : 'table';
    statementViewTab.value = nextTab;
    if (
        nextTab === 'histogram'
        && isSalaryStatement.value
        && !statementHistogramLoading.value
        && !statementHistogramRows.value.length
        && !statementHistogramError.value
    ) {
        void loadStatementHistogram();
    }
}


const consolidatedCandidates = computed(() =>
    visibleStatements.value.filter((item) => statementStatuses.has(item.status)),
);
const consolidatedCandidateIds = computed(() =>
    consolidatedCandidates.value
        .map((item) => Number(item.id))
        .filter((id) => Number.isFinite(id)),
);
const consolidatedSelectedIdSet = computed(() => new Set(consolidatedSelectedIds.value));
const consolidatedSelectedCount = computed(() =>
    consolidatedCandidateIds.value.filter((id) => consolidatedSelectedIdSet.value.has(id)).length,
);
const hasConsolidatedCandidates = computed(() => consolidatedCandidateIds.value.length > 0);
const isAllConsolidatedSelected = computed(
    () => hasConsolidatedCandidates.value && consolidatedSelectedCount.value === consolidatedCandidateIds.value.length,
);

const restaurantFilterOptions = computed(() => [
    { label: 'Все рестораны', value: '' },
    ...restaurantOptions.value,
]);

const activeTabLabel = computed(() => (activeTab.value === 'draft' ? 'Черновики' : 'Ведомости'));
const emptyListLabel = computed(() => (activeTab.value === 'draft' ? 'Черновиков пока нет.' : 'Ведомостей пока нет.'));
const sortDirectionLabel = computed(() => (sortDirection.value === 'asc' ? 'По возрастанию' : 'По убыванию'));
const currentStatementLabel = computed(() => {
    if (!currentStatement.value) return 'Черновик';
    return statementStatuses.has(currentStatement.value.status) ? 'Ведомость' : 'Черновик';
});

function toggleSortDirection() {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
}

const canCreate = computed(() => userStore.hasPermission('payroll.advance.create'));
const canEdit = computed(() => userStore.hasPermission('payroll.advance.edit'));
const canDownload = computed(() =>
    userStore.hasPermission('payroll.advance.download') || userStore.hasPermission('payroll.export'),
);
const canRefresh = computed(() => {
    if (!currentStatement.value) return false;
    return canEdit.value && !['ready', 'posted'].includes(currentStatement.value.status);
});
const canEditItem = computed(() => {
    if (!currentStatement.value) return false;
    return canEdit.value && ['draft', 'review'].includes(currentStatement.value.status);
});

const canPost = computed(() => {
    if (!currentStatement.value) return false;
    return userStore.hasPermission('payroll.advance.post') && ['ready', 'confirmed'].includes(currentStatement.value.status);
});

const canDelete = computed(() => {
    if (!currentStatement.value) return false;
    if (userStore.hasPermission('payroll.advance.delete')) return true;
    return canEdit.value && currentStatement.value.status !== 'posted';
});

function canChangeStatus(target) {
    if (!currentStatement.value) return false;
    if (userStore.hasPermission('payroll.advance.status.all')) return true;
    const map = {
        review: 'payroll.advance.status.review',
        confirmed: 'payroll.advance.status.confirm',
        ready: 'payroll.advance.status.ready',
        posted: 'payroll.advance.post',
        draft: 'payroll.advance.edit',
    };
    const code = map[target];
    return Boolean(code && userStore.hasPermission(code));
}

const statusWorkflowOptions = [
    { value: 'draft', label: 'Черновик' },
    { value: 'review', label: 'На проверку' },
    { value: 'confirmed', label: 'Подтвержден' },
    { value: 'ready', label: 'Готов к выдаче' },
];

const statusSelectOptions = computed(() => {
    const status = currentStatement.value?.status;
    if (status === 'posted') {
        return [...statusWorkflowOptions, { value: 'posted', label: 'Записан' }];
    }
    return statusWorkflowOptions;
});

function statusLabel(value) {
    const map = {
        draft: 'Черновик',
        review: 'На проверку',
        confirmed: 'Подтвержден',
        ready: 'Готов к выдаче',
        posted: 'Записан',
    };
    return map[value] || value;
}

function canTransitionToStatus(targetStatus) {
    const currentStatus = currentStatement.value?.status;
    if (!currentStatus || !targetStatus || targetStatus === currentStatus) return false;
    if (!canChangeStatus(targetStatus)) return false;
    if (targetStatus === 'draft') return currentStatus !== 'posted';
    if (targetStatus === 'review') return currentStatus === 'draft';
    if (targetStatus === 'confirmed') return ['draft', 'review'].includes(currentStatus);
    if (targetStatus === 'ready') return currentStatus === 'confirmed';
    return false;
}

const canApplySelectedStatus = computed(() => canTransitionToStatus(selectedStatus.value));

function applySelectedStatus() {
    if (!canApplySelectedStatus.value) return;
    void handleChangeStatus(selectedStatus.value);
}

async function loadOptions() {
    try {
        const data = await fetchTimesheetOptions();
        const restaurants = Array.isArray(data?.restaurants) ? data.restaurants : [];
        restaurantOptions.value = restaurants.map((item) => ({
            label: item.name || `Ресторан #${item.id}`,
            value: String(item.id),
        }));
        if (!createForm.value.restaurantId && restaurantOptions.value.length === 1) {
            createForm.value.restaurantId = restaurantOptions.value[0].value;
        }
        if (!listFilters.value.restaurantId && restaurantOptions.value.length === 1) {
            listFilters.value.restaurantId = restaurantOptions.value[0].value;
        }
    } catch (error) {
        toast.error('Не удалось загрузить список ресторанов');
        console.error(error);
    }
}

function defaultDates() {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    createForm.value.dateFrom = `${yyyy}-${mm}-01`;
    createForm.value.dateTo = `${yyyy}-${mm}-${dd}`;
    if (!listFilters.value.month) {
        listFilters.value.month = `${yyyy}-${mm}`;
    }
}

async function loadStatement(id) {
    try {
        const data = await fetchAdvanceStatement(id);
        currentStatement.value = normalizeStatement(data);
        syncStatementList(data);
        if (!statements.value.find((item) => item.id === data.id)) {
            statements.value.unshift(data);
        }
        await loadStatementHistogram();
    } catch (error) {
        toast.error('Не удалось загрузить документ');
        console.error(error);
    }
}

async function openStatementModal(id) {
    await loadStatement(id);
    if (currentStatement.value) {
        statementViewTab.value = 'table';
        showStatementModal.value = true;
    }
}

function closeStatementModal() {
    showEmployeeCardOverlay.value = false;
    removeEmployeeQueryFromRoute();
    pendingItemSaveMap.clear();
    persistedItemFinalAmountMap.clear();
    if (pendingItemSaveTimer) {
        clearTimeout(pendingItemSaveTimer);
        pendingItemSaveTimer = null;
    }
    showStatementModal.value = false;
    currentStatement.value = null;
    statementViewTab.value = 'table';
    statementHistogramRows.value = [];
    statementHistogramError.value = '';
    statementHistogramLoading.value = false;
    statementHistogramSubdivisionKey.value = '';
    statementHistogramTotals.value = null;
}

function normalizeStatement(data) {
    if (!data) return null;
    const items = Array.isArray(data.items) ? data.items.map((item) => ({ ...item })) : [];
    syncPersistedItemFinalAmounts(items);
    return { ...data, items };
}

function syncPersistedItemFinalAmounts(items = []) {
    persistedItemFinalAmountMap.clear();
    for (const item of items) {
        rememberPersistedFinalAmount(item);
    }
}

function rememberPersistedFinalAmount(item) {
    const itemId = Number(item?.id);
    if (!Number.isFinite(itemId)) return;
    const finalAmount = Number(item?.final_amount);
    if (!Number.isFinite(finalAmount)) return;
    persistedItemFinalAmountMap.set(itemId, quantizeMoney(finalAmount));
}

function restorePersistedFinalAmount(item) {
    const itemId = Number(item?.id);
    const persistedValue = persistedItemFinalAmountMap.get(itemId);
    const fallbackValue = Number.isFinite(persistedValue)
        ? Number(persistedValue)
        : quantizeMoney(Number(item?.calculated_amount ?? 0) || 0);
    if (item && typeof item === 'object') {
        item.final_amount = fallbackValue;
    }
    return fallbackValue;
}

function syncStatementList(data) {
    if (!data) return;
    const idx = statements.value.findIndex((item) => item.id === data.id);
    const payload = { ...data };
    if (idx === -1) {
        statements.value.unshift(payload);
    } else {
        statements.value[idx] = { ...statements.value[idx], ...payload };
    }
}

async function loadStatements() {
    try {
        const data = await fetchAdvanceStatements();
        statements.value = Array.isArray(data?.items) ? data.items : [];
    } catch (error) {
        toast.error('Не удалось загрузить список документов');
        console.error(error);
    }
}

async function loadConsolidatedStatementsList() {
    try {
        const data = await fetchAdvanceConsolidatedStatements();
        const items = Array.isArray(data?.items) ? data.items : [];
        consolidatedStatements.value = items
            .map((item) => normalizeConsolidatedStatement(item))
            .filter(Boolean);
    } catch (error) {
        toast.error('Не удалось загрузить общие ведомости');
        console.error(error);
    }
}

function openCreateModal() {
    if (!createForm.value.restaurantId && listFilters.value.restaurantId) {
        createForm.value.restaurantId = listFilters.value.restaurantId;
    }
    if (listFilters.value.month) {
        const range = getMonthRange(listFilters.value.month);
        if (range) {
            const yyyy = range.start.getFullYear();
            const mm = String(range.start.getMonth() + 1).padStart(2, '0');
            const from = `${yyyy}-${mm}-01`;
            const to = `${yyyy}-${mm}-${String(range.end.getDate()).padStart(2, '0')}`;
            createForm.value.dateFrom = from;
            createForm.value.dateTo = to;
        }
    }
    showCreateModal.value = true;
}

function closeCreateModal() {
    showCreateModal.value = false;
}

async function submitCreate() {
    if (!createForm.value.restaurantId || !createForm.value.dateFrom || !createForm.value.dateTo) {
        toast.error('Укажите ресторан и даты');
        return;
    }
    isCreating.value = true;
    try {
        const statementKind = createForm.value.statementKind === 'salary' ? 'salary' : 'advance';
        const salaryPercent =
            statementKind === 'salary' ? 100 : Number(createForm.value.salaryPercent ?? 50);
        const payload = {
            restaurant_id: Number(createForm.value.restaurantId),
            date_from: createForm.value.dateFrom,
            date_to: createForm.value.dateTo,
            statement_kind: statementKind,
            salary_percent: salaryPercent,
        };
        const data = await createAdvanceStatement(payload);
        currentStatement.value = normalizeStatement(data);
        syncStatementList(data);
        await loadStatementHistogram();
        showCreateModal.value = false;
        statementViewTab.value = 'table';
        showStatementModal.value = true;
        toast.success('Черновик ведомости сформирован');
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось сформировать черновик');
        console.error(error);
    } finally {
        isCreating.value = false;
    }
}

async function handleRefresh() {
    if (!currentStatement.value) return;
    isRefreshing.value = true;
    try {
        blurActiveElement();
        await nextTick();
        await ensurePendingItemSavesFlushed();
        const data = await refreshAdvanceStatement(currentStatement.value.id);
        currentStatement.value = normalizeStatement(data);
        syncStatementList(data);
        await loadStatementHistogram();
        toast.success('Расчёты обновлены');
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось обновить расчёты');
        console.error(error);
    } finally {
        isRefreshing.value = false;
    }
}

async function handleChangeStatus(targetStatus) {
    if (!currentStatement.value) return;
    isStatusChanging.value = true;
    try {
        await ensurePendingItemSavesFlushed();
        const data = await changeAdvanceStatus(currentStatement.value.id, { status: targetStatus });
        currentStatement.value = normalizeStatement(data);
        syncStatementList(data);
        toast.success(`Статус сменён на "${statusLabel(targetStatus)}"`);
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось сменить статус');
        console.error(error);
    } finally {
        isStatusChanging.value = false;
    }
}

function applyCompactUpdatedItems(updatedItems = [], meta = {}) {
    if (!currentStatement.value || !Array.isArray(updatedItems) || !updatedItems.length) {
        return;
    }
    const currentItems = Array.isArray(currentStatement.value.items)
        ? currentStatement.value.items
        : [];
    const nextItems = [...currentItems];
    const indexById = new Map(nextItems.map((row, idx) => [Number(row?.id), idx]));
    for (const updatedItem of updatedItems) {
        const idx = indexById.get(Number(updatedItem?.id));
        if (idx === undefined) {
            continue;
        }
        nextItems[idx] = {
            ...nextItems[idx],
            ...updatedItem,
        };
    }
    currentStatement.value = {
        ...currentStatement.value,
        items: nextItems,
        updated_at: meta?.updated_at ?? currentStatement.value.updated_at,
        updated_by_id: meta?.updated_by_id ?? currentStatement.value.updated_by_id,
    };
    syncPersistedItemFinalAmounts(nextItems);
}

async function flushPendingItemSaves() {
    if (pendingItemSaveRequest) {
        return pendingItemSaveRequest;
    }
    if (!currentStatement.value) {
        pendingItemSaveMap.clear();
        return null;
    }
    const statementId = Number(currentStatement.value.id);
    const queued = Array.from(pendingItemSaveMap.values());
    if (!queued.length) {
        return null;
    }
    pendingItemSaveMap.clear();

    pendingItemSaveRequest = (async () => {
        try {
            const response = await updateAdvanceItemsCompact(statementId, queued);
            if (!currentStatement.value || Number(currentStatement.value.id) !== statementId) {
                return;
            }
            applyCompactUpdatedItems(response?.items || [], {
                updated_at: response?.updated_at,
                updated_by_id: response?.updated_by_id,
            });
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось сохранить правки');
            console.error(error);
        } finally {
            pendingItemSaveRequest = null;
            if (pendingItemSaveMap.size) {
                void flushPendingItemSaves();
            }
        }
    })();

    return pendingItemSaveRequest;
}

async function ensurePendingItemSavesFlushed() {
    if (pendingItemSaveTimer) {
        clearTimeout(pendingItemSaveTimer);
        pendingItemSaveTimer = null;
    }
    if (!pendingItemSaveMap.size && !pendingItemSaveRequest) {
        return;
    }
    if (pendingItemSaveRequest) {
        await pendingItemSaveRequest;
        return;
    }
    await flushPendingItemSaves();
}

async function saveItem(item) {
    if (!currentStatement.value || !canEditItem.value) return;
    const itemId = Number(item?.id);
    if (!Number.isFinite(itemId)) return;
    const rawFinalAmount = item?.final_amount;
    if (rawFinalAmount === '' || rawFinalAmount === null || rawFinalAmount === undefined) {
        restorePersistedFinalAmount(item);
        toast.error('Итог к выплате не может быть пустым');
        return;
    }
    const finalAmount = Number(rawFinalAmount);
    if (!Number.isFinite(finalAmount)) {
        restorePersistedFinalAmount(item);
        toast.error('Введите корректную сумму');
        return;
    }

    pendingItemSaveMap.set(itemId, {
        item_id: itemId,
        final_amount: quantizeMoney(finalAmount),
        comment: item.comment,
    });

    if (pendingItemSaveTimer) {
        clearTimeout(pendingItemSaveTimer);
        pendingItemSaveTimer = null;
    }
    pendingItemSaveTimer = setTimeout(() => {
        pendingItemSaveTimer = null;
        void flushPendingItemSaves();
    }, 120);
}

function blurActiveElement() {
    if (typeof document === 'undefined') return;
    const activeElement = document.activeElement;
    if (!activeElement || typeof activeElement.blur !== 'function') return;
    activeElement.blur();
}


function setConsolidatedSelection(ids) {
    const next = [];
    const seen = new Set();
    for (const rawId of ids) {
        const id = Number(rawId);
        if (!Number.isFinite(id) || seen.has(id)) continue;
        seen.add(id);
        next.push(id);
    }
    consolidatedSelectedIds.value = next;
}

function isConsolidatedSelected(id) {
    return consolidatedSelectedIdSet.value.has(Number(id));
}

function openConsolidatedModal() {
    if (!hasConsolidatedCandidates.value) {
        toast.error('\u041d\u0435\u0442 \u0432\u0435\u0434\u043e\u043c\u043e\u0441\u0442\u0435\u0439 \u0434\u043b\u044f \u0441\u0432\u043e\u0434\u043d\u043e\u0433\u043e \u0444\u0430\u0439\u043b\u0430');
        return;
    }
    setConsolidatedSelection(consolidatedCandidateIds.value);
    showConsolidatedModal.value = true;
}

function closeConsolidatedModal() {
    showConsolidatedModal.value = false;
}

function openConsolidatedStatementModal(id) {
    const targetId = Number(id);
    if (!Number.isFinite(targetId)) return;
    const item = consolidatedStatements.value.find((row) => Number(row.id) === targetId);
    if (!item) {
        toast.error('Общая ведомость не найдена');
        return;
    }
    currentConsolidated.value = normalizeConsolidatedStatement(item);
    consolidatedViewTab.value = 'statements';
    showConsolidatedStatementModal.value = true;
}

function closeConsolidatedStatementModal() {
    showConsolidatedStatementModal.value = false;
    currentConsolidated.value = null;
    consolidatedViewTab.value = 'statements';
    consolidatedHistogramRows.value = [];
    consolidatedHistogramError.value = '';
    consolidatedHistogramLoading.value = false;
    consolidatedHistogramSubdivisionKey.value = '';
}

async function openStatementFromConsolidated(id) {
    const targetId = Number(id);
    if (!Number.isFinite(targetId)) return;
    if (statementById.value.has(targetId)) {
        showConsolidatedStatementModal.value = false;
        await openStatementModal(targetId);
    }
}

function toggleConsolidatedSelection(id) {
    const targetId = Number(id);
    if (!Number.isFinite(targetId)) return;
    const set = new Set(consolidatedSelectedIds.value);
    if (set.has(targetId)) {
        set.delete(targetId);
    } else {
        set.add(targetId);
    }
    consolidatedSelectedIds.value = Array.from(set);
}

function toggleConsolidatedSelectAll() {
    if (!hasConsolidatedCandidates.value) return;
    if (isAllConsolidatedSelected.value) {
        consolidatedSelectedIds.value = [];
        return;
    }
    setConsolidatedSelection(consolidatedCandidateIds.value);
}

async function handleConsolidatedCreate() {
    if (!consolidatedSelectedIds.value.length) {
        toast.error('Выберите ведомости');
        return;
    }
    isConsolidatedCreating.value = true;
    try {
        const monthLabel =
            listFilters.value.month ||
            consolidatedCandidates.value[0]?.date_from?.slice(0, 7) ||
            new Date().toISOString().slice(0, 7);
        const data = await createAdvanceConsolidatedStatement({
            statement_ids: consolidatedSelectedIds.value,
            title: `Общая ведомость ${monthLabel}`,
        });
        const consolidated = normalizeConsolidatedStatement(data);
        await loadConsolidatedStatementsList();
        showConsolidatedModal.value = false;
        toast.success('Общая ведомость создана');
        if (consolidated) {
            currentConsolidated.value = consolidated;
            showConsolidatedStatementModal.value = true;
        }
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось создать общую ведомость');
        console.error(error);
    } finally {
        isConsolidatedCreating.value = false;
    }
}

async function handleConsolidatedDownload() {
    if (!consolidatedSelectedIds.value.length) {
        toast.error('\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0432\u0435\u0434\u043e\u043c\u043e\u0441\u0442\u0438');
        return;
    }
    isConsolidatedDownloading.value = true;
    try {
        const payload = await downloadAdvanceConsolidated(consolidatedSelectedIds.value);
        const blob = payload?.blob ?? payload;
        const monthLabel =
            listFilters.value.month ||
            consolidatedCandidates.value[0]?.date_from?.slice(0, 7) ||
            new Date().toISOString().slice(0, 7);
        const fallbackName = buildConsolidatedFileName(monthLabel);
        const filename = ensureXlsxFilename(payload?.filename || fallbackName, fallbackName);
        downloadBlobFile(blob, filename);
        showConsolidatedModal.value = false;
        toast.success('\u0421\u0432\u043e\u0434\u043d\u0430\u044f \u0432\u0435\u0434\u043e\u043c\u043e\u0441\u0442\u044c \u0441\u0444\u043e\u0440\u043c\u0438\u0440\u043e\u0432\u0430\u043d\u0430');
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || '\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u0444\u043e\u0440\u043c\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u0441\u0432\u043e\u0434\u043d\u044b\u0439 \u0444\u0430\u0439\u043b');
        console.error(error);
    } finally {
        isConsolidatedDownloading.value = false;
    }
}

async function handleConsolidatedStatementDownload() {
    if (!currentConsolidated.value) return;
    isConsolidatedStatementDownloading.value = true;
    try {
        const payload = await downloadAdvanceConsolidatedById(currentConsolidated.value.id);
        const blob = payload?.blob ?? payload;
        const monthLabel =
            listFilters.value.month ||
            currentConsolidated.value.date_from?.slice(0, 7) ||
            new Date().toISOString().slice(0, 7);
        const fallbackName = buildConsolidatedStatementFileName(currentConsolidated.value, monthLabel);
        const filename = ensureXlsxFilename(payload?.filename || fallbackName, fallbackName);
        downloadBlobFile(blob, filename);
        toast.success('Сводная ведомость сформирована');
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось скачать файл');
        console.error(error);
    } finally {
        isConsolidatedStatementDownloading.value = false;
    }
}

async function handleConsolidatedStatementDelete() {
    if (!currentConsolidated.value) return;
    const confirmed = window.confirm('Удалить общую ведомость?');
    if (!confirmed) return;
    isConsolidatedStatementDeleting.value = true;
    try {
        await deleteAdvanceConsolidatedStatement(currentConsolidated.value.id);
        toast.success('Общая ведомость удалена');
        showConsolidatedStatementModal.value = false;
        currentConsolidated.value = null;
        await loadConsolidatedStatementsList();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось удалить общую ведомость');
        console.error(error);
    } finally {
        isConsolidatedStatementDeleting.value = false;
    }
}

async function handleDownload() {
    if (!currentStatement.value) return;
    isDownloading.value = true;
    try {
        const payload = await downloadAdvanceStatement(currentStatement.value.id);
        const blob = payload?.blob ?? payload;
        const fallbackName = buildStatementFileName(currentStatement.value);
        const filename = ensureXlsxFilename(payload?.filename || fallbackName, fallbackName);
        downloadBlobFile(blob, filename);
        toast.success('Выгрузка сформирована');
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось скачать файл');
        console.error(error);
    } finally {
        isDownloading.value = false;
    }
}

async function handleDelete() {
    if (!currentStatement.value || !canDelete.value) return;
    const confirmed = window.confirm('Удалить документ?');
    if (!confirmed) return;
    isDeleting.value = true;
    try {
        await deleteAdvanceStatement(currentStatement.value.id);
        toast.success('Документ удалён');
        showEmployeeCardOverlay.value = false;
        removeEmployeeQueryFromRoute();
        showStatementModal.value = false;
        currentStatement.value = null;
        await loadStatements();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось удалить документ');
        console.error(error);
    } finally {
        isDeleting.value = false;
    }
}

onMounted(() => {
    defaultDates();
    loadOptions();
    loadStatements();
    loadConsolidatedStatementsList();
});

watch(
    () => [showConsolidatedStatementModal.value, currentConsolidated.value?.id],
    ([isOpen, groupId]) => {
        if (!isOpen || !groupId) return;
        void loadConsolidatedTotals();
        if (consolidatedViewTab.value === 'histogram') {
            void loadConsolidatedHistogram();
        }
    },
);

watch(
    () => consolidatedViewTab.value,
    (tab) => {
        if (
            tab === 'histogram'
            && showConsolidatedStatementModal.value
            && currentConsolidated.value?.id
            && !consolidatedHistogramLoading.value
            && !consolidatedHistogramRows.value.length
            && !consolidatedHistogramError.value
        ) {
            void loadConsolidatedHistogram();
        }
    },
);

watch(
    () => createForm.value.statementKind,
    (kind) => {
        if (kind === 'salary') {
            createForm.value.salaryPercent = 100;
        } else if (!Number.isFinite(Number(createForm.value.salaryPercent))) {
            createForm.value.salaryPercent = 50;
        }
    },
);

watch(
    () => route.query.employeeId,
    (queryEmployeeId) => {
        if (!showEmployeeCardOverlay.value) return;
        if (!resolveEmployeeIdFromQuery(queryEmployeeId)) {
            showEmployeeCardOverlay.value = false;
        }
    },
);

watch(
    () => currentStatement.value?.status,
    (status) => {
        selectedStatus.value = status || '';
    },
    { immediate: true },
);

const adjustmentTypeOptions = computed(() =>
    adjustmentTypes.value.map((item) => ({
        label: `${item.name}${item.kind === 'deduction' ? ' (удержание)' : ''}`,
        value: String(item.id),
    })),
);

async function openPostModal() {
    if (!currentStatement.value) return;
    resetPostResult();
    if (!postForm.value.date) {
        const today = new Date();
        postForm.value.date = today.toISOString().slice(0, 10);
    }
    if (!adjustmentTypes.value.length) {
        try {
            const data = await fetchPayrollAdjustmentTypes();
            adjustmentTypes.value = Array.isArray(data?.items) ? data.items : [];
        } catch (error) {
            toast.error('Не удалось загрузить виды начислений');
            console.error(error);
            return;
        }
    }
    showPostModal.value = true;
}

function closePostModal() {
    showPostModal.value = false;
    resetPostResult();
}

async function handlePost() {
    if (!currentStatement.value) return;
    if (!postForm.value.adjustmentTypeId || !postForm.value.date) {
        toast.error('Заполните тип начисления и дату');
        return;
    }
    postLoading.value = true;
    try {
        await ensurePendingItemSavesFlushed();
        const result = await postAdvanceStatement(currentStatement.value.id, {
            adjustment_type_id: Number(postForm.value.adjustmentTypeId),
            date: postForm.value.date,
            comment: postForm.value.comment,
        });
        const createdCount = result?.created_count ?? 0;
        const createdTotal = Number(result?.created_total ?? 0);
        const skipped = Array.isArray(result?.skipped) ? result.skipped : [];
        const errors = Array.isArray(result?.errors) ? result.errors : [];
        const rawRows = Array.isArray(result?.results) ? result.results : [];
        let rows = rawRows.map((row) => ({
            staffCode: String(row?.staff_code || '').trim(),
            status: String(row?.status || ''),
            reason: row?.reason || '',
            fullName: '',
        }));
        if (!rows.length) {
            rows = [
                ...errors.map((row) => ({
                    staffCode: String(row?.staff_code || '').trim(),
                    status: 'error',
                    reason: row?.reason || '',
                    fullName: '',
                })),
                ...skipped.map((row) => ({
                    staffCode: String(row?.staff_code || '').trim(),
                    status: 'skipped',
                    reason: row?.reason || '',
                    fullName: '',
                })),
            ];
        }
        postResult.value = {
            createdCount,
            createdTotal,
            skippedCount: skipped.length,
            errorCount: errors.length,
            rows,
        };
        toast.success(`Создано записей: ${createdCount}. Сумма: ${formatMoney(createdTotal)}`);
        await loadStatement(currentStatement.value.id);
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось записать ведомость');
        console.error(error);
    } finally {
        postLoading.value = false;
    }
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/accounting-payroll-advance' as *;
</style>
