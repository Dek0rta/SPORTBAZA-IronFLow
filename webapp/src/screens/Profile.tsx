import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Trophy, ChevronRight, RefreshCw, Share2, Pencil, TrendingUp, Check, X } from 'lucide-react'
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
  const losses      = profile?.losses     ?? 0
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

    const W = 400, H = 220
    canvas.width = W
    canvas.height = H

    // Background
    ctx.fillStyle = '#0f172a'
    ctx.fillRect(0, 0, W, H)

    // Gradient header strip
    const grd = ctx.createLinearGradient(0, 0, W, 0)
    const [c1, c2] = rankCfg.gradient.match(/#[0-9a-f]{6}/gi) ?? ['#475569', '#94a3b8']
    grd.addColorStop(0, c1)
    grd.addColorStop(1, c2)
    ctx.fillStyle = grd
    ctx.fillRect(0, 0, W, 4)

    // Avatar circle
    ctx.fillStyle = grd
    ctx.beginPath()
    ctx.roundRect(24, 24, 64, 64, 16)
    ctx.fill()
    ctx.fillStyle = '#000'
    ctx.font = 'bold 32px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(name[0]?.toUpperCase() ?? '?', 56, 67)

    // Name
    ctx.fillStyle = '#fff'
    ctx.font = 'bold 20px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText(name, 104, 48)

    // Rank badge
    ctx.fillStyle = grd
    ctx.beginPath()
    ctx.roundRect(104, 58, 120, 24, 12)
    ctx.fill()
    ctx.fillStyle = '#000'
    ctx.font = 'bold 12px sans-serif'
    ctx.fillText(`🏆 ${rank}`, 114, 75)

    // MMR
    ctx.fillStyle = '#6b7280'
    ctx.font = '12px sans-serif'
    ctx.fillText('MMR', 104, 100)
    ctx.fillStyle = '#fff'
    ctx.font = 'bold 24px sans-serif'
    ctx.fillText(String(mmr), 140, 100)

    // Stats row
    const stats = [
      { label: 'Турниры', val: tournaments },
      { label: 'Победы',  val: wins },
      { label: 'Поражения', val: losses },
    ]
    ctx.fillStyle = 'rgba(255,255,255,0.05)'
    ctx.beginPath()
    ctx.roundRect(24, 116, W - 48, 60, 12)
    ctx.fill()
    stats.forEach((s, i) => {
      const x = 60 + i * 110
      ctx.fillStyle = rankCfg.color
      ctx.font = 'bold 20px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(String(s.val), x, 146)
      ctx.fillStyle = '#6b7280'
      ctx.font = '10px sans-serif'
      ctx.fillText(s.label, x, 162)
    })

    // Bio
    if (bio) {
      ctx.fillStyle = '#9ca3af'
      ctx.font = '11px sans-serif'
      ctx.textAlign = 'left'
      ctx.fillText(bio.slice(0, 60), 24, 196)
    }

    // Watermark
    ctx.fillStyle = '#1e293b'
    ctx.font = '10px sans-serif'
    ctx.textAlign = 'right'
    ctx.fillText('SPORTBAZA · Iron Flow', W - 16, H - 10)

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

          {/* ── Player Card ─────────────────────────────────────── */}
          <motion.div variants={item} className="glass-card relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: rankCfg.gradient }} />

            {/* Share button */}
            <button
              onClick={shareProfile}
              className="absolute top-3 right-3 w-8 h-8 rounded-xl bg-white/5 flex items-center justify-center active:scale-90 transition-transform"
            >
              <Share2 size={15} className="text-gray-400" />
            </button>

            <div className="flex items-center gap-4">
              <div
                className="w-20 h-20 rounded-2xl flex items-center justify-center shrink-0 text-3xl font-black text-black"
                style={{ background: rankCfg.gradient, boxShadow: `0 0 32px ${rankCfg.shadow}` }}
              >
                {name[0]?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0 pr-8">
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

            {/* Bio */}
            <div className="mt-3 flex items-start gap-2">
              {editBio ? (
                <div className="flex-1 flex gap-2">
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
                <>
                  <p
                    className="flex-1 text-gray-500 text-xs italic cursor-pointer"
                    onClick={() => { setBioInput(bio); setEditBio(true) }}
                  >
                    {bio || 'Добавь девиз...'}
                  </p>
                  <button
                    onClick={() => { haptic.impact('light'); setBioInput(bio); setEditBio(true) }}
                    className="shrink-0 active:scale-90"
                  >
                    <Pencil size={12} className="text-gray-600" />
                  </button>
                </>
              )}
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
              {pinned.length > 0 && <span className="ml-2 text-neon-green/60">({pinned.length}/3 закреплено)</span>}
            </p>
            {equippedAchs.length === 0 ? (
              <div className="glass-card text-center py-6 text-gray-600 text-sm">
                Нет разблокированных наград
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-3">
                {equippedAchs.map(ach => {
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

          {/* ── Buttons row ─────────────────────────────────────── */}
          <motion.div variants={item} className="grid grid-cols-2 gap-3">
            <button
              onClick={() => { haptic.impact('light'); setAchOpen(true) }}
              className="glass-card flex items-center gap-3 py-4 active:scale-[0.98] transition-transform"
            >
              <div className="w-9 h-9 rounded-xl bg-amber-400/10 flex items-center justify-center shrink-0">
                <Trophy size={16} className="text-amber-400" />
              </div>
              <div className="text-left min-w-0">
                <p className="text-white font-semibold text-xs">Награды</p>
                <p className="text-gray-500 text-[10px]">{unlockedN} / {achievements.length}</p>
              </div>
            </button>

            <button
              onClick={() => { haptic.impact('light'); setStatsOpen(true) }}
              className="glass-card flex items-center gap-3 py-4 active:scale-[0.98] transition-transform"
            >
              <div className="w-9 h-9 rounded-xl bg-neon-green/10 flex items-center justify-center shrink-0">
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

      {/* ── Stats full-screen sheet ──────────────────────────────── */}
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
              className="h-12 rounded-2xl bg-neon-green/15 border border-neon-green/25 text-neon-green font-bold text-sm active:scale-95 transition-transform"
            >
              Скачать PNG
            </button>
            <button
              onClick={shareTelegram}
              className="h-12 rounded-2xl bg-white/5 border border-white/10 text-white font-bold text-sm active:scale-95 transition-transform"
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
                className={`rounded-2xl p-4 border flex flex-col gap-2 relative ${
                  ach.unlocked
                    ? 'bg-white/5 border-white/10 active:scale-[0.97] transition-transform cursor-pointer'
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

// Needed for canvas.roundRect in TypeScript
declare global {
  interface CanvasRenderingContext2D {
    roundRect(x: number, y: number, w: number, h: number, r: number): void
  }
}
