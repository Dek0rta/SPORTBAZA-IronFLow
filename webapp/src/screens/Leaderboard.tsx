import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTelegram } from '../hooks/useTelegram'
import { mockLeaderboard, RANK_CONFIG } from '../data/mock'
import type { Tier } from '../data/mock'

const TOP3 = [
  { border: 'rgba(251,191,36,0.7)',  glow: 'rgba(251,191,36,0.18)', medal: '🥇' },
  { border: 'rgba(226,232,240,0.6)', glow: 'rgba(226,232,240,0.12)', medal: '🥈' },
  { border: 'rgba(245,158,11,0.55)', glow: 'rgba(245,158,11,0.14)', medal: '🥉' },
]

export function Leaderboard() {
  const { haptic } = useTelegram()
  const [tab, setTab] = useState<'global' | 'league'>('global')

  const myPlayer   = mockLeaderboard.find(p => p.isMe)!
  const players    = tab === 'global'
    ? mockLeaderboard
    : mockLeaderboard.filter(p => p.tier === myPlayer.tier)
  const myRank     = players.findIndex(p => p.isMe) + 1

  return (
    <div className="h-full flex flex-col overflow-hidden">

      {/* Header */}
      <div className="shrink-0 px-4 pt-6 pb-3">
        <h1 className="text-white text-2xl font-bold mb-4">Ладдер</h1>

        {/* Tab switcher */}
        <div className="grid grid-cols-2 gap-1 bg-white/5 rounded-2xl p-1">
          {(['global', 'league'] as const).map(id => (
            <button
              key={id}
              onClick={() => { haptic.impact('light'); setTab(id) }}
              className={`py-2.5 rounded-xl text-sm font-semibold transition-all ${
                tab === id ? 'bg-neon-green text-black' : 'text-gray-400'
              }`}
            >
              {id === 'global' ? 'Глобальный топ' : 'Моя лига'}
            </button>
          ))}
        </div>
      </div>

      {/* Scrollable list */}
      <div className="flex-1 overflow-y-auto overscroll-contain px-4 space-y-2 pb-2">
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="space-y-2"
          >
            {players.map((player, i) => {
              const rc     = RANK_CONFIG[player.tier]
              const top3   = i < 3 ? TOP3[i] : null

              return (
                <div
                  key={player.id}
                  className="rounded-2xl p-3 flex items-center gap-3 border"
                  style={{
                    background: player.isMe
                      ? 'rgba(57,255,20,0.07)'
                      : top3
                      ? 'rgba(255,255,255,0.05)'
                      : 'rgba(255,255,255,0.025)',
                    borderColor: player.isMe
                      ? 'rgba(57,255,20,0.35)'
                      : top3
                      ? top3.border
                      : 'rgba(255,255,255,0.07)',
                    boxShadow: top3 && !player.isMe ? `0 0 20px ${top3.glow}` : undefined,
                  }}
                >
                  {/* Position */}
                  <div className="w-8 text-center shrink-0">
                    {top3
                      ? <span className="text-xl">{top3.medal}</span>
                      : <span className="text-gray-500 font-bold text-sm">#{i + 1}</span>
                    }
                  </div>

                  {/* Avatar */}
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center font-black text-sm text-black shrink-0"
                    style={{ background: rc.gradient }}
                  >
                    {player.name[0]}
                  </div>

                  {/* Name + rank */}
                  <div className="flex-1 min-w-0">
                    <p className={`font-semibold text-sm truncate ${player.isMe ? 'text-neon-green' : 'text-white'}`}>
                      {player.name}{player.isMe ? ' (Вы)' : ''}
                    </p>
                    <span className="text-[10px] font-bold" style={{ color: rc.color }}>
                      {player.rank}
                    </span>
                  </div>

                  {/* MMR */}
                  <div className="text-right shrink-0">
                    <p className="text-white font-black text-sm">{player.mmr}</p>
                    <p className="text-gray-500 text-[10px]">MMR</p>
                  </div>
                </div>
              )
            })}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* ── Sticky my position ─────────────────────────────────── */}
      <div className="shrink-0 px-4 pb-2 pt-1 border-t border-white/5">
        <div className="flex items-center gap-1 mb-1.5">
          <span className="text-gray-500 text-[10px] uppercase tracking-widest font-semibold">
            Ваша позиция
          </span>
        </div>
        <MyPositionRow player={myPlayer} rank={myRank} tier={myPlayer.tier} />
      </div>

    </div>
  )
}

function MyPositionRow({
  player, rank, tier,
}: {
  player: { name: string; rank: string; mmr: number }
  rank: number
  tier: Tier
}) {
  const rc = RANK_CONFIG[tier]
  return (
    <div className="rounded-2xl p-3 flex items-center gap-3 bg-neon-green/10 border border-neon-green/30">
      <span className="text-gray-400 font-bold text-sm w-8 text-center shrink-0">#{rank}</span>
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center font-black text-sm text-black shrink-0"
        style={{ background: rc.gradient }}
      >
        {player.name[0]}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-neon-green font-semibold text-sm truncate">{player.name} (Вы)</p>
        <span className="text-[10px] font-bold" style={{ color: rc.color }}>{player.rank}</span>
      </div>
      <div className="text-right shrink-0">
        <p className="text-white font-black text-sm">{player.mmr}</p>
        <p className="text-gray-500 text-[10px]">MMR</p>
      </div>
    </div>
  )
}
