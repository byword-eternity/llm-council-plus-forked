import React from 'react';
import './CouncilGrid.css';

const PROVIDER_CONFIG = {
    openai: { color: '#10a37f', label: 'OpenAI', icon: '🟢' },
    anthropic: { color: '#d97757', label: 'Anthropic', icon: '🟠' },
    google: { color: '#4285f4', label: 'Google', icon: '🔵' },
    meta: { color: '#0668E1', label: 'Meta', icon: 'Ⓜ️' },
    mistral: { color: '#fcd34d', label: 'Mistral', icon: '🟡' },
    groq: { color: '#f55036', label: 'Groq', icon: '⚡' },
    ollama: { color: '#ffffff', label: 'Local', icon: '🦙' },
    default: { color: '#888888', label: 'Model', icon: '🤖' }
};

const getProviderInfo = (modelId) => {
    if (!modelId) return PROVIDER_CONFIG.default;
    const id = modelId.toLowerCase();
    if (id.includes('gpt')) return PROVIDER_CONFIG.openai;
    if (id.includes('claude')) return PROVIDER_CONFIG.anthropic;
    if (id.includes('gemini') || id.includes('google')) return PROVIDER_CONFIG.google;
    if (id.includes('llama')) return PROVIDER_CONFIG.meta;
    if (id.includes('mistral') || id.includes('mixtral')) return PROVIDER_CONFIG.mistral;
    if (id.startsWith('groq:')) return PROVIDER_CONFIG.groq;
    if (id.startsWith('ollama:')) return PROVIDER_CONFIG.ollama;

    return PROVIDER_CONFIG.default;
};

export default function CouncilGrid({
    models = [],
    chairman = null,
    status = 'idle', // 'idle', 'thinking', 'complete'
    progress = {}    // { currentModel: 'id', completed: ['id1', 'id2'] }
}) {
    // If no models provided, show placeholders
    const displayModels = models.length > 0 ? models : ['placeholder-1', 'placeholder-2', 'placeholder-3'];

    return (
        <div className="council-grid">
            {/* Regular Council Members */}
            {displayModels.map((modelId, index) => {
                const isPlaceholder = modelId.startsWith('placeholder');
                const info = isPlaceholder ? PROVIDER_CONFIG.default : getProviderInfo(modelId);
                const displayName = isPlaceholder ? 'Council Member' : modelId.split('/').pop().split(':')[0];

                // Determine state
                let cardState = 'idle';
                if (status === 'thinking') {
                    if (progress.completed?.includes(modelId)) {
                        cardState = 'done';
                    } else if (progress.currentModel === modelId) {
                        cardState = 'active';
                    } else {
                        cardState = 'waiting';
                    }
                } else if (status === 'complete') {
                    cardState = 'done';
                } else if (status === 'idle') {
                    cardState = 'ready';
                }

                return (
                    <div
                        key={index}
                        className={`council-card ${cardState}`}
                        style={{ '--provider-color': info.color }}
                    >
                        <div className="role-badge member">Member #{index + 1}</div>
                        <div className="council-avatar">
                            <span className="avatar-icon">{info.icon}</span>
                            {cardState === 'active' && <div className="thinking-ring"></div>}
                            {cardState === 'done' && <div className="done-badge">✓</div>}
                        </div>
                        <div className="council-info">
                            <span className="model-name" title={modelId}>{displayName}</span>
                            <span className="provider-label">{info.label}</span>
                        </div>
                    </div>
                );
            })}

            {/* Chairman Card (Always last or distinct) */}
            {chairman && (
                <div
                    className="council-card chairman ready"
                    style={{ '--provider-color': '#fbbf24' }} // Gold for Chairman
                >
                    <div className="role-badge chairman">Chairman</div>
                    <div className="council-avatar">
                        <span className="avatar-icon">⚖️</span>
                    </div>
                    <div className="council-info">
                        <span className="model-name" title={chairman}>{chairman.split('/').pop().split(':')[0]}</span>
                        <span className="provider-label">Final Verdict</span>
                    </div>
                </div>
            )}
        </div>
    );
}
