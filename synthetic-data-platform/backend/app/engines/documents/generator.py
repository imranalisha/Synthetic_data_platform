from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os
import uuid
from typing import Dict, Any

def generate_invoice_pdf(data: Dict[str, Any], output_dir: str = "generated_docs") -> str:
    """Generates a synthetic PDF invoice using ReportLab."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    filename = f"invoice_{uuid.uuid4().hex[:8]}.pdf"
    filepath = os.path.join(output_dir, filename)
    
    # Initialize PDF Canvas
    c = canvas.Canvas(filepath, pagesize=letter)
    
    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "SYNTHETIC INVOICE")
    
    # Client Details
    c.setFont("Helvetica", 12)
    c.drawString(50, 710, f"Billed To: {data.get('name', 'Unknown Client')}")
    c.drawString(50, 690, f"Email: {data.get('email', 'N/A')}")
    
    # Invoice Items
    c.drawString(50, 650, "Services/Products Rendered:")
    y = 630
    for item in data.get('items', [{'name': 'General Service', 'amount': 100.0}]):
        c.drawString(70, y, f"- {item['name']}: ${item['amount']}")
        y -= 20
        
    # Footer & Total
    c.line(50, y-10, 550, y-10)
    c.drawString(50, y-30, f"Total Amount Due: ${data.get('total', 0.0)}")
    
    c.save()
    return filepath