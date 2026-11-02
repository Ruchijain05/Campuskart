import { useState } from "react";
import { Download } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";

export function InvoiceDownloadButton({ orderId, className = "button button-light" }: { orderId: number; className?: string }) {
  const { token } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function download() {
    if (!token || busy) return;
    setBusy(true); setError("");
    try {
      const blob = await api.downloadOrderInvoice(orderId, token);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `campuskart-invoice-${orderId}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not download the invoice.");
    } finally { setBusy(false); }
  }

  return <span className="invoice-download-control"><button type="button" className={className} onClick={() => void download()} disabled={busy || !token}><Download size={14} />{busy ? "Preparing..." : "Download invoice"}</button>{error && <small role="alert">{error}</small>}</span>;
}
