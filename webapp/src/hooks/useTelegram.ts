import { useEffect } from 'react'

interface TelegramUser {
  id: number
  first_name: string
  last_name?: string
  username?: string
  photo_url?: string
}

interface HapticFeedback {
  impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void
  notificationOccurred(type: 'error' | 'success' | 'warning'): void
  selectionChanged(): void
}

export interface TelegramWebApp {
  ready(): void
  expand(): void
  close(): void
  setHeaderColor(color: string): void
  setBackgroundColor(color: string): void
  enableClosingConfirmation(): void
  disableClosingConfirmation(): void
  HapticFeedback: HapticFeedback
  initDataUnsafe: {
    user?: TelegramUser
    query_id?: string
    auth_date?: number
    hash?: string
  }
  themeParams: {
    bg_color?: string
    text_color?: string
    hint_color?: string
    link_color?: string
    button_color?: string
    button_text_color?: string
  }
}

declare global {
  interface Window {
    Telegram?: { WebApp: TelegramWebApp }
  }
}

const MOCK_USER: TelegramUser = {
  id: 0,
  first_name: 'Алексей',
  last_name: 'Силов',
  username: 'alex_power',
}

export function useTelegram() {
  const tg: TelegramWebApp | null = window.Telegram?.WebApp ?? null

  useEffect(() => {
    tg?.ready()
  }, [tg])

  const user: TelegramUser = tg?.initDataUnsafe?.user ?? MOCK_USER

  const haptic = {
    impact: (style: 'light' | 'medium' | 'heavy' = 'light') =>
      tg?.HapticFeedback?.impactOccurred(style),
    success: () => tg?.HapticFeedback?.notificationOccurred('success'),
    error: () => tg?.HapticFeedback?.notificationOccurred('error'),
  }

  return { tg, user, haptic }
}
