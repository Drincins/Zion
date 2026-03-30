<template>
    <Modal @close="closeTransferModal">
        <template #header>Перевести товар</template>
        <template #default>
            <div class="inventory-items__modal-form">
                <Input :model-value="transferForm.itemCode" label="Товар" disabled />
                <Select
                    :model-value="transferForm.sourceOptionId"
                    label="Откуда перевести"
                    :options="sourceTransferLocationOptions"
                    placeholder="Выберите источник"
                    searchable
                    @update:model-value="updateTransferFormField('sourceOptionId', $event)"
                />
                <Select
                    :model-value="transferForm.targetOptionId"
                    label="Куда перевести"
                    :options="targetTransferLocationOptions"
                    placeholder="Выберите ресторан или виртуальный склад"
                    searchable
                    @update:model-value="updateTransferFormField('targetOptionId', $event)"
                />
                <Input
                    :model-value="transferForm.quantity"
                    label="Количество"
                    type="number"
                    min="1"
                    @update:model-value="updateTransferFormField('quantity', $event)"
                />
            </div>
        </template>
        <template #footer>
            <Button color="ghost" :disabled="saving" @click="closeTransferModal">Отмена</Button>
            <Button v-if="canCreateMovement" color="primary" :loading="saving" @click="submitTransfer">Перевести</Button>
        </template>
    </Modal>
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';

const emit = defineEmits(['update:transferForm']);

const props = defineProps({
    canCreateMovement: { type: Boolean, required: true },
    closeTransferModal: { type: Function, required: true },
    saving: { type: Boolean, required: true },
    sourceTransferLocationOptions: { type: Array, required: true },
    submitTransfer: { type: Function, required: true },
    targetTransferLocationOptions: { type: Array, required: true },
    transferForm: { type: Object, required: true },
});

function updateTransferFormField(field, value) {
    emit('update:transferForm', {
        ...props.transferForm,
        [field]: value
    });
}
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-items' as *;
</style>

