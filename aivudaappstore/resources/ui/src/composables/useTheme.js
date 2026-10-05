import { computed, ref } from 'vue';
import { readSetting, saveSetting, resolveTheme, subscribeAppearance } from '../appearance';

const themeMode = ref(readSetting('theme'));
const effectiveTheme = ref(resolveTheme(themeMode.value));
const isDark = computed(() => effectiveTheme.value === 'dark');

function applyTheme() {
  effectiveTheme.value = resolveTheme(themeMode.value);
  document.documentElement.classList.toggle('dark', isDark.value);
}

function setThemeMode(mode) {
  themeMode.value = ['system', 'light', 'dark'].includes(mode) ? mode : 'system';
  saveSetting('theme', themeMode.value);
  applyTheme();
}

subscribeAppearance(() => {
  themeMode.value = readSetting('theme');
  applyTheme();
});
applyTheme();

export function useTheme() {
  function toggleTheme() {
    setThemeMode(isDark.value ? 'light' : 'dark');
  }
  return { isDark, themeMode, setThemeMode, toggleTheme };
}
