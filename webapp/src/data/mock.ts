export type Tier    = 'iron' | 'bronze' | 'silver' | 'gold' | 'elite'
export type Rarity  = 'common' | 'rare' | 'epic' | 'legendary'
export type RegStatus = 'approved' | 'pending' | 'rejected'

export interface Achievement {
  id: number
  name: string
  icon: string
  rarity: Rarity
  unlocked: boolean
  desc: string
}

export interface LeaderboardPlayer {
  id: number
  name: string
  rank: string
  tier: Tier
  mmr: number
  isMe: boolean
}

export interface Tournament {
  id: number
  name: string
  date: string
  location: string
  prize: string
  discipline: string
  slotsTotal: number
  slotsLeft: number
}

export interface MyRegistration {
  id: number
  name: string
  date: string
  location: string
  discipline: string
  weightClass: string
  status: RegStatus
  qrToken: string
  rules: string[]
}

export const RANK_CONFIG: Record<Tier, {
  label: string
  gradient: string
  color: string
  shadow: string
}> = {
  iron:   { label: 'Железо',  gradient: 'linear-gradient(135deg,#475569,#94a3b8)', color: '#94a3b8', shadow: 'rgba(148,163,184,0.3)' },
  bronze: { label: 'Бронза',  gradient: 'linear-gradient(135deg,#92400e,#f59e0b)', color: '#f59e0b', shadow: 'rgba(245,158,11,0.35)' },
  silver: { label: 'Серебро', gradient: 'linear-gradient(135deg,#64748b,#e2e8f0)', color: '#e2e8f0', shadow: 'rgba(226,232,240,0.25)' },
  gold:   { label: 'Золото',  gradient: 'linear-gradient(135deg,#b45309,#fbbf24)', color: '#fbbf24', shadow: 'rgba(251,191,36,0.4)' },
  elite:  { label: 'Элита',   gradient: 'linear-gradient(135deg,#6d28d9,#ec4899)', color: '#a855f7', shadow: 'rgba(168,85,247,0.45)' },
}

export const RARITY_CONFIG: Record<Rarity, { label: string; color: string; glow: string }> = {
  common:    { label: 'Обычная',    color: '#6b7280', glow: 'rgba(107,114,128,0.15)' },
  rare:      { label: 'Редкая',     color: '#3b82f6', glow: 'rgba(59,130,246,0.25)'  },
  epic:      { label: 'Эпическая',  color: '#a855f7', glow: 'rgba(168,85,247,0.3)'   },
  legendary: { label: 'Легендарная',color: '#fbbf24', glow: 'rgba(251,191,36,0.35)'  },
}

export const STATUS_CONFIG: Record<RegStatus, { label: string; color: string; bg: string }> = {
  approved: { label: 'Одобрена',       color: '#39ff14', bg: 'rgba(57,255,20,0.1)'   },
  pending:  { label: 'Ожидает взноса', color: '#f97316', bg: 'rgba(249,115,22,0.12)' },
  rejected: { label: 'Отклонена',      color: '#ef4444', bg: 'rgba(239,68,68,0.12)'  },
}

export const mockProfile = {
  rank:     'Gold II',
  tier:     'gold'  as Tier,
  mmr:      1450,
  mmrStart: 1300,
  mmrNext:  1600,
  wins:     23,
  losses:   7,
  tournaments: 8,
  equippedIds: [1, 2, 3],
}

export const mockAchievements: Achievement[] = [
  { id: 1, name: 'Железный человек', icon: '🏆', rarity: 'legendary', unlocked: true,  desc: 'Выиграй 3 турнира подряд' },
  { id: 2, name: 'Точный удар',      icon: '🎯', rarity: 'epic',      unlocked: true,  desc: '10 зачётных попыток без сброса' },
  { id: 3, name: 'Ветеран',          icon: '⚔️', rarity: 'rare',      unlocked: true,  desc: 'Завершил 5 турниров' },
  { id: 4, name: 'Чемпион лиги',     icon: '👑', rarity: 'legendary', unlocked: false, desc: 'Займи 1 место в своей лиге' },
  { id: 5, name: 'Первая кровь',     icon: '⚡', rarity: 'common',    unlocked: true,  desc: 'Первый завершённый турнир' },
  { id: 6, name: 'Нокаут',           icon: '💥', rarity: 'epic',      unlocked: false, desc: 'Установи рекорд чемпионата' },
  { id: 7, name: 'Несломленный',     icon: '🛡️', rarity: 'rare',      unlocked: true,  desc: 'Нет дисквалификаций за сезон' },
  { id: 8, name: 'Берсерк',          icon: '🔥', rarity: 'epic',      unlocked: false, desc: 'Выиграй 5 турниров за сезон' },
]

export const mockLeaderboard: LeaderboardPlayer[] = [
  { id: 1,  name: 'ИванС',      rank: 'Elite I',   tier: 'elite',  mmr: 2840, isMe: false },
  { id: 2,  name: 'МаксПауэр',  rank: 'Elite I',   tier: 'elite',  mmr: 2710, isMe: false },
  { id: 3,  name: 'СтальнойА',  rank: 'Elite I',   tier: 'elite',  mmr: 2650, isMe: false },
  { id: 4,  name: 'КовальА',    rank: 'Gold I',    tier: 'gold',   mmr: 1820, isMe: false },
  { id: 5,  name: 'РостовД',    rank: 'Gold I',    tier: 'gold',   mmr: 1790, isMe: false },
  { id: 6,  name: 'БогатырьВ',  rank: 'Gold I',    tier: 'gold',   mmr: 1710, isMe: false },
  { id: 7,  name: 'ТитановК',   rank: 'Gold II',   tier: 'gold',   mmr: 1680, isMe: false },
  { id: 8,  name: 'МолотД',     rank: 'Gold II',   tier: 'gold',   mmr: 1590, isMe: false },
  { id: 9,  name: 'СилачМ',     rank: 'Gold II',   tier: 'gold',   mmr: 1520, isMe: false },
  { id: 10, name: 'КаменьП',    rank: 'Gold II',   tier: 'gold',   mmr: 1490, isMe: false },
  { id: 11, name: 'ЖелезоС',    rank: 'Gold II',   tier: 'gold',   mmr: 1460, isMe: false },
  { id: 12, name: 'АлексейС',   rank: 'Gold II',   tier: 'gold',   mmr: 1450, isMe: true  },
  { id: 13, name: 'ТяжестьВ',   rank: 'Gold III',  tier: 'gold',   mmr: 1380, isMe: false },
  { id: 14, name: 'СталевойИ',  rank: 'Silver I',  tier: 'silver', mmr: 1290, isMe: false },
]

export const mockTournaments: Tournament[] = [
  { id: 1, name: 'Russian Powerlifting Cup 2026', date: '15 Апр 2026', location: 'Москва',          prize: '250 000 ₽', discipline: 'Пауэрлифтинг',  slotsTotal: 48, slotsLeft: 12 },
  { id: 2, name: 'IronFlow Open 2026',            date: '3 Мая 2026',  location: 'Санкт-Петербург', prize: '150 000 ₽', discipline: 'Жим лёжа',       slotsTotal: 32, slotsLeft: 5  },
  { id: 3, name: 'Сибирский силач 2026',          date: '21 Июн 2026', location: 'Новосибирск',     prize: '100 000 ₽', discipline: 'Стронгмен',      slotsTotal: 24, slotsLeft: 18 },
  { id: 4, name: 'Кубок Урала — Становая',        date: '10 Июл 2026', location: 'Екатеринбург',    prize: '80 000 ₽',  discipline: 'Становая тяга',  slotsTotal: 40, slotsLeft: 31 },
]

export const mockMyRegistrations: MyRegistration[] = [
  {
    id: 1,
    name: 'IronFlow Open 2026',
    date: '3 Мая 2026',
    location: 'Санкт-Петербург',
    discipline: 'Жим лёжа',
    weightClass: 'до 90 кг',
    status: 'approved',
    qrToken: 'a1b2-c3d4-e5f6',
    rules: [
      'Взвешивание за 2 часа до старта',
      'Допускается экипировка IPF Open',
      '3 попытки в каждом движении',
      'Опоздание более 5 мин = дисквалификация',
    ],
  },
  {
    id: 2,
    name: 'Сибирский силач 2026',
    date: '21 Июн 2026',
    location: 'Новосибирск',
    discipline: 'Стронгмен',
    weightClass: 'до 100 кг',
    status: 'pending',
    qrToken: 'f7g8-h9i0-j1k2',
    rules: [
      'Форма одежды: компрессионный костюм',
      'Личные замки для штанги не допускаются',
      'Судьи решают все спорные ситуации',
      'Оплата взноса до 1 Июня 2026',
    ],
  },
]
