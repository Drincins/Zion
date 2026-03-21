<template>
    <div class="inventory-catalog">
        <header class="inventory-catalog__header">
            <div class="inventory-catalog__header-main">
                <h1 class="inventory-catalog__title">Каталог товаров</h1>
                <p class="inventory-catalog__subtitle">
                    Полный каталог товаров компании с иерархией групп, категорий и видов.
                </p>
            </div>
            <div class="inventory-catalog__header-actions">
                <Button color="secondary" size="sm" :loading="loading" @click="loadItems">Обновить</Button>
                <Button v-if="canCreateNomenclature" color="primary" size="sm" @click="openCreateModal">Новый товар</Button>
            </div>
        </header>

        <section class="inventory-catalog__filters-panel">
            <button class="inventory-catalog__filters-toggle" type="button" @click="toggleFilters">
                Фильтры
                <span :class="['inventory-catalog__filters-icon', { 'is-open': isFiltersOpen }]">▼</span>
            </button>
            <div v-if="isFiltersOpen" class="inventory-catalog__filters-content">
                <div class="inventory-catalog__filters-row">
                    <Input
                        v-model="searchQuery"
                        label=""
                        class="inventory-catalog__search-control"
                        placeholder="Поиск по названию, описанию или коду товара"
                    />
                    <p class="inventory-catalog__summary">
                        Найдено: <strong>{{ filteredItems.length }}</strong>
                    </p>
                    <Button v-if="searchQuery" color="ghost" size="sm" @click="clearSearch">Сбросить</Button>
                </div>
            </div>
        </section>

        <section class="inventory-catalog__tree-card">
            <div v-if="loading" class="inventory-page__loading">Загрузка каталога...</div>

            <div v-else-if="groupedCatalog.length" :class="['inventory-catalog__workspace', { 'is-detail-hidden': !isDetailPaneVisible }]">
                <div class="inventory-catalog__tree-pane">
                    <div class="inventory-catalog__tree-toolbar">
                        <Button color="ghost" size="sm" @click="expandAllVisible">Развернуть всё</Button>
                        <Button color="ghost" size="sm" @click="collapseAll">Свернуть всё</Button>
                        <Button color="ghost" size="sm" @click="toggleDetailPane">
                            {{ isDetailPaneVisible ? 'Скрыть карточку' : 'Показать карточку' }}
                        </Button>
                    </div>

                    <div class="inventory-catalog__tree">
                        <div
                            v-for="groupNode in groupedCatalog"
                            :key="`g:${groupNode.id}`"
                            class="inventory-catalog__group"
                        >
                            <button
                                type="button"
                                class="inventory-catalog__line inventory-catalog__line--group"
                                @click="toggleGroup(groupNode.id)"
                            >
                                <span class="inventory-catalog__arrow">{{ isGroupExpanded(groupNode.id) ? '⌄' : '›' }}</span>
                                <span class="inventory-catalog__line-title">
                                    <template v-for="(part, partIndex) in getHighlightedParts(groupNode.name)" :key="`group:${groupNode.id}:${partIndex}`">
                                        <mark v-if="part.match" class="inventory-catalog__match">{{ part.text }}</mark>
                                        <span v-else>{{ part.text }}</span>
                                    </template>
                                </span>
                                <span class="inventory-catalog__line-count">{{ groupNode.itemsCount }} товаров</span>
                            </button>

                            <template v-if="isGroupExpanded(groupNode.id)">
                                <div
                                    v-for="categoryNode in groupNode.categories"
                                    :key="`c:${categoryNode.id}`"
                                    class="inventory-catalog__category"
                                >
                                    <button
                                        type="button"
                                        class="inventory-catalog__line inventory-catalog__line--category"
                                        @click="toggleCategory(categoryNode.id)"
                                    >
                                        <span class="inventory-catalog__arrow">{{ isCategoryExpanded(categoryNode.id) ? '⌄' : '›' }}</span>
                                        <span class="inventory-catalog__line-title">
                                            <template v-for="(part, partIndex) in getHighlightedParts(categoryNode.name)" :key="`category:${categoryNode.id}:${partIndex}`">
                                                <mark v-if="part.match" class="inventory-catalog__match">{{ part.text }}</mark>
                                                <span v-else>{{ part.text }}</span>
                                            </template>
                                        </span>
                                        <span class="inventory-catalog__line-count">{{ categoryNode.itemsCount }} товаров</span>
                                    </button>

                                    <template v-if="isCategoryExpanded(categoryNode.id)">
                                        <div
                                            v-for="kindNode in categoryNode.kinds"
                                            :key="`t:${kindNode.id}`"
                                            class="inventory-catalog__kind"
                                        >
                                            <button
                                                type="button"
                                                class="inventory-catalog__line inventory-catalog__line--kind"
                                                @click="toggleKind(kindNode.id)"
                                            >
                                                <span class="inventory-catalog__arrow">{{ isKindExpanded(kindNode.id) ? '⌄' : '›' }}</span>
                                                <span class="inventory-catalog__line-title">
                                                    <template v-for="(part, partIndex) in getHighlightedParts(kindNode.name)" :key="`kind:${kindNode.id}:${partIndex}`">
                                                        <mark v-if="part.match" class="inventory-catalog__match">{{ part.text }}</mark>
                                                        <span v-else>{{ part.text }}</span>
                                                    </template>
                                                </span>
                                                <span class="inventory-catalog__line-count">{{ kindNode.items.length }} товаров</span>
                                            </button>

                                            <div v-if="isKindExpanded(kindNode.id)" class="inventory-catalog__items">
                                                <div
                                                    v-for="item in kindNode.items"
                                                    :key="item.id"
                                                    :class="[
                                                        'inventory-catalog__item-row',
                                                        {
                                                            'is-selected': Number(selectedItemId) === Number(item.id),
                                                            'is-inactive': item.is_active === false
                                                        }
                                                    ]"
                                                    role="button"
                                                    tabindex="0"
                                                    @click="openItemDetail(item)"
                                                    @keydown.enter.prevent="openItemDetail(item)"
                                                    @keydown.space.prevent="openItemDetail(item)"
                                                >
                                                    <div class="inventory-catalog__item-main">
                                                        <span class="inventory-catalog__item-name">
                                                            <template v-for="(part, partIndex) in getHighlightedParts(item.name)" :key="`item:${item.id}:name:${partIndex}`">
                                                                <mark v-if="part.match" class="inventory-catalog__match">{{ part.text }}</mark>
                                                                <span v-else>{{ part.text }}</span>
                                                            </template>
                                                        </span>
                                                        <span
                                                            v-if="item.is_active === false"
                                                            class="inventory-catalog__item-status inventory-catalog__item-status--inactive"
                                                        >
                                                            Архив
                                                        </span>
                                                    </div>
                                                    <div class="inventory-catalog__item-actions">
                                                        <button
                                                            type="button"
                                                            class="inventory-catalog__icon-btn"
                                                            title="Информация"
                                                            aria-label="Информация"
                                                            @click.stop="openItemCard(item)"
                                                        >
                                                            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                                                <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.8" />
                                                                <path
                                                                    d="M12 10.25v5.25M12 7.75h.01"
                                                                    stroke="currentColor"
                                                                    stroke-width="1.8"
                                                                    stroke-linecap="round"
                                                                    stroke-linejoin="round"
                                                                />
                                                            </svg>
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </template>
                                </div>
                            </template>
                        </div>
                    </div>
                </div>

                <aside v-if="isDetailPaneVisible" class="inventory-catalog__detail-pane">
                    <div v-if="detailItem" class="inventory-catalog__detail-stack">
                        <div class="inventory-catalog__detail-shell inventory-catalog__detail-shell--head">
                            <div class="inventory-catalog__detail-head-layout">
                                <div
                                    v-if="detailItem.photo_url"
                                    class="inventory-catalog__detail-photo-tile"
                                >
                                    <img :src="detailItem.photo_url" :alt="detailItem.name || 'Фото товара'" />
                                </div>
                                <div v-else class="inventory-catalog__detail-photo-tile is-empty">
                                    <span class="inventory-catalog__detail-photo-empty">Нет фото</span>
                                </div>

                                <div class="inventory-catalog__detail-head-content">
                                    <h3 class="inventory-catalog__detail-title">{{ detailItem.name }}</h3>
                                    <p class="inventory-catalog__detail-path">{{ getCatalogPath(detailItem) }}</p>
                                    <p class="inventory-catalog__detail-note">{{ detailItem.note || 'Описание не заполнено' }}</p>
                                    <div class="inventory-catalog__detail-preview-meta">
                                        <span class="inventory-catalog__detail-preview-pill">{{ detailItem.code }}</span>
                                        <span class="inventory-catalog__detail-preview-pill">{{ formatMoney(detailItem.cost) }}</span>
                                        <span class="inventory-catalog__detail-preview-pill">{{ detailItem.total_quantity || 0 }} шт.</span>
                                        <span
                                            :class="[
                                                'inventory-catalog__detail-preview-pill',
                                                'inventory-catalog__status-pill',
                                                { 'is-inactive': detailItem.is_active === false }
                                            ]"
                                        >
                                            {{ detailItem.is_active === false ? 'Архив' : 'Активный' }}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="inventory-catalog__detail-shell inventory-catalog__detail-shell--specs">
                            <h4 class="inventory-catalog__detail-section-title">Дополнительно</h4>
                            <div class="inventory-catalog__detail-grid">
                                <div>
                                    <span class="inventory-catalog__detail-label">Производитель</span>
                                    <span class="inventory-catalog__detail-value">{{ detailItem.manufacturer || '—' }}</span>
                                </div>
                                <div>
                                    <span class="inventory-catalog__detail-label">Условия хранения</span>
                                    <span class="inventory-catalog__detail-value">{{ detailItem.storage_conditions || '—' }}</span>
                                </div>
                                <div>
                                    <span class="inventory-catalog__detail-label">Дата создания</span>
                                    <span class="inventory-catalog__detail-value">{{ formatItemCreatedAt(detailItem.created_at) }}</span>
                                </div>
                            </div>
                        </div>

                    </div>

                    <div v-else class="inventory-catalog__detail-placeholder">
                        Выберите товар в дереве слева, чтобы увидеть подробную карточку.
                    </div>
                </aside>
            </div>

            <div v-else class="inventory-page__empty">По текущему поиску товары не найдены.</div>
        </section>

        <Modal v-if="isItemModalOpen" @close="closeItemModal">
            <template #header>{{ isEditMode ? 'Изменить товар' : 'Новый товар' }}</template>
            <template #default>
                <div class="inventory-catalog__modal-form">
                    <Input v-model="itemForm.name" label="Название" />
                    <Input v-model="itemForm.note" label="Описание" placeholder="Описание товара" />
                    <Input v-model="itemForm.manufacturer" label="Производитель" placeholder="Например: Valio" />
                    <Input
                        v-model="itemForm.storageConditions"
                        label="Условия хранения"
                        placeholder="Температура, сроки, требования к хранению"
                    />
                    <label class="inventory-catalog__instance-toggle">
                        <input v-model="itemForm.useInstanceCodes" type="checkbox">
                        <span>Индивидуальные коды единиц (1, 2, 3...)</span>
                    </label>
                    <p class="inventory-catalog__instance-toggle-hint">
                        Для массовых товаров (например, тарелки) выключите переключатель, чтобы учитывать их только по общему коду.
                    </p>
                    <label class="inventory-catalog__instance-toggle">
                        <input v-model="itemForm.isActive" type="checkbox">
                        <span>Карточка активна</span>
                    </label>
                    <p class="inventory-catalog__instance-toggle-hint">
                        Неактивный товар переводится в архив, но сохраняется в истории и отчетах.
                    </p>

                    <div ref="catalogModalRef" class="inventory-catalog__picker">
                        <label class="inventory-catalog__picker-label">Группа / категория / вид</label>
                        <button
                            type="button"
                            class="inventory-catalog__picker-trigger"
                            @click="isCatalogModalOpen = !isCatalogModalOpen"
                        >
                            <span :class="{ 'is-placeholder': !itemForm.typeId }">{{ selectedTypeLabel }}</span>
                            <span>{{ isCatalogModalOpen ? '▲' : '▼' }}</span>
                        </button>

                        <div v-if="isCatalogModalOpen" class="inventory-catalog__picker-menu">
                            <template v-for="group in sortedGroups" :key="group.id">
                                <div class="inventory-catalog__picker-row inventory-catalog__picker-row--group">
                                    <button
                                        v-if="(categoriesByGroup.get(group.id) || []).length"
                                        type="button"
                                        class="inventory-catalog__picker-toggle"
                                        @click="toggleModalGroup(group.id)"
                                    >
                                        {{ isModalGroupExpanded(group.id) ? '⌄' : '›' }}
                                    </button>
                                    <span v-else class="inventory-catalog__picker-toggle inventory-catalog__picker-toggle--placeholder" />
                                    <span class="inventory-catalog__picker-node inventory-catalog__picker-node--static">{{ group.name }}</span>
                                </div>

                                <template v-if="isModalGroupExpanded(group.id)">
                                    <template v-for="category in categoriesByGroup.get(group.id) || []" :key="category.id">
                                        <div class="inventory-catalog__picker-row inventory-catalog__picker-row--category">
                                            <button
                                                v-if="(typesByCategory.get(category.id) || []).length"
                                                type="button"
                                                class="inventory-catalog__picker-toggle"
                                                @click="toggleModalCategory(category.id)"
                                            >
                                                {{ isModalCategoryExpanded(category.id) ? '⌄' : '›' }}
                                            </button>
                                            <span v-else class="inventory-catalog__picker-toggle inventory-catalog__picker-toggle--placeholder" />
                                            <span class="inventory-catalog__picker-node inventory-catalog__picker-node--static">{{ category.name }}</span>
                                        </div>

                                        <template v-if="isModalCategoryExpanded(category.id)">
                                            <div
                                                v-for="type in typesByCategory.get(category.id) || []"
                                                :key="type.id"
                                                class="inventory-catalog__picker-row inventory-catalog__picker-row--type"
                                            >
                                                <span class="inventory-catalog__picker-toggle inventory-catalog__picker-toggle--placeholder" />
                                                <button
                                                    type="button"
                                                    class="inventory-catalog__picker-node"
                                                    :class="{ 'is-selected': Number(itemForm.typeId) === Number(type.id) }"
                                                    @click="selectModalType(type.id)"
                                                >
                                                    {{ type.name }}
                                                </button>
                                            </div>
                                        </template>
                                    </template>
                                </template>
                            </template>
                        </div>
                    </div>
                    <Input v-model="itemForm.cost" label="Стоимость" type="number" step="0.01" min="0" />

                    <div class="inventory-catalog__photo-field">
                        <span class="inventory-catalog__photo-label">Фото</span>
                        <div class="inventory-catalog__photo-actions">
                            <button
                                type="button"
                                class="inventory-catalog__photo-button"
                                :disabled="uploadingPhoto || saving || !canSubmitItemModal"
                                @click="openPhotoPicker"
                            >
                                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                                    <path
                                        d="M4 8h3l1.2-2h7.6L17 8h3a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a1 1 0 0 1 1-1Z"
                                        stroke="currentColor"
                                        stroke-width="1.8"
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                    />
                                    <circle cx="12" cy="13.5" r="3.2" stroke="currentColor" stroke-width="1.8" />
                                </svg>
                                <span>{{ uploadingPhoto ? 'Загрузка...' : 'Загрузить фото' }}</span>
                            </button>
                            <input
                                ref="photoInputRef"
                                type="file"
                                accept="image/*"
                                class="inventory-catalog__photo-input"
                                @change="handleUploadItemPhoto"
                            />
                            <span v-if="itemForm.photoUrl" class="inventory-catalog__photo-added">Фото добавлено</span>
                            <Button
                                v-if="itemForm.photoUrl"
                                type="button"
                                color="ghost"
                                size="sm"
                                :disabled="uploadingPhoto || saving || !canSubmitItemModal"
                                @click="itemForm.photoUrl = ''"
                            >
                                Удалить фото
                            </Button>
                        </div>
                    </div>

                </div>
            </template>
            <template #footer>
                <Button color="ghost" :disabled="saving || uploadingPhoto" @click="closeItemModal">Отмена</Button>
                <Button v-if="canSubmitItemModal" color="primary" :loading="saving" @click="submitItem">Сохранить</Button>
            </template>
        </Modal>

        <Modal v-if="isItemCardOpen" class="inventory-catalog__card-modal-window" @close="closeItemCard">
            <template #header>
                <div class="inventory-catalog__card-header">
                    <button
                        type="button"
                        class="inventory-catalog__card-photo is-clickable"
                        :class="{ 'is-empty': !itemCardPhotoUrl }"
                        :aria-label="itemCardPhotoUrl ? 'Открыть фото товара' : 'Добавить фото товара'"
                        @click="openItemCardPhoto"
                    >
                        <img v-if="itemCardPhotoUrl" :src="itemCardPhotoUrl" :alt="itemCardItem?.name || 'Фото товара'" />
                        <span v-else>Нет фото</span>
                    </button>

                    <div class="inventory-catalog__card-heading">
                        <h3 class="inventory-catalog__card-title">{{ itemCardItem?.name || 'Карточка товара' }}</h3>
                        <p class="inventory-catalog__card-path">{{ itemCardItem ? getCatalogPath(itemCardItem) : '—' }}</p>
                        <p class="inventory-catalog__card-meta">
                            {{ itemCardItem?.code || `ITEM-${itemForm.id || '—'}` }} ·
                            {{ itemCardItem?.manufacturer || 'Производитель не указан' }} ·
                            {{ itemCardItem?.is_active === false ? 'Архив' : 'Активный' }}
                        </p>
                    </div>
                </div>

                <nav class="inventory-catalog__card-tabs" role="tablist" aria-label="Вкладки карточки товара">
                    <button
                        v-for="tab in ITEM_CARD_TABS"
                        :key="tab.value"
                        type="button"
                        class="inventory-catalog__card-tab"
                        :class="{ 'is-active': itemCardActiveTab === tab.value }"
                        :aria-pressed="itemCardActiveTab === tab.value"
                        @click="itemCardActiveTab = tab.value"
                    >
                        {{ tab.label }}
                    </button>
                </nav>
            </template>

            <template #default>
                <div v-if="itemCardActiveTab === 'info'" class="inventory-catalog__card-panel inventory-catalog__card-panel--info">
                    <div class="inventory-catalog__modal-form">
                        <Input v-model="itemForm.name" label="Название" :readonly="!canEditNomenclature" />
                        <Input
                            v-model="itemForm.note"
                            label="Описание"
                            placeholder="Описание товара"
                            :readonly="!canEditNomenclature"
                        />
                        <Input
                            v-model="itemForm.manufacturer"
                            label="Производитель"
                            placeholder="Например: Valio"
                            :readonly="!canEditNomenclature"
                        />
                        <Input
                            v-model="itemForm.storageConditions"
                            label="Условия хранения"
                            placeholder="Температура, сроки, требования к хранению"
                            :readonly="!canEditNomenclature"
                        />
                        <label class="inventory-catalog__instance-toggle">
                            <input v-model="itemForm.useInstanceCodes" type="checkbox" :disabled="!canEditNomenclature">
                            <span>Индивидуальные коды единиц (1, 2, 3...)</span>
                        </label>
                        <p class="inventory-catalog__instance-toggle-hint">
                            Включено: для каждой единицы создается свой код. Выключено: учет ведется только по общему коду товара.
                        </p>
                        <label class="inventory-catalog__instance-toggle">
                            <input v-model="itemForm.isActive" type="checkbox" :disabled="!canEditNomenclature">
                            <span>Карточка активна</span>
                        </label>
                        <p class="inventory-catalog__instance-toggle-hint">
                            Неактивный товар переводится в архив, но сохраняется в системе.
                        </p>

                        <div ref="catalogModalRef" class="inventory-catalog__picker">
                            <label class="inventory-catalog__picker-label">Группа / категория / вид</label>
                            <button
                                type="button"
                                class="inventory-catalog__picker-trigger"
                                :disabled="!canEditNomenclature"
                                @click="canEditNomenclature && (isCatalogModalOpen = !isCatalogModalOpen)"
                            >
                                <span :class="{ 'is-placeholder': !itemForm.typeId }">{{ selectedTypeLabel }}</span>
                                <span>{{ isCatalogModalOpen ? '▲' : '▼' }}</span>
                            </button>

                            <div v-if="isCatalogModalOpen" class="inventory-catalog__picker-menu">
                                <template v-for="group in sortedGroups" :key="group.id">
                                    <div class="inventory-catalog__picker-row inventory-catalog__picker-row--group">
                                        <button
                                            v-if="(categoriesByGroup.get(group.id) || []).length"
                                            type="button"
                                            class="inventory-catalog__picker-toggle"
                                            @click="toggleModalGroup(group.id)"
                                        >
                                            {{ isModalGroupExpanded(group.id) ? '⌄' : '›' }}
                                        </button>
                                        <span v-else class="inventory-catalog__picker-toggle inventory-catalog__picker-toggle--placeholder" />
                                        <span class="inventory-catalog__picker-node inventory-catalog__picker-node--static">{{ group.name }}</span>
                                    </div>

                                    <template v-if="isModalGroupExpanded(group.id)">
                                        <template v-for="category in categoriesByGroup.get(group.id) || []" :key="category.id">
                                            <div class="inventory-catalog__picker-row inventory-catalog__picker-row--category">
                                                <button
                                                    v-if="(typesByCategory.get(category.id) || []).length"
                                                    type="button"
                                                    class="inventory-catalog__picker-toggle"
                                                    @click="toggleModalCategory(category.id)"
                                                >
                                                    {{ isModalCategoryExpanded(category.id) ? '⌄' : '›' }}
                                                </button>
                                                <span v-else class="inventory-catalog__picker-toggle inventory-catalog__picker-toggle--placeholder" />
                                                <span class="inventory-catalog__picker-node inventory-catalog__picker-node--static">{{ category.name }}</span>
                                            </div>

                                            <template v-if="isModalCategoryExpanded(category.id)">
                                                <div
                                                    v-for="type in typesByCategory.get(category.id) || []"
                                                    :key="type.id"
                                                    class="inventory-catalog__picker-row inventory-catalog__picker-row--type"
                                                >
                                                    <span class="inventory-catalog__picker-toggle inventory-catalog__picker-toggle--placeholder" />
                                                    <button
                                                        type="button"
                                                        class="inventory-catalog__picker-node"
                                                        :class="{ 'is-selected': Number(itemForm.typeId) === Number(type.id) }"
                                                        @click="selectModalType(type.id)"
                                                    >
                                                        {{ type.name }}
                                                    </button>
                                                </div>
                                            </template>
                                        </template>
                                    </template>
                                </template>
                            </div>
                        </div>

                        <Input
                            v-model="itemForm.cost"
                            label="Стоимость"
                            type="number"
                            step="0.01"
                            min="0"
                            :readonly="!canEditNomenclature"
                        />
                        <div class="inventory-catalog__readonly-field">
                            <span class="inventory-catalog__picker-label">Дата создания</span>
                            <div class="inventory-catalog__readonly-value">
                                {{ formatItemCreatedAt(itemForm.createdAt) }}
                            </div>
                        </div>

                    </div>
                </div>

                <div v-else-if="itemCardActiveTab === 'changes'" class="inventory-catalog__card-panel">
                    <div class="inventory-catalog__card-panel-head">
                        <p class="inventory-catalog__card-panel-note">
                            Изменения цены, фото и параметров карточки товара.
                        </p>
                        <Button color="ghost" size="sm" :loading="itemCardChangesLoading" @click="reloadItemCardChanges">
                            Обновить
                        </Button>
                    </div>

                    <div v-if="itemCardChangesLoading" class="inventory-page__loading">Загрузка журнала...</div>
                    <p v-else-if="itemCardChangesError" class="inventory-page__empty">{{ itemCardChangesError }}</p>
                    <div v-else-if="itemCardChanges.length" class="inventory-catalog__card-table-wrap">
                        <Table>
                            <thead>
                                <tr>
                                    <th>Дата</th>
                                    <th>Поле</th>
                                    <th>Было</th>
                                    <th>Стало</th>
                                    <th>Ответственный</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="event in itemCardChanges" :key="event.id">
                                    <td>{{ formatItemCardChangeDate(event.created_at) }}</td>
                                    <td>{{ formatItemCardChangeField(event.field, event.action_type) }}</td>
                                    <td>{{ formatItemCardChangeValue(event.field, event.old_value) }}</td>
                                    <td>{{ formatItemCardChangeValue(event.field, event.new_value) }}</td>
                                    <td>{{ event.actor_name || 'Система' }}</td>
                                </tr>
                            </tbody>
                        </Table>
                    </div>
                    <p v-else class="inventory-page__empty">Для этого товара изменений пока нет.</p>
                </div>

                <div v-else class="inventory-catalog__card-panel">
                    <div class="inventory-catalog__card-stock-summary">
                        <div>
                            <span>Всего по компании</span>
                            <strong>{{ itemCardTotalQuantity }} шт.</strong>
                        </div>
                        <div>
                            <span>На складе</span>
                            <strong>{{ itemCardWarehouseQuantity }} шт.</strong>
                        </div>
                        <div>
                            <span>По ресторанам</span>
                            <strong>{{ itemCardRestaurantsQuantity }} шт.</strong>
                        </div>
                    </div>

                    <div v-if="itemCardRestaurantRows.length" class="inventory-catalog__card-table-wrap">
                        <Table>
                            <thead>
                                <tr>
                                    <th>Ресторан</th>
                                    <th>Количество</th>
                                    <th>Средняя себестоимость</th>
                                    <th>Последний приход</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="row in itemCardRestaurantRows" :key="row.restaurantId">
                                    <td>{{ row.restaurantName }}</td>
                                    <td>{{ row.quantity }} шт.</td>
                                    <td>{{ row.avgCost === null ? '—' : formatMoney(row.avgCost) }}</td>
                                    <td>{{ formatItemCreatedAt(row.lastArrivalAt) }}</td>
                                </tr>
                            </tbody>
                        </Table>
                    </div>
                    <p v-else class="inventory-page__empty">Рестораны пока не загружены или недоступны.</p>
                </div>
            </template>

            <template #footer>
                <div class="inventory-catalog__card-footer">
                    <Button color="ghost" :disabled="saving" @click="closeItemCard">Закрыть</Button>
                    <Button
                        v-if="itemCardActiveTab === 'info' && canEditNomenclature"
                        color="primary"
                        :loading="saving"
                        :disabled="uploadingPhoto"
                        @click="submitItemCardInfo"
                    >
                        Сохранить изменения
                    </Button>
                </div>
            </template>
        </Modal>

        <Modal v-if="previewPhotoItem" class="inventory-catalog__photo-modal-window" @close="closeItemPhoto">
            <div class="inventory-catalog__preview-modal">
                <div class="inventory-catalog__preview-media">
                    <img
                        v-if="previewPhotoUrl"
                        :src="previewPhotoUrl"
                        :alt="previewPhotoItem?.name || 'Фото товара'"
                        class="inventory-catalog__preview-image"
                    />
                    <p v-else class="inventory-catalog__preview-empty">Для этого товара фото не загружено.</p>
                </div>

                <div v-if="isPreviewPhotoEditable" class="inventory-catalog__preview-actions">
                    <Button color="ghost" :disabled="uploadingPhoto || saving" @click="openPreviewPhotoPicker">
                        {{ uploadingPhoto ? 'Загрузка...' : 'Заменить' }}
                    </Button>
                    <Button
                        color="danger"
                        :disabled="uploadingPhoto || saving || !canDeletePreviewPhoto"
                        @click="removePreviewPhoto"
                    >
                        Удалить
                    </Button>
                </div>
                <input
                    v-if="isPreviewPhotoEditable"
                    ref="previewPhotoInputRef"
                    type="file"
                    accept="image/*"
                    class="inventory-catalog__photo-input"
                    @change="handleReplacePreviewPhoto"
                />
            </div>
        </Modal>

    </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';
import {
    INVENTORY_NOMENCLATURE_CREATE_PERMISSIONS,
    INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS,
} from '@/accessPolicy';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Table from '@/components/UI-components/Table.vue';
import { useUserStore } from '@/stores/user';
import { formatDateTimeValue, formatNumberValue } from '@/utils/format';
import {
    createInventoryItem,
    fetchInventoryCategories,
    fetchInventoryGroups,
    fetchInventoryItems,
    fetchInventoryMovements,
    fetchRestaurants,
    fetchInventoryTypes,
    updateInventoryItem,
    uploadInventoryItemPhoto,
} from '@/api';

const TREE_STATE_STORAGE_KEY = 'zion.inventory.catalog.tree.v1';
const DETAIL_PANE_STORAGE_KEY = 'zion.inventory.catalog.detail-pane.v1';
const ITEM_CARD_TABS = [
    { value: 'info', label: 'Информация' },
    { value: 'changes', label: 'Журнал изменений' },
    { value: 'availability', label: 'Наличие по ресторанам' },
];
const ITEM_CARD_CHANGE_ACTIONS = ['item_created', 'item_updated', 'cost_changed'];
const ITEM_CARD_FIELD_LABELS = Object.freeze({
    code: 'Код',
    name: 'Название',
    group_id: 'Группа',
    category_id: 'Категория',
    kind_id: 'Вид',
    cost: 'Стоимость',
    default_cost: 'Себестоимость',
    photo_url: 'Фото',
    note: 'Описание',
    manufacturer: 'Производитель',
    storage_conditions: 'Условия хранения',
    use_instance_codes: 'Индивидуальные коды единиц',
    is_active: 'Статус карточки',
});

const toast = useToast();
const userStore = useUserStore();

const groups = ref([]);
const categories = ref([]);
const types = ref([]);
const restaurants = ref([]);
const items = ref([]);

const loading = ref(false);
const saving = ref(false);
const uploadingPhoto = ref(false);

const searchQuery = ref('');
const isFiltersOpen = ref(true);
const isDetailPaneVisible = ref(true);

const expandedGroupIds = ref(new Set());
const expandedCategoryIds = ref(new Set());
const expandedKindIds = ref(new Set());
const modalExpandedGroupIds = ref(new Set());
const modalExpandedCategoryIds = ref(new Set());

const isItemModalOpen = ref(false);
const isEditMode = ref(false);
const isCatalogModalOpen = ref(false);
const isItemCardOpen = ref(false);
const itemCardActiveTab = ref('info');
const itemCardChangesLoading = ref(false);
const itemCardChangesError = ref('');
const itemCardChanges = ref([]);
const itemForm = reactive({
    id: null,
    name: '',
    note: '',
    manufacturer: '',
    storageConditions: '',
    typeId: '',
    cost: '',
    photoUrl: '',
    useInstanceCodes: true,
    isActive: true,
    createdAt: '',
});

const previewPhotoItem = ref(null);
const selectedItemId = ref(null);
const photoInputRef = ref(null);
const previewPhotoInputRef = ref(null);
const catalogModalRef = ref(null);
const isPreviewPhotoEditable = ref(false);
const itemCardPhotoPreviewOverride = ref(null);

const groupMap = computed(() => {
    const map = new Map();
    groups.value.forEach((entry) => map.set(Number(entry.id), entry));
    return map;
});

const categoryMap = computed(() => {
    const map = new Map();
    categories.value.forEach((entry) => map.set(Number(entry.id), entry));
    return map;
});

const typeMap = computed(() => {
    const map = new Map();
    types.value.forEach((entry) => map.set(Number(entry.id), entry));
    return map;
});

const sortedGroups = computed(() =>
    [...groups.value].sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' })),
);

const sortedCategories = computed(() =>
    [...categories.value].sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' })),
);

const sortedTypes = computed(() =>
    [...types.value].sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' })),
);

const categoriesByGroup = computed(() => {
    const map = new Map();
    for (const category of sortedCategories.value) {
        const bucket = map.get(Number(category.group_id)) || [];
        bucket.push(category);
        map.set(Number(category.group_id), bucket);
    }
    return map;
});

const typesByCategory = computed(() => {
    const map = new Map();
    for (const type of sortedTypes.value) {
        const bucket = map.get(Number(type.category_id)) || [];
        bucket.push(type);
        map.set(Number(type.category_id), bucket);
    }
    return map;
});

const selectedTypeLabel = computed(() => {
    if (!itemForm.typeId) {
        return 'Выберите раздел';
    }
    return getCatalogPathByType(itemForm.typeId);
});

const itemCardItem = computed(() => {
    const id = Number(itemForm.id);
    if (!Number.isFinite(id) || id <= 0) {
        return null;
    }
    return items.value.find((item) => Number(item.id) === id) || null;
});

const itemCardPhotoUrl = computed(() => {
    if (itemCardPhotoPreviewOverride.value !== null) {
        return String(itemCardPhotoPreviewOverride.value || '');
    }
    return String(itemCardItem.value?.photo_url || '');
});

const previewPhotoUrl = computed(() => {
    if (!previewPhotoItem.value) {
        return '';
    }
    if (isPreviewPhotoEditable.value) {
        return itemCardPhotoUrl.value;
    }
    return String(previewPhotoItem.value.photo_url || '');
});

const canDeletePreviewPhoto = computed(() => Boolean(itemForm.photoUrl || previewPhotoUrl.value));
const canCreateNomenclature = computed(() => userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_CREATE_PERMISSIONS));
const canEditNomenclature = computed(() => userStore.hasAnyPermission(...INVENTORY_NOMENCLATURE_EDIT_PERMISSIONS));
const canSubmitItemModal = computed(() => (isEditMode.value ? canEditNomenclature.value : canCreateNomenclature.value));

const sortedRestaurants = computed(() =>
    [...restaurants.value].sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' })),
);

const itemCardRestaurantRows = computed(() => {
    const totals = Array.isArray(itemCardItem.value?.location_totals) ? itemCardItem.value.location_totals : [];
    const restaurantTotals = totals.filter((row) => row.location_kind === 'restaurant');
    const totalsByRestaurant = new Map(
        restaurantTotals
            .filter((row) => Number.isFinite(Number(row.restaurant_id)))
            .map((row) => [
                Number(row.restaurant_id),
                {
                    quantity: Number(row.quantity || 0),
                    avgCost: row.avg_cost === null || row.avg_cost === undefined ? null : Number(row.avg_cost),
                    locationName: row.location_name,
                    lastArrivalAt: row.last_arrival_at || null,
                },
            ]),
    );

    if (!sortedRestaurants.value.length) {
        return restaurantTotals
            .map((row) => ({
                restaurantId: Number(row.restaurant_id || 0),
                restaurantName: row.location_name || `Ресторан #${row.restaurant_id}`,
                quantity: Number(row.quantity || 0),
                avgCost: row.avg_cost === null || row.avg_cost === undefined ? null : Number(row.avg_cost),
                lastArrivalAt: row.last_arrival_at || null,
            }))
            .sort((a, b) => String(a.restaurantName || '').localeCompare(String(b.restaurantName || ''), 'ru', { sensitivity: 'base' }));
    }

    return sortedRestaurants.value.map((restaurant) => {
        const total = totalsByRestaurant.get(Number(restaurant.id));
        return {
            restaurantId: Number(restaurant.id),
            restaurantName: restaurant.name,
            quantity: Number(total?.quantity || 0),
            avgCost: total?.avgCost ?? null,
            lastArrivalAt: total?.lastArrivalAt ?? null,
        };
    });
});

const itemCardTotalQuantity = computed(() => Number(itemCardItem.value?.total_quantity || 0));
const itemCardWarehouseQuantity = computed(() => Number(itemCardItem.value?.warehouse_quantity || 0));
const itemCardRestaurantsQuantity = computed(() =>
    itemCardRestaurantRows.value.reduce((sum, row) => sum + Number(row.quantity || 0), 0),
);

const filteredItems = computed(() => {
    const needle = searchQuery.value.trim().toLowerCase();
    if (!needle) {
        return items.value;
    }
    return items.value.filter((item) => {
        const stack = [item.name, item.note, item.code, String(item.id)]
            .filter(Boolean)
            .join(' ')
            .toLowerCase();
        return stack.includes(needle);
    });
});

const detailItem = computed(() => {
    const id = Number(selectedItemId.value);
    if (!Number.isFinite(id)) {
        return null;
    }
    return items.value.find((item) => Number(item.id) === id) || null;
});

const groupedCatalog = computed(() => {
    const groupsMap = new Map();

    for (const item of filteredItems.value) {
        const groupId = Number(item.group_id || 0);
        const categoryId = Number(item.category_id || 0);
        const kindId = Number(item.kind_id || 0);

        let groupNode = groupsMap.get(groupId);
        if (!groupNode) {
            groupNode = {
                id: groupId,
                name: getCatalogGroupName(groupId),
                categoriesMap: new Map(),
                itemsCount: 0,
            };
            groupsMap.set(groupId, groupNode);
        }
        groupNode.itemsCount += 1;

        let categoryNode = groupNode.categoriesMap.get(categoryId);
        if (!categoryNode) {
            categoryNode = {
                id: categoryId,
                name: getCatalogCategoryName(categoryId),
                kindsMap: new Map(),
                itemsCount: 0,
            };
            groupNode.categoriesMap.set(categoryId, categoryNode);
        }
        categoryNode.itemsCount += 1;

        let kindNode = categoryNode.kindsMap.get(kindId);
        if (!kindNode) {
            kindNode = {
                id: kindId,
                name: getCatalogTypeName(kindId, item.kind_name),
                items: [],
            };
            categoryNode.kindsMap.set(kindId, kindNode);
        }
        kindNode.items.push(item);
    }

    return Array.from(groupsMap.values())
        .sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }))
        .map((groupNode) => ({
            id: groupNode.id,
            name: groupNode.name,
            itemsCount: groupNode.itemsCount,
            categories: Array.from(groupNode.categoriesMap.values())
                .sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }))
                .map((categoryNode) => ({
                    id: categoryNode.id,
                    name: categoryNode.name,
                    itemsCount: categoryNode.itemsCount,
                    kinds: Array.from(categoryNode.kindsMap.values())
                        .sort((a, b) => a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }))
                        .map((kindNode) => ({
                            id: kindNode.id,
                            name: kindNode.name,
                            items: [...kindNode.items].sort((a, b) =>
                                String(a.name || '').localeCompare(String(b.name || ''), 'ru', { sensitivity: 'base' }),
                            ),
                        })),
                })),
        }));
});

function getCatalogGroupName(groupId) {
    return groupMap.value.get(Number(groupId))?.name || `Группа #${groupId}`;
}

function getCatalogCategoryName(categoryId) {
    return categoryMap.value.get(Number(categoryId))?.name || `Категория #${categoryId}`;
}

function getCatalogTypeName(typeId, fallback = '') {
    return typeMap.value.get(Number(typeId))?.name || fallback || `Вид #${typeId}`;
}

function getCatalogPathByType(typeId) {
    const type = typeMap.value.get(Number(typeId));
    if (!type) {
        return '—';
    }
    const category = categoryMap.value.get(Number(type.category_id));
    const group = groupMap.value.get(Number(type.group_id));
    return [group?.name, category?.name, type.name].filter(Boolean).join(' > ');
}

function getCatalogPath(item) {
    if (item?.kind_id) {
        return getCatalogPathByType(item.kind_id);
    }
    const groupName = getCatalogGroupName(item?.group_id || 0);
    const categoryName = getCatalogCategoryName(item?.category_id || 0);
    return `${groupName} > ${categoryName}`;
}

function formatItemCardChangeDate(value) {
    return formatDateTimeValue(value, {
        emptyValue: '—',
        invalidValue: '—',
        locale: 'ru-RU',
        options: {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        },
    });
}

function formatItemCreatedAt(value) {
    return formatDateTimeValue(value, {
        emptyValue: '—',
        invalidValue: '—',
        locale: 'ru-RU',
        options: {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        },
    });
}

function formatItemCardChangeField(field, actionType) {
    if (actionType === 'item_created') {
        return 'Создание карточки';
    }
    return ITEM_CARD_FIELD_LABELS[field] || field || 'Поле';
}

function formatItemCardChangeValue(field, value) {
    if (value === null || value === undefined || value === '') {
        return '—';
    }
    if (field === 'cost' || field === 'default_cost') {
        return formatMoney(value);
    }
    if (field === 'photo_url') {
        return value ? 'Фото загружено' : 'Фото удалено';
    }
    if (field === 'use_instance_codes') {
        return ['true', '1', 'yes'].includes(String(value).toLowerCase()) ? 'Включено' : 'Выключено';
    }
    if (field === 'is_active') {
        return ['true', '1', 'yes'].includes(String(value).toLowerCase()) ? 'Активный' : 'Архив';
    }
    if (field === 'group_id') {
        return getCatalogGroupName(value);
    }
    if (field === 'category_id') {
        return getCatalogCategoryName(value);
    }
    if (field === 'kind_id') {
        return getCatalogPathByType(value);
    }
    return String(value);
}

function getHighlightedParts(value) {
    const source = String(value || '');
    const needle = searchQuery.value.trim();
    if (!needle || !source) {
        return [{ text: source, match: false }];
    }

    const sourceLower = source.toLowerCase();
    const needleLower = needle.toLowerCase();
    const parts = [];
    let cursor = 0;

    while (cursor < source.length) {
        const matchIndex = sourceLower.indexOf(needleLower, cursor);
        if (matchIndex === -1) {
            parts.push({ text: source.slice(cursor), match: false });
            break;
        }
        if (matchIndex > cursor) {
            parts.push({ text: source.slice(cursor, matchIndex), match: false });
        }
        parts.push({ text: source.slice(matchIndex, matchIndex + needle.length), match: true });
        cursor = matchIndex + needle.length;
    }

    return parts.length ? parts : [{ text: source, match: false }];
}

function isGroupExpanded(groupId) {
    return expandedGroupIds.value.has(Number(groupId));
}

function isCategoryExpanded(categoryId) {
    return expandedCategoryIds.value.has(Number(categoryId));
}

function isKindExpanded(kindId) {
    return expandedKindIds.value.has(Number(kindId));
}

function toggleFilters() {
    isFiltersOpen.value = !isFiltersOpen.value;
}

function toggleDetailPane() {
    isDetailPaneVisible.value = !isDetailPaneVisible.value;
}

function clearSearch() {
    searchQuery.value = '';
}

function toIdSet(values) {
    if (!Array.isArray(values)) {
        return new Set();
    }
    return new Set(
        values
            .map((value) => Number(value))
            .filter((value) => Number.isFinite(value)),
    );
}

function persistExpandedTree() {
    if (typeof window === 'undefined') {
        return;
    }
    const payload = {
        groups: Array.from(expandedGroupIds.value),
        categories: Array.from(expandedCategoryIds.value),
        kinds: Array.from(expandedKindIds.value),
    };
    window.localStorage.setItem(TREE_STATE_STORAGE_KEY, JSON.stringify(payload));
}

function restoreExpandedTree() {
    if (typeof window === 'undefined') {
        return;
    }
    const rawState = window.localStorage.getItem(TREE_STATE_STORAGE_KEY);
    if (!rawState) {
        return;
    }

    try {
        const parsed = JSON.parse(rawState);
        const knownGroups = new Set(groups.value.map((entry) => Number(entry.id)));
        const knownCategories = new Set(categories.value.map((entry) => Number(entry.id)));
        const knownKinds = new Set(types.value.map((entry) => Number(entry.id)));

        expandedGroupIds.value = new Set([...toIdSet(parsed?.groups)].filter((id) => knownGroups.has(id)));
        expandedCategoryIds.value = new Set([...toIdSet(parsed?.categories)].filter((id) => knownCategories.has(id)));
        expandedKindIds.value = new Set([...toIdSet(parsed?.kinds)].filter((id) => knownKinds.has(id)));
    } catch (error) {
        console.warn('Не удалось восстановить состояние дерева каталога', error);
    }
}

function restoreDetailPanePreference() {
    if (typeof window === 'undefined') {
        return;
    }
    const value = window.localStorage.getItem(DETAIL_PANE_STORAGE_KEY);
    if (value === null) {
        return;
    }
    isDetailPaneVisible.value = value !== '0';
}

function toggleSet(setRef, id, options = {}) {
    const { persist = false } = options;
    const next = new Set(setRef.value);
    if (next.has(Number(id))) {
        next.delete(Number(id));
    } else {
        next.add(Number(id));
    }
    setRef.value = next;
    if (persist) {
        persistExpandedTree();
    }
}

function toggleGroup(groupId) {
    toggleSet(expandedGroupIds, groupId, { persist: true });
}

function toggleCategory(categoryId) {
    toggleSet(expandedCategoryIds, categoryId, { persist: true });
}

function toggleKind(kindId) {
    toggleSet(expandedKindIds, kindId, { persist: true });
}

function seedExpandedTree(options = {}) {
    const { persist = false } = options;
    expandedGroupIds.value = new Set();
    expandedCategoryIds.value = new Set();
    expandedKindIds.value = new Set();
    if (persist) {
        persistExpandedTree();
    }
}

function expandAllVisible() {
    const groupIds = new Set();
    const categoryIds = new Set();
    const kindIds = new Set();

    groupedCatalog.value.forEach((groupNode) => {
        groupIds.add(Number(groupNode.id));
        groupNode.categories.forEach((categoryNode) => {
            categoryIds.add(Number(categoryNode.id));
            categoryNode.kinds.forEach((kindNode) => {
                kindIds.add(Number(kindNode.id));
            });
        });
    });

    expandedGroupIds.value = groupIds;
    expandedCategoryIds.value = categoryIds;
    expandedKindIds.value = kindIds;
    persistExpandedTree();
}

function collapseAll() {
    seedExpandedTree({ persist: true });
}

function expandPathForItem(item) {
    if (!item) {
        return;
    }
    const groupId = Number(item.group_id);
    const categoryId = Number(item.category_id);
    const kindId = Number(item.kind_id);

    if (Number.isFinite(groupId)) {
        expandedGroupIds.value = new Set([...expandedGroupIds.value, groupId]);
    }
    if (Number.isFinite(categoryId)) {
        expandedCategoryIds.value = new Set([...expandedCategoryIds.value, categoryId]);
    }
    if (Number.isFinite(kindId)) {
        expandedKindIds.value = new Set([...expandedKindIds.value, kindId]);
    }
    persistExpandedTree();
}

function ensureSelectedItem() {
    if (!filteredItems.value.length) {
        selectedItemId.value = null;
        return;
    }

    const exists = filteredItems.value.some((item) => Number(item.id) === Number(selectedItemId.value));
    if (exists) {
        return;
    }

    const fallback = filteredItems.value[0];
    selectedItemId.value = Number(fallback.id);
    expandPathForItem(fallback);
}

function isModalGroupExpanded(groupId) {
    return modalExpandedGroupIds.value.has(Number(groupId));
}

function isModalCategoryExpanded(categoryId) {
    return modalExpandedCategoryIds.value.has(Number(categoryId));
}

function toggleModalGroup(groupId) {
    toggleSet(modalExpandedGroupIds, groupId);
}

function toggleModalCategory(categoryId) {
    toggleSet(modalExpandedCategoryIds, categoryId);
}

function selectModalType(typeId) {
    itemForm.typeId = String(typeId);
    isCatalogModalOpen.value = false;
}

function seedModalPickerTree() {
    modalExpandedGroupIds.value = new Set();
    modalExpandedCategoryIds.value = new Set();
}

function onDocumentClick(event) {
    if (catalogModalRef.value && !catalogModalRef.value.contains(event.target)) {
        isCatalogModalOpen.value = false;
    }
}

async function loadLookupData() {
    const [groupData, categoryData, typeData, restaurantData] = await Promise.all([
        fetchInventoryGroups(),
        fetchInventoryCategories(),
        fetchInventoryTypes(),
        fetchRestaurants(),
    ]);
    groups.value = Array.isArray(groupData) ? groupData : [];
    categories.value = Array.isArray(categoryData) ? categoryData : [];
    types.value = Array.isArray(typeData) ? typeData : [];
    restaurants.value = Array.isArray(restaurantData) ? restaurantData : [];
    seedExpandedTree();
    restoreExpandedTree();
}

async function loadItems() {
    loading.value = true;
    try {
        const data = await fetchInventoryItems();
        items.value = Array.isArray(data) ? data : [];
        ensureSelectedItem();
    } catch (error) {
        toast.error('Не удалось загрузить каталог товаров');
        console.error(error);
    } finally {
        loading.value = false;
    }
}

function resetItemForm() {
    itemForm.id = null;
    itemForm.name = '';
    itemForm.note = '';
    itemForm.manufacturer = '';
    itemForm.storageConditions = '';
    itemForm.typeId = '';
    itemForm.cost = '';
    itemForm.photoUrl = '';
    itemForm.useInstanceCodes = true;
    itemForm.isActive = true;
    itemForm.createdAt = '';
    itemCardPhotoPreviewOverride.value = null;
}

function openCreateModal() {
    if (!canCreateNomenclature.value) {
        toast.error('Недостаточно прав для создания товара');
        return;
    }
    resetItemForm();
    isEditMode.value = false;
    isItemModalOpen.value = true;
    isCatalogModalOpen.value = false;
    seedModalPickerTree();
}

function setItemFormFromItem(item) {
    if (!item) {
        resetItemForm();
        return;
    }
    itemForm.id = item.id;
    itemForm.name = item.name || '';
    itemForm.note = item.note || '';
    itemForm.manufacturer = item.manufacturer || '';
    itemForm.storageConditions = item.storage_conditions || '';
    itemForm.typeId = item.kind_id ? String(item.kind_id) : '';
    itemForm.cost = item.cost !== null && item.cost !== undefined ? String(item.cost) : '';
    itemForm.photoUrl = item.photo_key || item.photo_url || '';
    itemForm.useInstanceCodes = item.use_instance_codes !== false;
    itemForm.isActive = item.is_active !== false;
    itemForm.createdAt = item.created_at || '';
    itemCardPhotoPreviewOverride.value = null;
}

function openItemCard(item) {
    if (!item) {
        return;
    }
    openItemDetail(item);
    setItemFormFromItem(item);
    itemCardActiveTab.value = 'info';
    isItemCardOpen.value = true;
    isItemModalOpen.value = false;
    isCatalogModalOpen.value = false;
    itemCardChangesError.value = '';
    itemCardChanges.value = [];
    seedModalPickerTree();
    void loadItemCardChanges(item.id);
}

function closeItemCard() {
    isItemCardOpen.value = false;
    itemCardActiveTab.value = 'info';
    itemCardChangesError.value = '';
    itemCardChanges.value = [];
    isCatalogModalOpen.value = false;
    isPreviewPhotoEditable.value = false;
    itemCardPhotoPreviewOverride.value = null;
    resetItemForm();
}

async function loadItemCardChanges(itemId) {
    const normalizedItemId = Number(itemId);
    if (!Number.isFinite(normalizedItemId) || normalizedItemId <= 0) {
        itemCardChanges.value = [];
        return;
    }
    itemCardChangesLoading.value = true;
    itemCardChangesError.value = '';
    try {
        const data = await fetchInventoryMovements({
            limit: 200,
            item_ids: [normalizedItemId],
            action_types: ITEM_CARD_CHANGE_ACTIONS,
        });
        const rows = Array.isArray(data) ? data : [];
        itemCardChanges.value = rows
            .filter((row) => Number(row.item_id) === normalizedItemId)
            .sort((a, b) => new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime());
    } catch (error) {
        itemCardChanges.value = [];
        itemCardChangesError.value = 'Не удалось загрузить журнал изменений';
        console.error(error);
    } finally {
        itemCardChangesLoading.value = false;
    }
}

async function reloadItemCardChanges() {
    await loadItemCardChanges(itemForm.id);
}

function closeItemModal() {
    isItemModalOpen.value = false;
    isCatalogModalOpen.value = false;
    isEditMode.value = false;
    resetItemForm();
}

function openItemDetail(item) {
    selectedItemId.value = Number(item.id);
    expandPathForItem(item);
}

function openItemCardPhoto() {
    if (!isItemCardOpen.value) {
        return;
    }
    const fallbackItem = itemCardItem.value || {
        id: itemForm.id,
        name: itemForm.name,
        photo_url: '',
    };
    openItemPhoto(fallbackItem, { editable: canEditNomenclature.value });
}

function openItemPhoto(item, options = {}) {
    if (!item) {
        return;
    }
    previewPhotoItem.value = item;
    isPreviewPhotoEditable.value = Boolean(options.editable);
}

function closeItemPhoto() {
    previewPhotoItem.value = null;
    isPreviewPhotoEditable.value = false;
}

function openPreviewPhotoPicker() {
    if (!isPreviewPhotoEditable.value || uploadingPhoto.value || saving.value || !previewPhotoInputRef.value) {
        return;
    }
    previewPhotoInputRef.value.click();
}

function removePreviewPhoto() {
    if (!isPreviewPhotoEditable.value || !canEditNomenclature.value || uploadingPhoto.value || saving.value) {
        return;
    }
    itemForm.photoUrl = '';
    itemCardPhotoPreviewOverride.value = '';
    toast.success('Фото будет удалено после сохранения карточки');
}

async function handleReplacePreviewPhoto(event) {
    const file = event?.target?.files?.[0];
    if (!file || !isPreviewPhotoEditable.value || !canEditNomenclature.value) {
        return;
    }
    uploadingPhoto.value = true;
    try {
        const response = await uploadInventoryItemPhoto(file);
        itemForm.photoUrl = response?.attachment_key || response?.attachment_url || '';
        if (response?.attachment_url) {
            itemCardPhotoPreviewOverride.value = response.attachment_url;
        }
        toast.success('Фото заменено. Нажмите «Сохранить изменения»');
    } catch (error) {
        toast.error('Не удалось загрузить фото');
        console.error(error);
    } finally {
        uploadingPhoto.value = false;
        if (event?.target) {
            event.target.value = '';
        }
    }
}

function openPhotoPicker() {
    if (!photoInputRef.value || uploadingPhoto.value || !canSubmitItemModal.value) {
        return;
    }
    photoInputRef.value.click();
}

async function handleUploadItemPhoto(event) {
    const file = event?.target?.files?.[0];
    if (!file || !canSubmitItemModal.value) {
        return;
    }
    uploadingPhoto.value = true;
    try {
        const response = await uploadInventoryItemPhoto(file);
        itemForm.photoUrl = response?.attachment_key || response?.attachment_url || '';
        toast.success('Фото загружено');
    } catch (error) {
        toast.error('Не удалось загрузить фото');
        console.error(error);
    } finally {
        uploadingPhoto.value = false;
        if (event?.target) {
            event.target.value = '';
        }
    }
}

function parseNumber(value) {
    const number = Number.parseFloat(String(value).replace(',', '.'));
    return Number.isFinite(number) ? number : NaN;
}

async function submitItem() {
    if (!canSubmitItemModal.value) {
        toast.error(isEditMode.value ? 'Недостаточно прав для редактирования товара' : 'Недостаточно прав для создания товара');
        return;
    }
    const name = itemForm.name.trim();
    if (!name) {
        toast.error('Введите название товара');
        return;
    }

    const type = typeMap.value.get(Number(itemForm.typeId));
    if (!type) {
        toast.error('Выберите вид товара');
        return;
    }

    const cost = parseNumber(itemForm.cost);
    if (Number.isNaN(cost)) {
        toast.error('Стоимость должна быть числом');
        return;
    }

    saving.value = true;
    try {
        const updatePhotoValue = resolveItemPhotoUpdateValue(itemForm.id);
        if (isEditMode.value && itemForm.id) {
            await updateInventoryItem(itemForm.id, {
                name,
                group_id: type.group_id,
                category_id: type.category_id,
                kind_id: type.id,
                cost,
                note: itemForm.note || undefined,
                manufacturer: itemForm.manufacturer || undefined,
                storage_conditions: itemForm.storageConditions || undefined,
                photo_url: updatePhotoValue,
                use_instance_codes: Boolean(itemForm.useInstanceCodes),
                is_active: Boolean(itemForm.isActive),
            });
            toast.success('Товар обновлен');
        } else {
            const createPayload = {
                name,
                group_id: type.group_id,
                category_id: type.category_id,
                kind_id: type.id,
                cost,
                note: itemForm.note || undefined,
                manufacturer: itemForm.manufacturer || undefined,
                storage_conditions: itemForm.storageConditions || undefined,
                photo_url: itemForm.photoUrl || null,
                use_instance_codes: Boolean(itemForm.useInstanceCodes),
                is_active: Boolean(itemForm.isActive),
                initial_quantity: 0,
            };

            await createInventoryItem(createPayload);
            toast.success('Товар создан');
        }

        closeItemModal();
        await loadItems();
    } catch (error) {
        toast.error('Не удалось сохранить товар');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

async function submitItemCardInfo() {
    if (!canEditNomenclature.value) {
        toast.error('Недостаточно прав для редактирования товара');
        return;
    }
    const itemId = Number(itemForm.id);
    if (!Number.isFinite(itemId) || itemId <= 0) {
        toast.error('Товар не выбран');
        return;
    }

    const name = itemForm.name.trim();
    if (!name) {
        toast.error('Введите название товара');
        return;
    }

    const type = typeMap.value.get(Number(itemForm.typeId));
    if (!type) {
        toast.error('Выберите вид товара');
        return;
    }

    const cost = parseNumber(itemForm.cost);
    if (Number.isNaN(cost)) {
        toast.error('Стоимость должна быть числом');
        return;
    }

    saving.value = true;
    try {
        const updatePhotoValue = resolveItemPhotoUpdateValue(itemId);
        await updateInventoryItem(itemId, {
            name,
            group_id: type.group_id,
            category_id: type.category_id,
            kind_id: type.id,
            cost,
            note: itemForm.note || undefined,
            manufacturer: itemForm.manufacturer || undefined,
            storage_conditions: itemForm.storageConditions || undefined,
            photo_url: updatePhotoValue,
            use_instance_codes: Boolean(itemForm.useInstanceCodes),
            is_active: Boolean(itemForm.isActive),
        });
        toast.success('Карточка товара обновлена');
        await loadItems();
        const refreshed = items.value.find((entry) => Number(entry.id) === itemId) || null;
        if (!refreshed) {
            closeItemCard();
            return;
        }
        openItemDetail(refreshed);
        setItemFormFromItem(refreshed);
        await loadItemCardChanges(itemId);
    } catch (error) {
        toast.error('Не удалось обновить карточку товара');
        console.error(error);
    } finally {
        saving.value = false;
    }
}

function formatMoney(value) {
    const amount = Number(value || 0);
    return formatNumberValue(amount, {
        emptyValue: '0.00',
        invalidValue: 'NaN',
        locale: 'ru-RU',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
}

function resolveItemPhotoUpdateValue(itemId) {
    const normalizedItemId = Number(itemId);
    const currentItem = items.value.find((entry) => Number(entry.id) === normalizedItemId) || null;
    const currentPhoto = String(currentItem?.photo_key || currentItem?.photo_url || '').trim();
    const draftPhoto = String(itemForm.photoUrl || '').trim();

    if (!draftPhoto && !currentPhoto) {
        return undefined;
    }
    return draftPhoto || '';
}

watch(filteredItems, () => {
    ensureSelectedItem();
});

watch(isDetailPaneVisible, (value) => {
    if (typeof window === 'undefined') {
        return;
    }
    window.localStorage.setItem(DETAIL_PANE_STORAGE_KEY, value ? '1' : '0');
});

onMounted(async () => {
    document.addEventListener('click', onDocumentClick);
    try {
        restoreDetailPanePreference();
        await loadLookupData();
        await loadItems();
    } catch (error) {
        toast.error('Не удалось загрузить каталог');
        console.error(error);
    }
});

onBeforeUnmount(() => {
    document.removeEventListener('click', onDocumentClick);
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-catalog' as *;
</style>
