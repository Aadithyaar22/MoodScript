import axios from "axios"

const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000"
const TOKEN_KEY = "moodscript_token"

const client = axios.create({ baseURL: BASE })

client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export function logout() {
  setToken(null)
  localStorage.removeItem("moodscript_username")
}

export async function signup(username, password) {
  const { data } = await client.post("/auth/signup", { username, password })
  setToken(data.token)
  localStorage.setItem("moodscript_username", data.username)
  return data
}

export async function login(username, password) {
  const { data } = await client.post("/auth/login", { username, password })
  setToken(data.token)
  localStorage.setItem("moodscript_username", data.username)
  return data
}

export async function sendChatMessage(message, imageBase64 = null, conversationId = null) {
  const { data } = await client.post("/chat", {
    message,
    image_base64: imageBase64,
    conversation_id: conversationId,
  })
  return data
}

export async function fetchHistory() {
  const { data } = await client.get("/history")
  return data
}

export async function fetchRating() {
  const { data } = await client.get("/rating")
  return data
}

export async function fetchConversations() {
  const { data } = await client.get("/conversations")
  return data
}

export async function fetchConversationMessages(conversationId) {
  const { data } = await client.get(`/conversations/${conversationId}/messages`)
  return data
}

export async function fetchReflection() {
  const { data } = await client.get("/reflection")
  return data
}

export async function exportJournal() {
  const response = await client.get("/export", { responseType: "blob" })
  const match = response.headers["content-disposition"]?.match(/filename=(.+)$/)
  const filename = match ? match[1] : "moodscript_journal.txt"
  const url = URL.createObjectURL(response.data)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export async function deleteAccount() {
  await client.delete("/account")
  logout()
}
