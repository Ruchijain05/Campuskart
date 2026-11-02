import { useEffect, useState, type FormEvent } from "react";
import { HelpCircle, MessageCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { LoadingState, Notice } from "../../components/SiteLayout";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { Product, ProductQuestion } from "../../lib/types";

export function ProductQuestionsSection({ product }: { product: Product }) {
  const { token, user } = useAuth();
  const [questions, setQuestions] = useState<ProductQuestion[]>([]);
  const [questionText, setQuestionText] = useState("");
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [busyAnswer, setBusyAnswer] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const ownsProduct = user?.role === "seller" && user.id === product.seller_id;

  useEffect(() => {
    let active = true;
    setLoading(true);
    api.listProductQuestions(product.id)
      .then((rows) => { if (active) setQuestions(rows); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load product questions."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [product.id]);

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || user?.role !== "buyer") return;
    setBusy(true); setError(""); setSuccess("");
    try {
      const question = await api.askProductQuestion(product.id, questionText, token);
      setQuestions((current) => [question, ...current]);
      setQuestionText("");
      setSuccess("Your question has been posted.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not post your question.");
    } finally { setBusy(false); }
  }

  async function submitAnswer(event: FormEvent<HTMLFormElement>, question: ProductQuestion) {
    event.preventDefault();
    if (!token || !ownsProduct) return;
    const answerText = answers[question.id] ?? question.answer ?? "";
    setBusyAnswer(question.id); setError(""); setSuccess("");
    try {
      const updated = await api.answerProductQuestion(question.id, answerText, token);
      setQuestions((current) => current.map((item) => item.id === updated.id ? updated : item));
      setAnswers((current) => ({ ...current, [question.id]: updated.answer ?? "" }));
      setSuccess("Your answer is now public.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save your answer.");
    } finally { setBusyAnswer(null); }
  }

  return (
    <section className="questions-section" aria-labelledby="questions-heading">
      <div className="questions-heading"><div><span className="eyebrow">ASK THE SELLER</span><h2 id="questions-heading">Product questions</h2></div><span>{questions.length} {questions.length === 1 ? "question" : "questions"}</span></div>
      {error && <Notice tone="error">{error}</Notice>}{success && <Notice tone="success">{success}</Notice>}
      {user?.role === "buyer" && token ? (
        <form className="question-form" onSubmit={(event) => void submitQuestion(event)}>
          <label htmlFor="product-question-input">Have a question about this product?</label>
          <textarea id="product-question-input" required minLength={1} maxLength={2000} rows={3} value={questionText} onChange={(event) => setQuestionText(event.target.value)} placeholder="Ask the seller about this item..." />
          <button className="button button-dark" disabled={busy}>{busy ? "Posting..." : "Ask question"}</button>
        </form>
      ) : !user ? <p className="question-signin"><Link to="/login">Sign in as a buyer</Link> to ask the seller a question.</p> : null}
      {loading ? <LoadingState label="Loading questions..." /> : questions.length ? (
        <div className="question-list">
          {questions.map((item) => (
            <article className="question-card" key={item.id}>
              <div className="question-card-heading"><span><HelpCircle size={17} /><b>{item.buyer_name} asked</b></span><time>{new Date(item.created_at).toLocaleDateString()}</time></div>
              <p className="question-text">{item.question}</p>
              {item.answer ? <div className="answer-box"><b><MessageCircle size={15} /> Seller answer</b><p>{item.answer}</p>{item.answered_at && <time>{new Date(item.answered_at).toLocaleDateString()}</time>}</div> : <p className="question-pending">Waiting for the seller to answer.</p>}
              {ownsProduct && token && <form className="seller-answer-form" onSubmit={(event) => void submitAnswer(event, item)}>
                <label htmlFor={`answer-${item.id}`}>{item.answer ? "Edit your answer" : "Write an answer"}</label>
                <textarea id={`answer-${item.id}`} required minLength={1} maxLength={3000} rows={3} value={answers[item.id] ?? item.answer ?? ""} onChange={(event) => setAnswers((current) => ({ ...current, [item.id]: event.target.value }))} />
                <button className="button button-outline" disabled={busyAnswer === item.id}>{busyAnswer === item.id ? "Saving..." : item.answer ? "Update answer" : "Post answer"}</button>
              </form>}
            </article>
          ))}
        </div>
      ) : <div className="questions-empty"><HelpCircle size={20} /><span>No questions yet. Ask the first one.</span></div>}
    </section>
  );
}
