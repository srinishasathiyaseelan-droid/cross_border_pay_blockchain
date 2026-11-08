/**
 * Risk-Adaptive Smart Contract Settlement for SME Cross-Border Payments
 * Interactive JavaScript Library with Live Currency Conversion
 */

const CURRENCY_SYMBOLS = {
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'INR': '₹',
    'SGD': 'S$',
    'AED': 'AED',
    'AUD': 'A$',
    'CAD': 'C$',
    'JPY': '¥'
};

const COUNTRY_TO_CURRENCY = {
    'United States': 'USD',
    'United Kingdom': 'GBP',
    'Germany': 'EUR',
    'France': 'EUR',
    'Singapore': 'SGD',
    'Japan': 'JPY',
    'India': 'INR',
    'United Arab Emirates': 'AED',
    'Australia': 'AUD',
    'Canada': 'CAD',
    'Brazil': 'USD',
    'Nigeria': 'USD'
};

let conversionDebounceTimer = null;
let currentNormalizedUsdAmount = 4500.0;

document.addEventListener('DOMContentLoaded', function () {
    // 1. Auto-dismiss flash alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // 2. Setup Currency Conversion Engine if on Payment page
    initCurrencyConverter();

    // 3. Setup Scenario Fillers if on Payment page
    initScenarioFillers();

    // 4. Setup Live Risk Preview on Payment form
    initLiveRiskPreview();

    // 5. Setup Blockchain Verification API Trigger
    initBlockchainVerifier();

    // 6. Setup Form Submit & Duplicate Submission Prevention
    initFormSubmissionGuard();
});

/**
 * Real-Time Currency Conversion Engine
 */
function initCurrencyConverter() {
    const senderCurrSelect = document.getElementById('sender_currency');
    const receiverCurrSelect = document.getElementById('receiver_currency');
    const senderCountrySelect = document.getElementById('sender_country');
    const receiverCountrySelect = document.getElementById('receiver_country');
    const amountInput = document.getElementById('amount');
    const convertBtn = document.getElementById('btn-convert-currency');

    if (!senderCurrSelect || !receiverCurrSelect || !amountInput) return;

    // Auto-update currency symbol prefix next to amount input
    const updateSymbolPrefix = () => {
        const symbolEl = document.getElementById('amount-currency-symbol');
        const labelEl = document.getElementById('source-currency-label');
        const curr = senderCurrSelect.value;
        const sym = CURRENCY_SYMBOLS[curr] || '$';
        if (symbolEl) symbolEl.innerText = sym;
        if (labelEl) labelEl.innerText = `${curr} ${sym}`;
    };

    // Auto-suggest currency on country change
    if (senderCountrySelect) {
        senderCountrySelect.addEventListener('change', function () {
            const defaultCurr = COUNTRY_TO_CURRENCY[this.value];
            if (defaultCurr && senderCurrSelect.querySelector(`option[value="${defaultCurr}"]`)) {
                senderCurrSelect.value = defaultCurr;
                updateSymbolPrefix();
                debounceConversion();
            }
        });
    }

    if (receiverCountrySelect) {
        receiverCountrySelect.addEventListener('change', function () {
            const defaultCurr = COUNTRY_TO_CURRENCY[this.value];
            if (defaultCurr && receiverCurrSelect.querySelector(`option[value="${defaultCurr}"]`)) {
                receiverCurrSelect.value = defaultCurr;
                debounceConversion();
            }
        });
    }

    senderCurrSelect.addEventListener('change', () => {
        updateSymbolPrefix();
        debounceConversion();
    });

    receiverCurrSelect.addEventListener('change', () => {
        debounceConversion();
    });

    amountInput.addEventListener('input', () => {
        debounceConversion();
    });

    if (convertBtn) {
        convertBtn.addEventListener('click', () => {
            performCurrencyConversion();
        });
    }

    updateSymbolPrefix();
    // Initial fetch on page load
    performCurrencyConversion();
}

function debounceConversion() {
    clearTimeout(conversionDebounceTimer);
    conversionDebounceTimer = setTimeout(() => {
        performCurrencyConversion();
    }, 450);
}

function performCurrencyConversion() {
    const amountInput = document.getElementById('amount');
    const senderCurrSelect = document.getElementById('sender_currency');
    const receiverCurrSelect = document.getElementById('receiver_currency');

    const loadingIndicator = document.getElementById('conversion-loading-indicator');
    const errorBox = document.getElementById('conversion-error-box');
    const errorText = document.getElementById('conversion-error-text');
    const detailsContent = document.getElementById('conversion-details-content');

    const rateDisplay = document.getElementById('display-exchange-rate');
    const convertedAmountDisplay = document.getElementById('display-converted-amount');
    const targetCurrCodeDisplay = document.getElementById('display-target-currency-code');
    const rateProviderDisplay = document.getElementById('display-rate-provider');
    const rateTimestampDisplay = document.getElementById('display-rate-timestamp');

    const hiddenRate = document.getElementById('confirmed_exchange_rate');
    const hiddenConverted = document.getElementById('confirmed_converted_amount');
    const hiddenProvider = document.getElementById('confirmed_rate_provider');
    const hiddenTimestamp = document.getElementById('confirmed_rate_timestamp');

    const convertBtn = document.getElementById('btn-convert-currency');

    if (!amountInput || !senderCurrSelect || !receiverCurrSelect) return;

    const amount = parseFloat(amountInput.value);
    const sourceCurr = senderCurrSelect.value;
    const targetCurr = receiverCurrSelect.value;

    // Validation
    if (isNaN(amount) || amount <= 0) {
        if (errorBox && errorText) {
            errorText.innerText = "Please enter a valid transaction amount greater than 0.";
            errorBox.style.display = 'block';
            if (detailsContent) detailsContent.style.opacity = '0.35';
        }
        return;
    }

    // Show loading feedback
    if (loadingIndicator) loadingIndicator.style.display = 'flex';
    if (errorBox) errorBox.style.display = 'none';
    if (detailsContent) detailsContent.style.opacity = '0.35';
    if (convertBtn) {
        convertBtn.disabled = true;
        const icon = document.getElementById('convert-btn-icon');
        if (icon) icon.innerHTML = '<span class="spinner-pulse"></span>';
    }

    const url = `/api/convert_currency?amount=${encodeURIComponent(amount)}&source_currency=${encodeURIComponent(sourceCurr)}&target_currency=${encodeURIComponent(targetCurr)}`;

    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (loadingIndicator) loadingIndicator.style.display = 'none';
            if (detailsContent) detailsContent.style.opacity = '1.0';
            if (convertBtn) {
                convertBtn.disabled = false;
                const icon = document.getElementById('convert-btn-icon');
                if (icon) icon.innerText = '🔄';
            }

            if (!data.success) {
                if (errorBox && errorText) {
                    errorText.innerText = data.error || "Failed to fetch live exchange rate.";
                    errorBox.style.display = 'block';
                }
                return;
            }

            // Populate Display
            if (rateDisplay) {
                rateDisplay.innerText = data.exchange_rate_formatted || `1 ${sourceCurr} = ${Number(data.exchange_rate).toFixed(6)} ${targetCurr}`;
            }

            if (convertedAmountDisplay) {
                convertedAmountDisplay.innerText = data.formatted_converted_amount;
            }

            if (targetCurrCodeDisplay) {
                targetCurrCodeDisplay.innerText = `${data.target_currency} (${data.target_name || 'Settlement Currency'})`;
            }

            if (rateProviderDisplay) {
                rateProviderDisplay.innerText = data.provider || "ExchangeRate-API";
            }

            if (rateTimestampDisplay) {
                rateTimestampDisplay.innerText = `Last Updated: ${data.last_updated || 'Real-time'}`;
            }

            // Populate Hidden Snapshot fields for strict confirmed submission
            if (hiddenRate) hiddenRate.value = data.exchange_rate;
            if (hiddenConverted) hiddenConverted.value = data.converted_amount;
            if (hiddenProvider) hiddenProvider.value = data.provider;
            if (hiddenTimestamp) hiddenTimestamp.value = data.last_updated;

            // Track normalized amount for ML risk preview
            currentNormalizedUsdAmount = data.normalized_usd_amount || amount;
            updateRiskPreview();
        })
        .catch(err => {
            if (loadingIndicator) loadingIndicator.style.display = 'none';
            if (detailsContent) detailsContent.style.opacity = '1.0';
            if (convertBtn) {
                convertBtn.disabled = false;
                const icon = document.getElementById('convert-btn-icon');
                if (icon) icon.innerText = '🔄';
            }
            if (errorBox && errorText) {
                errorText.innerText = "Network error: Could not connect to exchange rate service.";
                errorBox.style.display = 'block';
            }
            console.error("Currency conversion API error:", err);
        });
}

/**
 * Duplicate Submission Prevention Guard
 */
function initFormSubmissionGuard() {
    const form = document.getElementById('payment-form');
    const submitBtn = document.getElementById('btn-submit-payment');
    const submitText = document.getElementById('submit-btn-text');
    const amountInput = document.getElementById('amount');

    if (!form || !submitBtn) return;

    form.addEventListener('submit', function (e) {
        const amount = parseFloat(amountInput ? amountInput.value : 0);
        if (isNaN(amount) || amount <= 0) {
            e.preventDefault();
            alert("Validation Error: Transaction amount must be a positive number greater than 0.");
            return;
        }

        // Prevent duplicate double clicks
        submitBtn.disabled = true;
        submitBtn.style.opacity = '0.75';
        submitBtn.style.cursor = 'not-allowed';
        if (submitText) {
            submitText.innerHTML = '<span class="spinner-pulse" style="margin-right:8px;"></span> Verifying KYC, ML Risk & Executing Smart Contract...';
        }
    });
}

/**
 * 1-Click Test Scenario Fillers for Risk Engine Validation
 */
function fillDemoScenario(scenarioNumber) {
    const senderCountryInput = document.getElementById('sender_country');
    const senderCurrencyInput = document.getElementById('sender_currency');
    const receiverInput = document.getElementById('receiver');
    const receiverCountryInput = document.getElementById('receiver_country');
    const receiverCurrencyInput = document.getElementById('receiver_currency');
    const amountInput = document.getElementById('amount');
    const frequencyInput = document.getElementById('frequency');
    const prevTxInput = document.getElementById('previous_transactions');
    const suspTxInput = document.getElementById('suspicious_transactions');
    const ageInput = document.getElementById('account_age');
    const notesInput = document.getElementById('notes');

    if (!receiverInput) return;

    if (scenarioNumber === 1) {
        // SCENARIO 1: LOW RISK -> Expected: AUTO-APPROVE -> USD to EUR Settlement
        if (senderCountryInput) senderCountryInput.value = "United States";
        if (senderCurrencyInput) senderCurrencyInput.value = "USD";
        receiverInput.value = "EuroTech Industrial Gmbh";
        if (receiverCountryInput) receiverCountryInput.value = "Germany";
        if (receiverCurrencyInput) receiverCurrencyInput.value = "EUR";
        amountInput.value = "4500";
        frequencyInput.value = "2";
        prevTxInput.value = "48";
        suspTxInput.value = "0";
        ageInput.value = "26";
        if (notesInput) notesInput.value = "Routine supply chain invoice settlement - legitimate SME corridor (USD to EUR)";
        highlightFilledForm("var(--color-low)");
    } else if (scenarioNumber === 2) {
        // SCENARIO 2: MEDIUM RISK -> Expected: HOLD FOR REVIEW -> USD to EUR (moderate volume)
        if (senderCountryInput) senderCountryInput.value = "United States";
        if (senderCurrencyInput) senderCurrencyInput.value = "USD";
        receiverInput.value = "Apex Pacific Trade Corp";
        if (receiverCountryInput) receiverCountryInput.value = "Brazil";
        if (receiverCurrencyInput) receiverCurrencyInput.value = "EUR";
        amountInput.value = "28500";
        frequencyInput.value = "7";
        prevTxInput.value = "6";
        suspTxInput.value = "1";
        ageInput.value = "6";
        if (notesInput) notesInput.value = "Unusual seasonal volume transfer - moderate velocity variance (USD to EUR)";
        highlightFilledForm("var(--color-med)");
    } else if (scenarioNumber === 3) {
        // SCENARIO 3: HIGH RISK -> Expected: BLOCK -> USD to INR (extreme volume spike)
        if (senderCountryInput) senderCountryInput.value = "United States";
        if (senderCurrencyInput) senderCurrencyInput.value = "USD";
        receiverInput.value = "Shadow Frontier Express";
        if (receiverCountryInput) receiverCountryInput.value = "Nigeria";
        if (receiverCurrencyInput) receiverCurrencyInput.value = "INR";
        amountInput.value = "145000";
        frequencyInput.value = "19";
        prevTxInput.value = "1";
        suspTxInput.value = "4";
        ageInput.value = "1";
        if (notesInput) notesInput.value = "Rapid velocity spike on newly created account with prior suspicious flags (USD to INR)";
        highlightFilledForm("var(--color-high)");
    }

    // Update symbol prefix
    const symbolEl = document.getElementById('amount-currency-symbol');
    const labelEl = document.getElementById('source-currency-label');
    const curr = senderCurrencyInput ? senderCurrencyInput.value : 'USD';
    const sym = CURRENCY_SYMBOLS[curr] || '$';
    if (symbolEl) symbolEl.innerText = sym;
    if (labelEl) labelEl.innerText = `${curr} ${sym}`;

    // Trigger conversion and live preview
    performCurrencyConversion();
}

function highlightFilledForm(color) {
    const formCard = document.querySelector('.payment-form-card');
    if (formCard) {
        formCard.style.boxShadow = `0 0 24px ${color}`;
        setTimeout(() => {
            formCard.style.boxShadow = '';
        }, 1200);
    }
}

function initScenarioFillers() {
    const btnLow = document.getElementById('btn-scenario-low');
    const btnMed = document.getElementById('btn-scenario-med');
    const btnHigh = document.getElementById('btn-scenario-high');

    if (btnLow) btnLow.addEventListener('click', () => fillDemoScenario(1));
    if (btnMed) btnMed.addEventListener('click', () => fillDemoScenario(2));
    if (btnHigh) btnHigh.addEventListener('click', () => fillDemoScenario(3));
}

/**
 * Client-Side Heuristic Estimator for immediate visual feedback
 */
function initLiveRiskPreview() {
    const inputs = ['amount', 'frequency', 'previous_transactions', 'suspicious_transactions', 'account_age', 'receiver_country'];
    inputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', updateRiskPreview);
            el.addEventListener('change', updateRiskPreview);
        }
    });
    updateRiskPreview();
}

function updateRiskPreview() {
    const amountEl = document.getElementById('amount');
    const suspEl = document.getElementById('suspicious_transactions');
    const freqEl = document.getElementById('frequency');
    const previewBadge = document.getElementById('live-risk-badge');
    const previewDecision = document.getElementById('live-decision-badge');

    if (!amountEl || !previewBadge) return;

    // Use normalized reference USD amount if calculated, else raw amount
    const evalAmount = currentNormalizedUsdAmount || parseFloat(amountEl.value) || 0;
    const susp = parseInt(suspEl ? suspEl.value : 0) || 0;
    const freq = parseInt(freqEl ? freqEl.value : 1) || 1;

    if (evalAmount > 50000 || susp >= 2 || (freq >= 12 && evalAmount > 25000)) {
        previewBadge.className = 'badge badge-high';
        previewBadge.innerHTML = '<span class="dot dot-high"></span> HIGH RISK';
        if (previewDecision) {
            previewDecision.className = 'badge badge-blocked';
            previewDecision.innerText = 'DECISION: BLOCK';
        }
    } else if (evalAmount > 15000 || freq >= 5 || susp === 1) {
        previewBadge.className = 'badge badge-med';
        previewBadge.innerHTML = '<span class="dot dot-med"></span> MEDIUM RISK';
        if (previewDecision) {
            previewDecision.className = 'badge badge-hold';
            previewDecision.innerText = 'DECISION: HOLD';
        }
    } else {
        previewBadge.className = 'badge badge-low';
        previewBadge.innerHTML = '<span class="dot dot-low"></span> LOW RISK';
        if (previewDecision) {
            previewDecision.className = 'badge badge-approved';
            previewDecision.innerText = 'DECISION: APPROVE';
        }
    }
}

/**
 * Blockchain Integrity Verifier
 */
function initBlockchainVerifier() {
    const verifyBtn = document.getElementById('btn-verify-blockchain');
    const statusBox = document.getElementById('blockchain-verify-result');

    if (!verifyBtn || !statusBox) return;

    verifyBtn.addEventListener('click', function () {
        verifyBtn.disabled = true;
        verifyBtn.innerText = "Auditing Cryptographic Hashes...";

        fetch('/api/validate_chain')
            .then(res => res.json())
            .then(data => {
                verifyBtn.disabled = false;
                verifyBtn.innerText = "Verify Blockchain Integrity";

                if (data.valid) {
                    statusBox.innerHTML = `
                        <div class="alert alert-success" style="margin-top:16px;">
                            <strong>✅ Cryptographic Proof Verified:</strong> All ${data.total_blocks} blocks are linked with authentic SHA-256 parent hashes and Proof-of-Work nonces. Chain is tamper-free!
                        </div>
                    `;
                } else {
                    statusBox.innerHTML = `
                        <div class="alert alert-danger" style="margin-top:16px;">
                            <strong>❌ Integrity Alert:</strong> ${data.message}
                        </div>
                    `;
                }
            })
            .catch(err => {
                verifyBtn.disabled = false;
                verifyBtn.innerText = "Verify Blockchain Integrity";
                console.error(err);
            });
    });
}

