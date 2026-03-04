/**
 * REST API client for SPORTBAZA WebApp.
 * Sends Telegram initData in X-Telegram-Init-Data header for auth.
 */

const BASE = import.meta.env.VITE_API_URL ?? ''

function initData(): string {
  return window.Telegram?.WebApp?.initData ?? ''
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { 'X-Telegram-Init-Data': initData() },
  })
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json()
}

async function del(path: string): Promise<void> {
  const r = await fetch(`${BASE}${path}`, {
    method: 'DELETE',
    headers: { 'X-Telegram-Init-Data': initData() },
  })
  if (!r.ok) throw new Error(`${r.status}`)
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface Me {
  telegram_id: number
  first_name: string
  last_name: string | null
  username: string | null
  is_admin: boolean
  authenticated: boolean
}

export interface ApiTournament {
  id: number
  name: string
  status: string           // draft | registration | active | finished
  status_emoji: string
  tournament_type: string  // SBD | BP | DL | PP
  type_label: string
  description: string | null
  formula: string
  formula_label: string
  created_at: string | null
  participants_count: number
}

export interface LeaderboardEntry {
  user_id: number
  telegram_id: number
  first_name: string
  last_name: string | null
  username: string | null
  mmr: number
  rank: string
  tier: string
  tournaments_count: number
}

export interface Achievement {
  id: string
  name: string
  icon: string
  rarity: 'common' | 'rare' | 'epic' | 'legendary'
  desc: string
  unlocked: boolean
}

export interface UserProfile {
  mmr: number
  rank: string
  tier: string
  mmr_start: number
  mmr_next: number
  wins: number
  losses: number
  tournaments: number
  achievements: Achievement[]
}

export interface MyRegistration {
  id: number
  tournament_id: number
  name: string
  tournament_status: string
  tournament_type: string
  discipline: string
  weight_class: string
  registration_status: string
  qr_token: string | null
  checked_in: boolean
  full_name: string
  description: string | null
}

// ── Requests ───────────────────────────────────────────────────────────────

export const api = {
  me:                ()     => get<Me>('/api/me'),
  tournaments:       ()     => get<ApiTournament[]>('/api/tournaments'),
  deleteTournament:  (id: number) => del(`/api/tournaments/${id}`),
  leaderboard:       ()     => get<LeaderboardEntry[]>('/api/leaderboard'),
  profile:           ()     => get<UserProfile>('/api/profile'),
  myRegistrations:   ()     => get<MyRegistration[]>('/api/my-registrations'),
}
