import { useState } from 'react'
import { motion } from 'framer-motion'
import { Trophy, ChevronRight } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { BottomSheet } from '../components/BottomSheet'
import {
  mockProfile, mockAchievements,
  RANK_CONFIG, RARITY_CONFIG,
} from '../data/mock'

const item = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { ease: 'easeOut', duration: 0.4 } },
}
const container = { animate: { transition: { staggerChildren: 0.08 } } }

export function Profile() {
  const { user, haptic } = useTelegram()
  const [achOpen, setAchOpen] = useState(false)

  const { rank, tier, mmr, mmrStart, mmrNext, wins, losses, tournaments, equippedIds } = mockProfile
  const rankCfg  = RANK_CONFIG[tier]
  const progress  = ((mmr - mmrStart) / (mmrNext - mmrStart)) * 100
  const equipped  = mockAchievements.filter(a => equippedIds.includes(a.id))
  const unlockedCount = mockAchievements.filter(a => a.unlocked).length
  const name = `${user.first_name}${user.last_name ? ` ${user.last_name}` : ''}`

  return (
    <div className="h-full overflow-y-auto overscroll-contain">
      <div className="px-4 pt-6 pb-8">
        <motion.div variants={container} initial="initial" animate="animate" className="space-y-4">

          {/* ── Player Card ─────────────────────────────────────── */}
          <motion.div variants={item} className="glass-card relative overflow-hidden">
            {/* top accent bar */}
            <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: rankCfg.gradient }} />

            <div className="flex items-center gap-4">
              {/* Avatar */}
              <div
                className="w-20 h-20 rounded-2xl flex items-center justify-center shrink-0 text-3xl font-black text-black"
                style={{ background: rankCfg.gradient, boxShadow: `0 0 32px ${rankCfg.shadow}` }}
              >
                {name[0].toUpperCase()}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <h1 className="text-white font-bold text-xl truncate">{name}</h1>
                {user.username && (
                  <p className="text-gray-500 text-sm">@{user.username}</p>
                )}
                <div
                  className="inline-flex items-center gap-1.5 mt-2 px-3 py-1 rounded-full text-xs font-black text-black"
                  style={{ background: rankCfg.gradient }}
                >
                  <Trophy size={11} />
                  {rank}
                </div>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-2 mt-5 pt-4 border-t border-white/5">
              <StatCell label="Победы"    value={String(wins)}        color={rankCfg.color} />
              <StatCell label="Поражения" value={String(losses)}      color="#6b7280" />
              <StatCell label="Турниры"   value={String(tournaments)} color="#6b7280" />
            </div>
          </motion.div>

          {/* ── MMR Progress ─────────────────────────────────────── */}
          <motion.div variants={item} className="glass-card space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-400 text-xs uppercase tracking-widest font-semibold">
                Рейтинг (MMR)
              </span>
              <span className="text-white font-black text-lg">{mmr}</span>
            </div>

            {/* Bar */}
            <div className="h-3 bg-white/5 rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{ background: rankCfg.gradient }}
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 1.2, ease: 'easeOut', delay: 0.3 }}
              />
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500">
                До следующего ранга:{' '}
                <span className="font-bold" style={{ color: rankCfg.color }}>
                  {mmrNext - mmr} очков
                </span>
              </span>
              <span className="text-gray-600">{Math.round(progress)}%</span>
            </div>
          </motion.div>

          {/* ── Equipped Achievements ───────────────────────────── */}
          <motion.div variants={item}>
            <p className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-3">
              Экипированные награды
            </p>
            <div className="grid grid-cols-3 gap-3">
              {equipped.map(ach => {
                const rc = RARITY_CONFIG[ach.rarity]
                return (
                  <div
                    key={ach.id}
                    className="glass-card flex flex-col items-center gap-2 py-5 px-2"
                    style={{ boxShadow: `0 0 24px ${rc.glow}` }}
                  >
                    <span className="text-3xl">{ach.icon}</span>
                    <p className="text-white text-[10px] font-semibold text-center leading-tight">
                      {ach.name}
                    </p>
                    <span
                      className="text-[9px] font-black uppercase tracking-wide"
                      style={{ color: rc.color }}
                    >
                      {rc.label}
                    </span>
                  </div>
                )
              })}
            </div>
          </motion.div>

          {/* ── All Achievements Button ─────────────────────────── */}
          <motion.div variants={item}>
            <button
              onClick={() => { haptic.impact('light'); setAchOpen(true) }}
              className="w-full glass-card flex items-center justify-between py-4 active:scale-[0.98] transition-transform"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-400/10 flex items-center justify-center">
                  <Trophy size={18} className="text-amber-400" />
                </div>
                <div className="text-left">
                  <p className="text-white font-semibold text-sm">Вся коллекция наград</p>
                  <p className="text-gray-500 text-xs">
                    {unlockedCount} / {mockAchievements.length} разблокировано
                  </p>
                </div>
              </div>
              <ChevronRight size={18} className="text-gray-600" />
            </button>
          </motion.div>

        </motion.div>
      </div>

      {/* ── Achievements Modal ──────────────────────────────────── */}
      <BottomSheet isOpen={achOpen} onClose={() => setAchOpen(false)} title="Коллекция наград">
        <div className="grid grid-cols-2 gap-3 max-h-[58vh] overflow-y-auto overscroll-contain pb-1">
          {mockAchievements.map(ach => {
            const rc = RARITY_CONFIG[ach.rarity]
            return (
              <div
                key={ach.id}
                className={`rounded-2xl p-4 border flex flex-col gap-2 transition-opacity ${
                  ach.unlocked
                    ? 'bg-white/5 border-white/10'
                    : 'bg-white/[0.02] border-white/5 opacity-40'
                }`}
                style={ach.unlocked ? { boxShadow: `0 0 18px ${rc.glow}` } : {}}
              >
                <div className="flex items-start justify-between">
                  <span className="text-2xl">{ach.unlocked ? ach.icon : '🔒'}</span>
                  <span
                    className="text-[9px] font-black uppercase tracking-wide"
                    style={{ color: ach.unlocked ? rc.color : '#4b5563' }}
                  >
                    {rc.label}
                  </span>
                </div>
                <p className="text-white text-xs font-semibold leading-tight">{ach.name}</p>
                <p className="text-gray-500 text-[10px] leading-tight">{ach.desc}</p>
              </div>
            )
          })}
        </div>
      </BottomSheet>
    </div>
  )
}

function StatCell({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="text-center">
      <p className="font-black text-xl leading-none" style={{ color }}>{value}</p>
      <p className="text-gray-500 text-[10px] mt-1">{label}</p>
    </div>
  )
}
