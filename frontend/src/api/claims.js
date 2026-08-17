import client from "./client";

export async function submitClaim(claimText) {
  const response = await client.post("/claims", {
    claim_text: claimText,
  });

  return response.data.claim;
}