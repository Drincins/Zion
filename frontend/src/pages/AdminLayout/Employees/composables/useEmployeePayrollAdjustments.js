import { computed, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';
import {
    createPayrollAdjustment,
    deletePayrollAdjustment,
    fetchPayrollAdjustmentTypes,
    fetchPayrollAdjustments,
    updatePayrollAdjustment,
} from '@/api';

export function useEmployeePayrollAdjustments({
    activeEmployee,
    userStore,
    formatDateInput,
    payrollRestaurantOptions,
}) {
    const toast = useToast();

    const payrollAdjustmentTypes = ref([]);
    const payrollAdjustmentTypesLoading = ref(false);
    const payrollAdjustments = ref([]);
    const payrollAdjustmentsLoading = ref(false);
    const isPayrollAdjustmentFormVisible = ref(false);
    const creatingPayrollAdjustment = ref(false);
    const editingPayrollAdjustment = reactive({
        id: null,
        adjustmentTypeId: null,
        amount: '',
        date: '',
        restaurantId: null,
        responsibleId: null,
        comment: '',
    });
    const updatingPayrollAdjustment = ref(false);
    const deletingPayrollAdjustmentId = ref(null);
    const newPayrollAdjustment = reactive({
        adjustmentTypeId: null,
        restaurantId: null,
        amount: '',
        date: formatDateInput(new Date()),
        responsibleId: null,
        comment: '',
    });

    const payrollAdjustmentTypeOptions = computed(() =>
        payrollAdjustmentTypes.value.map((type) => ({
            value: String(type.id),
            label: type.name,
        })),
    );

    async function loadPayrollAdjustmentTypes() {
        payrollAdjustmentTypesLoading.value = true;
        try {
            const data = await fetchPayrollAdjustmentTypes();
            if (Array.isArray(data?.items)) {
                payrollAdjustmentTypes.value = data.items;
            } else if (Array.isArray(data)) {
                payrollAdjustmentTypes.value = data;
            } else {
                payrollAdjustmentTypes.value = [];
            }
            payrollAdjustmentTypes.value.sort((a, b) =>
                a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }),
            );
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            payrollAdjustmentTypesLoading.value = false;
        }
    }

    async function loadEmployeePayrollAdjustments() {
        if (!activeEmployee.value) return;
        payrollAdjustmentsLoading.value = true;
        try {
            const data = await fetchPayrollAdjustments({ user_id: activeEmployee.value.id });
            payrollAdjustments.value = Array.isArray(data?.items) ? data.items : [];
            if (
                editingPayrollAdjustment.id &&
                !payrollAdjustments.value.some((item) => item.id === editingPayrollAdjustment.id)
            ) {
                cancelEditPayrollAdjustment();
            }
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            payrollAdjustmentsLoading.value = false;
        }
    }

    function resetPayrollAdjustmentForm() {
        newPayrollAdjustment.adjustmentTypeId = payrollAdjustmentTypes.value.length
            ? String(payrollAdjustmentTypes.value[0].id)
            : null;
        newPayrollAdjustment.restaurantId = payrollRestaurantOptions.value.length
            ? String(payrollRestaurantOptions.value[0].value)
            : null;
        newPayrollAdjustment.amount = '';
        newPayrollAdjustment.date = formatDateInput(new Date());
        newPayrollAdjustment.responsibleId = userStore.id ? String(userStore.id) : null;
        newPayrollAdjustment.comment = '';
    }

    function openPayrollAdjustmentForm() {
        if (!payrollAdjustmentTypes.value.length && !payrollAdjustmentTypesLoading.value) {
            loadPayrollAdjustmentTypes();
        }
        cancelEditPayrollAdjustment();
        resetPayrollAdjustmentForm();
        isPayrollAdjustmentFormVisible.value = true;
    }

    function closePayrollAdjustmentForm() {
        isPayrollAdjustmentFormVisible.value = false;
    }

    function startEditPayrollAdjustment(adjustment) {
        if (!adjustment || !adjustment.id) {
            return;
        }
        if (adjustment.amount === null || adjustment.amount === undefined) {
            toast.error('Нет доступа к финансовым данным');
            return;
        }
        isPayrollAdjustmentFormVisible.value = false;
        editingPayrollAdjustment.id = adjustment.id;
        const rawTypeId =
            adjustment.adjustment_type_id ??
            adjustment.adjustment_type?.id ??
            null;
        editingPayrollAdjustment.adjustmentTypeId = rawTypeId ? String(rawTypeId) : null;
        editingPayrollAdjustment.amount =
            adjustment.amount !== null && adjustment.amount !== undefined
                ? String(adjustment.amount)
                : '';
        editingPayrollAdjustment.date = adjustment.date || '';
        editingPayrollAdjustment.restaurantId = adjustment.restaurant_id
            ? String(adjustment.restaurant_id)
            : adjustment.restaurant?.id
            ? String(adjustment.restaurant.id)
            : null;
        editingPayrollAdjustment.responsibleId = adjustment.responsible_id
            ? String(adjustment.responsible_id)
            : null;
        editingPayrollAdjustment.comment = adjustment.comment || '';
    }

    function cancelEditPayrollAdjustment() {
        editingPayrollAdjustment.id = null;
        editingPayrollAdjustment.adjustmentTypeId = null;
        editingPayrollAdjustment.amount = '';
        editingPayrollAdjustment.date = '';
        editingPayrollAdjustment.restaurantId = null;
        editingPayrollAdjustment.responsibleId = null;
        editingPayrollAdjustment.comment = '';
        updatingPayrollAdjustment.value = false;
    }

    async function handleUpdatePayrollAdjustment() {
        if (!editingPayrollAdjustment.id) {
            return;
        }
        const typeId = Number(editingPayrollAdjustment.adjustmentTypeId);
        if (!Number.isFinite(typeId) || typeId <= 0) {
            toast.error('Не удалось выполнить операцию');
            return;
        }

        const restaurantId = Number(editingPayrollAdjustment.restaurantId);
        if (!Number.isFinite(restaurantId) || restaurantId <= 0) {
            toast.error('Не удалось выполнить операцию');
            return;
        }

        const amountRaw = editingPayrollAdjustment.amount;
        const amount =
            typeof amountRaw === 'number'
                ? amountRaw
                : parseFloat(String(amountRaw).replace(',', '.'));
        if (!Number.isFinite(amount)) {
            toast.error('Не удалось выполнить операцию');
            return;
        }

        if (!editingPayrollAdjustment.date) {
            toast.error('Не удалось выполнить операцию');
            return;
        }

        const responsibleId = editingPayrollAdjustment.responsibleId
            ? Number(editingPayrollAdjustment.responsibleId)
            : null;
        if (responsibleId !== null && !Number.isFinite(responsibleId)) {
            toast.error('Не удалось выполнить операцию');
            return;
        }

        const comment =
            typeof editingPayrollAdjustment.comment === 'string'
                ? editingPayrollAdjustment.comment.trim()
                : '';

        updatingPayrollAdjustment.value = true;
        try {
            const payload = {
                adjustment_type_id: typeId,
                amount: Math.round(amount * 100) / 100,
                date: editingPayrollAdjustment.date,
                restaurant_id: restaurantId,
                responsible_id: responsibleId,
                comment: comment || null,
            };
            await updatePayrollAdjustment(editingPayrollAdjustment.id, payload);
            toast.success('Изменения сохранены');
            cancelEditPayrollAdjustment();
            await loadEmployeePayrollAdjustments();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            updatingPayrollAdjustment.value = false;
        }
    }

    async function handleDeletePayrollAdjustment(adjustmentId) {
        if (!adjustmentId) {
            return;
        }
        deletingPayrollAdjustmentId.value = adjustmentId;
        try {
            await deletePayrollAdjustment(adjustmentId);
            toast.success('Запись удалена');
            if (editingPayrollAdjustment.id === adjustmentId) {
                cancelEditPayrollAdjustment();
            }
            await loadEmployeePayrollAdjustments();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            deletingPayrollAdjustmentId.value = null;
        }
    }

    async function handleCreatePayrollAdjustment(formValues = newPayrollAdjustment) {
        if (!activeEmployee.value) {
            return;
        }

        const typeId = Number(formValues?.adjustmentTypeId);
        if (!Number.isFinite(typeId) || typeId <= 0) {
            toast.error('Выберите тип операции');
            return;
        }

        const restaurantId = Number(formValues?.restaurantId);
        if (!Number.isFinite(restaurantId) || restaurantId <= 0) {
            toast.error('Выберите ресторан');
            return;
        }

        const amountRaw = formValues?.amount;
        const amount = typeof amountRaw === 'number' ? amountRaw : parseFloat(String(amountRaw ?? '').replace(',', '.'));
        if (!Number.isFinite(amount) || amount <= 0) {
            toast.error('Укажите корректную сумму');
            return;
        }

        const adjustmentDate = typeof formValues?.date === 'string' ? formValues.date.trim() : '';
        if (!adjustmentDate) {
            toast.error('Укажите дату');
            return;
        }

        const responsibleId = formValues?.responsibleId
            ? Number(formValues.responsibleId)
            : null;
        if (responsibleId !== null && !Number.isFinite(responsibleId)) {
            toast.error('Некорректный ответственный');
            return;
        }

        const comment =
            typeof formValues?.comment === 'string'
                ? formValues.comment.trim()
                : '';

        creatingPayrollAdjustment.value = true;
        try {
            const payload = {
                user_id: activeEmployee.value.id,
                adjustment_type_id: typeId,
                amount: Math.round(amount * 100) / 100,
                date: adjustmentDate,
                restaurant_id: restaurantId,
                responsible_id: responsibleId,
                comment: comment || null,
            };
            const created = await createPayrollAdjustment(payload);
            if (!created?.id) {
                throw new Error('Не удалось создать запись');
            }
            toast.success('Запись создана');
            closePayrollAdjustmentForm();
            await loadEmployeePayrollAdjustments();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            creatingPayrollAdjustment.value = false;
        }
    }

    function resetEmployeePayrollState() {
        payrollAdjustments.value = [];
        isPayrollAdjustmentFormVisible.value = false;
        creatingPayrollAdjustment.value = false;
        cancelEditPayrollAdjustment();
    }

    watch(
        payrollAdjustmentTypes,
        (list) => {
            if (!isPayrollAdjustmentFormVisible.value) {
                return;
            }
            if (!Array.isArray(list) || list.length === 0) {
                newPayrollAdjustment.adjustmentTypeId = null;
                return;
            }
            const hasCurrent = list.some(
                (item) => String(item.id) === newPayrollAdjustment.adjustmentTypeId,
            );
            if (!hasCurrent) {
                newPayrollAdjustment.adjustmentTypeId = String(list[0].id);
            }
        },
    );

    return {
        payrollAdjustmentTypes,
        payrollAdjustmentTypesLoading,
        payrollAdjustments,
        payrollAdjustmentsLoading,
        isPayrollAdjustmentFormVisible,
        creatingPayrollAdjustment,
        editingPayrollAdjustment,
        updatingPayrollAdjustment,
        deletingPayrollAdjustmentId,
        newPayrollAdjustment,
        payrollAdjustmentTypeOptions,
        loadPayrollAdjustmentTypes,
        loadEmployeePayrollAdjustments,
        openPayrollAdjustmentForm,
        closePayrollAdjustmentForm,
        startEditPayrollAdjustment,
        cancelEditPayrollAdjustment,
        handleUpdatePayrollAdjustment,
        handleDeletePayrollAdjustment,
        handleCreatePayrollAdjustment,
        resetEmployeePayrollState,
    };
}

