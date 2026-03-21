<template>
    <Modal v-if="isOpen" @close="emit('close')">
        <template #header>
            <div class="employees-page__modal-header">
                <div>
                    <h3 class="employees-page__modal-title">
                        {{ isCreating ? 'Новая смена' : 'Редактирование смены' }}
                    </h3>
                    <p v-if="!isCreating && editingAttendance?.id" class="employees-page__modal-subtitle">
                        ID смены: {{ editingAttendance?.id }}
                    </p>
                </div>
            </div>
        </template>
        <template #default>
            <div class="employees-page__attendance-form">
                <DateInput v-model="attendanceForm.openDate" label="Дата открытия" required />
                <Input v-model="attendanceForm.openTime" label="Время открытия" type="time" required />
                <Select
                    v-model="selectedRestaurantId"
                    label="Ресторан"
                    :options="restaurantOptions"
                />
                <Select
                    v-model="selectedPositionId"
                    label="Должность"
                    :options="positionOptions"
                />
                <DateInput
                    v-model="attendanceForm.closeDate"
                    label="Дата закрытия"
                    :max="todayDate"
                />
                <Input v-model="attendanceForm.closeTime" label="Время закрытия" type="time" />
                <template v-if="rateHidden">
                    <Input :model-value="'$$$'" label="Ставка" type="text" disabled />
                </template>
                <template v-else>
                    <Input v-model="attendanceForm.rate" label="Ставка" type="number" step="0.01" />
                </template>
                <Input
                    v-model="attendanceForm.durationMinutes"
                    label="Длительность (мин)"
                    type="number"
                    min="0"
                />
                <Input
                    v-model="attendanceForm.nightMinutes"
                    label="Ночные (мин)"
                    type="number"
                    min="0"
                />
            </div>
            <p class="employees-page__attendance-hint">
                Чтобы оставить смену открытой, очистите поля даты и времени закрытия.
            </p>
        </template>
        <template #footer>
            <Button
                v-if="!isCreating"
                color="danger"
                :loading="deletingAttendance"
                @click="emit('delete-attendance')"
            >
                Удалить смену
            </Button>
            <Button color="ghost" @click="emit('close')">Отмена</Button>
            <Button color="primary" :loading="updatingAttendance" @click="emit('submit-attendance')">
                {{ isCreating ? 'Создать' : 'Сохранить' }}
            </Button>
        </template>
    </Modal>
</template>

<script setup>
import { computed, toRefs } from 'vue';
import Button from '@/components/UI-components/Button.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';

const props = defineProps({
    isOpen: { type: Boolean, default: false },
    attendanceForm: { type: Object, required: true },
    editingAttendance: { type: Object, default: null },
    isCreating: { type: Boolean, default: false },
    updatingAttendance: { type: Boolean, default: false },
    restaurantOptions: { type: Array, default: () => [] },
    positionOptions: { type: Array, default: () => [] },
    deletingAttendance: { type: Boolean, default: false },
    rateHidden: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'submit-attendance', 'delete-attendance']);

function getTodayDateValue() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

const todayDate = getTodayDateValue();

const {
    isOpen,
    attendanceForm,
    editingAttendance,
    isCreating,
    updatingAttendance,
    restaurantOptions,
    positionOptions,
    deletingAttendance,
    rateHidden,
} = toRefs(props);

const selectedRestaurantId = computed({
    get: () => {
        const value = attendanceForm.value?.restaurantId;
        if (value === null || value === undefined) {
            return '';
        }
        return String(value);
    },
    set: (newValue) => {
        if (!attendanceForm.value) {
            return;
        }
        if (newValue === null || newValue === undefined || newValue === '') {
            attendanceForm.value.restaurantId = null;
            return;
        }
        const parsed = Number(newValue);
        attendanceForm.value.restaurantId = Number.isFinite(parsed) ? parsed : null;
    },
});

const selectedPositionId = computed({
    get: () => {
        const value = attendanceForm.value?.positionId;
        if (value === null || value === undefined) {
            return '';
        }
        return String(value);
    },
    set: (newValue) => {
        if (!attendanceForm.value) {
            return;
        }
        if (newValue === null || newValue === undefined || newValue === '') {
            attendanceForm.value.positionId = null;
            return;
        }
        const parsed = Number(newValue);
        attendanceForm.value.positionId = Number.isFinite(parsed) ? parsed : null;
    },
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-attendance-edit-modal' as *;
</style>
