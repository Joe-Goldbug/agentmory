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
import { TOOLS } from '../../mocks';
import type { ProofLevel, ToolItem } from '../../types';

const PROOF_LABEL: Record<ProofLevel, string> = {
  'native-hook': '宿主原生 Hook 已验证',
  'watcher-observed': '观察器捕获',
  configured: '仅已配置',
  none: '未接入',
};

export async function fetchTools(): Promise<ToolItem[]> {
  if (USE_MOCK) return TOOLS;
  const raw = await request<RawTool[]>(ENDPOINTS.toolsCoverage);
  return raw.map((t, i) => {
    const proof = mapProof(t.proof_level);
    return {
      id: t.tool ?? String(i),
      name: t.tool ?? 'unknown',
      proof,
      proofLabel: PROOF_LABEL[proof],
      lastUsed: t.last_seen ? `最近使用：${t.last_seen}` : '暂无使用记录',
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
