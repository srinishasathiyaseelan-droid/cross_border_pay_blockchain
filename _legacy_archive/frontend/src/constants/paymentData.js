export const COMPANIES = [
    { id: 'abc-india', name: 'ABC India Pvt Ltd', country: 'India', type: 'buyer' },
    { id: 'global-gmbh', name: 'Global Components GmbH', country: 'Germany', type: 'supplier' },
    { id: 'technova', name: 'TechNova Solutions', country: 'India', type: 'buyer' },
    { id: 'europarts', name: 'EuroParts Manufacturing', country: 'France', type: 'supplier' },
    { id: 'us-components', name: 'US Components Inc.', country: 'USA', type: 'supplier' },
    { id: 'bharat-ind', name: 'Bharat Industrial Systems', country: 'India', type: 'buyer' },
    { id: 'asia-trade', name: 'Asia Trade Holdings', country: 'Singapore', type: 'buyer' },
    { id: 'uk-materials', name: 'UK Materials Ltd', country: 'UK', type: 'supplier' },
];

export const BUYER_COMPANIES = COMPANIES.filter(c => c.type === 'buyer');
export const SUPPLIER_COMPANIES = COMPANIES.filter(c => c.type === 'supplier');

export const COUNTRIES = ['India', 'Germany', 'USA', 'UK', 'France', 'Singapore', 'Japan', 'UAE'];

export const CURRENCIES = [
    { id: 'USD', label: 'USD — US Dollar', symbol: '$' },
    { id: 'EUR', label: 'EUR — Euro', symbol: '€' },
    { id: 'INR', label: 'INR — Indian Rupee', symbol: '₹' },
    { id: 'USDC', label: 'USDC — Stablecoin', symbol: '$' },
    { id: 'GBP', label: 'GBP — British Pound', symbol: '£' },
];

export const PAYMENT_PURPOSES = [
    'Raw Materials Purchase',
    'Component Supply',
    'Manufacturing Equipment',
    'Finished Goods',
    'Service Agreement',
    'Consulting Services',
    'Technology License',
];

export const PAYMENT_TERMS = [
    { id: 'full-advance', label: '100% Advance Payment' },
    { id: 'milestone', label: '30% Order / 40% Shipment / 30% Delivery' },
    { id: 'net-30', label: 'Net 30 Days' },
    { id: 'net-60', label: 'Net 60 Days' },
    { id: 'lc', label: 'Letter of Credit (L/C)' },
];

export const PAYMENT_STATUSES = [
    'Created', 'Accepted', 'Funded', 'In Progress',
    'Partially Released', 'Completed', 'Disputed', 'Refunded'
];

export const DOCUMENT_TYPES = [
    'Invoice',
    'Purchase Order',
    'Shipping Document',
    'Bill of Lading',
    'Delivery Proof',
    'Contract Agreement',
    'Inspection Certificate',
];

export const RISK_FACTORS = [
    'Large transaction amount',
    'New supplier',
    'Unusual transaction frequency',
    'Country risk',
    'Abnormal payment pattern',
    'First-time trade route',
    'Currency volatility',
];

// Maps existing batch data to payment-like display data
export const DEMO_PAYMENTS = [
    { id: 'CP-001', buyer: 'ABC India Pvt Ltd', supplier: 'Global Components GmbH', route: 'India → Germany', amount: 10000, currency: 'USD', status: 'Funded', risk: 'Low' },
    { id: 'CP-002', buyer: 'TechNova Solutions', supplier: 'US Components Inc.', route: 'India → USA', amount: 25000, currency: 'USD', status: 'Completed', risk: 'Low' },
    { id: 'CP-003', buyer: 'Bharat Industrial Systems', supplier: 'EuroParts Manufacturing', route: 'India → France', amount: 50000, currency: 'EUR', status: 'Pending', risk: 'Medium' },
    { id: 'CP-004', buyer: 'Asia Trade Holdings', supplier: 'UK Materials Ltd', route: 'India → UK', amount: 75000, currency: 'GBP', status: 'Review', risk: 'High' },
    { id: 'CP-005', buyer: 'ABC India Pvt Ltd', supplier: 'US Components Inc.', route: 'India → USA', amount: 15000, currency: 'USDC', status: 'In Progress', risk: 'Low' },
];

// Helper to map a batchId to demo payment data
export const mapBatchToPayment = (batch, index) => {
    const demo = DEMO_PAYMENTS[index % DEMO_PAYMENTS.length];
    const buyers = BUYER_COMPANIES;
    const suppliers = SUPPLIER_COMPANIES;
    const buyer = buyers[index % buyers.length];
    const supplier = suppliers[index % suppliers.length];
    return {
        paymentId: `CP-${String(batch.batchId || index + 1).padStart(3, '0')}`,
        buyer: buyer.name,
        supplier: supplier.name,
        buyerCountry: buyer.country,
        supplierCountry: supplier.country,
        route: `${buyer.country} → ${supplier.country}`,
        amount: demo.amount,
        currency: demo.currency,
        status: batch.statusLabel === 'ACTIVE' ? 'Funded' : batch.statusLabel === 'TRANSFERRED' ? 'Completed' : batch.statusLabel === 'EXPIRED' ? 'Refunded' : 'Pending',
        risk: batch.fraudScore > 70 ? 'High' : batch.fraudScore > 30 ? 'Medium' : 'Low',
        ...batch,
    };
};
