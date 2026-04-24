// storage.js - LocalStorage persistence layer
const Storage = {
  KEYS: {
    HISTORY: 'dle_history',
    PROGRESS: 'dle_progress',
    WRONG_STATS: 'dle_wrong_stats',
  },

  get(key) {
    try {
      const val = localStorage.getItem(key);
      return val ? JSON.parse(val) : null;
    } catch {
      return null;
    }
  },

  set(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  },

  remove(key) {
    localStorage.removeItem(key);
  },

  // --- Progress (in-progress quiz) ---
  saveProgress(state) {
    this.set(this.KEYS.PROGRESS, {
      questionIds: state.questionIds,
      currentIndex: state.currentIndex,
      answers: state.answers,
      mode: state.mode,
      startedAt: state.startedAt,
    });
  },

  loadProgress() {
    return this.get(this.KEYS.PROGRESS);
  },

  clearProgress() {
    this.remove(this.KEYS.PROGRESS);
  },

  // --- History ---
  getHistory() {
    return this.get(this.KEYS.HISTORY) || [];
  },

  addHistory(entry) {
    const history = this.getHistory();
    history.push({
      date: new Date().toISOString(),
      totalQuestions: entry.totalQuestions,
      correctCount: entry.correctCount,
      percent: entry.percent,
      categoryBreakdown: entry.categoryBreakdown,
      mode: entry.mode,
    });
    // Keep last 100 entries
    if (history.length > 100) history.splice(0, history.length - 100);
    this.set(this.KEYS.HISTORY, history);
  },

  // --- Wrong answer stats (per question) ---
  getWrongStats() {
    return this.get(this.KEYS.WRONG_STATS) || {};
  },

  recordAnswer(questionId, isCorrect) {
    const stats = this.getWrongStats();
    if (!stats[questionId]) {
      stats[questionId] = { attempts: 0, wrong: 0 };
    }
    stats[questionId].attempts++;
    if (!isCorrect) stats[questionId].wrong++;
    this.set(this.KEYS.WRONG_STATS, stats);
  },

  getWeakQuestionIds(minAttempts = 1) {
    const stats = this.getWrongStats();
    return Object.entries(stats)
      .filter(([, s]) => s.attempts >= minAttempts && s.wrong > 0)
      .sort((a, b) => (b[1].wrong / b[1].attempts) - (a[1].wrong / a[1].attempts))
      .map(([id]) => id);
  },
};
