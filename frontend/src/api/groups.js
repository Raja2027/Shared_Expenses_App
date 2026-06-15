import { api, jsonApi } from './client';

export async function fetchGroups() {
  return api('/groups');
}

export async function createGroup(name) {
  return jsonApi('/groups', { name });
}

export async function fetchGroupDetail(groupId) {
  return api(`/groups/${groupId}`);
}

export async function fetchMembers(groupId) {
  return api(`/groups/${groupId}/members`);
}

export async function addMember(groupId, payload) {
  return jsonApi(`/groups/${groupId}/members`, payload);
}

export async function addMemberAlias(groupId, memberId, rawName, normalizedName) {
  return jsonApi(`/groups/${groupId}/members/${memberId}/aliases`, {
    raw_name: rawName,
    normalized_name: normalizedName,
  });
}
