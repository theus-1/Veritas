import { useState } from "react";
import {
  createAnalysis,
  AnalysisApiError,
  GENERIC_ANALYSIS_ERROR,
  type AnalysisResponse,
} from "../services/analysisService";

const MAX_INPUT_TEXT_LENGTH = 10000;

interface AnalysisFormProps {
  onAnalysisComplete: (analysis: AnalysisResponse) => void;
}

function AnalysisForm({ onAnalysisComplete }: AnalysisFormProps) {
  const [title, setTitle] = useState("");
  const [inputText, setInputText] = useState("");
  const [inputUrl, setInputUrl] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(
    event: React.FormEvent<HTMLFormElement>
  ) {
    event.preventDefault();

    if (loading) {
      return;
    }

    const trimmedTitle = title.trim();
    const trimmedText = inputText.trim();
    const trimmedUrl = inputUrl.trim();

    if (!trimmedTitle) {
      setError("Informe o título da notícia.");
      return;
    }

    if (!trimmedText) {
      setError("Informe o texto da notícia.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const analysis = await createAnalysis({
        title: trimmedTitle,
        input_text: trimmedText,
        input_url: trimmedUrl || null,
      });

      onAnalysisComplete(analysis);
    } catch (error) {
      setError(error instanceof AnalysisApiError ? error.message : GENERIC_ANALYSIS_ERROR);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      className={`analysis-form ${loading ? "is-loading" : ""}`}
      onSubmit={handleSubmit}
    >
      <div className="form-group">
        <label htmlFor="title">Título da notícia</label>

        <input
          id="title"
          minLength={3}
          maxLength={300}
          type="text"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Ex.: Governo anuncia nova medida econômica"
          required
          disabled={loading}
        />
      </div>

      <div className="form-group">
        <label htmlFor="input-text">Texto da notícia</label>

        <textarea
          id="input-text"
          minLength={10}
          value={inputText}
          onChange={(event) => setInputText(event.target.value)}
          placeholder="Escreva ou cole afirmações específicas, separadas por ponto..."
          rows={10}
          required
          disabled={loading}
          maxLength={MAX_INPUT_TEXT_LENGTH}
        />

        <div className="input-meta">
          <span>
            O texto será dividido em afirmações para análise.
          </span>

          <span>
            {inputText.length}/{MAX_INPUT_TEXT_LENGTH}
          </span>
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="input-url">
          URL da notícia <span>(opcional)</span>
        </label>

        <input
          id="input-url"
          maxLength={2000}
          type="url"
          value={inputUrl}
          onChange={(event) => setInputUrl(event.target.value)}
          placeholder="https://exemplo.com/noticia"
          disabled={loading}
        />
      </div>

      {loading && (
        <div
          className="analysis-loading"
          role="status"
          aria-live="polite"
        >
          <span className="loading-spinner" aria-hidden="true" />

          <div>
            <strong>Analisando notícia</strong>

            <p>
              Estamos buscando fontes e comparando as
              informações encontradas.
            </p>
          </div>
        </div>
      )}

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <button
        className="analyze-button"
        type="submit"
        disabled={loading}
      >
        {loading ? "Verificando evidências..." : "Analisar notícia"}
      </button>
    </form>
  );
}

export default AnalysisForm;
