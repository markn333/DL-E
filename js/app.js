// app.js - Main application logic
const App = {
  state: {
    questionIds: [],
    currentIndex: 0,
    answers: {},  // { questionId: { selected: ['A'], correct: bool } }
    mode: 'random',
    startedAt: null,
    selectedChoices: [],
    answered: false,
  },

  async init() {
    await Quiz.loadQuestions();
    this.buildCategoryList();
    this.checkResume();
    this.bindEvents();
    this.registerSW();
  },

  // --- Navigation ---
  showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    window.scrollTo(0, 0);
  },

  // --- Home ---
  buildCategoryList() {
    const list = document.getElementById('category-list');
    list.innerHTML = '';
    for (const cat of Quiz.getCategories()) {
      const label = document.createElement('label');
      label.className = 'checkbox-label';
      label.innerHTML = `<input type="checkbox" class="cat-checkbox" value="${cat}" checked> ${cat}`;
      list.appendChild(label);
    }
  },

  checkResume() {
    const progress = Storage.loadProgress();
    const section = document.getElementById('resume-section');
    if (progress && progress.questionIds.length > 0) {
      const answered = Object.keys(progress.answers || {}).length;
      document.getElementById('resume-info').textContent =
        `${progress.questionIds.length}問中 ${answered}問回答済み`;
      section.classList.remove('hidden');
    } else {
      section.classList.add('hidden');
    }
  },

  getSelectedCategories() {
    const allChecked = document.getElementById('cat-all').checked;
    if (allChecked) return Quiz.getCategories();

    const checked = document.querySelectorAll('.cat-checkbox:checked');
    return Array.from(checked).map(cb => cb.value);
  },

  // --- Quiz ---
  startQuiz(questionIds, mode) {
    this.state = {
      questionIds,
      currentIndex: 0,
      answers: {},
      mode,
      startedAt: new Date().toISOString(),
      selectedChoices: [],
      answered: false,
    };
    this.showScreen('screen-quiz');
    this.renderQuestion();
  },

  resumeQuiz(progress) {
    this.state = {
      questionIds: progress.questionIds,
      currentIndex: progress.currentIndex,
      answers: progress.answers || {},
      mode: progress.mode,
      startedAt: progress.startedAt,
      selectedChoices: [],
      answered: false,
    };
    Storage.clearProgress();
    this.showScreen('screen-quiz');
    this.renderQuestion();
  },

  pauseQuiz() {
    Storage.saveProgress(this.state);
    this.showScreen('screen-home');
    this.checkResume();
  },

  renderQuestion() {
    const { questionIds, currentIndex } = this.state;
    const qId = questionIds[currentIndex];
    const q = Quiz.getQuestionById(qId);
    if (!q) return;

    this.state.selectedChoices = [];
    this.state.answered = false;

    // Progress
    document.getElementById('quiz-current').textContent = currentIndex + 1;
    document.getElementById('quiz-total').textContent = questionIds.length;
    const pct = ((currentIndex) / questionIds.length * 100);
    document.getElementById('quiz-progress-fill').style.width = pct + '%';

    // Question
    document.getElementById('question-category').textContent = q.category;
    const multiTag = document.getElementById('question-multi');
    if (q.multiAnswer) {
      multiTag.classList.remove('hidden');
      multiTag.textContent = `${q.answer.length}つ選択`;
    } else {
      multiTag.classList.add('hidden');
    }
    document.getElementById('question-text').textContent = q.question;

    // Choices
    const list = document.getElementById('choices-list');
    list.innerHTML = '';
    for (const choice of q.choices) {
      const letter = choice.charAt(0);
      const text = choice.substring(3); // Skip "A. "
      const btn = document.createElement('button');
      btn.className = 'choice-btn';
      btn.dataset.letter = letter;
      btn.innerHTML = `<span class="choice-label">${letter}</span><span class="choice-text">${this.escapeHtml(text)}</span>`;
      btn.addEventListener('click', () => this.toggleChoice(letter, btn));
      list.appendChild(btn);
    }

    // Show/hide buttons
    document.getElementById('btn-answer').classList.remove('hidden');
    document.getElementById('btn-next').classList.add('hidden');
    document.getElementById('answer-section').classList.add('hidden');

    // Scroll to top of quiz body
    document.querySelector('.quiz-body').scrollTop = 0;
  },

  toggleChoice(letter, btn) {
    if (this.state.answered) return;

    const q = Quiz.getQuestionById(this.state.questionIds[this.state.currentIndex]);
    const maxSelect = q.multiAnswer ? q.answer.length : 1;

    const idx = this.state.selectedChoices.indexOf(letter);
    if (idx >= 0) {
      this.state.selectedChoices.splice(idx, 1);
      btn.classList.remove('selected');
    } else {
      if (!q.multiAnswer) {
        // Single select: deselect others
        document.querySelectorAll('.choice-btn').forEach(b => b.classList.remove('selected'));
        this.state.selectedChoices = [];
      } else if (this.state.selectedChoices.length >= maxSelect) {
        return; // Max reached
      }
      this.state.selectedChoices.push(letter);
      btn.classList.add('selected');
    }
  },

  submitAnswer() {
    if (this.state.selectedChoices.length === 0) return;

    const qId = this.state.questionIds[this.state.currentIndex];
    const q = Quiz.getQuestionById(qId);
    const isCorrect = Quiz.checkAnswer(qId, this.state.selectedChoices);

    this.state.answered = true;
    this.state.answers[qId] = {
      selected: [...this.state.selectedChoices],
      correct: isCorrect,
    };

    Storage.recordAnswer(qId, isCorrect);

    // Highlight choices
    document.querySelectorAll('.choice-btn').forEach(btn => {
      const letter = btn.dataset.letter;
      const isAnswer = q.answer.includes(letter);
      const wasSelected = this.state.selectedChoices.includes(letter);

      if (isAnswer && wasSelected) {
        btn.classList.add('correct');
      } else if (!isAnswer && wasSelected) {
        btn.classList.add('incorrect');
      } else if (isAnswer && !wasSelected) {
        btn.classList.add('missed');
      }
      btn.style.pointerEvents = 'none';
    });

    // Show result & explanation
    const resultEl = document.getElementById('answer-result');
    resultEl.textContent = isCorrect ? '正解!' : `不正解 (正答: ${q.answer.join(', ')})`;
    resultEl.className = 'answer-result ' + (isCorrect ? 'correct' : 'incorrect');

    document.getElementById('answer-explanation').textContent = q.explanation;
    document.getElementById('answer-section').classList.remove('hidden');

    document.getElementById('btn-answer').classList.add('hidden');

    const isLast = this.state.currentIndex >= this.state.questionIds.length - 1;
    const nextBtn = document.getElementById('btn-next');
    nextBtn.textContent = isLast ? '結果を見る' : '次の問題';
    nextBtn.classList.remove('hidden');

    // Auto-save progress
    Storage.saveProgress(this.state);
  },

  nextQuestion() {
    this.state.currentIndex++;
    if (this.state.currentIndex >= this.state.questionIds.length) {
      this.finishQuiz();
    } else {
      this.renderQuestion();
      Storage.saveProgress(this.state);
    }
  },

  finishQuiz() {
    Storage.clearProgress();

    const { answers, questionIds } = this.state;
    const total = questionIds.length;
    const correctCount = Object.values(answers).filter(a => a.correct).length;
    const percent = Math.round(correctCount / total * 100);

    // Category breakdown
    const catBreakdown = {};
    for (const qId of questionIds) {
      const q = Quiz.getQuestionById(qId);
      if (!catBreakdown[q.category]) {
        catBreakdown[q.category] = { total: 0, correct: 0 };
      }
      catBreakdown[q.category].total++;
      if (answers[qId] && answers[qId].correct) catBreakdown[q.category].correct++;
    }

    // Save history
    Storage.addHistory({
      totalQuestions: total,
      correctCount,
      percent,
      categoryBreakdown: catBreakdown,
      mode: this.state.mode,
    });

    // Render result
    this.renderResult(total, correctCount, percent, catBreakdown, answers, questionIds);
    this.showScreen('screen-result');
  },

  renderResult(total, correctCount, percent, catBreakdown, answers, questionIds) {
    // Score circle
    const ring = document.getElementById('score-ring');
    const offset = 339.292 * (1 - percent / 100);
    setTimeout(() => {
      ring.style.strokeDashoffset = offset;
      ring.style.stroke = percent >= 70 ? '#16a34a' : percent >= 50 ? '#f59e0b' : '#dc2626';
    }, 100);
    document.getElementById('score-percent').textContent = percent;
    document.getElementById('score-detail').textContent = `${total}問中 ${correctCount}問正解`;

    // Category bars
    const catContainer = document.getElementById('category-results');
    catContainer.innerHTML = '';
    for (const [cat, s] of Object.entries(catBreakdown)) {
      const catPct = Math.round(s.correct / s.total * 100);
      const color = catPct >= 70 ? '#16a34a' : catPct >= 50 ? '#f59e0b' : '#dc2626';
      catContainer.innerHTML += `
        <div class="cat-result-item">
          <div class="cat-result-label">
            <span>${cat}</span>
            <span>${catPct}% (${s.correct}/${s.total})</span>
          </div>
          <div class="cat-result-bar">
            <div class="cat-result-fill" style="width:${catPct}%;background:${color}"></div>
          </div>
        </div>`;
    }

    // Wrong questions
    const wrongList = document.getElementById('wrong-questions-list');
    const wrongSection = document.getElementById('wrong-questions-section');
    const wrongIds = questionIds.filter(qId => answers[qId] && !answers[qId].correct);

    if (wrongIds.length === 0) {
      wrongSection.classList.add('hidden');
    } else {
      wrongSection.classList.remove('hidden');
      wrongList.innerHTML = '';
      for (const qId of wrongIds) {
        const q = Quiz.getQuestionById(qId);
        wrongList.innerHTML += `
          <div class="wrong-item">
            <div class="wrong-item-header">
              <span class="wrong-item-category">${q.category}</span>
              <span>正答: ${q.answer.join(', ')}</span>
            </div>
            <div class="wrong-item-q">${this.escapeHtml(q.question)}</div>
          </div>`;
      }
    }

    // Retry wrong button
    const retryBtn = document.getElementById('btn-retry-wrong');
    if (wrongIds.length > 0) {
      retryBtn.classList.remove('hidden');
      retryBtn.onclick = () => {
        this.startQuiz(wrongIds, 'weak');
      };
    } else {
      retryBtn.classList.add('hidden');
    }

    // Reset score ring for next time
    ring.style.strokeDashoffset = 339.292;
  },

  // --- History ---
  showHistory() {
    this.showScreen('screen-history');
    ChartHelper.renderHistoryChart('history-chart');
    this.renderStats();
    this.renderHistoryList();
  },

  renderStats() {
    const history = Storage.getHistory();
    const stats = Storage.getWrongStats();
    const totalAttempts = history.length;
    const totalQuestions = history.reduce((s, h) => s + h.totalQuestions, 0);
    const avgScore = totalAttempts > 0
      ? Math.round(history.reduce((s, h) => s + h.percent, 0) / totalAttempts)
      : 0;
    const uniqueQuestions = Object.keys(stats).length;

    document.getElementById('stats-summary').innerHTML = `
      <div class="stat-item"><div class="stat-value">${totalAttempts}</div><div class="stat-label">受験回数</div></div>
      <div class="stat-item"><div class="stat-value">${totalQuestions}</div><div class="stat-label">解答数</div></div>
      <div class="stat-item"><div class="stat-value">${avgScore}%</div><div class="stat-label">平均正解率</div></div>
      <div class="stat-item"><div class="stat-value">${uniqueQuestions}</div><div class="stat-label">挑戦済み問題</div></div>
    `;
  },

  renderHistoryList() {
    const history = Storage.getHistory().slice().reverse();
    const container = document.getElementById('history-list');

    if (history.length === 0) {
      container.innerHTML = '<p style="color:#6b7280;text-align:center">まだ履歴がありません</p>';
      return;
    }

    container.innerHTML = history.slice(0, 20).map(h => {
      const d = new Date(h.date);
      const dateStr = `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
      const color = h.percent >= 70 ? '#16a34a' : h.percent >= 50 ? '#f59e0b' : '#dc2626';
      return `<div class="history-item">
        <div><div class="history-date">${dateStr}</div><div>${h.totalQuestions}問</div></div>
        <div class="history-score" style="color:${color}">${h.percent}%</div>
      </div>`;
    }).join('');
  },

  // --- Weakness ---
  showWeakness() {
    this.showScreen('screen-weakness');

    // Set canvas height based on categories
    const canvas = document.getElementById('weakness-chart');
    const catCount = Quiz.getCategories().length;
    canvas.parentElement.style.height = Math.max(200, catCount * 40 + 40) + 'px';

    ChartHelper.renderWeaknessChart('weakness-chart');
    this.renderWeakQuestions();
  },

  renderWeakQuestions() {
    const stats = Storage.getWrongStats();
    const container = document.getElementById('weak-questions-list');

    const items = Object.entries(stats)
      .filter(([, s]) => s.wrong > 0)
      .map(([id, s]) => ({
        id,
        question: Quiz.getQuestionById(id),
        wrongRate: Math.round(s.wrong / s.attempts * 100),
        wrong: s.wrong,
        attempts: s.attempts,
      }))
      .filter(item => item.question)
      .sort((a, b) => b.wrongRate - a.wrongRate)
      .slice(0, 10);

    if (items.length === 0) {
      container.innerHTML = '<p style="color:#6b7280;text-align:center">まだデータがありません</p>';
      return;
    }

    container.innerHTML = items.map(item => `
      <div class="weak-item">
        <div class="weak-item-q">${this.escapeHtml(item.question.question)}</div>
        <div class="weak-item-rate">${item.wrongRate}%<br><small>${item.wrong}/${item.attempts}</small></div>
      </div>
    `).join('');
  },

  // --- Events ---
  bindEvents() {
    // Question count
    document.querySelectorAll('.btn-count').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-count').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });

    // Mode
    document.querySelectorAll('.btn-mode').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-mode').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      });
    });

    // Category "all" toggle
    document.getElementById('cat-all').addEventListener('change', (e) => {
      document.querySelectorAll('.cat-checkbox').forEach(cb => {
        cb.checked = e.target.checked;
      });
    });

    document.getElementById('category-list').addEventListener('change', () => {
      const all = document.querySelectorAll('.cat-checkbox');
      const checked = document.querySelectorAll('.cat-checkbox:checked');
      document.getElementById('cat-all').checked = all.length === checked.length;
    });

    // Start
    document.getElementById('btn-start').addEventListener('click', () => {
      const count = parseInt(document.querySelector('.btn-count.active').dataset.count);
      const mode = document.querySelector('.btn-mode.active').dataset.mode;
      const categories = this.getSelectedCategories();

      if (categories.length === 0) {
        alert('出題範囲を1つ以上選択してください');
        return;
      }

      const ids = Quiz.generateQuiz(count, categories, mode);
      if (ids.length === 0) {
        alert('条件に合う問題がありません');
        return;
      }
      this.startQuiz(ids, mode);
    });

    // Resume / Discard
    document.getElementById('btn-resume').addEventListener('click', () => {
      const progress = Storage.loadProgress();
      if (progress) this.resumeQuiz(progress);
    });

    document.getElementById('btn-discard').addEventListener('click', () => {
      Storage.clearProgress();
      this.checkResume();
    });

    // Quiz controls
    document.getElementById('btn-pause').addEventListener('click', () => this.pauseQuiz());
    document.getElementById('btn-answer').addEventListener('click', () => this.submitAnswer());
    document.getElementById('btn-next').addEventListener('click', () => this.nextQuestion());

    // Result
    document.getElementById('btn-back-home').addEventListener('click', () => {
      this.showScreen('screen-home');
      this.checkResume();
    });

    // History / Weakness
    document.getElementById('btn-go-history').addEventListener('click', () => this.showHistory());
    document.getElementById('btn-go-weakness').addEventListener('click', () => this.showWeakness());
    document.getElementById('btn-history-back').addEventListener('click', () => this.showScreen('screen-home'));
    document.getElementById('btn-weakness-back').addEventListener('click', () => this.showScreen('screen-home'));
  },

  // --- Service Worker ---
  registerSW() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('sw.js').catch(() => {});
    }
  },

  // --- Utility ---
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  },
};

// Boot
document.addEventListener('DOMContentLoaded', () => App.init());
