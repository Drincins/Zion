import { getCurrentInstance, onBeforeUnmount } from 'vue';

export function useDebounce(fn, delay = 300) {
    let timer = null;

    const cancel = () => {
        if (timer !== null) {
            clearTimeout(timer);
            timer = null;
        }
    };

    const debounced = (...args) => {
        cancel();
        timer = setTimeout(() => {
            fn(...args);
        }, delay);
    };

    debounced.cancel = cancel;

    if (getCurrentInstance()) {
        onBeforeUnmount(cancel);
    }

    return debounced;
}
