import { useEffect, useState, type FormEvent } from "react";
import { Star, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { LoadingState, Notice } from "../../components/SiteLayout";
import { useAuth } from "../../lib/auth";
import { api } from "../../lib/api";
import type { ProductReview, ProductReviewSummary } from "../../lib/types";

function Stars({ rating, interactive = false, onChange }: { rating: number; interactive?: boolean; onChange?: (rating: number) => void }) {
  return <span className={interactive ? "review-stars review-stars-edit" : "review-stars"} aria-label={`${rating} out of 5 stars`}>
    {[1, 2, 3, 4, 5].map((value) => interactive ? (
      <button type="button" key={value} aria-label={`${value} star${value === 1 ? "" : "s"}`} aria-pressed={rating === value} onClick={() => onChange?.(value)}>
        <Star size={19} fill={value <= rating ? "currentColor" : "none"} />
      </button>
    ) : <Star size={15} key={value} fill={value <= rating ? "currentColor" : "none"} />)}
  </span>;
}

export function ReviewsSection({ productId }: { productId: number }) {
  const { token, user } = useAuth();
  const [summary, setSummary] = useState<ProductReviewSummary | null>(null);
  const [myReview, setMyReview] = useState<ProductReview | null>(null);
  const [rating, setRating] = useState(5);
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    const mineRequest = token && user?.role === "buyer"
      ? api.getMyProductReview(productId, token)
      : Promise.resolve(null);
    Promise.all([api.getProductReviews(productId), mineRequest])
      .then(([nextSummary, mine]) => {
        if (!active) return;
        setSummary(nextSummary); setMyReview(mine);
        setRating(mine?.rating ?? 5); setBody(mine?.body ?? "");
      })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load product reviews."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [productId, token, user?.role]);

  async function refreshSummary() {
    setSummary(await api.getProductReviews(productId));
  }

  async function submitReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || user?.role !== "buyer") return;
    setError(""); setSuccess(""); setBusy(true);
    try {
      const input = { rating, body };
      const saved = myReview
        ? await api.updateProductReview(myReview.id, input, token)
        : await api.createProductReview(productId, input, token);
      setMyReview(saved); setBody(saved.body); setRating(saved.rating);
      await refreshSummary();
      setSuccess(myReview ? "Your review has been updated." : "Thanks for sharing your review.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save your review.");
    } finally { setBusy(false); }
  }

  async function deleteReview() {
    if (!token || !myReview || !window.confirm("Delete your review for this product?")) return;
    setError(""); setSuccess(""); setBusy(true);
    try {
      await api.deleteProductReview(myReview.id, token);
      setMyReview(null); setRating(5); setBody("");
      await refreshSummary();
      setSuccess("Your review has been deleted.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete your review.");
    } finally { setBusy(false); }
  }

  return (
    <section className="reviews-section" aria-labelledby="reviews-heading">
      <div className="reviews-heading"><div><span className="eyebrow">CAMPUSKART COMMUNITY</span><h2 id="reviews-heading">Reviews &amp; ratings</h2></div>
        {summary && <div className="reviews-average">{summary.review_count ? <><b>{Number(summary.average_rating).toFixed(1)}</b><Stars rating={Math.round(Number(summary.average_rating))} /><span>{summary.review_count} {summary.review_count === 1 ? "review" : "reviews"}</span></> : <span>No ratings yet</span>}</div>}
      </div>
      {error && <Notice tone="error">{error}</Notice>}{success && <Notice tone="success">{success}</Notice>}
      {loading ? <LoadingState label="Loading reviews..." /> : <>
        {user?.role === "buyer" && token ? <form className="review-form" onSubmit={(event) => void submitReview(event)}>
          <h3>{myReview ? "Edit your review" : "Share your experience"}</h3>
          <label className="review-rating-label">Your rating<Stars rating={rating} interactive onChange={setRating} /></label>
          <label className="review-body-label">Your review<textarea required minLength={1} maxLength={3000} rows={4} value={body} onChange={(event) => setBody(event.target.value)} placeholder="What should other students know about this product?" /></label>
          <div className="review-form-actions"><button className="button button-dark" disabled={busy}>{busy ? "Saving..." : myReview ? "Save changes" : "Post review"}</button>{myReview && <button type="button" className="button button-outline review-delete-button" onClick={() => void deleteReview()} disabled={busy}><Trash2 size={14} /> Delete review</button>}</div>
        </form> : !user ? <p className="review-signin"><Link to="/login">Sign in as a buyer</Link> to leave a rating and review.</p> : null}
        {summary?.reviews.length ? <div className="review-list">{summary.reviews.map((review) => <article className="review-card" key={review.id}>
          <div className="review-card-heading"><div><b>{review.reviewer_name}</b><Stars rating={review.rating} /></div><time dateTime={review.updated_at}>{new Date(review.updated_at).toLocaleDateString()}</time></div>
          <p>{review.body}</p>
        </article>)}</div> : <div className="reviews-empty"><Star size={22} /><span>No reviews yet. Be the first to share what you think.</span></div>}
      </>}
    </section>
  );
}
