import { test } from 'node:test';
import assert from 'node:assert/strict';
import { groupEvidences, sourceKey } from '../src/services/evidenceGroups.ts';

const make = (id, claim_id, source_url, verdict = 'SUPPORTS') => ({ id, claim_id, source_url, verdict, relevance: .9, reason: 'Contexto', title: 'Artigo', source_name: 'Fonte' });

test('agrupa rastreamento e fragmentos, conta claims distintas e preserva conflito', () => {
  const rows = [make('1', 'a', 'https://example.com/story?utm_source=x'), make('2', 'a', 'https://example.com/story#top'), make('3', 'b', 'https://example.com/story', 'CONTRADICTS')];
  const snapshot = JSON.stringify(rows);
  const groups = groupEvidences(rows);
  assert.equal(groups.length, 1);
  assert.deepEqual(groups[0].claimIds, ['a', 'b']);
  assert.deepEqual(groups[0].assessments.map(e => e.verdict), ['SUPPORTS', 'CONTRADICTS']);
  assert.equal(JSON.stringify(rows), snapshot);
});

test('mesmo domínio com artigos distintos não é duplicata', () => {
  assert.equal(groupEvidences([make('1', 'a', 'https://example.com/?id=1'), make('2', 'a', 'https://example.com/?id=2')]).length, 2);
  assert.equal(sourceKey('https://example.com/?b=2&a=1'), sourceKey('https://example.com/?a=1&b=2'));
});

test('preserva avaliações conflitantes dentro da mesma claim e entradas sem URL', () => {
  assert.equal(groupEvidences([make('1', 'a', 'https://example.com'), make('2', 'a', 'https://example.com', 'NEUTRAL')])[0].assessments.length, 2);
  assert.equal(groupEvidences([make('1', 'a', ''), make('2', 'a', '')]).length, 2);
  assert.deepEqual(groupEvidences([]), []);
});
