import { computed, reactive, ref } from 'vue';
import { useToast } from 'vue-toastification';
import {
    createEmployeeAttendance,
    deleteEmployeeAttendance,
    fetchEmployeeAttendances,
    recalculateEmployeeNightMinutes,
    updateEmployeeAttendance,
} from '@/api';

export function useEmployeeAttendances({
    activeEmployee,
    employeeCard,
    formatMinutesTotal,
    toMinutesValue,
}) {
    const toast = useToast();

    const employeeAttendances = reactive({ items: [], date_from: null, date_to: null });
    const reversedAttendances = computed(() => {
        if (!Array.isArray(employeeAttendances.items)) {
            return [];
        }
        return [...employeeAttendances.items].reverse();
    });
    const attendanceSummary = computed(() => {
        const items = reversedAttendances.value;
        if (!items.length) {
            return null;
        }

        let totalMinutes = 0;
        let nightMinutes = 0;
        for (const attendance of items) {
            totalMinutes += toMinutesValue(attendance?.duration_minutes);
            nightMinutes += toMinutesValue(attendance?.night_minutes);
        }

        return {
            shiftCount: items.length,
            totalDuration: formatMinutesTotal(totalMinutes),
            nightDuration: formatMinutesTotal(nightMinutes),
        };
    });
    const attendanceRateHidden = computed(() =>
        Boolean(employeeCard.value?.rate_hidden ?? activeEmployee.value?.rate_hidden),
    );
    const attendancesLoading = ref(false);
    const attendanceDateFrom = ref('');
    const attendanceDateTo = ref('');
    const recalculatingNightMinutes = ref(false);
    const isAttendanceEditModalOpen = ref(false);
    const isCreatingAttendance = ref(false);
    const editingAttendance = ref(null);
    const updatingAttendance = ref(false);
    const deletingAttendance = ref(false);
    const attendanceForm = reactive({
        openDate: '',
        openTime: '',
        restaurantId: null,
        positionId: null,
        closeDate: '',
        closeTime: '',
        rate: '',
        durationMinutes: '',
        nightMinutes: '',
    });

    const handleAttendanceDateFromChange = (value) => {
        attendanceDateFrom.value = value;
    };

    const handleAttendanceDateToChange = (value) => {
        attendanceDateTo.value = value;
    };

    async function loadEmployeeAttendances() {
        if (!activeEmployee.value) {
            return;
        }
        attendancesLoading.value = true;
        try {
            const params = {
                date_from: attendanceDateFrom.value || undefined,
                date_to: attendanceDateTo.value || undefined,
            };
            const data = await fetchEmployeeAttendances(activeEmployee.value.id, params);
            employeeAttendances.items = data.items || [];
            employeeAttendances.date_from = data.date_from;
            employeeAttendances.date_to = data.date_to;
            if (!attendanceDateFrom.value && data.date_from) {
                attendanceDateFrom.value = data.date_from;
            }
            if (!attendanceDateTo.value && data.date_to) {
                attendanceDateTo.value = data.date_to;
            }
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            attendancesLoading.value = false;
        }
    }

    function resetAttendanceForm() {
        attendanceForm.openDate = '';
        attendanceForm.openTime = '';
        attendanceForm.restaurantId = null;
        attendanceForm.positionId = null;
        attendanceForm.closeDate = '';
        attendanceForm.closeTime = '';
        attendanceForm.rate = '';
        attendanceForm.durationMinutes = '';
        attendanceForm.nightMinutes = '';
    }

    function prefillAttendanceRateFromEmployee() {
        if (attendanceRateHidden.value) {
            attendanceForm.rate = '';
            return;
        }
        const rateSources = [
            employeeCard.value?.rate,
            activeEmployee.value?.rate,
            activeEmployee.value?.position_rate,
        ];
        for (const rate of rateSources) {
            if (rate !== null && rate !== undefined && rate !== '') {
                attendanceForm.rate = String(rate);
                return;
            }
        }
        attendanceForm.rate = '';
    }

    function openAttendanceEditModal(attendance) {
        if (!attendance) {
            return;
        }
        resetAttendanceForm();
        editingAttendance.value = attendance;
        attendanceForm.openDate = attendance.open_date || '';
        attendanceForm.openTime = attendance.open_time ? attendance.open_time.slice(0, 5) : '';
        attendanceForm.restaurantId =
            attendance.restaurant_id !== null && attendance.restaurant_id !== undefined
                ? Number(attendance.restaurant_id)
                : null;
        attendanceForm.positionId =
            attendance.position_id !== null && attendance.position_id !== undefined
                ? Number(attendance.position_id)
                : activeEmployee.value?.position_id
                ? Number(activeEmployee.value.position_id)
                : null;
        attendanceForm.closeDate = attendance.close_date || '';
        attendanceForm.closeTime = attendance.close_time ? attendance.close_time.slice(0, 5) : '';
        attendanceForm.rate =
            !attendanceRateHidden.value && attendance.rate !== null && attendance.rate !== undefined
                ? String(attendance.rate)
                : '';
        attendanceForm.durationMinutes =
            attendance.duration_minutes !== null && attendance.duration_minutes !== undefined
                ? String(attendance.duration_minutes)
                : '';
        attendanceForm.nightMinutes =
            attendance.night_minutes !== null && attendance.night_minutes !== undefined
                ? String(attendance.night_minutes)
                : '';
        isCreatingAttendance.value = false;
        isAttendanceEditModalOpen.value = true;
    }

    function openAttendanceCreateModal() {
        if (!activeEmployee.value) {
            toast.error('Не удалось выполнить операцию');
            return;
        }
        resetAttendanceForm();
        prefillAttendanceRateFromEmployee();
        attendanceForm.positionId = activeEmployee.value.position_id
            ? Number(activeEmployee.value.position_id)
            : null;
        editingAttendance.value = null;
        isCreatingAttendance.value = true;
        isAttendanceEditModalOpen.value = true;
    }

    function closeAttendanceEditModal() {
        isAttendanceEditModalOpen.value = false;
        isCreatingAttendance.value = false;
        editingAttendance.value = null;
        deletingAttendance.value = false;
        resetAttendanceForm();
    }

    function getTodayDateValue() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function prepareAttendancePayload() {
        const openDate = (attendanceForm.openDate || '').trim();
        const openTime = (attendanceForm.openTime || '').trim();
        if (!openDate || !openTime) {
            toast.error('Не удалось выполнить операцию');
            return null;
        }
        const closeDateValue = (attendanceForm.closeDate || '').trim();
        const closeTimeValue = (attendanceForm.closeTime || '').trim();
        const hasCloseDate = Boolean(closeDateValue);
        const hasCloseTime = Boolean(closeTimeValue);
        if (hasCloseDate !== hasCloseTime) {
            toast.error('Не удалось выполнить операцию');
            return null;
        }
        if (hasCloseDate) {
            const todayDate = getTodayDateValue();
            if (closeDateValue > todayDate) {
                toast.error('Дата закрытия не может быть позже сегодняшней');
                return null;
            }
        }

        const payload = {
            open_date: openDate,
            open_time: openTime,
        };

        const restaurantIdRaw = attendanceForm.restaurantId;
        if (restaurantIdRaw !== null && restaurantIdRaw !== undefined && restaurantIdRaw !== '') {
            const parsedRestaurantId =
                typeof restaurantIdRaw === 'number'
                    ? restaurantIdRaw
                    : Number(String(restaurantIdRaw).trim());
            if (!Number.isFinite(parsedRestaurantId)) {
                toast.error('Не удалось выполнить операцию');
                return null;
            }
            payload.restaurant_id = parsedRestaurantId;
        } else {
            payload.restaurant_id = null;
        }

        const positionIdRaw = attendanceForm.positionId;
        if (positionIdRaw !== null && positionIdRaw !== undefined && positionIdRaw !== '') {
            const parsedPositionId =
                typeof positionIdRaw === 'number' ? positionIdRaw : Number(String(positionIdRaw).trim());
            if (!Number.isFinite(parsedPositionId)) {
                toast.error('Не удалось выполнить операцию');
                return null;
            }
            payload.position_id = parsedPositionId;
        } else {
            payload.position_id = null;
        }

        if (hasCloseDate && hasCloseTime) {
            payload.close_date = closeDateValue;
            payload.close_time = closeTimeValue;
        } else {
            payload.close_date = null;
            payload.close_time = null;
        }

        if (!attendanceRateHidden.value) {
            const rateValue =
                attendanceForm.rate === null || attendanceForm.rate === undefined
                    ? ''
                    : String(attendanceForm.rate).trim();
            if (rateValue !== '') {
                const rate = Number(rateValue.replace(',', '.'));
                if (!Number.isFinite(rate)) {
                    toast.error('Не удалось выполнить операцию');
                    return null;
                }
                payload.rate = rate;
            } else {
                payload.rate = null;
            }
        }

        const isEditing = Boolean(editingAttendance.value);
        const original = editingAttendance.value || {};
        const normalizeTimeValue = (value) => (value ? String(value).slice(0, 5) : '');
        const originalOpenDate = original.open_date ? String(original.open_date) : '';
        const originalOpenTime = normalizeTimeValue(original.open_time);
        const originalCloseDate = original.close_date ? String(original.close_date) : '';
        const originalCloseTime = normalizeTimeValue(original.close_time);
        const openCloseChanged =
            isEditing &&
            (openDate !== originalOpenDate ||
                openTime !== originalOpenTime ||
                closeDateValue !== originalCloseDate ||
                closeTimeValue !== originalCloseTime);

        const durationValue =
            attendanceForm.durationMinutes === null || attendanceForm.durationMinutes === undefined
                ? ''
                : String(attendanceForm.durationMinutes).trim();
        const originalDurationValue =
            original.duration_minutes === null || original.duration_minutes === undefined
                ? ''
                : String(original.duration_minutes).trim();
        if (durationValue !== '') {
            const duration = Number.parseInt(durationValue, 10);
            if (!Number.isFinite(duration) || duration < 0) {
                return null;
            }
            if (!openCloseChanged || durationValue !== originalDurationValue) {
                payload.duration_minutes = duration;
            }
        }

        const nightValue =
            attendanceForm.nightMinutes === null || attendanceForm.nightMinutes === undefined
                ? ''
                : String(attendanceForm.nightMinutes).trim();
        const originalNightValue =
            original.night_minutes === null || original.night_minutes === undefined
                ? ''
                : String(original.night_minutes).trim();
        if (nightValue !== '') {
            const night = Number.parseInt(nightValue, 10);
            if (!Number.isFinite(night) || night < 0) {
                return null;
            }
            if (!openCloseChanged || nightValue !== originalNightValue) {
                payload.night_minutes = night;
            }
        }

        return payload;
    }

    async function handleAttendanceCreate() {
        if (!activeEmployee.value) {
            toast.error('Не удалось выполнить операцию');
            return;
        }
        const payload = prepareAttendancePayload();
        if (!payload) {
            return;
        }

        updatingAttendance.value = true;
        try {
            await createEmployeeAttendance(activeEmployee.value.id, payload);
            toast.success('Смена создана');
            closeAttendanceEditModal();
            await loadEmployeeAttendances();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            updatingAttendance.value = false;
        }
    }

    async function handleAttendanceUpdate() {
        if (!activeEmployee.value || !editingAttendance.value) {
            return;
        }
        const payload = prepareAttendancePayload();
        if (!payload) {
            return;
        }

        updatingAttendance.value = true;
        try {
            await updateEmployeeAttendance(activeEmployee.value.id, editingAttendance.value.id, payload);
            toast.success('Смена обновлена');
            closeAttendanceEditModal();
            await loadEmployeeAttendances();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            updatingAttendance.value = false;
        }
    }

    async function handleAttendanceDelete() {
        if (!activeEmployee.value || !editingAttendance.value || deletingAttendance.value) {
            return;
        }
        deletingAttendance.value = true;
        try {
            await deleteEmployeeAttendance(activeEmployee.value.id, editingAttendance.value.id);
            toast.success('Смена удалена');
            closeAttendanceEditModal();
            await loadEmployeeAttendances();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            deletingAttendance.value = false;
        }
    }

    async function handleAttendanceSubmit() {
        if (isCreatingAttendance.value) {
            await handleAttendanceCreate();
        } else {
            await handleAttendanceUpdate();
        }
    }

    async function handleRecalculateNightMinutes() {
        if (!activeEmployee.value) {
            return;
        }
        recalculatingNightMinutes.value = true;
        try {
            const payload = {};
            if (attendanceDateFrom.value) {
                payload.date_from = attendanceDateFrom.value;
            }
            if (attendanceDateTo.value) {
                payload.date_to = attendanceDateTo.value;
            }
            const data = await recalculateEmployeeNightMinutes(activeEmployee.value.id, payload);
            employeeAttendances.items = data.items || [];
            employeeAttendances.date_from = data.date_from;
            employeeAttendances.date_to = data.date_to;
            toast.success('Ночные часы пересчитаны');
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            recalculatingNightMinutes.value = false;
        }
    }

    function resetEmployeeAttendancesState() {
        employeeAttendances.items = [];
        employeeAttendances.date_from = null;
        employeeAttendances.date_to = null;
        attendanceDateFrom.value = '';
        attendanceDateTo.value = '';
        attendancesLoading.value = false;
        recalculatingNightMinutes.value = false;
        closeAttendanceEditModal();
    }

    return {
        employeeAttendances,
        reversedAttendances,
        attendanceSummary,
        attendanceRateHidden,
        attendancesLoading,
        attendanceDateFrom,
        attendanceDateTo,
        recalculatingNightMinutes,
        isAttendanceEditModalOpen,
        isCreatingAttendance,
        editingAttendance,
        updatingAttendance,
        deletingAttendance,
        attendanceForm,
        handleAttendanceDateFromChange,
        handleAttendanceDateToChange,
        loadEmployeeAttendances,
        openAttendanceEditModal,
        openAttendanceCreateModal,
        closeAttendanceEditModal,
        handleAttendanceSubmit,
        handleAttendanceDelete,
        handleRecalculateNightMinutes,
        resetEmployeeAttendancesState,
    };
}
