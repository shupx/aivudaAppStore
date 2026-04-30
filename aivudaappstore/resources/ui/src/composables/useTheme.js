import { ref, onMounted } from 'vue';

export function useTheme() {
  const isDark = ref(false);

  function applyTheme(dark) {
    if (dark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }

  function toggleTheme() {
    isDark.value = !isDark.value;
    localStorage.setItem('theme', isDark.value ? 'dark' : 'light');
    applyTheme(isDark.value);
  }

  function initTheme() {
    const saved = localStorage.getItem('theme');
    if (saved) {
      isDark.value = saved === 'dark';
    } else {
      isDark.value = false;
    }
    applyTheme(isDark.value);
  }

  onMounted(() => {
    initTheme();
  });

  return { isDark, toggleTheme };
}
