from decimal import Decimal

from app.models.order import Order


def _pdf_text(value: object) -> str:
    # Built-in PDF Helvetica uses WinAnsi; replace unsupported characters safely.
    text = str(value).encode("cp1252", errors="replace").decode("cp1252")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").replace("\r", " ").replace("\n", " ")


def _money(value: Decimal | int | float | None) -> str:
    return f"INR {Decimal(value or 0):,.2f}"


def _invoice_lines(order: Order) -> list[tuple[str, int]]:
    lines: list[tuple[str, int]] = [
        ("CampusKart - Order Invoice", 18),
        (f"Invoice: CK-{order.id:06d}", 11),
        (f"Order date: {order.created_at:%Y-%m-%d %H:%M}", 10),
        (f"Order status: {order.status.title()} | Payment: {order.payment_method.upper()} ({order.payment_status})", 10),
        ("", 8),
        ("Collect at campus pickup" if getattr(order, "delivery_method", "home_delivery") == "campus_pickup" else "Deliver to", 12),
        (order.delivery_name, 10),
        (order.delivery_phone, 10),
        (order.address_line, 10),
        (f"{order.city}, {order.state} {order.postal_code}", 10),
        ("", 8),
        ("Products", 13),
        ("Product details | Qty | Unit price | Line total", 10),
        ("-" * 82, 9),
    ]
    for item in order.items:
        product = f"{item.product_name} (Product #{item.product_id})" if item.product_id is not None else item.product_name
        lines.append((f"{product} | {item.quantity} | {_money(item.unit_price)} | {_money(item.line_total)}", 10))
    lines.extend([
        ("-" * 82, 9),
        (f"Subtotal: {_money(order.subtotal)}", 11),
    ])
    if order.discount_amount:
        label = f"Discount{f' ({order.discount_description or order.coupon_code})' if order.discount_description or order.coupon_code else ''}"
        lines.append((f"{label}: -{_money(order.discount_amount)}", 11))
    lines.extend([
        (f"{'Pickup' if getattr(order, 'delivery_method', 'home_delivery') == 'campus_pickup' else 'Delivery'} charges: {_money(order.shipping_fee)}", 11),
        (f"Final amount: {_money(order.total)}", 14),
    ])
    if order.estimated_delivery_at:
        lines.append((f"Estimated delivery: {order.estimated_delivery_at:%Y-%m-%d %H:%M}", 10))
    if order.courier_name:
        lines.append((f"Courier: {order.courier_name}", 10))
    if order.tracking_id:
        lines.append((f"Tracking ID: {order.tracking_id}", 10))
    if getattr(order, "delivery_method", "home_delivery") == "campus_pickup":
        lines.append((f"Pickup status: {order.pickup_status.replace('_', ' ').title()}", 10))
    lines.extend([("", 8), ("Thank you for shopping with CampusKart.", 10)])
    return lines


def _wrap(text: str, max_chars: int = 88) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    words = text.split(" ")
    wrapped: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            wrapped.append(current)
            current = word
        else:
            current = candidate
    if current:
        wrapped.append(current)
    return wrapped


def generate_invoice_pdf(order: Order) -> bytes:
    pages: list[list[bytes]] = [[]]
    y = 795
    for text, font_size in _invoice_lines(order):
        for part in _wrap(text):
            if y < 55:
                pages.append([])
                y = 795
            safe = _pdf_text(part)
            command = f"BT /F1 {font_size} Tf 48 {y} Td ({safe}) Tj ET".encode("cp1252", errors="replace")
            pages[-1].append(command)
            y -= max(17, font_size + 6)

    objects: list[bytes] = []
    page_ids = [5 + page_index * 2 for page_index in range(len(pages))]
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii"))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    for index, commands in enumerate(pages):
        stream = b"\n".join(commands)
        content_id = 4 + index * 2
        page_id = content_id + 1
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("ascii") + stream + b"\nendstream")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode("ascii")
        )

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_id, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{object_id} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)
