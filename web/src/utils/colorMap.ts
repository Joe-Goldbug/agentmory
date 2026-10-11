/**
 * 静态配色映射表。
 *
 * 原因：Demo 原文件用 `bg-${color}-100` 动态拼接 Tailwind 类名，
 * Tailwind JIT 只扫描字面量，拼接产物不会生成对应 CSS，导致颜色全部丢失。
 * 这里改为全量枚举，工具类可安全引用。
 */
export type PaletteName = 'blue' | 'purple' | 'green' | 'orange' | 'red' | 'gray';

export const PALETTE = {
  blue: {
    dot: 'bg-blue-500',
    ring: 'ring-blue-50',
    soft: 'bg-blue-50',
    badge: 'border-blue-200 text-blue-700 bg-blue-50',
    avatar: 'bg-blue-100 text-blue-600',
    tile: 'bg-blue-50 text-blue-600 border-blue-100',
  },
  purple: {
    dot: 'bg-purple-500',
    ring: 'ring-purple-50',
    soft: 'bg-purple-50',
    badge: 'border-purple-200 text-purple-700 bg-purple-50',
    avatar: 'bg-purple-100 text-purple-600',
    tile: 'bg-purple-50 text-purple-600 border-purple-100',
  },
  green: {
    dot: 'bg-green-500',
    ring: 'ring-green-50',
    soft: 'bg-green-50',
    badge: 'border-green-200 text-green-700 bg-green-50',
    avatar: 'bg-green-100 text-green-600',
    tile: 'bg-green-50 text-green-600 border-green-100',
  },
  orange: {
    dot: 'bg-orange-500',
    ring: 'ring-orange-50',
    soft: 'bg-orange-50',
    badge: 'border-orange-200 text-orange-700 bg-orange-50',
    avatar: 'bg-orange-100 text-orange-600',
    tile: 'bg-orange-50 text-orange-600 border-orange-100',
  },
  red: {
    dot: 'bg-red-500',
    ring: 'ring-red-50',
    soft: 'bg-red-50',
    badge: 'border-red-200 text-red-700 bg-red-50',
    avatar: 'bg-red-100 text-red-600',
    tile: 'bg-red-50 text-red-600 border-red-100',
  },
  gray: {
    dot: 'bg-gray-500',
    ring: 'ring-gray-50',
    soft: 'bg-gray-50',
    badge: 'border-gray-200 text-gray-700 bg-gray-50',
    avatar: 'bg-gray-100 text-gray-600',
    tile: 'bg-gray-50 text-gray-600 border-gray-100',
  },
} as const;

export function palette(name: string) {
  return PALETTE[(name as PaletteName) in PALETTE ? (name as PaletteName) : 'gray'];
}
