import { computed, ref } from 'vue';

export function useEmployeeTableFilters({ onlyFired, positionOptions, restaurantOptions, userStore }) {
    const initialRestaurantFilter = userStore.workplaceRestaurantId
        ? String(userStore.workplaceRestaurantId)
        : '';
    const selectedRestaurantFilter = ref(initialRestaurantFilter);
    const selectedPositionFilters = ref([]);
    const hireDateFrom = ref('');
    const hireDateTo = ref('');
    const fireDateFrom = ref('');
    const fireDateTo = ref('');
    const positionFilterQuery = ref('');

    const includeFired = computed(
        () => onlyFired.value || Boolean(fireDateFrom.value || fireDateTo.value)
    );

    const filteredPositionOptions = computed(() => {
        const query = (positionFilterQuery.value || '').trim().toLowerCase();
        if (!query) {
            const selected = new Set(selectedPositionFilters.value);
            if (!selected.size) {
                return [];
            }
            return positionOptions.value.filter((position) => selected.has(position.value));
        }
        return positionOptions.value.filter((position) =>
            (position.label || '').toLowerCase().startsWith(query)
        );
    });

    const defaultRestaurantFilter = computed(() => {
        const workplaceId = userStore.workplaceRestaurantId;
        if (!workplaceId) {
            return '';
        }
        const normalized = String(workplaceId);
        if (!restaurantOptions.value.length) {
            return normalized;
        }
        const exists = restaurantOptions.value.some((option) => option.value === normalized);
        return exists ? normalized : '';
    });

    function togglePositionFilter(positionId, checked) {
        if (!positionId) {
            return;
        }
        const normalized = String(positionId);
        if (checked) {
            if (!selectedPositionFilters.value.includes(normalized)) {
                selectedPositionFilters.value = [...selectedPositionFilters.value, normalized];
            }
            return;
        }
        selectedPositionFilters.value = selectedPositionFilters.value.filter((id) => id !== normalized);
    }

    return {
        selectedRestaurantFilter,
        selectedPositionFilters,
        hireDateFrom,
        hireDateTo,
        fireDateFrom,
        fireDateTo,
        positionFilterQuery,
        includeFired,
        filteredPositionOptions,
        defaultRestaurantFilter,
        togglePositionFilter
    };
}
