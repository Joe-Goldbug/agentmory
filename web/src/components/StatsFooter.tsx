import { useEffect, useState } from 'react';
import type { StatusBar as StatusModel } from '../types';
import { useI18n } from '../i18n';

interface Props {
  status: StatusModel | null;
}

export default function StatsFooter({ status }: Props) {
  const { t, lang } = useI18n();

  // Animated values
  const [inferenceTime, setInferenceTime] = useState(0);
  const [uptime, setUptime] = useState(0);
  const [runtime, setRuntime] = useState(0);
  const [contextWindows, setContextWindows] = useState(0);

  useEffect(() => {
    const easeOutCubic = (x: number): number => 1 - Math.pow(1 - x, 3);
    const duration = 1500;
    const startTime = performance.now();

    let animationFrameId: number;

    function frame(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = easeOutCubic(progress);

      setInferenceTime(Math.round(120 * eased));
      setUptime(Number((99.99 * eased).toFixed(2)));
      setRuntime(Math.round(24 * eased));
      setContextWindows(Number((2.4 * eased).toFixed(1)));

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(frame);
      } else {
        setInferenceTime(120);
        setUptime(99.99);
        setRuntime(24);
        setContextWindows(2.4);
      }
    }

    animationFrameId = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  return (
    <footer className="stats-footer">
      {/* Metric 1 */}
      <div className="stat-item anim" style={{ ['--d' as string]: '0.35s' }}>
        <span className="stat-icon">&lt;</span>
        <span className="stat-value">{inferenceTime}ms</span>
        <span className="stat-label">{lang === 'zh' ? '推理解析延迟' : 'Inference Time'}</span>
      </div>

      {/* Metric 2 */}
      <div className="stat-item anim" style={{ ['--d' as string]: '0.42s' }}>
        <span className="stat-icon">%</span>
        <span className="stat-value">{uptime}%</span>
        <span className="stat-label">{lang === 'zh' ? '高可用保障' : 'Platform Uptime'}</span>
      </div>

      {/* Metric 3 */}
      <div className="stat-item anim" style={{ ['--d' as string]: '0.49s' }}>
        <span className="stat-icon">*</span>
        <span className="stat-value">{runtime}/7</span>
        <span className="stat-label">{lang === 'zh' ? '自动化运行' : 'Autonomous Runtime'}</span>
      </div>

      {/* Metric 4 */}
      <div className="stat-item anim" style={{ ['--d' as string]: '0.56s' }}>
        <span className="stat-icon">#</span>
        <span className="stat-value">{contextWindows}M</span>
        <span className="stat-label">
          {lang === 'zh' ? '上下文窗口' : 'Context Windows'}
          {status && (
            <span
              className="inline-block w-1.5 h-1.5 rounded-full ml-1.5 align-middle"
              style={{ backgroundColor: status.serviceOk ? '#22c55e' : '#ef4444' }}
              title={`${status.serviceLabel}: ${status.serviceOk ? t('status.ok') : t('status.down')} (${status.syncedAt})`}
            />
          )}
        </span>
      </div>
    </footer>
  );
}
