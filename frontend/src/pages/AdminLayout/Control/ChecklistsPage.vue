<template>
    <div class="control-checklists">
        <header class="control-checklists__header">
            <div>
                <h1 class="control-checklists__title">Контроль</h1>
                <p class="control-checklists__subtitle">
                    Управление чек-листами и отчеты по прохождениям.
                </p>
            </div>
            <div class="control-checklists__header-actions">
                <Button color="ghost" size="sm" :loading="loading" @click="loadAll">
                    Обновить
                </Button>
            </div>
        </header>

        <div class="control-checklists__tabs">
            <button
                type="button"
                class="control-checklists__tab"
                :class="{ 'is-active': activeTab === 'manage' }"
                @click="activeTab = 'manage'"
            >
                Чек-листы
            </button>
            <button
                type="button"
                class="control-checklists__tab"
                :class="{ 'is-active': activeTab === 'reports' }"
                @click="activeTab = 'reports'"
            >
                Статистика и отчеты
            </button>
        </div>

        <section v-if="activeTab === 'manage'" class="control-checklists__panel">
            <div class="control-checklists__panel-header control-checklists__panel-header--stacked">
                <div class="control-checklists__panel-toolbar">
                    <Input
                        v-model="checklistSearch"
                        class="control-checklists__search"
                        label="Поиск"
                        placeholder="Поиск по названию или описанию чек-листа"
                    />
                    <div class="control-checklists__panel-actions">
                        <Button
                            color="ghost"
                            size="sm"
                            @click="openPortal"
                        >
                            Пройти чек-лист
                        </Button>
                        <Button color="primary" size="sm" @click="openChecklistModal()">
                            Создать чек-лист
                        </Button>
                    </div>
                </div>

                <div class="control-checklists__manage-filters-shell">
                    <button
                        type="button"
                        class="control-checklists__panel-toggle control-checklists__panel-toggle--compact"
                        @click="toggleManageFilters"
                    >
                        Фильтры
                        <span class="control-checklists__panel-toggle-meta">
                            {{ manageFilterSummaryLabel }}
                        </span>
                        <span
                            :class="[
                                'control-checklists__panel-toggle-icon',
                                { 'is-open': isManageFiltersOpen },
                            ]"
                        >
                            ▼
                        </span>
                    </button>

                    <div v-if="isManageFiltersOpen" class="control-checklists__manage-filters-body">
                        <div class="control-checklists__filters control-checklists__filters--manage">
                            <Select
                                v-model="manageFilters.restaurantId"
                                label="Ресторан"
                                :options="manageRestaurantFilterOptions"
                                placeholder="Все рестораны"
                                searchable
                            />
                            <Select
                                v-model="manageFilters.subdivisionId"
                                label="Подразделение"
                                :options="manageSubdivisionFilterOptions"
                                placeholder="Все подразделения"
                                searchable
                            />
                            <Select
                                v-model="manageFilters.positionId"
                                label="Должность"
                                :options="managePositionFilterOptions"
                                placeholder="Все должности"
                                searchable
                            />
                            <Select
                                v-model="manageFilters.scoring"
                                label="Оценивание"
                                :options="manageScoringFilterOptions"
                                placeholder="Все типы"
                            />
                            <div class="control-checklists__filters-actions">
                                <Button
                                    type="button"
                                    color="ghost"
                                    size="sm"
                                    :disabled="!hasManageFilters"
                                    @click="resetManageFilters"
                                >
                                    Сбросить фильтры
                                </Button>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="control-checklists__filters-summary">
                    {{ manageResultsLabel }}
                </div>
            </div>
            <div v-if="loading" class="control-checklists__loading">Загрузка чек-листов...</div>
            <div v-else>
                <Table v-if="filteredChecklists.length" class="control-checklists__table control-checklists__table--manage">
                    <thead>
                        <tr>
                            <th>Название</th>
                            <th>Для кого</th>
                            <th>Должности</th>
                            <th>Оценочный</th>
                            <th class="control-checklists__actions-column">Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr
                            v-for="item in filteredChecklists"
                            :key="item.id"
                            class="control-checklists__row"
                            :class="{ 'control-checklists__row--readonly': !canEditChecklist(item) }"
                            @click="handleChecklistRowClick(item)"
                        >
                            <td>
                                <div class="control-checklists__name">
                                    <span>{{ item.name }}</span>
                                    <button
                                        type="button"
                                        class="control-checklists__info-button"
                                        title="Описание чек-листа"
                                        @click.stop="toggleDescription(item.id)"
                                    >
                                        i
                                    </button>
                                </div>
                                <div
                                    v-if="openDescriptions.has(item.id)"
                                    class="control-checklists__description"
                                >
                                    {{ item.description || 'Описание не задано.' }}
                                </div>
                            </td>
                            <td>{{ formatScope(item) }}</td>
                            <td>
                                <span
                                    v-if="item.position_ids?.length"
                                    class="control-checklists__positions-preview"
                                    :title="formatPositions(item.position_ids)"
                                >
                                    {{ formatPositionsPreview(item.position_ids) }}
                                </span>
                                <span v-else class="control-checklists__muted">Не назначены</span>
                            </td>
                            <td>{{ item.is_scored ? 'Да' : 'Нет' }}</td>
                            <td class="control-checklists__actions-column">
                                <div class="control-checklists__actions">
                                    <button
                                        type="button"
                                        class="control-checklists__icon-button"
                                        title="Редактировать чек-лист"
                                        aria-label="Редактировать чек-лист"
                                        :disabled="!canEditChecklist(item)"
                                        @click.stop="goManage(item.id)"
                                    >
                                        <BaseIcon name="Settings" />
                                    </button>
                                    <button
                                        type="button"
                                        class="control-checklists__icon-button"
                                        title="Удалить"
                                        aria-label="Удалить"
                                        :disabled="saving || !canEditChecklist(item)"
                                        @click.stop="handleDeleteChecklist(item.id)"
                                    >
                                        <BaseIcon name="Trash" />
                                    </button>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </Table>
                <p v-else class="control-checklists__empty">{{ manageEmptyState }}</p>
            </div>
        </section>

        <Modal v-if="isChecklistModalOpen" class="control-checklists__modal" @close="closeChecklistModal">
            <template #header>
                {{ checklistForm.id ? 'Редактирование чек-листа' : 'Новый чек-лист' }}
            </template>
            <template #default>
                <form class="control-checklists__modal-form" @submit.prevent="handleSubmitChecklist">
                    <section class="control-checklists__setup-card">
                        <div class="control-checklists__setup-head">
                            <div>
                                <h3 class="control-checklists__setup-title">Основные параметры</h3>
                                <p class="control-checklists__setup-note">
                                    Сначала заполните базовую информацию о чек-листе, затем выберите
                                    ресторан, подразделение и должность.
                                </p>
                            </div>
                            <span
                                class="control-checklists__setup-badge"
                                :class="{ 'is-active': checklistForm.isScored }"
                            >
                                {{ checklistForm.isScored ? 'Оцениваемый' : 'Без оценки' }}
                            </span>
                        </div>

                        <div
                            v-if="checklistMeta.creatorName || checklistMeta.createdAt"
                            class="control-checklists__setup-meta"
                        >
                            <div class="control-checklists__setup-meta-item">
                                <span class="control-checklists__setup-meta-label">Автор</span>
                                <span class="control-checklists__setup-meta-value">
                                    {{ checklistMeta.creatorName || '—' }}
                                </span>
                            </div>
                            <div class="control-checklists__setup-meta-item">
                                <span class="control-checklists__setup-meta-label">Создан</span>
                                <span class="control-checklists__setup-meta-value">
                                    {{ formatDateTime(checklistMeta.createdAt) || '—' }}
                                </span>
                            </div>
                        </div>

                        <div class="control-checklists__setup-stack">
                            <Input
                                v-model="checklistForm.name"
                                label="Введите название чек-листа"
                                placeholder="Например, Открытие смены"
                            />

                            <div class="control-checklists__textarea">
                                <label class="input-label">Описание чек-листа</label>
                                <textarea
                                    v-model="checklistForm.description"
                                    class="input-field"
                                    rows="4"
                                    placeholder="Коротко опишите, для чего нужен этот чек-лист"
                                ></textarea>
                            </div>

                            <div class="control-checklists__score-card">
                                <div class="control-checklists__score-copy">
                                    <span class="control-checklists__score-eyebrow">Формат проверки</span>
                                    <h4 class="control-checklists__score-title">Оцениваемый чек-лист</h4>
                                    <p class="control-checklists__score-note">
                                        Включите переключатель, если нужно считать итоговый балл и
                                        показывать оценку в отчётах.
                                    </p>
                                </div>

                                <label
                                    class="control-checklists__score-toggle"
                                    :class="{ 'is-active': checklistForm.isScored }"
                                >
                                    <input
                                        v-model="checklistForm.isScored"
                                        class="control-checklists__score-toggle-input"
                                        type="checkbox"
                                    />
                                    <span class="control-checklists__score-toggle-track" aria-hidden="true">
                                        <span class="control-checklists__score-toggle-thumb"></span>
                                    </span>
                                    <span class="control-checklists__score-toggle-state">
                                        {{ checklistForm.isScored ? 'Да' : 'Нет' }}
                                    </span>
                                </label>
                            </div>
                        </div>
                    </section>

                    <div class="control-checklists__scope-head">
                        <div>
                            <h3 class="control-checklists__scope-title">
                                Выбор ресторана, подразделения и должности
                            </h3>
                            <p class="control-checklists__scope-note">
                                Идем по порядку: сначала ресторан, затем подразделение, затем должность.
                                Чек-лист будет доступен только сотрудникам, которые попадают во все
                                выбранные условия.
                            </p>
                        </div>
                        <div class="control-checklists__scope-summary">
                            <span class="control-checklists__scope-chip">
                                Рестораны: {{ restaurantSelectionLabel }}
                            </span>
                            <span class="control-checklists__scope-chip">
                                Подразделения: {{ subdivisionSelectionLabel }}
                            </span>
                            <span class="control-checklists__scope-chip">
                                Должности: {{ positionSelectionLabel }}
                            </span>
                        </div>
                    </div>

                    <div class="control-checklists__selection-block control-checklists__selection-block--hierarchy">
                        <section class="control-checklists__scope-card">
                            <div class="control-checklists__scope-card-header">
                                <div class="control-checklists__scope-step">
                                    <span class="control-checklists__scope-step-badge">1</span>
                                    <span>Ресторан</span>
                                </div>
                                <span class="control-checklists__positions-meta">
                                    {{ restaurantSelectionLabel }}
                                </span>
                            </div>
                            <h4 class="control-checklists__scope-card-title">Выберите ресторан</h4>
                            <p class="control-checklists__scope-card-note">
                                Чек-лист появится только внутри отмеченных ресторанов. Этот шаг обязателен.
                            </p>
                            <div class="control-checklists__scope-options">
                                <Checkbox
                                    :model-value="allRestaurantsSelected"
                                    label="Все доступные рестораны"
                                    @update:model-value="handleToggleAllRestaurants"
                                />
                                <Checkbox
                                    v-for="restaurant in availableRestaurants"
                                    :key="restaurant.id"
                                    :label="restaurant.name"
                                    :model-value="checklistForm.restaurantIds.includes(restaurant.id)"
                                    @update:model-value="(checked) => handleToggleRestaurant(restaurant.id, checked)"
                                />
                                <p v-if="!availableRestaurants.length" class="control-checklists__muted">
                                    Нет доступных ресторанов.
                                </p>
                            </div>
                        </section>

                        <section
                            class="control-checklists__scope-card"
                            :class="{ 'is-disabled': !selectedRestaurantIds.length }"
                        >
                            <div class="control-checklists__scope-card-header">
                                <div class="control-checklists__scope-step">
                                    <span class="control-checklists__scope-step-badge">2</span>
                                    <span>Подразделение</span>
                                </div>
                                <span class="control-checklists__positions-meta">
                                    {{ subdivisionSelectionLabel }}
                                </span>
                            </div>
                            <h4 class="control-checklists__scope-card-title">Выберите подразделение</h4>
                            <p class="control-checklists__scope-card-note">
                                Шаг необязательный. Если ничего не выбирать, чек-лист будет доступен всем
                                подразделениям выбранных ресторанов.
                            </p>
                            <div v-if="selectedRestaurantIds.length" class="control-checklists__scope-options">
                                <Checkbox
                                    :model-value="allSubdivisionsSelected"
                                    label="Все подразделения выбранных ресторанов"
                                    @update:model-value="handleToggleAllSubdivisions"
                                />
                                <Checkbox
                                    v-for="subdivision in filteredSubdivisions"
                                    :key="subdivision.id"
                                    :label="subdivision.name"
                                    :model-value="checklistForm.subdivisionIds.includes(subdivision.id)"
                                    @update:model-value="(checked) => handleToggleSubdivision(subdivision.id, checked)"
                                />
                                <p v-if="!filteredSubdivisions.length" class="control-checklists__muted">
                                    Для выбранных ресторанов пока нет доступных подразделений.
                                </p>
                            </div>
                            <p v-else class="control-checklists__scope-placeholder">
                                Сначала выберите хотя бы один ресторан.
                            </p>
                        </section>

                        <section
                            class="control-checklists__scope-card"
                            :class="{ 'is-disabled': !selectedRestaurantIds.length }"
                        >
                            <div class="control-checklists__scope-card-header">
                                <div class="control-checklists__scope-step">
                                    <span class="control-checklists__scope-step-badge">3</span>
                                    <span>Должность</span>
                                </div>
                                <span class="control-checklists__positions-meta">
                                    {{ positionSelectionLabel }}
                                </span>
                            </div>
                            <h4 class="control-checklists__scope-card-title">Выберите должность</h4>
                            <p class="control-checklists__scope-card-note">
                                Чек-лист увидят только сотрудники выбранных должностей внутри текущего
                                scope. Этот шаг обязателен.
                            </p>
                            <div v-if="selectedRestaurantIds.length" class="control-checklists__scope-options">
                                <Checkbox
                                    :model-value="allPositionsSelected"
                                    label="Все должности в текущем scope"
                                    @update:model-value="handleToggleAllPositions"
                                />
                                <Checkbox
                                    v-for="position in filteredPositions"
                                    :key="position.id"
                                    :label="formatPositionOption(position)"
                                    :model-value="checklistForm.positionIds.includes(position.id)"
                                    @update:model-value="(checked) => handleTogglePosition(position.id, checked)"
                                />
                                <p v-if="!filteredPositions.length" class="control-checklists__muted">
                                    Нет подходящих должностей. Уточните ресторан или подразделение.
                                </p>
                            </div>
                            <p v-else class="control-checklists__scope-placeholder">
                                Сначала выберите ресторан, затем при необходимости подразделение.
                            </p>
                        </section>
                    </div>

                </form>
            </template>
            <template #footer>
                <Button type="button" color="ghost" size="sm" :disabled="saving" @click="closeChecklistModal">
                    Отмена
                </Button>
                <Button type="button" color="primary" size="sm" :loading="saving" @click="handleSubmitChecklist">
                    {{ checklistForm.id ? 'Сохранить' : 'Создать' }}
                </Button>
            </template>
        </Modal>


        <section v-if="activeTab === 'reports'" class="control-checklists__panel">
            <div class="control-checklists__filters">
                <div
                    class="control-checklists__positions-panel control-checklists__positions-panel--filters control-checklists__positions-panel--floating"
                >
                    <div class="control-checklists__positions-header">
                        <label class="input-label">Чек-листы</label>
                        <span class="control-checklists__positions-meta">
                            {{ reportChecklistSelectionLabel }}
                        </span>
                    </div>
                    <button
                        type="button"
                        class="control-checklists__panel-toggle"
                        @click="toggleReportChecklistPanel"
                    >
                        Выбрать чек-листы
                        <span class="control-checklists__panel-toggle-meta">
                            {{ reportChecklistSelectionLabel }}
                        </span>
                        <span
                            :class="[
                                'control-checklists__panel-toggle-icon',
                                { 'is-open': isReportChecklistPanelOpen },
                            ]"
                        >
                            ▼
                        </span>
                    </button>
                    <div v-if="isReportChecklistPanelOpen" class="control-checklists__panel-body">
                        <div class="control-checklists__panel-options control-checklists__panel-options--scroll">
                            <Checkbox
                                :model-value="allReportChecklistsSelected"
                                label="Все чек-листы"
                                @update:model-value="handleToggleAllReportChecklists"
                            />
                            <Checkbox
                                v-for="item in reportChecklistOptions"
                                :key="item.value"
                                :label="item.label"
                                :model-value="reportFilters.checklistIds.includes(Number(item.value))"
                                @update:model-value="(checked) => handleToggleReportChecklist(item.value, checked)"
                            />
                            <p v-if="!reportChecklistOptions.length" class="control-checklists__muted">
                                Нет доступных чек-листов.
                            </p>
                        </div>
                    </div>
                </div>

                <div
                    class="control-checklists__positions-panel control-checklists__positions-panel--filters control-checklists__positions-panel--floating"
                >
                    <div class="control-checklists__positions-header">
                        <label class="input-label">Объекты</label>
                        <span class="control-checklists__positions-meta">
                            {{ reportObjectSelectionLabel }}
                        </span>
                    </div>
                    <button type="button" class="control-checklists__panel-toggle" @click="toggleReportObjectPanel">
                        Выбрать объекты
                        <span class="control-checklists__panel-toggle-meta">
                            {{ reportObjectSelectionLabel }}
                        </span>
                        <span
                            :class="['control-checklists__panel-toggle-icon', { 'is-open': isReportObjectPanelOpen }]"
                        >
                            ▼
                        </span>
                    </button>
                    <div v-if="isReportObjectPanelOpen" class="control-checklists__panel-body">
                        <div class="control-checklists__panel-options control-checklists__panel-options--scroll">
                            <Checkbox
                                :model-value="allReportObjectsSelected"
                                label="Все объекты"
                                @update:model-value="handleToggleAllReportObjects"
                            />
                            <Checkbox
                                v-for="item in reportObjectOptions"
                                :key="item.value"
                                :label="item.label"
                                :model-value="reportFilters.objectNames.includes(item.value)"
                                @update:model-value="(checked) => handleToggleReportObject(item.value, checked)"
                            />
                            <p v-if="!reportObjectOptions.length" class="control-checklists__muted">
                                Нет объектов с отчетами.
                            </p>
                        </div>
                    </div>
                </div>
                <DateInput v-model="reportFilters.dateFrom" label="Дата с" />
                <DateInput v-model="reportFilters.dateTo" label="Дата по" />
                <div class="control-checklists__panel-actions">
                    <Button color="primary" size="sm" :loading="reportsLoading" @click="loadReports">
                        Показать
                    </Button>
                </div>
            </div>

            <div class="control-checklists__stats">
                <div class="control-checklists__stat-card">
                    <div class="control-checklists__stat-label">Всего прохождений</div>
                    <div class="control-checklists__stat-value">{{ reportTotals.total }}</div>
                </div>
            </div>

            <div class="control-checklists__charts">
                <div class="control-checklists__chart-card">
                    <div class="control-checklists__chart-title">Динамика прохождений</div>
                    <div class="control-checklists__chart-subtitle">
                        {{ reportChartSubtitle }}
                    </div>
                    <div class="control-checklists__chart-bar">
                        <div v-if="!dailyChartItems.length" class="control-checklists__muted">
                            Нет данных за выбранный период.
                        </div>
                        <div v-else class="control-checklists__bar-grid">
                            <div v-for="item in dailyChartItems" :key="item.key" class="control-checklists__bar-item">
                                <div class="control-checklists__bar-value">{{ item.count }}</div>
                                <div class="control-checklists__bar-column">
                                    <div class="control-checklists__bar-fill" :style="{ height: item.height }"></div>
                                </div>
                                <div class="control-checklists__bar-label">{{ item.label }}</div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="control-checklists__chart-card">
                    <div class="control-checklists__chart-title">Средний результат (оценочные)</div>
                    <div class="control-checklists__chart-subtitle">
                        {{ reportScoreSubtitle }}
                    </div>
                    <div class="control-checklists__pie">
                        <div
                            class="control-checklists__pie-chart"
                            :style="pieStyle"
                        ></div>
                        <div class="control-checklists__pie-value">
                            {{ averageScoreLabel }}
                        </div>
                    </div>
                </div>
            </div>

            <div v-if="reportsLoading" class="control-checklists__loading">Загрузка отчётов...</div>
            <div v-else>
                <Table v-if="reportAttempts.length">
                    <thead>
                        <tr>
                            <th>Дата</th>
                            <th>Чек-лист</th>
                            <th>Результат</th>
                            <th>Сотрудник</th>
                            <th>Подразделение</th>
                            <th class="control-checklists__actions-column">Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="attempt in reportAttempts" :key="attempt.id">
                            <td>{{ formatDateTime(attempt.submitted_at) }}</td>
                            <td>{{ attempt.checklist_name }}</td>
                            <td>
                                <span v-if="attempt.is_scored">{{ attempt.result || '—' }}</span>
                                <span v-else class="control-checklists__muted">—</span>
                            </td>
                            <td>{{ attempt.user_name }}</td>
                            <td>{{ attempt.department || '—' }}</td>
                            <td class="control-checklists__actions-column">
                                <div class="control-checklists__actions">
                                    <Button color="ghost" size="sm" @click="openAttemptModal(attempt.id)">
                                        Подробнее
                                    </Button>
                                    <button
                                        type="button"
                                        class="control-checklists__icon-button"
                                        title="PDF"
                                        aria-label="PDF"
                                        @click="handleExportAttempt(attempt.id, 'pdf')"
                                    >
                                        <BaseIcon name="Pdf" />
                                    </button>
                                    <button
                                        type="button"
                                        class="control-checklists__icon-button"
                                        title="Excel"
                                        aria-label="Excel"
                                        @click="handleExportAttempt(attempt.id, 'xlsx')"
                                    >
                                        <BaseIcon name="Excel" />
                                    </button>
                                    <button
                                        type="button"
                                        class="control-checklists__icon-button"
                                        title="Удалить"
                                        aria-label="Удалить"
                                        :disabled="reportsLoading"
                                        @click="handleDeleteAttempt(attempt.id)"
                                    >
                                        <BaseIcon name="Trash" />
                                    </button>
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </Table>
                <p v-else class="control-checklists__empty">Нет пройденных чек-листов по фильтру.</p>
                <div v-if="reportAttempts.length && reportAttempts.length < reportTotal" class="control-checklists__more">
                    <Button color="ghost" size="sm" :loading="reportsLoading" @click="loadMoreAttempts">
                        Показать еще
                    </Button>
                </div>
            </div>
        </section>

        <Modal
            v-if="isAttemptModalOpen"
            class="control-checklists__modal control-checklists__modal--report"
            @close="closeAttemptModal"
        >
            <template #header>
                {{ selectedAttempt?.checklist_name || 'Чек-лист' }}
            </template>
            <template #default>
                <div class="control-checklists__report-meta">
                    <div>
                        <div class="control-checklists__report-label">Дата и время</div>
                        <div class="control-checklists__report-value">
                            {{ selectedAttempt ? formatDateTime(selectedAttempt.submitted_at) : '—' }}
                        </div>
                    </div>
                    <div>
                        <div class="control-checklists__report-label">Проверяемый объект</div>
                        <div class="control-checklists__report-value">
                            {{ selectedAttempt?.department || '—' }}
                        </div>
                    </div>
                    <div>
                        <div class="control-checklists__report-label">Результат</div>
                        <div class="control-checklists__report-value">
                            {{ selectedAttempt?.result || '—' }}
                        </div>
                    </div>
                </div>

                <div v-if="attemptDetailLoading" class="control-checklists__loading">
                    Загрузка ответов...
                </div>
                <div v-else>
                    <div v-if="groupedAttemptSections.length" class="control-checklists__report-sections">
                        <div
                            v-for="section in groupedAttemptSections"
                            :key="section.title"
                            class="control-checklists__report-section"
                        >
                            <h4 class="control-checklists__report-section-title">
                                {{ section.title }}
                            </h4>
                            <div class="control-checklists__report-questions">
                                <div
                                    v-for="answer in section.answers"
                                    :key="answer.question_id"
                                    class="control-checklists__report-question"
                                >
                                    <div class="control-checklists__report-question-text">
                                        {{ answer.question_text }}
                                    </div>
                                    <div class="control-checklists__report-answer">
                                        <span class="control-checklists__report-label">Ответ:</span>
                                        <span>{{ answer.response_value || '—' }}</span>
                                    </div>
                                    <div class="control-checklists__report-answer">
                                        <span class="control-checklists__report-label">Комментарий:</span>
                                        <span>{{ answer.comment || '—' }}</span>
                                    </div>
                                    <div class="control-checklists__report-answer">
                                        <span class="control-checklists__report-label">Фото:</span>
                                        <span v-if="isPhotoUrl(answer.photo_path)">
                                            <Button
                                                color="ghost"
                                                size="sm"
                                                @click="openPhotoPreview(answer.photo_path, answer.question_text)"
                                            >
                                                Показать фото
                                            </Button>
                                        </span>
                                        <span v-else>{{ answer.photo_path ? 'Есть' : '—' }}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <p v-else class="control-checklists__empty">Ответов нет.</p>
                </div>
            </template>
        </Modal>

        <Modal
            v-if="isPhotoPreviewOpen"
            class="control-checklists__modal control-checklists__modal--report"
            @close="closePhotoPreview"
        >
            <template #header>
                Фото
            </template>
            <template #default>
                <div class="control-checklists__photo-preview">
                    <img :src="photoPreviewUrl" alt="Фото" />
                    <div class="control-checklists__photo-caption">
                        {{ photoPreviewCaption }}
                    </div>
                </div>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'vue-toastification';
import { useUserStore } from '@/stores/user';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Select from '@/components/UI-components/Select.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Table from '@/components/UI-components/Table.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import Modal from '@/components/UI-components/Modal.vue';
import BaseIcon from '@/components/UI-components/BaseIcon.vue';
import { useMultiSelect } from '@/composables/useMultiSelect';
import { formatDateTimeValue, formatDateValue } from '@/utils/format';
import {
    createChecklist,
    deleteChecklist,
    fetchChecklists,
    fetchAccessPositions,
    fetchEmployees,
    updateChecklist,
    fetchChecklistReportSummary,
    fetchChecklistReportMetrics,
    fetchChecklistAttempts,
    fetchChecklistAttemptDetail,
    exportChecklistAttempt,
    deleteChecklistAttempt,
    fetchRestaurants,
    fetchRestaurantSubdivisions,
} from '@/api';

const toast = useToast();
const userStore = useUserStore();
const router = useRouter();
const {
    toggleMultiValue,
    countSelectedValues,
    keepAllowedValues,
    buildSelectionLabel,
} = useMultiSelect();

const activeTab = ref('manage');
const loading = ref(false);
const saving = ref(false);
const reportsLoading = ref(false);
const attemptDetailLoading = ref(false);

const checklists = ref([]);
const checklistSearch = ref('');
const isChecklistModalOpen = ref(false);
const restaurants = ref([]);
const subdivisions = ref([]);
const positions = ref([]);
const employees = ref([]);
const openDescriptions = ref(new Set());
const isManageFiltersOpen = ref(false);

const reportSummary = ref([]);
const reportMetrics = ref({ daily_counts: [], average_scored_percent: null, scored_total: 0, departments: [] });
const reportAttempts = ref([]);
const reportTotal = ref(0);
const reportOffset = ref(0);
const reportLimit = ref(25);
const isReportChecklistPanelOpen = ref(false);
const isReportObjectPanelOpen = ref(false);
const selectedAttempt = ref(null);
const isAttemptModalOpen = ref(false);
const isPhotoPreviewOpen = ref(false);
const photoPreviewUrl = ref('');
const photoPreviewCaption = ref('');

const checklistForm = reactive({
    id: null,
    name: '',
    description: '',
    isScored: false,
    restaurantIds: [],
    subdivisionIds: [],
    positionIds: [],
});

const checklistMeta = reactive({
    creatorName: '',
    createdAt: '',
});

const manageFilters = reactive({
    restaurantId: null,
    subdivisionId: null,
    positionId: null,
    scoring: null,
});

const reportFilters = reactive({
    checklistIds: [],
    objectNames: [],
    dateFrom: '',
    dateTo: '',
});

function normalizeNumericIds(ids = []) {
    return ids
        .map((id) => Number(id))
        .filter((id) => Number.isFinite(id));
}

function uniqueNumericIds(ids = []) {
    return Array.from(new Set(normalizeNumericIds(ids)));
}

function toNullableNumber(value) {
    if (value === null || value === undefined || value === '') {
        return null;
    }
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : null;
}

const allowedRestaurantIdSet = computed(() => {
    if (userStore.hasFullRestaurantAccess || userStore.hasGlobalAccess) {
        return null;
    }
    const ids = new Set(
        (userStore.restaurantIds || [])
            .map((id) => Number(id))
            .filter((id) => Number.isFinite(id)),
    );
    if (Number.isFinite(Number(userStore.workplaceRestaurantId))) {
        ids.add(Number(userStore.workplaceRestaurantId));
    }
    return ids;
});

const availableRestaurants = computed(() => {
    const restrictedIds = allowedRestaurantIdSet.value;
    if (restrictedIds === null) {
        return restaurants.value;
    }
    if (!restrictedIds.size) {
        return restaurants.value;
    }
    return restaurants.value.filter((item) => restrictedIds.has(Number(item.id)));
});

const reportChecklistOptions = computed(() =>
    checklists.value.map((item) => ({ value: String(item.id), label: item.name }))
);

const reportObjectOptions = computed(() => {
    const options = new Map();
    const addOption = (label) => {
        if (!label) return;
        options.set(label, { value: label, label });
    };
    const source = reportMetrics.value?.departments || [];
    for (const dep of source) {
        addOption(dep);
    }
    return Array.from(options.values());
});

const positionMap = computed(() => {
    const map = new Map();
    for (const position of positions.value) {
        map.set(position.id, position.name);
    }
    return map;
});

const restaurantSubdivisionMap = computed(() => {
    const map = new Map();
    for (const employee of employees.value) {
        const subdivisionId = employee?.restaurant_subdivision_id;
        const workplaceId = employee?.workplace_restaurant_id;
        if (!subdivisionId || !workplaceId) {
            continue;
        }
        if (!map.has(workplaceId)) {
            map.set(workplaceId, new Set());
        }
        map.get(workplaceId).add(subdivisionId);
    }
    return map;
});

const subdivisionRestaurantMap = computed(() => {
    const map = new Map();
    for (const [restaurantId, subdivisionIds] of restaurantSubdivisionMap.value.entries()) {
        for (const subdivisionId of subdivisionIds) {
            if (!map.has(subdivisionId)) {
                map.set(subdivisionId, new Set());
            }
            map.get(subdivisionId).add(Number(restaurantId));
        }
    }
    return map;
});

const subdivisionMap = computed(() => {
    const map = new Map();
    for (const subdivision of subdivisions.value) {
        map.set(subdivision.id, subdivision.name);
    }
    return map;
});

const restaurantMap = computed(() => {
    const map = new Map();
    for (const restaurant of restaurants.value) {
        map.set(restaurant.id, restaurant.name);
    }
    return map;
});

const restaurantCompanyMap = computed(() => {
    const map = new Map();
    for (const restaurant of restaurants.value) {
        map.set(Number(restaurant.id), Number(restaurant.company_id));
    }
    return map;
});

const manageSelectedRestaurantId = computed(() => toNullableNumber(manageFilters.restaurantId));
const manageSelectedSubdivisionId = computed(() => toNullableNumber(manageFilters.subdivisionId));
const manageSelectedPositionId = computed(() => toNullableNumber(manageFilters.positionId));

const manageFilteredSubdivisions = computed(() => {
    const restaurantId = manageSelectedRestaurantId.value;
    if (!restaurantId) {
        return subdivisions.value;
    }
    const allowedIds = restaurantSubdivisionMap.value.get(restaurantId);
    if (!allowedIds?.size) {
        return [];
    }
    return subdivisions.value.filter((item) => allowedIds.has(item.id));
});

const manageFilteredPositions = computed(() => {
    const subdivisionId = manageSelectedSubdivisionId.value;
    if (subdivisionId) {
        return positions.value.filter((item) => Number(item.restaurant_subdivision_id) === subdivisionId);
    }
    const restaurantId = manageSelectedRestaurantId.value;
    if (!restaurantId) {
        return positions.value;
    }
    const allowedIds = restaurantSubdivisionMap.value.get(restaurantId);
    if (!allowedIds?.size) {
        return [];
    }
    return positions.value.filter((item) => allowedIds.has(item.restaurant_subdivision_id));
});

const manageRestaurantFilterOptions = computed(() =>
    availableRestaurants.value.map((item) => ({
        value: item.id,
        label: item.name,
    })),
);

const manageSubdivisionFilterOptions = computed(() =>
    manageFilteredSubdivisions.value.map((item) => ({
        value: item.id,
        label: item.name,
    })),
);

const managePositionFilterOptions = computed(() =>
    manageFilteredPositions.value.map((item) => ({
        value: item.id,
        label: formatPositionOption(item),
    })),
);

const manageScoringFilterOptions = [
    { value: 'scored', label: 'Оцениваемые' },
    { value: 'plain', label: 'Неоцениваемые' },
];

const selectedRestaurantIds = computed(() =>
    normalizeNumericIds(checklistForm.restaurantIds),
);

const filteredSubdivisions = computed(() => {
    if (!subdivisions.value.length) {
        return [];
    }
    const selected = selectedRestaurantIds.value;
    if (!selected.length) {
        return [];
    }
    const subdivisionIds = new Set();
    for (const restaurantId of selected) {
        const ids = restaurantSubdivisionMap.value.get(restaurantId);
        if (!ids || !ids.size) {
            continue;
        }
        ids.forEach((id) => subdivisionIds.add(id));
    }
    if (!subdivisionIds.size) {
        return subdivisions.value;
    }
    return subdivisions.value.filter((item) => subdivisionIds.has(item.id));
});

const selectedSubdivisionIds = computed(() =>
    normalizeNumericIds(checklistForm.subdivisionIds),
);

const selectedSubdivisionIdSet = computed(() => new Set(selectedSubdivisionIds.value));

const filteredPositions = computed(() => {
    let items = positions.value;
    if (selectedSubdivisionIdSet.value.size) {
        items = items.filter((item) => selectedSubdivisionIdSet.value.has(item.restaurant_subdivision_id));
    } else {
        const selected = selectedRestaurantIds.value;
        if (selected.length) {
            const allowedSubdivisions = new Set();
            for (const restaurantId of selected) {
                const ids = restaurantSubdivisionMap.value.get(restaurantId);
                if (!ids || !ids.size) {
                    continue;
                }
                ids.forEach((id) => allowedSubdivisions.add(id));
            }
            if (allowedSubdivisions.size) {
                items = items.filter((item) => allowedSubdivisions.has(item.restaurant_subdivision_id));
            }
        }
    }
    return items;
});

const positionSelectionCount = computed(() =>
    countSelectedValues(
        checklistForm.positionIds,
        filteredPositions.value.map((item) => item.id),
    ),
);

const restaurantSelectionCount = computed(() =>
    countSelectedValues(
        checklistForm.restaurantIds,
        availableRestaurants.value.map((item) => item.id),
    ),
);

const allPositionsSelected = computed(() => {
    const total = filteredPositions.value.length;
    return Boolean(total) && positionSelectionCount.value === total;
});

const allRestaurantsSelected = computed(() => {
    const total = availableRestaurants.value.length;
    return Boolean(total) && restaurantSelectionCount.value === total;
});

const allSubdivisionsSelected = computed(() => checklistForm.subdivisionIds.length === 0);

const subdivisionSelectionCount = computed(() =>
    countSelectedValues(
        checklistForm.subdivisionIds,
        filteredSubdivisions.value.map((item) => item.id),
    ),
);

const positionSelectionLabel = computed(() =>
    buildSelectionLabel({
        totalCount: filteredPositions.value.length,
        selectedCount: positionSelectionCount.value,
        noneLabel: 'Нет должностей',
        allLabel: 'Все',
        emptyLabel: 'Не выбрано',
        fullMeansAll: true,
    }),
);

const subdivisionSelectionLabel = computed(() =>
    buildSelectionLabel({
        totalCount: filteredSubdivisions.value.length,
        selectedCount: subdivisionSelectionCount.value,
        noneLabel: 'Нет подразделений',
        allLabel: 'Все',
        emptyLabel: 'Не выбрано',
        emptyMeansAll: true,
    }),
);

const restaurantSelectionLabel = computed(() =>
    buildSelectionLabel({
        totalCount: availableRestaurants.value.length,
        selectedCount: restaurantSelectionCount.value,
        noneLabel: 'Нет ресторанов',
        allLabel: 'Все рестораны',
        emptyLabel: 'Не выбрано',
        fullMeansAll: true,
    }),
);

const reportTotals = computed(() => {
    const total = reportSummary.value.reduce((acc, item) => acc + (item.total_completed || 0), 0);
    return {
        total,
    };
});

const reportChecklistSelectionLabel = computed(() =>
    buildSelectionLabel({
        totalCount: checklists.value.length,
        selectedCount: reportFilters.checklistIds.length,
        noneLabel: 'Нет чек-листов',
        allLabel: 'Все чек-листы',
        emptyLabel: 'Не выбрано',
        emptyMeansAll: true,
    }),
);

const reportObjectSelectionLabel = computed(() =>
    buildSelectionLabel({
        totalCount: reportObjectOptions.value.length,
        selectedCount: reportFilters.objectNames.length,
        noneLabel: 'Все объекты',
        allLabel: 'Все объекты',
        emptyLabel: 'Не выбрано',
        emptyMeansAll: true,
    }),
);

const allReportChecklistsSelected = computed(() => reportFilters.checklistIds.length === 0);
const allReportObjectsSelected = computed(() => reportFilters.objectNames.length === 0);

const dailyChartItems = computed(() => {
    const rows = reportMetrics.value?.daily_counts || [];
    if (!rows.length) {
        return [];
    }
    const max = Math.max(...rows.map((item) => item.total || 0), 1);
    return rows.map((item) => {
        const count = Number(item.total || 0);
        const height = `${Math.round((count / max) * 120)}px`;
        const label = formatDateValue(item.date, {
            emptyValue: '',
            invalidValue: item.date,
            locale: 'ru-RU',
            options: {
                timeZone: 'Europe/Moscow',
                day: '2-digit',
                month: '2-digit',
            },
        });
        return {
            key: item.date,
            count,
            height,
            label,
        };
    });
});

const reportChartSubtitle = computed(() => {
    if (!dailyChartItems.value.length) {
        return 'Нет данных';
    }
    return `За период: ${reportFilters.dateFrom || 'все'} — ${reportFilters.dateTo || 'сегодня'}`;
});

const averageScorePercent = computed(() => {
    const raw = reportMetrics.value?.average_scored_percent;
    if (raw === null || raw === undefined || Number.isNaN(Number(raw))) {
        return null;
    }
    return Math.max(0, Math.min(100, Number(raw)));
});

const averageScoreLabel = computed(() => {
    if (averageScorePercent.value === null) {
        return '—';
    }
    return `${averageScorePercent.value}%`;
});

const reportScoreSubtitle = computed(() => {
    const count = reportMetrics.value?.scored_total || 0;
    if (!count) {
        return 'Нет оценочных прохождений';
    }
    return `Прохождений: ${count}`;
});

const pieStyle = computed(() => {
    if (averageScorePercent.value === null) {
        return {
            background:
                'conic-gradient(color-mix(in srgb, var(--color-primary) 16%, var(--color-surface) 84%) 0deg, color-mix(in srgb, var(--color-primary) 16%, var(--color-surface) 84%) 360deg)',
        };
    }
    const percent = averageScorePercent.value;
    return {
        background: `conic-gradient(var(--color-primary) ${percent}%, color-mix(in srgb, var(--color-primary) 16%, var(--color-surface) 84%) ${percent}% 100%)`,
    };
});

const groupedAttemptSections = computed(() => {
    if (!selectedAttempt.value?.answers?.length) {
        return [];
    }
    const map = new Map();
    for (const answer of selectedAttempt.value.answers) {
        const key = answer.section_title || 'Без раздела';
        if (!map.has(key)) {
            map.set(key, []);
        }
        map.get(key).push(answer);
    }
    return Array.from(map.entries()).map(([title, answers]) => ({ title, answers }));
});

const hasManageFilters = computed(
    () =>
        manageSelectedRestaurantId.value !== null
        || manageSelectedSubdivisionId.value !== null
        || manageSelectedPositionId.value !== null
        || Boolean(manageFilters.scoring),
);

const hasManageRefinements = computed(
    () => hasManageFilters.value || Boolean(checklistSearch.value.trim()),
);

const activeManageFilterCount = computed(
    () =>
        [
            manageSelectedRestaurantId.value,
            manageSelectedSubdivisionId.value,
            manageSelectedPositionId.value,
            manageFilters.scoring,
        ].filter((value) => value !== null && value !== undefined && value !== '').length,
);

const manageFilterSummaryLabel = computed(() => {
    if (!hasManageFilters.value) {
        return 'Все чек-листы';
    }
    return `Активно: ${activeManageFilterCount.value}`;
});

const filteredChecklists = computed(() => {
    const term = checklistSearch.value.trim().toLowerCase();
    return checklists.value.filter((item) => {
        const haystack = [item.name, item.description].filter(Boolean).join(' ').toLowerCase();
        if (term && !haystack.includes(term)) {
            return false;
        }
        if (
            manageSelectedRestaurantId.value !== null
            && !checklistAppliesToRestaurant(item, manageSelectedRestaurantId.value)
        ) {
            return false;
        }
        if (
            manageSelectedSubdivisionId.value !== null
            && !checklistAppliesToSubdivision(item, manageSelectedSubdivisionId.value)
        ) {
            return false;
        }
        if (
            manageSelectedPositionId.value !== null
            && !normalizeNumericIds(item.position_ids).includes(manageSelectedPositionId.value)
        ) {
            return false;
        }
        if (manageFilters.scoring === 'scored' && !item.is_scored) {
            return false;
        }
        if (manageFilters.scoring === 'plain' && item.is_scored) {
            return false;
        }
        return true;
    });
});

const manageResultsLabel = computed(() => {
    const total = checklists.value.length;
    if (!total) {
        return 'Чек-листов пока нет.';
    }
    if (!hasManageRefinements.value) {
        return `Всего чек-листов: ${total}`;
    }
    return `Показано ${filteredChecklists.value.length} из ${total}`;
});

const manageEmptyState = computed(() => {
    if (!checklists.value.length) {
        return 'Чек-листы еще не созданы.';
    }
    return 'По выбранным фильтрам ничего не найдено.';
});

const canEditAllChecklists = computed(() =>
    userStore.hasAnyPermission('checklists.edit_all', 'companies.manage', 'staff.manage_all', 'system.admin'),
);

function canEditChecklist(item) {
    if (canEditAllChecklists.value) {
        return true;
    }
    if (!item || !item.created_by || !userStore.id) {
        return false;
    }
    return Number(item.created_by) === Number(userStore.id);
}

const POSITION_PREVIEW_LIMIT = 3;

function getPositionNames(ids = []) {
    return ids
        .map((id) => positionMap.value.get(id))
        .filter(Boolean);
}

function formatPositions(ids = []) {
    return getPositionNames(ids).join(', ');
}

function formatPositionsPreview(ids = [], limit = POSITION_PREVIEW_LIMIT) {
    const names = getPositionNames(ids);
    if (names.length <= limit) {
        return names.join(', ');
    }

    const visible = names.slice(0, limit).join(', ');
    const hiddenCount = names.length - limit;
    return `${visible} +${hiddenCount}`;
}

function formatPositionOption(position) {
    const name = position?.name || 'Должность';
    const subdivision = position?.restaurant_subdivision_name;
    return subdivision ? `${name} · ${subdivision}` : name;
}

function formatScope(item) {
    if (item.all_restaurants) {
        return 'Все рестораны';
    }
    if (item.scope_type === 'restaurants_multi' && Array.isArray(item.control_restaurant_ids)) {
        const restaurantIds = normalizeNumericIds(item.control_restaurant_ids);
        if (restaurantIds.length === 1) {
            return restaurantMap.value.get(restaurantIds[0]) || 'Ресторан';
        }
        if (restaurantIds.length > 1) {
            return `Ресторанов: ${restaurantIds.length}`;
        }
    }
    if (item.restaurant_id) {
        return restaurantMap.value.get(item.restaurant_id) || 'Ресторан';
    }
    if (item.access_all_subdivisions) {
        return 'Все подразделения';
    }
    if (Array.isArray(item.access_subdivision_ids) && item.access_subdivision_ids.length) {
        if (item.access_subdivision_ids.length === 1) {
            return subdivisionMap.value.get(item.access_subdivision_ids[0]) || 'Подразделение';
        }
        return `Подразделений: ${item.access_subdivision_ids.length}`;
    }
    if (item.scope_type === 'subdivision' && item.restaurant_subdivision_id) {
        return subdivisionMap.value.get(item.restaurant_subdivision_id) || 'Подразделение';
    }
    if (item.scope_type === 'restaurant') {
        return 'Ресторан';
    }
    return '—';
}

function checklistAppliesToRestaurant(item, restaurantId) {
    const targetRestaurantId = Number(restaurantId);
    if (!Number.isFinite(targetRestaurantId)) {
        return true;
    }
    if (item.all_restaurants) {
        return Number(restaurantCompanyMap.value.get(targetRestaurantId)) === Number(item.company_id);
    }
    const restaurantIds = uniqueNumericIds(item.control_restaurant_ids);
    if (restaurantIds.length) {
        return restaurantIds.includes(targetRestaurantId);
    }
    if (item.restaurant_id) {
        return Number(item.restaurant_id) === targetRestaurantId;
    }
    const subdivisionIds = uniqueNumericIds(item.access_subdivision_ids);
    if (subdivisionIds.length) {
        return subdivisionIds.some((subdivisionId) =>
            subdivisionRestaurantMap.value.get(subdivisionId)?.has(targetRestaurantId),
        );
    }
    if (item.restaurant_subdivision_id) {
        return Boolean(
            subdivisionRestaurantMap.value.get(Number(item.restaurant_subdivision_id))?.has(targetRestaurantId),
        );
    }
    return false;
}

function checklistAppliesToSubdivision(item, subdivisionId) {
    const targetSubdivisionId = Number(subdivisionId);
    if (!Number.isFinite(targetSubdivisionId)) {
        return true;
    }
    const subdivisionIds = uniqueNumericIds(item.access_subdivision_ids);
    if (subdivisionIds.length) {
        return subdivisionIds.includes(targetSubdivisionId);
    }
    if (item.restaurant_subdivision_id) {
        return Number(item.restaurant_subdivision_id) === targetSubdivisionId;
    }
    const restaurantIds = subdivisionRestaurantMap.value.get(targetSubdivisionId);
    if (!restaurantIds?.size) {
        return false;
    }
    for (const restaurantId of restaurantIds) {
        if (checklistAppliesToRestaurant(item, restaurantId)) {
            return true;
        }
    }
    return false;
}

function toggleDescription(id) {
    const set = new Set(openDescriptions.value);
    if (set.has(id)) {
        set.delete(id);
    } else {
        set.add(id);
    }
    openDescriptions.value = set;
}

function handleChecklistRowClick(item) {
    if (!canEditChecklist(item)) {
        return;
    }
    openChecklistModal(item);
}

function openChecklistModal(item = null) {
    if (item) {
        checklistForm.id = item.id;
        checklistForm.name = item.name;
        checklistForm.description = item.description || '';
        checklistForm.isScored = Boolean(item.is_scored);
        checklistForm.positionIds = Array.isArray(item.position_ids) ? [...item.position_ids] : [];
        checklistForm.subdivisionIds = Array.isArray(item.access_subdivision_ids)
            ? [...item.access_subdivision_ids]
            : [];
        if (item.access_all_subdivisions) {
            checklistForm.subdivisionIds = [];
        }
        if (!checklistForm.subdivisionIds.length && item.restaurant_subdivision_id) {
            checklistForm.subdivisionIds = [item.restaurant_subdivision_id];
        }
        if (item.scope_type === 'restaurants_multi' && Array.isArray(item.control_restaurant_ids)) {
            checklistForm.restaurantIds = normalizeNumericIds(item.control_restaurant_ids);
        } else if (item.all_restaurants) {
            checklistForm.restaurantIds = restaurants.value
                .filter((restaurant) => Number(restaurant.company_id) === Number(item.company_id))
                .map((restaurant) => restaurant.id);
        } else if (item.restaurant_id) {
            checklistForm.restaurantIds = [Number(item.restaurant_id)];
        } else {
            checklistForm.restaurantIds = [];
        }
        if (!checklistForm.subdivisionIds.length) {
            const fromPositions = new Set();
            for (const posId of checklistForm.positionIds) {
                const position = positions.value.find((item) => item.id === posId);
                if (position?.restaurant_subdivision_id) {
                    fromPositions.add(position.restaurant_subdivision_id);
                }
            }
            if (fromPositions.size) {
                checklistForm.subdivisionIds = Array.from(fromPositions);
            }
        }
        checklistForm.restaurantIds = keepAllowedValues(
            checklistForm.restaurantIds,
            availableRestaurants.value.map((restaurant) => restaurant.id),
        );
        checklistMeta.creatorName = item.creator_name || '';
        checklistMeta.createdAt = item.created_at || '';
    } else {
        resetChecklistForm();
    }
    isChecklistModalOpen.value = true;
}

function closeChecklistModal() {
    isChecklistModalOpen.value = false;
    if (!saving.value) {
        resetChecklistForm();
    }
}

function formatDateTime(value) {
    return formatDateTimeValue(value, {
        emptyValue: '',
        invalidValue: value,
        locale: 'ru-RU',
        timeZone: 'Europe/Moscow',
    });
}

function isPhotoUrl(value) {
    return typeof value === 'string' && value.startsWith('http');
}

function handleTogglePosition(id, checked) {
    toggleMultiValue(checklistForm.positionIds, id, checked);
}

function handleToggleRestaurant(id, checked) {
    toggleMultiValue(checklistForm.restaurantIds, id, checked);
}

function handleToggleAllRestaurants(checked) {
    if (checked) {
        checklistForm.restaurantIds = availableRestaurants.value.map((item) => item.id);
        return;
    }
    checklistForm.restaurantIds = [];
}

function handleToggleSubdivision(id, checked) {
    toggleMultiValue(checklistForm.subdivisionIds, id, checked);
}

function handleToggleAllPositions(checked) {
    if (checked) {
        checklistForm.positionIds = filteredPositions.value.map((item) => item.id);
    } else {
        checklistForm.positionIds = [];
    }
}

function handleToggleAllSubdivisions(checked) {
    if (checked) {
        checklistForm.subdivisionIds = [];
    }
}

function toggleManageFilters() {
    isManageFiltersOpen.value = !isManageFiltersOpen.value;
}

function resetManageFilters() {
    manageFilters.restaurantId = null;
    manageFilters.subdivisionId = null;
    manageFilters.positionId = null;
    manageFilters.scoring = null;
}

function openPortal() {
    window.open('/checklists/portal', '_blank');
}

function toggleReportChecklistPanel() {
    isReportObjectPanelOpen.value = false;
    isReportChecklistPanelOpen.value = !isReportChecklistPanelOpen.value;
}

function toggleReportObjectPanel() {
    isReportChecklistPanelOpen.value = false;
    isReportObjectPanelOpen.value = !isReportObjectPanelOpen.value;
}

function handleToggleReportChecklist(value, checked) {
    const id = Number(value);
    if (!Number.isFinite(id)) {
        return;
    }
    toggleMultiValue(reportFilters.checklistIds, id, checked);
}

function handleToggleAllReportChecklists(checked) {
    if (checked) {
        reportFilters.checklistIds = [];
    }
}

function handleToggleReportObject(value, checked) {
    toggleMultiValue(reportFilters.objectNames, value, checked);
}

function handleToggleAllReportObjects(checked) {
    if (checked) {
        reportFilters.objectNames = [];
    }
}

async function loadAll() {
    loading.value = true;
    try {
        const results = await Promise.allSettled([
            fetchChecklists(),
            fetchAccessPositions(),
            fetchRestaurants(),
            fetchRestaurantSubdivisions(),
            fetchEmployees({ include_fired: true, limit: 1000 }),
        ]);
        const [checklistsData, positionsData, restaurantsData, subdivisionsData, employeesData] = results.map(
            (res) => (res.status === 'fulfilled' ? res.value : []),
        );
        checklists.value = Array.isArray(checklistsData) ? checklistsData : [];
        positions.value = Array.isArray(positionsData) ? positionsData : [];
        restaurants.value = Array.isArray(restaurantsData) ? restaurantsData : [];
        subdivisions.value = Array.isArray(subdivisionsData) ? subdivisionsData : [];
        employees.value = Array.isArray(employeesData?.items) ? employeesData.items : [];
    } catch (error) {
        console.error(error);
        toast.error('Не удалось загрузить данные.');
    } finally {
        loading.value = false;
    }
}

async function loadReports(reset = true) {
    reportsLoading.value = true;
    try {
        if (reset) {
            reportOffset.value = 0;
            reportAttempts.value = [];
        }
        const params = {
            checklist_ids: reportFilters.checklistIds.length ? reportFilters.checklistIds : undefined,
            departments: reportFilters.objectNames.length ? reportFilters.objectNames : undefined,
            date_from: reportFilters.dateFrom || undefined,
            date_to: reportFilters.dateTo || undefined,
        };
        const [summaryData, metricsData, attemptsData] = await Promise.all([
            fetchChecklistReportSummary(params),
            fetchChecklistReportMetrics(params),
            fetchChecklistAttempts({
                ...params,
                limit: reportLimit.value,
                offset: reportOffset.value,
            }),
        ]);
        reportSummary.value = Array.isArray(summaryData) ? summaryData : [];
        reportMetrics.value = metricsData || {
            daily_counts: [],
            average_scored_percent: null,
            scored_total: 0,
            departments: [],
        };
        const items = Array.isArray(attemptsData?.items) ? attemptsData.items : [];
        reportAttempts.value = reset ? items : [...reportAttempts.value, ...items];
        reportTotal.value = Number(attemptsData?.total || 0);
        reportOffset.value = reportAttempts.value.length;
    } catch (error) {
        console.error(error);
        toast.error('Не удалось загрузить отчеты.');
    } finally {
        reportsLoading.value = false;
    }
}

async function loadMoreAttempts() {
    await loadReports(false);
}

async function handleSubmitChecklist() {
    if (!checklistForm.name?.trim()) {
        toast.error('Укажите название чек-листа.');
        return;
    }
    const selectedRestaurantIds = uniqueNumericIds(checklistForm.restaurantIds);
    if (!selectedRestaurantIds.length) {
        toast.error('Выберите хотя бы один ресторан.');
        return;
    }
    const selectedPositionIds = uniqueNumericIds(checklistForm.positionIds);
    if (!selectedPositionIds.length) {
        toast.error('Выберите хотя бы одну должность.');
        return;
    }
    const selectedRestaurants = restaurants.value.filter((item) => selectedRestaurantIds.includes(Number(item.id)));
    const companyIds = Array.from(
        new Set(
            selectedRestaurants
                .map((item) => Number(item.company_id))
                .filter((id) => Number.isFinite(id)),
        ),
    );
    if (!companyIds.length) {
        toast.error('Не удалось определить компанию выбранных ресторанов.');
        return;
    }
    if (companyIds.length > 1) {
        toast.error('Чек-лист можно привязать только к ресторанам одной компании.');
        return;
    }
    saving.value = true;
    try {
        const selectedSubdivisionIds = normalizeNumericIds(checklistForm.subdivisionIds);
        const availableRestaurantIds = availableRestaurants.value.map((item) => Number(item.id));
        const isAllRestaurants = availableRestaurantIds.length > 0
            && selectedRestaurantIds.length === availableRestaurantIds.length;

        let scopeType = 'restaurant';
        let restaurantId = null;
        let restaurantIdsForScope = null;

        if (isAllRestaurants) {
            scopeType = 'restaurant';
            restaurantId = null;
        } else if (selectedRestaurantIds.length === 1) {
            scopeType = 'restaurant';
            restaurantId = selectedRestaurantIds[0];
        } else {
            scopeType = 'restaurants_multi';
            restaurantId = null;
            restaurantIdsForScope = selectedRestaurantIds;
        }

        const payload = {
            name: checklistForm.name.trim(),
            description: checklistForm.description?.trim() || null,
            company_id: companyIds[0],
            is_scored: checklistForm.isScored,
            position_ids: selectedPositionIds,
            access_subdivision_ids: selectedSubdivisionIds,
            access_all_subdivisions: selectedSubdivisionIds.length === 0,
            scope_type: scopeType,
            restaurant_subdivision_id: null,
            all_restaurants: isAllRestaurants,
            restaurant_id: restaurantId,
            control_restaurant_ids: restaurantIdsForScope,
            control_all_restaurants: false,
        };

        if (checklistForm.id) {
            await updateChecklist(checklistForm.id, payload);
            toast.success('Чек-лист обновлен.');
            await goManage(checklistForm.id);
        } else {
            const created = await createChecklist(payload);
            toast.success('Чек-лист создан.');
            await loadAll();
            if (created?.id) {
                await goManage(created.id);
            }
        }
        closeChecklistModal();
    } catch (error) {
        console.error(error);
        toast.error('Не удалось сохранить чек-лист.');
    } finally {
        saving.value = false;
    }
}

function resetChecklistForm() {
    checklistForm.id = null;
    checklistForm.name = '';
    checklistForm.description = '';
    checklistForm.isScored = false;
    checklistForm.restaurantIds = [];
    checklistForm.subdivisionIds = [];
    checklistForm.positionIds = [];
    checklistMeta.creatorName = '';
    checklistMeta.createdAt = '';
}

async function handleDeleteChecklist(id) {
    if (!confirm('Удалить чек-лист?')) {
        return;
    }
    saving.value = true;
    try {
        await deleteChecklist(id);
        toast.success('Чек-лист удален.');
        await loadAll();
    } catch (error) {
        console.error(error);
        toast.error('Не удалось удалить чек-лист.');
    } finally {
        saving.value = false;
    }
}

async function goManage(id) {
    await router.push({ name: 'control-checklists-manage', params: { id } });
}

async function openAttemptModal(id) {
    attemptDetailLoading.value = true;
    try {
        const data = await fetchChecklistAttemptDetail(id);
        selectedAttempt.value = data || null;
        isAttemptModalOpen.value = true;
    } catch (error) {
        console.error(error);
        toast.error('Не удалось загрузить отчет.');
    } finally {
        attemptDetailLoading.value = false;
    }
}

function closeAttemptModal() {
    isAttemptModalOpen.value = false;
    selectedAttempt.value = null;
}

function openPhotoPreview(url, caption = '') {
    photoPreviewUrl.value = url;
    photoPreviewCaption.value = caption;
    isPhotoPreviewOpen.value = true;
}

function closePhotoPreview() {
    isPhotoPreviewOpen.value = false;
    photoPreviewUrl.value = '';
    photoPreviewCaption.value = '';
}

async function handleExportAttempt(id, format) {
    try {
        const blob = await exportChecklistAttempt(id, format);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `checklist_attempt_${id}.${format === 'pdf' ? 'pdf' : 'xlsx'}`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    } catch (error) {
        console.error(error);
        toast.error('Не удалось сформировать отчет.');
    }
}

async function handleDeleteAttempt(id) {
    if (!confirm('Удалить результат прохождения?')) {
        return;
    }
    try {
        await deleteChecklistAttempt(id);
        toast.success('Результат удален.');
        if (selectedAttempt.value?.id === id) {
            closeAttemptModal();
        }
        await loadReports();
    } catch (error) {
        console.error(error);
        toast.error('Не удалось удалить результат.');
    }
}


onMounted(async () => {
    await loadAll();
    await loadReports();
});

watch(
    availableRestaurants,
    () => {
        const allowedRestaurantIds = availableRestaurants.value.map((item) => item.id);
        checklistForm.restaurantIds = keepAllowedValues(checklistForm.restaurantIds, allowedRestaurantIds);
        const allowedSubdivisionIds = filteredSubdivisions.value.map((item) => item.id);
        checklistForm.subdivisionIds = keepAllowedValues(checklistForm.subdivisionIds, allowedSubdivisionIds);
    },
    { immediate: true },
);

watch(
    () => checklistForm.restaurantIds,
    () => {
        const allowedIds = filteredSubdivisions.value.map((item) => item.id);
        checklistForm.subdivisionIds = keepAllowedValues(checklistForm.subdivisionIds, allowedIds);
    },
    { deep: true },
);

watch(
    filteredSubdivisions,
    (list) => {
        checklistForm.subdivisionIds = keepAllowedValues(
            checklistForm.subdivisionIds,
            list.map((item) => item.id),
        );
    },
    { immediate: true },
);

watch(
    filteredPositions,
    (list) => {
        checklistForm.positionIds = keepAllowedValues(
            checklistForm.positionIds,
            list.map((item) => item.id),
        );
    },
    { immediate: true },
);

watch(
    manageRestaurantFilterOptions,
    (list) => {
        const allowedValues = list.map((item) => item.value);
        if (!allowedValues.includes(manageSelectedRestaurantId.value)) {
            manageFilters.restaurantId = null;
        }
    },
    { immediate: true },
);

watch(
    manageSubdivisionFilterOptions,
    (list) => {
        const allowedValues = list.map((item) => item.value);
        if (!allowedValues.includes(manageSelectedSubdivisionId.value)) {
            manageFilters.subdivisionId = null;
        }
    },
    { immediate: true },
);

watch(
    managePositionFilterOptions,
    (list) => {
        const allowedValues = list.map((item) => item.value);
        if (!allowedValues.includes(manageSelectedPositionId.value)) {
            manageFilters.positionId = null;
        }
    },
    { immediate: true },
);
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/control-checklists' as *;
</style>
