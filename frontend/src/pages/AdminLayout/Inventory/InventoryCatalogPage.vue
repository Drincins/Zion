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
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Table from '@/components/UI-components/Table.vue';
import { useInventoryCatalogPage } from './composables/useInventoryCatalogPage';

const {
    ITEM_CARD_TABS,
    loading,
    saving,
    uploadingPhoto,
    searchQuery,
    isFiltersOpen,
    isDetailPaneVisible,
    isItemModalOpen,
    isEditMode,
    isCatalogModalOpen,
    isItemCardOpen,
    itemCardActiveTab,
    itemCardChangesLoading,
    itemCardChangesError,
    itemCardChanges,
    itemForm,
    previewPhotoItem,
    selectedItemId,
    photoInputRef,
    previewPhotoInputRef,
    catalogModalRef,
    isPreviewPhotoEditable,
    selectedTypeLabel,
    itemCardItem,
    itemCardPhotoUrl,
    previewPhotoUrl,
    canDeletePreviewPhoto,
    canCreateNomenclature,
    canEditNomenclature,
    canSubmitItemModal,
    itemCardRestaurantRows,
    itemCardTotalQuantity,
    itemCardWarehouseQuantity,
    itemCardRestaurantsQuantity,
    filteredItems,
    detailItem,
    groupedCatalog,
    getCatalogPath,
    formatItemCardChangeDate,
    formatItemCreatedAt,
    formatItemCardChangeField,
    formatItemCardChangeValue,
    getHighlightedParts,
    isGroupExpanded,
    isCategoryExpanded,
    isKindExpanded,
    toggleFilters,
    toggleDetailPane,
    clearSearch,
    toggleGroup,
    toggleCategory,
    toggleKind,
    expandAllVisible,
    collapseAll,
    isModalGroupExpanded,
    isModalCategoryExpanded,
    toggleModalGroup,
    toggleModalCategory,
    selectModalType,
    loadItems,
    openCreateModal,
    openItemCard,
    closeItemCard,
    reloadItemCardChanges,
    closeItemModal,
    openItemDetail,
    openItemCardPhoto,
    closeItemPhoto,
    openPreviewPhotoPicker,
    removePreviewPhoto,
    handleReplacePreviewPhoto,
    openPhotoPicker,
    handleUploadItemPhoto,
    submitItem,
    submitItemCardInfo,
    formatMoney,
    sortedGroups,
    categoriesByGroup,
    typesByCategory,
} = useInventoryCatalogPage();
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-catalog' as *;
</style>
