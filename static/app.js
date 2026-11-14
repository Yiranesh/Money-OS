/**
 * MONEY OS — Frontend Interactions & API Integrations
 * static/app.js
 */
(function () {
  'use strict';

  // DOM Elements
  const incomeInput = document.getElementById('monthlyIncome');
  const liveInputStatus = document.getElementById('liveInputStatus');
  const receiptPaper = document.getElementById('thermalReceipt');

  const receiptIncomeTotal = document.getElementById('receiptIncomeTotal');
  const receiptNeedsVal = document.getElementById('receiptNeedsVal');
  const receiptWantsVal = document.getElementById('receiptWantsVal');
  const receiptSavingsVal = document.getElementById('receiptSavingsVal');
  const receiptLeftVal = document.getElementById('receiptLeftVal');
  const dailySpendSub = document.getElementById('dailySpendSub');

  const pieNeeds = document.getElementById('pieNeeds');
  const pieWants = document.getElementById('pieWants');
  const pieSavings = document.getElementById('pieSavings');

  const presetButtons = document.querySelectorAll('.preset-btn');
  const heroStatsLine = document.getElementById('heroStatsLine');

  // Dialog Elements
  const questionDialog = document.getElementById('questionDialog');
  const dialogCloseBtn = document.getElementById('dialogCloseBtn');
  const heroSecondaryCta = document.getElementById('heroSecondaryCta');
  const ctaSecondaryBtn = document.getElementById('ctaSecondaryBtn');
  const footerFaqTrigger = document.getElementById('footerFaqTrigger');

  const questionForm = document.getElementById('questionForm');
  const questionSubmitBtn = document.getElementById('questionSubmitBtn');
  const questionFeedback = document.getElementById('questionFeedback');

  // Waitlist Elements
  const waitlistForm = document.getElementById('waitlistForm');
  const waitlistEmail = document.getElementById('waitlistEmail');
  const waitlistSubmitBtn = document.getElementById('waitlistSubmitBtn');
  const waitlistFeedback = document.getElementById('waitlistFeedback');

  // CTA Links
  const heroPrimaryCta = document.getElementById('heroPrimaryCta');
  const ctaPrimaryBtn = document.getElementById('ctaPrimaryBtn');
  const headerTryBtn = document.getElementById('headerTryBtn');

  // Circumference of SVG circle with r=40: 2 * PI * 40 ≈ 251.327
  const CIRCUMFERENCE = 2 * Math.PI * 40;

  // Format Malaysian Ringgit
  function formatRM(num) {
    const val = isNaN(num) || num < 0 ? 0 : num;
    return 'RM ' + val.toLocaleString('en-MY', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  }

  // Trigger Receipt Feed-Print Animation
  function triggerPrintAnimation() {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }
    if (!receiptPaper) return;
    const lines = receiptPaper.querySelectorAll('.print-line');
    lines.forEach(line => {
      line.style.animation = 'none';
      void line.offsetWidth; // trigger reflow
      line.style.animation = '';
    });
  }

  // Local calculation fallback
  function calculateLocalSplit(income) {
    const needs = Math.round(income * 0.50 * 100) / 100;
    const wants = Math.round(income * 0.30 * 100) / 100;
    const savings = Math.round(income * 0.20 * 100) / 100;
    return { income, needs, wants, savings };
  }

  // Update UI with calculated split data
  function renderReceipt(split) {
    const income = split.income || 0;
    const needs = split.needs || 0;
    const wants = split.wants || 0;
    const savings = split.savings || 0;
    const dailySafe = wants / 30;

    receiptIncomeTotal.textContent = formatRM(income);
    receiptNeedsVal.textContent = formatRM(needs);
    receiptWantsVal.textContent = formatRM(wants);
    receiptSavingsVal.textContent = formatRM(savings);
    receiptLeftVal.textContent = formatRM(wants);
    dailySpendSub.textContent = '≈ ' + formatRM(dailySafe) + ' / DAY SAFE BALANCE';

    liveInputStatus.textContent = income === 1200 ? 'Default: RM 1,200' : 'Current: ' + formatRM(income);

    // Update SVG Pie Chart
    const lenNeeds = CIRCUMFERENCE * 0.50;
    const lenWants = CIRCUMFERENCE * 0.30;
    const lenSavings = CIRCUMFERENCE * 0.20;

    if (income === 0) {
      pieNeeds.setAttribute('stroke-dasharray', `0 ${CIRCUMFERENCE}`);
      pieWants.setAttribute('stroke-dasharray', `0 ${CIRCUMFERENCE}`);
      pieSavings.setAttribute('stroke-dasharray', `0 ${CIRCUMFERENCE}`);
    } else {
      pieNeeds.setAttribute('stroke-dasharray', `${lenNeeds.toFixed(2)} ${(CIRCUMFERENCE - lenNeeds).toFixed(2)}`);
      pieNeeds.setAttribute('stroke-dashoffset', '0');

      pieWants.setAttribute('stroke-dasharray', `${lenWants.toFixed(2)} ${(CIRCUMFERENCE - lenWants).toFixed(2)}`);
      pieWants.setAttribute('stroke-dashoffset', `-${lenNeeds.toFixed(2)}`);

      const offsetSavings = lenNeeds + lenWants;
      pieSavings.setAttribute('stroke-dasharray', `${lenSavings.toFixed(2)} ${(CIRCUMFERENCE - lenSavings).toFixed(2)}`);
      pieSavings.setAttribute('stroke-dashoffset', `-${offsetSavings.toFixed(2)}`);
    }

    // Active preset chip highlight
    presetButtons.forEach(btn => {
      if (parseFloat(btn.getAttribute('data-val')) === income) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Re-feed receipt
    triggerPrintAnimation();
  }

  // Debounced API Budget Call
  let budgetDebounceTimer = null;
  function syncBudgetWithBackend(income) {
    // 1. Immediately render local calculation for zero latency
    const local = calculateLocalSplit(income);
    renderReceipt(local);

    // 2. Debounce backend persistence call (300ms)
    clearTimeout(budgetDebounceTimer);
    budgetDebounceTimer = setTimeout(async () => {
      if (income < 0 || income > 1000000) return;
      try {
        const res = await fetch('/api/budget', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ income: income })
        });
        if (res.ok) {
          const data = await res.json();
          // Update stats line if present
          fetchStats();
        }
      } catch (err) {
        // Graceful fallback: local calculation already active
        console.warn('Backend sync failed, using local calculation:', err);
      }
    }, 300);
  }

  // Fetch /api/stats
  async function fetchStats() {
    try {
      const res = await fetch('/api/stats');
      if (res.ok) {
        const stats = await res.json();
        if (stats.budgets_created && stats.budgets_created > 0 && heroStatsLine) {
          heroStatsLine.style.display = 'inline-flex';
          heroStatsLine.textContent = `★ ${stats.budgets_created.toLocaleString()} budgets printed so far`;
        } else if (heroStatsLine) {
          heroStatsLine.style.display = 'none';
        }
      }
    } catch (err) {
      if (heroStatsLine) heroStatsLine.style.display = 'none';
    }
  }

  // Input Listeners
  if (incomeInput) {
    incomeInput.addEventListener('input', function (e) {
      const val = parseFloat(e.target.value) || 0;
      syncBudgetWithBackend(val);
    });
  }

  // Preset Chips
  presetButtons.forEach(btn => {
    btn.addEventListener('click', function () {
      const val = parseFloat(this.getAttribute('data-val')) || 0;
      if (incomeInput) incomeInput.value = val;
      syncBudgetWithBackend(val);
    });
  });

  window.setPreset = function (val) {
    if (incomeInput) incomeInput.value = val;
    syncBudgetWithBackend(val);
    const sec = document.getElementById('receiptSection');
    if (sec) sec.scrollIntoView({ behavior: 'smooth' });
  };

  // Primary Action Scroll & Focus
  function focusAllowanceInput(e) {
    if (e) e.preventDefault();
    const section = document.getElementById('receiptSection');
    if (section) {
      section.scrollIntoView({ behavior: 'smooth' });
      setTimeout(() => {
        if (incomeInput) {
          incomeInput.focus();
          incomeInput.select();
        }
      }, 350);
    }
  }

  if (heroPrimaryCta) heroPrimaryCta.addEventListener('click', focusAllowanceInput);
  if (ctaPrimaryBtn) ctaPrimaryBtn.addEventListener('click', focusAllowanceInput);
  if (headerTryBtn) headerTryBtn.addEventListener('click', focusAllowanceInput);

  // Dialog Modal for "Ask a question"
  function openQuestionDialog(e) {
    if (e) e.preventDefault();
    if (questionDialog) {
      if (typeof questionDialog.showModal === 'function') {
        questionDialog.showModal();
      } else {
        questionDialog.setAttribute('open', 'true');
      }
      const firstInput = questionDialog.querySelector('input');
      if (firstInput) firstInput.focus();
    }
  }

  function closeQuestionDialog() {
    if (questionDialog) {
      if (typeof questionDialog.close === 'function') {
        questionDialog.close();
      } else {
        questionDialog.removeAttribute('open');
      }
    }
  }

  if (heroSecondaryCta) heroSecondaryCta.addEventListener('click', openQuestionDialog);
  if (ctaSecondaryBtn) ctaSecondaryBtn.addEventListener('click', openQuestionDialog);
  if (footerFaqTrigger) footerFaqTrigger.addEventListener('click', openQuestionDialog);
  if (dialogCloseBtn) dialogCloseBtn.addEventListener('click', closeQuestionDialog);

  // Close dialog on outside backdrop click
  if (questionDialog) {
    questionDialog.addEventListener('click', function (e) {
      const rect = questionDialog.getBoundingClientRect();
      const isInDialog = (
        rect.top <= e.clientY && e.clientY <= rect.top + rect.height &&
        rect.left <= e.clientX && e.clientX <= rect.left + rect.width
      );
      if (!isInDialog) {
        closeQuestionDialog();
      }
    });
  }

  // Handle Question Form Submission
  if (questionForm) {
    questionForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      const name = document.getElementById('questionName').value.trim();
      const email = document.getElementById('questionEmail').value.trim();
      const message = document.getElementById('questionMessage').value.trim();

      questionFeedback.className = 'form-feedback';
      questionFeedback.style.display = 'none';

      // Client-side quick check
      if (!name || !email || !message) {
        questionFeedback.className = 'form-feedback error';
        questionFeedback.textContent = 'Please fill out all fields.';
        return;
      }
      if (message.length < 10) {
        questionFeedback.className = 'form-feedback error';
        questionFeedback.textContent = 'Please write a message with at least 10 characters so we can help.';
        return;
      }

      // Loading state
      questionSubmitBtn.disabled = true;
      const originalText = questionSubmitBtn.textContent;
      questionSubmitBtn.textContent = 'Sending question...';

      try {
        const res = await fetch('/api/questions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, message })
        });
        const data = await res.json();

        if (res.ok) {
          questionFeedback.className = 'form-feedback success';
          questionFeedback.textContent = data.message || 'Thank you! Your question has been received.';
          questionForm.reset();
          setTimeout(() => {
            closeQuestionDialog();
            questionFeedback.style.display = 'none';
          }, 2500);
        } else {
          questionFeedback.className = 'form-feedback error';
          questionFeedback.textContent = data.error || 'Unable to submit question. Please check your details and try again.';
        }
      } catch (err) {
        questionFeedback.className = 'form-feedback error';
        questionFeedback.textContent = 'Connection error. Please check your internet connection and try again.';
      } finally {
        questionSubmitBtn.disabled = false;
        questionSubmitBtn.textContent = originalText;
      }
    });
  }

  // Handle Waitlist Form Submission
  if (waitlistForm) {
    waitlistForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      const email = waitlistEmail.value.trim();

      waitlistFeedback.className = 'form-feedback';
      waitlistFeedback.style.display = 'none';

      if (!email || !email.includes('@')) {
        waitlistFeedback.className = 'form-feedback error';
        waitlistFeedback.textContent = 'Please provide a valid email address (e.g. name@student.edu.my).';
        return;
      }

      waitlistSubmitBtn.disabled = true;
      const origText = waitlistSubmitBtn.textContent;
      waitlistSubmitBtn.textContent = 'Joining...';

      try {
        const res = await fetch('/api/waitlist', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email })
        });
        const data = await res.json();

        if (res.ok) {
          waitlistFeedback.className = 'form-feedback success';
          waitlistFeedback.textContent = data.message || "You're in! Welcome to the Money OS waitlist.";
          waitlistForm.reset();
          fetchStats();
        } else if (res.status === 409) {
          waitlistFeedback.className = 'form-feedback error';
          waitlistFeedback.textContent = data.error || "You are already on the waitlist! We'll be in touch soon.";
        } else if (res.status === 429) {
          waitlistFeedback.className = 'form-feedback error';
          waitlistFeedback.textContent = 'Too many requests. Please wait a moment before trying again.';
        } else {
          waitlistFeedback.className = 'form-feedback error';
          waitlistFeedback.textContent = data.error || 'Something went wrong. Please check your email and try again.';
        }
      } catch (err) {
        waitlistFeedback.className = 'form-feedback error';
        waitlistFeedback.textContent = 'Connection error. Please try again in a few moments.';
      } finally {
        waitlistSubmitBtn.disabled = false;
        waitlistSubmitBtn.textContent = origText;
      }
    });
  }

  // Initialize
  syncBudgetWithBackend(1200);
  fetchStats();

})();
