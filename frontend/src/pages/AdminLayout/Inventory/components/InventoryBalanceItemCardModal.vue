<template>
    <Modal class="inventory-balance__card-modal-window" @close="closeItemCard">
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
                        @click="$emit('update:detailTab', 'arrivals')"
                    >
                        История прихода
                    </button>
                    <button
                        type="button"
                        :class="['inventory-balance__detail-tab', { 'is-active': detailTab === 'instances' }]"
                        :disabled="!instanceTrackingEnabled"
                        @click="$emit('update:detailTab', 'instances')"
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
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Modal from '@/components/UI-components/Modal.vue';

defineEmits(['update:detailTab']);

defineProps({
    closeItemCard: { type: Function, required: true },
    currentInstanceCount: { type: Number, required: true },
    detailArrivals: { type: Array, required: true },
    detailCardLoading: { type: Boolean, required: true },
    detailEntry: { type: Object, required: true },
    detailTab: { type: String, required: true },
    formatDateTime: { type: Function, required: true },
    formatMoney: { type: Function, required: true },
    getCatalogPath: { type: Function, required: true },
    historicalInstanceCount: { type: Number, required: true },
    instanceEvents: { type: Array, required: true },
    instanceEventsLoading: { type: Boolean, required: true },
    instanceSummaries: { type: Array, required: true },
    instanceTrackingEnabled: { type: Boolean, required: true },
    openInstanceEventModal: { type: Function, required: true },
    selectInstance: { type: Function, required: true },
    selectedInstanceCode: { type: String, required: true },
    selectedInstanceSummary: { type: Object, default: null },
    selectedRestaurantName: { type: String, required: true },
    selectedStoragePlaceLabel: { type: String, required: true },
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-balance' as *;
</style>
