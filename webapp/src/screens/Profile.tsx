import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Trophy, ChevronRight, RefreshCw } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { BottomSheet } from '../components/BottomSheet'
import { RANK_CONFIG, RARITY_CONFIG } from '../data/mock'
import { api } from '../services/api'
import type { UserProfile, Achievement } from '../services/api'

const item = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { ease: 'easeOut', duration: 0.4 } },
}
const container = { animate: { transition: { staggerChildren: 0.07 } } }

// Equipped = first 3 unlocked legendary/epic, or just first 3 unlocked
function pickEquipped(achievements: Achievement[]): Achievement[] {
  const unlocked = achievements.filter(a => a.unlocked)
  const priority = unlocked.filter(a => a.rarity === 'legendary' || a.rarity === 'epic')
  return (priority.length >= 3 ? priority : unlocked).slice(0, 3)
}

export function Profile() {
  const { user, haptic } = useTelegram()
  const [achOpen, setAchOpen]       = useState(false)
  const [profile, setProfile]       = useState<UserProfile | null>(null)
  const [loading, setLoading]       = useState(true)

  useEffect(() => {
    api.profile()
      .then(setProfile)
      .catch(() => setProfile(null))
      .finally(() => setLoading(false))
  }, [])

  const name = `${user.first_name}${user.last_name ? ` ${user.last_name}` : ''}`

  if (loading) return <Spinner />

  // Fallback to base state if API unavailable
  const rank       = profile?.rank       ?? 'Iron III'
  const tier       = (profile?.tier      ?? 'iron') as keyof typeof RANK_CONFIG
  const mmr        = profile?.mmr        ?? 500
  const mmrStart   = profile?.mmr_start  ?? 0
  const mmrNext    = profile?.mmr_next   ?? 650
  const wins       = profile?.wins       ?? 0
  const losses     = profile?.losses     ?? 0
  const tournaments = profile?.tournaments ?? 0
  const achievements = profile?.achievements ?? []

  const rankCfg    = RANK_CONFIG[tier] ?? RANK_CONFIG.iron
  const progress   = mmrNext > mmrStart
    ? Math.min(100, ((mmr - mmrStart) / (mmrNext - mmrStart)) * 100)
    : 100
  const equipped   = pickEquipped(achievements)
  const unlockedN  = achievements.filter(a => a.unlocked).length

  return (
    <div className="h-full overflow-y-auto overscroll-contain">
      <div className="px-4 pt-6 pb-8">
        <motion.div variants={container} initial="initial" animate="animate" className="space-y-4">

          {/* ── Player Card ─────────────────────────────────────── */}
          <motion.div variants={item} className="glass-card relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: rankCfg.gradient }} />

            <div className="flex items-center gap-4">
              <div
                className="w-20 h-20 rounded-2xl flex items-center justify-center shrink-0 text-3xl font-black text-black"
                style={{ background: rankCfg.gradient, boxShadow: `0 0 32px ${rankCfg.shadow}` }}
              >
                {name[0].toUpperCase()}
              </div>
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

            <div className="grid grid-cols-3 gap-2 mt-5 pt-4 border-t border-white/5">
              <StatCell label="Победы"    value={String(wins)}        color={rankCfg.color} />
              <StatCell label="Поражения" value={String(losses)}      color="#6b7280" />
              <StatCell label="Турниры"   value={String(tournaments)} color="#6b7280" />
            </div>
          </motion.div>

          {/* ── MMR Progress ─────────────────────────────────────── */}
          <motion.div variants={item} className="glass-card space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-400 text-xs uppercase tracking-widest font-semibold">Рейтинг (MMR)</span>
              <span className="text-white font-black text-lg">{mmr}</span>
            </div>
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
                До следующего:{' '}
                <span className="font-bold" style={{ color: rankCfg.color }}>
                  {Math.max(0, mmrNext - mmr)} очков
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
            {equipped.length === 0 ? (
              <div className="glass-card text-center py-6 text-gray-600 text-sm">
                Нет разблокированных наград
              </div>
            ) : (
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
                      <p className="text-white text-[10px] font-semibold text-center leading-tight">{ach.name}</p>
                      <span className="text-[9px] font-black uppercase tracking-wide" style={{ color: rc.color }}>
                        {rc.label}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
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
                    {unlockedN} / {achievements.length} разблокировано
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
          {achievements.map(ach => {
            const rc = RARITY_CONFIG[ach.rarity]
            return (
              <div
                key={ach.id}
                className={`rounded-2xl p-4 border flex flex-col gap-2 ${
                  ach.unlocked ? 'bg-white/5 border-white/10' : 'bg-white/[0.02] border-white/5 opacity-40'
                }`}
                style={ach.unlocked ? { boxShadow: `0 0 18px ${rc.glow}` } : {}}
              >
                <div className="flex items-start justify-between">
                  <span className="text-2xl">{ach.unlocked ? ach.icon : '🔒'}</span>
                  <span className="text-[9px] font-black uppercase tracking-wide"
                        style={{ color: ach.unlocked ? rc.color : '#4b5563' }}>
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

function Spinner() {
  return (
    <div className="h-full flex items-center justify-center">
      <RefreshCw size={28} className="text-neon-green animate-spin" />
    </div>
  )
}
