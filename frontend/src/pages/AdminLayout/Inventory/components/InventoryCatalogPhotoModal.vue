<template>
    <Modal class="inventory-catalog__photo-modal-window" @close="closeItemPhoto">
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
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Modal from '@/components/UI-components/Modal.vue';

defineProps({
    canDeletePreviewPhoto: { type: Boolean, required: true },
    closeItemPhoto: { type: Function, required: true },
    handleReplacePreviewPhoto: { type: Function, required: true },
    isPreviewPhotoEditable: { type: Boolean, required: true },
    openPreviewPhotoPicker: { type: Function, required: true },
    previewPhotoInputRef: { type: Object, required: true },
    previewPhotoItem: { type: Object, default: null },
    previewPhotoUrl: { type: String, required: true },
    removePreviewPhoto: { type: Function, required: true },
    saving: { type: Boolean, required: true },
    uploadingPhoto: { type: Boolean, required: true },
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-catalog' as *;
</style>
