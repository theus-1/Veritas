import {
  useEffect,
  useRef,
  useState,
} from "react";

import { groupEvidences } from "../services/evidenceGroups";

import AnalysisForm from "../components/AnalysisForm";

import type {
  AnalysisResponse,
  AnalysisVerdict,
  ClaimResponse,
  EvidenceResponse,
} from "../services/analysisService";


function AnalysisPage() {
  const closeButtonRef =
    useRef<HTMLButtonElement | null>(
      null
    );

  const [
    analysis,
    setAnalysis,
  ] = useState<AnalysisResponse | null>(
    null
  );

  const [
    openClaimId,
    setOpenClaimId,
  ] = useState<string | null>(
    null
  );

  const evidenceGroups = groupEvidences(analysis?.evidences ?? []);

  function closeAnalysis() {
    setAnalysis(null);
    setOpenClaimId(null);
  }

  useEffect(() => {
    if (!analysis) {
      return;
    }

    const previousOverflow =
      document.body.style.overflow;

    document.body.style.overflow =
      "hidden";

    const handleKeyDown = (
      event: KeyboardEvent
    ) => {
      if (event.key === "Escape") {
        closeAnalysis();
      }
    };

    document.addEventListener(
      "keydown",
      handleKeyDown
    );

    requestAnimationFrame(() => {
      closeButtonRef.current?.focus();
    });

    if (analysis.claims.length > 0) {
      setOpenClaimId(
        analysis.claims[0].id
      );
    }

    return () => {
      document.body.style.overflow =
        previousOverflow;

      document.removeEventListener(
        "keydown",
        handleKeyDown
      );
    };
  }, [analysis]);

  function getVerdictLabel(
    verdict: AnalysisVerdict | null
  ) {
    switch (verdict) {
      case "VERDADEIRA":
        return "Verdadeira";

      case "PROVAVELMENTE_VERDADEIRA":
        return "Provavelmente verdadeira";

      case "INCONCLUSIVA":
        return "Inconclusiva";

      case "PROVAVELMENTE_FALSA":
        return "Provavelmente falsa";

      case "FALSA":
        return "Falsa";

      default:
        return "Inconclusiva";
    }
  }

  function getVerdictDescription(
    verdict: AnalysisVerdict | null
  ) {
    switch (verdict) {
      case "VERDADEIRA":
        return (
          "As evidências encontradas " +
          "apoiam a afirmação."
        );

      case "PROVAVELMENTE_VERDADEIRA":
        return (
          "As evidências encontradas " +
          "apontam para a veracidade " +
          "da afirmação."
        );

      case "INCONCLUSIVA":
        return (
          "As evidências encontradas " +
          "não são suficientes para " +
          "confirmar ou negar a afirmação."
        );

      case "PROVAVELMENTE_FALSA":
        return (
          "As evidências encontradas " +
          "apontam para a falsidade " +
          "da afirmação."
        );

      case "FALSA":
        return (
          "As evidências encontradas " +
          "contradizem a afirmação."
        );

      default:
        return (
          "Não foi possível determinar " +
          "a veracidade da afirmação."
        );
    }
  }

  function formatConfidence(
    confidence: number | null
  ) {
    if (confidence === null) {
      return "—";
    }

    return `${Math.round(
      confidence * 100
    )}%`;
  }

  function getClaimEvidences(
    claim: ClaimResponse
  ): EvidenceResponse[] {
    if (!analysis) {
      return [];
    }

    return groupEvidences(analysis.evidences.filter(
      evidence => evidence.claim_id === claim.id
    )).flatMap(group => group.assessments);
  }

  function getDirectionalEvidences(
    claim: ClaimResponse
  ) {
    return getClaimEvidences(
      claim
    ).filter(
      (evidence) =>
        evidence.verdict !== "NEUTRAL"
    );
  }

  function getDirectionalSummary(
    claim: ClaimResponse
  ) {
    const evidences =
      getDirectionalEvidences(claim);

    const supports =
      evidences.filter(
        (evidence) =>
          evidence.verdict ===
          "SUPPORTS"
      ).length;

    const contradicts =
      evidences.filter(
        (evidence) =>
          evidence.verdict ===
          "CONTRADICTS"
      ).length;

    if (
      supports === 0 &&
      contradicts === 0
    ) {
      return (
        "Nenhuma evidência relevante " +
        "confirmou ou contradisse " +
        "diretamente esta afirmação."
      );
    }

    if (
      supports > 0 &&
      contradicts === 0
    ) {
      return `${supports} ${
        supports === 1
          ? "evidência apoia"
          : "evidências apoiam"
      } esta afirmação.`;
    }

    if (
      contradicts > 0 &&
      supports === 0
    ) {
      return `${contradicts} ${
        contradicts === 1
          ? "evidência contradiz"
          : "evidências contradizem"
      } esta afirmação.`;
    }

    return (
      `${supports} apoiam e ` +
      `${contradicts} contradizem ` +
      "esta afirmação."
    );
  }

  function toggleClaim(
    claimId: string
  ) {
    setOpenClaimId(
      (current) =>
        current === claimId
          ? null
          : claimId
    );
  }

  return (
    <main className="analysis-page">
      <div className="analysis-container">
        <header className="analysis-header">
          <span className="brand">
            VERITAS
          </span>

          <h1>
            Descubra o que é
            <span> verdade.</span>
          </h1>

          <p>
            Analise notícias, encontre
            evidências e tome decisões
            com mais confiança.
          </p>
        </header>

        <section className="analysis-card">
          <div className="analysis-card-header">
            <div>
              <h2>Analisar notícia</h2>

              <p>
                Insira o conteúdo que
                você deseja verificar.
              </p>
            </div>
          </div>

          <AnalysisForm
            onAnalysisComplete={
              setAnalysis
            }
          />
        </section>

        {analysis && (
          <div
            className="analysis-modal-overlay"
            onClick={closeAnalysis}
          >
            <section
              className="analysis-modal"
              onClick={(event) =>
                event.stopPropagation()
              }
              role="dialog"
              aria-modal="true"
              aria-labelledby="analysis-result-title"
            >
              <div className="analysis-modal-header">
                <div>
                  <span className="analysis-modal-label">
                    Resultado da análise
                  </span>

                  <h2 id="analysis-result-title">
                    {analysis.title}
                  </h2>
                </div>

                <button
                  ref={closeButtonRef}
                  type="button"
                  className="analysis-modal-close"
                  onClick={closeAnalysis}
                  aria-label="Fechar análise"
                >
                  ×
                </button>
              </div>

              <div className="analysis-modal-status">
                <span className="status-dot" />
                {analysis.status}
              </div>

              <div className="result-content">
                <div className="result-hero">
                  <div className="result-hero-main">
                    <span className="result-label">
                      Classificação geral
                    </span>

                    <strong
                      className={
                        `result-verdict-value ` +
                        `verdict-${(
                          analysis.verdict ??
                          "INCONCLUSIVA"
                        ).toLowerCase()}`
                      }
                    >
                      {getVerdictLabel(
                        analysis.verdict
                      )}
                    </strong>

                    <p>
                      {getVerdictDescription(
                        analysis.verdict
                      )}
                    </p>
                  </div>

                  <div className="result-confidence-card">
                    <span className="result-label">
                      Força das evidências
                    </span>

                    <strong>
                      {formatConfidence(
                        analysis.confidence
                      )}
                    </strong>

                    {analysis.confidence !==
                      null && (
                      <div className="confidence-bar">
                        <div
                          className="confidence-bar-fill"
                          style={{
                            width:
                              `${
                                Math.round(
                                  analysis.confidence *
                                    100
                                )
                              }%`,
                          }}
                        />
                      </div>
                    )}
                  </div>
                </div>

                <p className="claim-summary">Os índices são estimativas heurísticas, não probabilidades de verdade. Sem evidência suficiente, o resultado é inconclusivo.</p>

                {analysis.claims.length >
                  0 && (
                  <div className="result-section">
                    <div className="result-section-header">
                      <div>
                        <span>
                          Explicação por
                          afirmação
                        </span>

                        <p>
                          Abra uma afirmação
                          para entender as
                          evidências utilizadas.
                        </p>
                      </div>

                      <small>
                        {
                          analysis.claims
                            .length
                        }
                      </small>
                    </div>

                    <div className="claim-accordions">
                      {analysis.claims.map(
                        (
                          claim,
                          index
                        ) => {
                          const isOpen =
                            openClaimId ===
                            claim.id;

                          const directionalEvidences =
                            getDirectionalEvidences(
                              claim
                            );

                          return (
                            <article
                              className={
                                `claim-accordion ` +
                                `${
                                  isOpen
                                    ? "is-open"
                                    : ""
                                }`
                              }
                              key={claim.id}
                            >
                              <button
                                type="button"
                                className="claim-accordion-trigger"
                                onClick={() =>
                                  toggleClaim(
                                    claim.id
                                  )
                                }
                                aria-expanded={
                                  isOpen
                                }
                              >
                                <span className="claim-number">
                                  {String(
                                    index +
                                      1
                                  ).padStart(
                                    2,
                                    "0"
                                  )}
                                </span>

                                <span className="claim-accordion-main">
                                  <strong>
                                    {
                                      claim.text
                                    }
                                  </strong>

                                  <span className="claim-result-meta">
                                    <span
                                      className={
                                        `claim-verdict ` +
                                        `verdict-${(
                                          claim.verdict ??
                                          "INCONCLUSIVA"
                                        ).toLowerCase()}`
                                      }
                                    >
                                      {getVerdictLabel(
                                        claim.verdict
                                      )}
                                    </span>

                                    <span>
                                      {formatConfidence(
                                        claim.confidence
                                      )}
                                    </span>
                                  </span>
                                </span>

                                <span
                                  className={
                                    `claim-chevron ` +
                                    `${
                                      isOpen
                                        ? "is-open"
                                        : ""
                                    }`
                                  }
                                  aria-hidden="true"
                                >
                                  ›
                                </span>
                              </button>

                              {isOpen && (
                                <div className="claim-accordion-content">
                                  <p className="claim-summary">
                                    {getDirectionalSummary(
                                      claim
                                    )}
                                  </p>

                                  {directionalEvidences.length >
                                  0 ? (
                                    <div className="claim-explanations">
                                      {directionalEvidences.map(
                                        (
                                          evidence
                                        ) => (
                                          <div
                                            className={
                                              `claim-explanation-item ` +
                                              `claim-explanation-${evidence.verdict.toLowerCase()}`
                                            }
                                            key={
                                              evidence.id
                                            }
                                          >
                                            <div className="claim-explanation-header">
                                              <strong>
                                                {
                                                  evidence.source_name
                                                }
                                              </strong>

                                              <span>
                                                {Math.round(
                                                  evidence.relevance *
                                                    100
                                                )}
                                                %
                                              </span>
                                            </div>

                                            <p className="claim-explanation-title">
                                              {
                                                evidence.title
                                              }
                                            </p>

                                            {evidence.reason && (
                                              <p className="claim-explanation-reason">
                                                {
                                                  evidence.reason
                                                }
                                              </p>
                                            )}

                                            <a
                                              href={
                                                evidence.source_url
                                              }
                                              target="_blank"
                                              rel="noopener noreferrer"
                                            >
                                              Ver fonte ↗
                                            </a>
                                          </div>
                                        )
                                      )}
                                    </div>
                                  ) : (
                                    <div className="claim-inconclusive-message">
                                      <span>
                                        Evidências
                                        insuficientes
                                      </span>

                                      <p>
                                        As fontes
                                        encontradas
                                        não trataram
                                        diretamente
                                        desta
                                        afirmação.
                                      </p>
                                    </div>
                                  )}
                                </div>
                              )}
                            </article>
                          );
                        }
                      )}
                    </div>
                  </div>
                )}

                {analysis.claims.length >
                  0 && (
                  <div className="result-section">
                    <div className="result-section-header">
                      <div>
                        <span>
                          Afirmações analisadas
                        </span>

                        <p>
                          O que foi extraído
                          do conteúdo enviado.
                        </p>
                      </div>

                      <small>
                        {
                          analysis.claims
                            .length
                        }
                      </small>
                    </div>

                    <div className="claims-list">
                      {analysis.claims.map(
                        (
                          claim,
                          index
                        ) => (
                          <div
                            className="claim-item"
                            key={
                              claim.id
                            }
                          >
                            <span className="claim-number">
                              {String(
                                index + 1
                              ).padStart(
                                2,
                                "0"
                              )}
                            </span>

                            <div className="claim-item-content">
                              <p>
                                {
                                  claim.text
                                }
                              </p>

                              <div className="claim-item-result">
                                <span
                                  className={
                                    `claim-verdict ` +
                                    `verdict-${(
                                      claim.verdict ??
                                      "INCONCLUSIVA"
                                    ).toLowerCase()}`
                                  }
                                >
                                  {getVerdictLabel(
                                    claim.verdict
                                  )}
                                </span>

                                <span>
                                  {formatConfidence(
                                    claim.confidence
                                  )}
                                </span>
                              </div>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                )}

                {analysis.evidences.length >
                  0 && (
                  <div className="result-section">
                    <div className="result-section-header">
                      <div>
                        <span>
                          Evidências encontradas
                        </span>

                        <p>
                          Todas as fontes
                          utilizadas na análise.
                        </p>
                      </div>

                      <small>
                        {
                          evidenceGroups.length
                        }
                      </small>
                    </div>

                    <div className="evidences-list">
                      {evidenceGroups.map(group => (
                        <article className="evidence-item" key={group.key}>
                          <h3>{group.source.title}</h3>
                          <p className="evidence-source">{group.source.source_name}</p>
                          <p>Utilizada em {group.claimIds.length} {group.claimIds.length === 1 ? "afirmação" : "afirmações"}</p>
                          {group.assessments.map((evidence, index) => (
                            <div key={`${evidence.id}:${index}`} className="claim-summary">
                              <strong>Afirmação {analysis.claims.findIndex(claim => claim.id === evidence.claim_id) + 1}: </strong>
                              {evidence.verdict === "SUPPORTS" ? "Apoia" : evidence.verdict === "CONTRADICTS" ? "Contradiz" : "Neutra"}
                              {` · ${Math.round(evidence.relevance * 100)}% de relevância estimada`}
                              {evidence.reason && <p>{evidence.reason}</p>}
                            </div>
                          ))}
                          <a href={group.source.source_url} target="_blank" rel="noopener noreferrer" className="evidence-link">Ver fonte ↗</a>
                        </article>
                      ))}
                    </div>
                  </div>
                )}

                {analysis.claims.length ===
                  0 && (
                  <div className="result-empty">
                    <span>
                      Nenhuma afirmação
                      identificada
                    </span>

                    <p>
                      Não foi possível
                      identificar afirmações
                      verificáveis no
                      conteúdo enviado.
                    </p>
                  </div>
                )}
              </div>
            </section>
          </div>
        )}

        <footer className="analysis-footer">
          <p>
            Veritas · Verificação baseada
            em evidências
          </p>
        </footer>
      </div>
    </main>
  );
}

export default AnalysisPage;
