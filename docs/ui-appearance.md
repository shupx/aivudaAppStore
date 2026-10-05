# UI Appearance

Language (`appstore_locale`) defaults to `system`, with `en-US` and `zh-CN` overrides. Theme (`theme`) defaults to `system`, with `light` and `dark` overrides. Existing explicit choices remain independent; both selectors are available in the application top bar.

Follow System reads `navigator.language` and `matchMedia('(prefers-color-scheme: dark)')`. Standard `languagechange` and media-query change events update followers without reloading. Unsupported languages or unavailable browser APIs fall back to English and Light. Resolution lives in `resources/ui/src/appearance.js`; theme state also initializes on the login page. There is no dependency on any desktop host, storage key or custom event. Embedding applications can supply their preferences through the browser environment.
