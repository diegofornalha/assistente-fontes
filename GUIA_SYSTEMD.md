# Guia Completo: Mantendo Aplicações Sempre Ativas com Systemd

## Introdução

Este guia explica como usar o **systemd** para manter suas aplicações Python/FastAPI sempre rodando, mesmo após reiniciar o servidor ou se o processo cair.

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
WorkingDirectory=/home/dados/assistente-dados/backend-fontes  # Pasta onde o comando roda
Environment="PATH=/home/dados/assistente-dados/.venv/bin"     # Variável de ambiente PATH
EnvironmentFile=/home/dados/assistente-dados/.env             # Arquivo com variáveis secretas
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8182
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
WorkingDirectory=/home/dados/assistente-dados/backend-fontes
Environment="PATH=/home/dados/assistente-dados/.venv/bin"
EnvironmentFile=/home/dados/assistente-dados/.env
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8182
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

## Parte 6: Troubleshooting (Resolvendo Problemas)

### Problema: Serviço não inicia

1. **Verifique o status:**
   ```bash
   sudo systemctl status assistente-dados
   ```

2. **Veja os logs:**
   ```bash
   sudo journalctl -u assistente-dados -n 50
   ```

3. **Erros comuns:**
   - `code=exited, status=1` → Erro no comando ExecStart
   - `code=exited, status=127` → Comando não encontrado (caminho errado)
   - `code=exited, status=2` → Arquivo não encontrado

### Problema: Permissão negada

Verifique se o usuário tem acesso aos arquivos:
```bash
ls -la /home/dados/assistente-dados/
```

O usuário configurado em `User=` precisa ter permissão de leitura/execução.

### Problema: Variáveis de ambiente não carregam

1. Verifique se o arquivo `.env` existe:
   ```bash
   ls -la /home/dados/assistente-dados/.env
   ```

2. Verifique se o formato está correto (sem aspas, sem export):
   ```
   CHAVE=valor
   OUTRA_CHAVE=outro_valor
   ```

### Problema: Porta já em uso

Se aparecer erro de porta em uso:
```bash
# Ver o que está usando a porta 8182
sudo ss -tlnp | grep 8182

# Matar o processo (substitua PID pelo número)
sudo kill PID
```

---

## Parte 7: Customizações Avançadas

### Limitar uso de memória:

```ini
[Service]
MemoryMax=2G              # Máximo de 2GB de RAM
MemoryHigh=1G             # Aviso quando passar de 1GB
```

### Limitar uso de CPU:

```ini
[Service]
CPUQuota=50%              # Usar no máximo 50% da CPU
```

### Definir variáveis de ambiente diretamente:

```ini
[Service]
Environment="DEBUG=false"
Environment="LOG_LEVEL=info"
Environment="DATABASE_URL=postgresql://user:pass@localhost/db"
```

### Executar comando antes de iniciar:

```ini
[Service]
ExecStartPre=/home/dados/assistente-dados/pre-start.sh
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app
```

### Executar comando depois de parar:

```ini
[Service]
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app
ExecStopPost=/home/dados/assistente-dados/cleanup.sh
```

### Atrasar início (útil para dependências):

```ini
[Service]
ExecStartPre=/bin/sleep 10    # Espera 10 segundos antes de iniciar
```

### Diferentes políticas de reinício:

```ini
# Sempre reiniciar
Restart=always

# Só reiniciar se falhar (exit code diferente de 0)
Restart=on-failure

# Nunca reiniciar
Restart=no

# Reiniciar em caso de sinal anormal (kill, segfault)
Restart=on-abnormal
```

---

## Parte 8: Resumo dos Arquivos Criados

### Arquivos de serviço no servidor:

| Arquivo | Serviço | Porta |
|---------|---------|-------|
| `/etc/systemd/system/assistente-fontes.service` | Assistente Fontes | 8181 |
| `/etc/systemd/system/assistente-dados.service` | Assistente Dados | 8182 |

### Conteúdo do assistente-dados.service:

```ini
[Unit]
Description=Assistente Dados Backend FastAPI
After=network.target

[Service]
Type=simple
User=dados
WorkingDirectory=/home/dados/assistente-dados/backend-fontes
Environment="PATH=/home/dados/assistente-dados/.venv/bin"
EnvironmentFile=/home/dados/assistente-dados/.env
ExecStart=/home/dados/assistente-dados/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8182
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### Conteúdo do assistente-fontes.service:

```ini
[Unit]
Description=Assistente Fontes Backend FastAPI
After=network.target

[Service]
Type=simple
User=fontes
WorkingDirectory=/home/fontes/assistente-fontes/backend-fontes
Environment="PATH=/home/fontes/assistente-fontes/.venv/bin"
EnvironmentFile=/home/fontes/assistente-fontes/.env
ExecStart=/home/fontes/assistente-fontes/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8181
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

---

## Parte 9: Checklist Rápido

Quando precisar criar um novo serviço, siga este checklist:

- [ ] Criar arquivo em `/etc/systemd/system/nome.service`
- [ ] Definir `Description` descritiva
- [ ] Definir `User` correto
- [ ] Definir `WorkingDirectory` correto
- [ ] Definir `ExecStart` com caminho completo
- [ ] Definir `Restart=always` se quiser que reinicie sozinho
- [ ] Criar arquivo `.env` se precisar de variáveis de ambiente
- [ ] Rodar `sudo systemctl daemon-reload`
- [ ] Rodar `sudo systemctl enable nome`
- [ ] Rodar `sudo systemctl start nome`
- [ ] Verificar com `sudo systemctl status nome`

---

## Parte 10: Referência Rápida

### Comandos mais usados:

```bash
# Status
systemctl status assistente-dados

# Iniciar/Parar/Reiniciar
systemctl start assistente-dados
systemctl stop assistente-dados
systemctl restart assistente-dados

# Boot
systemctl enable assistente-dados   # Ativa no boot
systemctl disable assistente-dados  # Remove do boot

# Após editar .service
systemctl daemon-reload

# Logs
journalctl -u assistente-dados -f     # Tempo real
journalctl -u assistente-dados -n 50  # Últimas 50 linhas
```

### Locais importantes:

```
/etc/systemd/system/              # Seus serviços
/home/dados/assistente-dados/     # Seu projeto
/home/dados/assistente-dados/.env # Variáveis de ambiente
```

---

## Conclusão

O systemd é uma ferramenta poderosa para manter suas aplicações sempre rodando. Com ele você não precisa se preocupar em:

- Iniciar manualmente após reiniciar o servidor
- Monitorar se o processo caiu
- Criar scripts de watchdog manualmente

Tudo isso o systemd faz automaticamente para você!

---

*Guia criado em 18/12/2025*
*Servidor: nandamac*
*Serviços configurados: assistente-fontes (8181), assistente-dados (8182)*
