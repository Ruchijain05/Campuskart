import { useEffect, useState } from "react";
import { HelpCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { LoadingState, Notice, PageTitle } from "../../components/SiteLayout";
import { useAuth } from "../../lib/auth";
import { api } from "../../lib/api";
import type { ProductQuestion } from "../../lib/types";

export function MyQuestionsPage() {
  const { token } = useAuth();
  const [questions, setQuestions] = useState<ProductQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    if (!token) return;
    api.listMyQuestions(token)
      .then((rows) => { if (active) setQuestions(rows); })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load your questions."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token]);

  return (
    <section className="content-narrow my-questions-page">
      <PageTitle eyebrow="YOUR ACCOUNT" title="My questions" description="Questions you have asked about CampusKart products and the seller’s replies." />
      {error && <Notice tone="error">{error}</Notice>}
      {loading ? <LoadingState label="Loading your questions..." /> : questions.length ? (
        <div className="my-question-list">
          {questions.map((item) => (
            <article className="my-question-card" key={item.id}>
              <div className="my-question-product"><HelpCircle size={16} /><Link to={`/products/${item.product_id}`}>{item.product_name}</Link><time>{new Date(item.created_at).toLocaleDateString()}</time></div>
              <p className="my-question-text">{item.question}</p>
              {item.answer ? <div className="my-question-answer"><b>Seller answer</b><p>{item.answer}</p>{item.answered_at && <time>{new Date(item.answered_at).toLocaleDateString()}</time>}</div> : <span className="my-question-status">Waiting for an answer</span>}
            </article>
          ))}
        </div>
      ) : <div className="empty-state"><span className="empty-emoji"><HelpCircle size={24} /></span><h3>No questions yet</h3><p>Ask a seller from a product page to see your question here.</p><Link className="button button-dark" to="/">Browse products</Link></div>}
    </section>
  );
}
