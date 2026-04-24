// quiz.js - Quiz engine
const Quiz = {
  questions: [],
  categories: [],

  async loadQuestions() {
    const res = await fetch('data/questions.json');
    this.questions = await res.json();
    this.categories = [...new Set(this.questions.map(q => q.category))];
    return this.questions;
  },

  getCategories() {
    return this.categories;
  },

  generateQuiz(count, categories, mode) {
    let pool = this.questions;

    // Filter by categories
    if (categories && categories.length > 0 && categories.length < this.categories.length) {
      pool = pool.filter(q => categories.includes(q.category));
    }

    if (mode === 'weak') {
      const weakIds = Storage.getWeakQuestionIds();
      const weakPool = pool.filter(q => weakIds.includes(String(q.id)));
      if (weakPool.length > 0) {
        pool = weakPool;
      }
    }

    if (mode === 'sequential') {
      return pool.slice(0, count).map(q => q.id);
    }

    // Random shuffle and pick
    const shuffled = [...pool].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, Math.min(count, shuffled.length)).map(q => q.id);
  },

  getQuestionById(id) {
    return this.questions.find(q => q.id === id);
  },

  checkAnswer(questionId, selectedChoices) {
    const q = this.getQuestionById(questionId);
    if (!q) return false;

    const correct = [...q.answer].sort();
    const selected = [...selectedChoices].sort();

    if (correct.length !== selected.length) return false;
    return correct.every((v, i) => v === selected[i]);
  },
};
