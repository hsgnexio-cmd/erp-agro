// Calendrier de l'entreprise (phase 11)

export interface CompanyCalendar {
  year: number
  rules: { activity: string; days: string }[]
  holidays: { date: string; label: string; weekday: string }[]
  closures: {
    id: number
    site_code: string
    site_name: string
    start_date: string
    end_date: string
    reason: string
  }[]
}
