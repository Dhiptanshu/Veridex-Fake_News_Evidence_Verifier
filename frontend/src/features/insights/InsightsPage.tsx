import { useEffect, useState, type ReactNode } from "react";
import { fetchMetrics, type MetricsBundle } from "@/api/client";
import { Card, Eyebrow } from "@/components/Card";
import { ConfusionMatrix, HBars, LineChart, type BarRow, type Series } from "./charts";

/* eslint-disable @typescript-eslint/no-explicit-any */
type M = any;
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const C = { accent: "var(--accent)", good: "var(--supported)", bad: "var(--refuted)", warn: "var(--neutral)", ink: "var(--ink)", muted: "var(--muted)" };

function Section({ title, finding, children }: { title: string; finding?: ReactNode; children: ReactNode }) {
  return (
    <Card className="p-4">
      <Eyebrow>{title}</Eyebrow>
      {finding && <p className="mt-2 max-w-3xl text-base font-semibold leading-snug">{finding}</p>}
      <div className="mt-5">{children}</div>
    </Card>
  );
}

function verificationRows(m: MetricsBundle): BarRow[] {
  const rows: BarRow[] = [];
  const t = (k: string) => m.verification?.models?.[k]?.test?.retrieved;
  const add = (label: string, x: M, highlight = false) =>
    x && rows.push({ label, highlight, values: { acc: x.accuracy, f1: x.macro?.f1, fever: x.fever_score } });
  add("Claim only (no evidence)", t("claim_only"));
  add("BiLSTM + GloVe", t("lstm"));
  add("BiGRU + GloVe", t("gru"));
  add("BERT, evidence concatenated", t("bert"));
  add("BERT + stacker (default)", m.stacker?.test, true);
  return rows;
}

function retrievalRows(m: MetricsBundle): BarRow[] {
  const t = m.retrieval_semantic?.test;
  if (!t) return [];
  const pick = (label: string, x: M, highlight = false): BarRow | null =>
    x ? { label, highlight, values: { r1: x["sentence_recall@1"], r5: x["sentence_recall@5"] } } : null;
  return [
    pick("TF-IDF", t["tfidf"]),
    pick("Word2Vec + TF-IDF", t["tfidf + w2v (alpha=0.4)"]),
    pick("GloVe + TF-IDF", t["tfidf + glove (alpha=0.4)"]),
    pick("MiniLM + TF-IDF", t["tfidf + minilm (alpha=0.2)"]),
    pick("BGE-small", t["bge_small (rerank only)"]),
    pick("BGE-small + title bonus (default)", m.title_bonus?.test?.[String(m.title_bonus?.tuned_bonus)], true),
  ].filter((r): r is BarRow => r !== null);
}

function pageRows(m: MetricsBundle): BarRow[] {
  const t = m.retrieval_tfidf?.test;
  if (!t) return [];
  const names: [string, string][] = [
    ["claim_only", "TF-IDF, claim only"], ["ngram_title", "+ title match (n-grams)"],
    ["ngram+ner_title", "+ title match (NER too)"], ["ngram+ner_title+wordnet", "+ WordNet expansion"],
  ];
  return names.filter(([k]) => t[k]).map(([k, label]) => ({ label, values: { r5: t[k]["page_recall@5"], mrr: t[k]["page_mrr"] } }));
}

export function InsightsPage() {
  const [m, setM] = useState<MetricsBundle | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctl = new AbortController();
    fetchMetrics(ctl.signal).then(setM).catch((e: Error) => e.name !== "AbortError" && setError(e.message));
    return () => ctl.abort();
  }, []);

  if (error) return <p role="alert" className="rounded-md border border-refuted/40 bg-refuted/10 px-4 py-3 text-sm text-refuted">{error}</p>;
  if (!m) return <p className="text-sm text-muted">Loading results...</p>;

  const vRows = verificationRows(m);
  const claimOnly = m.verification?.models?.claim_only?.test?.retrieved?.accuracy;
  const best = m.stacker?.test;
  const h = m.history;
  const cm = best?.confusion_matrix;
  const ex = m.explanation;

  const verSeries: Series[] = [
    { key: "acc", label: "Accuracy", color: C.accent }, { key: "f1", label: "Macro-F1", color: C.good }, { key: "fever", label: "FEVER score", color: C.warn },
  ];

  return (
    <div className="space-y-6">
      <div>
        <p className="mt-1 text-sm text-muted">
          Every number here is read from the saved evaluation files in <code className="font-mono text-xs">docs/results</code>, on FEVER's
          balanced test set (chance = 33.3%).
        </p>
      </div>

      {vRows.length > 0 && (
        <Section
          title="Does evidence help?"
          finding={best && claimOnly ? <>Guessing from the claim alone reaches {pct(claimOnly)}; reading the retrieved evidence with BERT reaches <em className="text-accent">{pct(best.accuracy)}</em>.</> : undefined}
        >
          <HBars rows={vRows} series={verSeries} />
          <p className="mt-4 text-xs leading-relaxed text-muted">
            FEVER score counts a claim only if the label is right and a complete gold evidence set was retrieved. The recurrent baselines barely beat
            the claim-only model: on the imbalanced validation set they score higher only because they lean on the majority label.
          </p>
        </Section>
      )}

      {retrievalRows(m).length > 0 && (
        <Section
          title="Finding the right sentence"
          finding={<>Transformer sentence embeddings lift recall@5 from {pct(m.retrieval_semantic.test["tfidf"]["sentence_recall@5"])} (TF-IDF) to <em className="text-accent">{pct(m.title_bonus?.test?.[String(m.title_bonus?.tuned_bonus)]?.["sentence_recall@5"] ?? 0)}</em>.</>}
        >
          <HBars rows={retrievalRows(m)} series={[{ key: "r1", label: "Recall@1", color: C.warn }, { key: "r5", label: "Recall@5", color: C.accent }]} />
          {pageRows(m).length > 0 && (
            <div className="mt-8 border-t border-line pt-5">
              <p className="mb-3 text-sm font-semibold">Finding the right page (classical retrieval ablation)</p>
              <HBars rows={pageRows(m)} series={[{ key: "r5", label: "Page recall@5", color: C.accent }, { key: "mrr", label: "MRR", color: C.good }]} />
            </div>
          )}
          <p className="mt-4 text-xs text-muted">Measured on a 70k-page subset of Wikipedia, so absolute recall is optimistic versus the full encyclopedia.</p>
        </Section>
      )}

      {h?.bert && (
        <Section title="Training curves" finding="Both model families start to overfit early: validation loss turns up while training loss keeps falling.">
          <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <div>
              <p className="mb-2 text-sm font-semibold">BERT fine-tuning (cross-entropy)</p>
              <LineChart
                xLabel="training step" yLabel="loss"
                series={[
                  { key: "tr", label: "train", color: C.accent, points: h.bert.train_steps.map((p: M) => ({ x: p.step, y: p.train_loss })) },
                  { key: "va", label: "validation", color: C.bad, points: h.bert.evals.map((p: M) => ({ x: p.step, y: p.val_loss })) },
                ]}
              />
              <p className="mt-2 text-xs text-muted">Best validation accuracy {pct(h.bert.best_val_acc)} after about 1.5 epochs.</p>
            </div>
            {h.lstm && h.gru && (
              <div>
                <p className="mb-2 text-sm font-semibold">BiLSTM and BiGRU (cross-entropy per epoch)</p>
                <LineChart
                  xLabel="epoch" yLabel="loss"
                  series={[
                    { key: "lt", label: "LSTM train", color: C.accent, dashed: true, points: h.lstm.epochs.map((p: M) => ({ x: p.epoch, y: p.train_loss })) },
                    { key: "lv", label: "LSTM validation", color: C.accent, points: h.lstm.epochs.map((p: M) => ({ x: p.epoch, y: p.val_loss })) },
                    { key: "gt", label: "GRU train", color: C.good, dashed: true, points: h.gru.epochs.map((p: M) => ({ x: p.epoch, y: p.train_loss })) },
                    { key: "gv", label: "GRU validation", color: C.good, points: h.gru.epochs.map((p: M) => ({ x: p.epoch, y: p.val_loss })) },
                  ]}
                />
              </div>
            )}
          </div>
        </Section>
      )}

      {cm && (
        <Section title="Where it goes wrong" finding="Refuted claims are the hardest: they are most often mistaken for not-enough-info.">
          <div className="grid gap-8 lg:grid-cols-[auto_1fr]">
            <ConfusionMatrix labels={["supported", "refuted", "not enough info"]} matrix={cm.rows_true_cols_pred} />
            <table className="w-full max-w-md self-start text-sm">
              <thead>
                <tr className="text-left text-xs text-muted"><th className="pb-2 font-normal">Class</th><th className="pb-2 font-normal">Precision</th><th className="pb-2 font-normal">Recall</th><th className="pb-2 font-normal">F1</th></tr>
              </thead>
              <tbody>
                {Object.entries(best.per_class).map(([k, v]: [string, M]) => (
                  <tr key={k} className="border-t border-line">
                    <td className="py-1.5">{k.replaceAll("_", " ")}</td>
                    <td className="font-mono">{v.precision.toFixed(3)}</td><td className="font-mono">{v.recall.toFixed(3)}</td><td className="font-mono">{v.f1.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-4 text-xs text-muted">
            Calibration error {best.ece.toFixed(3)}, cross-entropy {best.cross_entropy.toFixed(3)}. With gold evidence the plain BERT reaches
            {" "}{pct(m.verification?.models?.bert?.test?.oracle?.accuracy ?? 0)}, so retrieval costs about 5 points.
          </p>
        </Section>
      )}

      {ex?.citations && (
        <Section
          title="Explanations"
          finding={<>The sentences the verifier picks as decisive contain gold evidence for <em className="text-accent">{pct(ex.citations["decisive (verifier-driven)"].hit_rate)}</em> of claims.</>}
        >
          <HBars
            rows={Object.entries(ex.citations).map(([k, v]: [string, M]) => ({ label: k, highlight: k.startsWith("decisive"), values: { hit: v.hit_rate, prec: v.precision } }))}
            series={[{ key: "hit", label: "A cited sentence is gold", color: C.accent }, { key: "prec", label: "Precision of citations", color: C.good }]}
          />
          {ex.attribution && (
            <p className="mt-5 text-sm text-ink/90">
              Word attribution check ({ex.attribution.claims} claims): deleting the 2 words ranked most important lowers the verdict probability by{" "}
              <b>{ex.attribution.mean_drop_top2_words.toFixed(2)}</b>, versus <b>{ex.attribution.mean_drop_random_2_words.toFixed(2)}</b> for 2 random words.
            </p>
          )}
          {ex.summaries && (
            <div className="mt-6 overflow-x-auto">
              <p className="mb-2 text-sm font-semibold">Evidence summaries vs gold evidence ({ex.summaries.claims} claims)</p>
              <table className="w-full text-sm">
                <thead><tr className="text-left text-xs text-muted">
                  <th className="pb-2 font-normal">Method</th><th className="pb-2 font-normal">ROUGE-1</th><th className="pb-2 font-normal">ROUGE-2</th><th className="pb-2 font-normal">ROUGE-L</th><th className="pb-2 font-normal">BLEU</th><th className="pb-2 font-normal">Faithfulness</th>
                </tr></thead>
                <tbody>
                  {Object.entries(ex.summaries).filter(([, v]) => typeof v === "object").map(([k, v]: [string, M]) => (
                    <tr key={k} className="border-t border-line">
                      <td className="py-1.5">{k}</td>
                      <td className="font-mono">{v.rouge1_f.toFixed(3)}</td><td className="font-mono">{v.rouge2_f.toFixed(3)}</td>
                      <td className="font-mono">{v.rougeL_f.toFixed(3)}</td><td className="font-mono">{v.bleu.toFixed(3)}</td><td className="font-mono">{v.faithfulness.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-2 text-xs text-muted">Shorter summaries score higher ROUGE against short gold evidence; faithfulness is the share of summary words found in the retrieved evidence.</p>
            </div>
          )}
        </Section>
      )}

      {m.liar && (
        <Section
          title="A second dataset: LIAR"
          finding={m.liar.transfer_from_fever
            ? <>Our FEVER-trained pipeline does <em className="text-accent">not</em> transfer to political statements: it answers "not enough info" for {pct(1 - m.liar.transfer_from_fever.fever_pipeline.coverage_not_nei)} of them.</>
            : "Claim-only text classifiers on 12.8k PolitiFact statements."}
        >
          <HBars
            rows={[
              { label: "6 classes, TF-IDF", values: { acc: m.liar.six_class_text_only["tfidf_1-2gram"].accuracy, major: m.liar.six_class_text_only.majority_class_accuracy } },
              { label: "True-ish vs false-ish, TF-IDF", values: { acc: m.liar.binary_text_only["tfidf_1-2gram"].accuracy, major: m.liar.binary_text_only.majority_class_accuracy } },
              { label: "+ speaker, party, subject", values: { acc: m.liar.binary_with_metadata["tfidf_1-2gram"].accuracy, major: m.liar.binary_with_metadata.majority_class_accuracy } },
            ]}
            series={[{ key: "acc", label: "Test accuracy", color: C.accent }, { key: "major", label: "Always guess the majority class", color: C.muted }]}
          />
          {m.liar.transfer_from_fever && (
            <p className="mt-5 text-sm leading-relaxed text-ink/90">
              Transfer test on {m.liar.transfer_from_fever.claims} statements with a clear truth value: of the{" "}
              {m.liar.transfer_from_fever.fever_pipeline.decisive_claims} where the FEVER pipeline committed to supported/refuted it was right{" "}
              {m.liar.transfer_from_fever.fever_pipeline.accuracy_when_decisive != null ? pct(m.liar.transfer_from_fever.fever_pipeline.accuracy_when_decisive) : "n/a"} of the time (always guessing the majority: {pct(m.liar.transfer_from_fever.majority_class_accuracy)}); a claim-only model trained on LIAR gets{" "}
              {pct(m.liar.transfer_from_fever.claim_only_trained_on_liar.accuracy)}. Political statements need records and statistics that an encyclopedia subset does not contain.
            </p>
          )}
        </Section>
      )}

      {m.topics?.topics && (
        <Section title="LDA topics of the evidence pages" finding={`${m.topics.n_topics} latent topics over ${m.topics.pages.toLocaleString()} pages (perplexity ${Math.round(m.topics.perplexity)}).`}>
          <ul className="grid gap-2 sm:grid-cols-2">
            {m.topics.topics.map((t: M) => (
              <li key={t.id} className="rounded-md border border-line bg-bg/60 px-3 py-2 text-sm">
                <span className="font-mono text-[11px] text-accent">#{t.id}</span>{" "}
                <span className="text-ink/90">{t.words.slice(0, 6).join(", ")}</span>
                <span className="ml-1 text-xs text-muted">({t.pages.toLocaleString()} pages)</span>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  );
}
