import client from "./client";

export async function submitClaim(claimText) {
  const response = await client.post("/claims", {
    claim_text: claimText,
  });

  return response.data.claim;
}

export async function getClaimStatus(claimId) {
  const response = await client.get(`/claims/${claimId}/status`);
  return response.data;
}

export async function getClaimById(claimId) {
  const response = await client.get(`/claims/${claimId}`);
  return response.data;
}

export async function getClaims() {
  const response = await client.get("/claims");
  return response.data.claims || [];
}
export async function uploadUrlClaim(url) {
  const response = await client.post("/claims/upload", { url });
  return response.data.claim;
}

export async function uploadPdfClaim(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await client.post("/claims/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data.claim;
}
