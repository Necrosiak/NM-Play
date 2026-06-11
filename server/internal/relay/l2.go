package relay

import (
"log"
"net"
"time"
)

type L2Relay struct {
addr    string
hub     *Hub
conn    *net.UDPConn
clients map[string]*Client
}

func NewL2Relay(addr string, hub *Hub) *L2Relay {
return &L2Relay{addr: addr, hub: hub, clients: make(map[string]*Client)}
}

func (r *L2Relay) Run() {
addr, _ := net.ResolveUDPAddr("udp", r.addr)
conn, err := net.ListenUDP("udp", addr)
if err != nil {
log.Fatalf("[L2] Failed to listen: %v", err)
}
r.conn = conn
defer conn.Close()
log.Printf("[L2] Listening on %s (PS2/PS3/Xbox/GameCube/Wii)", r.addr)
buf := make([]byte, 4096)
for {
n, remoteAddr, err := conn.ReadFromUDP(buf)
if err != nil || n < 7 {
continue
}
data := make([]byte, n)
copy(data, buf[:n])
go r.handlePacket(data, remoteAddr)
}
}

func (r *L2Relay) handlePacket(data []byte, remoteAddr *net.UDPAddr) {
key := remoteAddr.String()
platform := r.platformFromByte(data[0])
client, exists := r.clients[key]
if !exists {
client = NewRelayClient(platform, remoteAddr, net.IP(data[1:7]))
r.clients[key] = client
r.hub.Register(client)
go r.sendLoop(client)
log.Printf("[L2] New %s client: %s", platform, key)
}
client.LastSeen = time.Now()
r.hub.Broadcast(Packet{Data: data, From: client, Platform: platform})
}

func (r *L2Relay) platformFromByte(b byte) string {
switch b {
case 0x01: return PlatformPS2
case 0x02: return PlatformPS3
case 0x03: return PlatformXbox
case 0x04: return PlatformXbox360
case 0x05: return PlatformGameCube
case 0x06: return PlatformWii
default:   return PlatformPS2
}
}

func (r *L2Relay) sendLoop(client *Client) {
for pkt := range client.Send {
if client.RemoteIP != nil {
r.conn.WriteToUDP(pkt.Data, client.RemoteIP)
}
}
}
