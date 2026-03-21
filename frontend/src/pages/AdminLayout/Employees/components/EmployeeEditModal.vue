<template>
    <Modal v-if="isOpen" @close="emit('close')">
        <template #header>
            <div class="employees-edit-modal__header">
                <h3 class="employees-edit-modal__title">Редактирование сотрудника</h3>
                <p v-if="employeeName" class="employees-edit-modal__subtitle">{{ employeeName }}</p>
            </div>
        </template>
        <template #default>
            <div v-if="editContextLoading" class="employees-edit-modal__loading">
                Загрузка данных...
            </div>
            <form
                v-else
                class="employees-page__edit-form"
                @submit.prevent="emit('update-employee')"
            >
                <div class="employees-edit-modal__photo">
                    <div class="employees-edit-modal__photo-preview">
                        <img
                            v-if="employeeCard?.photo_url"
                            :src="employeeCard.photo_url"
                            alt="Фото сотрудника"
                        />
                        <div v-else class="employees-edit-modal__photo-placeholder">
                            Фото
                        </div>
                    </div>
                    <label class="employees-edit-modal__photo-action">
                        <input
                            type="file"
                            accept="image/*"
                            :disabled="updatingEmployee"
                            @change="onPhotoSelected"
                        />
                        <span>{{ employeeCard?.photo_url ? 'Заменить фото' : 'Добавить фото' }}</span>
                    </label>
                </div>
                <Input v-model="employeeEditForm.lastName" label="Фамилия" />
                <Input v-model="employeeEditForm.firstName" label="Имя" />
                <Input v-model="employeeEditForm.middleName" label="Отчество" />
                <Input v-model="employeeEditForm.username" label="Логин" />
                <Select
                    v-model="employeeEditForm.gender"
                    label="Пол"
                    :options="genderOptions"
                />
                <Input v-model="employeeEditForm.staffCode" label="Табельный номер" />
                <Input
                    v-model="employeeEditForm.phoneInput"
                    label="Телефон (+7XXXXXXXXXX)"
                    inputmode="tel"
                />
                <Input
                    v-model="employeeEditForm.email"
                    label="Электронная почта"
                    type="email"
                    inputmode="email"
                />
                <Input
                    v-if="canViewSensitiveStaffFields"
                    v-model="employeeEditForm.iikoCode"
                    label="Код iiko"
                />
                <Input
                    v-if="canEditIikoId"
                    v-model="employeeEditForm.iikoId"
                    label="Код сотрудника (Айки)"
                />
                <Select
                    v-model="employeeEditForm.companyId"
                    label="Компания"
                    :options="companyOptions"
                    placeholder="Выберите компанию"
                />
                <Select
                    v-if="canViewSensitiveStaffFields"
                    v-model="employeeEditForm.roleId"
                    label="Роль"
                    :options="roleOptions"
                    placeholder="Выберите роль"
                    :disabled="!canEditRoles || Boolean(employeeEditForm.positionId)"
                />
                <Select
                    v-model="employeeEditForm.positionId"
                    label="Должность"
                    :options="positionOptions"
                    placeholder="Выберите должность"
                />
                <Select
                    v-model="employeeEditForm.workplaceRestaurantId"
                    label="Место работы"
                    :options="workplaceRestaurantOptions"
                    placeholder="Не выбрано"
                />
                <template v-if="employeeEditForm.rateHidden">
                    <Input
                        :model-value="'$$$'"
                        label="Ставка"
                        type="text"
                        disabled
                    />
                </template>
                <template v-else>
                    <Checkbox v-model="employeeEditForm.useIndividualRate" :disabled="!canEditRates" label="Индивидуальная ставка" />
                    <Input
                        v-if="employeeEditForm.useIndividualRate"
                        v-model="employeeEditForm.individualRate" :disabled="!canEditRates"
                        label="Индивидуальная ставка"
                        type="number"
                        step="0.01"
                    />
                    <Input
                        v-else
                        v-model="employeeEditForm.rate" :disabled="!canEditRates"
                        label="Ставка"
                        type="number"
                        step="0.01"
                    />
                </template>
                <DateInput v-model="employeeEditForm.hireDate" label="Дата найма" />
                <DateInput
                    v-if="employeeCard?.fired"
                    v-model="employeeEditForm.fireDate"
                    label="Дата увольнения"
                />
                <DateInput v-model="employeeEditForm.birthDate" label="Дата рождения" />
                <Input
                    v-model="employeeEditForm.password"
                    label="Новый пароль"
                    type="password"
                    autocomplete="new-password"
                />
                <div class="employees-page__checkbox-inline">
                    <Checkbox v-model="employeeEditForm.isCisEmployee" label="Сотрудник СНГ" />
                    <Checkbox v-model="employeeEditForm.isFormalized" label="Оформлен оф." />
                    <Checkbox
                        v-if="canViewSensitiveStaffFields"
                        v-model="employeeEditForm.confidentialDataConsent"
                        label="Согласие на передачу конфиденциальных данных"
                    />
                </div>
                <label class="employees-page__form-label employees-page__form-label--full">
                    Рестораны
                </label>
                <div class="employees-page__restaurants employees-page__restaurants--edit">
                    <Checkbox
                        v-for="restaurant in restaurants"
                        :key="restaurant.id"
                        :model-value="employeeEditForm.hasGlobalAccess || employeeEditForm.hasFullRestaurantAccess || employeeEditForm.restaurantIds.includes(restaurant.id)"
                        :label="restaurant.name"
                        :disabled="employeeEditForm.hasGlobalAccess || (employeeEditForm.hasFullRestaurantAccess && !canEditFullAccess)"
                        @update:model-value="(checked) => emit('toggle-edit-restaurant', restaurant.id, checked)"
                    />
                </div>
            </form>
        </template>
        <template #footer>
            <Button color="ghost" :disabled="updatingEmployee" @click="emit('close')">
                Отмена
            </Button>
            <Button color="primary" :loading="updatingEmployee" @click="emit('update-employee')">
                Сохранить
            </Button>
        </template>
    </Modal>
</template>

<script setup>
import { computed, toRefs } from 'vue';
import Button from '@/components/UI-components/Button.vue';
import Checkbox from '@/components/UI-components/Checkbox.vue';
import Input from '@/components/UI-components/Input.vue';
import DateInput from '@/components/UI-components/DateInput.vue';
import Modal from '@/components/UI-components/Modal.vue';
import Select from '@/components/UI-components/Select.vue';

const props = defineProps({
    isOpen: { type: Boolean, default: false },
    employeeEditForm: { type: Object, required: true },
    genderOptions: { type: Array, default: () => [] },
    companyOptions: { type: Array, default: () => [] },
    roleOptions: { type: Array, default: () => [] },
    positionOptions: { type: Array, default: () => [] },
    workplaceRestaurantOptions: { type: Array, default: () => [] },
    restaurants: { type: Array, default: () => [] },
    canEditFullAccess: { type: Boolean, default: false },
    canEditRoles: { type: Boolean, default: false },
    canEditRates: { type: Boolean, default: false },
    canEditIikoId: { type: Boolean, default: false },
    updatingEmployee: { type: Boolean, default: false },
    editContextLoading: { type: Boolean, default: false },
    formatFullName: { type: Function, required: true },
    employeeCard: { type: Object, default: null },
    canViewSensitiveStaffFields: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'update-employee', 'toggle-edit-restaurant', 'upload-photo']);

const {
    isOpen,
    employeeEditForm,
    genderOptions,
    companyOptions,
    roleOptions,
    positionOptions,
    workplaceRestaurantOptions,
    restaurants,
    canEditFullAccess,
    canEditRoles,
    canEditRates,
    canEditIikoId,
    updatingEmployee,
    editContextLoading,
    formatFullName,
    employeeCard,
    canViewSensitiveStaffFields,
} = toRefs(props);

function onPhotoSelected(event) {
    const [file] = event?.target?.files || [];
    if (file) {
        emit('upload-photo', file);
    }
    if (event?.target) {
        event.target.value = '';
    }
}

const employeeName = computed(() => {
    if (!employeeCard.value) {
        return '';
    }
    return formatFullName.value(employeeCard.value) || '';
});
</script>

<style scoped lang="scss">
@use '@/assets/styles/pages/employees-edit-modal' as *;
</style>
