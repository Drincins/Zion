<template>
    <Modal @close="closeItemPhoto">
        <template #header>Фото товара</template>
        <template #default>
            <div class="inventory-items__preview-modal">
                <img
                    v-if="previewPhotoItem.photo_url"
                    :src="previewPhotoItem.photo_url"
                    :alt="previewPhotoItem.name || 'Фото товара'"
                    class="inventory-items__preview-image"
                />
                <p v-else class="inventory-items__preview-empty">Для этого товара фото не загружено.</p>
            </div>
        </template>
    </Modal>
</template>

<script setup>
import Modal from '@/components/UI-components/Modal.vue';

defineProps({
    closeItemPhoto: { type: Function, required: true },
    previewPhotoItem: { type: Object, required: true },
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-items' as *;
</style>
