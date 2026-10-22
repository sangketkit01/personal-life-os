export interface User {
  id: string
  username: string
  email: string
  telegram_chat_id: string | null
  is_telegram_connected: boolean
  created_at: string
}

export interface UserDeviceSession {
  id: string
  device_name: string
  ip_address: string | null
  last_active_at: string
  is_revoked: boolean
  is_current: boolean
  created_at: string
}

export interface InviteCode {
  id: string
  code: string
  uses_count: number
  max_uses: number
  is_active: boolean
  expires_at: string | null
  created_at: string
}

export interface ActivityLog {
  id: string
  category: 'AUTH' | 'FINANCE' | 'PORTFOLIO' | 'WORKSPACE'
  action: string
  description: string
  ip_address: string
  device_name: string
  status: 'SUCCESS' | 'FAILED' | 'WARNING'
  created_at: string
}

export * from './ledger'

