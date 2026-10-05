import { createI18n } from "vue-i18n";
import { ref } from "vue";
import { readSetting, saveSetting, resolveLanguage, subscribeAppearance } from "../appearance";

export const localeMode = ref(readSetting("appstore_locale"));
const DEFAULT_LOCALE = resolveLanguage(localeMode.value);

export const i18n = createI18n({
  legacy: false,
  locale: DEFAULT_LOCALE,
  fallbackLocale: "en-US",
  messages: {},
});

export async function loadLocaleMessages(locale) {
  const loaders = {
    "zh-CN": () => import("./locales/zh-CN.json"),
    "en-US": () => import("./locales/en-US.json"),
  };
  const loader = loaders[locale] || loaders["en-US"];
  const mod = await loader();
  i18n.global.setLocaleMessage(locale, mod.default);
}

let languageRevision = 0;
async function applyLocale() {
  const revision = ++languageRevision;
  const locale = resolveLanguage(localeMode.value);
  if (!i18n.global.availableLocales.includes(locale)) {
    await loadLocaleMessages(locale);
  }
  if (revision === languageRevision) i18n.global.locale.value = locale;
}

export async function setLocale(mode) {
  localeMode.value = ['system', 'en-US', 'zh-CN'].includes(mode) ? mode : 'system';
  saveSetting("appstore_locale", localeMode.value);
  await applyLocale();
}

subscribeAppearance(() => {
  localeMode.value = readSetting("appstore_locale");
  applyLocale().catch(error => console.warn('Language update failed:', error));
});

export function currentLocale() {
  return i18n.global.locale.value;
}
