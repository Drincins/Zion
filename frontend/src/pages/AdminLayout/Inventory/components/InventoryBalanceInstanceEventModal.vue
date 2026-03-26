<template>
    <Modal @close="closeInstanceEventModal">
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
</template>

<script setup>
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';

defineProps({
    closeInstanceEventModal: { type: Function, required: true },
    instanceEventForm: { type: Object, required: true },
    instanceEventSubmitting: { type: Boolean, required: true },
    instanceEventTypeOptions: { type: Array, required: true },
    selectedInstanceSummary: { type: Object, default: null },
    submitInstanceEvent: { type: Function, required: true },
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/inventory-balance' as *;
</style>
