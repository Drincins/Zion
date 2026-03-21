import { onBeforeUnmount, onMounted, unref } from 'vue';

function resolveElement(elementRef) {
    if (typeof elementRef === 'function') {
        return elementRef();
    }
    return unref(elementRef);
}

export function useClickOutside(entries, { eventName = 'click' } = {}) {
    const resolveEntries = () => (typeof entries === 'function' ? entries() : entries);

    const handleDocumentEvent = (event) => {
        const items = resolveEntries();
        if (!Array.isArray(items)) {
            return;
        }

        items.forEach((entry) => {
            if (!entry || typeof entry.onOutside !== 'function') {
                return;
            }
            if (typeof entry.when === 'function' && !entry.when()) {
                return;
            }

            const element = resolveElement(entry.element);
            if (!element || element.contains(event.target)) {
                return;
            }

            entry.onOutside(event);
        });
    };

    onMounted(() => {
        document.addEventListener(eventName, handleDocumentEvent);
    });

    onBeforeUnmount(() => {
        document.removeEventListener(eventName, handleDocumentEvent);
    });
}
