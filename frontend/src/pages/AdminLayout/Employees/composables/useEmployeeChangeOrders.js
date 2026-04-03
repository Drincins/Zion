import { computed, reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';
import {
    cancelEmployeeChangeOrder,
    createEmployeeChangeOrder,
    fetchEmployeeChangeOrders,
} from '@/api';

function parseOptionalNumber(value) {
    if (value === null || value === undefined) {
        return null;
    }
    const raw = String(value).trim();
    if (!raw) {
        return null;
    }
    const parsed = Number(raw.replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : NaN;
}

export function useEmployeeChangeOrders({
    activeEmployee,
    employeeCard,
    canManageEmployeeChangeOrders,
    canEditRates,
    formatDateInput,
}) {
    const toast = useToast();

    const employeeChangeOrders = ref([]);
    const employeeChangeOrdersLoading = ref(false);
    const employeeChangeOrdersError = ref('');
    const isEmployeeChangeOrderFormOpen = ref(false);
    const savingEmployeeChangeOrder = ref(false);
    const cancellingEmployeeChangeOrderId = ref(null);
    const employeeChangeOrderForm = reactive({
        effectiveDate: formatDateInput(new Date()),
        changePosition: false,
        positionIdNew: '',
        changeWorkplaceRestaurant: false,
        workplaceRestaurantIdNew: '',
        changeIndividualRate: false,
        individualRateNew: '',
        clearIndividualRate: false,
        applyToAttendances: false,
        comment: '',
    });

    const canManageRateChanges = computed(() =>
        Boolean(canEditRates?.value) && !Boolean(employeeCard.value?.rate_hidden),
    );

    function resetEmployeeChangeOrderForm() {
        employeeChangeOrderForm.effectiveDate = formatDateInput(new Date());
        employeeChangeOrderForm.changePosition = false;
        employeeChangeOrderForm.positionIdNew = '';
        employeeChangeOrderForm.changeWorkplaceRestaurant = false;
        employeeChangeOrderForm.workplaceRestaurantIdNew = '';
        employeeChangeOrderForm.changeIndividualRate = false;
        employeeChangeOrderForm.individualRateNew = '';
        employeeChangeOrderForm.clearIndividualRate = false;
        employeeChangeOrderForm.applyToAttendances = false;
        employeeChangeOrderForm.comment = '';
    }

    function openEmployeeChangeOrderForm() {
        resetEmployeeChangeOrderForm();
        isEmployeeChangeOrderFormOpen.value = true;
    }

    function closeEmployeeChangeOrderForm() {
        isEmployeeChangeOrderFormOpen.value = false;
        savingEmployeeChangeOrder.value = false;
        resetEmployeeChangeOrderForm();
    }

    function updateEmployeeChangeOrderFormField(payload) {
        const field = payload?.field;
        if (!field || !Object.prototype.hasOwnProperty.call(employeeChangeOrderForm, field)) {
            return;
        }
        employeeChangeOrderForm[field] = payload.value;

        if (field === 'changePosition' && !payload.value) {
            employeeChangeOrderForm.positionIdNew = '';
        }
        if (field === 'changeWorkplaceRestaurant' && !payload.value) {
            employeeChangeOrderForm.workplaceRestaurantIdNew = '';
        }
        if (field === 'changeIndividualRate' && !payload.value) {
            employeeChangeOrderForm.individualRateNew = '';
            employeeChangeOrderForm.clearIndividualRate = false;
        }
        if (field === 'clearIndividualRate' && payload.value) {
            employeeChangeOrderForm.individualRateNew = '';
        }
    }

    async function loadEmployeeChangeOrders() {
        if (!activeEmployee.value?.id || !canManageEmployeeChangeOrders.value) {
            employeeChangeOrders.value = [];
            employeeChangeOrdersError.value = '';
            return;
        }
        employeeChangeOrdersLoading.value = true;
        employeeChangeOrdersError.value = '';
        try {
            const data = await fetchEmployeeChangeOrders(activeEmployee.value.id);
            employeeChangeOrders.value = Array.isArray(data?.items) ? data.items : [];
        } catch (error) {
            employeeChangeOrders.value = [];
            employeeChangeOrdersError.value =
                error?.response?.data?.detail || 'Не удалось загрузить кадровые изменения';
            console.error(error);
        } finally {
            employeeChangeOrdersLoading.value = false;
        }
    }

    async function handleCreateEmployeeChangeOrder() {
        if (!activeEmployee.value?.id || !canManageEmployeeChangeOrders.value) {
            return;
        }
        if (!employeeChangeOrderForm.effectiveDate) {
            toast.error('Укажите дату вступления в силу');
            return;
        }

        const hasAnyChange = Boolean(
            employeeChangeOrderForm.changePosition ||
            employeeChangeOrderForm.changeWorkplaceRestaurant ||
            employeeChangeOrderForm.changeIndividualRate,
        );
        if (!hasAnyChange) {
            toast.error('Выберите хотя бы одно кадровое изменение');
            return;
        }

        if (employeeChangeOrderForm.changePosition && !employeeChangeOrderForm.positionIdNew) {
            toast.error('Выберите новую должность');
            return;
        }

        if (employeeChangeOrderForm.changeIndividualRate && !canManageRateChanges.value) {
            toast.error('Нет доступа к изменению ставок для этого сотрудника');
            return;
        }

        const shouldClearIndividualRate = Boolean(employeeChangeOrderForm.clearIndividualRate);
        const individualRateNew = employeeChangeOrderForm.changeIndividualRate && !shouldClearIndividualRate
            ? parseOptionalNumber(employeeChangeOrderForm.individualRateNew)
            : null;
        if (
            employeeChangeOrderForm.changeIndividualRate &&
            !shouldClearIndividualRate &&
            !Number.isFinite(individualRateNew)
        ) {
            toast.error('Укажите корректную индивидуальную ставку');
            return;
        }

        savingEmployeeChangeOrder.value = true;
        try {
            const payload = {
                effective_date: employeeChangeOrderForm.effectiveDate,
                change_position: Boolean(employeeChangeOrderForm.changePosition),
                position_id_new: employeeChangeOrderForm.changePosition
                    ? Number(employeeChangeOrderForm.positionIdNew)
                    : null,
                change_workplace_restaurant: Boolean(employeeChangeOrderForm.changeWorkplaceRestaurant),
                workplace_restaurant_id_new: employeeChangeOrderForm.changeWorkplaceRestaurant
                    ? (employeeChangeOrderForm.workplaceRestaurantIdNew
                        ? Number(employeeChangeOrderForm.workplaceRestaurantIdNew)
                        : null)
                    : null,
                change_rate: false,
                rate_new: null,
                change_individual_rate: Boolean(employeeChangeOrderForm.changeIndividualRate),
                individual_rate_new: employeeChangeOrderForm.changeIndividualRate
                    ? (shouldClearIndividualRate ? null : individualRateNew)
                    : null,
                apply_to_attendances: Boolean(employeeChangeOrderForm.applyToAttendances),
                comment: employeeChangeOrderForm.comment.trim() || null,
            };
            await createEmployeeChangeOrder(activeEmployee.value.id, payload);
            toast.success('Кадровое изменение сохранено');
            closeEmployeeChangeOrderForm();
            await loadEmployeeChangeOrders();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось сохранить кадровое изменение');
            console.error(error);
        } finally {
            savingEmployeeChangeOrder.value = false;
        }
    }

    async function handleCancelEmployeeChangeOrder(orderId) {
        if (!activeEmployee.value?.id || !orderId || !canManageEmployeeChangeOrders.value) {
            return;
        }
        cancellingEmployeeChangeOrderId.value = orderId;
        try {
            await cancelEmployeeChangeOrder(activeEmployee.value.id, orderId);
            toast.success('Кадровое изменение отменено');
            await loadEmployeeChangeOrders();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось отменить кадровое изменение');
            console.error(error);
        } finally {
            cancellingEmployeeChangeOrderId.value = null;
        }
    }

    function resetEmployeeChangeOrdersState() {
        employeeChangeOrders.value = [];
        employeeChangeOrdersLoading.value = false;
        employeeChangeOrdersError.value = '';
        cancellingEmployeeChangeOrderId.value = null;
        closeEmployeeChangeOrderForm();
    }

    return {
        employeeChangeOrders,
        employeeChangeOrdersLoading,
        employeeChangeOrdersError,
        isEmployeeChangeOrderFormOpen,
        savingEmployeeChangeOrder,
        cancellingEmployeeChangeOrderId,
        employeeChangeOrderForm,
        canManageRateChanges,
        openEmployeeChangeOrderForm,
        closeEmployeeChangeOrderForm,
        updateEmployeeChangeOrderFormField,
        loadEmployeeChangeOrders,
        handleCreateEmployeeChangeOrder,
        handleCancelEmployeeChangeOrder,
        resetEmployeeChangeOrdersState,
    };
}
