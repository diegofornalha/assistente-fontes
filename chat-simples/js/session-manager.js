/**
 * Gerenciador de Sessões - Modal para gerenciamento de título e resumo
 */
class SessionManager {
    constructor() {
        this.currentSessionId = null;
        this.init();
    }

    init() {
        // Vincular eventos dos botões
        this.bindEvents();

        // Carregar CSS
        this.loadCSS();
    }

    bindEvents() {
        // Botão de fechar modal
        const closeBtn = document.getElementById('close-modal-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeModal());
        }

        // Botão cancelar
        const cancelBtn = document.getElementById('cancel-modal-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.closeModal());
        }

        // Botão gerar resumo
        const generateBtn = document.getElementById('generate-summary-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generateSummary());
        }

        // Botão salvar
        const saveBtn = document.getElementById('save-session-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveMetadata());
        }

        // Fechar modal ao clicar fora
        const modal = document.getElementById('session-summary-modal');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal();
                }
            });
        }

        // ESC para fechar
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
    }

    loadCSS() {
        // Verificar se o CSS já está carregado
        if (!document.querySelector('link[href*="summary-modal.css"]')) {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'css/summary-modal.css';
            document.head.appendChild(link);
        }
    }

    openModal(sessionId, currentTitle = '', currentSummary = '') {
        this.currentSessionId = sessionId;

        // Buscar ou criar o modal
        let modal = document.getElementById('session-summary-modal');
        if (!modal) {
            modal = this.createModal();
        }

        // Preencher campos
        document.getElementById('session-title-input').value = currentTitle || '';
        document.getElementById('summary-textarea').value = currentSummary || '';

        // Resetar status
        this.updateSummaryStatus('', '');

        // Mostrar modal
        modal.classList.add('active');

        // Focar no campo título
        setTimeout(() => {
            document.getElementById('session-title-input').focus();
        }, 100);
    }

    closeModal() {
        const modal = document.getElementById('session-summary-modal');
        if (modal) {
            modal.classList.remove('active');
        }
        this.currentSessionId = null;
    }

    createModal() {
        const modal = document.createElement('div');
        modal.id = 'session-summary-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <button class="close-modal" id="close-modal-btn" title="Fechar">&times;</button>
                <h3>Gerenciar Sessão</h3>

                <div class="form-group">
                    <label for="session-title-input">Título da Sessão</label>
                    <input
                        type="text"
                        id="session-title-input"
                        placeholder="Ex: Implementação de feature X"
                        maxlength="100"
                    />
                </div>

                <div class="summary-section">
                    <div class="form-group">
                        <label for="summary-textarea">Resumo da Conversa</label>
                        <textarea
                            id="summary-textarea"
                            class="summary-textarea"
                            placeholder="Clique em 'Gerar Resumo com IA' para criar um resumo automático ou digite manualmente..."
                            maxlength="500"
                        ></textarea>
                    </div>

                    <div class="summary-actions-row" style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
                        <button id="generate-summary-btn" class="generate-summary-btn tooltip">
                            <span class="sparkle">✨</span>
                            Gerar Resumo com IA
                            <span class="tooltiptext">Usa LLM para criar um resumo automático da conversa</span>
                        </button>
                        <button id="save-session-btn" class="save-summary-btn" style="background-color: #27ae60; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; transition: all 0.2s;">
                            <span>💾</span>
                            Salvar
                        </button>
                    </div>

                    <div id="summary-status" class="summary-status">
                        <span id="summary-status-text"></span>
                    </div>
                </div>

                <div class="modal-actions">
                    <button id="cancel-modal-btn">Cancelar</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Rebind eventos
        this.bindEvents();

        return modal;
    }

    async generateSummary() {
        if (!this.currentSessionId) {
            alert('Nenhuma sessão selecionada');
            return;
        }

        const generateBtn = document.getElementById('generate-summary-btn');
        const statusDiv = document.getElementById('summary-status');
        const statusText = document.getElementById('summary-status-text');

        // Mostrar loading
        generateBtn.disabled = true;
        statusDiv.className = 'summary-status loading';
        statusText.innerHTML = '<span class="spinner"></span> Gerando resumo...';

        try {
            const response = await fetch(`/sessions/${this.currentSessionId}/summary`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ regenerate: false }),
            });

            const data = await response.json();

            if (data.success && data.summary) {
                document.getElementById('summary-textarea').value = data.summary;
                statusDiv.className = 'summary-status success';
                statusText.textContent = '✓ Resumo gerado com sucesso!';
            } else {
                throw new Error(data.error || 'Erro ao gerar resumo');
            }
        } catch (error) {
            console.error('Erro ao gerar resumo:', error);
            statusDiv.className = 'summary-status error';
            statusText.textContent = `✗ Erro: ${error.message}`;
        } finally {
            generateBtn.disabled = false;
        }
    }

    async saveMetadata() {
        if (!this.currentSessionId) {
            alert('Nenhuma sessão selecionada');
            return;
        }

        const saveBtn = document.getElementById('save-session-btn');
        const title = document.getElementById('session-title-input').value.trim();
        const summary = document.getElementById('summary-textarea').value.trim();

        saveBtn.disabled = true;
        saveBtn.textContent = 'Salvando...';

        try {
            const response = await fetch(`/sessions/${this.currentSessionId}/metadata`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ title, summary }),
            });

            const data = await response.json();

            if (data.success) {
                // Atualizar a UI da sessão
                this.updateSessionCard(this.currentSessionId, title, summary);

                // Fechar modal
                this.closeModal();

                // Mostrar feedback de sucesso
                this.showToast('Metadados salvos com sucesso!');
            } else {
                throw new Error(data.error || 'Erro ao salvar');
            }
        } catch (error) {
            console.error('Erro ao salvar metadados:', error);
            alert(`Erro ao salvar: ${error.message}`);
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Salvar';
        }
    }

    updateSessionCard(sessionId, title, summary) {
        // Encontrar o card da sessão
        const sessionCard = document.querySelector(`[data-session-id="${sessionId}"]`);
        if (!sessionCard) return;

        // Atualizar título
        const titleDisplay = sessionCard.querySelector('.session-title-display');
        if (title) {
            if (titleDisplay) {
                titleDisplay.textContent = title;
                titleDisplay.classList.remove('empty');
            } else {
                const newTitleDisplay = document.createElement('div');
                newTitleDisplay.className = 'session-title-display';
                newTitleDisplay.textContent = title;
                sessionCard.querySelector('.session-header').appendChild(newTitleDisplay);
            }
        }

        // Atualizar resumo
        const summaryPreview = sessionCard.querySelector('.session-summary-preview');
        if (summary) {
            if (summaryPreview) {
                const previewText = summaryPreview.querySelector('.preview-text');
                if (previewText) {
                    previewText.textContent = summary;
                }
                summaryPreview.classList.remove('empty');
            }
        }
    }

    updateSummaryStatus(type, message) {
        const statusDiv = document.getElementById('summary-status');
        const statusText = document.getElementById('summary-status-text');

        if (!statusDiv || !statusText) return;

        statusDiv.className = `summary-status ${type}`;
        statusText.textContent = message;
    }

    showToast(message, type = 'success') {
        // Criar toast
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#27ae60' : '#e74c3c'};
            color: white;
            padding: 12px 20px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            animation: slideInRight 0.3s ease-out;
        `;

        document.body.appendChild(toast);

        // Remover após 3 segundos
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease-in';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    async loadSessionMetadata(sessionId) {
        try {
            const response = await fetch(`/sessions/${sessionId}/metadata`);
            const data = await response.json();

            if (data.success) {
                return data.metadata;
            }
            return null;
        } catch (error) {
            console.error('Erro ao carregar metadados:', error);
            return null;
        }
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.sessionManager = new SessionManager();
});

// Exportar para uso global
window.SessionManager = SessionManager;
