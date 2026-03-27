<template>
    <Modal @close="closeItemModal">
        <template #header>{{ isEditMode ? 'Изменить товар' : 'Новый товар' }}</template>
        <template #default>
            <div class="inventory-items__modal-form">
                <div v-if="!isEditMode" class="inventory-items__catalog-source">
                    <Button
                        v-if="canToggleCreateSourceMode"
                        type="button"
                        color="ghost"
                        size="sm"
                        class="inventory-items__catalog-source-btn"
                        :disabled="loadingCatalogItems"
                        @click="toggleCatalogSourceMode"
                    >
                        {{ isCatalogSourceMode ? 'Добавить новый товар' : 'Выбрать из каталога' }}
                    </Button>
                    <p class="inventory-items__catalog-source-help">
                        {{ isCatalogSourceMode
                            ? 'Выберите товар из каталога, затем укажите объект, количество и цену партии.'
                            : 'Если в каталоге нет нужного товара, создайте новую карточку вручную.' }}
                    </p>
                </div>

                <div v-if="isCatalogSourceMode" class="inventory-items__catalog-search-block">
                    <Input
                        :model-value="itemForm.catalogSearch"
                        label="Поиск в каталоге"
                        placeholder="Введите название, описание или код"
                        @update:model-value="updateItemFormField('catalogSearch', $event)"
                    />
                    <div class="inventory-items__catalog-search-results">
                        <div v-if="loadingCatalogItems" class="inventory-items__catalog-empty">
                            Загружаем каталог...
                        </div>
                        <template v-else-if="catalogItemsForPicker.length">
                            <button
                                v-for="catalogItem in catalogItemsForPicker"
                                :key="catalogItem.id"
                                type="button"
                                class="inventory-items__catalog-search-item"
                                :class="{ 'is-selected': Number(itemForm.selectedCatalogItemId) === Number(catalogItem.id) }"
                                @click="selectCatalogItem(catalogItem)"
                            >
                                <span class="inventory-items__catalog-search-title">{{ catalogItem.name }}</span>
                                <span class="inventory-items__catalog-search-meta">
                                    {{ catalogItem.code || `ITEM-${catalogItem.id}` }} · {{ getCatalogPath(catalogItem) }}
                                </span>
                            </button>
                        </template>
                        <div v-else class="inventory-items__catalog-empty">Ничего не найдено.</div>
                    </div>
                </div>

                <Input
                    :model-value="itemForm.name"
                    label="Название"
                    :readonly="isCatalogSourceMode"
                    @update:model-value="updateItemFormField('name', $event)"
                />
                <Input
                    :model-value="itemForm.note"
                    label="Описание"
                    placeholder="Описание товара"
                    :readonly="isCatalogSourceMode"
                    @update:model-value="updateItemFormField('note', $event)"
                />
                <Input
                    :model-value="itemForm.manufacturer"
                    label="Производитель"
                    placeholder="Например: Valio"
                    :readonly="isCatalogSourceMode"
                    @update:model-value="updateItemFormField('manufacturer', $event)"
                />
                <Input
                    :model-value="itemForm.storageConditions"
                    label="Условия хранения"
                    placeholder="Температура, сроки, требования к хранению"
                    :readonly="isCatalogSourceMode"
                    @update:model-value="updateItemFormField('storageConditions', $event)"
                />
                <label v-if="!isCatalogSourceMode" class="inventory-items__instance-toggle">
                    <input
                        :checked="itemForm.useInstanceCodes"
                        type="checkbox"
                        @change="updateItemFormField('useInstanceCodes', $event.target.checked)"
                    >
                    <span>Индивидуальные коды единиц (1, 2, 3...)</span>
                </label>
                <p v-if="!isCatalogSourceMode" class="inventory-items__instance-toggle-hint">
                    Для массовых товаров можно выключить: учет будет только по общему коду.
                </p>

                <div :ref="catalogModalRef" class="catalog-picker catalog-picker--modal">
                    <label class="inventory-items__label">Группа / категория / вид</label>
                    <button
                        type="button"
                        class="catalog-picker__trigger"
                        :disabled="isCatalogSourceMode"
                        @click="!isCatalogSourceMode && $emit('update:isCatalogModalOpen', !isCatalogModalOpen)"
                    >
                        <span :class="{ 'is-placeholder': !itemForm.catalogNodeId }">{{ catalogModalLabel }}</span>
                        <span class="inventory-items__caret">{{ isCatalogModalOpen ? '▲' : '▼' }}</span>
                    </button>
                    <div v-if="isCatalogModalOpen" class="catalog-picker__menu">
                        <template v-for="group in sortedGroups" :key="group.id">
                            <div class="catalog-picker__row catalog-picker__row--l1">
                                <button
                                    v-if="(categoriesByGroup.get(group.id) || []).length"
                                    type="button"
                                    class="catalog-picker__toggle"
                                    @click="toggleModalGroup(group.id)"
                                >
                                    {{ isModalGroupExpanded(group.id) ? '⌄' : '›' }}
                                </button>
                                <span v-else class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                                <span class="catalog-picker__item catalog-picker__item--static">{{ group.name }}</span>
                            </div>

                            <template v-if="isModalGroupExpanded(group.id)">
                                <template v-for="category in categoriesByGroup.get(group.id) || []" :key="category.id">
                                    <div class="catalog-picker__row catalog-picker__row--l2">
                                        <button
                                            v-if="(typesByCategory.get(category.id) || []).length"
                                            type="button"
                                            class="catalog-picker__toggle"
                                            @click="toggleModalCategory(category.id)"
                                        >
                                            {{ isModalCategoryExpanded(category.id) ? '⌄' : '›' }}
                                        </button>
                                        <span v-else class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                                        <span class="catalog-picker__item catalog-picker__item--static">{{ category.name }}</span>
                                    </div>

                                    <template v-if="isModalCategoryExpanded(category.id)">
                                        <div
                                            v-for="type in typesByCategory.get(category.id) || []"
                                            :key="type.id"
                                            class="catalog-picker__row catalog-picker__row--l3"
                                        >
                                            <span class="catalog-picker__toggle catalog-picker__toggle--placeholder" />
                                            <button
                                                type="button"
                                                class="catalog-picker__item"
                                                :class="{ 'is-selected': itemForm.catalogNodeId === `t:${type.id}` }"
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
                    :disabled="isCatalogSourceMode && !selectedCatalogItem"
                    @update:model-value="updateItemFormField('cost', $event)"
                />
                <p v-if="isCatalogSourceMode" class="inventory-items__catalog-cost-hint" :class="{ 'is-warning': isCatalogCostOverride }">
                    <template v-if="isCatalogCostOverride">
                        Стоимость партии отличается от каталожной. Изменение запишется в «Журнал операций».
                    </template>
                    <template v-else>
                        Стоимость в каталоге не изменится. Можно задать цену только для добавляемой партии.
                    </template>
                </p>

                <div v-if="!isCatalogSourceMode" class="inventory-items__photo-block">
                    <label class="inventory-items__label">Фото</label>
                    <button
                        type="button"
                        class="inventory-items__photo-trigger"
                        :disabled="uploadingPhoto || !canEditModalPhoto"
                        @click="openPhotoPicker"
                    >
                        <span class="inventory-items__photo-icon" aria-hidden="true">
                            <svg viewBox="0 0 24 24" fill="none">
                                <path
                                    d="M4 8h3l1.2-2h7.6L17 8h3a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a1 1 0 0 1 1-1Z"
                                    stroke="currentColor"
                                    stroke-width="1.8"
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                />
                                <circle cx="12" cy="13.5" r="3.2" stroke="currentColor" stroke-width="1.8" />
                            </svg>
                        </span>
                        <span>{{ uploadingPhoto ? 'Загрузка...' : 'Загрузить фото' }}</span>
                    </button>
                    <input
                        :ref="photoInputRef"
                        class="inventory-items__photo-input"
                        type="file"
                        accept="image/*"
                        :disabled="uploadingPhoto || !canEditModalPhoto"
                        @change="handleUploadItemPhoto"
                    />
                    <div class="inventory-items__photo-meta">
                        <span v-if="itemForm.photoUrl" class="inventory-items__photo-state">
                            Фото добавлено
                        </span>
                        <span v-else class="inventory-items__photo-state inventory-items__photo-state--muted">
                            Фото пока не выбрано
                        </span>
                        <Button
                            v-if="itemForm.photoUrl"
                            type="button"
                            color="ghost"
                            size="sm"
                            :disabled="uploadingPhoto || saving || !canEditModalPhoto"
                            @click="clearItemPhoto"
                        >
                            Удалить фото
                        </Button>
                    </div>
                </div>
                <div v-else class="inventory-items__catalog-photo-readonly">
                    <label class="inventory-items__label">Фото</label>
                    <div v-if="itemForm.photoUrl" class="inventory-items__catalog-photo-preview">
                        <img :src="itemForm.photoUrl" alt="Фото из каталога" />
                    </div>
                    <p class="inventory-items__catalog-source-help">
                        Фото и описание подтягиваются из карточки каталога и в этом окне не редактируются.
                    </p>
                </div>

                <div v-if="!isEditMode && isCatalogSourceMode" class="inventory-items__assign-block">
                    <p class="inventory-items__catalog-source-help">
                        Укажите объект и количество для выбранного товара из каталога.
                    </p>

                    <div class="inventory-items__assign-fields">
                        <Select
                            :model-value="itemForm.targetOptionId"
                            label="Подразделение"
                            :options="createDepartmentOptions"
                            placeholder="Выберите подразделение"
                            searchable
                            @update:model-value="updateItemFormField('targetOptionId', $event)"
                        />
                        <Input
                            :model-value="itemForm.targetQuantity"
                            label="Количество наименований"
                            type="number"
                            min="1"
                            @update:model-value="updateItemFormField('targetQuantity', $event)"
                        />
                    </div>
                </div>
            </div>
        </template>
        <template #footer>
            <Button color="ghost" :disabled="saving || uploadingPhoto" @click="closeItemModal">Отмена</Button>
            <Button v-if="canSubmitItemModal" color="primary" :loading="saving" @click="submitItem">Сохранить</Button>
        </template>
    </Modal>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';

const emit = defineEmits(['update:isCatalogModalOpen', 'update:itemForm']);

const props = defineProps({
    canEditModalPhoto: { type: Boolean, required: true },
    canSubmitItemModal: { type: Boolean, required: true },
    canToggleCreateSourceMode: { type: Boolean, required: true },
    catalogItemsForPicker: { type: Array, required: true },
    catalogModalLabel: { type: String, required: true },
    catalogModalRef: { type: Object, required: true },
    categoriesByGroup: { type: Object, required: true },
    closeItemModal: { type: Function, required: true },
    createDepartmentOptions: { type: Array, required: true },
    getCatalogPath: { type: Function, required: true },
    handleUploadItemPhoto: { type: Function, required: true },
    isCatalogCostOverride: { type: Boolean, required: true },
    isCatalogModalOpen: { type: Boolean, required: true },
    isCatalogSourceMode: { type: Boolean, required: true },
    isEditMode: { type: Boolean, required: true },
    isModalCategoryExpanded: { type: Function, required: true },
    isModalGroupExpanded: { type: Function, required: true },
    itemForm: { type: Object, required: true },
    loadingCatalogItems: { type: Boolean, required: true },
    openPhotoPicker: { type: Function, required: true },
    photoInputRef: { type: [Object, Function], required: true },
    saving: { type: Boolean, required: true },
    selectCatalogItem: { type: Function, required: true },
    selectModalType: { type: Function, required: true },
    selectedCatalogItem: { type: Object, default: null },
    sortedGroups: { type: Array, required: true },
    submitItem: { type: Function, required: true },
    toggleCatalogSourceMode: { type: Function, required: true },
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

function clearItemPhoto() {
    updateItemFormField('photoUrl', '');
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-items' as *;
</style>

