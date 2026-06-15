import { api, jsonApi } from './client';

export async function fetchImports(groupId) {
  return api(`/groups/${groupId}/imports`);
}

export async function uploadCsv(groupId, file) {
  const formData = new FormData();
  formData.append('file', file);
  return api(`/groups/${groupId}/imports`, {
    method: 'POST',
    body: formData,
  });
}

export async function fetchImportReport(groupId, batchId) {
  return api(`/groups/${groupId}/imports/${batchId}`);
}

export async function resolveAnomaly(groupId, batchId, anomalyId, resolutionStatus) {
  return jsonApi(
    `/groups/${groupId}/imports/${batchId}/anomalies/${anomalyId}`,
    { resolution_status: resolutionStatus },
    'PATCH',
  );
}

export async function fetchBalances(groupId, batchId) {
  return api(`/groups/${groupId}/imports/${batchId}/balances`);
}
