const db = require('./db');
const axios = require('axios');

class Scheduler {
    static checkQuotaReset() {
        const today = new Date().toISOString().split('T')[0];
        db.prepare("UPDATE providers SET current_requests_today = 0, last_reset_date = ? WHERE last_reset_date != ? OR last_reset_date IS NULL").run(today, today);
    }

    static async fetchModels(providerId) {
        const provider = db.prepare('SELECT * FROM providers WHERE id = ?').get(providerId);
        if (!provider) throw new Error('Provider not found');

        const url = `${provider.base_url.replace(/\/$/, '')}/models`;
        try {
            const response = await axios.get(url, {
                headers: { 'Authorization': `Bearer ${provider.api_key}` }
            });
            const models = response.data.data.map(m => m.id);
            db.prepare('UPDATE providers SET models = ? WHERE id = ?').run(JSON.stringify(models), providerId);
            return models;
        } catch (err) {
            console.error(`Failed to fetch models for provider ${provider.name}:`, err.message);
            throw err;
        }
    }

    static getBestProvider(modelAlias) {
        this.checkQuotaReset();
        // 1. Check for model group mapping
        let group = db.prepare('SELECT * FROM model_groups WHERE alias = ?').get(modelAlias);
        let targetModels = group ? JSON.parse(group.target_models) : [modelAlias];

        // 2. Get all active providers
        const providers = db.prepare('SELECT * FROM providers WHERE is_active = 1').all();

        // 3. Filter available providers based on models and quota
        const available = providers.filter(p => {
            const supportedModels = JSON.parse(p.models || '[]');
            const hasModel = targetModels.some(m => supportedModels.includes(m));
            const withinQuota = p.current_requests_today < p.max_requests_per_day;
            return hasModel && withinQuota;
        });

        if (available.length === 0) return null;

        // 4. Selection strategy (Defaults to Weighted Random, can be switched to Round Robin)
        // For demonstration, let's use weighted random but keep hooks for others
        return this.weightedRandom(available);
    }

    static lastIndices = {}; // To track round robin per model

    static roundRobin(model, providers) {
        if (!this.lastIndices[model]) this.lastIndices[model] = 0;
        const index = this.lastIndices[model] % providers.length;
        this.lastIndices[model] = index + 1;
        return providers[index];
    }

    static weightedRandom(providers) {
        const totalWeight = providers.reduce((sum, p) => sum + p.weight, 0);
        let r = Math.random() * totalWeight;
        let cumulativeWeight = 0;

        for (const provider of providers) {
            cumulativeWeight += provider.weight;
            if (r <= cumulativeWeight) return provider;
        }
        return providers[0];
    }

    static incrementUsage(providerId, model, usage) {
        db.prepare('UPDATE providers SET current_requests_today = current_requests_today + 1 WHERE id = ?').run(providerId);

        if (usage) {
            db.prepare(`
                INSERT INTO usage_logs (provider_id, model, prompt_tokens, completion_tokens, total_tokens)
                VALUES (?, ?, ?, ?, ?)
            `).run(
                providerId,
                model,
                usage.prompt_tokens || 0,
                usage.completion_tokens || 0,
                usage.total_tokens || 0
            );
        }
    }
}

module.exports = Scheduler;
