<template>
    <div class="inventory-balance">
        <header class="inventory-balance__header">
            <div class="inventory-balance__header-main">
                <h1 class="inventory-balance__title">Баланс ресторана</h1>
                <p class="inventory-balance__subtitle">
                    Остатки, операции и карточки товара в выбранном ресторане и месте хранения.
                </p>
            </div>
            <div class="inventory-balance__header-actions">
                <router-link :to="{ name: 'inventory-journal' }" class="inventory-balance__journal-link">
                    Журнал операций
                </router-link>
                <Button color="secondary" size="sm" :loading="loading" :disabled="!selectedRestaurantId" @click="loadRestaurantItems">
                    Обновить
                </Button>
                <Button
                    v-if="canCreateMovement"
                    color="primary"
                    size="sm"
                    :disabled="!selectedRestaurantId"
                    @click="openOperationModal"
                >
                    Операция
                </Button>
            </div>
        </header>

        <section class="inventory-balance__filters-panel">
            <div class="inventory-balance__filters-row">
                <Select
                    v-model="selectedRestaurantId"
                    label="Ресторан"
                    :options="restaurantOptions"
                    placeholder="Выберите ресторан"
                    searchable
                    class="inventory-balance__restaurant-select"
                />
                <Select
                    v-model="selectedStoragePlaceId"
                    label="Место хранения"
                    :options="storagePlaceFilterOptions"
                    placeholder="Все места хранения"
                    :disabled="!selectedRestaurantId"
                    searchable
                    class="inventory-balance__storage-place-select"
                />
                <Input
                    v-model="searchQuery"
                    label=""
                    class="inventory-balance__search"
                    placeholder="Поиск по названию, описанию, коду"
                    :disabled="!selectedRestaurantId"
                />
                <p class="inventory-balance__summary">
                    {{ selectedStoragePlaceLabel }} · Найдено: <strong>{{ groupedItemsCount }}</strong>
                </p>
            </div>
        </section>

        <section class="inventory-balance__tree-card">
            <div v-if="!selectedRestaurantId" class="inventory-page__empty">
                Выберите ресторан, чтобы посмотреть баланс.
            </div>

            <div v-else-if="loading" class="inventory-page__loading">Загрузка баланса ресторана...</div>

            <div
                v-else-if="groupedCatalog.length"
                :class="['inventory-balance__workspace', { 'is-detail-hidden': !isDetailPaneVisible }]"
            >
                <div class="inventory-balance__tree-pane">
                    <div class="inventory-balance__tree-toolbar">
                        <Button color="ghost" size="sm" @click="expandAllVisible">Развернуть всё</Button>
                        <Button color="ghost" size="sm" @click="collapseAll">Свернуть всё</Button>
                        <Button color="ghost" size="sm" @click="toggleDetailPane">
                            {{ isDetailPaneVisible ? 'Скрыть карточку' : 'Показать карточку' }}
                        </Button>
                    </div>

                    <div class="inventory-balance__tree">
                        <div
                            v-for="groupNode in groupedCatalog"
                            :key="`g:${groupNode.id}`"
                            class="inventory-balance__group"
                        >
                            <button
                                type="button"
                                class="inventory-balance__line inventory-balance__line--group"
                                @click="toggleGroup(groupNode.id)"
                            >
                                <span class="inventory-balance__arrow">{{ isGroupExpanded(groupNode.id) ? '⌄' : '›' }}</span>
                                <span class="inventory-balance__line-title">
                                    <template v-for="(part, partIndex) in getHighlightedParts(groupNode.name)" :key="`group:${groupNode.id}:${partIndex}`">
                                        <mark v-if="part.match" class="inventory-balance__match">{{ part.text }}</mark>
                                        <span v-else>{{ part.text }}</span>
                                    </template>
                                </span>
                                <span class="inventory-balance__line-count">{{ groupNode.itemsCount }} товаров</span>
                            </button>

                            <template v-if="isGroupExpanded(groupNode.id)">
                                <div
                                    v-for="categoryNode in groupNode.categories"
                                    :key="`c:${categoryNode.id}`"
                                    class="inventory-balance__category"
                                >
                                    <button
                                        type="button"
                                        class="inventory-balance__line inventory-balance__line--category"
                                        @click="toggleCategory(categoryNode.id)"
                                    >
                                        <span class="inventory-balance__arrow">{{ isCategoryExpanded(categoryNode.id) ? '⌄' : '›' }}</span>
                                        <span class="inventory-balance__line-title">
                                            <template v-for="(part, partIndex) in getHighlightedParts(categoryNode.name)" :key="`category:${categoryNode.id}:${partIndex}`">
                                                <mark v-if="part.match" class="inventory-balance__match">{{ part.text }}</mark>
                                                <span v-else>{{ part.text }}</span>
                                            </template>
                                        </span>
                                        <span class="inventory-balance__line-count">{{ categoryNode.itemsCount }} товаров</span>
                                    </button>

                                    <template v-if="isCategoryExpanded(categoryNode.id)">
                                        <div
                                            v-for="kindNode in categoryNode.kinds"
                                            :key="`t:${kindNode.id}`"
                                            class="inventory-balance__kind"
                                        >
                                            <button
                                                type="button"
                                                class="inventory-balance__line inventory-balance__line--kind"
                                                @click="toggleKind(kindNode.id)"
                                            >
                                                <span class="inventory-balance__arrow">{{ isKindExpanded(kindNode.id) ? '⌄' : '›' }}</span>
                                                <span class="inventory-balance__line-title">
                                                    <template v-for="(part, partIndex) in getHighlightedParts(kindNode.name)" :key="`kind:${kindNode.id}:${partIndex}`">
                                                        <mark v-if="part.match" class="inventory-balance__match">{{ part.text }}</mark>
                                                        <span v-else>{{ part.text }}</span>
                                                    </template>
                                                </span>
                                                <span class="inventory-balance__line-count">{{ kindNode.items.length }} товаров</span>
                                            </button>

                                            <div v-if="isKindExpanded(kindNode.id)" class="inventory-balance__items">
                                                <div
                                                    v-for="entry in kindNode.items"
                                                    :key="entry.item.id"
                                                    :class="[
                                                        'inventory-balance__item-row',
                                                        {
                                                            'is-selected': Number(selectedItemId) === Number(entry.item.id),
                                                            'is-inactive': entry.item.is_active === false
                                                        }
                                                    ]"
                                                    role="button"
                                                    tabindex="0"
                                                    @click="openItemDetail(entry.item)"
                                                    @keydown.enter.prevent="openItemDetail(entry.item)"
                                                    @keydown.space.prevent="openItemDetail(entry.item)"
                                                >
                                                    <div class="inventory-balance__item-main">
                                                        <span class="inventory-balance__item-name">
                                                            <template v-for="(part, partIndex) in getHighlightedParts(entry.item.name)" :key="`item:${entry.item.id}:name:${partIndex}`">
                                                                <mark v-if="part.match" class="inventory-balance__match">{{ part.text }}</mark>
                                                                <span v-else>{{ part.text }}</span>
                                                            </template>
                                                        </span>
                                                        <span
                                                            v-if="entry.item.is_active === false"
                                                            class="inventory-balance__item-status inventory-balance__item-status--inactive"
                                                        >
                                                            Архив
                                                        </span>
                                                    </div>

                                                    <span class="inventory-balance__item-qty">{{ entry.quantity }} шт.</span>
                                                    <button
                                                        type="button"
                                                        class="inventory-balance__icon-btn"
                                                        title="Информация"
                                                        aria-label="Информация"
                                                        @click.stop="openItemCard(entry.item)"
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
                                    </template>
                                </div>
                            </template>
                        </div>
                    </div>
                </div>

                <aside v-if="isDetailPaneVisible" class="inventory-balance__detail-pane">
                    <div v-if="detailEntry" class="inventory-balance__detail-stack">
                        <div class="inventory-balance__detail-shell inventory-balance__detail-shell--head">
                            <div class="inventory-balance__detail-head-layout">
                                <div
                                    v-if="detailEntry.item.photo_url"
                                    class="inventory-balance__detail-photo-tile"
                                >
                                    <img :src="detailEntry.item.photo_url" :alt="detailEntry.item.name || 'Фото товара'" />
                                </div>
                                <div v-else class="inventory-balance__detail-photo-tile is-empty">
                                    <span class="inventory-balance__detail-photo-empty">Нет фото</span>
                                </div>

                                <div class="inventory-balance__detail-head-content">
                                    <h3 class="inventory-balance__detail-title">{{ detailEntry.item.name }}</h3>
                                    <p class="inventory-balance__detail-path">
                                        {{ getCatalogPath(detailEntry.item) }} · {{ selectedStoragePlaceLabel }}
                                    </p>
                                    <p class="inventory-balance__detail-note">{{ detailEntry.item.note || 'Описание не заполнено' }}</p>
                                    <div class="inventory-balance__detail-preview-meta">
                                        <span class="inventory-balance__detail-preview-pill">{{ detailEntry.item.code }}</span>
                                        <span class="inventory-balance__detail-preview-pill">{{ detailEntry.quantity }} шт.</span>
                                        <span class="inventory-balance__detail-preview-pill">{{ formatMoney(detailEntry.avgCost ?? detailEntry.item.cost) }}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div v-else class="inventory-balance__detail-placeholder">
                        Выберите товар в дереве слева, чтобы открыть карточку.
                    </div>
                </aside>
            </div>

            <div v-else class="inventory-page__empty">По выбранному ресторану товаров не найдено.</div>
        </section>

        <Modal
            v-if="isItemCardModalOpen && detailEntry"
            class="inventory-balance__card-modal-window"
            @close="closeItemCard"
        >
            <template #header>
                <div class="inventory-balance__card-modal-head">
                    <div class="inventory-balance__card-modal-heading">
                        <h3>{{ detailEntry.item.name }}</h3>
                        <p>{{ selectedRestaurantName }} · {{ selectedStoragePlaceLabel }} · {{ getCatalogPath(detailEntry.item) }}</p>
                    </div>
                    <div class="inventory-balance__card-modal-metrics">
                        <span>В ресторане: <strong>{{ detailEntry.quantity }} шт.</strong></span>
                        <span>Средняя себестоимость: <strong>{{ formatMoney(detailEntry.avgCost ?? detailEntry.item.cost) }}</strong></span>
                    </div>
                </div>
            </template>

            <template #default>
                <div class="inventory-balance__card-modal-body">
                    <div class="inventory-balance__detail-tabs">
                        <button
                            type="button"
                            :class="['inventory-balance__detail-tab', { 'is-active': detailTab === 'arrivals' }]"
                            @click="detailTab = 'arrivals'"
                        >
                            История прихода
                        </button>
                        <button
                            type="button"
                            :class="['inventory-balance__detail-tab', { 'is-active': detailTab === 'instances' }]"
                            :disabled="!instanceTrackingEnabled"
                            @click="detailTab = 'instances'"
                        >
                            Единицы и коды
                        </button>
                    </div>

                    <div v-if="detailCardLoading" class="inventory-balance__detail-loading">
                        Загружаем карточку товара в ресторане...
                    </div>

                    <template v-else-if="detailTab === 'arrivals'">
                        <div class="inventory-balance__modal-section-head">
                            <div class="inventory-balance__modal-section-copy">
                                <h4>История прихода</h4>
                                <p>Последние поступления товара в выбранный ресторан и место хранения.</p>
                            </div>
                            <span class="inventory-balance__modal-section-pill">{{ detailArrivals.length }}</span>
                        </div>
                        <div v-if="detailArrivals.length" class="inventory-balance__history-list">
                            <article
                                v-for="event in detailArrivals"
                                :key="event.id"
                                class="inventory-balance__history-card"
                            >
                                <div class="inventory-balance__history-head">
                                    <span class="inventory-balance__history-badge">{{ event.action_label }}</span>
                                    <span class="inventory-balance__history-date">{{ formatDateTime(event.created_at) }}</span>
                                </div>
                                <div class="inventory-balance__history-grid">
                                    <div>
                                        <span class="inventory-balance__detail-label">Количество</span>
                                        <strong class="inventory-balance__history-value">{{ event.quantity }} шт.</strong>
                                    </div>
                                    <div>
                                        <span class="inventory-balance__detail-label">Откуда</span>
                                        <strong class="inventory-balance__history-value">{{ event.source_location_name || '—' }}</strong>
                                    </div>
                                    <div>
                                        <span class="inventory-balance__detail-label">Куда</span>
                                        <strong class="inventory-balance__history-value">{{ event.target_location_name || selectedRestaurantName }}</strong>
                                    </div>
                                    <div>
                                        <span class="inventory-balance__detail-label">Кто провёл</span>
                                        <strong class="inventory-balance__history-value">{{ event.actor_name || 'Система' }}</strong>
                                    </div>
                                </div>
                                <p v-if="event.comment" class="inventory-balance__history-note">{{ event.comment }}</p>
                            </article>
                        </div>
                        <div v-else class="inventory-balance__detail-placeholder inventory-balance__detail-placeholder--inner">
                            Для этого товара в выбранном ресторане история прихода пока не найдена.
                        </div>
                    </template>

                    <template v-else>
                        <div
                            v-if="instanceTrackingEnabled"
                            class="inventory-balance__instances-shell"
                        >
                            <div class="inventory-balance__modal-section-head">
                                <div class="inventory-balance__modal-section-copy">
                                    <h4>Единицы и коды</h4>
                                    <p>
                                        Активных: {{ currentInstanceCount }} · Исторических: {{ historicalInstanceCount }}
                                    </p>
                                </div>
                                <span class="inventory-balance__modal-section-pill">{{ instanceSummaries.length }}</span>
                            </div>
                            <div class="inventory-balance__instances-layout">
                            <div class="inventory-balance__instances-list">
                                <button
                                    v-for="instance in instanceSummaries"
                                    :key="instance.instance_code"
                                    type="button"
                                    :class="[
                                        'inventory-balance__instance-item',
                                        {
                                            'is-active': instance.instance_code === selectedInstanceCode,
                                            'is-current': instance.is_current
                                        }
                                    ]"
                                    @click="selectInstance(instance.instance_code)"
                                >
                                    <div class="inventory-balance__instance-item-head">
                                        <strong>{{ instance.instance_code }}</strong>
                                        <span
                                            :class="[
                                                'inventory-balance__instance-state',
                                                `is-${instance.status_key}`
                                            ]"
                                        >
                                            {{ instance.status_label }}
                                        </span>
                                    </div>
                                    <span class="inventory-balance__instance-meta">
                                        Последнее: {{ instance.last_event_label || 'Поступление' }}
                                    </span>
                                    <span class="inventory-balance__instance-meta">
                                        {{ formatDateTime(instance.last_event_at || instance.arrived_at) }}
                                    </span>
                                </button>
                            </div>

                            <div class="inventory-balance__instance-panel">
                                <div v-if="selectedInstanceSummary" class="inventory-balance__instance-panel-head">
                                    <div class="inventory-balance__instance-panel-title">
                                        <h4>{{ selectedInstanceSummary.instance_code }}</h4>
                                        <p>
                                            {{ selectedInstanceSummary.current_location_name || selectedRestaurantName }} ·
                                            {{ selectedInstanceSummary.status_label }}
                                        </p>
                                        <div class="inventory-balance__instance-panel-meta">
                                            <span>Событий: {{ instanceEvents.length }}</span>
                                            <span>Последнее: {{ selectedInstanceSummary.last_event_label || 'Поступление' }}</span>
                                        </div>
                                    </div>
                                    <Button
                                        v-if="selectedInstanceSummary.instance_id"
                                        color="secondary"
                                        size="sm"
                                        @click="openInstanceEventModal"
                                    >
                                        Добавить событие
                                    </Button>
                                </div>

                                <div v-if="instanceEventsLoading" class="inventory-balance__detail-loading">
                                    Загружаем историю по коду...
                                </div>
                                <div
                                    v-else-if="instanceEvents.length"
                                    class="inventory-balance__instance-events"
                                >
                                    <article
                                        v-for="event in instanceEvents"
                                        :key="event.id"
                                        class="inventory-balance__instance-event"
                                    >
                                        <div class="inventory-balance__history-head">
                                            <span class="inventory-balance__history-badge">{{ event.action_label }}</span>
                                            <span class="inventory-balance__history-date">{{ formatDateTime(event.created_at) }}</span>
                                        </div>
                                        <div class="inventory-balance__history-grid">
                                            <div>
                                                <span class="inventory-balance__detail-label">Откуда</span>
                                                <strong class="inventory-balance__history-value">{{ event.from_location_name || '—' }}</strong>
                                            </div>
                                            <div>
                                                <span class="inventory-balance__detail-label">Куда</span>
                                                <strong class="inventory-balance__history-value">{{ event.to_location_name || '—' }}</strong>
                                            </div>
                                            <div>
                                                <span class="inventory-balance__detail-label">Кто провёл</span>
                                                <strong class="inventory-balance__history-value">{{ event.actor_name || 'Система' }}</strong>
                                            </div>
                                            <div>
                                                <span class="inventory-balance__detail-label">Себестоимость</span>
                                                <strong class="inventory-balance__history-value">{{ formatMoney(event.purchase_cost) }}</strong>
                                            </div>
                                        </div>
                                        <p v-if="event.comment" class="inventory-balance__history-note">{{ event.comment }}</p>
                                    </article>
                                </div>
                                <div v-else class="inventory-balance__detail-placeholder inventory-balance__detail-placeholder--inner">
                                    Для выбранного кода событий пока нет.
                                </div>
                            </div>
                            </div>
                        </div>
                        <div v-else class="inventory-balance__detail-placeholder inventory-balance__detail-placeholder--inner">
                            Для этого товара индивидуальный учет единиц выключен. История по кодам появится после включения
                            индивидуальных единиц в карточке товара.
                        </div>
                    </template>
                </div>
            </template>
        </Modal>

        <Modal v-if="isInstanceEventModalOpen" @close="closeInstanceEventModal">
            <template #header>
                <div class="inventory-balance__instance-modal-head">
                    <h3>Событие по коду</h3>
                    <p>{{ selectedInstanceSummary?.instance_code || '—' }}</p>
                </div>
            </template>

            <template #default>
                <div class="inventory-balance__instance-form">
                    <Select
                        v-model="instanceEventForm.eventTypeId"
                        label="Тип события"
                        :options="instanceEventTypeOptions"
                    />
                    <Input
                        v-model="instanceEventForm.comment"
                        label="Комментарий"
                        placeholder="Например: отправили в ремонт, провели ТО, проверили состояние"
                    />
                </div>
            </template>

            <template #footer>
                <div class="inventory-balance__instance-form-actions">
                    <Button color="ghost" size="sm" :disabled="instanceEventSubmitting" @click="closeInstanceEventModal">
                        Отмена
                    </Button>
                    <Button color="primary" size="sm" :loading="instanceEventSubmitting" @click="submitInstanceEvent">
                        Сохранить
                    </Button>
                </div>
            </template>
        </Modal>

        <Modal v-if="isOperationModalOpen" class="inventory-balance__operation-modal-window" @close="closeOperationModal">
            <template #header>
                <div class="inventory-balance__operation-modal-head">
                    <div>
                        <h3>Операция по товару</h3>
                        <p>{{ selectedRestaurantName }} · {{ selectedStoragePlaceLabel }}</p>
                    </div>
                </div>
            </template>

            <template #default>
                <div class="inventory-balance__operation-body">
                    <div class="inventory-balance__operation-type-list">
                        <button
                            v-for="option in operationTypeOptions"
                            :key="option.value"
                            type="button"
                            :class="['inventory-balance__operation-type-btn', { 'is-active': operationType === option.value }]"
                            @click="operationType = option.value"
                        >
                            {{ option.label }}
                        </button>
                    </div>

                    <div class="inventory-balance__operation-grid">
                        <Select
                            v-model="operationForm.itemId"
                            label="Товар"
                            :options="operationItemOptions"
                            placeholder="Выберите товар"
                            searchable
                        />
                        <Input
                            v-model="operationForm.quantity"
                            label="Количество"
                            type="number"
                            min="1"
                            step="1"
                            placeholder="Например, 5"
                        />

                        <Select
                            v-if="isIncomeOperation"
                            v-model="operationForm.targetStoragePlaceId"
                            label="Куда зачислить"
                            :options="targetStoragePlaceOptions"
                            placeholder="Выберите место хранения"
                            searchable
                        />

                        <Input
                            v-if="isIncomeOperation"
                            v-model="operationForm.unitCost"
                            label="Цена за единицу"
                            type="number"
                            min="0"
                            step="0.01"
                            placeholder="По умолчанию из карточки"
                        />

                        <Select
                            v-if="isTransferOperation || isWriteoffOperation"
                            v-model="operationForm.sourceStoragePlaceId"
                            label="Откуда"
                            :options="sourceStoragePlaceOptions"
                            placeholder="Выберите место хранения"
                            searchable
                        />

                        <Select
                            v-if="isTransferOperation"
                            v-model="operationForm.targetRestaurantId"
                            label="Куда перемещаем"
                            :options="restaurantOptions"
                            placeholder="Выберите ресторан"
                            searchable
                        />

                        <Select
                            v-if="isTransferOperation"
                            v-model="operationForm.targetStoragePlaceId"
                            label="Место хранения получателя"
                            :options="targetStoragePlaceOptions"
                            placeholder="Выберите место хранения"
                            searchable
                        />

                        <Input
                            v-model="operationForm.reason"
                            label="Комментарий / основание"
                            placeholder="Например: поставка, внутренний перевод, списание"
                        />
                    </div>

                    <p v-if="isTransferOperation || isWriteoffOperation" class="inventory-balance__operation-hint">
                        Доступно в источнике: <strong>{{ sourceLocationQuantity }}</strong> шт.
                    </p>
                    <p v-else-if="isIncomeOperation && selectedOperationItem" class="inventory-balance__operation-hint">
                        Товар будет зачислен в {{ selectedRestaurantName }} · {{ operationTargetStoragePlaceLabel }}.
                    </p>

                    <section class="inventory-balance__operation-preview">
                        <h4>Запись операции</h4>
                        <dl>
                            <dt>Что</dt>
                            <dd>{{ operationDraftRecord.what }}</dd>
                            <dt>Сколько</dt>
                            <dd>{{ operationDraftRecord.quantity }}</dd>
                            <dt>Откуда</dt>
                            <dd>{{ operationDraftRecord.from }}</dd>
                            <dt>Куда</dt>
                            <dd>{{ operationDraftRecord.to }}</dd>
                            <dt>Как</dt>
                            <dd>{{ operationDraftRecord.method }}</dd>
                            <dt>Почему</dt>
                            <dd>{{ operationDraftRecord.reason }}</dd>
                        </dl>
                    </section>
                </div>
            </template>

            <template #footer>
                <div class="inventory-balance__operation-actions">
                    <Button color="ghost" size="sm" :disabled="operationSubmitting" @click="closeOperationModal">
                        Отмена
                    </Button>
                    <Button color="primary" size="sm" :loading="operationSubmitting" @click="submitOperation">
                        Сохранить операцию
                    </Button>
                </div>
            </template>
        </Modal>
    </div>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';
import { useInventoryBalancePage } from './composables/useInventoryBalancePage';

const {
    canCreateMovement,
    closeInstanceEventModal,
    closeItemCard,
    closeOperationModal,
    collapseAll,
    currentInstanceCount,
    detailArrivals,
    detailCard,
    detailCardLoading,
    detailEntry,
    detailTab,
    expandAllVisible,
    filteredItems,
    formatDateTime,
    formatMoney,
    getCatalogPath,
    getHighlightedParts,
    groupedCatalog,
    groupedItemsCount,
    historicalInstanceCount,
    instanceEventForm,
    instanceEventSubmitting,
    instanceEventTypeOptions,
    instanceEvents,
    instanceEventsLoading,
    instanceSummaries,
    instanceTrackingEnabled,
    isCategoryExpanded,
    isDetailPaneVisible,
    isGroupExpanded,
    isIncomeOperation,
    isInstanceEventModalOpen,
    isItemCardModalOpen,
    isKindExpanded,
    isOperationModalOpen,
    isTransferOperation,
    isWriteoffOperation,
    loadRestaurantItems,
    loading,
    openInstanceEventModal,
    openItemCard,
    openItemDetail,
    openOperationModal,
    operationDraftRecord,
    operationForm,
    operationItemLoading,
    operationItemOptions,
    operationSubmitting,
    operationTargetStoragePlaceLabel,
    operationType,
    operationTypeOptions,
    restaurantOptions,
    restaurants,
    searchQuery,
    selectInstance,
    selectedInstanceCode,
    selectedInstanceSummary,
    selectedItemId,
    selectedOperationItem,
    selectedRestaurantId,
    selectedRestaurantName,
    selectedStoragePlaceId,
    selectedStoragePlaceLabel,
    sourceLocationQuantity,
    sourceStoragePlaceOptions,
    storagePlaceFilterOptions,
    submitInstanceEvent,
    submitOperation,
    targetStoragePlaceOptions,
    toggleCategory,
    toggleDetailPane,
    toggleGroup,
    toggleKind,
} = useInventoryBalancePage();
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-balance' as *;
</style>
