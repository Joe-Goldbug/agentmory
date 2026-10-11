/**
 * 语言状态（模块级单例）。
 *
 * 为什么不用 Context：adapters / mocks 层不是 React 组件，无法读 Context。
 * 这里保存一份"当前语言"的模块级状态，I18nProvider 负责同步，非组件代码
 * （mock 回退、时间文案等）用 getLang() 取当前语言。
 */
export type Lang = 'zh' | 'en';

const STORAGE_KEY = 'lwm_lang';

function detect(): Lang {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === 'zh' || saved === 'en') return saved;
  return navigator.language?.toLowerCase().startsWith('zh') ? 'zh' : 'en';
}

let lang: Lang = detect();
const listeners = new Set<(l: Lang) => void>();

export function getLang(): Lang {
  return lang;
}

export function setLangGlobal(next: Lang) {
  if (lang === next) return;
  lang = next;
  localStorage.setItem(STORAGE_KEY, next);
  document.documentElement.lang = next === 'zh' ? 'zh-CN' : 'en';
  listeners.forEach((fn) => fn(next));
}

export function subscribeLang(fn: (l: Lang) => void) {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}
