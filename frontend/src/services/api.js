const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export const SESSION_KEYS = {
  token: "careercloud_token",
  user: "careercloud_user",
};

export function getSessionUser() {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_KEYS.user) || "null");
  } catch {
    return null;
  }
}

export function saveSession({ token, user }) {
  sessionStorage.setItem(SESSION_KEYS.token, token);
  sessionStorage.setItem(SESSION_KEYS.user, JSON.stringify(user));
}

export function updateSessionUser(user) {
  sessionStorage.setItem(SESSION_KEYS.user, JSON.stringify(user));
}

export function clearSession() {
  sessionStorage.removeItem(SESSION_KEYS.token);
  sessionStorage.removeItem(SESSION_KEYS.user);
}

export function hasSession() {
  return Boolean(sessionStorage.getItem(SESSION_KEYS.token));
}

async function request(path, options = {}) {
  const token = sessionStorage.getItem(SESSION_KEYS.token);
  const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}), ...options.headers };
  if (token) headers.Authorization = `Bearer ${token}`;
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  const text = await response.text();
  let payload;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { message: text || "The server returned an invalid response." };
  }
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/auth/")) clearSession();
    throw new Error(payload.message || `Request failed (${response.status})`);
  }
  return payload;
}

export async function registerAccount(account) {
  return request("/auth/register", { method: "POST", body: JSON.stringify(account) });
}

export async function signIn(credentials) {
  return request("/auth/login", { method: "POST", body: JSON.stringify(credentials) });
}

export async function createUser(userData) {
  return request("/users", { method: "POST", body: JSON.stringify(userData) });
}

export async function getUser(userId) {
  return request(`/users/${encodeURIComponent(userId)}`);
}

export async function getDashboard(userId) {
  return request(`/dashboard/${encodeURIComponent(userId)}`);
}

export async function updateSkills(userId, skills) {
  return request(`/users/${encodeURIComponent(userId)}/skills`, {
    method: "PUT",
    body: JSON.stringify({ skills }),
  });
}

export async function submitAssessment(assessmentData) {
  return request("/assessment", {
    method: "POST",
    body: JSON.stringify(assessmentData),
  });
}

export async function generateRecommendation(assessmentId) {
  return request("/recommendation", {
    method: "POST",
    body: JSON.stringify({ assessmentId }),
  });
}

export async function generateRoadmap(recommendationId) {
  return request("/roadmap", {
    method: "POST",
    body: JSON.stringify({ recommendationId }),
  });
}

export async function getResumeUploadUrl(fileName) {
  return request("/resume/upload-url", {
    method: "POST",
    body: JSON.stringify({ fileName }),
  });
}
