import { readonly, ref } from 'vue';

const pendingNavigations = ref(0);
const pendingApiRequests = ref(0);
const isRouteLoading = ref(false);
const MIN_VISIBLE_MS = 260;
const HIDE_GRACE_MS = 220;
let visibleSince = 0;
let hideTimer = null;

function getPendingCount() {
    return pendingNavigations.value + pendingApiRequests.value;
}

function clearHideTimer() {
    if (!hideTimer) {
        return;
    }
    globalThis.clearTimeout(hideTimer);
    hideTimer = null;
}

function showLoading() {
    clearHideTimer();
    if (isRouteLoading.value) {
        return;
    }
    isRouteLoading.value = true;
    visibleSince = Date.now();
}

function hideLoadingWithMinDuration() {
    if (!isRouteLoading.value) {
        return;
    }
    const elapsed = Date.now() - visibleSince;
    const waitForMinVisibleMs = Math.max(0, MIN_VISIBLE_MS - elapsed);
    const waitMs = Math.max(waitForMinVisibleMs, HIDE_GRACE_MS);
    clearHideTimer();
    hideTimer = globalThis.setTimeout(() => {
        hideTimer = null;
        if (getPendingCount() === 0) {
            isRouteLoading.value = false;
        }
    }, waitMs);
}

export function beginRouteLoading() {
    pendingNavigations.value += 1;
    showLoading();
}

export function endRouteLoading() {
    pendingNavigations.value = Math.max(0, pendingNavigations.value - 1);
    if (getPendingCount() === 0) {
        hideLoadingWithMinDuration();
    }
}

export function resetRouteLoading() {
    pendingNavigations.value = 0;
    if (getPendingCount() === 0) {
        clearHideTimer();
        isRouteLoading.value = false;
        return;
    }
    showLoading();
}

export function beginApiLoading() {
    pendingApiRequests.value += 1;
    showLoading();
}

export function endApiLoading() {
    pendingApiRequests.value = Math.max(0, pendingApiRequests.value - 1);
    if (getPendingCount() === 0) {
        hideLoadingWithMinDuration();
    }
}

export function useRouteLoadingState() {
    return readonly(isRouteLoading);
}
