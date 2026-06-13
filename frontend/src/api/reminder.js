import request from './request'

export function getRemindersApi() {
  return request.get('/reminders')
}

export function createReminderApi(payload) {
  return request.post('/reminders', payload)
}

export function updateReminderApi(reminderId, payload) {
  return request.patch(`/reminders/${reminderId}`, payload)
}

export function deleteReminderApi(reminderId) {
  return request.delete(`/reminders/${reminderId}`)
}
