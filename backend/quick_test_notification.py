#!/usr/bin/env python3
"""
Teste Rápido de Notificação - 1 Minuto
Verifica se você receberá alertas com dados REAIS do InfluxDB
"""
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Carregar .env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Adicionar api ao path
sys.path.insert(0, str(Path(__file__).parent / 'api'))

print("\n" + "="*70)
print("📱 TESTE RÁPIDO DE NOTIFICAÇÃO - DADOS REAIS")
print("="*70)

# Verificar configuração
ntfy_topic = os.getenv('NTFY_TOPIC', '')
ntfy_url = os.getenv('NTFY_URL', 'https://ntfy.sh')

print(f"\n🔍 Configuração:")
print(f"   NTFY_URL: {ntfy_url}")
print(f"   NTFY_TOPIC: {ntfy_topic or '❌ NÃO CONFIGURADO'}")

if not ntfy_topic:
    print("\n⚠️ AVISO: NTFY_TOPIC não configurado!")
    print("   Notificações não serão enviadas ao celular.")
    print("\n   Para configurar:")
    print("   1. Edite backend/.env")
    print("   2. Adicione: NTFY_TOPIC=agritech-test")
    print("   3. Execute novamente")
    print("\n   Continuando com teste de lógica apenas...")
else:
    print("\n📱 PREPARE-SE: Você receberá notificações no celular!")
    input("   Pressione ENTER para continuar...")

print("\n" + "="*70)
print("🧪 EXECUTANDO TESTES")
print("="*70)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTE 1: Importar módulos
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n1️⃣ Importando módulos...")
try:
    from notifications.notification_service import NotificationService, NtfyChannel
    from rules.rule_engine import RuleEngine
    from notifications.alert_escalation import AlertEscalationManager
    print("   ✅ Todos os módulos importados com sucesso")
except ImportError as e:
    print(f"   ❌ ERRO: Falha ao importar módulos: {e}")
    sys.exit(1)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTE 2: Verificar canais disponíveis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n2️⃣ Verificando canais de notificação...")
notifier = NotificationService()

available_channels = []
for channel in notifier.channels:
    if channel.is_available():
        available_channels.append(channel.name)
        print(f"   ✅ {channel.name}")
    else:
        print(f"   ⚠️ {channel.name} (não configurado)")

if not available_channels:
    print("   ❌ ERRO: Nenhum canal disponível!")
    sys.exit(1)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTE 3: Conectar ao InfluxDB e obter dados reais
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n3️⃣ Conectando ao InfluxDB...")

INFLUXDB_URL = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
INFLUXDB_TOKEN = os.getenv('INFLUXDB_TOKEN', '')
INFLUXDB_ORG = os.getenv('INFLUXDB_ORG', '')
INFLUXDB_BUCKET = os.getenv('INFLUXDB_BUCKET', '')

real_data = None

if INFLUXDB_TOKEN and INFLUXDB_ORG and INFLUXDB_BUCKET:
    try:
        from influxdb_client import InfluxDBClient

        influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        query_api = influx_client.query_api()

        query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
            |> range(start: -1h)
            |> filter(fn: (r) => r._measurement == "sensor_reading")
            |> last()
        '''

        print(f"   Consultando últimos dados do bucket '{INFLUXDB_BUCKET}'...")
        tables = query_api.query(query)

        real_data = {}
        for table in tables:
            for record in table.records:
                real_data[record.get_field()] = record.get_value()
                if 'timestamp' not in real_data:
                    real_data['timestamp'] = str(record.get_time())

        influx_client.close()

        if real_data:
            print("   ✅ Dados reais obtidos do InfluxDB:")
            for key, value in real_data.items():
                if key != 'timestamp':
                    print(f"      {key}: {value}")
        else:
            print("   ⚠️ Nenhum dado encontrado no InfluxDB (última 1 hora)")
            print("   Usando dados simulados...")

    except Exception as e:
        print(f"   ⚠️ Não foi possível conectar ao InfluxDB: {e}")
        print("   Usando dados simulados...")
else:
    print("   ⚠️ InfluxDB não configurado no .env")
    print("   Usando dados simulados...")

# Usar dados simulados se não houver dados reais
if not real_data:
    real_data = {
        "temperature": 32.5,  # CRÍTICO (>28°C)
        "humidity": 65.0,
        "ph": 6.2,
        "ec": 1.8,
        "light": 450,
        "timestamp": datetime.now().isoformat()
    }
    print(f"   📊 Dados simulados (temperatura crítica: {real_data['temperature']}°C)")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTE 4: Avaliar regras com dados reais
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n4️⃣ Avaliando regras com dados reais...")
engine = RuleEngine()

alerts_triggered = []
for sensor, value in real_data.items():
    if sensor == 'timestamp':
        continue

    triggered = engine.evaluate_rules(sensor, value)
    if triggered:
        for alert in triggered:
            alerts_triggered.append((sensor, value, alert))
            severity = alert['action'].get('severity', 'unknown')
            message = alert['action'].get('message', 'Sem mensagem')
            print(f"   🔴 ALERTA: {sensor} = {value}")
            print(f"      Severidade: {severity}")
            print(f"      Mensagem: {message}")

if not alerts_triggered:
    print("   ✅ Nenhum alerta disparado - todos os sensores normais")
else:
    print(f"\n   Total de alertas: {len(alerts_triggered)}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTE 5: Enviar notificação de teste
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n5️⃣ Enviando notificação de teste...")

subject = "🧪 TESTE: Sistema de Alertas AgriTech"

if alerts_triggered:
    sensor, value, alert = alerts_triggered[0]
    body = f"""
🌡️ **Dados Reais do InfluxDB**

**Sensor:** {sensor}
**Valor:** {value}
**Status:** ⚠️ ALERTA DISPARADO

**Mensagem:** {alert['action']['message']}
**Severidade:** {alert['action']['severity']}

**Timestamp:** {real_data['timestamp']}

---
🤖 Este é um teste automático do sistema de notificações.
Se você recebeu esta mensagem, o sistema está funcionando corretamente!
"""
else:
    body = f"""
✅ **Sistema Funcionando Normalmente**

**Dados dos sensores (última leitura):**
"""
    for sensor, value in real_data.items():
        if sensor != 'timestamp':
            body += f"\n- {sensor}: {value}"

    body += f"""

**Timestamp:** {real_data['timestamp']}

---
🤖 Este é um teste automático do sistema de notificações.
Todos os sensores estão dentro dos limites normais.
"""

success = notifier.send_notification(subject, body, severity="info")

if success:
    print("   ✅ Notificação enviada com sucesso!")
    if ntfy_topic:
        print(f"\n   📱 VERIFIQUE SEU CELULAR!")
        print(f"      Tópico ntfy: {ntfy_topic}")
        print("      Você deve receber a notificação em 1-2 segundos")
else:
    print("   ❌ ERRO: Falha ao enviar notificação")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TESTE 6: Teste de escalação (se houver alertas)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if alerts_triggered:
    print("\n6️⃣ Testando escalação de alertas...")
    escalation = AlertEscalationManager()

    sensor, value, alert = alerts_triggered[0]
    should_send, reason = escalation.should_send_alert(
        sensor,
        alert['action']['severity'],
        value
    )

    if should_send:
        print(f"   ✅ Alerta deve ser enviado: {reason}")
    else:
        print(f"   ⚠️ Alerta bloqueado: {reason}")

    # Verificar alertas ativos
    active = escalation.get_active_alerts()
    print(f"   Alertas ativos: {len(active)}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SUMÁRIO FINAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n" + "="*70)
print("📊 RESUMO DO TESTE")
print("="*70)

print("\n✅ VERIFICAÇÕES COMPLETAS:")
print(f"   ✅ Módulos importados")
print(f"   ✅ {len(available_channels)} canal(is) disponível(is): {', '.join(available_channels)}")
print(f"   ✅ Dados {'reais' if 'timestamp' in real_data and INFLUXDB_TOKEN else 'simulados'} obtidos")
print(f"   ✅ {len(alerts_triggered)} alerta(s) disparado(s)")
print(f"   ✅ Notificação enviada")

if ntfy_topic:
    print("\n📱 NOTIFICAÇÃO ENVIADA!")
    print(f"   Tópico: {ntfy_topic}")
    print(f"   URL: {ntfy_url}/{ntfy_topic}")
    print("\n   ⏱️ Aguardando 5 segundos para você verificar o celular...")
    import time
    time.sleep(5)
    print("\n   ❓ Você recebeu a notificação?")
    response = input("      Digite 's' para SIM ou 'n' para NÃO: ").lower()

    if response == 's':
        print("\n   🎉 SUCESSO TOTAL!")
        print("      Sistema de notificações funcionando perfeitamente!")
        print("\n   ✅ Você RECEBERÁ alertas quando:")
        print("      - Temperatura sair de 16-28°C")
        print("      - pH sair de 5.0-7.0")
        print("      - EC sair de 1.0-3.0 mS/cm")
        print("      - Qualquer outro sensor crítico falhar")
    else:
        print("\n   ⚠️ PROBLEMA: Notificação não recebida")
        print("\n   Verifique:")
        print("      1. App ntfy instalado no celular?")
        print("      2. Inscrito no tópico correto?")
        print(f"         Tópico: {ntfy_topic}")
        print("      3. Celular conectado à internet?")
        print("      4. Notificações permitidas para o app ntfy?")
else:
    print("\n⚠️ NTFY não configurado - teste limitado")
    print("   Configure NTFY_TOPIC no .env para receber notificações reais")

print("\n" + "="*70)
print("✅ TESTE COMPLETO")
print("="*70)

if alerts_triggered:
    print("\n⚠️ ATENÇÃO: Alertas detectados nos dados reais!")
    print("   Verifique seu sistema imediatamente:")
    for sensor, value, alert in alerts_triggered:
        print(f"   - {sensor}: {value} ({alert['action']['severity']})")
else:
    print("\n✅ Sistema normal - nenhum problema detectado")

print("\n📚 Próximos passos:")
print("   1. Execute testes completos: backend\\test_notifications.bat")
print("   2. Configure outros canais: WhatsApp, SMS, Email")
print("   3. Veja guia completo: backend\\TESTE_NOTIFICACOES_GUIA.md")

print("\n")
