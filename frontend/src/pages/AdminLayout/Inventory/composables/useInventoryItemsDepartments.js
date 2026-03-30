import { computed, ref } from 'vue';

export function useInventoryItemsDepartments({ departmentOptions }) {
    const isDepartmentsOpen = ref(false);
    const departmentSearch = ref('');
    const selectedDepartmentIds = ref([]);

    const filteredDepartmentOptions = computed(() => {
        const search = departmentSearch.value.trim().toLowerCase();
        const sorted = [...departmentOptions.value].sort((a, b) => {
            const priority = (option) => {
                if (option.id === 'all_departments') return 0;
                if (option.id === 'all_restaurants') return 1;
                if (option.id === 'warehouse') return 2;
                if (option.type === 'restaurant') return 3;
                return 4;
            };
            const pa = priority(a);
            const pb = priority(b);
            if (pa !== pb) {
                return pa - pb;
            }
            return a.label.localeCompare(b.label, 'ru', { sensitivity: 'base' });
        });
        if (!search) {
            return sorted;
        }
        return sorted.filter((option) => option.label.toLowerCase().includes(search));
    });

    const selectedDepartmentLabels = computed(() =>
        departmentOptions.value
            .filter((option) => selectedDepartmentIds.value.includes(option.id))
            .map((option) => option.label),
    );

    const departmentsLabel = computed(() => {
        if (!selectedDepartmentLabels.value.length) {
            return 'Выберите подразделения';
        }
        if (selectedDepartmentLabels.value.length <= 2) {
            return selectedDepartmentLabels.value.join(', ');
        }
        return `${selectedDepartmentLabels.value.slice(0, 2).join(', ')} +${selectedDepartmentLabels.value.length - 2}`;
    });

    function toggleDepartment(option) {
        const selected = new Set(selectedDepartmentIds.value);
        const isSelected = selected.has(option.id);
        if (option.id === 'all_departments') {
            selectedDepartmentIds.value = isSelected ? [] : ['all_departments'];
            return;
        }
        if (isSelected) {
            selected.delete(option.id);
        } else {
            selected.add(option.id);
            selected.delete('all_departments');
        }
        selectedDepartmentIds.value = Array.from(selected);
    }

    function parseDepartmentFilters() {
        const selected = new Set(selectedDepartmentIds.value);
        const allRestaurantIds = departmentOptions.value
            .filter((option) => option.type === 'restaurant' && option.restaurant_id)
            .map((option) => Number(option.restaurant_id));
        const allSubdivisionIds = departmentOptions.value
            .filter((option) => option.type === 'subdivision' && option.subdivision_id)
            .map((option) => Number(option.subdivision_id));

        if (selected.has('all_departments')) {
            return {
                restaurant_ids: allRestaurantIds,
                subdivision_ids: allSubdivisionIds,
                include_warehouse: true,
            };
        }

        const restaurantIds = new Set();
        const subdivisionIds = new Set();
        let includeWarehouse = false;

        if (selected.has('all_restaurants')) {
            allRestaurantIds.forEach((id) => restaurantIds.add(id));
        }
        if (selected.has('warehouse')) {
            includeWarehouse = true;
        }

        for (const option of departmentOptions.value) {
            if (!selected.has(option.id)) {
                continue;
            }
            if (option.type === 'restaurant' && option.restaurant_id) {
                restaurantIds.add(Number(option.restaurant_id));
            }
            if (option.type === 'subdivision' && option.subdivision_id) {
                subdivisionIds.add(Number(option.subdivision_id));
            }
        }

        return {
            restaurant_ids: Array.from(restaurantIds),
            subdivision_ids: Array.from(subdivisionIds),
            include_warehouse: includeWarehouse,
        };
    }

    return {
        departmentSearch,
        departmentsLabel,
        filteredDepartmentOptions,
        isDepartmentsOpen,
        parseDepartmentFilters,
        selectedDepartmentIds,
        selectedDepartmentLabels,
        toggleDepartment,
    };
}
