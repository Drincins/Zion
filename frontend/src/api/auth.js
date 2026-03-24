import axios from 'axios';
import { api } from './client';

const fingerAgentUrl =
    (import.meta.env.VITE_FINGER_AGENT_URL || '').trim() || 'http://127.0.0.1:47123';

export async function loginUser(username, password) {
    const { data } = await api.post('/api/login', {
        username,
        password,
    });
    return data;
}

export async function logoutUser() {
    await api.post('/api/auth/logout');
}

export async function fetchCurrentSessionUser() {
    const { data } = await api.get('/api/auth/me');
    return data;
}

export async function loginStaffByCode(staffCode, options = {}) {
    const payload = { staff_code: staffCode };
    if (options.authMethod) {
        payload.auth_method = options.authMethod;
    }
    if (Number.isFinite(options.fingerprintScore)) {
        payload.fingerprint_score = options.fingerprintScore;
    }
    if (Number.isFinite(options.fingerprintSlot)) {
        payload.fingerprint_slot = options.fingerprintSlot;
    }
    const { data } = await api.post('/api/staff/login', payload);
    return data;
}

export async function identifyFingerprint() {
    const { data } = await axios.post(`${fingerAgentUrl}/identify`, {}, { timeout: 20000 });
    return data;
}
