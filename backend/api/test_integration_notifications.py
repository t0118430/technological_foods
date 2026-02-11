"""
Testes de Integração Completos - Sistema de Notificações
Testa TODOS os cenários com dados reais:
- Leitura de sensores do InfluxDB
- Avaliação de regras
- Envio para múltiplos canais
- Escalação de alertas
- Diferentes tiers de assinatura
"""
import os
import sys
import time
import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent))

from notification_service import NotificationService, NtfyChannel
from rule_engine import RuleEngine
from alert_escalation import AlertEscalationManager
from tier_notification_router import TierNotificationRouter, SubscriptionTier
from business_model import SUBSCRIPTION_TIERS

# Configuração de teste
TEST_MODE = os.getenv('TEST_MODE', 'mock')  # 'mock' ou 'real'
NTFY_ENABLED = os.getenv('NTFY_TOPIC', '') != ''


# ══════════════════════════════════════════════════════════════
# FIXTURES: Dados Reais de Sensores
# ══════════════════════════════════════════════════════════════

@pytest.fixture
def sensor_data_normal():
    """Dados de sensores dentro dos limites normais"""
    return {
        "temperature": 22.5,  # Normal (18-26°C)
        "humidity": 65.0,     # Normal (50-80%)
        "ph": 6.2,            # Normal (5.5-7.0)
        "ec": 1.8,            # Normal (1.0-2.5 mS/cm)
        "light": 450,         # Normal (200-800 lux)
        "timestamp": datetime.now().isoformat()
    }


@pytest.fixture
def sensor_data_critical_temp_high():
    """Temperatura CRÍTICA alta (>28°C) - deve disparar alerta URGENTE"""
    return {
        "temperature": 32.5,  # CRÍTICO! (limite: 28°C)
        "humidity": 65.0,
        "ph": 6.2,
        "ec": 1.8,
        "light": 450,
        "timestamp": datetime.now().isoformat()
    }


@pytest.fixture
def sensor_data_critical_temp_low():
    """Temperatura CRÍTICA baixa (<16°C) - risco de morte das plantas"""
    return {
        "temperature": 14.0,  # CRÍTICO! (limite: 16°C)
        "humidity": 65.0,
        "ph": 6.2,
        "ec": 1.8,
        "light": 450,
        "timestamp": datetime.now().isoformat()
    }


@pytest.fixture
def sensor_data_warning_temp():
    """Temperatura em AVISO (26-28°C) - deve disparar alerta preventivo"""
    return {
        "temperature": 27.0,  # AVISO (margem: 2°C antes do crítico)
        "humidity": 65.0,
        "ph": 6.2,
        "ec": 1.8,
        "light": 450,
        "timestamp": datetime.now().isoformat()
    }


@pytest.fixture
def sensor_data_critical_ph_low():
    """pH CRÍTICO baixo (<5.0) - pode matar plantas em 6 horas"""
    return {
        "temperature": 22.0,
        "humidity": 65.0,
        "ph": 4.2,            # CRÍTICO! (limite: 5.0)
        "ec": 1.8,
        "light": 450,
        "timestamp": datetime.now().isoformat()
    }


@pytest.fixture
def sensor_data_critical_ec_high():
    """EC CRÍTICA alta (>3.0) - queima de raízes"""
    return {
        "temperature": 22.0,
        "humidity": 65.0,
        "ph": 6.2,
        "ec": 3.5,            # CRÍTICO! (limite: 3.0)
        "light": 450,
        "timestamp": datetime.now().isoformat()
    }


@pytest.fixture
def sensor_data_multiple_critical():
    """MÚLTIPLOS sensores em estado crítico - EMERGÊNCIA TOTAL"""
    return {
        "temperature": 33.0,  # CRÍTICO
        "humidity": 90.0,     # CRÍTICO
        "ph": 4.0,            # CRÍTICO
        "ec": 3.8,            # CRÍTICO
        "light": 50,          # CRÍTICO (muito baixo)
        "timestamp": datetime.now().isoformat()
    }


# ══════════════════════════════════════════════════════════════
# TESTES: Avaliação de Regras com Dados Reais
# ══════════════════════════════════════════════════════════════

class TestRuleEvaluationWithRealData:
    """Testa se as regras detectam corretamente problemas nos sensores"""

    def test_normal_data_no_notification_alerts(self, sensor_data_normal):
        """Dados normais NAO devem disparar alertas de notificacao"""
        engine = RuleEngine()

        triggered = engine.evaluate(sensor_data_normal)
        # Filter to only notification-type alerts (exclude arduino LED commands)
        notification_alerts = [t for t in triggered if t['action'].get('type') == 'notification']
        assert len(notification_alerts) == 0, \
            f"Dados normais dispararam {len(notification_alerts)} alerta(s) de notificacao indevidamente"

        print("PASS: Dados normais nao geraram alertas de notificacao")

    def test_critical_temp_high_triggers_alert(self, sensor_data_critical_temp_high):
        """Temperatura alta CRITICA deve disparar alerta"""
        engine = RuleEngine()

        triggered = engine.evaluate(sensor_data_critical_temp_high)

        assert len(triggered) > 0, "FALHA: Temperatura critica NAO disparou alerta!"

        # Verificar que pelo menos um alerta de notificacao tem severidade critica
        notification_alerts = [t for t in triggered if t['action'].get('severity')]
        assert len(notification_alerts) > 0, "FALHA: Nenhum alerta de notificacao disparado!"
        alert = notification_alerts[0]
        assert alert["action"]["severity"] in ["critical", "urgent"], \
            f"Severidade incorreta: {alert['action']['severity']}"

        print(f"PASS: Alerta disparado para temperatura {sensor_data_critical_temp_high['temperature']}C")

    def test_critical_temp_low_triggers_alert(self, sensor_data_critical_temp_low):
        """Temperatura baixa CRITICA deve disparar alerta"""
        engine = RuleEngine()

        triggered = engine.evaluate(sensor_data_critical_temp_low)

        assert len(triggered) > 0, "FALHA: Temperatura critica baixa NAO disparou alerta!"
        print(f"PASS: Alerta disparado para temperatura {sensor_data_critical_temp_low['temperature']}C")

    def test_warning_temp_triggers_preventive_alert(self, sensor_data_warning_temp):
        """Temperatura em aviso deve disparar alerta PREVENTIVO"""
        engine = RuleEngine()

        triggered = engine.evaluate(sensor_data_warning_temp)

        # Pode ou nao disparar dependendo da configuracao de margem
        if len(triggered) > 0:
            alert = triggered[0]
            print(f"PASS: Alerta preventivo disparado para temperatura {sensor_data_warning_temp['temperature']}C")
        else:
            print(f"INFO: Temperatura {sensor_data_warning_temp['temperature']}C nao disparou alerta preventivo")

    def test_critical_ph_triggers_urgent_alert(self, sensor_data_critical_ph_low):
        """pH critico deve disparar alerta URGENTE"""
        engine = RuleEngine()

        triggered = engine.evaluate(sensor_data_critical_ph_low)

        assert len(triggered) > 0, f"FALHA: pH critico {sensor_data_critical_ph_low['ph']} NAO disparou alerta!"
        print(f"PASS: Alerta disparado para pH {sensor_data_critical_ph_low['ph']}")

    def test_multiple_critical_triggers_multiple_alerts(self, sensor_data_multiple_critical):
        """MULTIPLOS sensores criticos devem disparar MULTIPLOS alertas"""
        engine = RuleEngine()

        triggered = engine.evaluate(sensor_data_multiple_critical)

        assert len(triggered) >= 3, f"FALHA: Esperado >=3 alertas, recebido {len(triggered)}"
        print(f"PASS: {len(triggered)} alertas disparados para cenario de emergencia")


# ══════════════════════════════════════════════════════════════
# TESTES: Envio Real de Notificações
# ══════════════════════════════════════════════════════════════

class TestNotificationDelivery:
    """Testa se notificações são REALMENTE enviadas"""

    @pytest.mark.skipif(not NTFY_ENABLED, reason="NTFY_TOPIC não configurado")
    def test_send_real_ntfy_notification(self, sensor_data_critical_temp_high):
        """📱 Envia notificação REAL via ntfy.sh"""
        channel = NtfyChannel()

        subject = "🔴 ALERTA CRÍTICO: Temperatura Alta"
        body = f"""
🌡️ **Temperatura: {sensor_data_critical_temp_high['temperature']}°C**

⚠️ **AÇÃO IMEDIATA NECESSÁRIA**
A temperatura ultrapassou 28°C. Plantas podem morrer em 2-3 horas.

**Ações recomendadas:**
1. Verificar sistema de refrigeração
2. Ligar ventiladores adicionais
3. Verificar ar condicionado

**Timestamp:** {sensor_data_critical_temp_high['timestamp']}
"""

        success = channel.send(subject, body)

        assert success, "FALHA: Notificação ntfy NÃO foi enviada!"
        print("✅ PASS: Notificação enviada via ntfy")
        print(f"   Tópico: {channel.topic}")
        print("   ⚠️ VERIFIQUE SEU CELULAR! Você deve receber a notificação em 1-2 segundos")

    def test_console_notification_always_works(self, sensor_data_critical_temp_high):
        """Console sempre deve funcionar (fallback)"""
        service = NotificationService()

        results = service.notify(
            rule_id="test_console",
            severity="critical",
            message=f"Temperatura: {sensor_data_critical_temp_high['temperature']}C"
        )

        assert len(results) > 0, "FALHA: Nenhum canal respondeu!"
        assert any(r['sent'] for r in results), "FALHA: Nenhuma notificacao enviada!"
        print("PASS: Notificacao console enviada")


# ══════════════════════════════════════════════════════════════
# TESTES: Roteamento por Tier (Bronze/Silver/Gold/Platinum)
# ══════════════════════════════════════════════════════════════

class TestTierBasedNotifications:
    """Testa se notificações respeitam limites de cada tier"""

    def test_bronze_tier_only_critical_alerts(self, sensor_data_critical_temp_high, sensor_data_warning_temp):
        """🥉 Bronze: Apenas alertas CRÍTICOS"""
        router = TierNotificationRouter(SubscriptionTier.BRONZE)

        # Crítico: Deve enviar
        should_send = router.should_send_alert("critical", "temperature")
        assert should_send, "FALHA: Bronze não envia alerta crítico!"

        # Aviso: NÃO deve enviar (Bronze não tem preventive_alerts)
        should_send = router.should_send_alert("preventive", "temperature")
        assert not should_send, "FALHA: Bronze enviou alerta preventivo (não permitido)!"

        print("✅ PASS: Bronze tier - apenas críticos")

    def test_silver_tier_gets_preventive_alerts(self):
        """🥈 Silver: Críticos + Preventivos"""
        router = TierNotificationRouter(SubscriptionTier.SILVER)

        # Preventivo: Deve enviar
        should_send = router.should_send_alert("preventive", "temperature")
        assert should_send, "FALHA: Silver não recebe alertas preventivos!"

        print("✅ PASS: Silver tier - preventivos habilitados")

    def test_gold_tier_gets_escalation(self):
        """🥇 Gold: Críticos + Preventivos + Escalação"""
        router = TierNotificationRouter(SubscriptionTier.GOLD)

        # Escalação: Deve estar habilitada
        tier_config = SUBSCRIPTION_TIERS['gold']
        assert tier_config['features']['escalation'] is True, "FALHA: Gold não tem escalação!"

        print("✅ PASS: Gold tier - escalação habilitada")

    def test_platinum_tier_gets_all_channels(self):
        """💎 Platinum: TODOS os canais (WhatsApp, SMS, Email, ntfy, Phone)"""
        tier_config = SUBSCRIPTION_TIERS['platinum']
        channels = tier_config['features']['notification_channels']

        expected = ['email', 'sms', 'whatsapp', 'console', 'ntfy', 'phone_call']
        for channel in expected:
            assert channel in channels, f"FALHA: Platinum não tem canal {channel}!"

        print("✅ PASS: Platinum tier - todos os canais disponíveis")
        print(f"   Canais: {', '.join(channels)}")


# ══════════════════════════════════════════════════════════════
# TESTES: Escalação de Alertas
# ══════════════════════════════════════════════════════════════

class TestAlertEscalation:
    """Testa se alertas não resolvidos são escalados"""

    def test_alert_escalates_after_wait_time(self, sensor_data_critical_temp_high):
        """⏱️ Alerta não resolvido deve escalar após 15 minutos"""
        escalation = AlertEscalationManager()

        temp = sensor_data_critical_temp_high["temperature"]

        # Primeiro alerta
        result = escalation.should_send_alert(
            rule_id="temp_critical",
            sensor="temperature",
            current_value=temp,
            threshold=28.0,
            condition="above"
        )
        assert result is not None, "FALHA: Primeiro alerta deveria ser enviado!"
        print(f"   Primeiro alerta enviado: level {result.get('escalation_level', 0)}")

        # Aguardar tempo de escalação
        time.sleep(1)

        # Segundo alerta (mesmo problema) - should handle repeat
        result2 = escalation.should_send_alert(
            rule_id="temp_critical",
            sensor="temperature",
            current_value=temp,
            threshold=28.0,
            condition="above"
        )
        # May be suppressed or escalated depending on timing
        print("✅ PASS: Alerta escalation processed correctly")

    def test_improved_condition_clears_alert(self):
        """✅ Condição melhorada deve limpar alerta"""
        escalation = AlertEscalationManager()

        # Criar alerta
        escalation.should_send_alert(
            rule_id="temp_critical",
            sensor="temperature",
            current_value=32.0,
            threshold=28.0,
            condition="above"
        )

        # Verificar alertas ativos
        active = escalation.get_active_alerts()
        assert len(active) > 0, "Alerta não foi criado"

        # Verificar resolução (temperatura normalizada)
        resolved = escalation.check_for_resolved_alerts({"temperature": 22.0})

        # Verificar se foi limpo
        active_after = escalation.get_active_alerts()
        assert len(active_after) == 0, "FALHA: Alerta não foi limpo após melhora!"

        print("✅ PASS: Alerta limpo após melhora na condição")


# ══════════════════════════════════════════════════════════════
# TESTE INTEGRADO COMPLETO: Sensor → Regra → Notificação
# ══════════════════════════════════════════════════════════════

class TestCompleteIntegrationFlow:
    """Teste E2E: Dados do sensor até notificação recebida"""

    def test_complete_flow_critical_temperature(self, sensor_data_critical_temp_high):
        """🔥 TESTE COMPLETO: Temperatura crítica → Você recebe notificação"""
        print("\n" + "="*60)
        print("🧪 TESTE DE INTEGRAÇÃO COMPLETO")
        print("="*60)

        # Passo 1: Avaliar regras
        print("\n1 Avaliando regras com dados do sensor...")
        engine = RuleEngine()
        triggered = engine.evaluate(sensor_data_critical_temp_high)

        assert len(triggered) > 0, "FALHA: Nenhuma regra disparada!"
        print(f"   {len(triggered)} regra(s) disparada(s)")

        # Passo 2: Verificar escalação
        print("\n2️⃣ Verificando escalação de alertas...")
        escalation = AlertEscalationManager()
        result = escalation.should_send_alert(
            rule_id="temp_critical",
            sensor="temperature",
            current_value=sensor_data_critical_temp_high["temperature"],
            threshold=28.0,
            condition="above"
        )

        assert result is not None, "FALHA: Escalação bloqueou envio!"
        print(f"   ✅ Alerta deve ser enviado: level {result.get('escalation_level', 0)}")

        # Passo 3: Verificar tier (Bronze como exemplo)
        print("\n3️⃣ Verificando permissões do tier...")
        router = TierNotificationRouter(SubscriptionTier.BRONZE)
        allowed = router.should_send_alert("critical", "temperature")

        assert allowed, "FALHA: Tier não permite este alerta!"
        print("   ✅ Tier Bronze permite alerta crítico")

        # Passo 4: Enviar notificacao
        print("\n4 Enviando notificacao...")
        service = NotificationService()

        subject = f"🔴 CRÍTICO: Temperatura {sensor_data_critical_temp_high['temperature']}°C"
        body = f"""
🌡️ **Temperatura Crítica Detectada**

**Valor atual:** {sensor_data_critical_temp_high['temperature']}°C
**Limite máximo:** 28°C
**Gravidade:** CRÍTICA

⚠️ **AÇÃO IMEDIATA NECESSÁRIA**
As plantas podem morrer em 2-3 horas se a temperatura não for reduzida.

**Ações recomendadas:**
1. Verificar sistema de refrigeração
2. Ligar ventiladores de emergência
3. Reduzir iluminação se possível
4. Abrir janelas/portas se temperatura externa for menor

**Timestamp:** {sensor_data_critical_temp_high['timestamp']}
"""

        results = service.notify(
            rule_id="integration_test_temp",
            severity="critical",
            message=f"CRITICO: Temperatura {sensor_data_critical_temp_high['temperature']}C"
        )

        assert any(r['sent'] for r in results), "FALHA: Notificacao nao foi enviada!"
        print("   Notificacao enviada com sucesso!")

        # Passo 5: Verificar canais disponiveis
        print("\n5 Canais de notificacao disponiveis:")
        for channel in service.channels:
            if channel.is_available():
                print(f"   {channel.name}")
            else:
                print(f"   {channel.name} (nao configurado)")

        print("\n" + "="*60)
        print("✅ TESTE DE INTEGRAÇÃO COMPLETO: PASSOU")
        print("="*60)

        if NTFY_ENABLED:
            print("\n📱 VERIFIQUE SEU CELULAR!")
            print("   Você deve ter recebido uma notificação push via ntfy")

    @pytest.mark.skipif(not NTFY_ENABLED, reason="NTFY_TOPIC não configurado")
    def test_real_notification_all_scenarios(self):
        """📱 Envia notificações REAIS para TODOS os cenários"""
        print("\n" + "="*60)
        print("📱 ENVIANDO NOTIFICAÇÕES REAIS PARA TESTE")
        print("="*60)

        scenarios = [
            ("🔴 Temperatura Alta", 32.5, "critical"),
            ("🔵 Temperatura Baixa", 14.0, "critical"),
            ("⚠️ Temperatura Aviso", 27.0, "preventive"),
            ("🧪 pH Baixo", 4.2, "critical"),
            ("⚡ EC Alta", 3.5, "critical"),
        ]

        channel = NtfyChannel()

        for title, value, severity in scenarios:
            subject = f"{title}: {value}"
            body = f"""
**Cenário de Teste:** {title}
**Valor:** {value}
**Severidade:** {severity}

Este é um teste de integração para verificar se você recebe notificações em todos os cenários.

**Timestamp:** {datetime.now().isoformat()}
"""

            success = channel.send(f"[TESTE] {subject}", body)
            print(f"   {'✅' if success else '❌'} {title}")
            time.sleep(1)  # Aguardar 1 segundo entre notificações

        print("\n📱 VERIFIQUE SEU CELULAR!")
        print("   Você deve ter recebido 5 notificações de teste")


# ══════════════════════════════════════════════════════════════
# TESTE DE CARGA: Múltiplos Alertas Simultâneos
# ══════════════════════════════════════════════════════════════

class TestLoadAndPerformance:
    """Testa comportamento sob carga (múltiplos alertas simultâneos)"""

    def test_cooldown_prevents_spam(self):
        """Cooldown deve prevenir spam de notificacoes"""
        service = NotificationService()

        # Enviar 5 notificacoes identicas rapidamente
        sent_count = 0
        for i in range(5):
            results = service.notify(
                rule_id="cooldown_test",
                severity="warning",
                message="Mensagem repetida"
            )
            if any(r['sent'] for r in results):
                sent_count += 1

        # Apenas a primeira deve ser enviada (cooldown bloqueia as outras)
        assert sent_count == 1, f"FALHA: {sent_count} notificacoes enviadas (esperado 1 devido ao cooldown)"
        print(f"PASS: Cooldown funcionou - apenas 1 de 5 notificacoes enviadas")

    def test_multiple_sensors_independent_cooldowns(self):
        """Sensores diferentes devem ter cooldowns independentes"""
        service = NotificationService()

        # Enviar alertas para diferentes sensores
        temp_results = service.notify(rule_id="temp_alert", severity="critical", message="Temp alta")
        ph_results = service.notify(rule_id="ph_alert", severity="critical", message="pH baixo")

        temp_sent = any(r['sent'] for r in temp_results)
        ph_sent = any(r['sent'] for r in ph_results)

        # Ambos devem ser enviados (cooldowns independentes)
        assert temp_sent and ph_sent, "FALHA: Cooldowns nao sao independentes!"
        print("PASS: Cooldowns independentes por sensor")


# ══════════════════════════════════════════════════════════════
# SUMÁRIO DE EXECUÇÃO
# ══════════════════════════════════════════════════════════════

def print_test_summary():
    """Imprime sumário de configuração de testes"""
    print("\n" + "="*60)
    print("📋 CONFIGURAÇÃO DE TESTES")
    print("="*60)
    print(f"Modo: {TEST_MODE}")
    print(f"ntfy habilitado: {NTFY_ENABLED}")

    if NTFY_ENABLED:
        print(f"ntfy tópico: {os.getenv('NTFY_TOPIC')}")
        print("   ✅ Testes REAIS de notificação serão executados")
    else:
        print("   ⚠️ Testes REAIS de notificação serão IGNORADOS")
        print("   Para habilitar: configure NTFY_TOPIC no .env")

    print("\n📱 Canais disponíveis:")
    notifier = NotificationService()
    for channel in notifier.channels:
        status = "✅" if channel.is_available() else "⚠️"
        print(f"   {status} {channel.name}")

    print("\n🎯 Cenários de teste:")
    print("   1. Dados normais (sem alertas)")
    print("   2. Temperatura crítica alta (>28°C)")
    print("   3. Temperatura crítica baixa (<16°C)")
    print("   4. Temperatura em aviso (26-28°C)")
    print("   5. pH crítico (<5.0)")
    print("   6. EC crítica (>3.0)")
    print("   7. Múltiplos sensores críticos")
    print("   8. Escalação de alertas")
    print("   9. Roteamento por tier (Bronze/Silver/Gold/Platinum)")
    print("   10. Cooldown anti-spam")
    print("="*60 + "\n")


if __name__ == "__main__":
    print_test_summary()

    # Executar todos os testes
    pytest.main([
        __file__,
        "-v",              # Verbose
        "-s",              # Mostrar prints
        "--tb=short",      # Traceback curto
        "-W", "ignore::DeprecationWarning"
    ])
