/**
 * i18n：Provider + useI18n()。
 *
 * 语言状态同时存在于模块级 store（供 adapters/mocks 读取）与 React 状态
 * （供组件重渲染），setLang 时两边一起更新。
 */
import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { DICTS, interpolate, type MessageKey } from './messages';
import { getLang, setLangGlobal, subscribeLang, type Lang } from './store';

interface I18nValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  toggle: () => void;
  /** t('ws.title') / t('ws.handoffMsg', { tool: 'Codex' }) */
  t: (key: MessageKey, params?: Record<string, string | number>) => string;
}

const Ctx = createContext<I18nValue>({
  lang: getLang(),
  setLang: () => {},
  toggle: () => {},
  t: (key) => key,
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(getLang());

  useEffect(() => {
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    return subscribeLang(setLangState);
  }, [lang]);

  const setLang = useCallback((l: Lang) => setLangGlobal(l), []);
  const toggle = useCallback(() => setLangGlobal(getLang() === 'zh' ? 'en' : 'zh'), []);

  const t = useCallback(
    (key: MessageKey, params?: Record<string, string | number>) =>
      interpolate(DICTS[lang][key] ?? key, params),
    [lang],
  );

  return <Ctx.Provider value={{ lang, setLang, toggle, t }}>{children}</Ctx.Provider>;
}

export function useI18n() {
  return useContext(Ctx);
}

export { getLang, type Lang };
