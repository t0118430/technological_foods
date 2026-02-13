# 📱 Guia de Teste de Notificações - Dados Reais

## 🎯 Objetivo
Verificar se você **receberá notificações em TODOS os cenários** de alerta:
- ✅ Temperatura crítica alta/baixa
- ✅ pH crítico
- ✅ EC crítica
- ✅ Múltiplos sensores em falha
- ✅ Escalação de alertas
- ✅ Diferentes tiers (Bronze/Silver/Gold/Platinum)

---

## 🚀 Configuração Rápida (5 minutos)

### Passo 1: Configurar .env

```bash
cd backend
copy .env.example .env
```

Edite `.env` e configure:

```bash
# Para receber notificações REAIS no celular
NTFY_TOPIC=agritech-test-seu-nome  # Use nome único!
NTFY_URL=https://ntfy.sh

# Opcional: Para usar servidor privado
# NTFY_TOKEN=seu-token-secreto
```

### Passo 2: Instalar app ntfy no celular

**Android:**
- https://play.google.com/store/apps/details?id=io.heckel.ntfy

**iPhone:**
- https://apps.apple.com/us/app/ntfy/id1625396347

### Passo 3: Inscrever-se no tópico

1. Abra o app ntfy
2. Toque em "+"
3. Digite: `agritech-test-seu-nome` (mesmo nome do .env)
4. Toque em "Subscribe"

### Passo 4: Executar testes

```bash
# Windows
backend\test_notifications.bat

# Linux/Mac
cd backend
python -m pytest api/test_integration_notifications.py -v -s
```

---

## 📱 O Que Você Vai Receber

Durante o teste, você receberá **5 notificações** no celular:

### 1. 🔴 Temperatura Alta (32.5°C)
```
🔴 CRÍTICO: Temperatura Alta: 32.5°C

Cenário de Teste: Temperatura Alta
Valor: 32.5°C
Severidade: critical

⚠️ AÇÃO IMEDIATA NECESSÁRIA
Plantas podem morrer em 2-3 horas.
```

### 2. 🔵 Temperatura Baixa (14.0°C)
```
🔵 CRÍTICO: Temperatura Baixa: 14.0°C

Valor: 14.0°C
Severidade: critical
```

### 3. ⚠️ Temperatura Aviso (27.0°C)
```
⚠️ PREVENTIVO: Temperatura Aviso: 27.0°C

Valor: 27.0°C
Severidade: preventive
```

### 4. 🧪 pH Baixo (4.2)
```
🧪 CRÍTICO: pH Baixo: 4.2

Valor: 4.2
Severidade: critical
```

### 5. ⚡ EC Alta (3.5 mS/cm)
```
⚡ CRÍTICO: EC Alta: 3.5

Valor: 3.5 mS/cm
Severidade: critical
```

---

## 🧪 Cenários Testados

### ✅ Teste 1: Dados Normais (Sem Alertas)
**Dados:**
- Temperatura: 22.5°C (normal)
- Humidade: 65% (normal)
- pH: 6.2 (normal)
- EC: 1.8 mS/cm (normal)

**Resultado esperado:** ✅ Nenhum alerta disparado

---

### 🔴 Teste 2: Temperatura Crítica Alta
**Dados:**
- Temperatura: **32.5°C** (limite: 28°C)

**Resultado esperado:**
- ✅ Alerta crítico disparado
- ✅ Notificação enviada para TODOS os canais disponíveis
- ✅ Mensagem: "AÇÃO IMEDIATA NECESSÁRIA"

---

### 🔵 Teste 3: Temperatura Crítica Baixa
**Dados:**
- Temperatura: **14.0°C** (limite: 16°C)

**Resultado esperado:**
- ✅ Alerta crítico disparado
- ✅ Risco de morte das plantas

---

### ⚠️ Teste 4: Temperatura em Aviso (Preventivo)
**Dados:**
- Temperatura: **27.0°C** (margem: 1°C antes do crítico)

**Resultado esperado:**
- ✅ Alerta **PREVENTIVO** disparado (apenas para Silver/Gold/Platinum)
- ❌ Bronze tier NÃO recebe (sem preventive_alerts)

---

### 🧪 Teste 5: pH Crítico
**Dados:**
- pH: **4.2** (limite: 5.0)

**Resultado esperado:**
- ✅ Alerta URGENTE (pode matar plantas em 6 horas)
- ✅ Prioridade máxima

---

### ⚡ Teste 6: EC Crítica
**Dados:**
- EC: **3.5 mS/cm** (limite: 3.0)

**Resultado esperado:**
- ✅ Alerta crítico (queima de raízes)
- ✅ Ação imediata necessária

---

### 🚨 Teste 7: Múltiplos Sensores Críticos
**Dados:**
- Temperatura: 33.0°C (CRÍTICO)
- Humidade: 90% (CRÍTICO)
- pH: 4.0 (CRÍTICO)
- EC: 3.8 mS/cm (CRÍTICO)

**Resultado esperado:**
- ✅ **≥3 alertas** disparados
- ✅ Emergência total
- ✅ Múltiplas notificações enviadas

---

### ⏱️ Teste 8: Escalação de Alertas
**Cenário:**
1. Alerta crítico enviado às 10:00
2. Problema NÃO resolvido
3. 15 minutos depois (10:15)...

**Resultado esperado:**
- ✅ Alerta **ESCALA** automaticamente
- ✅ Mensagem: "ALERTA NÃO RESOLVIDO - ESCALANDO"
- ✅ Próxima escalação: 30 minutos (2x)

---

### 🎖️ Teste 9: Roteamento por Tier

#### 🥉 Bronze (€49/mês)
- ✅ Alertas críticos
- ❌ Alertas preventivos
- ❌ Escalação
- Canais: Email + Console

#### 🥈 Silver (€199/mês)
- ✅ Alertas críticos
- ✅ Alertas preventivos
- ❌ Escalação
- Canais: Email + SMS + Console

#### 🥇 Gold (€499/mês)
- ✅ Alertas críticos
- ✅ Alertas preventivos
- ✅ Escalação
- Canais: Email + SMS + WhatsApp + ntfy + Console

#### 💎 Platinum (€799/mês)
- ✅ Alertas críticos
- ✅ Alertas preventivos
- ✅ Escalação
- ✅ Suporte remoto
- Canais: TODOS (Email, SMS, WhatsApp, ntfy, Phone, Console)

---

### ⏱️ Teste 10: Cooldown Anti-Spam
**Cenário:**
- Enviar 5 notificações idênticas em 10 segundos

**Resultado esperado:**
- ✅ Apenas **1 notificação** enviada
- ✅ 4 bloqueadas pelo cooldown (15 minutos)
- ✅ Previne spam

---

## 📊 Resultado dos Testes

### ✅ Sucesso Total
```bash
====================================
✅ SUCESSO: Todos os testes passaram!
====================================

Verificado:
  ✅ Regras detectam problemas nos sensores
  ✅ Alertas são gerados corretamente
  ✅ Escalação funciona após tempo de espera
  ✅ Cooldown previne spam
  ✅ Tiers respeitam limites de features
  ✅ Notificações enviadas via ntfy

📱 VERIFIQUE SEU CELULAR!
   Você deve ter recebido 5 notificações de teste.
```

### ❌ Se Algum Teste Falhar

**Problema: "NTFY_TOPIC não configurado"**
```bash
# Solução:
cd backend
notepad .env
# Adicione: NTFY_TOPIC=agritech-test
```

**Problema: "Nenhuma notificação recebida"**
```bash
# Verificações:
1. App ntfy instalado no celular? ✅
2. Inscrito no tópico correto? ✅
3. Celular conectado à internet? ✅
4. Tópico no .env igual ao do app? ✅
```

**Problema: "Regras não dispararam alerta"**
```bash
# Verificar configuração:
cd backend/api
python -c "from rule_engine import RuleEngine; e = RuleEngine(); print(e.get_rules())"

# Deve mostrar regras de temperatura, pH, EC, etc.
```

---

## 🔧 Modo de Debug

Para ver TUDO que está acontecendo:

```bash
cd backend/api
python -m pytest test_integration_notifications.py -v -s --log-cli-level=DEBUG
```

Isso mostra:
- 🔍 Cada regra sendo avaliada
- 📤 Cada notificação sendo enviada
- ⏱️ Tempos de cooldown
- 🔄 Escalações de alerta

---

## 📱 Testando Canais Específicos

### Teste apenas ntfy:
```python
from notification_service import NtfyChannel

channel = NtfyChannel()
success = channel.send("Teste Manual", "Corpo da mensagem")
print(f"Enviado: {success}")
```

### Teste todos os canais disponíveis:
```python
from notification_service import NotificationService

notifier = NotificationService()
notifier.send_notification(
    "Teste Completo",
    "Testando todos os canais",
    severity="critical"
)
```

---

## 🎯 Checklist de Verificação

Antes de considerar o teste completo, confirme:

- [ ] ✅ Teste 1 passou (dados normais não geram alerta)
- [ ] ✅ Teste 2 passou (temperatura alta gera alerta)
- [ ] ✅ Teste 3 passou (temperatura baixa gera alerta)
- [ ] ✅ Teste 4 passou (alerta preventivo funciona)
- [ ] ✅ Teste 5 passou (pH crítico gera alerta)
- [ ] ✅ Teste 6 passou (EC crítica gera alerta)
- [ ] ✅ Teste 7 passou (múltiplos sensores críticos)
- [ ] ✅ Teste 8 passou (escalação após 15 minutos)
- [ ] ✅ Teste 9 passou (tiers respeitam limites)
- [ ] ✅ Teste 10 passou (cooldown previne spam)
- [ ] 📱 **Recebi 5 notificações no celular via ntfy**

---

## 🚀 Próximos Passos

### Após Teste Bem-Sucedido:

1. **Configurar outros canais (opcional):**
```bash
# WhatsApp/SMS via Twilio
TWILIO_ACCOUNT_SID=seu-sid
TWILIO_AUTH_TOKEN=seu-token
TWILIO_WHATSAPP_FROM=+14155238886
TWILIO_WHATSAPP_TO=+351XXXXXXXXX

# Email via SMTP
SMTP_HOST=smtp.gmail.com
SMTP_USER=seu-email@gmail.com
SMTP_PASS=sua-senha-app
ALERT_EMAIL_TO=destino@exemplo.com
```

2. **Testar com dados reais do InfluxDB:**
```bash
cd backend
python test_real_notification.py
```

3. **Deploy em produção:**
- Configure tópico ntfy privado (com token)
- Configure números de telefone reais
- Configure emails de produção
- Execute testes novamente

---

## 🆘 Suporte

**Problemas? Verifique:**
1. `backend/.env` - Configuração correta?
2. App ntfy instalado e inscrito no tópico?
3. Internet funcionando?
4. Logs: `backend/api/pytest.log`

**Documentos relacionados:**
- `IMMEDIATE_ACTIONS.md` - Próximos passos
- `CODE_REVIEW_feature-dashboard.md` - Análise técnica
- `backend/api/notification_service.py` - Código fonte

---

**✅ Quando todos os testes passarem e você receber as 5 notificações:**
**Seu sistema está pronto para produção!** 🎉

O sistema garantirá que você **SEMPRE** receberá alertas quando:
- Temperatura sair dos limites (16-28°C)
- pH sair dos limites (5.0-7.0)
- EC sair dos limites (1.0-3.0 mS/cm)
- Qualquer outro sensor crítico falhar
- Alertas não forem resolvidos (escalação automática)
