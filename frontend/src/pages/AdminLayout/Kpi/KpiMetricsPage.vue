<template>
    <div class="kpi-page">
        <section class="kpi-page__heading">
            <h2 class="kpi-panel__title">{{ contentView === 'metrics' ? 'Показатели KPI' : 'Группы KPI' }}</h2>
        </section>

        <section class="kpi-metrics__controls">
            <div class="kpi-metrics__toolbar">
                <div class="kpi-metrics__toolbar-filters">
                    <div class="kpi-metrics__status-switch kpi-metrics__status-switch--page" role="tablist" aria-label="Раздел KPI">
                        <button
                            v-for="page in contentViewOptions"
                            :key="page.value"
                            type="button"
                            class="kpi-metrics__status-button"
                            :class="{ 'is-active': contentView === page.value }"
                            :aria-pressed="(contentView === page.value).toString()"
                            @click="setContentView(page.value)"
                        >
                            {{ page.label }}
                        </button>
                    </div>
                    <div
                        class="kpi-metrics__status-switch"
                        role="tablist"
                        :aria-label="contentView === 'metrics' ? 'Фильтр статуса KPI' : 'Фильтр статуса групп KPI'"
                    >
                        <button
                            v-for="option in metricStatusOptions"
                            :key="option.value"
                            type="button"
                            class="kpi-metrics__status-button"
                            :class="{ 'is-active': currentStatusFilter === option.value }"
                            :aria-pressed="(currentStatusFilter === option.value).toString()"
                            @click="contentView === 'metrics' ? setMetricStatusFilter(option.value) : setMetricGroupStatusFilter(option.value)"
                        >
                            {{ option.label }}
                        </button>
                    </div>
                </div>
                <div class="kpi-metrics__toolbar-actions">
                    <button
                        type="button"
                        class="kpi-metrics__icon-button"
                        :disabled="isCurrentViewRefreshing"
                        title="Обновить"
                        aria-label="Обновить"
                        @click="refreshCurrentView"
                    >
                        <BaseIcon name="Refresh" />
                    </button>
                    <button
                        type="button"
                        class="kpi-metrics__icon-button kpi-metrics__icon-button--primary"
                        :title="contentView === 'metrics' ? 'Добавить KPI' : 'Добавить группу KPI'"
                        :aria-label="contentView === 'metrics' ? 'Добавить KPI' : 'Добавить группу KPI'"
                        @click="contentView === 'metrics' ? openCreateModal() : openCreateMetricGroupModal()"
                    >
                        <BaseIcon name="Plus" />
                    </button>
                </div>
            </div>
        </section>

        <Transition name="kpi-view-switch" mode="out-in">
            <section v-if="contentView === 'metrics'" key="metrics">
                <div
                    v-if="metricsLoading && !metrics.length"
                    class="kpi-metrics__table-wrap kpi-metrics__table-wrap--skeleton"
                    aria-hidden="true"
                >
                    <table class="kpi-metrics__table kpi-metrics__table--skeleton">
                        <thead>
                            <tr>
                                <th>Показатель</th>
                                <th>Группа</th>
                                <th>Единица</th>
                                <th>Рестораны</th>
                                <th>Тип выплаты</th>
                                <th>Тип удержания</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="row in 6" :key="`metrics-skeleton-${row}`">
                                <td v-for="col in 6" :key="`metrics-skeleton-${row}-${col}`">
                                    <span class="kpi-skeleton-line" :class="{ 'is-short': col > 3 }"></span>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div v-else-if="metrics.length" class="kpi-metrics__table-wrap">
                <table class="kpi-metrics__table">
                    <thead>
                        <tr>
                            <th>Показатель</th>
                            <th>Группа</th>
                            <th>Единица</th>
                            <th>Рестораны</th>
                            <th>Тип выплаты</th>
                            <th>Тип удержания</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="metric in metrics"
                            :key="metric.id"
                            class="kpi-metrics__row"
                            tabindex="0"
                            role="button"
                            @click="openEditModal(metric)"
                            @keydown.enter.prevent="openEditModal(metric)"
                            @keydown.space.prevent="openEditModal(metric)"
                        >
                            <td>
                                <div class="kpi-metrics__name-cell">
                                    <div class="kpi-metrics__name-line">
                                        <span class="kpi-metrics__name">{{ metric.name }}</span>
                                        <span class="kpi-card__status" :class="{ 'is-muted': !metric.is_active }">
                                            {{ metric.is_active ? 'Активна' : 'Отключена' }}
                                        </span>
                                    </div>
                                    <p v-if="metric.description" class="kpi-metrics__description">
                                        {{ metric.description }}
                                    </p>
                                    <p v-else class="kpi-metrics__description kpi-metrics__description--muted">
                                        Описание не указано
                                    </p>
                                </div>
                            </td>
                            <td>
                                <span class="kpi-metrics__value">
                                    {{ metricGroupLabel(metric) }}
                                </span>
                            </td>
                            <td>
                                <span class="kpi-metrics__value">
                                    {{ metric.unit || 'Без единицы' }}
                                </span>
                            </td>
                            <td>
                                <span class="kpi-metrics__value">
                                    {{ metricRestaurantsSummary(metric) }}
                                </span>
                            </td>
                            <td>
                                <span class="kpi-metrics__value">
                                    {{ metricAdjustmentTypeLabel(metric.bonus_adjustment_type_id) }}
                                </span>
                            </td>
                            <td>
                                <span class="kpi-metrics__value">
                                    {{ metricAdjustmentTypeLabel(metric.penalty_adjustment_type_id) }}
                                </span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p v-else class="kpi-list__empty">
                {{ metricStatusFilter === 'active' ? 'Действующие показатели пока не созданы.' : 'Архивных показателей пока нет.' }}
            </p>
        </section>

            <section v-else key="groups" class="kpi-panel kpi-panel--list">
                <div
                    v-if="metricGroupsLoading && !visibleMetricGroups.length"
                    class="kpi-metrics__table-wrap kpi-metrics__table-wrap--skeleton"
                    aria-hidden="true"
                >
                    <table class="kpi-metrics__table kpi-metrics__table--skeleton">
                        <thead>
                            <tr>
                                <th>Группа</th>
                                <th>Состав</th>
                                <th>Единица</th>
                                <th>Цель группы</th>
                                <th>Тип начисления</th>
                                <th>Тип удержания</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="row in 6" :key="`groups-skeleton-${row}`">
                                <td v-for="col in 6" :key="`groups-skeleton-${row}-${col}`">
                                    <span class="kpi-skeleton-line" :class="{ 'is-short': col > 3 }"></span>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div v-else-if="visibleMetricGroups.length" class="kpi-metrics__table-wrap">
                <table class="kpi-metrics__table">
                    <thead>
                        <tr>
                            <th>Группа</th>
                            <th>Состав</th>
                            <th>Единица</th>
                            <th>Цель группы</th>
                            <th>Тип начисления</th>
                            <th>Тип удержания</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="group in visibleMetricGroups"
                            :key="group.id"
                            class="kpi-metrics__row"
                            tabindex="0"
                            role="button"
                            @click="openEditMetricGroupModal(group)"
                            @keydown.enter.prevent="openEditMetricGroupModal(group)"
                            @keydown.space.prevent="openEditMetricGroupModal(group)"
                        >
                            <td>
                                <div class="kpi-metrics__name-cell">
                                    <div class="kpi-metrics__name-line">
                                        <span class="kpi-metrics__name">{{ group.name }}</span>
                                        <span class="kpi-card__status" :class="{ 'is-muted': isMetricGroupArchived(group) }">
                                            {{ isMetricGroupArchived(group) ? 'Архивная' : 'Действующая' }}
                                        </span>
                                    </div>
                                    <p
                                        class="kpi-metrics__description"
                                        :class="{ 'kpi-metrics__description--muted': !group.description }"
                                    >
                                        {{ group.description || 'Описание не указано' }}
                                    </p>
                                </div>
                            </td>
                            <td>
                                <span class="kpi-metrics__value">
                                    {{ metricGroupMembersSummary(group) }}
                                </span>
                            </td>
                            <td>
                                <span class="kpi-metrics__value">
                                    {{ group.unit || 'Без единицы' }}
                                </span>
                            </td>
                            <td>
                                <span class="kpi-metrics__value">
                                    {{ formatMetricGroupTarget(group.plan_target_percent) }}
                                </span>
                            </td>
                            <td>
                                <span class="kpi-metrics__value">
                                    {{ metricAdjustmentTypeLabel(group.bonus_adjustment_type_id) }}
                                </span>
                            </td>
                            <td>
                                <span class="kpi-metrics__value">
                                    {{ metricAdjustmentTypeLabel(group.penalty_adjustment_type_id) }}
                                </span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p v-else class="kpi-list__empty">
                {{ metricGroupStatusFilter === 'active' ? 'Действующих групп KPI пока нет.' : 'Архивных групп KPI пока нет.' }}
            </p>
            </section>
        </Transition>

        
        <Modal v-if="isModalOpen" class="kpi-metrics__modal" @close="closeModal">
            <template #header>
                <div class="kpi-metrics__modal-header">
                    <div>
                        <h3 class="kpi-metrics__modal-title">{{ metricFormTitle }}</h3>
                        <p class="kpi-metrics__modal-subtitle">
                            Заполните название, единицу измерения и описание показателя.
                        </p>
                    </div>
                    <div class="kpi-metrics__modal-header-actions">
                        <button
                            v-if="metricEditingId"
                            type="button"
                            class="kpi-metrics__modal-icon-button kpi-metrics__modal-icon-button--danger"
                            :disabled="metricSaving || metricDeletingId === metricEditingId"
                            title="Удалить KPI"
                            aria-label="Удалить KPI"
                            @click="handleDeleteMetric({ id: metricEditingId })"
                        >
                            <BaseIcon name="Trash" />
                        </button>
                        <button
                            type="button"
                            class="kpi-metrics__modal-icon-button"
                            :disabled="metricSaving"
                            title="Закрыть"
                            aria-label="Закрыть"
                            @click="closeModal"
                        >
                            <BaseIcon name="Close" />
                        </button>
                    </div>
                </div>
            </template>

            <div class="kpi-tabs">
                <button
                    v-for="tab in kpiTabs"
                    :key="tab.value"
                    type="button"
                    class="kpi-tabs__item"
                    :class="{
                        'is-active': activeTab === tab.value,
                        'is-disabled': tab.requiresMetric && !metricEditingId,
                    }"
                    :disabled="tab.requiresMetric && !metricEditingId"
                    @click="setActiveTab(tab)"
                >
                    {{ tab.label }}
                </button>
            </div>

            <div v-if="activeTab === 'info'" class="kpi-tab__content">
                <div class="kpi-metric-info">
                    <div class="kpi-metric-info__toolbar">
                        <Checkbox
                            class="kpi-metric-info__active-toggle"
                            :model-value="metricForm.isActive"
                            label="Активна"
                            @update:model-value="(checked) => { metricForm.isActive = Boolean(checked); }"
                        />
                    </div>

                    <div class="kpi-metric-info__layout">
                        <div class="kpi-metric-info__main">
                            <Input
                                v-model="metricForm.name"
                                label="Название"
                                placeholder="Выручка"
                                required
                            />
                            <Select
                                v-model="metricForm.groupId"
                                label="Группа KPI"
                                :options="metricGroupOptions"
                                placeholder="Без группы"
                            />
                            <Select
                                v-model="metricForm.bonusAdjustmentTypeId"
                                label="Тип начисления"
                                :options="bonusAdjustmentTypeOptions"
                                placeholder="Выберите тип"
                            />
                            <Select
                                v-model="metricForm.penaltyAdjustmentTypeId"
                                label="Тип удержания"
                                :options="penaltyAdjustmentTypeOptions"
                                placeholder="Выберите тип"
                            />
                        </div>

                        <div class="kpi-metric-info__side">
                            <Select
                                v-model="metricForm.unit"
                                label="Единица измерения"
                                :options="unitOptions"
                                placeholder="Выберите единицу"
                            />
                            <div class="kpi-panel__field">
                                <label class="kpi-panel__label">Зона действия KPI</label>
                                <div class="kpi-panel__checkbox-row">
                                    <Checkbox
                                        :model-value="metricForm.allRestaurants"
                                        label="Все рестораны"
                                        @update:model-value="handleAllRestaurantsToggle"
                                    />
                                </div>
                                <div
                                    v-if="!metricForm.allRestaurants"
                                    ref="metricRestaurantSelectRef"
                                    class="kpi-panel__multiselect-dropdown"
                                >
                                    <button
                                        type="button"
                                        class="kpi-panel__multiselect-trigger"
                                        :aria-expanded="isMetricRestaurantSelectOpen.toString()"
                                        aria-haspopup="listbox"
                                        @click="toggleMetricRestaurantSelect"
                                        @keydown="handleMetricRestaurantSelectKeydown"
                                    >
                                        <span
                                            :class="[
                                                'kpi-panel__multiselect-value',
                                                { 'is-placeholder': !metricRestaurantSelectionCount },
                                            ]"
                                        >
                                            {{ metricRestaurantSelectionLabel }}
                                        </span>
                                        <span
                                            :class="[
                                                'kpi-panel__multiselect-icon',
                                                { 'is-open': isMetricRestaurantSelectOpen },
                                            ]"
                                        >
                                            ▾
                                        </span>
                                    </button>
                                    <div
                                        v-if="isMetricRestaurantSelectOpen"
                                        class="kpi-panel__multiselect-menu"
                                        role="listbox"
                                    >
                                        <div class="kpi-panel__multiselect-options">
                                            <Checkbox
                                                v-for="rest in restaurantOptions"
                                                :key="rest.value"
                                                :label="rest.label"
                                                :model-value="metricForm.restaurantIds.includes(rest.value)"
                                                @update:model-value="(checked) => toggleMetricRestaurant(rest.value, checked)"
                                            />
                                            <p v-if="!restaurantOptions.length" class="kpi-panel__multiselect-empty">
                                                Нет доступных ресторанов
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="kpi-panel__field">
                                <label class="kpi-panel__label">Описание</label>
                                <textarea v-model="metricForm.description" class="kpi-panel__textarea" rows="4" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div v-else-if="activeTab === 'rules'" class="kpi-tab__content">
                <section class="kpi-subpanel">
                    <div class="kpi-subpanel__toolbar">
                        <div class="kpi-subpanel__heading">
                            <h4 class="kpi-subpanel__title">Правила показателя</h4>
                            <p class="kpi-subpanel__subtitle">
                                Каждое правило задает условие премии или удержания для выбранной области действия.
                            </p>
                        </div>
                        <div class="kpi-subpanel__actions">
                            <button
                                type="button"
                                class="kpi-metrics__icon-button"
                                :disabled="rulesLoading"
                                title="Обновить правила"
                                aria-label="Обновить правила"
                                @click="loadMetricRules"
                            >
                                <BaseIcon name="Refresh" />
                            </button>
                            <button
                                type="button"
                                class="kpi-metrics__action-chip"
                                @click="openCreateRuleModal"
                            >
                                <BaseIcon name="Plus" />
                                <span>Добавить правило</span>
                            </button>
                        </div>
                    </div>

                    <div v-if="metricRules.length" class="kpi-rule-list">
                        <article
                            v-for="rule in metricRules"
                            :key="rule.id"
                            class="kpi-rule-row"
                        >
                            <div
                                class="kpi-rule-row__main"
                                role="button"
                                tabindex="0"
                                @click="openEditRuleModal(rule)"
                                @keydown.enter.prevent="openEditRuleModal(rule)"
                                @keydown.space.prevent="openEditRuleModal(rule)"
                            >
                                <div class="kpi-rule-row__top">
                                    <div class="kpi-rule-row__identity">
                                        <span class="kpi-rule-row__title">Правило #{{ rule.id }}</span>
                                        <span class="kpi-card__status" :class="{ 'is-muted': !rule.is_active }">
                                            {{ rule.is_active ? 'Активно' : 'Отключено' }}
                                        </span>
                                    </div>
                                    <div class="kpi-rule-row__chips">
                                        <span class="kpi-rule-row__chip">{{ ruleRestaurantLabel(rule) }}</span>
                                        <span class="kpi-rule-row__chip">{{ subdivisionLabel(rule.position_id) }}</span>
                                        <span class="kpi-rule-row__chip">{{ positionLabel(rule.position_id) }}</span>
                                        <span v-if="rule.employee_id" class="kpi-rule-row__chip">
                                            Сотрудник: {{ employeeLabel(rule.employee_id) }}
                                        </span>
                                    </div>
                                </div>

                                <div class="kpi-rule-row__content">
                                    <div class="kpi-rule-row__section">
                                        <span class="kpi-rule-row__section-label">База сравнения</span>
                                        <span class="kpi-rule-row__section-value">
                                            {{ comparisonBasisLabel(rule.comparison_basis) }}
                                        </span>
                                    </div>
                                    <div class="kpi-rule-row__section">
                                        <span class="kpi-rule-row__section-label">Премия</span>
                                        <span class="kpi-rule-row__section-value">
                                            если факт {{ comparisonLabel(rule.bonus_condition) }}
                                            {{ formatNumber(rule.target_value) }},
                                            {{ effectLabel(rule.bonus_type, rule.bonus_value) }}
                                        </span>
                                    </div>
                                    <div class="kpi-rule-row__section">
                                        <span class="kpi-rule-row__section-label">Удержание</span>
                                        <span class="kpi-rule-row__section-value">
                                            если факт {{ comparisonLabel(rule.penalty_condition) }}
                                            {{ formatNumber(rule.warning_value ?? rule.target_value) }},
                                            {{ effectLabel(rule.penalty_type, rule.penalty_value) }}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <button
                                type="button"
                                class="kpi-metrics__modal-icon-button kpi-metrics__modal-icon-button--danger kpi-rule-row__delete"
                                :disabled="ruleDeletingId === rule.id"
                                title="Удалить правило"
                                aria-label="Удалить правило"
                                @click.stop="handleDeleteRule(rule)"
                            >
                                <BaseIcon name="Trash" />
                            </button>
                        </article>
                    </div>
                    <p v-else class="kpi-list__empty">Правила для показателя пока не созданы.</p>
                </section>
            </div>

            <div v-else-if="activeTab === 'plans'" class="kpi-tab__content">
                <section v-if="metricEditingId && planForms[metricEditingId]" class="kpi-subpanel kpi-plan-editor">
                    <div class="kpi-subpanel__toolbar">
                        <div class="kpi-subpanel__heading">
                            <h4 class="kpi-subpanel__title">Плановые показатели</h4>
                            <p class="kpi-subpanel__subtitle">Настройка плана на {{ planYear }} год</p>
                        </div>
                        <button
                            type="button"
                            class="kpi-metrics__action-chip"
                            :disabled="planSaving[metricEditingId]"
                            @click="savePlan(metricEditingId)"
                        >
                            <BaseIcon name="Save" />
                            <span>Сохранить план</span>
                        </button>
                    </div>

                    <div class="kpi-plan-editor__settings">
                        <div class="kpi-plan-editor__settings-row">
                            <div class="kpi-plan-editor__mode">
                                <span class="kpi-plan-editor__label">Тип плана</span>
                                <div class="kpi-plan-editor__mode-switch">
                                    <button
                                        type="button"
                                        class="kpi-plan-editor__mode-button"
                                        :class="{ 'is-active': planForms[metricEditingId].planMode === 'shared' }"
                                        @click="planForms[metricEditingId].planMode = 'shared'"
                                    >
                                        Единый
                                    </button>
                                    <button
                                        type="button"
                                        class="kpi-plan-editor__mode-button"
                                        :class="{ 'is-active': planForms[metricEditingId].planMode === 'per_restaurant' }"
                                        @click="planForms[metricEditingId].planMode = 'per_restaurant'"
                                    >
                                        По ресторанам
                                    </button>
                                </div>
                            </div>

                            <label class="kpi-plan-editor__toggle">
                                <input
                                    v-model="planForms[metricEditingId].isDynamic"
                                    type="checkbox"
                                >
                                <span>Динамический</span>
                            </label>

                            <label class="kpi-plan-editor__toggle">
                                <input
                                    v-model="metricForm.useMaxScale"
                                    type="checkbox"
                                >
                                <span>Есть макс. шкала</span>
                            </label>

                            <div v-if="metricForm.useMaxScale" class="kpi-plan-editor__max-scale">
                                <label class="kpi-plan-editor__label" for="kpi-max-scale">Максимум</label>
                                <input
                                    id="kpi-max-scale"
                                    v-model="metricForm.maxScaleValue"
                                    class="kpi-plan-editor__input kpi-plan-editor__input--compact"
                                    type="number"
                                    step="0.01"
                                    placeholder="100"
                                >
                            </div>

                            <div class="kpi-plan-editor__direction">
                                <span class="kpi-plan-editor__label">Направление KPI</span>
                                <div class="kpi-plan-editor__mode-switch">
                                    <button
                                        type="button"
                                        class="kpi-plan-editor__mode-button"
                                        :class="{ 'is-active': metricForm.planDirection === 'higher_better' }"
                                        @click="metricForm.planDirection = 'higher_better'"
                                    >
                                        Не ниже плана
                                    </button>
                                    <button
                                        type="button"
                                        class="kpi-plan-editor__mode-button"
                                        :class="{ 'is-active': metricForm.planDirection === 'lower_better' }"
                                        @click="metricForm.planDirection = 'lower_better'"
                                    >
                                        Не выше плана
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="kpi-plan-editor__body">
                        <div
                            v-if="planForms[metricEditingId].planMode === 'per_restaurant'"
                            class="kpi-plan-editor__row kpi-plan-editor__row--filters"
                        >
                            <div class="kpi-plan-editor__field kpi-plan-editor__field--restaurant">
                                <Select
                                    v-model="planForms[metricEditingId].restaurantId"
                                    label="Ресторан"
                                    :options="planRestaurantOptions"
                                    placeholder="Выберите ресторан"
                                />
                            </div>
                            <p v-if="!planRestaurantOptions.length" class="kpi-plan-editor__empty">
                                Нет доступных ресторанов для этого KPI
                            </p>
                        </div>

                        <div
                            v-if="!planForms[metricEditingId].isDynamic"
                            class="kpi-plan-editor__row kpi-plan-editor__row--static"
                        >
                            <div class="kpi-plan-editor__field kpi-plan-editor__field--value">
                                <label class="kpi-plan-editor__label">
                                    {{ planForms[metricEditingId].planMode === 'per_restaurant' ? 'План для ресторана' : 'План на месяц' }}
                                </label>
                                <input
                                    v-model="planForms[metricEditingId].constantValue"
                                    class="kpi-plan-editor__input kpi-plan-editor__input--compact"
                                    type="number"
                                    step="0.01"
                                    placeholder="0"
                                >
                            </div>
                        </div>
                        <div v-else class="kpi-plan-editor__grid">
                            <div v-for="month in months" :key="month.month" class="kpi-plan-editor__month-card">
                                <label class="kpi-plan-editor__month-label">{{ month.short }}</label>
                                <input
                                    v-model="planForms[metricEditingId].months[month.month]"
                                    class="kpi-plan-editor__input"
                                    type="number"
                                    step="0.01"
                                    placeholder="0"
                                >
                            </div>
                        </div>
                    </div>
                </section>
            </div>
            <template #footer>
                <div class="kpi-metrics__modal-actions">
                    <button
                        type="button"
                        class="kpi-metrics__modal-icon-button kpi-metrics__modal-icon-button--primary"
                        :disabled="metricSaving"
                        :title="metricFormAction"
                        :aria-label="metricFormAction"
                        @click="handleSaveMetric"
                    >
                        <BaseIcon name="Save" />
                    </button>
                </div>
            </template>
        </Modal>

        <Modal v-if="isRuleModalOpen" class="kpi-rules__modal" @close="closeRuleModal">
            <template #header>
                <div class="kpi-metrics__modal-header">
                    <div>
                        <h3 class="kpi-rules__modal-title">{{ ruleFormTitle }}</h3>
                        <p class="kpi-rules__modal-subtitle">Настройте условия начисления KPI.</p>
                    </div>
                    <div class="kpi-metrics__modal-header-actions">
                        <button
                            v-if="ruleEditingId"
                            type="button"
                            class="kpi-metrics__modal-icon-button kpi-metrics__modal-icon-button--danger"
                            :disabled="ruleSaving || ruleDeletingId === ruleEditingId"
                            title="Удалить правило"
                            aria-label="Удалить правило"
                            @click="handleDeleteRule({ id: ruleEditingId })"
                        >
                            <BaseIcon name="Trash" />
                        </button>
                        <button
                            type="button"
                            class="kpi-metrics__modal-icon-button"
                            :disabled="ruleSaving"
                            title="Закрыть"
                            aria-label="Закрыть"
                            @click="closeRuleModal"
                        >
                            <BaseIcon name="Close" />
                        </button>
                    </div>
                </div>
            </template>

            <div class="kpi-rules-editor">
                <section class="kpi-subpanel kpi-rules__panel">
                    <div class="kpi-subpanel__heading">
                        <h4 class="kpi-subpanel__title">Область действия</h4>
                        <p class="kpi-subpanel__subtitle">
                            Выберите подразделение, должности и при необходимости конкретного сотрудника.
                        </p>
                    </div>
                    <div class="kpi-rules__scope-grid">
                        <div ref="ruleSubdivisionSelectRef" class="kpi-panel__field kpi-panel__field--scope-subdivision">
                            <label class="kpi-panel__label">Подразделения</label>
                            <div class="kpi-panel__multiselect-dropdown">
                                <button
                                    type="button"
                                    class="kpi-panel__multiselect-trigger"
                                    :aria-expanded="isRuleSubdivisionSelectOpen.toString()"
                                    aria-haspopup="listbox"
                                    @click="toggleRuleSubdivisionSelect"
                                    @keydown="handleRuleSubdivisionSelectKeydown"
                                >
                                    <span class="kpi-panel__multiselect-value">
                                        {{ ruleSubdivisionSelectionLabel }}
                                    </span>
                                    <span
                                        :class="[
                                            'kpi-panel__multiselect-icon',
                                            { 'is-open': isRuleSubdivisionSelectOpen },
                                        ]"
                                    >
                                        ▾
                                    </span>
                                </button>
                                <div
                                    v-if="isRuleSubdivisionSelectOpen"
                                    class="kpi-panel__multiselect-menu"
                                    role="listbox"
                                >
                                    <div class="kpi-panel__multiselect-options">
                                        <Checkbox
                                            label="Все подразделения"
                                            :model-value="ruleForm.subdivisionId === null"
                                            @update:model-value="(checked) => toggleRuleSubdivision(null, checked)"
                                        />
                                        <Checkbox
                                            v-for="sub in subdivisionOptions"
                                            :key="sub.value"
                                            :label="sub.label"
                                            :model-value="Number(ruleForm.subdivisionId) === Number(sub.value)"
                                            @update:model-value="(checked) => toggleRuleSubdivision(sub.value, checked)"
                                        />
                                        <p v-if="!subdivisionOptions.length" class="kpi-panel__multiselect-empty">
                                            Нет доступных подразделений
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="kpi-panel__field kpi-panel__field--scope-position">
                            <label class="kpi-panel__label">Должности</label>
                            <div
                                ref="rulePositionSelectRef"
                                class="kpi-panel__multiselect-dropdown"
                            >
                                <button
                                    type="button"
                                    class="kpi-panel__multiselect-trigger"
                                    :aria-expanded="isRulePositionSelectOpen.toString()"
                                    aria-haspopup="listbox"
                                    @click="toggleRulePositionSelect"
                                    @keydown="handleRulePositionSelectKeydown"
                                >
                                    <span
                                        :class="[
                                            'kpi-panel__multiselect-value',
                                            { 'is-placeholder': !rulePositionHasSelection },
                                        ]"
                                    >
                                        {{ rulePositionSelectionLabel }}
                                    </span>
                                    <span
                                        :class="[
                                            'kpi-panel__multiselect-icon',
                                            { 'is-open': isRulePositionSelectOpen },
                                        ]"
                                    >
                                        ▾
                                    </span>
                                </button>
                                <div
                                    v-if="isRulePositionSelectOpen"
                                    class="kpi-panel__multiselect-menu"
                                    role="listbox"
                                >
                                    <div class="kpi-panel__multiselect-options">
                                        <Checkbox
                                            label="Все должности"
                                            :model-value="ruleForm.allPositions"
                                            @update:model-value="handleAllPositionsToggle"
                                        />
                                        <Checkbox
                                            v-for="pos in positionOptions"
                                            :key="pos.value"
                                            :label="pos.label"
                                            :model-value="!ruleForm.allPositions && ruleForm.positionIds.includes(pos.value)"
                                            @update:model-value="(checked) => toggleRulePosition(pos.value, checked)"
                                        />
                                        <p v-if="!positionOptions.length" class="kpi-panel__multiselect-empty">
                                            Нет доступных должностей
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="kpi-panel__field kpi-panel__field--checkbox-top kpi-panel__field--scope-flag">
                            <label class="kpi-panel__label kpi-panel__label--hidden">Индивидуальный KPI</label>
                            <Checkbox
                                class="kpi-rules__flag"
                                :model-value="ruleForm.isIndividual"
                                label="Индивидуальный KPI"
                                @update:model-value="(checked) => { ruleForm.isIndividual = Boolean(checked); }"
                            />
                        </div>

                        <div class="kpi-panel__field kpi-panel__field--checkbox-top kpi-panel__field--scope-flag">
                            <label class="kpi-panel__label kpi-panel__label--hidden">Активно</label>
                            <Checkbox
                                class="kpi-rules__flag"
                                :model-value="ruleForm.isActive"
                                label="Активно"
                                @update:model-value="(checked) => { ruleForm.isActive = Boolean(checked); }"
                            />
                        </div>

                        <div v-if="ruleForm.isIndividual" class="kpi-panel__field kpi-panel__field--full kpi-rules__employee">
                            <Select
                                v-model="ruleForm.employeeId"
                                label="Сотрудник"
                                :options="employeeOptions"
                                placeholder="Выберите сотрудника"
                                :disabled="employeeSearchLoading"
                                searchable
                                search-placeholder="Введите ФИО"
                                @search="handleEmployeeSearch"
                            />
                        </div>
                    </div>
                </section>

                <section class="kpi-subpanel kpi-rules__panel">
                    <div class="kpi-subpanel__toolbar">
                        <div class="kpi-subpanel__heading">
                            <h4 class="kpi-subpanel__title">Условия премии и удержания</h4>
                            <p class="kpi-subpanel__subtitle">
                                Каждая строка задает одно условие: премию или удержание.
                            </p>
                        </div>
                        <button
                            type="button"
                            class="kpi-metrics__action-chip"
                            :disabled="!canAddRuleActionRow"
                            @click="addRuleActionRow"
                        >
                            <BaseIcon name="Plus" />
                            <span>Добавить условие</span>
                        </button>
                    </div>

                    <div class="kpi-rule-lines">
                        <div
                            v-for="row in ruleActionRows"
                            :key="row.id"
                            class="kpi-rule-lines__row"
                        >
                            <Select
                                v-model="row.type"
                                class="kpi-rule-lines__field kpi-rule-lines__field--type"
                                label="Тип"
                                :options="ruleActionTypeOptionsForRow(row.id)"
                            />
                            <Select
                                :model-value="row.planSource"
                                class="kpi-rule-lines__field kpi-rule-lines__field--plan-source"
                                label="Плановый показатель"
                                :options="rulePlanSourceOptions"
                                @update:model-value="(value) => handleRulePlanSourceChange(row, value)"
                            />
                            <div v-if="row.planSource === 'custom'" class="kpi-panel__field kpi-rule-lines__field kpi-rule-lines__field--plan-value">
                                <label class="kpi-panel__label">Свое значение</label>
                                <input
                                    v-model="row.planValue"
                                    class="kpi-panel__input"
                                    type="number"
                                    step="0.01"
                                >
                            </div>
                            <div v-else class="kpi-panel__field kpi-rule-lines__field kpi-rule-lines__field--plan-value">
                                <label class="kpi-panel__label">Значение из плана</label>
                                <div class="kpi-rule-lines__plan-ref">
                                    {{ rulePlanReferenceDisplay }}
                                </div>
                            </div>
                            <Select
                                v-model="row.effectType"
                                class="kpi-rule-lines__field kpi-rule-lines__field--format"
                                label="Формат"
                                :options="effectTypeLineOptions"
                            />
                            <div class="kpi-panel__field kpi-rule-lines__field kpi-rule-lines__field--value">
                                <label class="kpi-panel__label">Значение</label>
                                <div class="kpi-rule-lines__value-control" :class="{ 'is-disabled': row.effectType === 'none' }">
                                    <input
                                        v-model="row.effectValue"
                                        class="kpi-rule-lines__value-input"
                                        type="number"
                                        step="0.01"
                                        :disabled="row.effectType === 'none'"
                                    >
                                    <span
                                        v-if="row.effectType === 'percent' || row.effectType === 'fixed'"
                                        class="kpi-rule-lines__value-suffix"
                                    >
                                        {{ row.effectType === 'percent' ? '%' : '₽' }}
                                    </span>
                                </div>
                            </div>
                            <div class="kpi-rule-lines__remove">
                                <button
                                    type="button"
                                    class="kpi-metrics__modal-icon-button kpi-rule-lines__remove-button"
                                    :disabled="ruleActionRows.length <= 1"
                                    :aria-label="`Удалить условие ${row.type === 'bonus' ? 'премии' : 'удержания'}`"
                                    @click="removeRuleActionRow(row.id)"
                                >
                                    <BaseIcon name="Trash" class="kpi-rule-lines__remove-icon" />
                                </button>
                            </div>
                        </div>
                    </div>
                </section>
            </div>

            <template #footer>
                <div class="kpi-metrics__modal-actions">
                    <button
                        type="button"
                        class="kpi-metrics__modal-icon-button kpi-metrics__modal-icon-button--primary"
                        :disabled="ruleSaving"
                        :title="ruleFormAction"
                        :aria-label="ruleFormAction"
                        @click="handleSaveRule"
                    >
                        <BaseIcon name="Save" />
                    </button>
                </div>
            </template>
        </Modal>

        <Modal v-if="isGroupModalOpen" class="kpi-metrics__groups-modal" @close="closeMetricGroupsModal">
            <template #header>
                <div class="kpi-metrics__modal-header">
                    <div>
                        <h3 class="kpi-metrics__modal-title">{{ metricGroupFormTitle }}</h3>
                        <p class="kpi-metrics__modal-subtitle">
                            Настройте состав группы, правила и плановые показатели.
                        </p>
                    </div>
                    <div class="kpi-metrics__modal-header-actions">
                        <button
                            v-if="metricGroupEditingId"
                            type="button"
                            class="kpi-metrics__modal-icon-button kpi-metrics__modal-icon-button--danger"
                            :disabled="metricGroupSaving || metricGroupDeletingId === metricGroupEditingId"
                            title="Удалить группу KPI"
                            aria-label="Удалить группу KPI"
                            @click="handleDeleteMetricGroup({ id: metricGroupEditingId, name: metricGroupForm.name })"
                        >
                            <BaseIcon name="Trash" />
                        </button>
                        <button
                            type="button"
                            class="kpi-metrics__modal-icon-button"
                            :disabled="metricGroupSaving"
                            title="Закрыть"
                            aria-label="Закрыть"
                            @click="closeMetricGroupsModal"
                        >
                            <BaseIcon name="Close" />
                        </button>
                    </div>
                </div>
            </template>

            <div class="kpi-tabs">
                <button
                    v-for="tab in metricGroupTabs"
                    :key="tab.value"
                    type="button"
                    class="kpi-tabs__item"
                    :class="{
                        'is-active': metricGroupActiveTab === tab.value,
                        'is-disabled': tab.requiresGroup && !metricGroupEditingId,
                    }"
                    :disabled="tab.requiresGroup && !metricGroupEditingId"
                    @click="setActiveMetricGroupTab(tab)"
                >
                    {{ tab.label }}
                </button>
            </div>

            <div v-if="metricGroupActiveTab === 'info'" class="kpi-tab__content">
                <div class="kpi-metric-info">
                    <div class="kpi-metric-info__layout">
                        <div class="kpi-metric-info__main">
                            <Input
                                v-model="metricGroupForm.name"
                                label="Название группы"
                                placeholder="СанПин"
                                required
                            />
                            <Select
                                v-model="metricGroupForm.unit"
                                label="Что оцениваем"
                                :options="unitOptions"
                                placeholder="Выберите единицу"
                            />
                            <Select
                                v-model="metricGroupForm.bonusAdjustmentTypeId"
                                label="Начисление по умолчанию"
                                :options="bonusAdjustmentTypeOptions"
                                placeholder="Выберите тип"
                            />
                            <Select
                                v-model="metricGroupForm.penaltyAdjustmentTypeId"
                                label="Депремирование по умолчанию"
                                :options="penaltyAdjustmentTypeOptions"
                                placeholder="Выберите тип"
                            />
                        </div>

                        <div class="kpi-metric-info__side">
                            <div class="kpi-panel__field">
                                <label class="kpi-panel__label">Кто входит в группу</label>
                                <div
                                    ref="metricGroupMembersSelectRef"
                                    class="kpi-panel__multiselect-dropdown"
                                >
                                    <button
                                        type="button"
                                        class="kpi-panel__multiselect-trigger"
                                        :aria-expanded="isMetricGroupMembersSelectOpen.toString()"
                                        aria-haspopup="listbox"
                                        @click="toggleMetricGroupMembersSelect"
                                        @keydown="handleMetricGroupMembersSelectKeydown"
                                    >
                                        <span
                                            :class="[
                                                'kpi-panel__multiselect-value',
                                                { 'is-placeholder': !metricGroupMemberSelectionCount },
                                            ]"
                                        >
                                            {{ metricGroupMemberSelectionLabel }}
                                        </span>
                                        <span
                                            :class="[
                                                'kpi-panel__multiselect-icon',
                                                { 'is-open': isMetricGroupMembersSelectOpen },
                                            ]"
                                        >
                                            ▾
                                        </span>
                                    </button>
                                    <div
                                        v-if="isMetricGroupMembersSelectOpen"
                                        class="kpi-panel__multiselect-menu"
                                        role="listbox"
                                    >
                                        <div class="kpi-panel__multiselect-options">
                                            <Checkbox
                                                v-for="metric in metricGroupMemberOptions"
                                                :key="metric.value"
                                                :label="metric.label"
                                                :model-value="metricGroupForm.memberIds.includes(metric.value)"
                                                @update:model-value="(checked) => toggleMetricGroupMember(metric.value, checked)"
                                            />
                                            <p v-if="!metricGroupMemberOptions.length" class="kpi-panel__multiselect-empty">
                                                Нет доступных показателей
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="kpi-panel__field">
                                <label class="kpi-panel__label">Описание</label>
                                <textarea
                                    v-model="metricGroupForm.description"
                                    class="kpi-panel__textarea"
                                    rows="4"
                                    placeholder="Что входит в эту группу"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div v-else-if="metricGroupActiveTab === 'rules'" class="kpi-tab__content">
                <section class="kpi-subpanel">
                    <div class="kpi-panel__header kpi-panel__header--tight">
                        <div>
                            <h4 class="kpi-panel__title">Правила группы</h4>
                            <p class="kpi-panel__subtitle">Условия выплаты и удержания по агрегированному результату группы.</p>
                        </div>
                        <div class="kpi-panel__header-actions">
                            <Button color="outline" size="sm" :loading="metricGroupRulesLoading" @click="loadMetricGroupRules()">
                                Обновить
                            </Button>
                            <Button color="primary" size="sm" @click="openCreateGroupRuleModal">
                                Добавить правило
                            </Button>
                        </div>
                    </div>
                    <div v-if="metricGroupRules.length" class="kpi-rule-list">
                        <article
                            v-for="rule in metricGroupRules"
                            :key="`group-rule-${rule.id}`"
                            class="kpi-rule-row"
                        >
                            <div
                                class="kpi-rule-row__main"
                                role="button"
                                tabindex="0"
                                @click="openEditGroupRuleModal(rule)"
                                @keydown.enter.prevent="openEditGroupRuleModal(rule)"
                                @keydown.space.prevent="openEditGroupRuleModal(rule)"
                            >
                                <div class="kpi-rule-row__top">
                                    <div class="kpi-rule-row__identity">
                                        <span class="kpi-rule-row__title">Правило #{{ rule.id }}</span>
                                        <span class="kpi-card__status" :class="{ 'is-muted': !rule.is_active }">
                                            {{ rule.is_active ? 'Активно' : 'Отключено' }}
                                        </span>
                                    </div>
                                    <div class="kpi-rule-row__chips">
                                        <span class="kpi-rule-row__chip">{{ ruleRestaurantLabel(rule) }}</span>
                                        <span class="kpi-rule-row__chip">{{ subdivisionLabel(rule.position_id) }}</span>
                                        <span class="kpi-rule-row__chip">{{ positionLabel(rule.position_id) }}</span>
                                        <span v-if="rule.employee_id" class="kpi-rule-row__chip">Сотрудник: {{ employeeLabel(rule.employee_id) }}</span>
                                    </div>
                                </div>

                                <div class="kpi-rule-row__content">
                                    <div class="kpi-rule-row__section">
                                        <span class="kpi-rule-row__section-label">База сравнения</span>
                                        <span class="kpi-rule-row__section-value">
                                            {{ comparisonBasisLabel(rule.comparison_basis) }}
                                        </span>
                                    </div>
                                    <div class="kpi-rule-row__section">
                                        <span class="kpi-rule-row__section-label">Премия</span>
                                        <span class="kpi-rule-row__section-value">
                                            если итог {{ comparisonLabel(rule.bonus_condition) }}
                                            {{ formatNumber(rule.target_value) }},
                                            {{ effectLabel(rule.bonus_type, rule.bonus_value) }}
                                        </span>
                                    </div>
                                    <div class="kpi-rule-row__section">
                                        <span class="kpi-rule-row__section-label">Удержание</span>
                                        <span class="kpi-rule-row__section-value">
                                            если итог {{ comparisonLabel(rule.penalty_condition) }}
                                            {{ formatNumber(rule.warning_value ?? rule.target_value) }},
                                            {{ effectLabel(rule.penalty_type, rule.penalty_value) }}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <button
                                type="button"
                                class="kpi-metrics__modal-icon-button kpi-metrics__modal-icon-button--danger kpi-rule-row__delete"
                                :disabled="ruleDeletingId === rule.id"
                                title="Удалить правило"
                                aria-label="Удалить правило"
                                @click.stop="handleDeleteRule(rule)"
                            >
                                <BaseIcon name="Trash" />
                            </button>
                        </article>
                    </div>
                    <p v-else class="kpi-list__empty">Для группы пока нет правил.</p>
                </section>
            </div>

            <div v-else-if="metricGroupActiveTab === 'plans'" class="kpi-tab__content">
                <section
                    v-if="metricGroupEditingId && activeMetricGroupPlanForm"
                    class="kpi-subpanel kpi-plan-editor"
                >
                    <div class="kpi-subpanel__toolbar">
                        <div class="kpi-subpanel__heading">
                            <h4 class="kpi-subpanel__title">Плановые показатели группы</h4>
                            <p class="kpi-subpanel__subtitle">Настройка плана на {{ planYear }} год</p>
                        </div>
                        <button
                            type="button"
                            class="kpi-metrics__action-chip"
                            :disabled="metricGroupPlanSaving[metricGroupEditingId]"
                            @click="saveMetricGroupPlan(metricGroupEditingId)"
                        >
                            <BaseIcon name="Save" />
                            <span>Сохранить план</span>
                        </button>
                    </div>

                    <div class="kpi-plan-editor__settings">
                        <div class="kpi-plan-editor__settings-row">
                            <div class="kpi-plan-editor__mode">
                                <span class="kpi-plan-editor__label">Тип плана</span>
                                <div class="kpi-plan-editor__mode-switch">
                                    <button
                                        type="button"
                                        class="kpi-plan-editor__mode-button"
                                        :class="{ 'is-active': activeMetricGroupPlanForm.planMode === 'shared' }"
                                        @click="activeMetricGroupPlanForm.planMode = 'shared'"
                                    >
                                        Единый
                                    </button>
                                    <button
                                        type="button"
                                        class="kpi-plan-editor__mode-button"
                                        :class="{ 'is-active': activeMetricGroupPlanForm.planMode === 'per_restaurant' }"
                                        @click="activeMetricGroupPlanForm.planMode = 'per_restaurant'"
                                    >
                                        По ресторанам
                                    </button>
                                </div>
                            </div>

                            <label class="kpi-plan-editor__toggle">
                                <input
                                    v-model="activeMetricGroupPlanForm.isDynamic"
                                    type="checkbox"
                                >
                                <span>Динамический</span>
                            </label>

                            <div class="kpi-plan-editor__target">
                                <label class="kpi-plan-editor__label" for="kpi-group-target-percent">Цель группы, %</label>
                                <input
                                    id="kpi-group-target-percent"
                                    v-model="metricGroupForm.planTargetPercent"
                                    class="kpi-plan-editor__input kpi-plan-editor__input--compact"
                                    type="number"
                                    min="0"
                                    max="100"
                                    step="0.01"
                                    placeholder="100"
                                >
                            </div>

                            <div class="kpi-plan-editor__direction">
                                <span class="kpi-plan-editor__label">Направление KPI</span>
                                <div class="kpi-plan-editor__mode-switch">
                                    <button
                                        type="button"
                                        class="kpi-plan-editor__mode-button"
                                        :class="{ 'is-active': metricGroupForm.planDirection === 'higher_better' }"
                                        @click="metricGroupForm.planDirection = 'higher_better'"
                                    >
                                        Не ниже плана
                                    </button>
                                    <button
                                        type="button"
                                        class="kpi-plan-editor__mode-button"
                                        :class="{ 'is-active': metricGroupForm.planDirection === 'lower_better' }"
                                        @click="metricGroupForm.planDirection = 'lower_better'"
                                    >
                                        Не выше плана
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div class="kpi-plan-editor__settings-row">
                            <label class="kpi-plan-editor__toggle">
                                <input
                                    v-model="metricGroupForm.useMaxScale"
                                    type="checkbox"
                                >
                                <span>Есть макс. шкала</span>
                            </label>

                            <div v-if="metricGroupForm.useMaxScale" class="kpi-plan-editor__max-scale">
                                <label class="kpi-plan-editor__label" for="kpi-group-max-scale">Максимум</label>
                                <input
                                    id="kpi-group-max-scale"
                                    v-model="metricGroupForm.maxScaleValue"
                                    class="kpi-plan-editor__input kpi-plan-editor__input--compact"
                                    type="number"
                                    step="0.01"
                                    placeholder="100"
                                >
                            </div>
                        </div>
                    </div>

                    <div class="kpi-plan-editor__body">
                        <div
                            v-if="activeMetricGroupPlanForm.planMode === 'per_restaurant'"
                            class="kpi-plan-editor__row kpi-plan-editor__row--filters"
                        >
                            <div class="kpi-plan-editor__field kpi-plan-editor__field--restaurant">
                                <Select
                                    v-model="activeMetricGroupPlanForm.restaurantId"
                                    label="Ресторан"
                                    :options="metricGroupPlanRestaurantOptions"
                                    placeholder="Выберите ресторан"
                                />
                            </div>
                            <p v-if="!metricGroupPlanRestaurantOptions.length" class="kpi-plan-editor__empty">
                                Нет доступных ресторанов для этой группы
                            </p>
                        </div>

                        <div
                            v-if="!activeMetricGroupPlanForm.isDynamic"
                            class="kpi-plan-editor__row kpi-plan-editor__row--static"
                        >
                            <div class="kpi-plan-editor__field kpi-plan-editor__field--value">
                                <label class="kpi-plan-editor__label">
                                    {{ activeMetricGroupPlanForm.planMode === 'per_restaurant' ? 'План для ресторана' : 'План на месяц' }}
                                </label>
                                <input
                                    v-model="activeMetricGroupPlanForm.constantValue"
                                    class="kpi-plan-editor__input kpi-plan-editor__input--compact"
                                    type="number"
                                    step="0.01"
                                    placeholder="0"
                                >
                            </div>
                        </div>
                        <div v-else class="kpi-plan-editor__grid">
                            <div v-for="month in months" :key="month.month" class="kpi-plan-editor__month-card">
                                <label class="kpi-plan-editor__month-label">{{ month.short }}</label>
                                <input
                                    v-model="activeMetricGroupPlanForm.months[month.month]"
                                    class="kpi-plan-editor__input"
                                    type="number"
                                    step="0.01"
                                    placeholder="0"
                                >
                            </div>
                        </div>
                    </div>
                </section>
            </div>

            <template #footer>
                <div class="kpi-metrics__modal-actions">
                    <button
                        type="button"
                        class="kpi-metrics__modal-icon-button kpi-metrics__modal-icon-button--primary"
                        :disabled="metricGroupSaving"
                        :title="metricGroupFormAction"
                        :aria-label="metricGroupFormAction"
                        @click="handleSaveMetricGroup"
                    >
                        <BaseIcon name="Save" />
                    </button>
                </div>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import {
    createKpiMetricGroup,
    createKpiMetricGroupRule,
    createKpiMetric,
    createKpiRule,
    deleteKpiMetricGroup,
    deleteKpiMetricGroupRule,
    deleteKpiRule,
    deleteKpiMetric,
    fetchAccessPositions,
    fetchAllEmployees,
    fetchEmployees,
    fetchKpiMetricGroups,
    fetchKpiMetricGroupPlanFacts,
    fetchKpiMetricGroupPlanFactsBulk,
    fetchKpiMetricGroupPlanPreferences,
    fetchKpiMetricGroupRules,
    fetchKpiPlanFacts,
    fetchKpiPlanFactsBulk,
    fetchKpiPlanPreferences,
    fetchKpiMetrics,
    fetchKpiRules,
    fetchPayrollAdjustmentTypes,
    fetchRestaurantSubdivisions,
    fetchRestaurants,
    upsertKpiMetricGroupPlanFactsBulk,
    upsertKpiMetricGroupPlanPreference,
    upsertKpiPlanFactsBulk,
    upsertKpiPlanPreference,
    updateKpiMetricGroup,
    updateKpiMetricGroupRule,
    updateKpiMetric,
    updateKpiRule,
} from '@/api';
import { useDebounce } from '@/composables/useDebounce';
import { useToast } from 'vue-toastification';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';

const toast = useToast();

const contentView = ref('metrics');
const metrics = ref([]);
const metricsCatalog = ref([]);
const metricsTotal = ref(0);
const metricsLoading = ref(false);
const metricStatusFilter = ref('active');
const metricSaving = ref(false);
const metricDeletingId = ref(null);
const metricEditingId = ref(null);
const isModalOpen = ref(false);
const metricGroups = ref([]);
const metricGroupsLoading = ref(false);
const metricGroupStatusFilter = ref('active');
const metricGroupSaving = ref(false);
const metricGroupDeletingId = ref(null);
const metricGroupEditingId = ref(null);
const isGroupModalOpen = ref(false);
const metricGroupRules = ref([]);
const metricGroupRulesLoading = ref(false);
const metricGroupTabs = [
    { value: 'info', label: 'Основное', requiresGroup: false },
    { value: 'rules', label: 'Правила', requiresGroup: true },
    { value: 'plans', label: 'Плановые показатели', requiresGroup: true },
];
const metricGroupActiveTab = ref('info');
const kpiTabs = [
    { value: 'info', label: 'Основное', requiresMetric: false },
    { value: 'rules', label: 'Правила', requiresMetric: true },
    { value: 'plans', label: 'Плановые показатели', requiresMetric: true },
];
const activeTab = ref('info');
const planYear = ref(new Date().getFullYear());
const planForms = ref({});
const planFactsByMetric = ref({});
const planSaving = ref({});
const planPrefsByMetric = ref({});
const planPrefPersistTimers = new Map();
const metricGroupPlanForms = ref({});
const metricGroupPlanFactsByGroup = ref({});
const metricGroupPlanSaving = ref({});
const metricGroupPlanPrefsByGroup = ref({});
const metricGroupPlanPrefPersistTimers = new Map();
const restaurants = ref([]);
const adjustmentTypes = ref([]);
const metricRules = ref([]);
const rulesLoading = ref(false);
const ruleSaving = ref(false);
const ruleDeletingId = ref(null);
const ruleEditingId = ref(null);
const isRuleModalOpen = ref(false);
const ruleMode = ref('metric');
const positions = ref([]);
const subdivisions = ref([]);
const employeeSearch = ref('');
const employeeSearchResults = ref([]);
const employeeSearchLoading = ref(false);
const employeeDirectory = ref([]);
const ruleOptionsLoaded = ref(false);
const ruleActionRows = ref([]);
const isMetricRestaurantSelectOpen = ref(false);
const isMetricGroupMembersSelectOpen = ref(false);
const isRuleSubdivisionSelectOpen = ref(false);
const isRulePositionSelectOpen = ref(false);
const metricRestaurantSelectRef = ref(null);
const metricGroupMembersSelectRef = ref(null);
const ruleSubdivisionSelectRef = ref(null);
const rulePositionSelectRef = ref(null);
let ruleActionRowCounter = 0;

const contentViewOptions = [
    { value: 'metrics', label: 'Показатели' },
    { value: 'groups', label: 'Группы KPI' },
];
const metricStatusOptions = [
    { value: 'active', label: 'Действующие' },
    { value: 'archived', label: 'Архивные' },
];

const unitOptions = [
    { value: null, label: 'Без единицы' },
    { value: '₽', label: '₽ (рубли)' },
    { value: '%', label: '% (проценты)' },
    { value: 'шт', label: 'шт' },
    { value: 'балл', label: 'баллы' },
];

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
const currentMonth = new Date().getMonth() + 1;

const comparisonOptions = [
    { value: 'gte', label: 'больше или равно' },
    { value: 'gt', label: 'больше' },
    { value: 'lte', label: 'меньше или равно' },
    { value: 'lt', label: 'меньше' },
    { value: 'eq', label: 'равно' },
];
const comparisonBasisOptions = [
    { value: 'absolute', label: 'Абсолютное значение' },
    { value: 'plan_percent', label: 'Выполнение плана, %' },
    { value: 'plan_delta_percent', label: 'Отклонение от плана, %' },
];
const effectTypeOptions = [
    { value: 'none', label: 'Нет' },
    { value: 'fixed', label: 'Фиксированная сумма' },
    { value: 'percent', label: 'Процент' },
];
const effectTypeLineOptions = [
    { value: 'none', label: 'Нет' },
    { value: 'fixed', label: 'Фиксированная сумма' },
    { value: 'percent', label: 'Процент' },
];
const rulePlanSourceOptions = [
    { value: 'plan', label: 'Из плановых показателей' },
    { value: 'custom', label: 'Свое значение' },
];
const ruleActionTypeOptions = [
    { value: 'bonus', label: 'Премия (+)' },
    { value: 'penalty', label: 'Удержание (-)' },
];

const metricForm = ref(defaultMetricForm());
const metricGroupForm = ref(defaultMetricGroupForm());
const ruleForm = ref(defaultRuleForm());

function defaultMetricForm() {
    return {
        code: '',
        name: '',
        description: '',
        unit: null,
        groupId: null,
        useMaxScale: false,
        maxScaleValue: '',
        planDirection: 'higher_better',
        isActive: true,
        allRestaurants: true,
        restaurantIds: [],
        bonusAdjustmentTypeId: null,
        penaltyAdjustmentTypeId: null,
    };
}

function defaultMetricGroupForm() {
    return {
        name: '',
        description: '',
        unit: null,
        memberIds: [],
        useMaxScale: false,
        maxScaleValue: '',
        planDirection: 'higher_better',
        planTargetPercent: '100',
        bonusAdjustmentTypeId: null,
        penaltyAdjustmentTypeId: null,
    };
}

function defaultRuleForm() {
    return {
        metricId: null,
        groupId: null,
        comparisonBasis: 'absolute',
        subdivisionId: null,
        allPositions: true,
        positionIds: [],
        isIndividual: false,
        employeeId: null,
        targetValue: '',
        warningValue: '',
        bonusCondition: 'gte',
        bonusType: 'none',
        bonusValue: '',
        penaltyCondition: 'lte',
        penaltyType: 'none',
        penaltyValue: '',
        isActive: true,
    };
}

const metricFormTitle = computed(() =>
    metricEditingId.value ? 'Редактировать показатель' : 'Новый показатель',
);
const metricFormAction = computed(() => (metricEditingId.value ? 'Сохранить' : 'Создать'));
const metricGroupFormAction = computed(() => (metricGroupEditingId.value ? 'Сохранить группу' : 'Создать группу'));
const metricGroupFormTitle = computed(() =>
    metricGroupEditingId.value ? 'Редактировать группу KPI' : 'Новая группа KPI',
);
const ruleFormTitle = computed(() =>
    ruleEditingId.value
        ? (ruleMode.value === 'group' ? 'Редактировать правило группы' : 'Редактировать правило')
        : (ruleMode.value === 'group' ? 'Новое правило группы' : 'Новое правило'),
);
const ruleFormAction = computed(() => (ruleEditingId.value ? 'Сохранить' : 'Создать'));
const restaurantOptions = computed(() =>
    restaurants.value.map((rest) => ({
        value: Number(rest.id),
        label: rest.name,
    })),
);
const activeMetric = computed(() =>
    metrics.value.find((metric) => Number(metric.id) === Number(metricEditingId.value)) || null,
);
const activeMetricGroup = computed(() =>
    metricGroups.value.find((group) => Number(group.id) === Number(metricGroupEditingId.value)) || null,
);
const activePlanForm = computed(() =>
    metricEditingId.value ? planForms.value[metricEditingId.value] : null,
);
const activeMetricGroupPlanForm = computed(() =>
    metricGroupEditingId.value ? metricGroupPlanForms.value[metricGroupEditingId.value] : null,
);
const rulePlanReferenceMonth = computed(() =>
    normalizeMonth(
        ruleMode.value === 'group'
            ? activeMetricGroupPlanForm.value?.selectedMonth ?? currentMonth
            : activePlanForm.value?.selectedMonth ?? currentMonth,
    ),
);
const rulePlanReferenceValue = computed(() => {
    if (ruleMode.value === 'group') {
        return parseNumber(activeMetricGroup.value?.plan_target_percent);
    }
    const month = rulePlanReferenceMonth.value;
    const raw = activePlanForm.value?.months?.[month];
    return parseNumber(raw);
});
const rulePlanReferenceDisplay = computed(() => {
    if (rulePlanReferenceValue.value === null) {
        return 'Не задан';
    }
    return formatNumber(rulePlanReferenceValue.value);
});
const planRestaurantOptions = computed(() =>
    activeMetric.value ? metricRestaurantOptions(activeMetric.value) : [],
);
const metricGroupPlanRestaurantOptions = computed(() =>
    activeMetricGroup.value ? metricGroupRestaurantOptions(activeMetricGroup.value) : [],
);
const bonusAdjustmentTypeOptions = computed(() => {
    const types = adjustmentTypes.value.filter((type) => type.kind === 'accrual');
    return [
        { value: null, label: 'Не выбрано' },
        ...types.map((type) => ({ value: Number(type.id), label: type.name })),
    ];
});
const penaltyAdjustmentTypeOptions = computed(() => {
    const types = adjustmentTypes.value.filter((type) => type.kind === 'deduction');
    return [
        { value: null, label: 'Не выбрано' },
        ...types.map((type) => ({ value: Number(type.id), label: type.name })),
    ];
});
const adjustmentTypeLabels = computed(() => {
    const map = new Map();
    adjustmentTypes.value.forEach((type) => {
        const id = Number(type?.id);
        if (!Number.isFinite(id)) return;
        map.set(id, type.name || `Тип ${id}`);
    });
    return map;
});
const metricGroupOptions = computed(() => [
    { value: null, label: 'Без группы' },
    ...metricGroups.value.map((group) => ({
        value: Number(group.id),
        label: group.name,
    })),
]);
const metricGroupMemberOptions = computed(() =>
    metricsCatalog.value.map((metric) => {
        const groupName = metric?.group?.name || null;
        return {
            value: Number(metric.id),
            label: groupName ? `${metric.name} (${groupName})` : metric.name,
        };
    }),
);
const subdivisionOptions = computed(() =>
    subdivisions.value.map((sub) => ({ value: Number(sub.id), label: sub.name })),
);
const positionOptions = computed(() => {
    if (!ruleForm.value.subdivisionId) {
        return positions.value.map((pos) => ({ value: Number(pos.id), label: pos.name }));
    }
    const filtered = positions.value.filter(
        (pos) => Number(pos.restaurant_subdivision_id) === Number(ruleForm.value.subdivisionId),
    );
    return filtered.map((pos) => ({ value: Number(pos.id), label: pos.name }));
});
const employeeDirectoryMap = computed(() => {
    const map = new Map();
    employeeDirectory.value.forEach((employee) => {
        const id = Number(employee?.id);
        if (Number.isFinite(id)) {
            map.set(id, employee);
        }
    });
    return map;
});
const employeeOptions = computed(() => {
    const options = [];
    const seen = new Set();
    const pushEmployee = (employee) => {
        const id = Number(employee?.id);
        if (!Number.isFinite(id) || seen.has(id)) {
            return;
        }
        seen.add(id);
        options.push({
            value: id,
            label: formatFullName(employee),
        });
    };
    employeeSearchResults.value.forEach(pushEmployee);
    if (
        ruleForm.value.employeeId &&
        !seen.has(Number(ruleForm.value.employeeId))
    ) {
        const selectedEmployee = employeeDirectoryMap.value.get(Number(ruleForm.value.employeeId));
        if (selectedEmployee) {
            options.unshift({
                value: Number(selectedEmployee.id),
                label: formatFullName(selectedEmployee),
            });
        } else {
            options.unshift({ value: ruleForm.value.employeeId, label: `ID ${ruleForm.value.employeeId}` });
        }
    }
    return options;
});
const ruleSubdivisionSelectionLabel = computed(() => {
    if (ruleForm.value.subdivisionId === null || ruleForm.value.subdivisionId === undefined) {
        return 'Все подразделения';
    }
    const item = subdivisionOptions.value.find(
        (subdivision) => Number(subdivision.value) === Number(ruleForm.value.subdivisionId),
    );
    return item?.label || `Подразделение ${ruleForm.value.subdivisionId}`;
});
const metricRestaurantSelectionCount = computed(() => metricForm.value.restaurantIds.length);
const metricRestaurantSelectionLabel = computed(() => {
    if (!restaurantOptions.value.length) {
        return 'Нет доступных ресторанов';
    }
    const selectedIds = new Set(
        (metricForm.value.restaurantIds || []).map((id) => Number(id)).filter((id) => Number.isFinite(id)),
    );
    const selected = restaurantOptions.value.filter((item) => selectedIds.has(Number(item.value)));
    if (!selected.length) {
        return 'Выберите рестораны';
    }
    if (selected.length <= 2) {
        return selected.map((item) => item.label).join(', ');
    }
    return `Выбрано: ${selected.length}`;
});
const metricGroupMemberSelectionCount = computed(() => metricGroupForm.value.memberIds.length);
const metricGroupMemberSelectionLabel = computed(() => {
    if (!metricGroupMemberOptions.value.length) {
        return 'Нет доступных показателей';
    }
    const selectedIds = new Set(
        (metricGroupForm.value.memberIds || []).map((id) => Number(id)).filter((id) => Number.isFinite(id)),
    );
    const selected = metricGroupMemberOptions.value.filter((item) => selectedIds.has(Number(item.value)));
    if (!selected.length) {
        return 'Выберите показатели';
    }
    if (selected.length <= 2) {
        return selected.map((item) => item.label).join(', ');
    }
    return `Выбрано: ${selected.length}`;
});
const rulePositionSelectionCount = computed(() => ruleForm.value.positionIds.length);
const rulePositionSelectionLabel = computed(() => {
    if (ruleForm.value.allPositions) {
        return 'Все должности';
    }
    if (!positionOptions.value.length) {
        return 'Нет доступных должностей';
    }
    const selectedIds = new Set(
        (ruleForm.value.positionIds || []).map((id) => Number(id)).filter((id) => Number.isFinite(id)),
    );
    const selected = positionOptions.value.filter((item) => selectedIds.has(Number(item.value)));
    if (!selected.length) {
        return 'Выберите должности';
    }
    if (selected.length <= 2) {
        return selected.map((item) => item.label).join(', ');
    }
    return `Выбрано: ${selected.length}`;
});
const rulePositionHasSelection = computed(() => ruleForm.value.allPositions || rulePositionSelectionCount.value > 0);
const canAddRuleActionRow = computed(() => ruleActionRows.value.length < ruleActionTypeOptions.length);
const isCurrentViewRefreshing = computed(() =>
    contentView.value === 'metrics' ? metricsLoading.value : metricGroupsLoading.value,
);
const currentStatusFilter = computed(() =>
    contentView.value === 'metrics' ? metricStatusFilter.value : metricGroupStatusFilter.value,
);
const visibleMetricGroups = computed(() =>
    metricGroups.value.filter((group) => {
        const isArchived = isMetricGroupArchived(group);
        return metricGroupStatusFilter.value === 'archived' ? isArchived : !isArchived;
    }),
);

function normalizeMetricCode(value) {
    return String(value || '')
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '')
        .slice(0, 100);
}

function generateMetricCode(name) {
    const base = normalizeMetricCode(name);
    const fallback = `kpi_${Date.now()}`;
    const existingCodes = new Set(
        metrics.value.map((metric) => String(metric.code || '').toLowerCase()),
    );
    let code = base || fallback;
    if (!existingCodes.has(code)) {
        return code;
    }
    let counter = 2;
    while (existingCodes.has(`${code}_${counter}`)) {
        counter += 1;
    }
    return `${code}_${counter}`;
}

function parseNumber(value) {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(String(value).replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : null;
}

async function upsertPlanFactsInBatches(payloads, batchSize = 20) {
    for (let index = 0; index < payloads.length; index += batchSize) {
        const chunk = payloads.slice(index, index + batchSize);
        await upsertKpiPlanFactsBulk(chunk);
    }
}

function normalizePlanPreference(pref) {
    if (!pref || pref.metric_id === null || pref.metric_id === undefined) return null;
    return {
        metricId: Number(pref.metric_id),
        planMode: pref.plan_mode === 'per_restaurant' ? 'per_restaurant' : 'shared',
        restaurantId:
            pref.restaurant_id !== null && pref.restaurant_id !== undefined
                ? Number(pref.restaurant_id)
                : null,
        isDynamic: Boolean(pref.is_dynamic),
        selectedMonth: pref.selected_month !== null && pref.selected_month !== undefined
            ? Number(pref.selected_month)
            : null,
    };
}

async function loadPlanPreferences(metricId = null) {
    try {
        const params = {};
        if (metricId !== null && metricId !== undefined) {
            params.metric_id = Number(metricId);
        }
        const data = await fetchKpiPlanPreferences(params);
        const items = Array.isArray(data?.items) ? data.items : data || [];

        const next = metricId !== null && metricId !== undefined
            ? { ...(planPrefsByMetric.value || {}) }
            : {};

        if (metricId !== null && metricId !== undefined) {
            delete next[String(metricId)];
        }

        items.forEach((item) => {
            const normalized = normalizePlanPreference(item);
            if (!normalized) return;
            next[String(normalized.metricId)] = normalized;
        });

        planPrefsByMetric.value = next;
    } catch (error) {
        console.error('Failed to load KPI plan preferences', error);
    }
}

async function persistPlanPreference(metricId) {
    if (!metricId) return;
    const form = planForms.value?.[metricId];
    if (!form) return;

    const payload = {
        metric_id: Number(metricId),
        plan_mode: form.planMode === 'per_restaurant' ? 'per_restaurant' : 'shared',
        restaurant_id:
            form.restaurantId !== null && form.restaurantId !== undefined
                ? Number(form.restaurantId)
                : null,
        is_dynamic: Boolean(form.isDynamic),
        selected_month: form.isDynamic ? (Number(form.selectedMonth) || null) : null,
    };

    try {
        const saved = await upsertKpiPlanPreference(payload);
        const normalized = normalizePlanPreference(saved);
        if (!normalized) return;
        planPrefsByMetric.value = {
            ...(planPrefsByMetric.value || {}),
            [String(normalized.metricId)]: normalized,
        };
    } catch (error) {
        console.error('Failed to save KPI plan preferences', error);
    }
}

function schedulePlanPreferencePersist(metricId, delayMs = 500) {
    if (!metricId) return;
    const key = Number(metricId);
    const current = planPrefPersistTimers.get(key);
    if (current) {
        clearTimeout(current);
    }
    const timeoutId = setTimeout(async () => {
        planPrefPersistTimers.delete(key);
        await persistPlanPreference(key);
    }, delayMs);
    planPrefPersistTimers.set(key, timeoutId);
}

function normalizeMetricGroupPlanPreference(pref) {
    if (!pref || pref.group_id === null || pref.group_id === undefined) return null;
    return {
        groupId: Number(pref.group_id),
        planMode: pref.plan_mode === 'per_restaurant' ? 'per_restaurant' : 'shared',
        restaurantId:
            pref.restaurant_id !== null && pref.restaurant_id !== undefined
                ? Number(pref.restaurant_id)
                : null,
        isDynamic: Boolean(pref.is_dynamic),
        selectedMonth: pref.selected_month !== null && pref.selected_month !== undefined
            ? Number(pref.selected_month)
            : null,
    };
}

async function loadMetricGroupPlanPreferences(groupId = null) {
    try {
        const params = {};
        if (groupId !== null && groupId !== undefined) {
            params.group_id = Number(groupId);
        }
        const data = await fetchKpiMetricGroupPlanPreferences(params);
        const items = Array.isArray(data?.items) ? data.items : data || [];

        const next = groupId !== null && groupId !== undefined
            ? { ...(metricGroupPlanPrefsByGroup.value || {}) }
            : {};

        if (groupId !== null && groupId !== undefined) {
            delete next[String(groupId)];
        }

        items.forEach((item) => {
            const normalized = normalizeMetricGroupPlanPreference(item);
            if (!normalized) return;
            next[String(normalized.groupId)] = normalized;
        });

        metricGroupPlanPrefsByGroup.value = next;
    } catch (error) {
        console.error('Failed to load KPI group plan preferences', error);
    }
}

async function persistMetricGroupPlanPreference(groupId) {
    if (!groupId) return;
    const form = metricGroupPlanForms.value?.[groupId];
    if (!form) return;

    const payload = {
        group_id: Number(groupId),
        plan_mode: form.planMode === 'per_restaurant' ? 'per_restaurant' : 'shared',
        restaurant_id:
            form.restaurantId !== null && form.restaurantId !== undefined
                ? Number(form.restaurantId)
                : null,
        is_dynamic: Boolean(form.isDynamic),
        selected_month: form.isDynamic ? (Number(form.selectedMonth) || null) : null,
    };

    try {
        const saved = await upsertKpiMetricGroupPlanPreference(payload);
        const normalized = normalizeMetricGroupPlanPreference(saved);
        if (!normalized) return;
        metricGroupPlanPrefsByGroup.value = {
            ...(metricGroupPlanPrefsByGroup.value || {}),
            [String(normalized.groupId)]: normalized,
        };
    } catch (error) {
        console.error('Failed to save KPI group plan preferences', error);
    }
}

function scheduleMetricGroupPlanPreferencePersist(groupId, delayMs = 500) {
    if (!groupId) return;
    const key = Number(groupId);
    const current = metricGroupPlanPrefPersistTimers.get(key);
    if (current) {
        clearTimeout(current);
    }
    const timeoutId = setTimeout(async () => {
        metricGroupPlanPrefPersistTimers.delete(key);
        await persistMetricGroupPlanPreference(key);
    }, delayMs);
    metricGroupPlanPrefPersistTimers.set(key, timeoutId);
}

function formatNumberInput(value) {
    const parsed = parseNumber(value);
    return parsed === null ? '' : String(parsed);
}

function nextRuleActionRowId() {
    ruleActionRowCounter += 1;
    return `kpi-rule-action-${ruleActionRowCounter}`;
}

function createRuleActionRow(type = 'bonus', source = {}) {
    return {
        id: nextRuleActionRowId(),
        type,
        planSource: source.planSource ?? 'plan',
        planValue: source.planValue ?? '',
        effectType: source.effectType ?? 'fixed',
        effectValue: source.effectValue ?? '',
    };
}

function ruleActionTypeOptionsForRow(rowId) {
    const row = (ruleActionRows.value || []).find((item) => item.id === rowId);
    const currentType = row?.type || null;
    const usedTypes = new Set(
        (ruleActionRows.value || [])
            .filter((item) => item.id !== rowId)
            .map((item) => item.type),
    );
    return ruleActionTypeOptions.filter(
        (option) => option.value === currentType || !usedTypes.has(option.value),
    );
}

function addRuleActionRow() {
    if (!canAddRuleActionRow.value) {
        return;
    }
    const used = new Set((ruleActionRows.value || []).map((item) => item.type));
    const nextType = ruleActionTypeOptions.find((item) => !used.has(item.value))?.value || 'bonus';
    ruleActionRows.value = [
        ...ruleActionRows.value,
        createRuleActionRow(nextType, { planSource: rulePlanReferenceValue.value === null ? 'custom' : 'plan' }),
    ];
}

function handleRulePlanSourceChange(row, value) {
    if (!row) return;
    row.planSource = value;
    row.planValue = '';
}

function removeRuleActionRow(rowId) {
    const nextRows = (ruleActionRows.value || []).filter((item) => item.id !== rowId);
    if (!nextRows.length) {
        return;
    }
    ruleActionRows.value = nextRows;
}

function syncRuleActionRowsFromRuleForm() {
    const planValue = rulePlanReferenceValue.value;
    const toAbsoluteThreshold = (rawValue) => {
        const numeric = parseNumber(rawValue);
        if (numeric === null) {
            return null;
        }
        if (ruleForm.value.comparisonBasis === 'plan_percent' && planValue !== null) {
            return (planValue * numeric) / 100;
        }
        if (ruleForm.value.comparisonBasis === 'plan_delta_percent' && planValue !== null) {
            return planValue * (1 + (numeric / 100));
        }
        return numeric;
    };
    const resolvePlanSource = (absoluteValue) => {
        if (absoluteValue === null) {
            return planValue === null ? 'custom' : 'plan';
        }
        if (planValue !== null && Math.abs(Number(absoluteValue) - Number(planValue)) < 0.000001) {
            return 'plan';
        }
        return 'custom';
    };

    const rows = [];
    const canPrefillCustomValue = ruleForm.value.comparisonBasis === 'absolute';
    if (String(ruleForm.value.bonusType || 'none') !== 'none') {
        const thresholdValue = toAbsoluteThreshold(ruleForm.value.targetValue);
        const source = resolvePlanSource(thresholdValue);
        rows.push(
            createRuleActionRow('bonus', {
                planSource: source,
                planValue: source === 'custom' && canPrefillCustomValue ? formatNumberInput(thresholdValue) : '',
                effectType: ruleForm.value.bonusType || 'fixed',
                effectValue: ruleForm.value.bonusValue ?? '',
            }),
        );
    }
    if (String(ruleForm.value.penaltyType || 'none') !== 'none') {
        const thresholdValue = toAbsoluteThreshold(ruleForm.value.warningValue ?? ruleForm.value.targetValue);
        const source = resolvePlanSource(thresholdValue);
        rows.push(
            createRuleActionRow('penalty', {
                planSource: source,
                planValue: source === 'custom' && canPrefillCustomValue ? formatNumberInput(thresholdValue) : '',
                effectType: ruleForm.value.penaltyType || 'fixed',
                effectValue: ruleForm.value.penaltyValue ?? '',
            }),
        );
    }
    if (!rows.length) {
        rows.push(
            createRuleActionRow('bonus', {
                planSource: planValue === null ? 'custom' : 'plan',
                planValue: planValue === null ? formatNumberInput(toAbsoluteThreshold(ruleForm.value.targetValue)) : '',
            }),
        );
    }
    ruleActionRows.value = rows;
}

function comparisonLabel(value) {
    const option = comparisonOptions.find((item) => item.value === value);
    return option ? option.label : value;
}

function comparisonBasisLabel(value) {
    if (!value) {
        return '—';
    }
    const option = comparisonBasisOptions.find((item) => item.value === value);
    return option ? option.label : value;
}

function effectLabel(type, value) {
    const typeLabel = effectTypeOptions.find((item) => item.value === type)?.label || type;
    if (type === 'none') {
        return 'нет';
    }
    if (type === 'fixed') {
        return `${typeLabel}: ${formatNumber(value)}`;
    }
    return `${typeLabel}: ${formatNumber(value)} от итоговых часов`;
}

function formatNumber(value) {
    const num = Number(value || 0);
    return new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(num);
}

function formatFullName(employee) {
    if (!employee) return '—';
    const parts = [employee.last_name, employee.first_name, employee.middle_name].filter(Boolean);
    return parts.length ? parts.join(' ') : employee.username || `ID ${employee.id}`;
}

function employeeLabel(employeeId) {
    if (!employeeId) {
        return '—';
    }
    const employee = employeeDirectoryMap.value.get(Number(employeeId));
    return employee ? formatFullName(employee) : `ID ${employeeId}`;
}

function subdivisionLabel(positionId) {
    if (!positionId) {
        return 'Все подразделения';
    }
    const position = positions.value.find((item) => Number(item.id) === Number(positionId));
    const subdivisionId = position?.restaurant_subdivision_id;
    if (!subdivisionId) {
        return 'Без подразделения';
    }
    const subdivision = subdivisions.value.find((item) => Number(item.id) === Number(subdivisionId));
    return subdivision?.name || `Подразделение ${subdivisionId}`;
}

function positionLabel(id) {
    const pos = positions.value.find((item) => Number(item.id) === Number(id));
    return pos?.name || (id ? `Должность ${id}` : 'Все должности');
}

function restaurantLabel(id) {
    if (id === null || id === undefined) {
        return 'Все рестораны';
    }
    const rest = restaurants.value.find((item) => Number(item.id) === Number(id));
    return rest?.name || `Ресторан ${id}`;
}

function ruleRestaurantLabel(rule) {
    if (rule?.restaurant_id) {
        return restaurantLabel(rule.restaurant_id);
    }
    const metric = activeMetric.value;
    if (!metric) {
        return 'Все рестораны';
    }
    if (metric.all_restaurants !== false) {
        return 'Все рестораны';
    }
    const ids = Array.isArray(metric.restaurant_ids)
        ? metric.restaurant_ids.map((id) => Number(id)).filter((id) => Number.isFinite(id))
        : [];
    if (!ids.length) {
        return 'Рестораны не выбраны';
    }
    if (ids.length === 1) {
        return restaurantLabel(ids[0]);
    }
    return `Выбранные рестораны (${ids.length})`;
}

function metricRestaurantsSummary(metric) {
    if (!metric) {
        return 'Все рестораны';
    }
    if (metric.all_restaurants !== false) {
        return 'Все рестораны';
    }
    const ids = Array.isArray(metric.restaurant_ids)
        ? metric.restaurant_ids.map((id) => Number(id)).filter((id) => Number.isFinite(id))
        : [];
    if (!ids.length) {
        return 'Рестораны не выбраны';
    }
    const names = ids
        .map((id) => restaurantLabel(id))
        .filter(Boolean);
    if (!names.length) {
        return 'Рестораны не выбраны';
    }
    if (names.length <= 2) {
        return names.join(', ');
    }
    return `${names.slice(0, 2).join(', ')} +${names.length - 2}`;
}

function metricAdjustmentTypeLabel(adjustmentTypeId) {
    if (adjustmentTypeId === null || adjustmentTypeId === undefined) {
        return 'Не задан';
    }
    const id = Number(adjustmentTypeId);
    return adjustmentTypeLabels.value.get(id) || `Тип ${id}`;
}

function metricGroupLabel(metric) {
    return metric?.group?.name || 'Без группы';
}

function metricGroupMembers(group) {
    const groupId = Number(group?.id);
    if (!Number.isFinite(groupId) || groupId <= 0) {
        return [];
    }
    return metricsCatalog.value.filter((metric) => Number(metric?.group_id ?? metric?.group?.id) === groupId);
}

function metricGroupMembersSummary(group) {
    const members = metricGroupMembers(group);
    if (!members.length) {
        return 'Показатели не выбраны';
    }
    const names = members.map((metric) => metric.name).filter(Boolean);
    if (!names.length) {
        return `Выбрано: ${members.length}`;
    }
    if (names.length <= 2) {
        return names.join(', ');
    }
    return `${names.slice(0, 2).join(', ')} +${names.length - 2}`;
}

function isMetricGroupArchived(group) {
    const members = metricGroupMembers(group);
    if (!members.length) {
        return false;
    }
    return members.every((metric) => !metric?.is_active);
}

function setContentView(value) {
    if (!value || contentView.value === value) {
        return;
    }
    contentView.value = value;
    refreshCurrentView();
}

function setMetricStatusFilter(value) {
    if (!value || metricStatusFilter.value === value) {
        return;
    }
    metricStatusFilter.value = value;
    loadMetrics();
}

function setMetricGroupStatusFilter(value) {
    if (!value || metricGroupStatusFilter.value === value) {
        return;
    }
    metricGroupStatusFilter.value = value;
}

async function refreshCurrentView() {
    if (contentView.value === 'groups') {
        await Promise.all([loadMetricGroups(), loadMetricsCatalog()]);
        return;
    }
    await Promise.all([loadMetrics(), loadMetricsCatalog()]);
}

async function loadMetricsCatalog() {
    try {
        const data = await fetchKpiMetrics();
        metricsCatalog.value = Array.isArray(data?.items) ? data.items : data || [];
    } catch (error) {
        toast.error('Не удалось загрузить список KPI для групп');
        console.error(error);
    }
}

async function loadMetricGroups() {
    metricGroupsLoading.value = true;
    try {
        const data = await fetchKpiMetricGroups();
        metricGroups.value = Array.isArray(data?.items) ? data.items : data || [];
    } catch (error) {
        toast.error('Не удалось загрузить группы KPI');
        console.error(error);
    } finally {
        metricGroupsLoading.value = false;
    }
}

function resetMetricGroupForm() {
    metricGroupEditingId.value = null;
    metricGroupRules.value = [];
    metricGroupActiveTab.value = 'info';
    metricGroupForm.value = defaultMetricGroupForm();
    closeMetricGroupMembersSelect();
}

function openCreateMetricGroupModal() {
    resetMetricGroupForm();
    isGroupModalOpen.value = true;
    loadMetricsCatalog();
}

function closeMetricGroupsModal() {
    isGroupModalOpen.value = false;
    metricGroupSaving.value = false;
    metricGroupActiveTab.value = 'info';
    closeMetricGroupMembersSelect();
    resetMetricGroupForm();
}

function startEditMetricGroup(group) {
    if (!group) return;
    metricGroupEditingId.value = Number(group.id);
    const memberIds = metricGroupMembers(group)
        .map((metric) => Number(metric.id))
        .filter((id) => Number.isFinite(id));
    metricGroupForm.value = {
        name: group.name || '',
        description: group.description || '',
        unit: group.unit ?? null,
        memberIds,
        useMaxScale: Boolean(group.use_max_scale),
        maxScaleValue:
            group.max_scale_value !== null && group.max_scale_value !== undefined
                ? formatNumberInput(group.max_scale_value)
                : '',
        planDirection: group.plan_direction || 'higher_better',
        planTargetPercent:
            group.plan_target_percent !== null && group.plan_target_percent !== undefined
                ? String(group.plan_target_percent)
                : '100',
        bonusAdjustmentTypeId:
            group.bonus_adjustment_type_id !== null && group.bonus_adjustment_type_id !== undefined
                ? Number(group.bonus_adjustment_type_id)
                : null,
        penaltyAdjustmentTypeId:
            group.penalty_adjustment_type_id !== null && group.penalty_adjustment_type_id !== undefined
                ? Number(group.penalty_adjustment_type_id)
                : null,
    };
    loadMetricGroupRules(group.id);
}

async function openEditMetricGroupModal(group) {
    if (!group) return;
    startEditMetricGroup(group);
    await loadMetricGroupPlanPreferences(group.id);
    ensureMetricGroupPlanForm(group);
    metricGroupActiveTab.value = 'info';
    isGroupModalOpen.value = true;
    await loadMetricGroupPlanFacts(group.id);
}

function setActiveMetricGroupTab(tab) {
    if (!tab) {
        return;
    }
    if (tab.requiresGroup && !metricGroupEditingId.value) {
        toast.info('Сначала сохраните группу KPI, затем откроются правила и плановые показатели');
        metricGroupActiveTab.value = 'info';
        return;
    }
    metricGroupActiveTab.value = tab.value;
}

function formatMetricGroupTarget(value) {
    if (value === null || value === undefined || value === '') return '100%';
    const parsed = Number(String(value).replace(',', '.'));
    if (!Number.isFinite(parsed)) return '100%';
    return `${new Intl.NumberFormat('ru-RU', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    }).format(parsed)}%`;
}

async function syncMetricGroupMemberships(groupId) {
    const normalizedGroupId = Number(groupId);
    if (!Number.isFinite(normalizedGroupId) || normalizedGroupId <= 0) {
        return;
    }
    const selectedIds = new Set(
        (metricGroupForm.value.memberIds || [])
            .map((id) => Number(id))
            .filter((id) => Number.isFinite(id) && id > 0),
    );
    const updates = [];
    metricsCatalog.value.forEach((metric) => {
        const metricId = Number(metric?.id);
        if (!Number.isFinite(metricId) || metricId <= 0) {
            return;
        }
        const currentGroupId = Number(metric?.group_id ?? metric?.group?.id);
        const isCurrentlyInGroup = Number.isFinite(currentGroupId) && currentGroupId === normalizedGroupId;
        const shouldBeInGroup = selectedIds.has(metricId);
        if (shouldBeInGroup && !isCurrentlyInGroup) {
            updates.push(updateKpiMetric(metricId, { group_id: normalizedGroupId }));
        } else if (!shouldBeInGroup && isCurrentlyInGroup) {
            updates.push(updateKpiMetric(metricId, { group_id: null }));
        }
    });
    if (updates.length) {
        await Promise.all(updates);
    }
}

async function handleSaveMetricGroup() {
    const trimmedName = metricGroupForm.value.name.trim();
    if (!trimmedName) {
        toast.error('Укажите название группы KPI');
        return;
    }
    const targetPercent =
        metricGroupForm.value.planTargetPercent === ''
            ? 100
            : Number(String(metricGroupForm.value.planTargetPercent).replace(',', '.'));
    if (!Number.isFinite(targetPercent) || targetPercent < 0 || targetPercent > 100) {
        toast.error('Цель группы должна быть в диапазоне от 0 до 100%');
        return;
    }
    const parsedMaxScaleValue = parseNumber(metricGroupForm.value.maxScaleValue);
    if (metricGroupForm.value.useMaxScale && (parsedMaxScaleValue === null || parsedMaxScaleValue <= 0)) {
        toast.error('Укажите корректное максимальное значение шкалы группы');
        return;
    }

    const payload = {
        name: trimmedName,
        description: metricGroupForm.value.description?.trim() || null,
        unit: metricGroupForm.value.unit || null,
        use_max_scale: Boolean(metricGroupForm.value.useMaxScale),
        max_scale_value: metricGroupForm.value.useMaxScale ? parsedMaxScaleValue : null,
        plan_direction: metricGroupForm.value.planDirection || 'higher_better',
        plan_target_percent: targetPercent,
        bonus_adjustment_type_id:
            metricGroupForm.value.bonusAdjustmentTypeId !== null &&
            metricGroupForm.value.bonusAdjustmentTypeId !== undefined
                ? Number(metricGroupForm.value.bonusAdjustmentTypeId)
                : null,
        penalty_adjustment_type_id:
            metricGroupForm.value.penaltyAdjustmentTypeId !== null &&
            metricGroupForm.value.penaltyAdjustmentTypeId !== undefined
                ? Number(metricGroupForm.value.penaltyAdjustmentTypeId)
                : null,
    };

    metricGroupSaving.value = true;
    try {
        const isEditing = Boolean(metricGroupEditingId.value);
        const saved = isEditing
            ? await updateKpiMetricGroup(metricGroupEditingId.value, payload)
            : await createKpiMetricGroup(payload);
        const savedGroupId = Number(saved?.id || metricGroupEditingId.value);
        await syncMetricGroupMemberships(savedGroupId);
        toast.success(isEditing ? 'Группа KPI обновлена' : 'Группа KPI создана');
        await Promise.all([loadMetricGroups(), loadMetrics(), loadMetricsCatalog()]);
        const nextGroup = metricGroups.value.find((group) => Number(group.id) === savedGroupId) || saved || null;
        if (nextGroup) {
            startEditMetricGroup(nextGroup);
            await loadMetricGroupPlanPreferences(savedGroupId);
            ensureMetricGroupPlanForm(nextGroup);
            if (metricGroupActiveTab.value === 'plans') {
                await loadMetricGroupPlanFacts(savedGroupId);
            }
        }
        if (!isGroupModalOpen.value) {
            resetMetricGroupForm();
        }
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось сохранить группу KPI');
        console.error(error);
    } finally {
        metricGroupSaving.value = false;
    }
}

async function handleDeleteMetricGroup(group) {
    if (!group?.id) return;
    const groupName = group.name || activeMetricGroup.value?.name || 'без названия';
    if (!window.confirm(`Удалить группу KPI «${groupName}»?`)) return;

    metricGroupDeletingId.value = Number(group.id);
    try {
        await deleteKpiMetricGroup(group.id);
        if (Number(metricForm.value.groupId) === Number(group.id)) {
            metricForm.value.groupId = null;
        }
        toast.success('Группа KPI удалена');
        await Promise.all([loadMetricGroups(), loadMetrics(), loadMetricsCatalog()]);
        if (metricGroupEditingId.value === Number(group.id)) {
            closeMetricGroupsModal();
        }
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось удалить группу KPI');
        console.error(error);
    } finally {
        metricGroupDeletingId.value = null;
    }
}

function setActiveTab(tab) {
    if (!tab) {
        return;
    }
    if (tab.requiresMetric && !metricEditingId.value) {
        toast.info('Сначала сохраните показатель KPI, затем откроются правила и плановые показатели');
        activeTab.value = 'info';
        return;
    }
    activeTab.value = tab.value;
}

function normalizeMonth(value) {
    const month = Number(value);
    return months.some((item) => Number(item.month) === month) ? month : currentMonth;
}

function buildPlanForm(
    metricId,
    monthMap = {},
    restaurantId = null,
    planMode = 'shared',
    {
        selectedMonth = currentMonth,
    } = {},
) {
    const monthValues = {};
    const distinctValues = new Set();
    months.forEach(({ month }) => {
        const rawPlanValue = monthMap?.[month]?.plan_value;
        const planValue = rawPlanValue ?? null;
        monthValues[month] = planValue === null || planValue === undefined ? '' : formatNumberInput(planValue);
        if (planValue !== null && planValue !== undefined) {
            distinctValues.add(formatNumberInput(planValue));
        }
    });

    const filledMonths = months.filter(({ month }) => monthValues[month] !== '').length;
    let isDynamic = false;
    let constantValue = '';

    if (filledMonths === 0) {
        isDynamic = false;
    } else if (distinctValues.size === 1) {
        isDynamic = false;
        constantValue = Array.from(distinctValues)[0];
    } else {
        isDynamic = true;
    }

    const normalizedSelectedMonth = normalizeMonth(selectedMonth);
    if (!constantValue && monthValues[normalizedSelectedMonth] !== '') {
        constantValue = monthValues[normalizedSelectedMonth];
    }
    if (!constantValue) {
        const firstFilled = months.find(({ month }) => monthValues[month] !== '');
        if (firstFilled) {
            constantValue = monthValues[firstFilled.month];
        }
    }

    return {
        metricId,
        restaurantId,
        planMode,
        isDynamic,
        constantValue,
        selectedMonth: normalizedSelectedMonth,
        months: monthValues,
    };
}

function metricRestaurantOptions(metric) {
    if (!metric) return [];
    const allowedIds = metric.all_restaurants === false && Array.isArray(metric.restaurant_ids)
        ? metric.restaurant_ids.map((id) => Number(id))
        : null;
    const list = restaurants.value || [];
    const filtered = allowedIds
        ? list.filter((rest) => allowedIds.includes(Number(rest.id)))
        : list;
    return filtered.map((rest) => ({
        value: Number(rest.id),
        label: rest.name,
    }));
}

function ensurePlanForm(metric) {
    if (!metric) return;
    const options = metricRestaurantOptions(metric);
    const defaultRestaurantId = options[0]?.value ?? null;
    const pref = planPrefsByMetric.value?.[String(metric.id)] || null;
    const preferredMode = pref?.planMode === 'per_restaurant' ? 'per_restaurant' : 'shared';
    const preferredRestaurantId =
        pref?.restaurantId !== null && pref?.restaurantId !== undefined ? Number(pref.restaurantId) : null;
    const preferredIsDynamic = typeof pref?.isDynamic === 'boolean' ? pref.isDynamic : null;
    const preferredSelectedMonth = normalizeMonth(pref?.selectedMonth);
    const resolvedPreferredRestaurantId =
        preferredRestaurantId !== null && options.some((opt) => Number(opt.value) === preferredRestaurantId)
            ? preferredRestaurantId
            : null;
    if (!planForms.value[metric.id]) {
        const createdForm = buildPlanForm(
            metric.id,
            {},
            resolvedPreferredRestaurantId ?? defaultRestaurantId,
            preferredMode,
            { selectedMonth: preferredSelectedMonth },
        );
        if (preferredIsDynamic !== null) {
            createdForm.isDynamic = preferredIsDynamic;
        }
        planForms.value[metric.id] = createdForm;
        return;
    }
    const form = planForms.value[metric.id];
    if (!form.planMode) {
        form.planMode = preferredMode;
    }
    if (!form.restaurantId || !options.some((opt) => Number(opt.value) === Number(form.restaurantId))) {
        form.restaurantId = resolvedPreferredRestaurantId ?? defaultRestaurantId;
    }
    form.selectedMonth = normalizeMonth(form.selectedMonth ?? preferredSelectedMonth);
    if (typeof form.isDynamic !== 'boolean' && preferredIsDynamic !== null) {
        form.isDynamic = preferredIsDynamic;
    }
}

function metricGroupRestaurantOptions(group) {
    if (!group) {
        return restaurantOptions.value;
    }
    const selectedMetricIds = (metricGroupForm.value.memberIds || [])
        .map((id) => Number(id))
        .filter((id) => Number.isFinite(id) && id > 0);
    const members = selectedMetricIds.length
        ? metricsCatalog.value.filter((metric) => selectedMetricIds.includes(Number(metric.id)))
        : metricGroupMembers(group);
    if (!members.length) {
        return restaurantOptions.value;
    }

    const allowedIds = new Set();
    members.forEach((metric) => {
        if (metric?.all_restaurants !== false) {
            restaurantOptions.value.forEach((rest) => allowedIds.add(Number(rest.value)));
            return;
        }
        metricRestaurantOptions(metric).forEach((rest) => allowedIds.add(Number(rest.value)));
    });

    const filtered = restaurantOptions.value.filter((rest) => allowedIds.has(Number(rest.value)));
    return filtered.length ? filtered : restaurantOptions.value;
}

function ensureMetricGroupPlanForm(group) {
    if (!group) return;
    const options = metricGroupRestaurantOptions(group);
    const defaultRestaurantId = options[0]?.value ?? null;
    const pref = metricGroupPlanPrefsByGroup.value?.[String(group.id)] || null;
    const preferredMode = pref?.planMode === 'per_restaurant' ? 'per_restaurant' : 'shared';
    const preferredRestaurantId =
        pref?.restaurantId !== null && pref?.restaurantId !== undefined ? Number(pref.restaurantId) : null;
    const preferredIsDynamic = typeof pref?.isDynamic === 'boolean' ? pref.isDynamic : null;
    const preferredSelectedMonth = normalizeMonth(pref?.selectedMonth);
    const resolvedPreferredRestaurantId =
        preferredRestaurantId !== null && options.some((opt) => Number(opt.value) === preferredRestaurantId)
            ? preferredRestaurantId
            : null;
    if (!metricGroupPlanForms.value[group.id]) {
        const createdForm = buildPlanForm(
            group.id,
            {},
            resolvedPreferredRestaurantId ?? defaultRestaurantId,
            preferredMode,
            { selectedMonth: preferredSelectedMonth },
        );
        if (preferredIsDynamic !== null) {
            createdForm.isDynamic = preferredIsDynamic;
        }
        metricGroupPlanForms.value[group.id] = createdForm;
        return;
    }
    const form = metricGroupPlanForms.value[group.id];
    if (!form.planMode) {
        form.planMode = preferredMode;
    }
    if (!form.restaurantId || !options.some((opt) => Number(opt.value) === Number(form.restaurantId))) {
        form.restaurantId = resolvedPreferredRestaurantId ?? defaultRestaurantId;
    }
    form.selectedMonth = normalizeMonth(form.selectedMonth ?? preferredSelectedMonth);
    if (typeof form.isDynamic !== 'boolean' && preferredIsDynamic !== null) {
        form.isDynamic = preferredIsDynamic;
    }
}

async function loadMetrics() {
    metricsLoading.value = true;
    try {
        const data = await fetchKpiMetrics({
            is_active: metricStatusFilter.value === 'active',
        });
        metrics.value = Array.isArray(data?.items) ? data.items : data || [];
        metricsTotal.value = Number(data?.total) || metrics.value.length;
    } catch (error) {
        toast.error('Не удалось загрузить показатели');
        console.error(error);
    } finally {
        metricsLoading.value = false;
    }
}

async function loadPlanFactsForMetric(metricId) {
    const form = planForms.value?.[metricId];
    if (!form) {
        return;
    }
    const options = metricRestaurantOptions(activeMetric.value);
    const targetRestaurantId =
        form.planMode === 'per_restaurant' ? form.restaurantId : form.restaurantId || options[0]?.value || null;
    if (!targetRestaurantId) {
        return;
    }

    try {
        const yearValue = Number(planYear.value);
        const data = await fetchKpiPlanFacts({
            metric_id: metricId,
            restaurant_id: Number(targetRestaurantId),
            year: yearValue,
        });
        const items = Array.isArray(data?.items) ? data.items : data || [];
        const monthMap = {};
        items.forEach((item) => {
            monthMap[Number(item.month)] = {
                plan_value: item.plan_value ?? null,
                fact_value: item.fact_value ?? null,
            };
        });
        planFactsByMetric.value = {
            ...planFactsByMetric.value,
            [metricId]: {
                restaurantId: Number(targetRestaurantId),
                months: monthMap,
            },
        };
        const pref = planPrefsByMetric.value?.[String(metricId)] || null;
        const preferredIsDynamic = typeof pref?.isDynamic === 'boolean' ? pref.isDynamic : null;
        const preferredSelectedMonth = normalizeMonth(pref?.selectedMonth);
        const builtForm = buildPlanForm(
            metricId,
            monthMap,
            Number(targetRestaurantId),
            form.planMode || 'shared',
            { selectedMonth: form.selectedMonth ?? preferredSelectedMonth },
        );
        const hasPlanData = Object.values(builtForm.months).some((value) => value !== '');
        const resolvedIsDynamic = preferredIsDynamic !== null
            ? preferredIsDynamic
            : (hasPlanData ? builtForm.isDynamic : (typeof form.isDynamic === 'boolean' ? form.isDynamic : builtForm.isDynamic));
        planForms.value[metricId] = {
            ...builtForm,
            restaurantId: Number(targetRestaurantId),
            planMode: form.planMode || 'shared',
            isDynamic: resolvedIsDynamic,
            selectedMonth: normalizeMonth(form.selectedMonth ?? preferredSelectedMonth),
        };
    } catch (error) {
        toast.error('Не удалось загрузить плановые значения');
        console.error(error);
    }
}

async function loadMetricGroupPlanFacts(groupId) {
    const form = metricGroupPlanForms.value?.[groupId];
    if (!form) {
        return;
    }
    const sourceGroup = activeMetricGroup.value || metricGroups.value.find((group) => Number(group.id) === Number(groupId));
    const options = metricGroupRestaurantOptions(sourceGroup);
    const targetRestaurantId =
        form.planMode === 'per_restaurant' ? form.restaurantId : form.restaurantId || options[0]?.value || null;
    if (!targetRestaurantId) {
        return;
    }

    try {
        const yearValue = Number(planYear.value);
        const data = await fetchKpiMetricGroupPlanFacts({
            group_id: groupId,
            restaurant_id: Number(targetRestaurantId),
            year: yearValue,
        });
        const items = Array.isArray(data?.items) ? data.items : data || [];
        const monthMap = {};
        items.forEach((item) => {
            monthMap[Number(item.month)] = {
                plan_value: item.plan_value ?? null,
                fact_value: item.fact_value ?? null,
            };
        });
        metricGroupPlanFactsByGroup.value = {
            ...metricGroupPlanFactsByGroup.value,
            [groupId]: {
                restaurantId: Number(targetRestaurantId),
                months: monthMap,
            },
        };
        const pref = metricGroupPlanPrefsByGroup.value?.[String(groupId)] || null;
        const preferredIsDynamic = typeof pref?.isDynamic === 'boolean' ? pref.isDynamic : null;
        const preferredSelectedMonth = normalizeMonth(pref?.selectedMonth);
        const builtForm = buildPlanForm(
            groupId,
            monthMap,
            Number(targetRestaurantId),
            form.planMode || 'shared',
            { selectedMonth: form.selectedMonth ?? preferredSelectedMonth },
        );
        const hasPlanData = Object.values(builtForm.months).some((value) => value !== '');
        const resolvedIsDynamic = preferredIsDynamic !== null
            ? preferredIsDynamic
            : (hasPlanData
                ? builtForm.isDynamic
                : (typeof form.isDynamic === 'boolean' ? form.isDynamic : builtForm.isDynamic));
        metricGroupPlanForms.value[groupId] = {
            ...builtForm,
            restaurantId: Number(targetRestaurantId),
            planMode: form.planMode || 'shared',
            isDynamic: resolvedIsDynamic,
            selectedMonth: normalizeMonth(form.selectedMonth ?? preferredSelectedMonth),
        };
    } catch (error) {
        toast.error('Не удалось загрузить плановые значения группы');
        console.error(error);
    }
}

async function persistMetricGroupPlanSettings(groupId) {
    if (!groupId) return;
    const targetPercent =
        metricGroupForm.value.planTargetPercent === ''
            ? 100
            : Number(String(metricGroupForm.value.planTargetPercent).replace(',', '.'));
    if (!Number.isFinite(targetPercent) || targetPercent < 0 || targetPercent > 100) {
        toast.error('Цель группы должна быть в диапазоне от 0 до 100%');
        return false;
    }
    const parsedMaxScaleValue = parseNumber(metricGroupForm.value.maxScaleValue);
    if (metricGroupForm.value.useMaxScale && (parsedMaxScaleValue === null || parsedMaxScaleValue <= 0)) {
        toast.error('Укажите корректное максимальное значение шкалы группы');
        return false;
    }
    await updateKpiMetricGroup(groupId, {
        use_max_scale: Boolean(metricGroupForm.value.useMaxScale),
        max_scale_value: metricGroupForm.value.useMaxScale ? parsedMaxScaleValue : null,
        plan_direction: metricGroupForm.value.planDirection || 'higher_better',
        plan_target_percent: targetPercent,
    });
    return true;
}

async function persistMetricPlanSettings(metricId) {
    if (!metricId) return false;
    const parsedMaxScaleValue = parseNumber(metricForm.value.maxScaleValue);
    if (metricForm.value.useMaxScale && (parsedMaxScaleValue === null || parsedMaxScaleValue <= 0)) {
        toast.error('Укажите корректное максимальное значение шкалы');
        return false;
    }
    const updatedMetric = await updateKpiMetric(metricId, {
        use_max_scale: Boolean(metricForm.value.useMaxScale),
        max_scale_value: metricForm.value.useMaxScale ? parsedMaxScaleValue : null,
        plan_direction: metricForm.value.planDirection || 'higher_better',
    });
    if (updatedMetric && Number(updatedMetric.id) === Number(metricId)) {
        metrics.value = metrics.value.map((metric) => (
            Number(metric.id) === Number(metricId)
                ? { ...metric, ...updatedMetric }
                : metric
        ));
        metricsCatalog.value = metricsCatalog.value.map((metric) => (
            Number(metric.id) === Number(metricId)
                ? { ...metric, ...updatedMetric }
                : metric
        ));
    }
    return true;
}

async function savePlan(metricId) {
    const form = planForms.value?.[metricId];
    if (!form) return;
    const targetRestaurants =
        form.planMode === 'per_restaurant'
            ? (form.restaurantId ? [Number(form.restaurantId)] : [])
            : planRestaurantOptions.value.map((opt) => Number(opt.value));
    if (!targetRestaurants.length) {
        toast.error('Выберите ресторан');
        return;
    }

    planSaving.value[metricId] = true;
    try {
        const settingsSaved = await persistMetricPlanSettings(metricId);
        if (!settingsSaved) {
            return;
        }

        const yearValue = Number(planYear.value);
        if (!form.isDynamic) {
            months.forEach(({ month }) => {
                form.months[month] = form.constantValue;
            });
        }

        const updates = [];
        const storedFacts = planFactsByMetric.value?.[metricId];

        let existingKeys = null;
        if (form.planMode !== 'per_restaurant') {
            const bulk = await fetchKpiPlanFactsBulk({ year: yearValue, metric_id: metricId });
            const items = Array.isArray(bulk?.items) ? bulk.items : bulk || [];
            existingKeys = new Set(
                items.map((item) => `${Number(item.restaurant_id)}-${Number(item.month)}`),
            );
        }

        const storedRestaurantId =
            storedFacts?.restaurantId !== null && storedFacts?.restaurantId !== undefined
                ? Number(storedFacts.restaurantId)
                : null;
        const monthsForSave = months;
        targetRestaurants.forEach((restaurantId) => {
            monthsForSave.forEach(({ month }) => {
                const rawValue = form.isDynamic ? form.months[month] : form.constantValue;
                const planValue = parseNumber(rawValue);
                const hasExisting = existingKeys
                    ? existingKeys.has(`${Number(restaurantId)}-${Number(month)}`)
                    : (storedRestaurantId !== null &&
                          Number(storedRestaurantId) === Number(restaurantId) &&
                          Boolean(storedFacts?.months?.[month]));
                if (planValue === null && !hasExisting) {
                    return;
                }
                updates.push({
                    metric_id: metricId,
                    restaurant_id: Number(restaurantId),
                    year: yearValue,
                    month,
                    plan_value: planValue,
                });
            });
        });

        if (!updates.length) {
            await persistPlanPreference(metricId);
            toast.success('Настройки плана сохранены');
            return;
        }

        await upsertPlanFactsInBatches(updates, 20);
        await loadPlanFactsForMetric(metricId);
        await persistPlanPreference(metricId);
        toast.success('План сохранен');
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось сохранить план');
        console.error(error);
    } finally {
        planSaving.value[metricId] = false;
    }
}

async function saveMetricGroupPlan(groupId) {
    const form = metricGroupPlanForms.value?.[groupId];
    if (!form) return;
    const targetRestaurants =
        form.planMode === 'per_restaurant'
            ? (form.restaurantId ? [Number(form.restaurantId)] : [])
            : metricGroupPlanRestaurantOptions.value.map((opt) => Number(opt.value));
    if (!targetRestaurants.length) {
        toast.error('Выберите ресторан');
        return;
    }

    metricGroupPlanSaving.value[groupId] = true;
    try {
        const settingsSaved = await persistMetricGroupPlanSettings(groupId);
        if (!settingsSaved) {
            return;
        }

        const yearValue = Number(planYear.value);
        if (!form.isDynamic) {
            months.forEach(({ month }) => {
                form.months[month] = form.constantValue;
            });
        }

        const updates = [];
        const storedFacts = metricGroupPlanFactsByGroup.value?.[groupId];

        let existingKeys = null;
        if (form.planMode !== 'per_restaurant') {
            const bulk = await fetchKpiMetricGroupPlanFactsBulk({ year: yearValue, group_id: groupId });
            const items = Array.isArray(bulk?.items) ? bulk.items : bulk || [];
            existingKeys = new Set(
                items.map((item) => `${Number(item.restaurant_id)}-${Number(item.month)}`),
            );
        }

        const storedRestaurantId =
            storedFacts?.restaurantId !== null && storedFacts?.restaurantId !== undefined
                ? Number(storedFacts.restaurantId)
                : null;
        const monthsForSave = months;
        targetRestaurants.forEach((restaurantId) => {
            monthsForSave.forEach(({ month }) => {
                const rawValue = form.isDynamic ? form.months[month] : form.constantValue;
                const planValue = parseNumber(rawValue);
                const hasExisting = existingKeys
                    ? existingKeys.has(`${Number(restaurantId)}-${Number(month)}`)
                    : (storedRestaurantId !== null &&
                          Number(storedRestaurantId) === Number(restaurantId) &&
                          Boolean(storedFacts?.months?.[month]));
                if (planValue === null && !hasExisting) {
                    return;
                }
                updates.push({
                    group_id: groupId,
                    restaurant_id: Number(restaurantId),
                    year: yearValue,
                    month,
                    plan_value: planValue,
                });
            });
        });

        if (!updates.length) {
            await Promise.all([
                persistMetricGroupPlanPreference(groupId),
                loadMetricGroups(),
                loadMetricsCatalog(),
            ]);
            toast.success('Настройки плана группы сохранены');
            return;
        }

        for (let index = 0; index < updates.length; index += 20) {
            const chunk = updates.slice(index, index + 20);
            await upsertKpiMetricGroupPlanFactsBulk(chunk);
        }
        await Promise.all([
            loadMetricGroupPlanFacts(groupId),
            persistMetricGroupPlanPreference(groupId),
            loadMetricGroups(),
            loadMetricsCatalog(),
        ]);
        toast.success('План группы сохранен');
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось сохранить план группы');
        console.error(error);
    } finally {
        metricGroupPlanSaving.value[groupId] = false;
    }
}

async function loadRestaurants() {
    try {
        const data = await fetchRestaurants();
        restaurants.value = Array.isArray(data?.items) ? data.items : data || [];
    } catch (error) {
        toast.error('Не удалось загрузить рестораны');
        console.error(error);
    }
}

async function loadAdjustmentTypes() {
    try {
        const data = await fetchPayrollAdjustmentTypes();
        adjustmentTypes.value = Array.isArray(data?.items) ? data.items : data || [];
    } catch (error) {
        toast.error('Не удалось загрузить виды выплат');
        console.error(error);
    }
}

async function loadRuleOptions() {
    if (ruleOptionsLoaded.value) return;
    try {
        const [positionsData, subdivisionsData, employeesData] = await Promise.all([
            fetchAccessPositions(),
            fetchRestaurantSubdivisions(),
            fetchAllEmployees({ include_fired: true, limit: 250 }),
        ]);
        positions.value = Array.isArray(positionsData) ? positionsData : positionsData?.items || [];
        subdivisions.value = Array.isArray(subdivisionsData) ? subdivisionsData : [];
        employeeDirectory.value = Array.isArray(employeesData?.items) ? employeesData.items : employeesData || [];
        ruleOptionsLoaded.value = true;
    } catch (error) {
        toast.error('Не удалось загрузить справочники для правил');
        console.error(error);
    }
}

async function loadMetricRules() {
    if (!metricEditingId.value) return;
    rulesLoading.value = true;
    try {
        const data = await fetchKpiRules({ metric_id: metricEditingId.value });
        metricRules.value = Array.isArray(data?.items) ? data.items : data || [];
    } catch (error) {
        toast.error('Не удалось загрузить правила KPI');
        console.error(error);
    } finally {
        rulesLoading.value = false;
    }
}

async function loadMetricGroupRules(groupId = metricGroupEditingId.value) {
    if (!groupId) return;
    metricGroupRulesLoading.value = true;
    try {
        const data = await fetchKpiMetricGroupRules({ group_id: groupId });
        metricGroupRules.value = Array.isArray(data?.items) ? data.items : data || [];
    } catch (error) {
        toast.error('Не удалось загрузить правила группы KPI');
        console.error(error);
    } finally {
        metricGroupRulesLoading.value = false;
    }
}

function resetRuleForm() {
    ruleEditingId.value = null;
    ruleMode.value = 'metric';
    ruleForm.value = defaultRuleForm();
    ruleActionRows.value = [
        createRuleActionRow('bonus', { planSource: rulePlanReferenceValue.value === null ? 'custom' : 'plan' }),
    ];
    employeeSearch.value = '';
    employeeSearchResults.value = [];
}

function openCreateRuleModal() {
    if (!metricEditingId.value) return;
    resetRuleForm();
    ruleMode.value = 'metric';
    ruleForm.value.metricId = metricEditingId.value;
    ruleForm.value.comparisonBasis = 'absolute';
    loadRuleOptions();
    isRuleModalOpen.value = true;
}

async function openEditRuleModal(rule) {
    if (!rule) return;
    await loadRuleOptions();
    ruleMode.value = 'metric';
    startEditRule(rule);
    isRuleModalOpen.value = true;
}

function openCreateGroupRuleModal() {
    if (!metricGroupEditingId.value) return;
    resetRuleForm();
    ruleMode.value = 'group';
    ruleForm.value.groupId = metricGroupEditingId.value;
    ruleForm.value.comparisonBasis = 'absolute';
    loadRuleOptions();
    isRuleModalOpen.value = true;
}

async function openEditGroupRuleModal(rule) {
    if (!rule) return;
    await loadRuleOptions();
    ruleMode.value = 'group';
    startEditGroupRule(rule);
    isRuleModalOpen.value = true;
}

function closeRuleModal() {
    isRuleModalOpen.value = false;
    ruleSaving.value = false;
    closeRuleSubdivisionSelect();
    closeRulePositionSelect();
    resetRuleForm();
}

function startEditRule(rule) {
    ruleEditingId.value = rule.id;
    const position = positions.value.find((item) => Number(item.id) === Number(rule.position_id));
    const selectedPositionId =
        rule.position_id !== null && rule.position_id !== undefined ? Number(rule.position_id) : null;
    ruleForm.value = {
        metricId: rule.metric_id || metricEditingId.value,
        comparisonBasis: rule.comparison_basis || 'absolute',
        subdivisionId: position?.restaurant_subdivision_id ?? null,
        allPositions: selectedPositionId === null,
        positionIds: selectedPositionId !== null ? [selectedPositionId] : [],
        isIndividual: Boolean(rule.employee_id),
        employeeId: rule.employee_id ?? null,
        targetValue: rule.target_value ?? '',
        warningValue: rule.warning_value ?? '',
        bonusCondition: rule.bonus_condition || 'gte',
        bonusType: rule.bonus_type || 'none',
        bonusValue: rule.bonus_value ?? '',
        penaltyCondition: rule.penalty_condition || 'lte',
        penaltyType: rule.penalty_type || 'none',
        penaltyValue: rule.penalty_value ?? '',
        isActive: Boolean(rule.is_active),
    };
    employeeSearch.value = '';
    employeeSearchResults.value = [];
    syncRuleActionRowsFromRuleForm();
}

function startEditGroupRule(rule) {
    ruleEditingId.value = rule.id;
    const position = positions.value.find((item) => Number(item.id) === Number(rule.position_id));
    const selectedPositionId =
        rule.position_id !== null && rule.position_id !== undefined ? Number(rule.position_id) : null;
    ruleForm.value = {
        metricId: null,
        groupId: rule.group_id || metricGroupEditingId.value,
        comparisonBasis: rule.comparison_basis || 'absolute',
        subdivisionId: position?.restaurant_subdivision_id ?? null,
        allPositions: selectedPositionId === null,
        positionIds: selectedPositionId !== null ? [selectedPositionId] : [],
        isIndividual: Boolean(rule.employee_id),
        employeeId: rule.employee_id ?? null,
        targetValue: rule.target_value ?? '',
        warningValue: rule.warning_value ?? '',
        bonusCondition: rule.bonus_condition || 'gte',
        bonusType: rule.bonus_type || 'none',
        bonusValue: rule.bonus_value ?? '',
        penaltyCondition: rule.penalty_condition || 'lte',
        penaltyType: rule.penalty_type || 'none',
        penaltyValue: rule.penalty_value ?? '',
        isActive: Boolean(rule.is_active),
    };
    employeeSearch.value = '';
    employeeSearchResults.value = [];
    syncRuleActionRowsFromRuleForm();
}

function handleAllPositionsToggle(checked) {
    ruleForm.value.allPositions = Boolean(checked);
    if (checked) {
        ruleForm.value.positionIds = [];
    }
}

function toggleRulePosition(positionId, checked) {
    const id = Number(positionId);
    const next = new Set((ruleForm.value.positionIds || []).map((item) => Number(item)));
    if (checked) {
        next.add(id);
    } else {
        next.delete(id);
    }
    ruleForm.value.positionIds = Array.from(next);
    if (checked) {
        ruleForm.value.allPositions = false;
    } else if (!ruleForm.value.positionIds.length) {
        ruleForm.value.allPositions = true;
    }
}

async function handleSaveRule() {
    if (ruleMode.value === 'metric' && !ruleForm.value.metricId) {
        toast.error('Выберите показатель KPI');
        return;
    }
    if (ruleMode.value === 'group' && !ruleForm.value.groupId) {
        toast.error('Выберите группу KPI');
        return;
    }
    if (ruleForm.value.isIndividual && !ruleForm.value.employeeId) {
        toast.error('Выберите сотрудника для индивидуального KPI');
        return;
    }

    const rows = (ruleActionRows.value || []).filter((row) => row?.type);
    if (!rows.length) {
        toast.error('Добавьте хотя бы одно условие премии или удержания');
        return;
    }

    const typeSet = new Set(rows.map((row) => row.type));
    if (typeSet.size !== rows.length) {
        toast.error('Каждый тип условия можно добавить только один раз');
        return;
    }

    const bonusRow = rows.find((row) => row.type === 'bonus') || null;
    const penaltyRow = rows.find((row) => row.type === 'penalty') || null;

    const resolveThresholdValue = (row, label) => {
        if (!row) return null;
        if (row.planSource === 'plan') {
            const planValue = rulePlanReferenceValue.value;
            if (planValue === null) {
                toast.error(`Для ${label} не задан плановый показатель в настройках KPI`);
                return undefined;
            }
            return planValue;
        }
        const customValue = parseNumber(row.planValue);
        if (customValue === null) {
            toast.error(`Укажите свое значение планового показателя для ${label}`);
            return undefined;
        }
        return customValue;
    };

    const bonusThreshold = resolveThresholdValue(bonusRow, 'премии');
    const penaltyThreshold = resolveThresholdValue(penaltyRow, 'удержания');
    if ((bonusRow && bonusThreshold === undefined) || (penaltyRow && penaltyThreshold === undefined)) {
        return;
    }

    const targetValue = bonusThreshold ?? penaltyThreshold;
    if (targetValue === null) {
        toast.error('Добавьте плановый показатель для условия');
        return;
    }
    const normalizedWarning = penaltyThreshold ?? targetValue;

    const bonusType = bonusRow?.effectType || 'none';
    const bonusValueParsed = parseNumber(bonusRow?.effectValue);
    if (bonusRow && bonusType !== 'none' && bonusValueParsed === null) {
        toast.error('Укажите значение премии');
        return;
    }
    const bonusValue = bonusType === 'none' ? 0 : bonusValueParsed ?? 0;

    const penaltyType = penaltyRow?.effectType || 'none';
    const penaltyValueParsed = parseNumber(penaltyRow?.effectValue);
    if (penaltyRow && penaltyType !== 'none' && penaltyValueParsed === null) {
        toast.error('Укажите значение удержания');
        return;
    }
    const penaltyValue = penaltyType === 'none' ? 0 : penaltyValueParsed ?? 0;

    const selectedPositionIds = ruleForm.value.allPositions
        ? [null]
        : Array.from(
            new Set((ruleForm.value.positionIds || []).map((id) => Number(id)).filter((id) => Number.isFinite(id))),
        );
    if (!ruleForm.value.allPositions && !selectedPositionIds.length) {
        toast.error('Выберите хотя бы одну должность или включите "Все должности"');
        return;
    }

    const basePayload = {
        restaurant_id: null,
        department_code: null,
        employee_id: ruleForm.value.isIndividual ? Number(ruleForm.value.employeeId) : null,
        comparison_basis: 'absolute',
        threshold_type: 'dual',
        target_value: targetValue,
        warning_value: normalizedWarning,
        bonus_condition: ruleMode.value === 'group'
            ? ((metricGroupForm.value.planDirection || activeMetricGroup.value?.plan_direction || 'higher_better') === 'lower_better'
                ? 'lte'
                : 'gte')
            : (metricForm.value.planDirection === 'lower_better' ? 'lte' : 'gte'),
        bonus_type: bonusType,
        bonus_value: bonusValue,
        penalty_condition: ruleMode.value === 'group'
            ? ((metricGroupForm.value.planDirection || activeMetricGroup.value?.plan_direction || 'higher_better') === 'lower_better'
                ? 'gte'
                : 'lte')
            : (metricForm.value.planDirection === 'lower_better' ? 'gte' : 'lte'),
        penalty_type: penaltyType,
        penalty_value: penaltyValue,
        is_active: Boolean(ruleForm.value.isActive),
        comment: null,
    };

    ruleSaving.value = true;
    try {
        const payloads = selectedPositionIds.map((positionId) => ({
            ...basePayload,
            metric_id: ruleMode.value === 'metric' ? Number(ruleForm.value.metricId) : undefined,
            group_id: ruleMode.value === 'group' ? Number(ruleForm.value.groupId) : undefined,
            position_id: positionId !== null ? Number(positionId) : null,
        }));
        if (ruleEditingId.value) {
            const [firstPayload, ...restPayloads] = payloads;
            if (ruleMode.value === 'group') {
                await updateKpiMetricGroupRule(ruleEditingId.value, firstPayload);
            } else {
                await updateKpiRule(ruleEditingId.value, firstPayload);
            }
            if (restPayloads.length) {
                await Promise.all(restPayloads.map((payload) => (
                    ruleMode.value === 'group'
                        ? createKpiMetricGroupRule(payload)
                        : createKpiRule(payload)
                )));
            }
            toast.success(restPayloads.length ? 'Правило обновлено и расширено по должностям' : 'Правило обновлено');
        } else {
            await Promise.all(payloads.map((payload) => (
                ruleMode.value === 'group'
                    ? createKpiMetricGroupRule(payload)
                    : createKpiRule(payload)
            )));
            toast.success(payloads.length > 1 ? 'Создано несколько правил для выбранных должностей' : 'Правило создано');
        }
        if (ruleMode.value === 'group') {
            await loadMetricGroupRules();
        } else {
            await loadMetricRules();
        }
        closeRuleModal();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось сохранить правило');
        console.error(error);
    } finally {
        ruleSaving.value = false;
    }
}

async function handleDeleteRule(rule) {
    const ruleId = rule?.id || null;
    if (!ruleId) return;
    if (!window.confirm('Удалить правило?')) return;
    ruleDeletingId.value = ruleId;
    try {
        if (ruleMode.value === 'group' || rule?.group_id) {
            await deleteKpiMetricGroupRule(ruleId);
            await loadMetricGroupRules();
        } else {
            await deleteKpiRule(ruleId);
            await loadMetricRules();
        }
        toast.success('Правило удалено');
        if (ruleEditingId.value === ruleId) {
            closeRuleModal();
        }
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось удалить правило');
        console.error(error);
    } finally {
        ruleDeletingId.value = null;
    }
}

const searchEmployees = useDebounce(async (query) => {
    if (!ruleForm.value.isIndividual || !query || query.trim().length < 2) {
        employeeSearchResults.value = [];
        return;
    }
    employeeSearchLoading.value = true;
    try {
        const data = await fetchEmployees({ q: query.trim(), include_fired: true, limit: 50 });
        employeeSearchResults.value = Array.isArray(data?.items) ? data.items : data || [];
    } catch (error) {
        console.error(error);
        employeeSearchResults.value = [];
    } finally {
        employeeSearchLoading.value = false;
    }
}, 350);

function handleEmployeeSearch(query) {
    employeeSearch.value = query;
    searchEmployees(query);
}

function toggleMetricRestaurantSelect() {
    if (metricForm.value.allRestaurants) {
        return;
    }
    const next = !isMetricRestaurantSelectOpen.value;
    isMetricRestaurantSelectOpen.value = next;
    if (next) {
        closeMetricGroupMembersSelect();
        closeRuleSubdivisionSelect();
        closeRulePositionSelect();
    }
}

function closeMetricRestaurantSelect() {
    isMetricRestaurantSelectOpen.value = false;
}

function handleMetricRestaurantSelectKeydown(event) {
    if (event.key === 'Escape') {
        closeMetricRestaurantSelect();
        return;
    }
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleMetricRestaurantSelect();
    }
}

function toggleMetricGroupMembersSelect() {
    const next = !isMetricGroupMembersSelectOpen.value;
    isMetricGroupMembersSelectOpen.value = next;
    if (next) {
        closeMetricRestaurantSelect();
        closeRuleSubdivisionSelect();
        closeRulePositionSelect();
    }
}

function closeMetricGroupMembersSelect() {
    isMetricGroupMembersSelectOpen.value = false;
}

function handleMetricGroupMembersSelectKeydown(event) {
    if (event.key === 'Escape') {
        closeMetricGroupMembersSelect();
        return;
    }
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleMetricGroupMembersSelect();
    }
}

function toggleMetricGroupMember(metricId, checked) {
    const id = Number(metricId);
    const next = new Set((metricGroupForm.value.memberIds || []).map((item) => Number(item)));
    if (checked) {
        next.add(id);
    } else {
        next.delete(id);
    }
    metricGroupForm.value.memberIds = Array.from(next);
}

function toggleRuleSubdivisionSelect() {
    const next = !isRuleSubdivisionSelectOpen.value;
    isRuleSubdivisionSelectOpen.value = next;
    if (next) {
        closeMetricRestaurantSelect();
        closeMetricGroupMembersSelect();
        closeRulePositionSelect();
    }
}

function closeRuleSubdivisionSelect() {
    isRuleSubdivisionSelectOpen.value = false;
}

function handleRuleSubdivisionSelectKeydown(event) {
    if (event.key === 'Escape') {
        closeRuleSubdivisionSelect();
        return;
    }
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleRuleSubdivisionSelect();
    }
}

function toggleRuleSubdivision(subdivisionId, checked) {
    if (!checked) {
        if (subdivisionId === null) {
            return;
        }
        if (Number(ruleForm.value.subdivisionId) === Number(subdivisionId)) {
            ruleForm.value.subdivisionId = null;
        }
        return;
    }
    ruleForm.value.subdivisionId =
        subdivisionId === null || subdivisionId === undefined ? null : Number(subdivisionId);
    closeRuleSubdivisionSelect();
}

function toggleRulePositionSelect() {
    const next = !isRulePositionSelectOpen.value;
    isRulePositionSelectOpen.value = next;
    if (next) {
        closeMetricRestaurantSelect();
        closeMetricGroupMembersSelect();
        closeRuleSubdivisionSelect();
    }
}

function closeRulePositionSelect() {
    isRulePositionSelectOpen.value = false;
}

function handleRulePositionSelectKeydown(event) {
    if (event.key === 'Escape') {
        closeRulePositionSelect();
        return;
    }
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleRulePositionSelect();
    }
}

function handleOutsideMultiselectClick(event) {
    if (isMetricRestaurantSelectOpen.value) {
        const root = metricRestaurantSelectRef.value;
        if (root && !root.contains(event.target)) {
            closeMetricRestaurantSelect();
        }
    }
    if (isMetricGroupMembersSelectOpen.value) {
        const root = metricGroupMembersSelectRef.value;
        if (root && !root.contains(event.target)) {
            closeMetricGroupMembersSelect();
        }
    }
    if (isRuleSubdivisionSelectOpen.value) {
        const root = ruleSubdivisionSelectRef.value;
        if (root && !root.contains(event.target)) {
            closeRuleSubdivisionSelect();
        }
    }
    if (isRulePositionSelectOpen.value) {
        const root = rulePositionSelectRef.value;
        if (root && !root.contains(event.target)) {
            closeRulePositionSelect();
        }
    }
}

function handleAllRestaurantsToggle(checked) {
    metricForm.value.allRestaurants = Boolean(checked);
    if (checked) {
        metricForm.value.restaurantIds = [];
        closeMetricRestaurantSelect();
    }
}

function toggleMetricRestaurant(restaurantId, checked) {
    const id = Number(restaurantId);
    const next = new Set(metricForm.value.restaurantIds.map((item) => Number(item)));
    if (checked) {
        next.add(id);
    } else {
        next.delete(id);
    }
    metricForm.value.restaurantIds = Array.from(next);
}

function startEditMetric(metric) {
    metricEditingId.value = metric.id;
    metricForm.value = {
        code: metric.code || '',
        name: metric.name || '',
        description: metric.description || '',
        unit: metric.unit ?? null,
        groupId:
            metric.group_id !== null && metric.group_id !== undefined
                ? Number(metric.group_id)
                : null,
        useMaxScale: Boolean(metric.use_max_scale),
        maxScaleValue:
            metric.max_scale_value !== null && metric.max_scale_value !== undefined
                ? formatNumberInput(metric.max_scale_value)
                : '',
        planDirection: metric.plan_direction || 'higher_better',
        isActive: Boolean(metric.is_active),
        allRestaurants: metric.all_restaurants !== false,
        restaurantIds: Array.isArray(metric.restaurant_ids)
            ? metric.restaurant_ids.map((id) => Number(id))
            : [],
        bonusAdjustmentTypeId:
            metric.bonus_adjustment_type_id !== null && metric.bonus_adjustment_type_id !== undefined
                ? Number(metric.bonus_adjustment_type_id)
                : null,
        penaltyAdjustmentTypeId:
            metric.penalty_adjustment_type_id !== null && metric.penalty_adjustment_type_id !== undefined
                ? Number(metric.penalty_adjustment_type_id)
                : null,
    };
}

function resetMetricForm() {
    metricEditingId.value = null;
    metricForm.value = defaultMetricForm();
}

function openCreateModal() {
    resetMetricForm();
    activeTab.value = 'info';
    isModalOpen.value = true;
}

async function openEditModal(metric) {
    if (!metric) return;
    startEditMetric(metric);
    await loadPlanPreferences(metric.id);
    ensurePlanForm(metric);
    activeTab.value = 'info';
    isModalOpen.value = true;
    await loadPlanFactsForMetric(metric.id);
}

function closeModal() {
    isModalOpen.value = false;
    metricSaving.value = false;
    activeTab.value = 'info';
    isRuleModalOpen.value = false;
    closeMetricRestaurantSelect();
    closeRuleSubdivisionSelect();
    closeRulePositionSelect();
    resetMetricForm();
}

async function handleSaveMetric() {
    const trimmedName = metricForm.value.name.trim();
    if (!trimmedName) {
        toast.error('Укажите название показателя');
        return;
    }

    const parsedMaxScaleValue = parseNumber(metricForm.value.maxScaleValue);
    if (metricForm.value.useMaxScale && (parsedMaxScaleValue === null || parsedMaxScaleValue <= 0)) {
        toast.error('Укажите корректное максимальное значение шкалы');
        return;
    }

    const existingCode = String(metricForm.value.code || '').trim();
    const code = metricEditingId.value ? existingCode || generateMetricCode(trimmedName) : generateMetricCode(trimmedName);

    const payload = {
        code,
        name: trimmedName,
        description: metricForm.value.description?.trim() || null,
        unit: metricForm.value.unit || null,
        group_id:
            metricForm.value.groupId !== null && metricForm.value.groupId !== undefined
                ? Number(metricForm.value.groupId)
                : null,
        calculation_base: 'none',
        use_max_scale: Boolean(metricForm.value.useMaxScale),
        max_scale_value: metricForm.value.useMaxScale ? parsedMaxScaleValue : null,
        plan_direction: metricForm.value.planDirection || 'higher_better',
        is_active: Boolean(metricForm.value.isActive),
        all_restaurants: Boolean(metricForm.value.allRestaurants),
        restaurant_ids: metricForm.value.allRestaurants
            ? null
            : metricForm.value.restaurantIds.map((id) => Number(id)),
        bonus_adjustment_type_id:
            metricForm.value.bonusAdjustmentTypeId !== null && metricForm.value.bonusAdjustmentTypeId !== undefined
                ? Number(metricForm.value.bonusAdjustmentTypeId)
                : null,
        penalty_adjustment_type_id:
            metricForm.value.penaltyAdjustmentTypeId !== null &&
            metricForm.value.penaltyAdjustmentTypeId !== undefined
                ? Number(metricForm.value.penaltyAdjustmentTypeId)
                : null,
    };

    if (!payload.code) {
        toast.error('Не удалось сформировать код показателя');
        return;
    }

    metricSaving.value = true;
    try {
        const isCreating = !metricEditingId.value;
        if (metricEditingId.value) {
            await updateKpiMetric(metricEditingId.value, payload);
            toast.success('Показатель обновлен');
        } else {
            await createKpiMetric(payload);
            toast.success('Показатель создан');
        }
        if (isCreating && metricStatusFilter.value === 'archived') {
            metricStatusFilter.value = 'active';
        }
        await loadMetrics();
        resetMetricForm();
        closeModal();
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось сохранить показатель');
        console.error(error);
    } finally {
        metricSaving.value = false;
    }
}

async function handleDeleteMetric(metric) {
    if (!metric?.id) return;
    if (!window.confirm('Удалить показатель?')) return;
    metricDeletingId.value = metric.id;
    try {
        await deleteKpiMetric(metric.id);
        toast.success('Показатель удален');
        await loadMetrics();
        if (metricEditingId.value === metric.id) {
            closeModal();
        }
    } catch (error) {
        const detail = error?.response?.data?.detail;
        toast.error(detail || 'Не удалось удалить показатель');
        console.error(error);
    } finally {
        metricDeletingId.value = null;
    }
}

watch(
    () => planYear.value,
    () => {
        if (metricEditingId.value) {
            loadPlanFactsForMetric(metricEditingId.value);
        }
        if (metricGroupEditingId.value && metricGroupActiveTab.value === 'plans') {
            loadMetricGroupPlanFacts(metricGroupEditingId.value);
        }
    },
);

watch(
    () => activePlanForm.value?.restaurantId,
    () => {
        if (metricEditingId.value) {
            schedulePlanPreferencePersist(metricEditingId.value);
            loadPlanFactsForMetric(metricEditingId.value);
        }
    },
);

watch(
    () => activePlanForm.value?.planMode,
    () => {
        if (metricEditingId.value) {
            schedulePlanPreferencePersist(metricEditingId.value);
            loadPlanFactsForMetric(metricEditingId.value);
        }
    },
);

watch(
    () => activePlanForm.value?.isDynamic,
    () => {
        if (metricEditingId.value) {
            schedulePlanPreferencePersist(metricEditingId.value);
        }
    },
);

watch(
    () => activePlanForm.value?.selectedMonth,
    () => {
        if (metricEditingId.value) {
            schedulePlanPreferencePersist(metricEditingId.value);
        }
    },
);

watch(
    () => restaurants.value,
    () => {
        if (activeMetric.value) {
            ensurePlanForm(activeMetric.value);
            if (activePlanForm.value?.restaurantId) {
                loadPlanFactsForMetric(activeMetric.value.id);
            }
        }
        if (activeMetricGroup.value) {
            ensureMetricGroupPlanForm(activeMetricGroup.value);
            if (activeMetricGroupPlanForm.value?.restaurantId && metricGroupActiveTab.value === 'plans') {
                loadMetricGroupPlanFacts(activeMetricGroup.value.id);
            }
        }
    },
);

watch(
    () => activeTab.value,
    (value) => {
        if (value === 'rules') {
            loadMetricRules();
            loadRuleOptions();
        }
    },
);

watch(
    () => metricGroupActiveTab.value,
    (value) => {
        if (value === 'rules') {
            loadMetricGroupRules();
            loadRuleOptions();
        }
        if (value === 'plans' && metricGroupEditingId.value) {
            ensureMetricGroupPlanForm(activeMetricGroup.value);
            loadMetricGroupPlanFacts(metricGroupEditingId.value);
        }
    },
);

watch(
    () => metricEditingId.value,
    (value) => {
        if (value && activeTab.value === 'rules') {
            loadMetricRules();
        }
    },
);

watch(
    () => metricGroupEditingId.value,
    (value) => {
        if (value && metricGroupActiveTab.value === 'rules') {
            loadMetricGroupRules(value);
        }
        if (value && metricGroupActiveTab.value === 'plans') {
            ensureMetricGroupPlanForm(activeMetricGroup.value);
            loadMetricGroupPlanFacts(value);
        }
    },
);

watch(
    () => metricForm.value.allRestaurants,
    (value) => {
        if (value) {
            closeMetricRestaurantSelect();
        }
    },
);

watch(
    () => metricForm.value.useMaxScale,
    (value) => {
        if (!value) {
            metricForm.value.maxScaleValue = '';
        }
    },
);

watch(
    () => metricGroupForm.value.useMaxScale,
    (value) => {
        if (!value) {
            metricGroupForm.value.maxScaleValue = '';
        }
    },
);

watch(
    () => metricGroupForm.value.memberIds,
    () => {
        if (activeMetricGroup.value) {
            ensureMetricGroupPlanForm(activeMetricGroup.value);
        }
    },
    { deep: true },
);

watch(
    () => activeMetricGroupPlanForm.value?.restaurantId,
    () => {
        if (metricGroupEditingId.value) {
            scheduleMetricGroupPlanPreferencePersist(metricGroupEditingId.value);
            loadMetricGroupPlanFacts(metricGroupEditingId.value);
        }
    },
);

watch(
    () => activeMetricGroupPlanForm.value?.planMode,
    () => {
        if (metricGroupEditingId.value) {
            scheduleMetricGroupPlanPreferencePersist(metricGroupEditingId.value);
            loadMetricGroupPlanFacts(metricGroupEditingId.value);
        }
    },
);

watch(
    () => activeMetricGroupPlanForm.value?.isDynamic,
    () => {
        if (metricGroupEditingId.value) {
            scheduleMetricGroupPlanPreferencePersist(metricGroupEditingId.value);
        }
    },
);

watch(
    () => activeMetricGroupPlanForm.value?.selectedMonth,
    () => {
        if (metricGroupEditingId.value) {
            scheduleMetricGroupPlanPreferencePersist(metricGroupEditingId.value);
        }
    },
);

watch(
    () => ruleForm.value.subdivisionId,
    () => {
        if (ruleForm.value.allPositions) return;
        if (!positionOptions.value.length) return;
        const allowedIds = new Set(positionOptions.value.map((item) => Number(item.value)));
        const filtered = (ruleForm.value.positionIds || [])
            .map((id) => Number(id))
            .filter((id) => allowedIds.has(id));
        ruleForm.value.positionIds = filtered;
        if (!filtered.length) {
            ruleForm.value.allPositions = true;
        }
    },
);

watch(
    () => ruleForm.value.isIndividual,
    (value) => {
        if (!value) {
            ruleForm.value.employeeId = null;
            employeeSearch.value = '';
            employeeSearchResults.value = [];
        }
    },
);

watch(
    () => ruleForm.value.allPositions,
    (value) => {
        if (value) {
            closeRulePositionSelect();
        }
    },
);

onMounted(async () => {
    document.addEventListener('mousedown', handleOutsideMultiselectClick);
    await Promise.all([
        loadMetrics(),
        loadMetricsCatalog(),
        loadMetricGroups(),
        loadRestaurants(),
        loadAdjustmentTypes(),
        loadPlanPreferences(),
    ]);
});

onBeforeUnmount(() => {
    document.removeEventListener('mousedown', handleOutsideMultiselectClick);
    Array.from(planPrefPersistTimers.values()).forEach((timer) => clearTimeout(timer));
    planPrefPersistTimers.clear();
    Array.from(metricGroupPlanPrefPersistTimers.values()).forEach((timer) => clearTimeout(timer));
    metricGroupPlanPrefPersistTimers.clear();
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/kpi-metrics' as *;
</style>
