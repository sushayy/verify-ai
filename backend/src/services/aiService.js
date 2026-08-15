const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';
const USE_MOCK = process.env.USE_MOCK_AI === 'true';

function mockVerify(claimText) {
  return {
    claim: {
      original_text: claimText,
      normalized_statement: claimText,
      entities: [],
      dates: [],
      claim_type: 'general_fact',
    },
    final_result: 'UNVERIFIED',
    confidence_score: 0.5,
    explanation: 'This is a mock response — the real AI service is not connected yet.',
    evidence: [
      {
        source_name: 'Mock Source',
        url: null,
        extracted_text: 'Placeholder evidence text.',
        stance: 'neutral',
        reliability_score: 0.5,
      },
    ],
  };
}

async function verifyClaim(claimText) {
  if (USE_MOCK) {
    return mockVerify(claimText);
  }

  const response = await fetch(`${AI_SERVICE_URL}/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ claim_text: claimText }),
  });

  if (!response.ok) {
    throw new Error(`AI service responded with status ${response.status}`);
  }

  return response.json();
}

module.exports = { verifyClaim };
