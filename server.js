const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');
const cors = require('cors');
const path = require('path');
const db = require('./db');
const Scheduler = require('./scheduler');

const app = express();
const PORT = 3000;

app.use(cors());
app.use(bodyParser.json());
app.use(express.static('public'));

// --- Admin API ---
app.post('/admin/providers', (req, res) => {
    const { name, base_url, api_key, models, weight, max_requests_per_day } = req.body;
    try {
        db.prepare(`
            INSERT INTO providers (name, base_url, api_key, models, weight, max_requests_per_day)
            VALUES (?, ?, ?, ?, ?, ?)
        `).run(name, base_url, api_key, JSON.stringify(models), weight || 1, max_requests_per_day || 1000);
        res.json({ status: 'success' });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});

app.get('/admin/providers', (req, res) => {
    const providers = db.prepare('SELECT * FROM providers').all();
    providers.forEach(p => p.models = JSON.parse(p.models || '[]'));
    res.json(providers);
});

app.put('/admin/providers/:id', (req, res) => {
    const { name, base_url, api_key, models, weight, max_requests_per_day, is_active } = req.body;
    try {
        db.prepare(`
            UPDATE providers 
            SET name = ?, base_url = ?, api_key = ?, models = ?, weight = ?, max_requests_per_day = ?, is_active = ?
            WHERE id = ?
        `).run(name, base_url, api_key, JSON.stringify(models), weight, max_requests_per_day, is_active ? 1 : 0, req.params.id);
        res.json({ status: 'success' });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});

app.delete('/admin/providers/:id', (req, res) => {
    try {
        db.prepare('DELETE FROM providers WHERE id = ?').run(req.params.id);
        res.json({ status: 'success' });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});

app.post('/admin/providers/:id/fetch-models', async (req, res) => {
    try {
        const models = await Scheduler.fetchModels(req.params.id);
        res.json({ status: 'success', models });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/admin/groups', (req, res) => {
    const { name, alias, target_models } = req.body;
    try {
        db.prepare('INSERT INTO model_groups (name, alias, target_models) VALUES (?, ?, ?)')
            .run(name, alias, JSON.stringify(target_models));
        res.json({ status: 'success' });
    } catch (err) {
        res.status(400).json({ error: err.message });
    }
});

app.get('/admin/groups', (req, res) => {
    const groups = db.prepare('SELECT * FROM model_groups').all();
    groups.forEach(g => g.target_models = JSON.parse(g.target_models));
    res.json(groups);
});

// --- OpenAI Proxy ---
// --- OpenAI Proxy ---
async function handleChatCompletion(req, res, attempt = 0, excludedIds = new Set()) {
    const modelRequested = req.body.model;
    const providers = db.prepare('SELECT * FROM providers WHERE is_active = 1').all();

    // Check for model group mapping
    let group = db.prepare('SELECT * FROM model_groups WHERE alias = ?').get(modelRequested);
    let targetModels = group ? JSON.parse(group.target_models) : [modelRequested];

    // Filter available
    const available = providers.filter(p => {
        if (excludedIds.has(p.id)) return false;
        const supportedModels = JSON.parse(p.models || '[]');
        const hasModel = targetModels.some(m => supportedModels.includes(m));
        const withinQuota = p.current_requests_today < p.max_requests_per_day;
        return hasModel && withinQuota;
    });

    if (available.length === 0) {
        return res.status(404).json({ error: 'No provider found or quota exceeded' });
    }

    // Use Weighted Random
    const provider = Scheduler.weightedRandom(available);

    const url = `${provider.base_url.replace(/\/$/, '')}/chat/completions`;
    const headers = {
        'Authorization': `Bearer ${provider.api_key}`,
        'Content-Type': 'application/json'
    };

    try {
        if (req.body.stream) {
            const response = await axios({
                method: 'post',
                url: url,
                data: req.body,
                headers: headers,
                responseType: 'stream',
                timeout: 30000
            });
            res.setHeader('Content-Type', 'text/event-stream');

            response.data.on('end', () => {
                Scheduler.incrementUsage(provider.id, modelRequested, null);
            });

            response.data.pipe(res);
        } else {
            const response = await axios.post(url, req.body, { headers, timeout: 30000 });
            res.json(response.data);
            Scheduler.incrementUsage(provider.id, modelRequested, response.data.usage);
        }
    } catch (err) {
        console.error(`Provider ${provider.name} failed:`, err.message);
        if (attempt < 2 && available.length > 1) {
            excludedIds.add(provider.id);
            return handleChatCompletion(req, res, attempt + 1, excludedIds);
        }
        res.status(err.response?.status || 500).json(err.response?.data || { error: err.message });
    }
}

app.post('/v1/chat/completions', (req, res) => {
    Scheduler.checkQuotaReset();
    handleChatCompletion(req, res);
});

app.get('/v1/models', (req, res) => {
    const providers = db.prepare('SELECT models FROM providers WHERE is_active = 1').all();
    const allModels = new Set();
    providers.forEach(p => JSON.parse(p.models).forEach(m => allModels.add(m)));

    res.json({
        object: 'list',
        data: Array.from(allModels).map(m => ({ id: m, object: 'model' }))
    });
});

app.listen(PORT, () => {
    console.log(`SimapleLLMDispatch (Node.js) running at http://localhost:${PORT}`);
    console.log(`Dashboard available at http://localhost:${PORT}/dashboard.html`);
});
