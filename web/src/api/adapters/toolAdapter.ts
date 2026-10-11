/**
 * ⑤ 工具连接适配层
 *
 * 真实来源：GET /api/tools（hub_service.list_tools）
 *          GET /api/tools/coverage（hub_service.coverage_report）
 * 关键映射：Demo 的 status "已连接" -> 本项目三级 Proof 等级
 *   configured        仅生成配置文件
 *   watcher-observed  观察器捕获
 *   native-hook       宿主原生 Hook 凭证回执（README §真实凭证严格审计）
 */
import { request, USE_MOCK } from '../client';
import { ENDPOINTS } from '../endpoints';
import { getMocks } from '../../mocks';
import { getLang } from '../../i18n/store';
import { DICTS } from '../../i18n/messages';
import type { ProofLevel, ToolItem } from '../../types';

const proofLabel = (level: ProofLevel): string => {
  const d = DICTS[getLang()];
  if (level === 'native-hook') return d['proof.nativeHook'];
  if (level === 'watcher-observed') return d['proof.watcherObserved'];
  if (level === 'configured') return d['proof.configured'];
  return d['proof.none'];
};

export async function fetchTools(): Promise<ToolItem[]> {
  if (USE_MOCK) return getMocks().TOOLS;
  const raw = await request<RawTool[]>(ENDPOINTS.toolsCoverage);
  return raw.map((t, i) => {
    const proof = mapProof(t.proof_level);
    return {
      id: t.tool ?? String(i),
      name: t.tool ?? 'unknown',
      proof,
      proofLabel: proofLabel(proof),
      lastUsed: t.last_seen
        ? DICTS[getLang()]['tools.lastUsed'].replace('{time}', t.last_seen)
        : DICTS[getLang()]['tools.noUsage'],
      initial: (t.tool ?? '?').charAt(0).toUpperCase(),
      color: ['orange', 'blue', 'purple', 'green', 'red'][i % 5],
      enabled: t.readable === true || t.writable === true,
    };
  });
}

function mapProof(level?: string): ProofLevel {
  if (level === 'native-hook' || level === 'native_hook') return 'native-hook';
  if (level === 'watcher-observed' || level === 'watcher_observed') return 'watcher-observed';
  if (level === 'configured') return 'configured';
  return 'none';
}

interface RawTool {
  tool?: string;
  proof_level?: string;
  last_seen?: string;
  readable?: boolean;
  writable?: boolean;
}
