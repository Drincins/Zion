<template>
    <Modal class="inventory-catalog__card-modal-window" @close="closeItemCard">
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
                    v-for="tab in itemCardTabs"
                    :key="tab.value"
                    type="button"
                    class="inventory-catalog__card-tab"
                    :class="{ 'is-active': itemCardActiveTab === tab.value }"
                    :aria-pressed="itemCardActiveTab === tab.value"
                    @click="$emit('update:itemCardActiveTab', tab.value)"
                >
                    {{ tab.label }}
                </button>
            </nav>
        </template>

        <template #default>
            <div v-if="itemCardActiveTab === 'info'" class="inventory-catalog__card-panel inventory-catalog__card-panel--info">
                <div class="inventory-catalog__modal-form">
                    <Input
                        :model-value="itemForm.name"
                        label="Название"
                        :readonly="!canEditNomenclature"
                        @update:model-value="updateItemFormField('name', $event)"
                    />
                    <Input
                        :model-value="itemForm.note"
                        label="Описание"
                        placeholder="Описание товара"
                        :readonly="!canEditNomenclature"
                        @update:model-value="updateItemFormField('note', $event)"
                    />
                    <Input
                        :model-value="itemForm.manufacturer"
                        label="Производитель"
                        placeholder="Например: Valio"
                        :readonly="!canEditNomenclature"
                        @update:model-value="updateItemFormField('manufacturer', $event)"
                    />
                    <Input
                        :model-value="itemForm.storageConditions"
                        label="Условия хранения"
                        placeholder="Температура, сроки, требования к хранению"
                        :readonly="!canEditNomenclature"
                        @update:model-value="updateItemFormField('storageConditions', $event)"
                    />
                    <label class="inventory-catalog__instance-toggle">
                        <input
                            :checked="itemForm.useInstanceCodes"
                            type="checkbox"
                            :disabled="!canEditNomenclature"
                            @change="updateItemFormField('useInstanceCodes', $event.target.checked)"
                        >
                        <span>Индивидуальные коды единиц (1, 2, 3...)</span>
                    </label>
                    <p class="inventory-catalog__instance-toggle-hint">
                        Включено: для каждой единицы создается свой код. Выключено: учет ведется только по общему коду товара.
                    </p>
                    <label class="inventory-catalog__instance-toggle">
                        <input
                            :checked="itemForm.isActive"
                            type="checkbox"
                            :disabled="!canEditNomenclature"
                            @change="updateItemFormField('isActive', $event.target.checked)"
                        >
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
                            @click="canEditNomenclature && $emit('update:isCatalogModalOpen', !isCatalogModalOpen)"
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
                        :model-value="itemForm.cost"
                        label="Стоимость"
                        type="number"
                        step="0.01"
                        min="0"
                        :readonly="!canEditNomenclature"
                        @update:model-value="updateItemFormField('cost', $event)"
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
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Table from '@/components/UI-components/Table.vue';

const emit = defineEmits(['update:isCatalogModalOpen', 'update:itemCardActiveTab', 'update:itemForm']);

const props = defineProps({
    canEditNomenclature: { type: Boolean, required: true },
    categoriesByGroup: { type: Object, required: true },
    catalogModalRef: { type: Object, required: true },
    closeItemCard: { type: Function, required: true },
    formatItemCardChangeDate: { type: Function, required: true },
    formatItemCardChangeField: { type: Function, required: true },
    formatItemCardChangeValue: { type: Function, required: true },
    formatItemCreatedAt: { type: Function, required: true },
    formatMoney: { type: Function, required: true },
    getCatalogPath: { type: Function, required: true },
    isCatalogModalOpen: { type: Boolean, required: true },
    isModalCategoryExpanded: { type: Function, required: true },
    isModalGroupExpanded: { type: Function, required: true },
    itemCardActiveTab: { type: String, required: true },
    itemCardChanges: { type: Array, required: true },
    itemCardChangesError: { type: String, required: true },
    itemCardChangesLoading: { type: Boolean, required: true },
    itemCardItem: { type: Object, default: null },
    itemCardPhotoUrl: { type: String, required: true },
    itemCardRestaurantRows: { type: Array, required: true },
    itemCardRestaurantsQuantity: { type: Number, required: true },
    itemCardTabs: { type: Array, required: true },
    itemCardTotalQuantity: { type: Number, required: true },
    itemCardWarehouseQuantity: { type: Number, required: true },
    itemForm: { type: Object, required: true },
    openItemCardPhoto: { type: Function, required: true },
    reloadItemCardChanges: { type: Function, required: true },
    saving: { type: Boolean, required: true },
    selectModalType: { type: Function, required: true },
    selectedTypeLabel: { type: String, required: true },
    sortedGroups: { type: Array, required: true },
    submitItemCardInfo: { type: Function, required: true },
    toggleModalCategory: { type: Function, required: true },
    toggleModalGroup: { type: Function, required: true },
    typesByCategory: { type: Object, required: true },
    uploadingPhoto: { type: Boolean, required: true },
});

function updateItemFormField(field, value) {
    emit('update:itemForm', {
        ...props.itemForm,
        [field]: value
    });
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-catalog' as *;
</style>

