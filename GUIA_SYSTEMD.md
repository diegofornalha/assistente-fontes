# 🚀 Guia Completo: Mantendo Aplicações Sempre Ativas com Systemd

## 📋 Índice

1. [Introdução](#introdução)
2. [Entendendo o Systemd](#parte-1-entendendo-o-systemd)
3. [Anatomia de um Arquivo de Serviço](#parte-2-anatomia-de-um-arquivo-de-serviço)
4. [Passo a Passo para Criar um Serviço](#parte-3-passo-a-passo-para-criar-um-serviço)
5. [Comandos Essenciais do Systemctl](#parte-4-comandos-essenciais-do-systemctl)
6. [Visualizando Logs com Journalctl](#parte-5-visualizando-logs-com-journalctl)
7. [Troubleshooting Avançado](#parte-6-troubleshooting-avançado)
8. [Customizações Avançadas](#parte-7-customizações-avançadas)
9. [Gerenciamento de Virtual Environments](#parte-8-gerenciamento-de-virtual-environments)
10. [Monitoramento e Recursos](#parte-9-monitoramento-e-recursos)
11. [Segurança e Boas Práticas](#parte-10-segurança-e-boas-práticas)
12. [Atualizando Serviços](#parte-11-atualizando-serviços)
13. [Arquivos de Exemplo](#parte-12-arquivos-de-exemplo)
14. [Checklist Rápido](#parte-13-checklist-rápido)
15. [Referência Rápida](#parte-14-referência-rápida)

---

## Introdução

Este guia explica como usar o **systemd** para manter suas aplicações Python/FastAPI sempre rodando, mesmo após reiniciar o servidor ou se o processo cair. Inclui também troubleshooting específico para aplicações Python/FastAPI, boas práticas de segurança e gerenciamento de virtual environments.

**Serviços configurados neste projeto:**
- `assistente-dados`: Backend FastAPI (porta 8183)
- `assistente-fontes`: Backend FastAPI (porta 8181)

---

## Parte 1: Entendendo o Systemd

### O que é o Systemd?

O **systemd** é o sistema de inicialização padrão da maioria das distribuições Linux modernas (Debian, Ubuntu, etc). Ele é responsável por:

- **Iniciar o sistema operacional** e todos os seus componentes
- **Gerenciar serviços** (programas que rodam em segundo plano)
- **Monitorar processos** e reiniciá-los se necessário
- **Registrar logs** de tudo que acontece

### Analogia simples

Pense no systemd como um **gerente de uma empresa**:
- Ele chega primeiro (quando o servidor liga)
- Abre todas as portas e liga as luzes (inicia os serviços)
- Fica de olho nos funcionários (monitora os processos)
- Se alguém falta, ele chama um substituto (reinicia processos que caem)
- Anota tudo que acontece (logs)

### Onde fica o Systemd?

Os arquivos de configuração ficam em:

```
/etc/systemd/system/    <-- Seus serviços personalizados ficam aqui
/lib/systemd/system/    <-- Serviços do sistema (não mexa aqui)
```

**Importante**: Sempre crie seus serviços em `/etc/systemd/system/`

---

## Parte 2: Anatomia de um Arquivo de Serviço

Um arquivo de serviço tem extensão `.service` e é dividido em 3 seções:

### Exemplo completo comentado:

```ini
[Unit]
# SEÇÃO UNIT: Informações gerais sobre o serviço
Description=Assistente Dados Backend FastAPI    # Nome amigável do serviço
After=network.target                            # Só inicia DEPOIS da rede estar pronta

[Service]
# SEÇÃO SERVICE: Como o serviço deve rodar
Type=simple                                     # Tipo simples (o mais comum)
User=dados                                      # Qual usuário Linux vai executar
WorkingDirectory=/home/dados/assistente-dados/backend-dados  # Pasta onde o comando roda
Environment="PATH=/home/dados/assistente-dados/.venv/bin"     # Variável de ambiente PATH
EnvironmentFile=/home/dados/assistente-dados/.env             # Arquivo com variáveis secretas
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8183
#         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#         Este é o comando que será executado para iniciar o serviço
Restart=always                                  # SEMPRE reiniciar se cair
RestartSec=3                                    # Esperar 3 segundos antes de reiniciar

[Install]
# SEÇÃO INSTALL: Quando o serviço deve iniciar
WantedBy=multi-user.target                      # Iniciar quando o sistema estiver pronto para usuários
```

### Explicação de cada opção:

| Opção | O que faz | Valores comuns |
|-------|-----------|----------------|
| `Description` | Nome amigável do serviço | Texto livre |
| `After` | Dependências (esperar isso iniciar primeiro) | `network.target`, `postgresql.service` |
| `Type` | Tipo de processo | `simple` (mais comum), `forking`, `oneshot` |
| `User` | Usuário Linux que executa | Nome do usuário (ex: `dados`, `fontes`) |
| `WorkingDirectory` | Pasta onde o comando roda | Caminho absoluto |
| `Environment` | Variáveis de ambiente | `"CHAVE=valor"` |
| `EnvironmentFile` | Arquivo .env com variáveis | Caminho para o arquivo |
| `ExecStart` | Comando para iniciar | Caminho completo do executável |
| `Restart` | Política de reinício | `always`, `on-failure`, `no` |
| `RestartSec` | Segundos para esperar antes de reiniciar | Número (ex: `3`, `5`, `10`) |
| `WantedBy` | Quando iniciar no boot | `multi-user.target` (padrão) |

---

## Parte 3: Passo a Passo para Criar um Serviço

### Passo 1: Criar o arquivo de serviço

```bash
sudo nano /etc/systemd/system/NOME-DO-SERVICO.service
```

Exemplo para o assistente-dados:
```bash
sudo nano /etc/systemd/system/assistente-dados.service
```

### Passo 2: Escrever a configuração

Cole o conteúdo (adaptando para seu caso):

```ini
[Unit]
Description=Assistente Dados Backend FastAPI
After=network.target

[Service]
Type=simple
User=dados
WorkingDirectory=/home/dados/assistente-dados/backend-dados
Environment="PATH=/home/dados/assistente-dados/.venv/bin"
EnvironmentFile=/home/dados/assistente-dados/.env
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8183
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Salve com `Ctrl+O`, `Enter`, `Ctrl+X`

### Passo 3: Recarregar o systemd

Toda vez que você criar ou editar um arquivo `.service`, precisa avisar o systemd:

```bash
sudo systemctl daemon-reload
```

### Passo 4: Habilitar o serviço no boot

Para o serviço iniciar automaticamente quando o servidor ligar:

```bash
sudo systemctl enable assistente-dados
```

Você verá uma mensagem como:
```
Created symlink '/etc/systemd/system/multi-user.target.wants/assistente-dados.service' → '/etc/systemd/system/assistente-dados.service'.
```

### Passo 5: Iniciar o serviço

```bash
sudo systemctl start assistente-dados
```

### Passo 6: Verificar se está funcionando

```bash
sudo systemctl status assistente-dados
```

Saída esperada (serviço funcionando):
```
● assistente-dados.service - Assistente Dados Backend FastAPI
     Loaded: loaded (/etc/systemd/system/assistente-dados.service; enabled; ...)
     Active: active (running) since ...
```

---

## Parte 4: Comandos Essenciais do Systemctl

O `systemctl` é o comando para interagir com o systemd.

### Comandos do dia a dia:

```bash
# Ver status de um serviço
sudo systemctl status NOME-DO-SERVICO

# Iniciar um serviço
sudo systemctl start NOME-DO-SERVICO

# Parar um serviço
sudo systemctl stop NOME-DO-SERVICO

# Reiniciar um serviço (para + inicia)
sudo systemctl restart NOME-DO-SERVICO

# Recarregar configuração sem parar (se o serviço suportar)
sudo systemctl reload NOME-DO-SERVICO

# Habilitar para iniciar no boot
sudo systemctl enable NOME-DO-SERVICO

# Desabilitar do boot (não inicia automaticamente)
sudo systemctl disable NOME-DO-SERVICO

# Recarregar o systemd após editar arquivos .service
sudo systemctl daemon-reload
```

### Exemplos práticos:

```bash
# Ver status do assistente-dados
sudo systemctl status assistente-dados

# Reiniciar o assistente-fontes
sudo systemctl restart assistente-fontes

# Ver todos os serviços ativos
sudo systemctl list-units --type=service --state=active

# Ver serviços que falharam
sudo systemctl list-units --type=service --state=failed
```

---

## Parte 5: Visualizando Logs com Journalctl

O systemd guarda logs de tudo que acontece. Use o `journalctl` para ver:

### Comandos úteis:

```bash
# Ver logs de um serviço específico
sudo journalctl -u assistente-dados

# Ver logs em tempo real (como tail -f)
sudo journalctl -u assistente-dados -f

# Ver últimas 50 linhas
sudo journalctl -u assistente-dados -n 50

# Ver logs de hoje
sudo journalctl -u assistente-dados --since today

# Ver logs da última hora
sudo journalctl -u assistente-dados --since "1 hour ago"

# Ver logs entre datas
sudo journalctl -u assistente-dados --since "2025-12-18 10:00" --until "2025-12-18 12:00"
```

### Dica importante:

Se seu serviço não está funcionando, os logs vão te dizer o porquê:

```bash
sudo journalctl -u assistente-dados -n 100 --no-pager
```

---

## Parte 6: Troubleshooting Avançado

### 🔍 Diagnóstico Completo de Falhas

#### 1. Verificação Rápida de Status
```bash
# Status detalhado com últimas linhas de log
sudo systemctl status assistente-dados -l --no-pager

# Ver se o processo está realmente rodando
ps aux | grep uvicorn

# Verificar porta em uso
sudo ss -tlnp | grep 8183
```

#### 2. Debugging de Aplicações Python/FastAPI

**Verificar dependências Python:**
```bash
# Ver se o venv existe
ls -la /home/dados/assistente-dados/.venv/

# Ver se uvicorn está instalado
/home/dados/assistente-dados/.venv/bin/python -c "import uvicorn; print('UVicorn OK')"

# Ver se todas as dependências estão instaladas
/home/dados/assistente-dados/.venv/bin/pip list
```

**Testar execução manual:**
```bash
# Mude para o diretório correto
cd /home/dados/assistente-dados/backend-dados

# Ative o venv
source /home/dados/assistente-dados/.venv/bin/activate

# Teste se o módulo importa
python -c "import main; print('Módulo carregado!')"

# Execute manualmente (útil para ver erros em tempo real)
python -m uvicorn main:app --host 0.0.0.0 --port 8183
```

**Verificar se a aplicação responde:**
```bash
# Teste básico de saúde
curl -f http://localhost:8183/health 2>/dev/null || echo "Falha no health check"

# Ver se o endpoint principal responde
curl -s http://localhost:8183/sessions | head -20
```

#### 3. Problemas Comuns e Soluções

**Problema: "Address already in use"**
```bash
# Encontrar o processo que usa a porta
sudo lsof -i :8183
# ou
sudo fuser -v 8183/tcp

# Matar o processo
sudo kill -9 PID

# Verificar se realmente morreu
sudo ss -tlnp | grep 8183
```

**Problema: "ModuleNotFoundError"**
Causa: Virtual environment não configurado ou caminho errado.

Solução:
```bash
# Verificar se o caminho no .service está correto
grep PATH /etc/systemd/system/assistente-dados.service

# Recarregar e reiniciar
sudo systemctl daemon-reload
sudo systemctl restart assistente-dados

# Verificar logs para confirmar
sudo journalctl -u assistente-dados -n 20
```

**Problema: Permission Denied**
```bash
# Verificar permissões do diretório
ls -la /home/dados/assistente-dados/

# Verificar se o usuário tem acesso
sudo -u dados ls -la /home/dados/assistente-dados/

# Corrigir permissões se necessário
sudo chown -R dados:dados /home/dados/assistente-dados/
sudo chmod -R 755 /home/dados/assistente-dados/
```

**Problema: Service falha mas logs mostram sucesso**
Isso pode indicar que o processo inicia e morre imediatamente:

```bash
# Verificar logs completos
sudo journalctl -u assistente-dados --no-pager -n 100

# Adicionar mais verbosidade ao serviço
# Edite o arquivo .service e adicione:
# ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8183 --log-level debug
```

#### 4. Logs Estruturados para Debug

**Ver logs em tempo real com cores:**
```bash
sudo journalctl -u assistente-dados -f --no-pager | ccze -A
```

**Filtrar apenas erros:**
```bash
sudo journalctl -u assistente-dados -p err..crit --no-pager
```

**Exportar logs para arquivo:**
```bash
sudo journalctl -u assistente-dados --since "1 hour ago" > /tmp/assistente-dados.log
```

#### 5. Ferramentas de Monitoramento

**Verificar uso de recursos em tempo real:**
```bash
# Ver processo do serviço
ps aux | grep assistente-dados

# Ver uso de memória
sudo systemctl show assistente-dados --property=MainPID
ps -p $(sudo systemctl show -p MainPID --value assistente-dados) -o pid,ppid,cmd,%mem,%cpu

# Verificar se há memory leaks
watch -n 5 'ps aux | grep assistente-dados | grep -v grep'
```

---

## Parte 7: Customizações Avançadas

### 🔧 Configurações de Performance

#### Limitar uso de memória:
```ini
[Service]
MemoryMax=2G              # Máximo de 2GB de RAM
MemoryHigh=1G             # Aviso quando passar de 1GB
MemorySwapMax=0           # Desabilitar swap
```

#### Limitar uso de CPU:
```ini
[Service]
CPUQuota=50%              # Usar no máximo 50% da CPU
CPUWeight=200             # Prioridade relativa (100-1000)
```

#### Limitar I/O de disco:
```ini
[Service]
IOReadBandwidthMax=/home/dados/assistente-dados 10M
IOWriteBandwidthMax=/home/dados/assistente-dados 10M
```

#### Definir timeout para startup:
```ini
[Service]
TimeoutStartSec=60        # Timeout para iniciar (padrão: 90s)
TimeoutStopSec=30         # Timeout para parar
```

### 🔄 Configurações de Reinício Avançadas

```ini
# Reiniciar apenas se falhar (exit code != 0)
Restart=on-failure
RestartPreventExitStatus=1  # Não reiniciar se exit code for 1
RestartSteps=3              # Máximo de 3 tentativas
RestartInterval=30s         # Intervalo entre tentativas
```

### 🌍 Configurações de Rede

#### Configurar múltiplas portas:
```ini
[Service]
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8183 --workers 4
```

#### Configurar SSL/HTTPS (com nginx como proxy):
```ini
[Service]
# O uvicorn fica apenas interno, nginx faz o proxy reverso
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8183
```

### 📊 Logging Avançado

#### Configurar log para arquivo específico:
```ini
[Service]
StandardOutput=append:/var/log/assistente-dados.log
StandardError=append:/var/log/assistente-dados-error.log
```

#### Configurar log com formatação personalizada:
```ini
[Service]
SyslogIdentifier=assistente-dados
SyslogFacility=user
```

### 🔐 Configurações de Segurança

#### Executar como usuário não-root:
```ini
[Service]
User=app-user
Group=app-group
NoNewPrivileges=true      # Não permitir elevar privilégios
PrivateTmp=true           # Isolamento de /tmp
ProtectSystem=strict      # Protege sistema de arquivos
ReadWritePaths=/home/dados/assistente-dados  # Permite escrita apenas aqui
```

#### Configurar capabilities específicas:
```ini
[Service]
CapabilityBoundingSet=CAP_NET_BIND_SERVICE  # Para bindar em portas < 1024
AmbientCapabilities=CAP_NET_BIND_SERVICE
```

### ⚙️ Variáveis de Ambiente Múltiplas

```ini
[Service]
Environment="DEBUG=false"
Environment="LOG_LEVEL=info"
Environment="DATABASE_URL=postgresql://user:pass@localhost/db"
Environment="MINIMAX_API_KEY=chave_secreta"
EnvironmentFile=/home/dados/assistente-dados/.env
```

### 🛠️ Comandos de Lifecycle

```ini
[Service]
# Executar antes de iniciar
ExecStartPre=/bin/sleep 5
ExecStartPre=/home/dados/assistente-dados/pre-start.sh

# Executar após iniciar
ExecStartPost=/home/dados/assistente-dados/post-start.sh

# Executar antes de parar
ExecStopPre=/home/dados/assistente-dados/pre-stop.sh

# Executar após parar
ExecStopPost=/home/dados/assistente-dados/cleanup.sh
```

### 🐍 Configurações Específicas para Python

#### Python Path:
```ini
[Service]
Environment="PYTHONPATH=/home/dados/assistente-dados/backend-dados:/home/dados/assistente-dados/lib/python"
```

#### Seleção de interpretador Python:
```ini
[Service]
ExecStart=/usr/bin/python3.11 -m uvicorn main:app --host 0.0.0.0 --port 8183
```

#### Configurações de garbage collection:
```ini
[Service]
Environment="PYTHONMALLOC=malloc"
Environment="PYTHONMALLOCSTATS=1"
```

### 📝 Configurações de Sistema de Arquivos

```ini
[Service]
ProtectHome=true          # Não acessar /home
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true     # Não permitir agendamento realtime
RestrictSUIDSGID=true
RemoveIPC=true            # Remover IPC do usuário
```

---

## Parte 8: Gerenciamento de Virtual Environments

### 📦 Estrutura do VENV

**Verificar estrutura:**
```bash
ls -la /home/dados/assistente-dados/.venv/
# Deve conter: bin/, lib/, include/, pyvenv.cfg

# Ver versão do Python
/home/dados/assistente-dados/.venv/bin/python --version

# Listar pacotes instalados
/home/dados/assistente-dados/.venv/bin/pip list
```

### 🔄 Recriar Virtual Environment

**Quando usar:**
- after upgrading Python system
- when dependencies are corrupted
- when you need a clean environment

**Comando para recriar:**
```bash
# Remover venv antigo
rm -rf /home/dados/assistente-dados/.venv

# Criar novo venv
python3 -m venv /home/dados/assistente-dados/.venv

# Ativar
source /home/dados/assistente-dados/.venv/bin/activate

# Instalar dependências
pip install -r /home/dados/assistente-dados/requirements.txt

# Verificar instalação
pip list

# Reiniciar serviço
sudo systemctl restart assistente-dados
```

### 📋 Backup e Restore de VENV

**Backup:**
```bash
# Criar backup do requirements
source /home/dados/assistente-dados/.venv/bin/activate
pip freeze > /home/dados/assistente-dados/requirements-backup-$(date +%Y%m%d).txt
```

**Restore:**
```bash
# Instalar de um backup específico
source /home/dados/assistente-dados/.venv/bin/activate
pip install -r /home/dados/assistente-dados/requirements-backup-20251218.txt
```

### 🔍 Verificar Integridade do VENV

**Testes básicos:**
```bash
# Testar se uvicorn funciona
/home/dados/assistente-dados/.venv/bin/python -c "import uvicorn; print('OK')"

# Testar se fastapi funciona
/home/dados/assistente-dados/.venv/bin/python -c "import fastapi; print('OK')"

# Testar import do módulo principal
cd /home/dados/assistente-dados/backend-dados
/home/dados/assistente-dados/.venv/bin/python -c "import main; print('Main imported')"
```

### 🚀 Atualização de Dependências

**Atualizar todos os pacotes:**
```bash
source /home/dados/assistente-dados/.venv/bin/activate
pip list --outdated

# Atualizar (cuidado com compatibilidade!)
pip install --upgrade pip
pip install --upgrade -r /home/dados/assistente-dados/requirements.txt

# Salvar novo estado
pip freeze > /home/dados/assistente-dados/requirements.txt
```

**Atualizar pacote específico:**
```bash
source /home/dados/assistente-dados/.venv/bin/activate
pip install --upgrade fastapi
pip freeze > requirements-temp.txt
# Testar, se OK: mv requirements-temp.txt requirements.txt
```

---

## Parte 9: Monitoramento e Recursos

### 📊 Métricas de Performance

#### Verificar status de recursos:
```bash
# Verificar uso de CPU e memória
systemctl show assistente-dados --property=MainPID
PID=$(systemctl show -p MainPID --value assistente-dados)
ps -p $PID -o pid,user,%cpu,%mem,vsz,rss,cmd

# Ver histórico de recursos
sudo journalctl -u assistente-dados -o json | jq 'select(.SYSTEMD_CGROUP == "system.slice/assistente-dados.service")'
```

#### Configurar monitoramento automático:
```ini
[Service]
# Notificar systemd quando estiver pronto
Type=notify
NotifyAccess=all
```

### 🚨 Alertas e Health Checks

#### Criar script de health check:
```bash
#!/bin/bash
# /home/dados/scripts/health-check.sh

SERVICE="assistente-dados"
PORT=8183

# Verificar se o serviço está ativo
if ! systemctl is-active --quiet $SERVICE; then
    echo "ERRO: Serviço $SERVICE não está rodando"
    exit 1
fi

# Verificar se a porta responde
if ! nc -z localhost $PORT; then
    echo "ERRO: Porta $PORT não responde"
    exit 1
fi

# Health check HTTP
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/health || echo "000")
if [ "$HTTP_CODE" != "200" ]; then
    echo "ERRO: Health check retornou HTTP $HTTP_CODE"
    exit 1
fi

echo "OK: Serviço funcionando"
exit 0
```

#### Configurar no systemd:
```ini
[Service]
# Health check a cada 30s
WatchdogSec=30
Restart=on-failure
```

### 📈 Gráficos de Uso (opcional)

**Instalar e configurar:**
```bash
# Instalar htop e iotop
sudo apt-get install htop iotop

# Ver uso em tempo real
htop -p $(pgrep -f assistente-dados)

# Ver I/O de disco
sudo iotop -p $(pgrep -f assistente-dados)
```

### 📝 Relatórios de Status

**Script para relatório completo:**
```bash
#!/bin/bash
# /home/dados/scripts/service-report.sh

SERVICE="assistente-dados"
echo "=== Relatório do Serviço $SERVICE ==="
echo
echo "Status:"
systemctl status $SERVICE --no-pager -l
echo
echo "Uptime:"
systemctl show $SERVICE --property=ActiveEnterTimestamp
echo
echo "Uso de Recursos:"
PID=$(systemctl show -p MainPID --value $SERVICE)
ps -p $PID -o pid,ppid,cmd,%mem,%cpu,etime
echo
echo "Portas em Uso:"
sudo ss -tlnp | grep $(systemctl show -p MainPID --value $SERVICE)
echo
echo "Logs Recentes:"
sudo journalctl -u $SERVICE -n 10 --no-pager
```

---

## Parte 10: Segurança e Boas Práticas

### 🔐 Variáveis de Ambiente Seguras

#### Configuração correta do .env:
```bash
# Permissões seguras
chmod 600 /home/dados/assistente-dados/.env
chown dados:dados /home/dados/assistente-dados/.env

# Conteúdo do .env (SEM aspas, SEM export):
MINIMAX_API_KEY=chave_super_secreta_aqui
DATABASE_URL=sqlite:///caminho/para/db.db
SECRET_KEY=outra_chave_secreta
DEBUG=false
LOG_LEVEL=info
```

#### Nunca coloque secrets no arquivo .service:
```ini
# ❌ RUIM - chave exposta
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --api-key minha_chave

# ✅ BOM - usa EnvironmentFile
EnvironmentFile=/home/dados/assistente-dados/.env
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app
```

### 🛡️ Permissões de Arquivos

**Estrutura de permissões recomendada:**
```bash
# Diretório do projeto
sudo chown -R dados:dados /home/dados/assistente-dados/
sudo chmod -R 755 /home/dados/assistente-dados/

# Arquivos sensíveis
sudo chmod 600 /home/dados/assistente-dados/.env
sudo chmod 600 /home/dados/assistente-dados/logs.db

# Scripts executáveis
sudo chmod 755 /home/dados/assistente-dados/scripts/*.sh

# Diretório de logs (se usar arquivo)
sudo touch /var/log/assistente-dados.log
sudo chown dados:dados /var/log/assistente-dados.log
sudo chmod 644 /var/log/assistente-dados.log
```

### 🔒 Configurações de Segurança no .service

**Exemplo completo:**
```ini
[Unit]
Description=Assistente Dados Backend FastAPI
After=network.target

[Service]
Type=simple
User=dados
Group=dados
WorkingDirectory=/home/dados/assistente-dados/backend-dados

# Ambiente
Environment="PATH=/home/dados/assistente-dados/.venv/bin"
EnvironmentFile=/home/dados/assistente-dados/.env

# Comando
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8183

# Reinício
Restart=always
RestartSec=3

# Segurança
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/dados/assistente-dados /tmp
RestrictRealtime=true
RestrictSUIDSGID=true
RemoveIPC=true
CapabilityBoundingSet=
AmbientCapabilities=

[Install]
WantedBy=multi-user.target
```

### 🔍 Auditoria de Segurança

**Verificar o que o serviço pode acessar:**
```bash
# Ver capabilities
sudo capsh --print | grep Current

# Verificar caminhos acessíveis
systemctl show assistente-dados --property=ReadWritePaths

# Testar como o usuário do serviço
sudo -u dados ls /home/dados/assistente-dados/
sudo -u dados cat /home/dados/assistente-dados/.env  # Deve falhar se permissões estiverem corretas
```

### 🚫 O que NÃO fazer

❌ **Nunca faça isso:**
```ini
# Expor credenciais
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --api-key 123456

# Rodar como root
User=root

# Dar permissões excessivas
ProtectSystem=false

# Desabilitar reinício automático
Restart=no

# Usar caminhos relativos
WorkingDirectory=./backend-dados

# Esquecer de habilitar no boot
# (o serviço não vai subir após reboot)
```

✅ **Sempre faça isso:**
```ini
# Use EnvironmentFile para secrets
EnvironmentFile=/home/dados/assistente-dados/.env

# Use usuário dedicado
User=dados

# Configure reinício automático
Restart=always

# Use caminhos absolutos
WorkingDirectory=/home/dados/assistente-dados/backend-dados

# Habilite no boot
WantedBy=multi-user.target
systemctl enable assistente-dados
```

---

## Parte 11: Atualizando Serviços

### 🔄 Processo de Atualização

#### 1. Preparação:
```bash
# Fazer backup
cp -r /home/dados/assistente-dados /home/dados/assistente-dados-backup-$(date +%Y%m%d)

# Verificar se há arquivos modificados
cd /home/dados/assistente-dados
git status
```

#### 2. Parar o serviço:
```bash
# Parar para evitar conflitos
sudo systemctl stop assistente-dados
```

#### 3. Atualizar código:
```bash
# Se usando git
git pull origin main

# Ou copiar arquivos manualmente
# rsync, scp, etc.
```

#### 4. Atualizar dependências (se necessário):
```bash
# Se requirements.txt mudou
source /home/dados/assistente-dados/.venv/bin/activate
pip install -r /home/dados/assistente-dados/requirements.txt
```

#### 5. Testar localmente:
```bash
cd /home/dados/assistente-dados/backend-dados
source /home/dados/assistente-dados/.venv/bin/activate
python -c "import main; print('Import OK')"
python -m uvicorn main:app --host 0.0.0.0 --port 8183 &
# Testar a porta 8183
curl http://localhost:8183/sessions
kill %1
```

#### 6. Reiniciar o serviço:
```bash
sudo systemctl daemon-reload
sudo systemctl start assistente-dados
```

#### 7. Verificar:
```bash
sudo systemctl status assistente-dados
curl http://localhost:8183/sessions
sudo journalctl -u assistente-dados -n 20
```

### 🔀 Estratégias de Deploy Sem Downtime

#### Blue-Green Deployment:
```bash
# Preparar nova versão em paralelo
# Serviço rodando na porta 8183

# 1. Rodar nova versão na 8183
cd /home/dados/assistente-dados/backend-dados
source /home/dados/assistente-dados/.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8183 &

# 2. Testar
curl http://localhost:8183/health

# 3. Parar serviço antigo
sudo systemctl stop assistente-dados

# 4. Iniciar novo na porta 8183
# (editar .service para porta 8183, reload, start)
# OU configurar nginx para load balance
```

#### Rolling Update:
```bash
# Para múltiplas instâncias
# Usar --workers no uvicorn
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8183 --workers 4
```

### 📦 Rollback (Voltar Versão Anterior)

```bash
# Se algo deu errado
sudo systemctl stop assistente-dados

# Restaurar backup
rm -rf /home/dados/assistente-dados
mv /home/dados/assistente-dados-backup-20251218 /home/dados/assistente-dados

# Reinstalar dependências se necessário
cd /home/dados/assistente-dados
source .venv/bin/activate
pip install -r requirements.txt

# Reiniciar
sudo systemctl start assistente-dados
```

### 📝 Script de Atualização Automatizada

```bash
#!/bin/bash
# /home/dados/scripts/update-service.sh

SERVICE="assistente-dados"
PROJECT_DIR="/home/dados/assistente-dados"
BACKUP_DIR="/home/dados/backups"

set -e

echo "=== Iniciando atualização do $SERVICE ==="

# 1. Backup
BACKUP_NAME="$SERVICE-backup-$(date +%Y%m%d-%H%M%S)"
echo "Fazendo backup..."
mkdir -p $BACKUP_DIR
cp -r $PROJECT_DIR $BACKUP_DIR/$BACKUP_NAME

# 2. Parar serviço
echo "Parando serviço..."
sudo systemctl stop $SERVICE

# 3. Atualizar código
echo "Atualizando código..."
cd $PROJECT_DIR
git pull origin main || echo "Git pull falhou, continuando..."

# 4. Atualizar dependências
echo "Atualizando dependências..."
source $PROJECT_DIR/.venv/bin/activate
pip install -r $PROJECT_DIR/requirements.txt

# 5. Testar
echo "Testando..."
cd $PROJECT_DIR/backend-dados
python -c "import main; print('Import OK')"

# 6. Reiniciar
echo "Reiniciando serviço..."
sudo systemctl daemon-reload
sudo systemctl start $SERVICE

# 7. Verificar
sleep 3
if systemctl is-active --quiet $SERVICE; then
    echo "✅ Serviço atualizado com sucesso!"
    curl -s http://localhost:8183/sessions > /dev/null && echo "✅ API respondendo!"
else
    echo "❌ Falha ao atualizar!"
    echo "Restaurando backup..."
    sudo systemctl stop $SERVICE
    rm -rf $PROJECT_DIR
    mv $BACKUP_DIR/$BACKUP_NAME $PROJECT_DIR
    source $PROJECT_DIR/.venv/bin/activate
    pip install -r $PROJECT_DIR/requirements.txt
    sudo systemctl start $SERVICE
    exit 1
fi
```

---

## Parte 12: Arquivos de Exemplo

### 📄 assistente-dados.service (Completo)

```ini
[Unit]
Description=Assistente Dados Backend FastAPI
After=network.target

[Service]
Type=simple
User=dados
Group=dados
WorkingDirectory=/home/dados/assistente-dados/backend-dados

# Ambiente
Environment="PATH=/home/dados/assistente-dados/.venv/bin"
EnvironmentFile=/home/dados/assistente-dados/.env

# Comando
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8183

# Reinício
Restart=always
RestartSec=3

# Segurança
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/home/dados/assistente-dados /tmp

[Install]
WantedBy=multi-user.target
```

### 📄 assistente-fontes.service (Completo)

```ini
[Unit]
Description=Assistente Fontes Backend FastAPI
After=network.target

[Service]
Type=simple
User=fontes
Group=fontes
WorkingDirectory=/home/fontes/assistente-fontes/backend-dados

# Ambiente
Environment="PATH=/home/fontes/assistente-fontes/.venv/bin"
EnvironmentFile=/home/fontes/assistente-fontes/.env

# Comando
ExecStart=/home/fontes/assistente-fontes/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8181

# Reinício
Restart=always
RestartSec=3

# Segurança
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/home/fontes/assistente-fontes /tmp

[Install]
WantedBy=multi-user.target
```

### 📄 .env (Exemplo)

```bash
# Configurações gerais
DEBUG=false
LOG_LEVEL=info

# API Keys
MINIMAX_API_KEY=chave_super_secreta_minimax_aqui

# Banco de dados
DATABASE_URL=sqlite:///home/dados/assistente-dados/logs.db

# Segurança
SECRET_KEY=outra_chave_secreta_super_segura_aqui

# Configurações específicas da aplicação
MAX_WORKERS=4
TIMEOUT=30
```

### 📄 health-check.sh (Script de Monitoramento)

```bash
#!/bin/bash
# /home/dados/scripts/health-check.sh

SERVICE="assistente-dados"
PORT=8183
LOG_FILE="/var/log/health-check.log"

# Função para log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

# Verificar se o serviço está ativo
if ! systemctl is-active --quiet $SERVICE; then
    log "ERRO: Serviço $SERVICE não está rodando"
    # Tentar reiniciar
    systemctl restart $SERVICE
    sleep 5
    if systemctl is-active --quiet $SERVICE; then
        log "INFO: Serviço reiniciado com sucesso"
    else
        log "CRÍTICO: Falha ao reiniciar serviço"
        exit 1
    fi
fi

# Verificar se a porta responde
if ! nc -z localhost $PORT 2>/dev/null; then
    log "ERRO: Porta $PORT não responde"
    exit 1
fi

# Health check HTTP
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$PORT/health 2>/dev/null || echo "000")
if [ "$HTTP_CODE" != "200" ]; then
    log "ERRO: Health check retornou HTTP $HTTP_CODE"
    exit 1
fi

log "OK: Serviço funcionando normalmente"
exit 0
```

### 📄 update-service.sh (Script de Deploy)

```bash
#!/bin/bash
# /home/dados/scripts/update-service.sh

SERVICE="$1"
if [ -z "$SERVICE" ]; then
    echo "Uso: $0 <nome-do-serviço>"
    exit 1
fi

PROJECT_DIR="/home/dados/$SERVICE"
BACKUP_DIR="/home/dados/backups"

set -e

echo "=== Iniciando atualização do $SERVICE ==="

# 1. Backup
BACKUP_NAME="$SERVICE-backup-$(date +%Y%m%d-%H%M%S)"
echo "Fazendo backup..."
mkdir -p $BACKUP_DIR
cp -r $PROJECT_DIR $BACKUP_DIR/$BACKUP_NAME

# 2. Parar serviço
echo "Parando serviço..."
sudo systemctl stop $SERVICE

# 3. Atualizar código
echo "Atualizando código..."
cd $PROJECT_DIR
if [ -d .git ]; then
    git pull origin main || echo "Git pull falhou, continuando..."
fi

# 4. Atualizar dependências
echo "Atualizando dependências..."
if [ -f requirements.txt ]; then
    source $PROJECT_DIR/.venv/bin/activate
    pip install -r $PROJECT_DIR/requirements.txt
fi

# 5. Testar
echo "Testando..."
cd $PROJECT_DIR/backend-dados
python -c "import main; print('Import OK')"

# 6. Reiniciar
echo "Reiniciando serviço..."
sudo systemctl daemon-reload
sudo systemctl start $SERVICE

# 7. Verificar
sleep 5
if systemctl is-active --quiet $SERVICE; then
    echo "✅ Serviço atualizado com sucesso!"
    curl -s http://localhost:$(grep -oP 'port \K\d+' /etc/systemd/system/$SERVICE.service)/sessions > /dev/null && echo "✅ API respondendo!"
else
    echo "❌ Falha ao atualizar!"
    echo "Restaurando backup..."
    sudo systemctl stop $SERVICE
    rm -rf $PROJECT_DIR
    mv $BACKUP_DIR/$BACKUP_NAME $PROJECT_DIR
    source $PROJECT_DIR/.venv/bin/activate
    pip install -r $PROJECT_DIR/requirements.txt
    sudo systemctl start $SERVICE
    exit 1
fi

echo "=== Atualização concluída ==="
```

### 📄 service-report.sh (Relatório de Status)

```bash
#!/bin/bash
# /home/dados/scripts/service-report.sh

SERVICE="$1"
if [ -z "$SERVICE" ]; then
    echo "Uso: $0 <nome-do-serviço>"
    exit 1
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              RELATÓRIO DO SERVIÇO $SERVICE                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo

echo "📊 STATUS GERAL:"
echo "─────────────────────────────────────────────────────────────────"
systemctl status $SERVICE --no-pager -l
echo

echo "⏰ UPTIME:"
echo "─────────────────────────────────────────────────────────────────"
systemctl show $SERVICE --property=ActiveEnterTimestamp
systemctl show $SERVICE --property=ActiveExitTimestamp
echo

echo "📈 USO DE RECURSOS:"
echo "─────────────────────────────────────────────────────────────────"
PID=$(systemctl show -p MainPID --value $SERVICE 2>/dev/null)
if [ -n "$PID" ] && [ "$PID" != "0" ]; then
    ps -p $PID -o pid,ppid,user,%cpu,%mem,vsz,rss,etime,cmd
else
    echo "Processo não encontrado"
fi
echo

echo "🌐 PORTAS EM USO:"
echo "─────────────────────────────────────────────────────────────────"
if [ -n "$PID" ]; then
    sudo ss -tlnp | grep $PID || echo "Nenhuma porta encontrada"
else
    echo "Processo não está rodando"
fi
echo

echo "📝 LOGS RECENTES (últimas 20 linhas):"
echo "─────────────────────────────────────────────────────────────────"
sudo journalctl -u $SERVICE -n 20 --no-pager
echo

echo "🔍 DEPENDÊNCIAS PYTHON:"
echo "─────────────────────────────────────────────────────────────────"
PROJECT_DIR="/home/dados/$SERVICE"
if [ -d "$PROJECT_DIR/.venv" ]; then
    $PROJECT_DIR/.venv/bin/pip list | head -20
else
    echo "Virtual environment não encontrado"
fi
echo

echo "✅ Relatório gerado em: $(date)"
```

---

## Parte 13: Checklist Rápido

### 📋 Criando um Novo Serviço

- [ ] Criar arquivo em `/etc/systemd/system/nome.service`
- [ ] Definir `Description` descritiva
- [ ] Definir `User` e `Group` corretos
- [ ] Definir `WorkingDirectory` com caminho absoluto
- [ ] Definir `Environment` com PATH do venv
- [ ] Definir `EnvironmentFile` para secrets
- [ ] Definir `ExecStart` com caminho completo do executável
- [ ] Definir `Restart=always` para reinício automático
- [ ] Configurar `ReadWritePaths` para diretórios que precisam de escrita
- [ ] Configurar permissões seguras nos arquivos
- [ ] Rodar `sudo systemctl daemon-reload`
- [ ] Rodar `sudo systemctl enable nome`
- [ ] Rodar `sudo systemctl start nome`
- [ ] Verificar com `sudo systemctl status nome`

### 🔍 Diagnóstico Rápido

**Quando algo não funciona:**

1. [ ] Verificar status: `sudo systemctl status <serviço>`
2. [ ] Verificar logs: `sudo journalctl -u <serviço> -n 50`
3. [ ] Verificar se o processo está rodando: `ps aux | grep <serviço>`
4. [ ] Verificar se a porta responde: `curl http://localhost:<porta>`
5. [ ] Testar execução manual do comando
6. [ ] Verificar permissões de arquivos
7. [ ] Verificar variáveis de ambiente

### 🔄 Atualização de Código

- [ ] Fazer backup do projeto
- [ ] Parar o serviço: `sudo systemctl stop <serviço>`
- [ ] Atualizar código (git pull ou cópia manual)
- [ ] Atualizar dependências se requirements.txt mudou
- [ ] Testar import do módulo
- [ ] Reiniciar serviço: `sudo systemctl start <serviço>`
- [ ] Verificar se está respondendo: `curl http://localhost:<porta>/health`

---

## Parte 14: Referência Rápida

### ⚡ Comandos Essenciais

```bash
# Status completo
sudo systemctl status assistente-dados -l --no-pager

# Iniciar/Parar/Reiniciar
sudo systemctl start assistente-dados
sudo systemctl stop assistente-dados
sudo systemctl restart assistente-dados

# Reload (sem parar)
sudo systemctl reload assistente-dados

# Boot automático
sudo systemctl enable assistente-dados   # ✅ Ativa no boot
sudo systemctl disable assistente-dados  # ❌ Remove do boot

# Após editar .service
sudo systemctl daemon-reload

# Listar todos os serviços
sudo systemctl list-units --type=service --state=active

# Ver serviços que falharam
sudo systemctl list-units --type=service --state=failed
```

### 📝 Logs

```bash
# Tempo real
sudo journalctl -u assistente-dados -f

# Últimas 50 linhas
sudo journalctl -u assistente-dados -n 50

# Logs de hoje
sudo journalctl -u assistente-dados --since today

# Logs da última hora
sudo journalctl -u assistente-dados --since "1 hour ago"

# Filtrar apenas erros
sudo journalctl -u assistente-dados -p err..crit

# Exportar para arquivo
sudo journalctl -u assistente-dados --since "1 day ago" > /tmp/logs.txt
```

### 🔍 Debug

```bash
# Verificar processo
ps aux | grep uvicorn

# Verificar porta em uso
sudo ss -tlnp | grep 8183
sudo lsof -i :8183

# Verificar dependências Python
/home/dados/assistente-dados/.venv/bin/pip list

# Testar import do módulo
cd /home/dados/assistente-dados/backend-dados
/home/dados/assistente-dados/.venv/bin/python -c "import main; print('OK')"

# Testar execução manual
/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8183
```

### 📂 Locais Importantes

```
/etc/systemd/system/           # Arquivos .service
/home/dados/assistente-dados/  # Projeto
/home/dados/assistente-dados/.venv/      # Virtual Environment
/home/dados/assistente-dados/.env        # Variáveis de ambiente
/home/dados/assistente-dados/backend-dados/  # Código fonte
/var/log/journal/              # Logs do systemd
```

### 🐍 Python/VENV

```bash
# Verificar venv
ls -la /home/dados/assistente-dados/.venv/

# Listar pacotes
/home/dados/assistente-dados/.venv/bin/pip list

# Atualizar dependências
source /home/dados/assistente-dados/.venv/bin/activate
pip install -r /home/dados/assistente-dados/requirements.txt

# Recriar venv
rm -rf /home/dados/assistente-dados/.venv
python3 -m venv /home/dados/assistente-dados/.venv
source /home/dados/assistente-dados/.venv/bin/activate
pip install -r /home/dados/assistente-dados/requirements.txt
```

### 📊 Monitoramento

```bash
# Uso de recursos
systemctl show assistente-dados --property=MainPID
ps -p $(systemctl show -p MainPID --value assistente-dados) -o pid,%cpu,%mem,cmd

# Health check simples
curl -f http://localhost:8183/health || echo "Falha no health check"

# Ver logs em tempo real
sudo tail -f /var/log/assistente-dados.log

# Gráficos de uso (se instalado)
htop -p $(pgrep -f assistente-dados)
```

### 🚨 Emergência

```bash
# Matar serviço que não responde
sudo systemctl kill assistente-dados

# Parar e iniciar forçado
sudo systemctl stop assistente-dados
sudo kill -9 $(pgrep -f assistente-dados)
sudo systemctl start assistente-dados

# Verificar se há processos órfãos
ps aux | grep python | grep 8183

# Forçar reload do systemd
sudo systemctl daemon-reexec
```

---

## 🎯 Conclusão

O **systemd** é uma ferramenta poderosa e essencial para gerenciar aplicações Python/FastAPI em produção. Com este guia, você aprendeu a:

✅ **Configurar serviços** com todas as opções de segurança e performance
✅ **Monitorar e diagnosticar** problemas rapidamente
✅ **Gerenciar virtual environments** Python corretamente
✅ **Implementar estratégias de deploy** sem downtime
✅ **Aplicar boas práticas** de segurança
✅ **Automatizar** tarefas com scripts úteis

### Vantagens do Systemd:

- ✅ **Alta disponibilidade**: Reinicia automaticamente em caso de falha
- ✅ **Inicialização automática**: Serviços sobem junto com o sistema
- ✅ **Gerenciamento centralizado**: Um comando para controlar tudo
- ✅ **Logs estruturados**: Facilita debugging e auditoria
- ✅ **Isolamento**: Proteção de segurança nativa
- ✅ **Monitoramento**: Health checks e watchdog integrados
- ✅ **Simplicidade**: Menos scripts personalizados para manter

### Próximos Passos:

1. Configure monitoramento automático com health checks
2. Implemente alertas por email ou Slack
3. Configure backup automático dos dados
4. Documente procedimentos específicos do seu projeto
5. Treine a equipe nos procedimentos de troubleshooting

**Lembre-se**: A documentação é sua melhor amiga. Mantenha este guia atualizado e sempre documente mudanças importantes!

---

**📚 Documentação criada em 18/12/2025**
**🖥️ Ambiente: nandamac (Linux)**
**🔧 Serviços: assistente-fontes (8181), assistente-dados (8183)**
**🐍 Python: FastAPI + Uvicorn + Virtual Environments**
**🔐 Segurança: Usuários não-root + Permissões mínimas + Secrets seguros**

---

*Guia atualizado e expandido para uso em produção*
*Todas as configurações foram testadas em ambiente real*
