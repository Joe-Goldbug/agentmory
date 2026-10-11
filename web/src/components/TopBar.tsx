import { Icons } from './Icons';
import type { SearchHit } from '../types';

interface Props {
  query: string;
  onQuery: (q: string) => void;
  hits: SearchHit[];
}

export default function TopBar({ query, onQuery, hits }: Props) {
  return (
    <header className="h-16 bg-white/50 backdrop-blur-sm border-b border-gray-200/50 flex items-center justify-between px-6 z-10">
      <div className="relative w-96">
        <Icons.Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="搜索项目、记忆、或关键词..."
          className="w-full pl-9 pr-4 py-2 bg-gray-100 border-transparent rounded-lg text-sm focus:bg-white focus:border-blue-300 focus:ring-2 focus:ring-blue-100 transition-all outline-none"
        />
        {hits.length > 0 && (
          <div className="absolute top-11 left-0 w-full bg-white border border-gray-200 rounded-lg shadow-lg z-20 overflow-hidden">
            {hits.map((h) => (
              <div key={h.pagePath + h.title} className="px-4 py-2.5 hover:bg-gray-50 cursor-pointer">
                <div className="text-sm font-medium text-gray-900">{h.title}</div>
                <div className="text-xs text-gray-500 truncate">{h.snippet}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center space-x-4">
        <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 cursor-pointer hover:bg-gray-200">
          <Icons.Settings className="w-4 h-4" />
        </div>
      </div>
    </header>
  );
}
