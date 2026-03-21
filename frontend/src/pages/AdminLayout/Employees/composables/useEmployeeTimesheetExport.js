import { computed, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';
import { exportTimesheetReport, fetchTimesheetOptions } from '@/api';
import { useMultiSelect } from '@/composables/useMultiSelect';
import { extractApiErrorMessage } from '@/utils/apiErrors';
import { downloadBlobFile } from '@/utils/downloadBlobFile';

function createEmptyTimesheetOptions() {
    return { restaurants: [], subdivisions: [], positions: [] };
}

export function useEmployeeTimesheetExport({ formatDateInput }) {
    const toast = useToast();
    const { toggleMultiValue, keepAllowedValues } = useMultiSelect();

    const isTimesheetExportModalOpen = ref(false);
    const timesheetExporting = ref(false);
    const timesheetOptionsLoading = ref(false);
    const timesheetOptions = ref(createEmptyTimesheetOptions());
    const isTimesheetSubdivisionPanelOpen = ref(true);
    const isTimesheetPositionPanelOpen = ref(true);

    const timesheetExportForm = reactive({
        restaurantId: '',
        dateFrom: '',
        dateTo: '',
        subdivisionIds: [],
        positionIds: [],
    });

    const timesheetRestaurantOptions = computed(() =>
        Array.isArray(timesheetOptions.value?.restaurants)
            ? timesheetOptions.value.restaurants
                  .map((restaurant) => ({
                      value: String(restaurant.id),
                      label: restaurant.name || `ID ${restaurant.id}`,
                  }))
                  .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' }))
            : []
    );

    const timesheetSubdivisionOptions = computed(() =>
        Array.isArray(timesheetOptions.value?.subdivisions)
            ? timesheetOptions.value.subdivisions
                  .map((subdivision) => ({
                      id: subdivision.id,
                      label: subdivision.name || `ID ${subdivision.id}`,
                  }))
                  .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' }))
            : []
    );

    const timesheetPositionOptions = computed(() =>
        Array.isArray(timesheetOptions.value?.positions)
            ? timesheetOptions.value.positions
                  .map((position) => ({
                      id: position.id,
                      label: position.name || `ID ${position.id}`,
                      subdivisionId: position.restaurant_subdivision_id || null,
                  }))
                  .sort((a, b) => a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' }))
            : []
    );

    const timesheetPositionOptionsFiltered = computed(() => {
        if (!timesheetExportForm.subdivisionIds.length) {
            return timesheetPositionOptions.value;
        }
        const filterIds = new Set(timesheetExportForm.subdivisionIds);
        return timesheetPositionOptions.value.filter(
            (item) => item.subdivisionId && filterIds.has(item.subdivisionId)
        );
    });

    const timesheetSubdivisionAll = computed(() => timesheetExportForm.subdivisionIds.length === 0);
    const timesheetPositionAll = computed(() => timesheetExportForm.positionIds.length === 0);

    const timesheetSubdivisionSelectionLabel = computed(() => {
        const count = timesheetExportForm.subdivisionIds.length;
        return count ? `выбрано: ${count}` : 'все';
    });

    const timesheetPositionSelectionLabel = computed(() => {
        const count = timesheetExportForm.positionIds.length;
        return count ? `выбрано: ${count}` : 'все';
    });

    function resetTimesheetExportForm() {
        const now = new Date();
        const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
        const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        timesheetExportForm.dateFrom = formatDateInput(firstDay);
        timesheetExportForm.dateTo = formatDateInput(lastDay);
        timesheetExportForm.restaurantId = '';
        timesheetExportForm.subdivisionIds = [];
        timesheetExportForm.positionIds = [];
    }

    function syncTimesheetRestaurantDefault() {
        if (timesheetExportForm.restaurantId) {
            const exists = timesheetRestaurantOptions.value.some(
                (item) => String(item.value) === String(timesheetExportForm.restaurantId)
            );
            if (exists) {
                return;
            }
        }
        const first = timesheetRestaurantOptions.value[0];
        timesheetExportForm.restaurantId = first ? String(first.value) : '';
    }

    async function loadTimesheetOptions() {
        timesheetOptionsLoading.value = true;
        try {
            const data = await fetchTimesheetOptions();
            timesheetOptions.value = data || createEmptyTimesheetOptions();
        } catch (error) {
            toast.error(extractApiErrorMessage(error, 'Не удалось загрузить параметры табеля'));
            console.error(error);
            timesheetOptions.value = createEmptyTimesheetOptions();
        } finally {
            timesheetOptionsLoading.value = false;
            syncTimesheetRestaurantDefault();
        }
    }

    async function openTimesheetExportModal() {
        resetTimesheetExportForm();
        isTimesheetSubdivisionPanelOpen.value = true;
        isTimesheetPositionPanelOpen.value = true;
        isTimesheetExportModalOpen.value = true;
        await loadTimesheetOptions();
    }

    function closeTimesheetExportModal() {
        isTimesheetExportModalOpen.value = false;
        timesheetExporting.value = false;
    }

    function toggleTimesheetSubdivisionPanel() {
        isTimesheetSubdivisionPanelOpen.value = !isTimesheetSubdivisionPanelOpen.value;
    }

    function toggleTimesheetPositionPanel() {
        isTimesheetPositionPanelOpen.value = !isTimesheetPositionPanelOpen.value;
    }

    function handleTimesheetSubdivisionAll(checked) {
        if (checked) {
            timesheetExportForm.subdivisionIds = [];
        }
    }

    function toggleTimesheetSubdivision(id, checked) {
        const parsed = Number(id);
        if (!Number.isFinite(parsed)) {
            return;
        }
        toggleMultiValue(timesheetExportForm.subdivisionIds, parsed, checked);
    }

    function handleTimesheetPositionAll(checked) {
        if (checked) {
            timesheetExportForm.positionIds = [];
        }
    }

    function toggleTimesheetPosition(id, checked) {
        const parsed = Number(id);
        if (!Number.isFinite(parsed)) {
            return;
        }
        toggleMultiValue(timesheetExportForm.positionIds, parsed, checked);
    }

    async function handleExportTimesheet() {
        if (!timesheetExportForm.restaurantId) {
            toast.error('Укажите ресторан');
            return;
        }
        if (!timesheetExportForm.dateFrom || !timesheetExportForm.dateTo) {
            toast.error('Укажите период для выгрузки');
            return;
        }
        if (timesheetExportForm.dateFrom > timesheetExportForm.dateTo) {
            toast.error('Дата "с" должна быть меньше или равна дате "по"');
            return;
        }

        const restaurantId = Number(timesheetExportForm.restaurantId);
        if (!Number.isFinite(restaurantId)) {
            toast.error('Некорректный ресторан');
            return;
        }

        const params = {
            restaurant_id: restaurantId,
            date_from: timesheetExportForm.dateFrom,
            date_to: timesheetExportForm.dateTo,
        };

        if (timesheetExportForm.subdivisionIds.length) {
            params.restaurant_subdivision_ids = timesheetExportForm.subdivisionIds;
        }
        if (timesheetExportForm.positionIds.length) {
            params.position_ids = timesheetExportForm.positionIds;
        }

        timesheetExporting.value = true;
        try {
            const blob = await exportTimesheetReport(params);
            const rangeLabel =
                timesheetExportForm.dateFrom === timesheetExportForm.dateTo
                    ? timesheetExportForm.dateFrom
                    : `${timesheetExportForm.dateFrom}_${timesheetExportForm.dateTo}`;
            downloadBlobFile(blob, `timesheet_${rangeLabel}.xlsx`);
            toast.success('Табель смен выгружен');
            closeTimesheetExportModal();
        } catch (error) {
            toast.error(extractApiErrorMessage(error, 'Не удалось выполнить выгрузку'));
            console.error(error);
        } finally {
            timesheetExporting.value = false;
        }
    }

    watch(
        () => timesheetExportForm.subdivisionIds.slice(),
        () => {
            if (!timesheetExportForm.positionIds.length) {
                return;
            }
            timesheetExportForm.positionIds = keepAllowedValues(
                timesheetExportForm.positionIds,
                timesheetPositionOptionsFiltered.value.map((item) => item.id)
            );
        }
    );

    return {
        isTimesheetExportModalOpen,
        timesheetExporting,
        timesheetOptionsLoading,
        timesheetOptions,
        isTimesheetSubdivisionPanelOpen,
        isTimesheetPositionPanelOpen,
        timesheetExportForm,
        timesheetRestaurantOptions,
        timesheetSubdivisionOptions,
        timesheetPositionOptionsFiltered,
        timesheetSubdivisionAll,
        timesheetPositionAll,
        timesheetSubdivisionSelectionLabel,
        timesheetPositionSelectionLabel,
        loadTimesheetOptions,
        openTimesheetExportModal,
        closeTimesheetExportModal,
        toggleTimesheetSubdivisionPanel,
        toggleTimesheetPositionPanel,
        handleTimesheetSubdivisionAll,
        toggleTimesheetSubdivision,
        handleTimesheetPositionAll,
        toggleTimesheetPosition,
        handleExportTimesheet,
    };
}
