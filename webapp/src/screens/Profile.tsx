import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Trophy, RefreshCw, Share2, Pencil, TrendingUp, Check, X, CalendarDays } from 'lucide-react'
import { useTelegram } from '../hooks/useTelegram'
import { BottomSheet } from '../components/BottomSheet'
import { RANK_CONFIG, RARITY_CONFIG } from '../data/mock'
import { api } from '../services/api'
import { Stats } from './Stats'
import type { UserProfile, Achievement } from '../services/api'

const PINNED_KEY = (id: number) => `sportbaza_pinned_${id}`

function getPinned(tgId: number): string[] {
  try { return JSON.parse(localStorage.getItem(PINNED_KEY(tgId)) || 'null') ?? [] }
  catch { return [] }
}
function setPinned(tgId: number, ids: string[]) {
  localStorage.setItem(PINNED_KEY(tgId), JSON.stringify(ids))
}

const item = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { ease: 'easeOut', duration: 0.4 } },
}
const container = { animate: { transition: { staggerChildren: 0.07 } } }

export function Profile() {
  const { user, haptic, tg } = useTelegram()
  const [achOpen, setAchOpen]     = useState(false)
  const [statsOpen, setStatsOpen] = useState(false)
  const [shareOpen, setShareOpen] = useState(false)
  const [editBio, setEditBio]     = useState(false)
  const [profile, setProfile]     = useState<UserProfile | null>(null)
  const [loading, setLoading]     = useState(true)
  const [bio, setBio]             = useState('')
  const [bioInput, setBioInput]   = useState('')
  const [savingBio, setSavingBio] = useState(false)
  const [pinned, setPinnedState]  = useState<string[]>([])
  const canvasRef                 = useRef<HTMLCanvasElement>(null)

  const tgId = user.id

  useEffect(() => {
    api.profile()
      .then(p => { setProfile(p); setBio(p.bio ?? '') })
      .catch(() => setProfile(null))
      .finally(() => setLoading(false))
    setPinnedState(getPinned(tgId))
  }, [tgId])

  const name = `${user.first_name}${user.last_name ? ` ${user.last_name}` : ''}`

  if (loading) return <Spinner />

  const rank        = profile?.rank       ?? 'Iron III'
  const tier        = (profile?.tier      ?? 'iron') as keyof typeof RANK_CONFIG
  const mmr         = profile?.mmr        ?? 500
  const mmrStart    = profile?.mmr_start  ?? 0
  const mmrNext     = profile?.mmr_next   ?? 650
  const wins        = profile?.wins       ?? 0
  const tournaments = profile?.tournaments ?? 0
  const achievements = profile?.achievements ?? []

  const rankCfg  = RANK_CONFIG[tier] ?? RANK_CONFIG.iron
  const progress = mmrNext > mmrStart
    ? Math.min(100, ((mmr - mmrStart) / (mmrNext - mmrStart)) * 100)
    : 100

  // Equipped: pinned first, then auto-pick legendary/epic
  const equippedAchs: Achievement[] = (() => {
    if (pinned.length > 0) {
      const pinnedAchs = pinned
        .map(id => achievements.find(a => a.id === id && a.unlocked))
        .filter(Boolean) as Achievement[]
      if (pinnedAchs.length > 0) return pinnedAchs.slice(0, 3)
    }
    const unlocked = achievements.filter(a => a.unlocked)
    const priority = unlocked.filter(a => a.rarity === 'legendary' || a.rarity === 'epic')
    return (priority.length >= 3 ? priority : unlocked).slice(0, 3)
  })()

  const unlockedN = achievements.filter(a => a.unlocked).length

  const togglePin = (achId: string) => {
    haptic.impact('light')
    setPinnedState(prev => {
      const next = prev.includes(achId)
        ? prev.filter(id => id !== achId)
        : prev.length < 3 ? [...prev, achId] : prev
      setPinned(tgId, next)
      return next
    })
  }

  const saveBio = async () => {
    setSavingBio(true)
    try {
      await api.updateBio(bioInput.trim() || null)
      setBio(bioInput.trim())
      setEditBio(false)
    } catch { /* silent */ } finally {
      setSavingBio(false)
    }
  }

  const shareProfile = () => {
    haptic.impact('medium')
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = 400, H = 210
    canvas.width = W
    canvas.height = H

    // Background
    ctx.fillStyle = '#0f172a'
    ctx.fillRect(0, 0, W, H)

    // Gradient header strip (top + left)
    const [c1, c2] = rankCfg.gradient.match(/#[0-9a-f]{6}/gi) ?? ['#475569', '#94a3b8']
    const grd = ctx.createLinearGradient(0, 0, W, 0)
    grd.addColorStop(0, c1)
    grd.addColorStop(1, c2)
    ctx.fillStyle = grd
    ctx.fillRect(0, 0, W, 5)
    ctx.fillRect(0, 0, 5, H)

    // Avatar circle
    ctx.fillStyle = grd
    ctx.beginPath()
    ctx.roundRect(20, 20, 70, 70, 16)
    ctx.fill()
    ctx.fillStyle = '#000'
    ctx.font = 'bold 34px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(name[0]?.toUpperCase() ?? '?', 55, 67)

    // Name
    ctx.fillStyle = '#ffffff'
    ctx.font = 'bold 20px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText(name, 106, 44)

    // Username
    if (user.username) {
      ctx.fillStyle = '#6b7280'
      ctx.font = '12px sans-serif'
      ctx.fillText(`@${user.username}`, 106, 62)
    }

    // Rank badge
    ctx.fillStyle = grd
    ctx.beginPath()
    ctx.roundRect(106, user.username ? 72 : 60, 116, 22, 11)
    ctx.fill()
    ctx.fillStyle = '#000'
    ctx.font = 'bold 11px sans-serif'
    ctx.fillText(`🏆 ${rank}`, 118, user.username ? 87 : 75)

    // MMR label
    ctx.fillStyle = '#6b7280'
    ctx.font = '11px sans-serif'
    ctx.fillText('MMR', 238, user.username ? 87 : 75)
    ctx.fillStyle = rankCfg.color
    ctx.font = 'bold 22px sans-serif'
    ctx.fillText(String(mmr), 268, user.username ? 87 : 75)

    // Stats row
    const stats = [
      { label: 'Турниры', val: tournaments },
      { label: 'Победы',  val: wins },
    ]
    ctx.fillStyle = 'rgba(255,255,255,0.04)'
    ctx.beginPath()
    ctx.roundRect(20, 108, W - 40, 62, 12)
    ctx.fill()
    stats.forEach((s, i) => {
      const x = 80 + i * 140
      ctx.fillStyle = rankCfg.color
      ctx.font = 'bold 24px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(String(s.val), x, 140)
      ctx.fillStyle = '#6b7280'
      ctx.font = '10px sans-serif'
      ctx.fillText(s.label, x, 158)
    })

    // Bio
    if (bio) {
      ctx.fillStyle = '#9ca3af'
      ctx.font = 'italic 11px sans-serif'
      ctx.textAlign = 'left'
      ctx.fillText(`"${bio.slice(0, 55)}"`, 20, 195)
    }

    // Watermark
    ctx.fillStyle = '#334155'
    ctx.font = '10px sans-serif'
    ctx.textAlign = 'right'
    ctx.fillText('SPORTBAZA · Iron Flow', W - 16, H - 8)

    setShareOpen(true)
  }

  const downloadCard = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    const link = document.createElement('a')
    link.download = `sportbaza-${name.replace(/\s/g, '_')}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
    haptic.success()
  }

  const shareTelegram = () => {
    const text = `🏆 ${name}\n⚡ ${rank} · ${mmr} MMR\n🏅 Турниров: ${tournaments} · Побед: ${wins}\n\n#SPORTBAZA #IronFlow`
    tg?.switchInlineQuery(text)
    haptic.success()
  }

  return (
    <div className="h-full overflow-y-auto overscroll-contain">
      <canvas ref={canvasRef} className="hidden" />
      <div className="px-4 pt-6 pb-8">
        <motion.div variants={container} initial="initial" animate="animate" className="space-y-4">

          {/* ── Hero Card ───────────────────────────────────────────── */}
          <motion.div variants={item} className="relative overflow-hidden rounded-3xl"
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}
          >
            {/* Top gradient bar */}
            <div className="absolute top-0 left-0 right-0 h-1 rounded-t-3xl" style={{ background: rankCfg.gradient }} />

            {/* Subtle glow blob */}
            <div
              className="absolute -top-10 -right-10 w-48 h-48 rounded-full opacity-10 blur-3xl pointer-events-none"
              style={{ background: rankCfg.color }}
            />

            <div className="px-5 pt-6 pb-5">
              {/* Share button */}
              <button
                onClick={shareProfile}
                className="absolute top-4 right-4 w-9 h-9 rounded-2xl flex items-center justify-center active:scale-90 transition-transform"
                style={{ background: 'rgba(255,255,255,0.06)' }}
              >
                <Share2 size={15} className="text-gray-400" />
              </button>

              {/* Avatar + name */}
              <div className="flex items-center gap-4">
                <div className="relative shrink-0">
                  <div
                    className="w-[72px] h-[72px] rounded-2xl flex items-center justify-center text-3xl font-black text-black"
                    style={{ background: rankCfg.gradient, boxShadow: `0 0 28px ${rankCfg.shadow}, 0 0 56px ${rankCfg.shadow}40` }}
                  >
                    {name[0]?.toUpperCase()}
                  </div>
                </div>

                <div className="flex-1 min-w-0 pr-10">
                  <h1 className="text-white font-bold text-xl leading-tight truncate">{name}</h1>
                  {user.username && (
                    <p className="text-gray-500 text-xs mt-0.5">@{user.username}</p>
                  )}
                  <div
                    className="inline-flex items-center gap-1.5 mt-2 px-3 py-1.5 rounded-full text-[11px] font-black text-black"
                    style={{ background: rankCfg.gradient }}
                  >
                    <Trophy size={10} />
                    {rank}
                  </div>
                </div>
              </div>

              {/* Bio */}
              <div className="mt-4">
                {editBio ? (
                  <div className="flex gap-2">
                    <input
                      autoFocus
                      maxLength={150}
                      value={bioInput}
                      onChange={e => setBioInput(e.target.value)}
                      placeholder="Девиз или описание..."
                      className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white text-sm placeholder:text-gray-600 outline-none focus:border-neon-green/40"
                    />
                    <button
                      onClick={saveBio}
                      disabled={savingBio}
                      className="w-9 h-9 rounded-xl bg-neon-green/20 flex items-center justify-center active:scale-90 shrink-0"
                    >
                      <Check size={15} className="text-neon-green" />
                    </button>
                    <button
                      onClick={() => setEditBio(false)}
                      className="w-9 h-9 rounded-xl bg-white/5 flex items-center justify-center active:scale-90 shrink-0"
                    >
                      <X size={15} className="text-gray-400" />
                    </button>
                  </div>
                ) : (
                  <button
                    className="flex items-center gap-2 group w-full text-left"
                    onClick={() => { haptic.impact('light'); setBioInput(bio); setEditBio(true) }}
                  >
                    <p className="flex-1 text-gray-500 text-xs italic leading-relaxed">
                      {bio || 'Добавь девиз...'}
                    </p>
                    <Pencil size={11} className="text-gray-700 group-active:text-gray-400 shrink-0 transition-colors" />
                  </button>
                )}
              </div>

              {/* Stats */}
              <div
                className="grid grid-cols-2 gap-3 mt-5 pt-4"
                style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}
              >
                <StatCell
                  icon={<Trophy size={14} />}
                  label="Победы"
                  value={String(wins)}
                  color={rankCfg.color}
                />
                <StatCell
                  icon={<CalendarDays size={14} />}
                  label="Турниры"
                  value={String(tournaments)}
                  color="#94a3b8"
                />
              </div>
            </div>
          </motion.div>

          {/* ── MMR Progress ─────────────────────────────────────── */}
          <motion.div variants={item}
            className="rounded-3xl px-5 py-5 space-y-4"
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-400 text-[10px] uppercase tracking-widest font-semibold">Рейтинг</p>
                <p className="text-white font-black text-3xl mt-0.5 leading-none">{mmr} <span className="text-gray-500 text-sm font-normal">MMR</span></p>
              </div>
              <div
                className="px-4 py-2 rounded-2xl text-xs font-black"
                style={{ background: `${rankCfg.color}18`, color: rankCfg.color, border: `1px solid ${rankCfg.color}30` }}
              >
                {rank}
              </div>
            </div>

            <div className="space-y-2">
              <div className="h-2.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                <motion.div
                  className="h-full rounded-full"
                  style={{ background: rankCfg.gradient }}
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 1.2, ease: 'easeOut', delay: 0.3 }}
                />
              </div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-gray-600">
                  До следующего:{' '}
                  <span className="font-bold" style={{ color: rankCfg.color }}>
                    {Math.max(0, mmrNext - mmr)} очков
                  </span>
                </span>
                <span className="text-gray-600 font-medium">{Math.round(progress)}%</span>
              </div>
            </div>
          </motion.div>

          {/* ── Equipped Achievements ───────────────────────────── */}
          <motion.div variants={item}>
            <div className="flex items-center justify-between mb-3">
              <p className="text-gray-400 text-[10px] font-semibold uppercase tracking-widest">
                Экипированные награды
              </p>
              {pinned.length > 0 && (
                <span className="text-[10px] text-neon-green/60 font-medium">{pinned.length}/3 закреплено</span>
              )}
            </div>
            {equippedAchs.length === 0 ? (
              <div
                className="rounded-3xl text-center py-7 text-gray-600 text-sm"
                style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
              >
                Нет разблокированных наград
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-3">
                {equippedAchs.map(ach => {
                  const rc = RARITY_CONFIG[ach.rarity]
                  return (
                    <div
                      key={ach.id}
                      className="rounded-3xl flex flex-col items-center gap-2 py-5 px-2"
                      style={{
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.08)',
                        boxShadow: `0 0 20px ${rc.glow}`,
                      }}
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

          {/* ── Action Buttons ───────────────────────────────────── */}
          <motion.div variants={item} className="grid grid-cols-2 gap-3">
            <button
              onClick={() => { haptic.impact('light'); setAchOpen(true) }}
              className="flex items-center gap-3 px-4 py-4 rounded-3xl active:scale-[0.97] transition-transform"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}
            >
              <div
                className="w-10 h-10 rounded-2xl flex items-center justify-center shrink-0"
                style={{ background: 'rgba(251,191,36,0.12)' }}
              >
                <Trophy size={16} className="text-amber-400" />
              </div>
              <div className="text-left min-w-0">
                <p className="text-white font-semibold text-xs">Награды</p>
                <p className="text-gray-500 text-[10px]">{unlockedN} / {achievements.length}</p>
              </div>
            </button>

            <button
              onClick={() => { haptic.impact('light'); setStatsOpen(true) }}
              className="flex items-center gap-3 px-4 py-4 rounded-3xl active:scale-[0.97] transition-transform"
              style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}
            >
              <div
                className="w-10 h-10 rounded-2xl flex items-center justify-center shrink-0"
                style={{ background: 'rgba(57,255,20,0.08)' }}
              >
                <TrendingUp size={16} className="text-neon-green" />
              </div>
              <div className="text-left">
                <p className="text-white font-semibold text-xs">Статистика</p>
                <p className="text-gray-500 text-[10px]">Графики прогресса</p>
              </div>
            </button>
          </motion.div>

        </motion.div>
      </div>

      {/* ── Stats sheet ──────────────────────────────────────────── */}
      <BottomSheet isOpen={statsOpen} onClose={() => setStatsOpen(false)} title="Статистика">
        <div className="max-h-[70vh] overflow-y-auto overscroll-contain -mx-4 px-4">
          <Stats />
        </div>
      </BottomSheet>

      {/* ── Share sheet ──────────────────────────────────────────── */}
      <BottomSheet isOpen={shareOpen} onClose={() => setShareOpen(false)} title="Поделиться профилем">
        <div className="space-y-4">
          <div className="rounded-2xl overflow-hidden bg-slate-900 flex justify-center p-2">
            {canvasRef.current && (
              <img
                src={canvasRef.current.toDataURL()}
                alt="Profile card"
                className="rounded-xl w-full max-w-sm"
              />
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={downloadCard}
              className="h-12 rounded-2xl font-bold text-sm active:scale-95 transition-transform text-neon-green"
              style={{ background: 'rgba(57,255,20,0.1)', border: '1px solid rgba(57,255,20,0.2)' }}
            >
              Скачать PNG
            </button>
            <button
              onClick={shareTelegram}
              className="h-12 rounded-2xl font-bold text-sm active:scale-95 transition-transform text-white"
              style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}
            >
              В Telegram
            </button>
          </div>
          <p className="text-gray-600 text-[10px] text-center">Или сделай скриншот и сохрани в галерею</p>
        </div>
      </BottomSheet>

      {/* ── Achievements Modal ──────────────────────────────────── */}
      <BottomSheet isOpen={achOpen} onClose={() => setAchOpen(false)} title="Коллекция наград">
        <p className="text-gray-500 text-xs mb-3 text-center">
          Нажми на разблокированную награду чтобы закрепить её (макс. 3)
        </p>
        <div className="grid grid-cols-2 gap-3 max-h-[58vh] overflow-y-auto overscroll-contain pb-1">
          {achievements.map(ach => {
            const rc = RARITY_CONFIG[ach.rarity]
            const isPinned = pinned.includes(ach.id)
            return (
              <div
                key={ach.id}
                onClick={() => ach.unlocked && togglePin(ach.id)}
                className={`rounded-2xl p-4 border flex flex-col gap-2 relative transition-transform ${
                  ach.unlocked
                    ? 'bg-white/5 border-white/10 active:scale-[0.97] cursor-pointer'
                    : 'bg-white/[0.02] border-white/5 opacity-40'
                } ${isPinned ? 'ring-2 ring-neon-green/50' : ''}`}
                style={ach.unlocked ? { boxShadow: `0 0 18px ${rc.glow}` } : {}}
              >
                {isPinned && (
                  <span className="absolute top-2 right-2 text-[10px] font-black text-neon-green">📌</span>
                )}
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

function StatCell({
  icon, label, value, color,
}: {
  icon: React.ReactNode
  label: string
  value: string
  color: string
}) {
  return (
    <div
      className="flex items-center gap-3 px-3 py-3 rounded-2xl"
      style={{ background: `${color}10`, border: `1px solid ${color}20` }}
    >
      <div
        className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
        style={{ color, background: `${color}15` }}
      >
        {icon}
      </div>
      <div>
        <p className="font-black text-lg leading-none" style={{ color }}>{value}</p>
        <p className="text-gray-500 text-[10px] mt-0.5">{label}</p>
      </div>
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

// Needed for canvas.roundRect in TypeScript
declare global {
  interface CanvasRenderingContext2D {
    roundRect(x: number, y: number, w: number, h: number, r: number): void
  }
}
