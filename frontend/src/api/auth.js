import { api } from './client';

export async function loginUser(email, password) {
  const body = new URLSearchParams({ username: email, password });
  return api('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
}

export async function registerUser(name, email, password) {
  return api('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, email, password }),
  });
}

export async function fetchMe() {
  return api('/auth/me');
}
