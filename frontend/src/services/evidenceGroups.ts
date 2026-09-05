import type { EvidenceResponse } from "./analysisService";

// Remove only known tracking parameters; article-identifying queries stay intact.
export function sourceKey(value: string): string {
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol)) return value;
    url.hash = '';
    for (const key of [...url.searchParams.keys()]) {
      if (/^utm_/i.test(key) || /^(fbclid|gclid)$/i.test(key)) url.searchParams.delete(key);
    }
    url.searchParams.sort();
    return url.toString();
  } catch { return value; }
}

export function groupEvidences(evidences: EvidenceResponse[]) {
  const groups = new Map<string, { key: string; source: EvidenceResponse; assessments: EvidenceResponse[]; claimIds: string[] }>();
  for (const evidence of evidences) {
    const key = evidence.source_url.trim() ? sourceKey(evidence.source_url) : `missing:${evidence.id}`;
    let group = groups.get(key);
    if (!group) {
      group = { key, source: evidence, assessments: [], claimIds: [] };
      groups.set(key, group);
    }
    if (!group.claimIds.includes(evidence.claim_id)) group.claimIds.push(evidence.claim_id);
    // Keep conflicting assessments visible, even for a duplicate within a claim.
    if (!group.assessments.some(item => item.claim_id === evidence.claim_id && item.verdict === evidence.verdict && item.reason === evidence.reason && item.relevance === evidence.relevance)) {
      group.assessments.push(evidence);
    }
  }
  return [...groups.values()];
}
