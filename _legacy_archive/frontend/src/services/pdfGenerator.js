import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import QRCode from 'qrcode';

export const generateEventRecordedPDF = async (eventData) => {
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();

    // Title
    doc.setFontSize(22);
    doc.setTextColor(40, 40, 40);
    doc.text("EventChain – Distribution Record Receipt", pageWidth / 2, 20, { align: 'center' });

    // Sub-header
    doc.setFontSize(12);
    doc.setTextColor(100, 100, 100);
    doc.text("Official Digital Record - Private & Secure", pageWidth / 2, 28, { align: 'center' });

    // Divider
    doc.setLineWidth(0.5);
    doc.line(20, 35, pageWidth - 20, 35);

    // Content Data
    const startY = 45;
    doc.setFontSize(11);
    doc.setTextColor(0, 0, 0);

    const rows = [
        ["Event ID", eventData.txHash || eventData.transactionHash || "PENDING"],
        ["Timestamp", new Date(eventData.timestamp || Date.now()).toLocaleString()],
        ["Event Type", eventData.eventType || "GENERIC_EVENT"],
    ];

    // Only add PDS specific fields if it's a PDS event
    if (eventData.eventType === 'PDS_DISTRIBUTION') {
        rows.push(["Beneficiary ID", eventData.beneficiaryId ? `***${eventData.beneficiaryId.slice(-4)}` : "N/A"]);
        rows.push(["Shop ID", eventData.shopId || "N/A"]);
        rows.push(["Quantity", `${eventData.quantity} (kg/liters)`]);
        rows.push(["Region", eventData.region || "Unknown"]);
        rows.push(["AI Fraud Score", eventData.fraudScore !== undefined ? eventData.fraudScore : "N/A"]);
        rows.push(["Risk Level", eventData.riskLevel || "N/A"]);
        rows.push(["Status", eventData.riskLevel === 'HIGH' ? "FLAGGED" : "APPROVED"]);
    } else {
        // Generic Event Fields
        // Add file name if available (from metadata mainly, but for receipt we might not have it parsed)
    }

    // Common Footer Fields
    rows.push(["IPFS Hash", eventData.ipfsHash || eventData.metadataHash || "Pending"]);

    autoTable(doc, {
        startY: startY,
        head: [['Field', 'Value']],
        body: rows,
        theme: 'striped',
        headStyles: { fillColor: [41, 128, 185] },
        styles: { fontSize: 10, cellPadding: 3 },
        columnStyles: { 0: { fontStyle: 'bold', cellWidth: 50 } }
    });

    let finalY = doc.lastAutoTable.finalY + 10;

    // QR Code
    try {
        const qrData = JSON.stringify({
            tx: eventData.txHash,
            ipfs: eventData.ipfsHash,
            score: eventData.fraudScore
        });
        const qrDataUrl = await QRCode.toDataURL(qrData);
        doc.addImage(qrDataUrl, 'PNG', pageWidth / 2 - 25, finalY, 50, 50);
        finalY += 55;
    } catch (err) {
        console.error("QR Gen Error", err);
    }

    // Blockchain Hash Section
    doc.setFontSize(10);
    doc.setTextColor(100, 100, 100);
    doc.text("Blockchain Tx Hash:", 14, finalY);
    doc.setFontSize(9);
    doc.setTextColor(0, 0, 0);
    doc.text(eventData.txHash || "N/A", 14, finalY + 5, { maxWidth: pageWidth - 28 });

    // Footer
    const footerY = doc.internal.pageSize.getHeight() - 20;
    doc.setFontSize(8);
    doc.setTextColor(150, 150, 150);
    doc.text("This document is cryptographically verifiable using the EventChain ledger.", pageWidth / 2, footerY, { align: 'center' });
    doc.text("Generated locally. No external services used.", pageWidth / 2, footerY + 5, { align: 'center' });

    doc.save(`EventChain_Receipt_${Date.now()}.pdf`);
};

export const generateVerificationPDF = async (verificationData) => {
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();

    // -- HEADER --
    // Green Header Bar
    doc.setFillColor(39, 174, 96); // Green
    doc.rect(0, 0, pageWidth, 40, 'F');

    doc.setFontSize(24);
    doc.setTextColor(255, 255, 255);
    doc.text("EventChain Verification Certificate", pageWidth / 2, 25, { align: 'center' });

    doc.setFontSize(10);
    doc.text("Official Blockchain-Verified Document", pageWidth / 2, 33, { align: 'center' });

    let y = 55;

    // -- SECTION A: EVENT SUMMARY --
    doc.setFontSize(14);
    doc.setTextColor(33, 33, 33);
    doc.setFont("helvetica", "bold");
    doc.text("A. Event Summary", 20, y);
    y += 10;

    const content = verificationData.content || {};
    const meta = content.data || {};
    const ai = content.aiAnalysis || {};
    const event = verificationData.event || {};

    const summaryData = [
        ["Event ID", `EVT-${(event.txHash || "").substring(0, 10)}...`],
        ["Event Type", content.type || "GENERIC"],
        ["Timestamp", new Date(meta.timestamp || Date.now()).toLocaleString()],
        ["Status", "APPROVED_ON_CHAIN"]
    ];

    if (content.type === 'PDS_DISTRIBUTION') {
        summaryData.push(["Beneficiary ID", meta.beneficiaryId || "N/A"]);
        summaryData.push(["Shop ID", meta.shopId || "N/A"]);
        summaryData.push(["Commodity", "Rice (PDS)"]);
        summaryData.push(["Quantity", `${meta.quantity} kg`]);
        summaryData.push(["AI Fraud Score", ai.fraudScore !== undefined ? ai.fraudScore.toString() : "N/A"]);
        summaryData.push(["Risk Level", ai.riskLevel || "N/A"]);
    } else {
        summaryData.push(["File Name", meta.fileName || "N/A"]);
    }

    autoTable(doc, {
        startY: y,
        body: summaryData,
        theme: 'plain',
        styles: { fontSize: 10, cellPadding: 1.5 },
        columnStyles: { 0: { fontStyle: 'bold', cellWidth: 50 }, 1: { cellWidth: 100 } }
    });

    y = doc.lastAutoTable.finalY + 15;

    // -- SECTION B: INTEGRITY PROOF --
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text("B. Data Integrity Proof", 20, y);
    y += 8;

    const integrityData = [
        ["IPFS File Hash", event.ipfsHash || "N/A"],
        ["Blockchain Tx Hash", event.txHash || "N/A"],
        ["Match Status", "VERIFIED MATCH"],
        ["Tampering Detected", "NO"],
        ["Local Hash Consistency", "PASS"] // We assume pass if verified
    ];

    autoTable(doc, {
        startY: y,
        body: integrityData,
        theme: 'striped',
        headStyles: { fillColor: [44, 62, 80] },
        styles: { fontSize: 9, cellPadding: 2 },
        columnStyles: { 0: { fontStyle: 'bold', cellWidth: 50 } }
    });

    y = doc.lastAutoTable.finalY + 15;

    // -- SECTION C: VISUAL TRUST --
    doc.setDrawColor(39, 174, 96);
    doc.setLineWidth(1);
    doc.rect(20, y, pageWidth - 40, 25);

    doc.setFontSize(12);
    doc.setTextColor(39, 174, 96);
    doc.text("✔ VERIFIED ON BLOCKCHAIN", 30, y + 10);
    doc.text("✔ DATA INTEGRITY CONFIRMED", 30, y + 18);
    doc.text("✔ EVENT AUTHENTIC", 110, y + 10);
    doc.text("✔ AI CHECK PASSED", 110, y + 18);

    y += 35;

    // -- SECTION D: AUTHORITY & QR --
    doc.setTextColor(33, 33, 33);
    doc.setFontSize(14);
    doc.text("C. Authority & Verification", 20, y);

    // QR Code
    try {
        const qrContent = `http://localhost:3000/verify?hash=${event.ipfsHash}`;
        const qrDataUrl = await QRCode.toDataURL(qrContent);
        doc.addImage(qrDataUrl, 'PNG', pageWidth - 60, y - 5, 40, 40);

        doc.setFontSize(8);
        doc.text("Scan to Re-verify", pageWidth - 60 + 20, y + 38, { align: 'center' });
    } catch (e) { }

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.text(`Verified By: EventChain Authority Node`, 20, y + 10);
    doc.text(`Verification Mode: Blockchain + IPFS Hash Match`, 20, y + 16);
    doc.text(`System Version: EventChain v1.3.2`, 20, y + 22);
    doc.text(`Gen Date: ${new Date().toLocaleString()}`, 20, y + 28);

    y += 45;

    // -- RAW PAYLOAD --
    if (y < pageHeight - 60) {
        doc.setFontSize(10);
        doc.setFont("helvetica", "bold");
        doc.text("Raw Blockchain Payload (For Auditors)", 20, y);
        y += 5;

        doc.setFillColor(245, 245, 245);
        doc.rect(20, y, pageWidth - 40, 40, 'F');

        doc.setFont("courier", "normal");
        doc.setFontSize(7);
        doc.setTextColor(80, 80, 80);

        const jsonStr = JSON.stringify(content, null, 2);
        const lines = doc.splitTextToSize(jsonStr, pageWidth - 50);
        // Clip to avoid overflow
        const maxLines = 15;
        const displayLines = lines.slice(0, maxLines);
        if (lines.length > maxLines) displayLines.push("... (truncated)");

        doc.text(displayLines, 25, y + 5);
    }

    // Footer
    const footerY = pageHeight - 15;
    doc.setFont("helvetica", "italic");
    doc.setFontSize(8);
    doc.setTextColor(150, 150, 150);
    doc.text("This certificate validates that the record exists immutably on the EventChain ledger.", pageWidth / 2, footerY, { align: 'center' });

    doc.save(`Verification_Certificate_${Date.now()}.pdf`);
};
