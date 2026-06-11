package relay

import (
"bufio"
"log"
"net"
"time"
)

type PSPRelay struct {
addr string
hub  *Hub
}

func NewPSPRelay(addr string, hub *Hub) *PSPRelay {
return &PSPRelay{addr: addr, hub: hub}
}

func (r *PSPRelay) Run() {
ln, err := net.Listen("tcp", r.addr)
if err != nil {
log.Fatalf("[PSP] Failed to listen: %v", err)
}
defer ln.Close()
log.Printf("[PSP] Listening on %s (PSP/Vita)", r.addr)
for {
conn, err := ln.Accept()
if err != nil {
continue
}
go r.handleConn(conn)
}
}

func (r *PSPRelay) handleConn(conn net.Conn) {
remoteAddr := conn.RemoteAddr().(*net.TCPAddr)
udpAddr := &net.UDPAddr{IP: remoteAddr.IP, Port: remoteAddr.Port}
client := NewRelayClient(PlatformPSP, udpAddr, nil)
client.TCPConn = conn
r.hub.Register(client)
log.Printf("[PSP] New client: %s", remoteAddr)
defer func() {
conn.Close()
r.hub.Unregister(client)
}()
go func() {
for pkt := range client.Send {
conn.SetWriteDeadline(time.Now().Add(5 * time.Second))
conn.Write(pkt.Data)
}
}()
reader := bufio.NewReader(conn)
buf := make([]byte, 4096)
for {
conn.SetReadDeadline(time.Now().Add(2 * time.Minute))
n, err := reader.Read(buf)
if err != nil {
return
}
if n == 0 {
continue
}
client.LastSeen = time.Now()
data := make([]byte, n)
copy(data, buf[:n])
r.hub.Broadcast(Packet{Data: data, From: client, Platform: PlatformPSP})
}
}
