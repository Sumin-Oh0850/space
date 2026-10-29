// Supabase Auth 오류 메시지를 한국어로 바꿉니다. (알 수 없는 오류는 원문 그대로 표시)
export function authErrorMessage(error) {
  const m = (error?.message || '').toLowerCase()
  if (m.includes('invalid login credentials')) return '이메일 또는 비밀번호가 올바르지 않습니다.'
  if (m.includes('email not confirmed')) return '이메일 인증이 아직 완료되지 않았습니다. 메일함의 인증 링크를 눌러 주세요.'
  if (m.includes('user already registered')) return '이미 가입된 이메일입니다. 로그인해 주세요.'
  if (m.includes('password should be at least')) return '비밀번호는 6자 이상이어야 합니다.'
  if (m.includes('unable to validate email') || m.includes('invalid email')) return '이메일 형식이 올바르지 않습니다.'
  if (m.includes('rate limit') || m.includes('too many')) return '요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.'
  if (m.includes('signups not allowed')) return '현재 회원가입이 허용되지 않은 설정입니다.'
  return error?.message || '알 수 없는 오류가 발생했습니다.'
}
