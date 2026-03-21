import { computed, reactive, ref, watch } from 'vue';
import { useToast } from 'vue-toastification';
import {
    createPositionTrainingRequirement,
    createTrainingEventRecord,
    deleteTrainingEventRecord,
    fetchTrainingEventRecords,
    fetchTrainingEventTypes,
    fetchTrainingRequirementSuggestions,
    updatePositionTrainingRequirement,
    updateTrainingEventRecord,
} from '@/api';
import { extractApiErrorMessage } from '@/utils/apiErrors';

export function useEmployeeTrainings({
    activeEmployee,
    employeeCard,
    formatDateInput,
}) {
    const toast = useToast();

    const employeeTrainings = ref([]);
    const trainingsLoading = ref(false);
    const trainingEventTypes = ref([]);
    const trainingTypesLoading = ref(false);
    const trainingForm = reactive({
        eventTypeId: null,
        date: formatDateInput(new Date()),
        comment: '',
    });
    const creatingTrainingRecord = ref(false);
    const isTrainingAssignmentModalOpen = ref(false);
    const editingTrainingRecord = reactive({
        id: null,
        eventTypeId: null,
        date: '',
        comment: '',
    });
    const updatingTrainingRecord = ref(false);
    const deletingTrainingRecordId = ref(null);
    const trainingRequirementSuggestions = ref([]);
    const trainingRequirementsLoading = ref(false);
    const updatingTrainingRequirementId = ref(null);

    const trainingTypeOptions = computed(() =>
        trainingEventTypes.value.map((type) => ({
            value: String(type.id),
            label: type.name,
        })),
    );

    async function loadTrainingEventTypes() {
        trainingTypesLoading.value = true;
        try {
            const data = await fetchTrainingEventTypes();
            let list = [];
            if (Array.isArray(data?.items)) {
                list = data.items;
            } else if (Array.isArray(data)) {
                list = data;
            }
            trainingEventTypes.value = list.sort((a, b) =>
                a.name.localeCompare(b.name, 'ru', { sensitivity: 'base' }),
            );
        } catch (error) {
            toast.error(extractApiErrorMessage(error, 'Не удалось выполнить операцию'));
            console.error(error);
        } finally {
            trainingTypesLoading.value = false;
        }
    }

    async function loadEmployeeTrainings() {
        if (!activeEmployee.value) {
            return;
        }
        trainingsLoading.value = true;
        try {
            const data = await fetchTrainingEventRecords({ user_id: activeEmployee.value.id });
            let list = [];
            if (Array.isArray(data?.items)) {
                list = data.items;
            } else if (Array.isArray(data)) {
                list = data;
            }

            employeeTrainings.value = list.sort((a, b) => {
                const dateA = new Date(a.date).getTime();
                const dateB = new Date(b.date).getTime();
                if (Number.isNaN(dateA) && Number.isNaN(dateB)) {
                    return 0;
                }
                if (Number.isNaN(dateA)) {
                    return 1;
                }
                if (Number.isNaN(dateB)) {
                    return -1;
                }
                return dateB - dateA;
            });

            if (
                editingTrainingRecord.id &&
                !employeeTrainings.value.some((item) => item.id === editingTrainingRecord.id)
            ) {
                cancelEditTrainingRecord();
            }
        } catch (error) {
            toast.error(extractApiErrorMessage(error, 'Не удалось выполнить операцию'));
            console.error(error);
        } finally {
            trainingsLoading.value = false;
        }
    }

    async function loadTrainingRequirements() {
        const positionId = activeEmployee.value?.position_id || employeeCard.value?.position_id;
        if (!positionId) {
            trainingRequirementSuggestions.value = [];
            return;
        }
        trainingRequirementsLoading.value = true;
        try {
            const data = await fetchTrainingRequirementSuggestions(positionId, activeEmployee.value?.id);
            if (Array.isArray(data?.items)) {
                trainingRequirementSuggestions.value = data.items;
            } else if (Array.isArray(data)) {
                trainingRequirementSuggestions.value = data;
            } else {
                trainingRequirementSuggestions.value = [];
            }
        } catch (error) {
            const detail = error?.response?.data?.detail;
            trainingRequirementSuggestions.value = [];
            console.error(error);
            toast.error(detail || 'Не удалось выполнить операцию');
        } finally {
            trainingRequirementsLoading.value = false;
        }
    }

    async function toggleTrainingRequirement(eventTypeId, required) {
        const positionId = activeEmployee.value?.position_id || employeeCard.value?.position_id;
        if (!positionId) {
            toast.error('Не удалось выполнить операцию');
            return;
        }
        const suggestion = trainingRequirementSuggestions.value.find(
            (item) => item.event_type_id === eventTypeId,
        );
        if (!suggestion && !required) {
            return;
        }

        updatingTrainingRequirementId.value = eventTypeId;
        try {
            if (suggestion?.requirement_id) {
                await updatePositionTrainingRequirement(suggestion.requirement_id, { required });
            } else if (required) {
                await createPositionTrainingRequirement({
                    position_id: positionId,
                    event_type_id: eventTypeId,
                    required,
                });
            }
            await loadTrainingRequirements();
            toast.success('Требования по тренингу обновлены');
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            updatingTrainingRequirementId.value = null;
        }
    }

    function openTrainingAssignmentModal() {
        isTrainingAssignmentModalOpen.value = true;
    }

    function closeTrainingAssignmentModal() {
        isTrainingAssignmentModalOpen.value = false;
    }

    async function handleCreateTrainingRecord(formValues = trainingForm) {
        if (!activeEmployee.value) {
            return;
        }

        const eventTypeId = Number(formValues?.eventTypeId);
        if (!Number.isFinite(eventTypeId) || eventTypeId <= 0) {
            toast.error('Выберите тип тренинга');
            return;
        }

        const trainingDate = typeof formValues?.date === 'string' ? formValues.date.trim() : '';
        if (!trainingDate) {
            toast.error('Укажите дату тренинга');
            return;
        }

        const comment =
            typeof formValues?.comment === 'string'
                ? formValues.comment.trim()
                : '';

        creatingTrainingRecord.value = true;
        try {
            const payload = {
                user_id: activeEmployee.value.id,
                event_type_id: eventTypeId,
                date: trainingDate,
                comment: comment || null,
            };
            await createTrainingEventRecord(payload);
            toast.success('Тренинг назначен');
            closeTrainingAssignmentModal();
            trainingForm.comment = '';
            await loadEmployeeTrainings();
            await loadTrainingRequirements();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            creatingTrainingRecord.value = false;
        }
    }

    function startEditTrainingRecord(record) {
        closeTrainingAssignmentModal();
        editingTrainingRecord.id = record.id;
        editingTrainingRecord.eventTypeId = record.event_type_id ? String(record.event_type_id) : null;
        editingTrainingRecord.date = record.date || '';
        editingTrainingRecord.comment = record.comment || '';
    }

    function cancelEditTrainingRecord() {
        editingTrainingRecord.id = null;
        editingTrainingRecord.eventTypeId = null;
        editingTrainingRecord.date = '';
        editingTrainingRecord.comment = '';
        updatingTrainingRecord.value = false;
    }

    async function handleUpdateTrainingRecord() {
        if (!editingTrainingRecord.id) {
            return;
        }
        if (!activeEmployee.value || !editingTrainingRecord.eventTypeId || !editingTrainingRecord.date) {
            toast.error('Не удалось выполнить операцию');
            return;
        }

        updatingTrainingRecord.value = true;
        try {
            const payload = {
                user_id: activeEmployee.value.id,
                event_type_id: Number(editingTrainingRecord.eventTypeId),
                date: editingTrainingRecord.date,
                comment: editingTrainingRecord.comment ? editingTrainingRecord.comment.trim() : null,
            };
            await updateTrainingEventRecord(editingTrainingRecord.id, payload);
            toast.success('Тренинг обновлен');
            cancelEditTrainingRecord();
            await loadEmployeeTrainings();
            await loadTrainingRequirements();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            updatingTrainingRecord.value = false;
        }
    }

    async function handleDeleteTrainingRecord(recordId) {
        if (!recordId) {
            return;
        }
        deletingTrainingRecordId.value = recordId;
        try {
            await deleteTrainingEventRecord(recordId);
            toast.success('Запись удалена');
            if (editingTrainingRecord.id === recordId) {
                cancelEditTrainingRecord();
            }
            await loadEmployeeTrainings();
            await loadTrainingRequirements();
        } catch (error) {
            const detail = error?.response?.data?.detail;
            toast.error(detail || 'Не удалось выполнить операцию');
            console.error(error);
        } finally {
            deletingTrainingRecordId.value = null;
        }
    }

    function resetEmployeeTrainingsState() {
        trainingForm.comment = '';
        trainingForm.date = formatDateInput(new Date());
        employeeTrainings.value = [];
        trainingRequirementSuggestions.value = [];
        trainingsLoading.value = false;
        trainingRequirementsLoading.value = false;
        creatingTrainingRecord.value = false;
        deletingTrainingRecordId.value = null;
        updatingTrainingRequirementId.value = null;
        closeTrainingAssignmentModal();
        cancelEditTrainingRecord();
    }

    watch(
        trainingEventTypes,
        (list) => {
            if (!Array.isArray(list) || list.length === 0) {
                trainingForm.eventTypeId = null;
                return;
            }
            const hasCurrent = list.some((item) => String(item.id) === trainingForm.eventTypeId);
            if (!hasCurrent) {
                trainingForm.eventTypeId = String(list[0].id);
            }
        },
        { immediate: true },
    );

    return {
        employeeTrainings,
        trainingsLoading,
        trainingEventTypes,
        trainingTypesLoading,
        trainingForm,
        creatingTrainingRecord,
        isTrainingAssignmentModalOpen,
        editingTrainingRecord,
        updatingTrainingRecord,
        deletingTrainingRecordId,
        trainingRequirementSuggestions,
        trainingRequirementsLoading,
        updatingTrainingRequirementId,
        trainingTypeOptions,
        loadTrainingEventTypes,
        loadEmployeeTrainings,
        loadTrainingRequirements,
        toggleTrainingRequirement,
        openTrainingAssignmentModal,
        closeTrainingAssignmentModal,
        handleCreateTrainingRecord,
        startEditTrainingRecord,
        cancelEditTrainingRecord,
        handleUpdateTrainingRecord,
        handleDeleteTrainingRecord,
        resetEmployeeTrainingsState,
    };
}
