import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw, ExternalLink, Trophy } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { BottomSheet } from '../components/BottomSheet'
import { RANK_CONFIG } from '../data/mock'
import { api } from '../services/api'
import type { LeaderboardEntry, PublicProfile } from '../services/api'

// Top-3 podium visual config
const TOP3_CFG = [
  {
    medal: '🥇', rankColor: '#fbbf24',
    border: 'rgba(251,191,36,0.5)',
    glow: 'rgba(251,191,36,0.18)',
    bg: 'rgba(251,191,36,0.06)',
    innerBorder: 'rgba(251,191,36,0.15)',
  },
  {
    medal: '🥈', rankColor: '#cbd5e1',
    border: 'rgba(203,213,225,0.4)',
    glow: 'rgba(203,213,225,0.12)',
    bg: 'rgba(203,213,225,0.04)',
    innerBorder: 'rgba(203,213,225,0.1)',
  },
  {
    medal: '🥉', rankColor: '#f59e0b',
    border: 'rgba(245,158,11,0.4)',
    glow: 'rgba(245,158,11,0.14)',
    bg: 'rgba(245,158,11,0.05)',
    innerBorder: 'rgba(245,158,11,0.12)',
  },
]

export function Leaderboard() {
  const { haptic, tg, user } = useTelegram()
  const [tab, setTab]                 = useState<'global' | 'league'>('global')
  const [all, setAll]                 = useState<LeaderboardEntry[]>([])
  const [loading, setLoading]         = useState(true)
  const [selectedEntry, setSelectedEntry] = useState<LeaderboardEntry | null>(null)
  const [profile, setProfile]         = useState<PublicProfile | null>(null)
  const [profileLoading, setProfileLoading] = useState(false)

  useEffect(() => {
    api.leaderboard()
      .then(setAll)
      .catch(() => setAll([]))
      .finally(() => setLoading(false))
  }, [])

  const myEntry  = all.find(p => p.telegram_id === user.id)
  const myTier   = myEntry?.tier ?? 'iron'
  const players  = tab === 'global' ? all : all.filter(p => p.tier === myTier)
  const myRank   = players.findIndex(p => p.telegram_id === user.id) + 1

  const openProfile = async (entry: LeaderboardEntry) => {
    haptic.impact('light')
    setSelectedEntry(entry)
    setProfile(null)
    setProfileLoading(true)
    try {
      const data = await api.userProfile(entry.telegram_id)
      setProfile(data)
    } catch { /* silent */ } finally {
      setProfileLoading(false)
    }
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">

      {/* Header */}
      <div className="shrink-0 px-4 pt-6 pb-3">
        <h1 className="gradient-text-gold text-2xl font-bold mb-4">Ладдер</h1>
        <div className="grid grid-cols-2 gap-1 rounded-2xl p-1" style={{ background: 'rgba(255,255,255,0.05)' }}>
          {(['global', 'league'] as const).map(id => (
            <button
              key={id}
              onClick={() => { haptic.impact('light'); setTab(id) }}
              className={`py-2.5 rounded-xl text-sm font-bold transition-all ${
                tab === id ? 'text-black' : 'text-gray-500'
              }`}
              style={tab === id ? {
                background: 'linear-gradient(135deg,#b45309,#fbbf24)',
                boxShadow: '0 0 18px rgba(251,191,36,0.35)',
              } : {}}
            >
              {id === 'global' ? '🌍 Глобальный' : '⚔️ Моя лига'}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto overscroll-contain px-4 space-y-2 pb-2">
        {loading ? (
          <div className="flex justify-center pt-12">
            <RefreshCw size={28} className="text-yellow-400 animate-spin" />
          </div>
        ) : players.length === 0 ? (
          <div className="text-center pt-12 text-gray-500 text-sm">
            Нет данных — атлеты ещё не участвовали в завершённых турнирах
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="space-y-2"
            >
              {players.map((p, i) => {
                const rc   = RANK_CONFIG[(p.tier as keyof typeof RANK_CONFIG)] ?? RANK_CONFIG.iron
                const top3 = i < 3 ? TOP3_CFG[i] : null
                const isMe = p.telegram_id === user.id

                if (top3) {
                  // ── Podium card for top 3 ──────────────────────
                  return (
                    <motion.button
                      key={p.user_id}
                      initial={{ opacity: 0, y: 16 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.07 }}
                      onClick={() => openProfile(p)}
                      className="w-full text-left rounded-3xl overflow-hidden active:scale-[0.98] transition-transform"
                      style={{
                        background: isMe ? 'rgba(57,255,20,0.07)' : top3.bg,
                        border: `1px solid ${isMe ? 'rgba(57,255,20,0.4)' : top3.border}`,
                        boxShadow: `0 0 28px ${top3.glow}`,
                      }}
                    >
                      {/* Top gradient strip */}
                      <div className="h-0.5" style={{
                        background: isMe
                          ? 'linear-gradient(90deg,#39ff14,#22c55e)'
                          : `linear-gradient(90deg, ${top3.rankColor}88, ${top3.rankColor})`,
                      }} />
                      <div className="px-4 py-3.5 flex items-center gap-3">
                        {/* Medal */}
                        <div className="flex flex-col items-center shrink-0 w-10">
                          <span className="text-2xl leading-none">{top3.medal}</span>
                          <span className="text-[10px] font-black mt-0.5" style={{ color: top3.rankColor }}>
                            #{i + 1}
                          </span>
                        </div>

                        {/* Avatar */}
                        <div
                          className="w-12 h-12 rounded-2xl flex items-center justify-center font-black text-base text-black shrink-0"
                          style={{ background: rc.gradient, boxShadow: `0 0 16px ${rc.shadow}` }}
                        >
                          {p.first_name[0]}
                        </div>

                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          <p className={`font-bold text-sm truncate ${isMe ? 'text-neon-green' : 'text-white'}`}>
                            {p.first_name}{p.last_name ? ` ${p.last_name}` : ''}{isMe ? ' (Вы)' : ''}
                          </p>
                          <p className="text-[11px] font-bold mt-0.5" style={{ color: rc.color }}>{p.rank}</p>
                          {p.username && (
                            <p className="text-gray-600 text-[10px]">@{p.username}</p>
                          )}
                        </div>

                        {/* MMR */}
                        <div className="text-right shrink-0">
                          <p className="font-black text-lg leading-none" style={{ color: top3.rankColor }}>{p.mmr}</p>
                          <p className="text-gray-500 text-[10px] mt-0.5">MMR</p>
                          <p className="text-gray-600 text-[10px]">🏆 {p.tournaments_count}</p>
                        </div>
                      </div>
                    </motion.button>
                  )
                }

                // ── Regular row ───────────────────────────────────
                return (
                  <motion.button
                    key={p.user_id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: Math.min(i * 0.04, 0.3) }}
                    onClick={() => openProfile(p)}
                    className="w-full rounded-2xl p-3 flex items-center gap-3 text-left active:scale-[0.98] transition-transform overflow-hidden relative"
                    style={{
                      background: isMe ? 'rgba(57,255,20,0.06)' : 'rgba(255,255,255,0.03)',
                      border: `1px solid ${isMe ? 'rgba(57,255,20,0.3)' : 'rgba(255,255,255,0.06)'}`,
                    }}
                  >
                    {/* Tier color left accent */}
                    <div
                      className="absolute left-0 top-0 bottom-0 w-0.5 rounded-l-full"
                      style={{ background: isMe ? '#39ff14' : rc.color }}
                    />

                    {/* Position */}
                    <span className="text-gray-600 font-bold text-sm w-8 text-center shrink-0 ml-1">
                      #{i + 1}
                    </span>

                    {/* Avatar */}
                    <div
                      className="w-9 h-9 rounded-xl flex items-center justify-center font-black text-sm text-black shrink-0"
                      style={{ background: rc.gradient }}
                    >
                      {p.first_name[0]}
                    </div>

                    {/* Name + rank */}
                    <div className="flex-1 min-w-0">
                      <p className={`font-semibold text-sm truncate ${isMe ? 'text-neon-green' : 'text-white'}`}>
                        {p.first_name}{p.last_name ? ` ${p.last_name}` : ''}{isMe ? ' (Вы)' : ''}
                      </p>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[10px] font-bold" style={{ color: rc.color }}>{p.rank}</span>
                        {p.username && (
                          <span className="text-gray-600 text-[10px]">· @{p.username}</span>
                        )}
                      </div>
                    </div>

                    {/* MMR + tournaments */}
                    <div className="text-right shrink-0">
                      <p className="text-white font-black text-sm">{p.mmr}</p>
                      <p className="text-gray-600 text-[10px]">🏆 {p.tournaments_count}</p>
                    </div>
                  </motion.button>
                )
              })}
            </motion.div>
          </AnimatePresence>
        )}
      </div>

      {/* My position sticky bar */}
      <div className="shrink-0 px-4 pb-2 pt-2" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <p className="text-gray-600 text-[10px] uppercase tracking-widest font-semibold mb-1.5">
          Ваша позиция
        </p>
        {myEntry ? (
          <MyRow entry={myEntry} rank={myRank || '—'} />
        ) : (
          <div className="rounded-2xl p-3 text-gray-500 text-xs text-center" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
            Участвуйте в турнирах, чтобы попасть в рейтинг
          </div>
        )}
      </div>

      {/* ── Participant profile BottomSheet ───────────────────── */}
      <BottomSheet
        isOpen={selectedEntry !== null}
        onClose={() => { setSelectedEntry(null); setProfile(null) }}
        title={selectedEntry ? `${selectedEntry.first_name}${selectedEntry.last_name ? ` ${selectedEntry.last_name}` : ''}` : ''}
      >
        {profileLoading && (
          <div className="flex justify-center py-8">
            <RefreshCw size={28} className="text-yellow-400 animate-spin" />
          </div>
        )}
        {profile && selectedEntry && (
          <PlayerProfile profile={profile} entry={selectedEntry} onTgLink={() => {
            if (profile.username) tg?.openTelegramLink(`https://t.me/${profile.username}`)
          }} />
        )}
      </BottomSheet>
    </div>
  )
}

// ── Player profile sheet ──────────────────────────────────────────────────────

function PlayerProfile({
  profile, entry, onTgLink,
}: {
  profile: PublicProfile
  entry: LeaderboardEntry
  onTgLink: () => void
}) {
  const rc      = RANK_CONFIG[(profile.tier as keyof typeof RANK_CONFIG)] ?? RANK_CONFIG.iron
  const unlocked = profile.achievements.filter(a => a.unlocked)

  return (
    <div className="space-y-5">
      {/* Avatar + rank hero */}
      <div className="rounded-3xl p-4 flex items-center gap-4 relative overflow-hidden"
        style={{ background: `${rc.color}0c`, border: `1px solid ${rc.color}25` }}>
        <div className="absolute -top-6 -right-6 w-28 h-28 rounded-full opacity-15 blur-2xl pointer-events-none"
          style={{ background: rc.color }} />
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center font-black text-2xl text-black shrink-0"
          style={{ background: rc.gradient, boxShadow: `0 0 20px ${rc.shadow}` }}
        >
          {profile.first_name[0]}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-white font-bold text-lg leading-tight">
            {profile.first_name}{profile.last_name ? ` ${profile.last_name}` : ''}
          </p>
          {profile.username && (
            <p className="text-gray-500 text-xs mt-0.5">@{profile.username}</p>
          )}
          <div
            className="inline-flex items-center gap-1.5 mt-2 px-3 py-1 rounded-full text-xs font-black text-black"
            style={{ background: rc.gradient }}
          >
            <Trophy size={10} /> {profile.rank}
          </div>
        </div>
        {profile.username && (
          <button
            onClick={onTgLink}
            className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 active:scale-95"
            style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)' }}
          >
            <ExternalLink size={15} className="text-gray-400" />
          </button>
        )}
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'MMR',      value: profile.mmr,         color: rc.color },
          { label: 'Турниры',  value: profile.tournaments,  color: '#94a3b8' },
          { label: 'Победы',   value: profile.wins,         color: '#39ff14' },
        ].map(s => (
          <div
            key={s.label}
            className="rounded-2xl p-3 text-center"
            style={{ background: `${s.color}0e`, border: `1px solid ${s.color}22` }}
          >
            <p className="font-black text-xl leading-none" style={{ color: s.color }}>{s.value}</p>
            <p className="text-gray-500 text-[10px] mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Recent tournaments */}
      {profile.recent_tournaments.length > 0 && (
        <div>
          <p className="text-gray-400 text-[10px] font-semibold uppercase tracking-widest mb-2">
            Последние турниры
          </p>
          <div className="space-y-1.5">
            {profile.recent_tournaments.map((t, i) => (
              <div key={i} className="rounded-2xl px-3 py-2.5 flex items-center gap-3"
                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
                <div className="flex-1 min-w-0">
                  <p className="text-white text-xs font-semibold truncate">{t.name}</p>
                  <p className="text-gray-500 text-[10px]">{t.type}{t.category ? ` · ${t.category}` : ''}</p>
                </div>
                {t.total !== null && (
                  <p className="font-black text-sm shrink-0" style={{ color: '#39ff14' }}>{t.total} кг</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Achievements */}
      {unlocked.length > 0 && (
        <div>
          <p className="text-gray-400 text-[10px] font-semibold uppercase tracking-widest mb-2">
            Достижения ({unlocked.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {unlocked.slice(0, 6).map(a => (
              <div
                key={a.id}
                className="flex items-center gap-1.5 rounded-xl px-2.5 py-1.5"
                style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}
                title={a.desc}
              >
                <span className="text-base">{a.icon}</span>
                <span className="text-white text-xs font-semibold">{a.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function MyRow({ entry, rank }: { entry: LeaderboardEntry; rank: number | string }) {
  const rc = RANK_CONFIG[(entry.tier as keyof typeof RANK_CONFIG)] ?? RANK_CONFIG.iron
  return (
    <div className="rounded-2xl p-3 flex items-center gap-3 relative overflow-hidden"
      style={{ background: 'rgba(57,255,20,0.07)', border: '1px solid rgba(57,255,20,0.25)' }}>
      <div className="absolute left-0 top-0 bottom-0 w-0.5 rounded-l-full bg-neon-green" />
      <span className="text-gray-400 font-bold text-sm w-8 text-center shrink-0 ml-1">#{rank}</span>
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center font-black text-sm text-black shrink-0"
        style={{ background: rc.gradient }}
      >
        {entry.first_name[0]}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-neon-green font-semibold text-sm truncate">
          {entry.first_name}{entry.last_name ? ` ${entry.last_name}` : ''} (Вы)
        </p>
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-bold" style={{ color: rc.color }}>{entry.rank}</span>
          <span className="text-gray-600 text-[9px]">· 🏆 {entry.tournaments_count}</span>
        </div>
      </div>
      <div className="text-right shrink-0">
        <p className="text-white font-black text-sm">{entry.mmr}</p>
        <p className="text-gray-500 text-[10px]">MMR</p>
      </div>
    </div>
  )
}
