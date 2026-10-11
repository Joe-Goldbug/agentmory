/**
 * 登录页：邮箱注册/登录 + Solana 钱包（Phantom）签名登录。
 *
 * 钱包流程：
 *  1. window.solana（Phantom 等）connect 拿公钥；
 *  2. 网关发 nonce；3. signMessage 签名；
 *  4. 前端 tweetnacl 验签（Ed25519）；5. 提交网关换取会话 token。
 */
import { useState } from 'react';
import nacl from 'tweetnacl';
import bs58 from 'bs58';
import { login as apiLogin, register as apiRegister, walletNonce, walletVerify } from '../api/auth';
import { useAuth } from '../auth/AuthContext';
import { useI18n } from '../i18n';
import { Icons } from '../components/Icons';

interface PhantomProvider {
  connect: () => Promise<{ publicKey: { toString(): string } }>;
  signMessage: (msg: Uint8Array, enc?: string) => Promise<{ signature: Uint8Array; publicKey: unknown }>;
  publicKey?: { toString(): string } | null;
}

function getProvider(): PhantomProvider | null {
  const w = window as unknown as { solana?: PhantomProvider; phantom?: PhantomProvider };
  return w.phantom ?? w.solana ?? null;
}

const inputCls =
  'w-full px-4 py-2.5 bg-white border border-gray-200 rounded-lg text-sm focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none transition-all';
const btnPrimary =
  'w-full py-2.5 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all';

export default function LoginView() {
  const { login } = useAuth();
  const { t, lang, toggle } = useI18n();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submitEmail(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      const res =
        mode === 'login' ? await apiLogin(email, password) : await apiRegister(email, password, name);
      login(res.token, res.user);
    } catch (err) {
      setError((err as Error).message || t('login.failed'));
    } finally {
      setBusy(false);
    }
  }

  async function connectWallet() {
    setError('');
    const provider = getProvider();
    if (!provider) {
      setError(t('login.noProvider'));
      return;
    }
    setBusy(true);
    try {
      const { publicKey } = await provider.connect();
      const address = publicKey.toString();
      const { nonce } = await walletNonce(address);
      const { signature } = await provider.signMessage(new TextEncoder().encode(nonce), 'utf8');
      // 前端 Ed25519 验签（服务端标准库无法验签，见 lwm/webauth.py）
      const pubkeyBytes = bs58.decode(address);
      const ok = nacl.sign.detached.verify(new TextEncoder().encode(nonce), signature, pubkeyBytes);
      if (!ok) throw new Error(t('login.badSig'));
      const res = await walletVerify(address, nonce, bs58.encode(signature));
      login(res.token, res.user);
    } catch (err) {
      const msg = (err as Error).message || '';
      setError(
        msg.startsWith('User rejected') || msg.includes('declined') ? t('login.rejected') : msg || t('login.failed'),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen w-full bg-[#f8f9fa] flex items-center justify-center p-6 relative">
      <button
        onClick={toggle}
        className="absolute top-6 right-6 flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-gray-200 bg-white text-xs font-medium text-gray-600 hover:text-blue-600 hover:border-blue-200 transition"
      >
        <Icons.Globe className="w-3.5 h-3.5" />
        <span>{lang === 'zh' ? 'English' : '中文'}</span>
      </button>

      <div className="w-full max-w-md bg-white rounded-2xl border border-gray-200 shadow-lg p-8 animate-fade-in">
        <div className="flex items-center space-x-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white text-xl font-bold">
            ∞
          </div>
          <h1 className="text-xl font-bold text-gray-900">
            {lang === 'zh' ? 'AI 工作记忆' : 'AI Work Memory'}
          </h1>
        </div>
        <p className="text-sm text-gray-500 mb-6">{t('login.subtitle')}</p>

        {error && (
          <div className="mb-4 px-4 py-2.5 bg-red-50 border border-red-200 text-red-600 text-sm rounded-lg">
            {error}
          </div>
        )}

        <button
          onClick={connectWallet}
          disabled={busy}
          className="w-full py-3 bg-[#ab9ff2] hover:bg-[#9a8cf0] text-white rounded-lg text-sm font-semibold flex items-center justify-center space-x-2 disabled:opacity-50 transition-all mb-6"
        >
          <svg viewBox="0 0 32 32" className="w-5 h-5" fill="currentColor" aria-hidden>
            <path d="M10.5 7h14L21 12H7l3.5-5zm0 18h14L21 20H7l3.5 5zM7 13.5h11l3.5 2.5L18 18.5H7L3.5 16 7 13.5z" />
          </svg>
          <span>{busy ? t('login.walletWaiting') : t('login.wallet')}</span>
        </button>

        <div className="flex items-center space-x-3 mb-6">
          <div className="flex-1 h-px bg-gray-200"></div>
          <span className="text-xs text-gray-400">{t('login.orEmail')}</span>
          <div className="flex-1 h-px bg-gray-200"></div>
        </div>

        <div className="flex bg-gray-100 rounded-lg p-1 mb-5 text-sm font-medium">
          {(['login', 'register'] as const).map((m) => (
            <button
              key={m}
              onClick={() => {
                setMode(m);
                setError('');
              }}
              className={`flex-1 py-1.5 rounded-md transition-all ${
                mode === m ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500'
              }`}
            >
              {m === 'login' ? t('login.tabLogin') : t('login.tabRegister')}
            </button>
          ))}
        </div>

        <form onSubmit={submitEmail} className="space-y-3">
          {mode === 'register' && (
            <input
              className={inputCls}
              placeholder={t('login.namePlaceholder')}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          )}
          <input
            className={inputCls}
            type="email"
            required
            placeholder={t('login.emailPlaceholder')}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            className={inputCls}
            type="password"
            required
            minLength={6}
            placeholder={t('login.passwordPlaceholder')}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button type="submit" disabled={busy} className={btnPrimary}>
            {busy ? t('login.busy') : mode === 'login' ? t('login.submitLogin') : t('login.submitRegister')}
          </button>
        </form>

        <p className="text-[11px] text-gray-400 mt-6 leading-relaxed">{t('login.privacy')}</p>
      </div>
    </div>
  );
}
