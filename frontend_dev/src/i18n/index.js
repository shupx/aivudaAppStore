import { createI18n } from "vue-i18n";

const DEFAULT_LOCALE = localStorage.getItem("appstore_locale") || "zh-CN";

export const i18n = createI18n({
  legacy: false,
  locale: DEFAULT_LOCALE,
  fallbackLocale: "zh-CN",
  messages: {},
});

export async function loadLocaleMessages(locale) {
  const loaders = {
    "zh-CN": () => import("./locales/zh-CN.json"),
    "en-US": () => import("./locales/en-US.json"),
  };
  const loader = loaders[locale] || loaders["zh-CN"];
  const mod = await loader();
  i18n.global.setLocaleMessage(locale, mod.default);
}

export async function setLocale(locale) {
  if (!i18n.global.availableLocales.includes(locale)) {
    await loadLocaleMessages(locale);
  }
  i18n.global.locale.value = locale;
  localStorage.setItem("appstore_locale", locale);
}

export function currentLocale() {
  return i18n.global.locale.value;
}
