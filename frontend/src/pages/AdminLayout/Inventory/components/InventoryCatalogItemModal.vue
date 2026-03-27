<template>
    <Modal @close="closeItemModal">
        <template #header>{{ isEditMode ? 'Изменить товар' : 'Новый товар' }}</template>
        <template #default>
            <div class="inventory-catalog__modal-form">
                <Input
                    :model-value="itemForm.name"
                    label="Название"
                    @update:model-value="updateItemFormField('name', $event)"
                />
                <Input
                    :model-value="itemForm.note"
                    label="Описание"
                    placeholder="Описание товара"
                    @update:model-value="updateItemFormField('note', $event)"
                />
                <Input
                    :model-value="itemForm.manufacturer"
                    label="Производитель"
                    placeholder="Например: Valio"
                    @update:model-value="updateItemFormField('manufacturer', $event)"
                />
                <Input
                    :model-value="itemForm.storageConditions"
                    label="Условия хранения"
                    placeholder="Температура, сроки, требования к хранению"
                    @update:model-value="updateItemFormField('storageConditions', $event)"
                />
                <label class="inventory-catalog__instance-toggle">
                    <input
                        :checked="itemForm.useInstanceCodes"
                        type="checkbox"
                        @change="updateItemFormField('useInstanceCodes', $event.target.checked)"
                    >
                    <span>Индивидуальные коды единиц (1, 2, 3...)</span>
                </label>
                <p class="inventory-catalog__instance-toggle-hint">
                    Для массовых товаров (например, тарелки) выключите переключатель, чтобы учитывать их только по общему коду.
                </p>
                <label class="inventory-catalog__instance-toggle">
                    <input
                        :checked="itemForm.isActive"
                        type="checkbox"
                        @change="updateItemFormField('isActive', $event.target.checked)"
                    >
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
                        @click="$emit('update:isCatalogModalOpen', !isCatalogModalOpen)"
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
                    @update:model-value="updateItemFormField('cost', $event)"
                />

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
                            :ref="photoInputRef"
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
                            @click="clearItemPhoto"
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
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';

const emit = defineEmits(['update:isCatalogModalOpen', 'update:itemForm']);

const props = defineProps({
    canSubmitItemModal: { type: Boolean, required: true },
    categoriesByGroup: { type: Object, required: true },
    catalogModalRef: { type: Object, required: true },
    closeItemModal: { type: Function, required: true },
    handleUploadItemPhoto: { type: Function, required: true },
    isCatalogModalOpen: { type: Boolean, required: true },
    isEditMode: { type: Boolean, required: true },
    isModalCategoryExpanded: { type: Function, required: true },
    isModalGroupExpanded: { type: Function, required: true },
    itemForm: { type: Object, required: true },
    openPhotoPicker: { type: Function, required: true },
    photoInputRef: { type: [Object, Function], required: true },
    saving: { type: Boolean, required: true },
    selectModalType: { type: Function, required: true },
    selectedTypeLabel: { type: String, required: true },
    sortedGroups: { type: Array, required: true },
    submitItem: { type: Function, required: true },
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
@use '@/assets/styles/pages/inventory-catalog' as *;
</style>

