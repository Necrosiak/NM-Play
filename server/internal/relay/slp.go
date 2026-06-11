package relay

import (
"log"
"net"
"time"
)

const (
SLPKeepalive = 0x00
SLPIPV4      = 0x01
)

type SLPRelay struct {
addr    string
hub     *Hub
conn    *net.UDPConn
clients map[string]*Client
}

func NewSLPRelay(addr string, hub *Hub) *SLPRelay {
return &SLPRelay{addr: addr, hub: hub, clients: make(map[string]*Client)}
}

func (r *SLPRelay) Run() {
addr, _ := net.ResolveUDPAddr("udp", r.addr)
conn, err := net.ListenUDP("udp", addr)
if err != nil {
log.Fatalf("[SLP] Failed to listen: %v", err)
}
r.conn = conn
defer conn.Close()
log.Printf("[SLP] Listening on %s (Switch)", r.addr)
buf := make([]byte, 2048)
for {
n, remoteAddr, err := conn.ReadFromUDP(buf)
if err != nil || n < 1 {
continue
}
data := make([]byte, n)
copy(data, buf[:n])
go r.handlePacket(data, remoteAddr)
}
}

func (r *SLPRelay) handlePacket(data []byte, remoteAddr *net.UDPAddr) {
key := remoteAddr.String()
client, exists := r.clients[key]
if !exists {
var lanIP net.IP
if len(data) >= 5 {
lanIP = net.IP(data[1:5])
}
client = NewRelayClient(PlatformSwitch, remoteAddr, lanIP)
r.clients[key] = client
r.hub.Register(client)
go r.sendLoop(client)
}
client.LastSeen = time.Now()
switch data[0] {
case SLPKeepalive:
if len(data) >= 5 {
client.LanIP = net.IP(data[1:5])
}
pkt := []byte{SLPKeepalive, 0, 0, 0, 0}
r.conn.WriteToUDP(pkt, remoteAddr)
case SLPIPV4:
if len(data) >= 6 {
r.hub.Broadcast(Packet{Data: data, From: client, Platform: PlatformSwitch})
}
}
}

func (r *SLPRelay) sendLoop(client *Client) {
for pkt := range client.Send {
if client.RemoteIP != nil {
r.conn.WriteToUDP(pkt.Data, client.RemoteIP)
}
}
}
