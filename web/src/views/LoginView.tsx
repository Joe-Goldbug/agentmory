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
  const w = window as unknown as {
    phantom?: { solana?: PhantomProvider };
    solana?: PhantomProvider;
    solflare?: PhantomProvider;
  };
  return w.phantom?.solana ?? w.solana ?? w.solflare ?? null;
}

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
    <div className="min-h-screen w-full bg-black text-white flex items-center justify-center p-6 relative overflow-hidden">
      <div className="bg-layer" />

      {/* Language Switch Top Right */}
      <button
        onClick={toggle}
        className="absolute top-6 right-6 header-icon-btn z-20 text-xs"
      >
        <Icons.Globe className="w-3.5 h-3.5 mr-1" />
        <span>{lang === 'zh' ? 'EN' : '中文'}</span>
      </button>

      <div className="w-full max-w-md glass-panel p-8 relative z-10 shadow-2xl anim">
        {/* Logo and Brand */}
        <div className="flex flex-col items-center text-center mb-6">
          <div className="logo-btn mb-4 w-12 h-12 shadow-md">
            <svg className="logo-svg" viewBox="0 0 100 100" width="100%" height="100%">
              <defs>
                <linearGradient id="flowGradLogin" x1="15%" y1="15%" x2="85%" y2="85%">
                  <stop offset="0%" stopColor="#0a0a0a" />
                  <stop offset="100%" stopColor="#222222" />
                </linearGradient>
              </defs>
              <path
                d="M 32 30 C 18 30, 14 42, 14 50 C 14 58, 18 70, 32 70 C 44 70, 50 56, 50 50 C 50 44, 56 30, 68 30 C 82 30, 86 42, 86 50 C 86 58, 82 70, 68 70 C 56 70, 50 56, 50 50"
                fill="none"
                stroke="url(#flowGradLogin)"
                strokeWidth="7.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="23" cy="50" r="4.5" fill="#111111" />
              <circle cx="77" cy="50" r="4.5" fill="#111111" />
              <g transform="translate(50, 50)">
                <polygon points="0,-7 6,-3.5 0,0 -6,-3.5" fill="#111111" />
                <polygon points="-6,-3.5 0,0 0,7 -6,3.5" fill="#333333" />
                <polygon points="0,0 6,-3.5 6,3.5 0,7" fill="#1a1a1a" />
              </g>
            </svg>
          </div>
          <h1 className="text-xl font-bold font-display tracking-tight text-white mb-1">
            Flowmory
          </h1>
          <p className="text-xs text-gray-400">
            {lang === 'zh'
              ? '多 Agent 协同工作流 · 跨工具工作记忆 · 链上加密审计'
              : 'Intelligence Designed To Evolve · Multi-Agent Memory'}
          </p>
        </div>

        {error && (
          <div className="mb-4 px-4 py-2.5 bg-red-500/15 border border-red-500/30 text-red-300 text-xs rounded-xl">
            {error}
          </div>
        )}

        {/* Solana Wallet Phantom Login Button */}
        <button
          onClick={connectWallet}
          disabled={busy}
          className="w-full py-2.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 bg-[#ab9ff2]/15 hover:bg-[#ab9ff2]/25 border border-[#ab9ff2]/40 text-[#ab9ff2] transition disabled:opacity-50 mb-4"
        >
          <svg viewBox="0 0 32 32" className="w-4 h-4" fill="currentColor" aria-hidden>
            <path d="M10.5 7h14L21 12H7l3.5-5zm0 18h14L21 20H7l3.5 5zM7 13.5h11l3.5 2.5L18 18.5H7L3.5 16 7 13.5z" />
          </svg>
          <span>{busy ? t('login.walletWaiting') : t('login.wallet')}</span>
        </button>

        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px bg-white/10" />
          <span className="text-[11px] text-gray-500">{t('login.orEmail')}</span>
          <div className="flex-1 h-px bg-white/10" />
        </div>

        {/* Mode switch */}
        <div className="flex bg-black/40 border border-white/10 rounded-full p-1 mb-4 text-xs font-medium">
          {(['login', 'register'] as const).map((m) => (
            <button
              key={m}
              onClick={() => {
                setMode(m);
                setError('');
              }}
              className={`flex-1 py-1 rounded-full transition ${
                mode === m ? 'bg-white text-black font-semibold' : 'text-gray-400 hover:text-white'
              }`}
            >
              {m === 'login' ? t('login.tabLogin') : t('login.tabRegister')}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={submitEmail} className="space-y-3">
          {mode === 'register' && (
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('login.namePlaceholder')}
              className="w-full px-3.5 py-2 bg-[#121214] border border-white/15 rounded-xl text-xs text-white placeholder-gray-500 outline-none focus:border-white/40 transition"
            />
          )}
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t('login.emailPlaceholder')}
            className="w-full px-3.5 py-2 bg-[#121214] border border-white/15 rounded-xl text-xs text-white placeholder-gray-500 outline-none focus:border-white/40 transition"
          />
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t('login.passwordPlaceholder')}
            className="w-full px-3.5 py-2 bg-[#121214] border border-white/15 rounded-xl text-xs text-white placeholder-gray-500 outline-none focus:border-white/40 transition"
          />

          <button
            type="submit"
            disabled={busy}
            className="btn-mini btn-mini-primary w-full py-2.5 text-xs font-semibold mt-2"
          >
            {busy ? t('common.loading') : mode === 'login' ? t('login.submitLogin') : t('login.submitRegister')}
          </button>
        </form>
      </div>
    </div>
  );
}
