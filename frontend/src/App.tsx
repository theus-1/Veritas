import { useEffect, useRef, useState } from "react";
import AnalysisPage from "./pages/AnalysisPage";

function App() {
  const [showWelcome, setShowWelcome] = useState(true);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!showWelcome) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setShowWelcome(false);
    };

    document.addEventListener("keydown", handleKeyDown);
    requestAnimationFrame(() => closeButtonRef.current?.focus());

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [showWelcome]);

  return (
    <>
      <AnalysisPage />

      {showWelcome && (
        <div className="welcome-overlay" onClick={() => setShowWelcome(false)}>
          <section
            className="welcome-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="welcome-title"
            onClick={(event) => event.stopPropagation()}
          >
            <span className="welcome-eyebrow">ANTES DE COMEÇAR</span>
            <h2 id="welcome-title">Como obter uma análise melhor</h2>
            <p className="welcome-intro">
              Menos afirmações, escritas com clareza e contexto, tendem a gerar
              análises mais precisas e estáveis.
            </p>

            <div className="welcome-note">
              <strong>Como o Veritas funciona</strong>
              <p>
                O Veritas compara o conteúdo enviado com evidências obtidas por
                APIs de consulta a notícias e modelos de inteligência artificial.
                As fontes encontradas podem estar incompletas, ambíguas ou
                desatualizadas, por isso o resultado não representa uma garantia
                absoluta de verdade.
              </p>
            </div>

            <p className="welcome-recommendation">
              Para decisões importantes, confirme a informação também em fontes
              independentes e confiáveis.
            </p>

            <button
              ref={closeButtonRef}
              className="welcome-button"
              type="button"
              onClick={() => setShowWelcome(false)}
            >
              Entendi, continuar
            </button>
          </section>
        </div>
      )}
    </>
  );
}

export default App;
