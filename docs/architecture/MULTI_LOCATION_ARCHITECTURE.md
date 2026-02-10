# 🌐 Multi-Location Network Architecture

**Central Porto Server → Remote Sites (Lisbon, Algarve, etc.)**

---

## 🗺️ **Your Expansion Strategy**

> *"Starting in Porto, can visit Lisbon and fix whatever in 2 weeks, connect production to my central"*

**Perfect approach!** Here's the architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                 CENTRAL SERVER (Porto)                       │
│         Quarter Bedroom Size (~2m² rack)                     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Main Server (Mini PC or Rack Server)              │    │
│  │  - PostgreSQL (central database)                   │    │
│  │  - InfluxDB cluster (all location data)            │    │
│  │  - Business Intelligence Dashboard                  │    │
│  │  - Client Management System                         │    │
│  │  - Data Marketplace API                            │    │
│  │  - VPN Server (WireGuard)                          │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Network Equipment                                  │    │
│  │  - Router with VPN (OpenWrt)                       │    │
│  │  - Network switch (managed, 24-port)               │    │
│  │  - UPS (uninterruptible power supply)             │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↓ ↓ ↓
            ┌───────────────┼───────────────┐
            ↓               ↓               ↓
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   LISBON     │ │   ALGARVE    │ │   BRAGA      │
    │   Site #2    │ │   Site #3    │ │   Site #4    │
    └──────────────┘ └──────────────┘ └──────────────┘

Each Remote Site:
- Raspberry Pi 4 (local monitoring)
- Arduino sensors (greenhouse data)
- VPN tunnel to Porto (encrypted)
- Local data backup (SD card + USB)
- Auto-sync to central server
```

---

## 🔐 **Secure VPN Connection (WireGuard)**

### **Why VPN?**
- ✅ Encrypted traffic (no one can sniff sensor data)
- ✅ Access from anywhere (you in Porto, site in Lisbon)
- ✅ No public IP needed (works behind NAT)
- ✅ Low overhead (fast, battery-friendly)

### **Setup WireGuard**

**1. Central Server (Porto) - VPN Server**

```bash
# Install WireGuard on central server
sudo apt install wireguard

# Generate server keys
wg genkey | tee server_private.key | wg pubkey > server_public.key

# Configure server: /etc/wireguard/wg0.conf
[Interface]
Address = 10.200.0.1/24
ListenPort = 51820
PrivateKey = <server_private.key>

# Remote site 1 (Lisbon)
[Peer]
PublicKey = <lisbon_public.key>
AllowedIPs = 10.200.0.2/32

# Remote site 2 (Algarve)
[Peer]
PublicKey = <algarve_public.key>
AllowedIPs = 10.200.0.3/32

# Start WireGuard
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0
```

**2. Remote Site (Lisbon) - VPN Client**

```bash
# On Raspberry Pi at Lisbon site
sudo apt install wireguard

# Generate client keys
wg genkey | tee lisbon_private.key | wg pubkey > lisbon_public.key

# Configure: /etc/wireguard/wg0.conf
[Interface]
Address = 10.200.0.2/24
PrivateKey = <lisbon_private.key>

[Peer]
PublicKey = <server_public.key>
Endpoint = your-porto-server.duckdns.org:51820
AllowedIPs = 10.200.0.0/24
PersistentKeepalive = 25

# Start VPN
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0
```

**3. Test Connection**

```bash
# From Lisbon Pi, ping Porto server
ping 10.200.0.1

# From Porto server, access Lisbon Pi
ssh pi@10.200.0.2

# Check VPN status
sudo wg show
```

---

## 📊 **Data Synchronization Strategy**

### **Hybrid: Local + Central Storage**

```python
# On each remote site (Lisbon, Algarve, etc.)

class RemoteSiteSync:
    """
    Sync local sensor data to central Porto server
    """

    def __init__(self):
        self.site_id = "lisbon_1"  # Unique site identifier
        self.central_api = "http://10.200.0.1:3001"  # Central server VPN IP
        self.local_influx = "http://localhost:8086"  # Local InfluxDB
        self.sync_interval = 60  # Sync every 60 seconds

    def sync_sensor_data(self):
        """
        Read from local InfluxDB, send to central server
        """

        # Query last hour of data from local InfluxDB
        query = '''
            from(bucket: "hydroponics")
              |> range(start: -1h)
              |> filter(fn: (r) => r["_measurement"] == "sensor_reading")
        '''

        local_data = self.query_local_influx(query)

        # Send to central server with site_id tag
        for reading in local_data:
            reading['site_id'] = self.site_id
            self.send_to_central(reading)

    def send_to_central(self, data):
        """
        POST sensor data to central server API
        Includes retry logic for network failures
        """

        try:
            response = requests.post(
                f"{self.central_api}/api/data/remote",
                json=data,
                timeout=10
            )

            if response.status_code == 201:
                logger.info(f"Data synced to central: {data}")
            else:
                logger.error(f"Sync failed: {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error, will retry: {e}")
            # Store failed sync in queue for retry
            self.queue_for_retry(data)
```

### **Offline Resilience**

If VPN goes down (internet outage):
1. ✅ **Local storage continues** - Raspberry Pi saves to local InfluxDB
2. ✅ **Queue syncs** - Failed uploads stored in local queue
3. ✅ **Auto-retry** - When VPN reconnects, sync backlog automatically
4. ✅ **No data loss** - Local SD card + USB backup

---

## 🏠 **Quarter Bedroom Server Security**

> *"How safe could be in a server quarter bedroom size?"*

### **Physical Security**

```
Quarter Bedroom Setup (2m² rack space):

┌──────────────────────────────────────┐
│  Server Rack (12U, 60cm × 60cm)     │
│                                      │
│  [1U] Network Switch                │
│  [2U] Main Server (Mini PC)         │
│  [1U] UPS (Battery Backup)          │
│  [2U] NAS (Data Storage)            │
│  [1U] VPN Router                    │
│  [5U] Free space / Future expansion │
│                                      │
│  + Lock (physical security)         │
│  + Temperature monitor              │
│  + Smoke detector                   │
└──────────────────────────────────────┘

Cost: €1,500-2,500 total
```

### **Network Security Layers**

```
Internet (Public)
    ↓
┌─────────────────────────────────────┐
│ Layer 1: ISP Router (Firewall)     │ ← Only port 51820 (WireGuard) open
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Layer 2: pfSense Firewall           │ ← Block all except VPN + HTTPS
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Layer 3: VPN (WireGuard)            │ ← Encrypted tunnel only
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Layer 4: Internal Network           │ ← 10.200.0.0/24 (private)
│ - Central server                    │
│ - Database                          │
│ - Dashboard                         │
└─────────────────────────────────────┘
```

### **Security Checklist**

| Security Measure | Priority | Implementation |
|------------------|----------|----------------|
| **🔐 VPN Encryption** | CRITICAL | WireGuard (ChaCha20) |
| **🔒 Firewall** | CRITICAL | pfSense or UFW |
| **🔑 SSH Keys Only** | CRITICAL | No password auth |
| **📡 Fail2Ban** | HIGH | Auto-ban brute force |
| **📊 Monitoring** | HIGH | Prometheus + Grafana |
| **⚡ UPS** | HIGH | Prevent data corruption |
| **🔥 Smoke Detector** | MEDIUM | Fire protection |
| **🌡️ Temperature Monitor** | MEDIUM | Overheat alerts |
| **🔒 Physical Lock** | MEDIUM | Rack with key |
| **💾 Daily Backups** | CRITICAL | Encrypted off-site |

---

## 🛡️ **GDPR Compliance (Critical for EU)**

### **Data Storage Rules**

| Data Type | Storage Location | Retention | Encryption |
|-----------|------------------|-----------|------------|
| **Customer personal data** | Portugal only (GDPR) | 3 years | AES-256 |
| **Sensor data** | Porto + remote sites | 90 days local, 1 year central | TLS in transit |
| **Client contracts** | Porto central | 7 years (legal requirement) | Encrypted at rest |
| **Lead data** | Porto central | Until consent withdrawn | Hashed emails |

### **Server Location Matters**

✅ **SAFE: Home server in Porto, Portugal**
- EU-based (GDPR compliant)
- No foreign jurisdiction
- Full data control

❌ **RISKY: Cloud servers outside EU**
- US servers (CLOUD Act issues)
- China servers (data access laws)
- No control over physical access

**Your quarter-bedroom server = MORE secure than cloud!**

---

## 📡 **Remote Site Monitoring**

### **Central Dashboard (Porto Server)**

```
http://10.200.0.1:3001/locations

┌─────────────────────────────────────────────────────────┐
│  🗺️ Multi-Location Dashboard                           │
├─────────────────────────────────────────────────────────┤
│  Porto HQ        [●] Online   | Last: 2s ago            │
│  - 12 crops active                                      │
│  - Sensors: 8/8 online (100%)                           │
│  - Revenue: €1,200/month                                │
│                                                          │
│  Lisbon Site #1  [●] Online   | Last: 5s ago            │
│  - 8 crops active                                       │
│  - Sensors: 6/6 online (100%)                           │
│  - Revenue: €800/month                                  │
│                                                          │
│  Algarve Site #2 [○] Offline  | Last: 2h ago ⚠️         │
│  - Network issue detected                               │
│  - Local backup active                                  │
│  - Action: Call site manager                            │
└─────────────────────────────────────────────────────────┘
```

### **Automatic Failover**

If Lisbon site loses internet:
1. ⚠️ Alert sent to Porto (via 4G backup, SMS, ntfy)
2. 💾 Local Raspberry Pi continues monitoring
3. 🔄 Auto-sync when connection restored
4. 📞 You get notification: "Lisbon offline, local backup active"

---

## 🚗 **Visit Schedule (Porto → Lisbon)**

> *"Can visit Lisbon and fix whatever in 2 weeks"*

**Recommended Schedule:**

```
Week 1-2: Porto site (establish baseline)
Week 3: Visit Lisbon (2-day trip)
  - Day 1: Install sensors, configure Pi, test VPN
  - Day 2: Train local contact, verify remote monitoring

Week 4: Porto (monitor both locations remotely)

Week 5-6: Algarve expansion (4-day trip)
  - Day 1: Travel, site survey
  - Day 2-3: Installation
  - Day 4: Training, return

Week 7-8: Porto (monitor all 3 locations)

Monthly: 1-day visit to each site (calibration check)
```

**Remote vs On-Site:**
- 90% monitoring: Remote from Porto (via VPN)
- 10% on-site: Calibration, hardware fixes, client meetings

---

## 💰 **Multi-Location Business Model**

### **Revenue Per Location**

| Location | Clients | MRR | Service Visits/Month | Total/Month |
|----------|---------|-----|---------------------|-------------|
| **Porto** | 10 | €1,500 | €400 | €1,900 |
| **Lisbon** | 8 | €1,200 | €300 | €1,500 |
| **Algarve** | 6 | €900 | €250 | €1,150 |
| **TOTAL** | 24 | €3,600 | €950 | **€4,550/month** |

**Annual:** €54,600/year (3 locations)

### **Central Server Benefits**

✅ **Single dashboard** - Monitor all locations
✅ **Shared knowledge** - Porto data helps Lisbon clients
✅ **Efficiency** - One system, multiple sites
✅ **Data marketplace** - Aggregate data = higher value
✅ **Scalability** - Add site #4, #5 easily

---

## 🔧 **Hardware Recommendations**

### **Central Server (Porto) - Quarter Bedroom**

**Option 1: Budget (€1,500)**
```
- Mini PC (Intel NUC 11 Pro): €600
  - 16GB RAM, 500GB SSD
  - Runs PostgreSQL + InfluxDB
- Synology NAS DS220+ (backup): €400
- UPS (APC 650VA): €120
- Network switch (8-port): €80
- Total: €1,200 + misc cables
```

**Option 2: Professional (€3,500)**
```
- Dell PowerEdge T140 (tower server): €1,500
  - 32GB RAM, 2TB SSD
  - RAID 1 (redundancy)
- Synology NAS DS920+ (backup): €650
- UPS (APC 1500VA): €250
- Managed switch (24-port): €200
- Rack cabinet (12U): €300
- Total: €2,900 + installation
```

### **Remote Site (Lisbon, Algarve, etc.)**

**Per Site: €500**
```
- Raspberry Pi 4 (8GB): €90
- SD card (64GB, industrial grade): €25
- USB SSD (256GB backup): €50
- Arduino UNO R4 WiFi: €35
- 2x DHT20 sensors: €20
- Power supply + case: €30
- Network: Use existing WiFi/LTE
```

---

## 📶 **Internet Backup (4G LTE)**

For critical sites (Algarve tourist season):

```
Primary: Fiber/Cable internet (fast, cheap)
Backup: 4G LTE dongle (failover)

If fiber goes down:
1. Raspberry Pi detects no internet
2. Switches to 4G USB dongle
3. VPN reconnects via 4G
4. Sends alert: "Site on backup internet"
5. Data continues syncing (slower)

Cost: €10-20/month for 4G backup SIM
```

---

## 🎯 **Implementation Roadmap**

### **Phase 1: Porto (Month 1)**
- ✅ Set up quarter-bedroom server
- ✅ Configure VPN server (WireGuard)
- ✅ Deploy first greenhouse (test site)
- ✅ Establish monitoring baseline

### **Phase 2: Lisbon Expansion (Month 2)**
- ✅ Configure remote Raspberry Pi
- ✅ VPN tunnel to Porto
- ✅ 2-day on-site setup
- ✅ Train local contact
- ✅ Monitor remotely from Porto

### **Phase 3: Multi-Site Management (Month 3)**
- ✅ Add Algarve site
- ✅ Central dashboard (all locations)
- ✅ Automated alerting
- ✅ Monthly visit schedule

### **Phase 4: Scale (Month 6)**
- ✅ 5-10 locations across Portugal
- ✅ Hire regional technician
- ✅ Data marketplace launch
- ✅ Franchise model ready

---

## 🔒 **Is Quarter-Bedroom Server Safe?**

**YES! Here's why:**

✅ **Physical security** - In your home, under your control
✅ **Network security** - VPN encryption + firewall
✅ **GDPR compliant** - Portugal-based, EU jurisdiction
✅ **Cost effective** - No monthly cloud fees (€0 vs €200+/month)
✅ **Performance** - Low latency, fast response
✅ **Privacy** - No third-party access to client data
✅ **Scalable** - Add locations without infrastructure changes

**Better than cloud for:**
- Sensitive customer data
- Real-time monitoring (low latency)
- GDPR compliance (data sovereignty)
- Cost at scale (3+ locations)

**When to upgrade:**
- 10+ locations (consider colo/datacenter)
- 100+ clients (need redundancy)
- International expansion (need CDN)

---

## 📚 **Related Documentation**

- `BUSINESS_INTELLIGENCE.md` - Client management
- `HOT_CULTURE_LOCAL_MARKETS.md` - Crop strategies
- `DUAL_SENSOR_REDUNDANCY.md` - Sensor reliability

---

**Your multi-location network is ready. Start Porto, expand smartly, scale profitably!** 🌐🚀
