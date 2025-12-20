/**
 * Gerenciador de Resumo da Conversa
 * Extrai tópicos, módulos/aulas, insights e gera sugestões
 */

class ConversationSummary {
    constructor() {
        this.conversationHistory = [];
        this.summary = null;
        this.init();
    }

    init() {
        this.bindEvents();
    }

    bindEvents() {
        const summaryBtn = document.getElementById('summary-btn');
        const closeBtn = document.getElementById('close-summary-modal');
        const regenerateBtn = document.getElementById('regenerate-summary-btn');
        const exportBtn = document.getElementById('export-summary-btn');
        const generateAIBtn = document.getElementById('generate-ai-summary-btn');
        const saveBtn = document.getElementById('save-conversation-btn');
        const modal = document.getElementById('conversation-summary-modal');

        if (summaryBtn) {
            summaryBtn.addEventListener('click', () => this.openSummaryModal());
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeSummaryModal());
        }

        if (regenerateBtn) {
            regenerateBtn.addEventListener('click', () => this.regenerateSummary());
        }

        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportSummary());
        }

        if (generateAIBtn) {
            generateAIBtn.addEventListener('click', () => this.generateAISummary());
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveConversation());
        }

        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeSummaryModal();
                }
            });
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal?.classList.contains('active')) {
                this.closeSummaryModal();
            }
        });
    }

    updateHistory(messages) {
        this.conversationHistory = messages || [];
    }

    openSummaryModal() {
        this.generateSummary();
        const modal = document.getElementById('conversation-summary-modal');
        if (modal) {
            modal.classList.add('active');
        }
    }

    closeSummaryModal() {
        const modal = document.getElementById('conversation-summary-modal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    generateSummary() {
        if (this.conversationHistory.length === 0) {
            this.displayEmptySummary();
            return;
        }

        this.summary = {
            overview: this.generateOverview(),
            topics: this.extractTopics(),
            modules: this.extractModules(),
            insights: this.generateInsights(),
            progress: this.calculateProgress(),
            suggestions: this.generateSuggestions()
        };

        this.displaySummary();
    }

    regenerateSummary() {
        this.generateSummary();
    }

    generateOverview() {
        const totalMessages = this.conversationHistory.length;
        const userMessages = this.conversationHistory.filter(m => m.role === 'user').length;
        const aiMessages = this.conversationHistory.filter(m => m.role === 'assistant').length;

        return `Esta conversa contém ${totalMessages} mensagens (${userMessages} perguntas suas e ${aiMessages} respostas da assistente). A conversa aborda questões sobre sistemas de CRM, Data Lake, arquitetura de dados e desenvolvimento de software.`;
    }

    extractTopics() {
        const topics = new Set();
        const keywords = {
            'Atração de Pacientes': ['atrair', 'captação', 'conquistar', 'marketing', 'pacientes'],
            'Precificação': ['preço', 'valor', 'cobrar', 'precificação', 'valoração'],
            'Arquitetura de Dados': ['data lake', 'bronze', 'silver', 'gold', 'arquitetura', 'schema'],
            'Comunicação com Pacientes': ['comunicação', 'conversa', 'relacionamento', 'vínculo'],
            'Estratégias de Vendas': ['venda', 'vendas', 'fechamento', 'proposta'],
            'Especialidades Médicas': ['dermatologista', 'pediatra', 'psicóloga', 'dentista', 'cardiologista'],
            'Health Plan': ['health plan', 'plano de saúde', 'tratamento', 'plano'],
            'Automação': ['automação', 'automatizar', 'whatsapp', 'chatbot', 'sistema']
        };

        const allText = this.conversationHistory
            .map(m => m.content || '')
            .join(' ')
            .toLowerCase();

        for (const [topic, words] of Object.entries(keywords)) {
            if (words.some(word => allText.includes(word))) {
                topics.add(topic);
            }
        }

        return Array.from(topics);
    }

    extractModules() {
        const modules = new Set();
        const moduleNames = {
            1: 'Data Lake - Bronze',
            2: 'Data Lake - Silver',
            3: 'Data Lake - Gold',
            4: 'CRM Operacional',
            5: 'RLS Policies',
            6: 'Funções SQL',
            7: 'Especialidades Médicas'
        };

        const modulePattern = /(?:módulo|modulo)\s*(\d+)/gi;
        const aulaPattern = /aula\s*(\d+)\.(\d+)(?:\.(\d+))?/gi;

        const allText = this.conversationHistory
            .map(m => m.content || '')
            .join(' ');

        let match;
        while ((match = modulePattern.exec(allText)) !== null) {
            const moduleNum = parseInt(match[1]);
            if (moduleNum >= 1 && moduleNum <= 7) {
                modules.add({
                    number: moduleNum,
                    name: moduleNames[moduleNum] || `Módulo ${moduleNum}`,
                    type: 'module'
                });
            }
        }

        while ((match = aulaPattern.exec(allText)) !== null) {
            const mod = parseInt(match[1]);
            const aula = parseInt(match[2]);
            if (mod >= 1 && mod <= 7) {
                modules.add({
                    number: mod,
                    name: `Módulo ${mod} - Aula ${aula}`,
                    type: 'lesson',
                    detail: `Aula ${aula}`
                });
            }
        }

        return Array.from(modules);
    }

    generateInsights() {
        const insights = [];

        const topics = this.summary?.topics || this.extractTopics();
        if (topics.length > 0) {
            insights.push({
                icon: '💡',
                text: `Você explorou ${topics.length} tópicos principais do curso, demonstrando interesse em áreas específicas do marketing médico.`
            });
        }

        const modules = this.summary?.modules || this.extractModules();
        if (modules.length > 0) {
            insights.push({
                icon: '📈',
                text: `Conhecimento em ${modules.length} módulo(s)/aula(s) foi construído durante esta conversa.`
            });
        }

        const userMessages = this.conversationHistory.filter(m => m.role === 'user').length;
        if (userMessages >= 5) {
            insights.push({
                icon: '🎯',
                text: `Alta engajamento detectado com ${userMessages} perguntas, indicando um estudo ativo e aprofundado.`
            });
        }

        if (insights.length === 0) {
            insights.push({
                icon: '🌟',
                text: 'Início de uma conversa sobre sistemas de CRM e Data Lake. Continue explorando os tópicos para mais insights!'
            });
        }

        return insights;
    }

    calculateProgress() {
        const modules = this.extractModules();
        const totalModules = 7;

        const uniqueModules = new Set(modules.map(m => m.number)).size;
        const percentage = Math.round((uniqueModules / totalModules) * 100);

        return {
            percentage,
            modulesStudied: uniqueModules,
            totalModules,
            text: `${percentage}% do curso concluído (${uniqueModules}/${totalModules} módulos)`
        };
    }

    generateSuggestions() {
        const suggestions = [];
        const modules = this.extractModules();
        const uniqueModuleNumbers = new Set(modules.map(m => m.number));

        if (uniqueModuleNumbers.size === 0) {
            suggestions.push({
                icon: '🚀',
                text: 'Comece explorando Data Lake - Bronze: estrutura básica de dados'
            });
            suggestions.push({
                icon: '❓',
                text: 'Faça uma pergunta sobre estratégias de atração de pacientes'
            });
        } else {
            const lastModule = Math.max(...uniqueModuleNumbers);
            if (lastModule < 7) {
                suggestions.push({
                    icon: '➡️',
                    text: `Continue com o Módulo ${lastModule + 1}: ${this.getModuleName(lastModule + 1)}`
                });
            }

            if (uniqueModuleNumbers.has(1)) {
                suggestions.push({
                    icon: '💰',
                    text: 'Aprofunde-se no Módulo 3 sobre Precificação e Monetização'
                });
            }

            if (uniqueModuleNumbers.has(2)) {
                suggestions.push({
                    icon: '🎯',
                    text: 'Explore técnicas específicas do Módulo 2 para atração de pacientes'
                });
            }

            suggestions.push({
                icon: '🤔',
                text: 'Tire dúvidas específicas sobre sua especialidade médica'
            });
        }

        return suggestions;
    }

    getModuleName(moduleNumber) {
        const names = {
            1: 'Data Lake - Bronze',
            2: 'Estratégias de Atração de Pacientes',
            3: 'Precificação e Monetização',
            4: 'Estruturação de Processos',
            5: 'Comunicação e Relacionamento',
            6: 'Automação e Sistemas',
            7: 'Especialidades Médicas'
        };
        return names[moduleNumber] || `Módulo ${moduleNumber}`;
    }

    displayEmptySummary() {
        const overview = document.getElementById('summary-overview');
        const topics = document.getElementById('summary-topics');
        const modules = document.getElementById('summary-modules');
        const insights = document.getElementById('summary-insights');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const suggestions = document.getElementById('suggestions-list');

        if (overview) overview.innerHTML = '<p class="empty-message">Nenhuma conversa iniciada ainda.</p>';
        if (topics) topics.innerHTML = '<p class="empty-message">Nenhum tópico identificado.</p>';
        if (modules) modules.innerHTML = '<p class="empty-message">Nenhum módulo ou aula foi mencionado.</p>';
        if (insights) insights.innerHTML = '<p class="empty-message">Nenhum insight foi gerado ainda.</p>';
        if (progressFill) progressFill.style.width = '0%';
        if (progressText) progressText.textContent = '0% do curso concluído';
        if (suggestions) {
            suggestions.innerHTML = '<li>Comece uma conversa para receber sugestões personalizadas</li>';
        }
    }

    displaySummary() {
        if (!this.summary) return;

        const overview = document.getElementById('summary-overview');
        const topics = document.getElementById('summary-topics');
        const modules = document.getElementById('summary-modules');
        const insights = document.getElementById('summary-insights');
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const suggestions = document.getElementById('suggestions-list');

        if (overview) {
            overview.innerHTML = `<p>${this.summary.overview}</p>`;
        }

        if (topics) {
            if (this.summary.topics.length === 0) {
                topics.innerHTML = '<p class="empty-message">Nenhum tópico específico identificado.</p>';
            } else {
                topics.innerHTML = `
                    <ul class="summary-topics-list">
                        ${this.summary.topics.map(topic => `<li class="topic-tag">${topic}</li>`).join('')}
                    </ul>
                `;
            }
        }

        if (modules) {
            if (this.summary.modules.length === 0) {
                modules.innerHTML = '<p class="empty-message">Nenhum módulo ou aula foi mencionado.</p>';
            } else {
                modules.innerHTML = `
                    <ul class="modules-list">
                        ${this.summary.modules.map(mod => `
                            <li class="module-item">
                                <span class="module-icon">📚</span>
                                <div class="module-info">
                                    <div class="module-name">${mod.name}</div>
                                    ${mod.detail ? `<div class="module-detail">${mod.detail}</div>` : ''}
                                </div>
                            </li>
                        `).join('')}
                    </ul>
                `;
            }
        }

        if (insights) {
            insights.innerHTML = `
                <ul class="insights-list">
                    ${this.summary.insights.map(insight => `
                        <li class="insight-item">
                            <span class="insight-icon">${insight.icon}</span>
                            <span class="insight-text">${insight.text}</span>
                        </li>
                    `).join('')}
                </ul>
            `;
        }

        if (progressFill) {
            progressFill.style.width = `${this.summary.progress.percentage}%`;
        }

        if (progressText) {
            progressText.textContent = this.summary.progress.text;
        }

        if (suggestions) {
            suggestions.innerHTML = `
                ${this.summary.suggestions.map(suggestion => `
                    <li>
                        <span class="suggestion-icon">${suggestion.icon}</span>
                        <span class="suggestion-text">${suggestion.text}</span>
                    </li>
                `).join('')}
            `;
        }
    }

    async generateAISummary() {
        if (this.conversationHistory.length === 0) {
            alert('Nenhuma conversa para resumir');
            return;
        }

        const generateBtn = document.getElementById('generate-ai-summary-btn');
        const statusDiv = document.getElementById('ai-summary-status');
        const overview = document.getElementById('summary-overview');

        // Mostrar loading
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="spinner"></span> Gerando com IA...';

        // Limpar overview e mostrar indicador de typing
        if (overview) {
            overview.innerHTML = `
                <p><strong>🤖 Resumo Inteligente:</strong></p>
                <div class="typing-summary">
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                    <span class="typing-dot"></span>
                </div>
            `;
        }

        try {
            const response = await fetch('/api/conversation/summary/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    messages: this.conversationHistory
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullSummary = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6).trim();

                        if (data === '[DONE]') {
                            if (statusDiv) {
                                statusDiv.innerHTML = '<span class="success-icon">✓</span> Resumo gerado com sucesso!';
                                statusDiv.className = 'summary-status success';
                            }
                            break;
                        }

                        if (data.startsWith('[ERROR]')) {
                            throw new Error(data.slice(7));
                        }

                        // Acumular o resumo
                        fullSummary += data;

                        // Atualizar o overview em tempo real
                        if (overview) {
                            const contentDiv = overview.querySelector('.typing-summary');
                            if (contentDiv) {
                                overview.innerHTML = `
                                    <p><strong>🤖 Resumo Inteligente:</strong></p>
                                    <p style="margin-top: 1rem; line-height: 1.6;">${fullSummary}</p>
                                `;
                            }
                        }
                    }
                }
            }

        } catch (error) {
            console.error('Erro ao gerar resumo com IA:', error);
            if (overview) {
                overview.innerHTML = '<p class="error-message">Erro ao gerar resumo com IA</p>';
            }
            if (statusDiv) {
                statusDiv.innerHTML = `<span class="error-icon">✗</span> Erro: ${error.message}`;
                statusDiv.className = 'summary-status error';
            }
        } finally {
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<span class="sparkle">✨</span> Gerar Resumo com IA';
        }
    }

    async saveConversation() {
        if (this.conversationHistory.length === 0) {
            alert('Nenhuma conversa para salvar');
            return;
        }

        const saveBtn = document.getElementById('save-conversation-btn');
        const statusDiv = document.getElementById('ai-summary-status');

        // Mostrar loading
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner"></span> Salvando...';

        try {
            // Salvar cada mensagem no banco via WebSocket
            if (window.claudeChatApp && window.claudeChatApp.ws) {
                // Recriar a conversa via WebSocket para persistir no logs.db
                for (const msg of this.conversationHistory) {
                    if (msg.role === 'user') {
                        // Enviar mensagem do usuário
                        window.claudeChatApp.ws.send(JSON.stringify({
                            message: msg.content,
                            conversation_id: window.claudeChatApp.conversationId || 'summary_' + Date.now()
                        }));

                        // Aguardar um pouco para não sobrecarregar
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }
                }

                if (statusDiv) {
                    statusDiv.innerHTML = '<span class="success-icon">✓</span> Conversa salva com sucesso!';
                    statusDiv.className = 'summary-status success';
                }

                // Mostrar notificação de sucesso
                this.showToast('Conversa salva com sucesso no histórico!', 'success');
            } else {
                throw new Error('WebSocket não disponível');
            }

        } catch (error) {
            console.error('Erro ao salvar conversa:', error);
            if (statusDiv) {
                statusDiv.innerHTML = `<span class="error-icon">✗</span> Erro: ${error.message}`;
                statusDiv.className = 'summary-status error';
            }
            this.showToast('Erro ao salvar conversa', 'error');
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<span class="btn-icon">💾</span> Salvar Conversa';
        }
    }

    exportSummary() {
        if (!this.summary) {
            alert('Nenhum resumo para exportar');
            return;
        }

        const content = `
RESUMO DA CONVERSA - Sistema CRM/Data Lake
=============================================

📝 RESUMO GERAL
${this.summary.overview}

🎯 TÓPICOS ABORDADOS
${this.summary.topics.map(t => `- ${t}`).join('\n') || 'Nenhum'}

📚 MÓDULOS/AULAS COBERTOS
${this.summary.modules.map(m => `- ${m.name}`).join('\n') || 'Nenhum'}

💡 INSIGHTS PRINCIPAIS
${this.summary.insights.map(i => `- ${i.text}`).join('\n')}

🚀 PROGRESSO NA JORNADA
${this.summary.progress.text}

➡️ PRÓXIMOS PASSOS SUGERIDOS
${this.summary.suggestions.map(s => `- ${s.text}`).join('\n')}

---
Gerado em: ${new Date().toLocaleString('pt-BR')}
        `.trim();

        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `resumo-conversa-${new Date().toISOString().slice(0, 10)}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.conversationSummary = new ConversationSummary();
});

// Exportar para uso global
window.ConversationSummary = ConversationSummary;
