const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

export interface AnalysisRequest {
  title: string;
  input_text: string;
  input_url?: string | null;
}

export type AnalysisVerdict =
  | "VERDADEIRA"
  | "PROVAVELMENTE_VERDADEIRA"
  | "INCONCLUSIVA"
  | "PROVAVELMENTE_FALSA"
  | "FALSA";

export type EvidenceVerdict =
  | "SUPPORTS"
  | "CONTRADICTS"
  | "NEUTRAL";

export type AnalysisStatus =
  | "Pendente"
  | "Processando"
  | "Completa"
  | "Falhou";

export interface ClaimResponse {
  id: string;
  text: string;

  verdict: AnalysisVerdict | null;
  confidence: number | null;

  created_at: string;
}

export interface EvidenceResponse {
  id: string;
  claim_id: string;

  source_name: string;
  source_url: string;
  title: string;

  relevance: number;
  verdict: EvidenceVerdict;

  reason: string | null;

  created_at: string;
}

export interface AnalysisResponse {
  id: string;
  title: string;
  input_text: string;
  input_url: string | null;

  verdict: AnalysisVerdict | null;
  confidence: number | null;

  /*
   * Mantido temporariamente por compatibilidade
   * com o backend.
   *
   * O frontend novo não depende mais dessa
   * string gigante.
   */
  explanation: string | null;

  status: AnalysisStatus;
  created_at: string;

  claims: ClaimResponse[];
  evidences: EvidenceResponse[];
}

export const GENERIC_ANALYSIS_ERROR =
  "Não foi possível realizar a análise. Tente novamente.";

export class AnalysisApiError extends Error {}

export async function createAnalysis(
  data: AnalysisRequest
): Promise<AnalysisResponse> {
  const response = await fetch(
    `${API_BASE_URL}/analysis/`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(data),
    }
  );

  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => null);

    const message =
      body?.error?.message;

    if (
      typeof body?.error?.code === "string" &&
      typeof message === "string" &&
      message.trim()
    ) {
      throw new AnalysisApiError(
        message
      );
    }

    throw new Error(
      GENERIC_ANALYSIS_ERROR
    );
  }

  return response.json();
}
