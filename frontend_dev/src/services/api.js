import { reactive } from "vue";
import { i18n } from "../i18n";

export const session = reactive({
  baseUrl: localStorage.getItem("appstore_base_url") || "http://127.0.0.1:9001",
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

export function buildApiUrl(path) {
  return apiUrl(path);
}

export async function request(path, { method = "GET", body = null, auth = false } = {}) {
  const headers = {};
  if (auth) {
    if (!session.token) throw new Error(i18n.global.t("common.loginFirst"));
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

export async function login(username, password) {
  const fd = new FormData();
  fd.append("username", username);
  fd.append("password", password);
  const data = await request("/dev/auth/login", { method: "POST", body: fd });
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

export async function fetchStoreDownloadUrl(appId, version) {
  return request(`/store/apps/${encodeURIComponent(appId)}/versions/${encodeURIComponent(version)}/download-url`, { auth: true });
}

export async function uploadPackage(formData) {
  return request("/dev/apps/upload-package", { method: "POST", body: formData, auth: true });
}

export async function parsePackageManifest(formData) {
  return request("/dev/apps/manifest/parse-package", { method: "POST", body: formData, auth: true });
}

export async function uploadVersion(appId, formData) {
  return request(`/dev/apps/${encodeURIComponent(appId)}/versions`, {
    method: "POST",
    body: formData,
    auth: true,
  });
}

export async function modifyVersion(appId, version, formData) {
  return request(
    `/dev/apps/${encodeURIComponent(appId)}/versions/${encodeURIComponent(version)}`,
    { method: "PATCH", body: formData, auth: true }
  );
}

export async function unpublishVersion(appId, version) {
  return request(
    `/dev/apps/${encodeURIComponent(appId)}/versions/${encodeURIComponent(version)}/unpublish`,
    { method: "POST", auth: true }
  );
}

export async function publishVersion(appId, version) {
  return request(
    `/dev/apps/${encodeURIComponent(appId)}/versions/${encodeURIComponent(version)}/publish`,
    { method: "POST", auth: true }
  );
}

export async function deleteVersion(appId, version) {
  return request(
    `/dev/apps/${encodeURIComponent(appId)}/versions/${encodeURIComponent(version)}`,
    { method: "DELETE", auth: true }
  );
}

export async function deleteApp(appId) {
  return request(
    `/dev/apps/${encodeURIComponent(appId)}`,
    { method: "DELETE", auth: true }
  );
}
