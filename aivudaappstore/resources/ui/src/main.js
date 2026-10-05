import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./styles.css";
import { i18n, loadLocaleMessages, currentLocale } from "./i18n";
import "./composables/useTheme";

async function bootstrap() {
	await loadLocaleMessages('en-US');
	await loadLocaleMessages(currentLocale());
	createApp(App).use(router).use(i18n).mount("#app");
}

bootstrap();
