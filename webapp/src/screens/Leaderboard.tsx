import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw, ExternalLink } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { BottomSheet } from '../components/BottomSheet'
import { RANK_CONFIG } from '../data/mock'
import { api } from '../services/api'
import type { LeaderboardEntry, PublicProfile } from '../services/api'

const TOP3 = [
  { border: 'rgba(251,191,36,0.7)',  glow: 'rgba(251,191,36,0.18)', medal: '🥇' },
  { border: 'rgba(226,232,240,0.6)', glow: 'rgba(226,232,240,0.12)', medal: '🥈' },
  { border: 'rgba(245,158,11,0.55)', glow: 'rgba(245,158,11,0.14)', medal: '🥉' },
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
        <h1 className="text-white text-2xl font-bold mb-4">Ладдер</h1>
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

      {/* List */}
      <div className="flex-1 overflow-y-auto overscroll-contain px-4 space-y-2 pb-2">
        {loading ? (
          <div className="flex justify-center pt-12">
            <RefreshCw size={28} className="text-neon-green animate-spin" />
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
                const rc    = RANK_CONFIG[(p.tier as keyof typeof RANK_CONFIG)] ?? RANK_CONFIG.iron
                const top3  = i < 3 ? TOP3[i] : null
                const isMe  = p.telegram_id === user.id

                return (
                  <button
                    key={p.user_id}
                    onClick={() => openProfile(p)}
                    className="w-full rounded-2xl p-3 flex items-center gap-3 border text-left active:scale-[0.98] transition-transform"
                    style={{
                      background: isMe
                        ? 'rgba(57,255,20,0.07)'
                        : top3 ? 'rgba(255,255,255,0.05)' : 'rgba(255,255,255,0.025)',
                      borderColor: isMe
                        ? 'rgba(57,255,20,0.35)'
                        : top3 ? top3.border : 'rgba(255,255,255,0.07)',
                      boxShadow: top3 && !isMe ? `0 0 20px ${top3.glow}` : undefined,
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
                      {p.first_name[0]}
                    </div>

                    {/* Name + username + rank */}
                    <div className="flex-1 min-w-0">
                      <p className={`font-semibold text-sm truncate ${isMe ? 'text-neon-green' : 'text-white'}`}>
                        {p.first_name}{p.last_name ? ` ${p.last_name}` : ''}{isMe ? ' (Вы)' : ''}
                      </p>
                      <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                        <span className="text-[10px] font-bold" style={{ color: rc.color }}>
                          {p.rank}
                        </span>
                        {p.username && (
                          <>
                            <span className="text-gray-700 text-[9px]">·</span>
                            <span className="text-gray-500 text-[10px]">@{p.username}</span>
                          </>
                        )}
                      </div>
                      <div className="flex items-center gap-1 mt-0.5">
                        <span className="text-gray-600 text-[10px]">🏆 {p.tournaments_count} турн.</span>
                      </div>
                    </div>

                    {/* MMR */}
                    <div className="text-right shrink-0">
                      <p className="text-white font-black text-sm">{p.mmr}</p>
                      <p className="text-gray-500 text-[10px]">MMR</p>
                    </div>
                  </button>
                )
              })}
            </motion.div>
          </AnimatePresence>
        )}
      </div>

      {/* Sticky my position */}
      <div className="shrink-0 px-4 pb-2 pt-1 border-t border-white/5">
        <p className="text-gray-500 text-[10px] uppercase tracking-widest font-semibold mb-1.5">
          Ваша позиция
        </p>
        {myEntry ? (
          <MyRow entry={myEntry} rank={myRank || '—'} />
        ) : (
          <div className="rounded-2xl p-3 bg-white/[0.03] border border-white/[0.07] text-gray-500 text-xs text-center">
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
            <RefreshCw size={28} className="text-neon-green animate-spin" />
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

// ── Player profile sheet content ─────────────────────────────────────────────

function PlayerProfile({
  profile, entry, onTgLink,
}: {
  profile: PublicProfile
  entry: LeaderboardEntry
  onTgLink: () => void
}) {
  const rc = RANK_CONFIG[(profile.tier as keyof typeof RANK_CONFIG)] ?? RANK_CONFIG.iron
  const unlocked = profile.achievements.filter(a => a.unlocked)

  return (
    <div className="space-y-5">
      {/* Avatar + rank */}
      <div className="flex items-center gap-4">
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center font-black text-2xl text-black shrink-0"
          style={{ background: rc.gradient }}
        >
          {profile.first_name[0]}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-white font-bold text-lg leading-tight">
            {profile.first_name}{profile.last_name ? ` ${profile.last_name}` : ''}
          </p>
          {profile.username && (
            <p className="text-gray-500 text-xs">@{profile.username}</p>
          )}
          <p className="font-bold text-sm mt-0.5" style={{ color: rc.color }}>{profile.rank}</p>
        </div>
        {profile.username && (
          <button
            onClick={onTgLink}
            className="w-9 h-9 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center shrink-0 active:scale-95"
          >
            <ExternalLink size={15} className="text-gray-400" />
          </button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'MMR', value: profile.mmr },
          { label: 'Турниров', value: profile.tournaments },
          { label: 'Победы', value: profile.wins },
        ].map(s => (
          <div key={s.label} className="rounded-xl bg-white/5 p-3 text-center">
            <p className="text-white font-black text-lg">{s.value}</p>
            <p className="text-gray-500 text-[10px]">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Recent tournaments */}
      {profile.recent_tournaments.length > 0 && (
        <div>
          <p className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-2">
            Последние турниры
          </p>
          <div className="space-y-1.5">
            {profile.recent_tournaments.map((t, i) => (
              <div key={i} className="rounded-xl bg-white/[0.04] px-3 py-2 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-white text-xs font-semibold truncate">{t.name}</p>
                  <p className="text-gray-500 text-[10px]">{t.type}{t.category ? ` · ${t.category}` : ''}</p>
                </div>
                {t.total !== null && (
                  <p className="text-neon-green font-black text-sm shrink-0">{t.total} кг</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Achievements */}
      {unlocked.length > 0 && (
        <div>
          <p className="text-gray-400 text-xs font-semibold uppercase tracking-widest mb-2">
            Достижения ({unlocked.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {unlocked.slice(0, 6).map(a => (
              <div
                key={a.id}
                className="flex items-center gap-1.5 rounded-xl bg-white/5 px-2.5 py-1.5"
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
    <div className="rounded-2xl p-3 flex items-center gap-3 bg-neon-green/10 border border-neon-green/30">
      <span className="text-gray-400 font-bold text-sm w-8 text-center shrink-0">
        #{rank}
      </span>
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
          <span className="text-gray-600 text-[9px]">· 🏆 {entry.tournaments_count} турн.</span>
        </div>
      </div>
      <div className="text-right shrink-0">
        <p className="text-white font-black text-sm">{entry.mmr}</p>
        <p className="text-gray-500 text-[10px]">MMR</p>
      </div>
    </div>
  )
}
