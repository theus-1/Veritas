import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createAnalysis, AnalysisApiError } from '../src/services/analysisService.ts';

const payload = { title: 'Teste', input_text: 'Texto de teste' };

test('preserva mensagem estruturada para apresentação no formulário', async () => {
  const original = globalThis.fetch;
  try {
    for (const status of [401, 422, 429, 500, 503]) {
      globalThis.fetch = async () => new Response(JSON.stringify({ error: { code: 'TEST_ERROR', message: 'Mensagem do backend' } }), { status });
      await assert.rejects(createAnalysis(payload), (error) => error instanceof AnalysisApiError && error.message === 'Mensagem do backend');
    }
  } finally { globalThis.fetch = original; }
});

test('resposta sem estrutura e falha de rede usam caminho genérico', async () => {
  const original = globalThis.fetch;
  try {
    for (const body of ['invalid json', '{}', '{"error":{"message":123}}', '{"error":{"code":"X","message":""}}']) {
      globalThis.fetch = async () => new Response(body, { status: 503 });
      await assert.rejects(createAnalysis(payload), (error) => error instanceof Error && !(error instanceof AnalysisApiError));
    }
    globalThis.fetch = async () => { throw new TypeError('Network unavailable'); };
    await assert.rejects(createAnalysis(payload), (error) => !(error instanceof AnalysisApiError));
  } finally { globalThis.fetch = original; }
});

test('resposta de sucesso permanece disponível', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response(JSON.stringify({ verdict: 'INCONCLUSIVA', confidence: null }), { status: 200 });
    assert.deepEqual(await createAnalysis(payload), { verdict: 'INCONCLUSIVA', confidence: null });
  } finally { globalThis.fetch = original; }
});
