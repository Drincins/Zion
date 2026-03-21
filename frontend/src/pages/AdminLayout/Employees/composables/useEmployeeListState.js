import { computed, ref, watch } from 'vue';

export function useEmployeeListState({
    canViewSensitiveStaffFields,
    getEmployeeColumns,
    onMinColumnsError
}) {
    const employeeColumnOptions = computed(() =>
        getEmployeeColumns(canViewSensitiveStaffFields.value)
    );
    const selectedEmployeeColumns = ref([]);
    watch(
        employeeColumnOptions,
        (options) => {
            const availableIds = options.map((option) => option.id);
            const filteredSelected = selectedEmployeeColumns.value.filter((id) =>
                availableIds.includes(id)
            );

            selectedEmployeeColumns.value = filteredSelected.length
                ? filteredSelected
                : availableIds;
        },
        { immediate: true }
    );

    const search = ref('');
    const onlyFired = ref(false);
    const onlyFormalized = ref(false);
    const onlyNotFormalized = ref(false);
    const onlyCis = ref(false);
    const sortBy = ref('staff_code');
    const sortDirection = ref('asc');
    const isFiltersOpen = ref(false);
    const isColumnSelectorOpen = ref(false);

    const handleSearchChange = (value) => {
        search.value = value;
    };

    const handleOnlyFiredChange = (value) => {
        onlyFired.value = value;
    };

    const handleOnlyFormalizedChange = (value) => {
        onlyFormalized.value = value;
        if (value) {
            onlyNotFormalized.value = false;
        }
    };

    const handleOnlyNotFormalizedChange = (value) => {
        onlyNotFormalized.value = value;
        if (value) {
            onlyFormalized.value = false;
        }
    };

    const handleOnlyCisChange = (value) => {
        onlyCis.value = value;
    };

    const handleSortByChange = (value) => {
        sortBy.value = value;
    };

    const handleSortDirectionChange = (value) => {
        sortDirection.value = value;
    };

    function handleEmployeeColumnChange(columnId, checked) {
        if (!columnId) {
            return;
        }
        if (checked) {
            if (!selectedEmployeeColumns.value.includes(columnId)) {
                selectedEmployeeColumns.value = [...selectedEmployeeColumns.value, columnId];
            }
            return;
        }
        if (selectedEmployeeColumns.value.length <= 1) {
            if (typeof onMinColumnsError === 'function') {
                onMinColumnsError();
            }
            return;
        }
        selectedEmployeeColumns.value = selectedEmployeeColumns.value.filter(
            (column) => column !== columnId
        );
    }

    function toggleFilters() {
        isFiltersOpen.value = !isFiltersOpen.value;
    }

    function toggleColumnSelector() {
        isColumnSelectorOpen.value = !isColumnSelectorOpen.value;
    }

    return {
        employeeColumnOptions,
        selectedEmployeeColumns,
        search,
        onlyFired,
        onlyFormalized,
        onlyNotFormalized,
        onlyCis,
        sortBy,
        sortDirection,
        isFiltersOpen,
        isColumnSelectorOpen,
        handleSearchChange,
        handleOnlyFiredChange,
        handleOnlyFormalizedChange,
        handleOnlyNotFormalizedChange,
        handleOnlyCisChange,
        handleSortByChange,
        handleSortDirectionChange,
        handleEmployeeColumnChange,
        toggleFilters,
        toggleColumnSelector
    };
}
