import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

export function useFloatingPanel({
    rootRef,
    panelRef,
    isOpen,
    triggerSelector,
    onRequestClose,
    computeStyle
}) {
    const floatingStyle = ref({});

    function getTriggerRect() {
        if (!rootRef.value) {
            return null;
        }
        const trigger = rootRef.value.querySelector(triggerSelector);
        return trigger ? trigger.getBoundingClientRect() : null;
    }

    function updateFloatingPosition() {
        const rect = getTriggerRect();
        if (!rect) {
            return;
        }

        floatingStyle.value = computeStyle({
            rect,
            panelElement: panelRef.value,
            viewportHeight: window.innerHeight || document.documentElement.clientHeight,
            viewportWidth: window.innerWidth || document.documentElement.clientWidth
        });
    }

    function onViewportChange() {
        if (!isOpen.value) {
            return;
        }
        updateFloatingPosition();
    }

    function addViewportListeners() {
        window.addEventListener('resize', onViewportChange);
        window.addEventListener('scroll', onViewportChange, true);
    }

    function removeViewportListeners() {
        window.removeEventListener('resize', onViewportChange);
        window.removeEventListener('scroll', onViewportChange, true);
    }

    function handleClickOutside(event) {
        if (!isOpen.value) {
            return;
        }
        if (rootRef.value && rootRef.value.contains(event.target)) {
            return;
        }
        if (panelRef.value && panelRef.value.contains(event.target)) {
            return;
        }
        onRequestClose(event);
    }

    onMounted(() => {
        document.addEventListener('mousedown', handleClickOutside);
    });

    onBeforeUnmount(() => {
        document.removeEventListener('mousedown', handleClickOutside);
        removeViewportListeners();
    });

    watch(isOpen, async (open) => {
        if (open) {
            await nextTick();
            updateFloatingPosition();
            addViewportListeners();
            return;
        }
        removeViewportListeners();
    });

    return {
        floatingStyle,
        updateFloatingPosition
    };
}
