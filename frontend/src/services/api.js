import { reactive } from "vue";

export const session = reactive({
  baseUrl: localStorage.getItem("appstore_base_url") || "",
  token: localStorage.getItem("appstore_token") || "",
  user: null,
});

export function setBaseUrl(url) {
  session.baseUrl = (url || "").trim();
  localStorage.setItem("appstore_base_url", session.baseUrl);
}

function apiUrl(path) {
  if (!session.baseUrl) return path;
  return `${session.baseUrl.replace(/\/$/, "")}${path}`;
}

export async function request(path, { method = "GET", body = null, auth = false } = {}) {
  const headers = {};
  if (auth) {
    if (!session.token) throw new Error("请先登录");
    headers.Authorization = `Bearer ${session.token}`;
  }

  const res = await fetch(apiUrl(path), { method, headers, body });
  const text = await res.text();
  let data = text;
  try {
    data = JSON.parse(text);
  } catch {
    // keep raw text
  }
  if (!res.ok) throw new Error(`${res.status} ${JSON.stringify(data)}`);
  return data;
}

export function toFormData(payload, file = null) {
  const fd = new FormData();
  Object.entries(payload).forEach(([k, v]) => {
    if (v === "" || v === null || v === undefined) return;
    fd.append(k, v);
  });
  if (file) fd.append("file", file);
  return fd;
}

export async function login(username, password) {
  const data = await request("/dev/auth/login", {
    method: "POST",
    body: toFormData({ username, password }),
  });
  session.token = data.access_token;
  session.user = data.user;
  localStorage.setItem("appstore_token", session.token);
  return data;
}

export function logout() {
  session.token = "";
  session.user = null;
  localStorage.removeItem("appstore_token");
}

export async function fetchMe() {
  const data = await request("/dev/me", { auth: true });
  session.user = data.user;
  return data.user;
}

export async function fetchStoreApps() {
  return request("/store/index", { auth: true });
}

export async function fetchStoreAppDetail(appId) {
  return request(`/store/apps/${encodeURIComponent(appId)}`, { auth: true });
}

export async function uploadSimpleApp(payload, file) {
  return request("/dev/apps/upload-simple", {
    method: "POST",
    body: toFormData(payload, file),
    auth: true,
  });
}
